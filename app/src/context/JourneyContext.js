import React, { createContext, useContext, useState } from "react";

// Shared journey state across the 9 screens: origin/destination, the chosen
// route from /route, the journey_id, and current safety state.
const JourneyContext = createContext(null);

export function JourneyProvider({ children }) {
  const [origin, setOrigin] = useState(null); // {lat, lon, label}
  const [destination, setDestination] = useState(null);
  const [mode, setMode] = useState("ride_hailing");
  const [routeResult, setRouteResult] = useState(null); // RouteResponse
  const [journeyId, setJourneyId] = useState(null);
  const [safeDropResult, setSafeDropResult] = useState(null);
  const [safetyState, setSafetyState] = useState("normal"); // normal|level1|level2

  const value = {
    origin, setOrigin,
    destination, setDestination,
    mode, setMode,
    routeResult, setRouteResult,
    journeyId, setJourneyId,
    safeDropResult, setSafeDropResult,
    safetyState, setSafetyState,
  };

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  const ctx = useContext(JourneyContext);
  if (!ctx) throw new Error("useJourney must be used within JourneyProvider");
  return ctx;
}
