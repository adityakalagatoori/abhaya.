# ABHAYA RAG — Example Outputs (retrieved text side-by-side with generated explanation)

## Night walk near Athwa riverfront, Surat (high structured risk)
- **Location**: Athwa Lines riverfront service road, Surat
- **Time**: 2026-09-21T21:30:00+05:30
- **Structured risk context**: `{"segments": [{"segment_id": "seg-4821", "description": "riverfront service road near Athwa, low commercial density, low lighting reported"}], "total_risk": 0.71, "high_risk_factors": ["low_lighting_reported_zone", "isolated_after_dark", "low_foot_traffic"]}`
- **Generation backend used**: ollama:qwen2.5:1.5b-instruct
- **Grounded**: True

**Retrieved evidence (side A):**
> [0.467] Surat Municipal Corporation — Streetlight Department (official page) — Surat Municipal Corporation (government) (https://www.suratmunicipal.gov.in/Departments/StreetLightsHome) (undated (official standing government page), retrieved 2026-09-21)
> "Citizens can file streetlight outage/complaint reports through the online portal (Complaint section under Online Services) or by phone at +91-261-2423750 to 2423756 or +91-261-2422285 to 2422287. Relevance note: This is an official municipal government source documenting that street lighting mainten..."
>
> [0.454] Surat Municipal Corporation — Streetlight Department (official page) — Surat Municipal Corporation (government) (https://www.suratmunicipal.gov.in/Departments/StreetLightsHome) (undated (official standing government page), retrieved 2026-09-21)
> "The Surat Municipal Corporation's Streetlight Department is responsible for installation, operation, and maintenance of all streetlights on roads within SMC limits, as well as street/road lights on high masts at major traffic junctions. Streetlight services are provided through a partially decentral..."
>
> [0.394] Railways: Guidelines to prevent incidents of Crime against Women in trains and in railway premises — GovtEmpDiary (reproducing Indian Railways Security Circular No. 02/2021) (https://govtempdiary.com/2021/03/railways-guidelines-to-prevent-incidents-of-crime-against-women-in-trains-and-in-railway-premises/73935) (2021-03-02, retrieved 2026-09-21)
> "Relevance note: this is an official (secondarily reproduced) railway security circular. It is generic national guidance, not a Surat-specific incident report, but is relevant background for any route/waiting-point context near Surat railway station (e.g., verified safe-haven pickup near a station, o..."
>
> [0.375] Surat Municipal Corporation — Streetlight Department (official page) — Surat Municipal Corporation (government) (https://www.suratmunicipal.gov.in/Departments/StreetLightsHome) (undated (official standing government page), retrieved 2026-09-21)
> "Stated responsibilities (quoted from the official page):
- "Installation, operation & maintenance of all streetlight on the roads within SMC limits"
- Management of street and road lights at high masts positioned at major traffic junctions
- "Installation, operation & maintenance of Decorative Lumin..."
>

**Generated explanation (side B):**
> The risk score for the Athwa Lines riverfront service road in Surat is 0.71, indicating a moderate risk level. The structured risk context reveals that the road is located in a low commercial density area with low lighting reported, which contributes to the moderate risk. The retrieved evidence confirms that the Surat Municipal Corporation's Streetlight Department is responsible for maintaining streetlights and high masts, but does not provide specific information about the current lighting conditions or the presence of CCTV or access control. The risk is not directly related to the specific location of the road, but rather to the overall infrastructure and maintenance practices in Surat.

---

## Route near Surat railway station at night
- **Location**: Surat railway station approach road
- **Time**: 2026-09-21T22:15:00+05:30
- **Structured risk context**: `{"segments": [{"segment_id": "seg-1190", "description": "station approach road, moderate foot traffic, unverified lighting"}], "total_risk": 0.55, "high_risk_factors": ["station_adjacent", "night_travel"]}`
- **Generation backend used**: ollama:qwen2.5:1.5b-instruct
- **Grounded**: True

**Retrieved evidence (side A):**
> [0.633] Railways: Guidelines to prevent incidents of Crime against Women in trains and in railway premises — GovtEmpDiary (reproducing Indian Railways Security Circular No. 02/2021) (https://govtempdiary.com/2021/03/railways-guidelines-to-prevent-incidents-of-crime-against-women-in-trains-and-in-railway-premises/73935) (2021-03-02, retrieved 2026-09-21)
> "Relevance note: this is an official (secondarily reproduced) railway security circular. It is generic national guidance, not a Surat-specific incident report, but is relevant background for any route/waiting-point context near Surat railway station (e.g., verified safe-haven pickup near a station, o..."
>
> [0.529] Surat Municipal Corporation — Streetlight Department (official page) — Surat Municipal Corporation (government) (https://www.suratmunicipal.gov.in/Departments/StreetLightsHome) (undated (official standing government page), retrieved 2026-09-21)
> "The Surat Municipal Corporation's Streetlight Department is responsible for installation, operation, and maintenance of all streetlights on roads within SMC limits, as well as street/road lights on high masts at major traffic junctions. Streetlight services are provided through a partially decentral..."
>
> [0.479] Is Surat Safe for Travel Right Now? (2026 Safety Rating) — TravelSafe-Abroad.com (https://www.travelsafe-abroad.com/india/surat/) (2026 (site-dated safety index page), retrieved 2026-09-21)
> "Surat scores 80/80 on this site's safety index, placing it, per the source, among India's safer major cities alongside Navi Mumbai. The page frames most concerns as practical rather than violent-crime-related. Low-risk areas noted: Gopi Talav and other family-oriented public areas draw local familie..."
>
> [0.453] 2022 crime rate: NCRB data burns holes in much-touted Gujarat Model — The Federal (https://thefederal.com/category/states/west/gujarat/2022-crime-rate-ncrb-data-burns-holes-in-much-touted-gujarat-model-102570) (2023-12-07, retrieved 2026-09-21)
> "Surat-specific finding: Surat, described as the economic hub of Gujarat, recorded the highest number of crimes against women among cities in the state. The surge is attributed by the report to rising consumption of IMFL (India-made foreign liquor) and country liquor. A social activist filed an RTI a..."
>

**Generated explanation (side B):**
> The structured risk context indicates moderate foot traffic and unverified lighting on the Surat railway station approach road. The retrieved evidence does not provide specific details about lighting or CCTV status at this location. The safety index for Surat, which is listed as 80/80, places it among safer major cities in India alongside Navi Mumbai. The 2022 crime rate data shows that Surat, as the economic hub of Gujarat, has experienced a surge in crimes against women, particularly attributed to the consumption of IMFL and country liquor.

---

## Daytime route in a well-documented low-risk area (should trigger uncertainty / low-grounding path)
- **Location**: Gopi Talav area, Surat
- **Time**: 2026-09-21T11:00:00+05:30
- **Structured risk context**: `{"segments": [{"segment_id": "seg-0042", "description": "family park frontage road, daytime, high foot traffic"}], "total_risk": 0.12, "high_risk_factors": []}`
- **Generation backend used**: ollama:qwen2.5:1.5b-instruct
- **Grounded**: True

**Retrieved evidence (side A):**
> [0.521] Is Surat Safe for Travel Right Now? (2026 Safety Rating) — TravelSafe-Abroad.com (https://www.travelsafe-abroad.com/india/surat/) (2026 (site-dated safety index page), retrieved 2026-09-21)
> "Surat scores 80/80 on this site's safety index, placing it, per the source, among India's safer major cities alongside Navi Mumbai. The page frames most concerns as practical rather than violent-crime-related. Low-risk areas noted: Gopi Talav and other family-oriented public areas draw local familie..."
>
> [0.369] 2022 crime rate: NCRB data burns holes in much-touted Gujarat Model — The Federal (https://thefederal.com/category/states/west/gujarat/2022-crime-rate-ncrb-data-burns-holes-in-much-touted-gujarat-model-102570) (2023-12-07, retrieved 2026-09-21)
> "Surat-specific finding: Surat, described as the economic hub of Gujarat, recorded the highest number of crimes against women among cities in the state. The surge is attributed by the report to rising consumption of IMFL (India-made foreign liquor) and country liquor. A social activist filed an RTI a..."
>
> [0.351] Crime in India 2022 (Volume/Book 1) — National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India (https://www.ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577CrimeinIndia2022Book1.pdf) (2023 (release of 2022 data), retrieved 2026-09-21)
> "Note for developers: for a production system, download and parse the actual state/district tables from this PDF (or from data.gov.in's NCRB datasets) rather than relying only on secondary news analysis, to get precise, per-district figures for Surat...."
>
> [0.350] Is Surat Safe for Travel Right Now? (2026 Safety Rating) — TravelSafe-Abroad.com (https://www.travelsafe-abroad.com/india/surat/) (2026 (site-dated safety index page), retrieved 2026-09-21)
> "Relevance note: This is a general tourist-safety index/advisory, not an incident report. It supports general guidance about isolated/unlit areas after dark but contains no specific incident data and should not be cited as evidence of a specific crime event...."
>

**Generated explanation (side B):**
> The Gopi Talav area in Surat is generally considered safe for travel, as it is described as a family-oriented public area and is noted as a safer public space. The structured risk context indicates a low risk score of 0.12, with no high-risk factors present. The retrieved evidence supports this assessment by highlighting that Surat, despite being the economic hub of Gujarat, has a relatively low crime rate, including a specific finding that Surat recorded the highest number of crimes against women among cities in the state. This suggests that while the area is generally safe, it is advisable to be cautious after dark, especially in unlit areas.

---

## Different city (Bengaluru) -- corpus is India/Gujarat-crime themed so generic passages still clear threshold; shown to demonstrate the model is NOT told this is Surat-specific
- **Location**: MG Road, Bengaluru
- **Time**: 2026-09-21T23:00:00+05:30
- **Structured risk context**: `{"segments": [{"segment_id": "seg-9999", "description": "unmapped segment, no local evidence available"}], "total_risk": 0.4, "high_risk_factors": ["no_local_evidence"]}`
- **Generation backend used**: ollama:qwen2.5:1.5b-instruct
- **Grounded**: True

**Retrieved evidence (side A):**
> [0.413] Is Surat Safe for Travel Right Now? (2026 Safety Rating) — TravelSafe-Abroad.com (https://www.travelsafe-abroad.com/india/surat/) (2026 (site-dated safety index page), retrieved 2026-09-21)
> "Relevance note: This is a general tourist-safety index/advisory, not an incident report. It supports general guidance about isolated/unlit areas after dark but contains no specific incident data and should not be cited as evidence of a specific crime event...."
>
> [0.392] Railways: Guidelines to prevent incidents of Crime against Women in trains and in railway premises — GovtEmpDiary (reproducing Indian Railways Security Circular No. 02/2021) (https://govtempdiary.com/2021/03/railways-guidelines-to-prevent-incidents-of-crime-against-women-in-trains-and-in-railway-premises/73935) (2021-03-02, retrieved 2026-09-21)
> "Relevance note: this is an official (secondarily reproduced) railway security circular. It is generic national guidance, not a Surat-specific incident report, but is relevant background for any route/waiting-point context near Surat railway station (e.g., verified safe-haven pickup near a station, o..."
>
> [0.383] Crime in India 2022 (Volume/Book 1) — National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India (https://www.ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577CrimeinIndia2022Book1.pdf) (2023 (release of 2022 data), retrieved 2026-09-21)
> "Use in this corpus: this document is referenced as the authoritative government source underlying secondary reporting (see corpus entry 001, The Federal's analysis of Gujarat's 2022 NCRB figures, including Surat-specific commentary about crimes against women in the city). The full PDF was not reprod..."
>
> [0.361] Crime in India 2022 (Volume/Book 1) — National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India (https://www.ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577CrimeinIndia2022Book1.pdf) (2023 (release of 2022 data), retrieved 2026-09-21)
> "This is the official annual NCRB "Crime in India" publication for reporting year 2022, published by the Ministry of Home Affairs. It is the primary government source of state- and city-level registered crime statistics in India, including categories such as crimes against women (IPC/BNS-defined offe..."
>

**Generated explanation (side B):**
> The location MG Road, Bengaluru, is currently assessed by the routing/risk engine as having a total risk score of 0.4, indicating a moderate level of risk. The structured risk context mentions that there is no local evidence available for this segment, which is a key factor contributing to the low risk score. The retrieved evidence does not provide specific incident data or details about lighting or CCTV conditions in this particular location. It does, however, offer general guidance on the relevance of lighting and access control as risk factors for railway-adjacent areas, which is relevant to the context of the location. The evidence is general/regional context and should not be cited as a live report or specific incident data.

---

## Fully out-of-domain query (must return honest uncertainty, no fabrication -- proves MIN_RELEVANCE_SCORE guardrail actually fires)
- **Location**: unspecified location
- **Time**: 2026-09-21T12:00:00+05:30
- **Structured risk context**: `{"segments": [{"segment_id": "seg-0000", "description": "restaurant menu pricing and weather forecast"}], "total_risk": 0.0, "high_risk_factors": ["cheese_supply_shortage", "average_rainfall_variance"]}`
- **Generation backend used**: n/a (uncertainty path, no generation called)
- **Grounded**: False

**Retrieved evidence (side A):**
> (none above relevance threshold)

**Generated explanation (side B):**
> No sufficiently relevant real source text was found for this location/time/risk context in the current corpus. This is not a statement that the area is unsafe or safe -- it means the RAG layer has insufficient grounded evidence to comment beyond the structured risk score already computed by the routing/risk engine.

**Uncertainty note:** No sufficiently relevant real source text was found for this location/time/risk context in the current corpus. This is not a statement that the area is unsafe or safe -- it means the RAG layer has insufficient grounded evidence to comment beyond the structured risk score already computed by the routing/risk engine.

---
