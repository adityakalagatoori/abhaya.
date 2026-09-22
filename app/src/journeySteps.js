// The real journey order per spec section 8 ("Complete User Journey") and
// section 14 (demo story): route -> safe-haven pickup -> SafeDrop near
// destination -> live ride with RouteGuard -> WalkGuard after the ride.
// Used to drive the persistent TripBar (plan item #3) and to replace the
// old "wall of 6 unordered buttons" RouteComparison hub (plan item #2).
export const JOURNEY_STEPS = [
  { key: "route", screen: "RouteComparison", label: "Your route" },
  { key: "safehaven", screen: "SafeHaven", label: "Waiting spot" },
  { key: "safedrop", screen: "SafeDrop", label: "Drop-off spot" },
  { key: "ride", screen: "LiveRide", label: "Your ride" },
  { key: "walkguard", screen: "WalkGuard", label: "Walk home" },
];

export function stepIndexForScreen(screenName) {
  return JOURNEY_STEPS.findIndex((s) => s.screen === screenName);
}
