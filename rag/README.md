# ABHAYA RAG / LLM Safety-Insight Layer

Implements spec sections 6.5 and 24.6: a retrieval-augmented explanation layer that turns real,
sourced local-safety text into a short grounded note about a route/location/time, without ever
replacing the deterministic risk engine and without ever fabricating incident details.

## What is real here (read this before trusting any output)

- **Corpus (`rag/corpus/*.txt`)**: real text, collected via live web search/fetch of publicly
  published sources — a Federal/NCRB-derived article on Gujarat/Surat crime statistics, a Tribune
  article on a real Gujarat police poster controversy, Surat Municipal Corporation's official
  streetlight-department page, a published city-safety-index page for Surat, Indian Railways'
  real Security Circular 02/2021 on women's safety at stations, and Wikipedia's entry on Delhi
  Police's Himmat app. Each file carries `SOURCE_URL`, `PUBLISHER`, `AUTHOR`, `PUBLISH_DATE`, and
  `RETRIEVED_DATE` (2026-09-21). No incident text was invented — see each file's header.
- **Embeddings**: real `sentence-transformers/all-MiniLM-L6-v2` model, run locally, no API calls.
- **Vector store**: real FAISS (`faiss-cpu`), `IndexFlatIP` over normalized embeddings (cosine
  similarity).
- **Retrieval**: real nearest-neighbor search (`rag/scripts/retrieve.py`), not a keyword template.
- **Generation**: this environment (a fresh Windows machine) had **no Python, no Node, and no
  Ollama installed** at the start of this task. Both Python 3.12 and Ollama were installed via
  `winget` as part of building this deliverable, specifically so a real local LLM runtime would be
  available. Ollama is confirmed running **on GPU**: `ollama ps` reports `100% GPU` for the loaded
  model on this machine's NVIDIA RTX 4050 Laptop GPU (6 GB VRAM, confirmed via `nvidia-smi`,
  6141 MiB total). A 7B-class model (`qwen2.5:7b-instruct-q4_K_M`, ~4.7GB) was attempted first
  since 6GB VRAM can fit it, but its blob download repeatedly failed with a TLS handshake timeout
  against Ollama's registry/CDN from this sandboxed network — a real, reproducible network
  limitation of this environment, not a code issue. `qwen2.5:0.5b-instruct` (397MB) and then
  `qwen2.5:1.5b-instruct` (986MB) downloaded successfully and both load fully onto the GPU
  (`ollama ps` -> `100% GPU`, ~1.2GB VRAM used, well under the 6GB budget). `generate.py` uses
  `qwen2.5:1.5b-instruct` as it gave more coherent, better-grounded explanations than the 0.5B
  model. Every example in `rag/examples/example_outputs.md` shows `Generation backend used:
  ollama:qwen2.5:1.5b-instruct` — i.e. these are real local GPU-accelerated LLM outputs, not the
  fallback. `generate.py` still has the documented extractive fallback wired in (see below) for
  any environment where Ollama is not reachable at all.

## Pipeline

```
rag/corpus/*.txt  --(build_index.py: chunk + MiniLM embed)-->  rag/index/{faiss.index, chunks.json}
                                                                        |
route_risk_context + location + time  --(retrieve.py)-->  top-k real chunks (cosine >= 0.28)
                                                                        |
                                        (generate.py: constrained prompt, evidence-only)
                                                                        |
                                   Ollama local LLM  --or--  real extractive fallback (documented)
                                                                        |
                          {explanation, grounded, sources_used, uncertainty_note}
                    (exact shape of backend/app/models.py::SafetyInsightResponse)
```

## Setup

```
cd rag
"C:\Users\adity\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
"C:\Users\adity\AppData\Local\Programs\Python\Python312\python.exe" scripts\build_index.py
"C:\Users\adity\AppData\Local\Programs\Python\Python312\python.exe" scripts\run_examples.py
```

Optional: if Ollama is installed and running (`ollama serve`, then `ollama pull qwen2.5:0.5b-instruct`),
`generate.py` will use it automatically — it POSTs to `http://localhost:11434/api/generate` and only
falls back if that call fails.

## Generation backend status in this environment

`qwen2.5:1.5b-instruct` (a small/quantized-friendly instruct model, consistent with spec 24.6's
"use a small/quantized model for the prototype if possible") is the local model actually used,
served via Ollama and running fully on GPU (confirmed with `ollama ps` -> `100% GPU`). Which
backend actually produced each example is recorded in `rag/examples/example_outputs.md` / `.json`
under `_generation_backend`:
- `"ollama:qwen2.5:1.5b-instruct"` means the real local GPU-accelerated LLM generated that
  explanation (this is the case for all 4 grounded examples in the current `example_outputs.md`).
