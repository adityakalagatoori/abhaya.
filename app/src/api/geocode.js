// Real place-name search via OpenStreetMap's free Nominatim API (no API key
// needed, matches the docx's OSM-only stack). Used to replace raw lat/lon
// text fields with a normal "type a place name" search -- see plan item #1.
//
// Proxied through our own backend (GET /geocode/search) instead of calling
// Nominatim directly from the browser: Nominatim doesn't send CORS headers,
// so a direct browser fetch() is silently blocked by the browser's CORS
// policy on the deployed web build (confirmed live -- curl to Nominatim
// succeeds, the browser's fetch does not). The backend has no CORS
// restriction calling out to Nominatim server-side, and our own backend
// already has permissive CORS enabled for this frontend. Native builds
// aren't subject to CORS either way, so this keeps one code path for both.
import { API_BASE_URL } from "./client";

export async function searchPlaces(query, { limit = 5, biasLat, biasLon } = {}) {
  if (!query || query.trim().length < 3) return [];

  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (biasLat != null && biasLon != null) {
    params.set("bias_lat", String(biasLat));
    params.set("bias_lon", String(biasLon));
  }

  const res = await fetch(`${API_BASE_URL}/geocode/search?${params.toString()}`);
  if (!res.ok) throw new Error(`Place search failed: ${res.status}`);
  return res.json();
}
