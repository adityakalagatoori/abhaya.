import { colors } from "../theme";

// Turns a raw 0..1 point risk_score (from the backend's risk engine) into a
// plain-language label + color, so screens never show a bare decimal to the
// user without context.
export function riskLevel(score) {
  const s = Number(score) || 0;
  if (s < 0.25) return { label: "Low concern", color: colors.mint };
  if (s < 0.5) return { label: "Some concern", color: colors.amber };
  if (s < 0.75) return { label: "Elevated concern", color: colors.coral };
  return { label: "High concern", color: colors.danger };
}

// A route's total_risk is a SUM across every segment, so a bigger route has
// a bigger number even if it's no riskier per-step. Average it back down to
// a comparable 0..1-ish scale for a fair Low/Some/Elevated/High label.
export function averageRouteRisk(routeResult) {
  const segs = routeResult?.segments || [];
  if (!segs.length) return 0;
  return (routeResult.total_risk || 0) / segs.length;
}

export function formatDistance(m) {
  if (m == null || Number.isNaN(m)) return "";
  if (m < 1000) return `${Math.round(m)} m`;
  return `${(m / 1000).toFixed(1)} km`;
}

export function formatMinutes(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "";
  const min = seconds / 60;
  if (min < 1) return "under a minute";
  return `${min.toFixed(0)} min`;
}