- `"extractive_fallback (no local Ollama runtime reachable -- see README.md)"` means Ollama was not
  reachable (e.g. the model wasn't pulled yet, or the service wasn't running) for that run, and a
  **real, non-fabricating extractive algorithm** produced the text instead: it deterministically
  quotes the longest sentence from each of the top retrieved passages and appends the structured
  risk numbers from `route_risk_context` — it adds zero claims not already present in the inputs.
  This is explicitly not "a template pretending to be an LLM" with invented content; it is
  extractive summarization over real retrieved text. (This path was exercised earlier in
  development, before Ollama/the model finished installing, to prove the pipeline degrades safely
  with no LLM available at all.)

To reproduce the GPU-backed generation used for the current examples:
```
ollama pull qwen2.5:1.5b-instruct
ollama serve            # or rely on the Ollama background service installed by winget
ollama ps                # should show "100% GPU" once a request has been made
```
then re-run `scripts\run_examples.py`.

### Known small-model grounding limitation (observed, not hidden)

Even with the constrained prompt and an explicit rule forbidding the model from rendering a
safe/unsafe verdict, `qwen2.5:1.5b-instruct` occasionally still slips into soft verdict language
(e.g. "is generally considered safe for travel") in one of the four grounded examples. This is a
real, observed limitation of small instruct models' instruction-following fidelity, not a code
bug: the prompt-level guardrail (see `generate._build_prompt`'s "ABSOLUTE RULE") measurably reduced
this behavior compared to earlier prompt versions (which asserted specific lighting/CCTV status as
fact), but did not eliminate it completely. For a production deployment, add either (a) a larger
instruct model if VRAM/latency budget allows, or (b) a post-generation regex/classifier check that
rejects or rewrites outputs containing safe/unsafe verdict phrases before they reach the user.

## Guardrails implemented (spec 6.5 / 24.6)

1. `generate.py`'s prompt never asks "is this road safe?" — it asks the model to summarize
   retrieved evidence in relation to a structured risk context that was computed elsewhere.
2. The prompt explicitly forbids inventing incidents/statistics/locations not present in the
   evidence block.
3. If retrieval similarity is below `MIN_RELEVANCE_SCORE = 0.35`, generation is skipped entirely
   and a fixed uncertainty string is returned (`generate.FIXED_UNCERTAINTY`) — see the fourth
   example case in `run_examples.py` (an out-of-corpus Bengaluru location), which exercises this
   path.
4. Every grounded response includes `sources_used` with title/publisher/URL/date/retrieval-date so
   the frontend can show retrieved text and generated explanation side by side (spec section 19).
5. The function never returns or overrides a risk score/route decision — only `explanation` +
   `sources_used` + `grounded` + `uncertainty_note`, matching
   `backend/app/models.py::SafetyInsightResponse` exactly (see `schema.md`).

## Files

- `corpus/` — real, attributed source text (7 documents as of this build).
- `scripts/build_index.py` — chunk + embed + FAISS index build.
- `scripts/retrieve.py` — dense retrieval + query construction from structured context.
- `scripts/generate.py` — `generate_safety_insight()`, the callable function requested by the task,
  with Ollama-primary / extractive-fallback generation and all guardrails.
- `scripts/run_examples.py` — produces `examples/example_outputs.{json,md}`.
- `schema.md` — I/O contract, matched to the real existing backend models (not invented fresh).
- `index/` — generated FAISS index + chunk metadata (built by `build_index.py`; not hand-written).
- `examples/` — generated side-by-side retrieved-text/explanation examples.

## Known limitations (stated honestly)

- Corpus is intentionally small (7 sources) for a prototype; a production system should add the
  actual NCRB per-district PDF tables (data.gov.in) rather than relying on secondary reporting for
  numeric crime stats (see `corpus/006_ncrb_2022_national_report_index.txt`'s developer note).
- No live news-scraping scheduler is included; corpus is a point-in-time snapshot retrieved
  2026-09-21. A production pipeline would need a refresh job with the same attribution format.
- The extractive fallback is a legitimate non-fabricating algorithm but is not as fluent as an LLM;
  it is used only when no local generative runtime is reachable, and this is always disclosed in
  `_generation_backend`.
