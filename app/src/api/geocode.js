// Real place-name search via OpenStreetMap's free Nominatim API (no API key
// needed, matches the docx's OSM-only stack). Used to replace raw lat/lon
// text fields with a normal "type a place name" search -- see plan item #1.
//
// Nominatim's usage policy requires a descriptive User-Agent and asks
// clients not to hammer it; we debounce calls in the UI layer (see
// PlaceSearchInput) rather than here.
const NOMINATIM_BASE = "https://nominatim.openstreetmap.org";

export async function searchPlaces(query, { limit = 5, biasLat, biasLon } = {}) {
  if (!query || query.trim().length < 3) return [];

  const params = new URLSearchParams({
    q: query,
    format: "jsonv2",
    limit: String(limit),
    addressdetails: "0",
  });
  // Bias results toward the area the user is already working in (e.g. Surat)
  // by preferring results near a viewbox, without hard-restricting to it.
  if (biasLat != null && biasLon != null) {
    const delta = 0.5; // ~55km box, generous enough not to exclude real nearby places
    params.set("viewbox", `${biasLon - delta},${biasLat + delta},${biasLon + delta},${biasLat - delta}`);
    params.set("bounded", "0");
  }

  const res = await fetch(`${NOMINATIM_BASE}/search?${params.toString()}`, {
    headers: {
      // Nominatim's usage policy requires a real identifying User-Agent.
      "User-Agent": "ABHAYA-safety-navigation-app/1.0 (hackathon prototype)",
    },
  });
  if (!res.ok) throw new Error(`Place search failed: ${res.status}`);
  const data = await res.json();
  return data.map((r) => ({
    label: r.display_name,
    lat: parseFloat(r.lat),
    lon: parseFloat(r.lon),
  }));
}
