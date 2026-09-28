// ABHAYA backend API client.
//
// Local/device testing: change API_BASE_URL to your machine's LAN IP (not
// "localhost"), e.g. "http://192.168.1.23:8000". On an Android emulator,
// "http://10.0.2.2:8000" reaches your host machine.
//
// Production (Vercel web build): set EXPO_PUBLIC_API_BASE_URL in Vercel's
// environment variables to the deployed Render backend URL, e.g.
// "https://abhaya-backend.onrender.com". Expo inlines EXPO_PUBLIC_* env vars
// at build time -- this is the supported way to configure it without
// editing source per-environment. Falls back to the dev tunnel URL below
// only when that env var isn't set (i.e. local dev).
export let API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || "https://society-pearl-monday-andrews.trycloudflare.com";

export function setApiBaseUrl(url) {
  API_BASE_URL = url.replace(/\/+$/, "");
}

// Render's free tier has genuinely throttled/shared CPU -- measured a
// trivial 57m route taking 10.3s there (vs. milliseconds on a local dev
// machine), and a real cross-city route occasionally taking 20s+. 15s was
// too tight for legitimate (if slow) responses on that tier, so this is
// raised with real headroom rather than tuned to the bare minimum observed.
const REQUEST_TIMEOUT_MS = 30000;

// Thrown when a request doesn't finish within REQUEST_TIMEOUT_MS. Screens
// check `err.isTimeout` to show a "Retry" affordance instead of a dead
// spinner (see the DEC-004 fix: infinite spinner with no way out).
export class ApiTimeoutError extends Error {
  constructor(path) {
    super(`Request to ${path} timed out after ${REQUEST_TIMEOUT_MS / 1000}s. Check your connection and try again.`);
    this.isTimeout = true;
  }
}

async function request(path, { method = "GET", body, query } = {}) {
  let url = `${API_BASE_URL}${path}`;
  if (query) {
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    if (qs) url += `?${qs}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    if (e.name === "AbortError") throw new ApiTimeoutError(path);
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`ABHAYA API ${method} ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

// POST /route  -- RouteRequest -> RouteResponse
export function postRoute({ origin, destination, mode = "walk", time, w_safety, w_time, w_infra }) {
  return request("/route", {
    method: "POST",
    body: { origin, destination, mode, time, w_safety, w_time, w_infra },
  });
}

// GET /infrastructure?lat=&lon=&radius=
export function getInfrastructure({ lat, lon, radius = 300 }) {
  return request("/infrastructure", { query: { lat, lon, radius } });
}

// POST /safedrop -- SafeDropRequest -> SafeDropResponse
export function postSafeDrop({ destination, candidates, time, max_extra_walk_m = 250.0 }) {
  return request("/safedrop", {
    method: "POST",
    body: { destination, candidates, time, max_extra_walk_m },
  });
}

// POST /routeguard/check -- RouteGuardCheckRequest -> RouteGuardCheckResponse
export function postRouteGuardCheck({
  journey_id,
  expected_route_segment_ids,
  current,
  current_time,
  expected_time,
}) {
  return request("/routeguard/check", {
    method: "POST",
    body: { journey_id, expected_route_segment_ids, current, current_time, expected_time },
  });
}

// POST /walkguard/event -- WalkGuardEventRequest -> WalkGuardEventResponse
// NOTE: `location` is required by the backend (WalkGuardEventRequest.location:
// LatLon) -- it combines motion anomaly with the location's risk context per
// spec 24.5/24.9, so a call without it will 422.
export function postWalkGuardEvent({
  journey_id,
  location,
  timestamp,
  accel_magnitude,
  accel_variance,
  gyro_magnitude,
  speed_mps,
  impact_detected = false,
  baseline_accel_magnitude,
}) {
  return request("/walkguard/event", {
    method: "POST",
    body: {
      journey_id,
      location,
      timestamp,
      accel_magnitude,
      accel_variance,
      gyro_magnitude,
      speed_mps,
      impact_detected,
      baseline_accel_magnitude,
    },
  });
}

// GET /safe-havens?lat=&lon=&time=&radius=
export function getSafeHavens({ lat, lon, time, radius = 400 }) {
  return request("/safe-havens", { query: { lat, lon, time, radius } });
}

// POST /safety-insight -- SafetyInsightRequest -> SafetyInsightResponse
export function postSafetyInsight({ route_context, retrieved_passages = [], question }) {
  return request("/safety-insight", {
    method: "POST",
    body: { route_context, retrieved_passages, question },
  });
}

export function getHealth() {
  return request("/health");
}

// POST /companions/match -- CompanionMatchRequest -> CompanionMatchResponse
export function postCompanionsMatch({ origin, destination, time, mode = "walk" }) {
  return request("/companions/match", {
    method: "POST",
    body: { origin, destination, time, mode },
  });
}

// POST /companions/request -- CompanionRequestIn -> CompanionRequestResponse
export function postCompanionsRequest({ journey_id, candidate_id }) {
  return request("/companions/request", {
    method: "POST",
    body: { journey_id, candidate_id },
  });
}

// GET /bus/safety-status?vehicle_id=&operator=&journey_id=
export function getBusSafetyStatus({ vehicle_id, operator, journey_id }) {
  return request("/bus/safety-status", { query: { vehicle_id, operator, journey_id } });
}

// POST /transitguard/check -- TransitGuardCheckRequest -> TransitGuardCheckResponse
export function postTransitGuardCheck({
  journey_id,
  vehicle_id,
  expected_route_segment_ids,
  current,
  current_time,
  expected_time,
  include_bus_evidence = true,
}) {
  return request("/transitguard/check", {
    method: "POST",
    body: {
      journey_id,
      vehicle_id,
      expected_route_segment_ids,
      current,
      current_time,
      expected_time,
      include_bus_evidence,
    },
  });
}
