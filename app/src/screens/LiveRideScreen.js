import React, { useEffect, useRef, useState } from "react";
import { View, Text, TouchableOpacity } from "react-native";
import LeafletMap from "../components/LeafletMap";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { postRouteGuardCheck } from "../api/client";
import { replayGpsTrace, SURAT_REAL_TRACE } from "../api/suratRealTrace";
import { formatDistance } from "../utils/risk";
import TripBar from "../components/TripBar";

const LEVEL_INFO = {
  normal: { label: "On track", color: colors.mint },
  level1_subtle_checkin: { label: "Quick check-in", color: colors.amber },
  level2_critical_escalation: { label: "Needs attention", color: colors.danger },
};

// Live ride demo: there is no real ride-hailing integration, so per the
// agreed approach we replay the REAL recorded GPS trace from
// data/gps_traces/surat_real_trace.csv as the vehicle position feed, at
// (scaled) real timestamps, and call POST /routeguard/check on every sample
// -- exactly like we would with a live ride-hailing position stream.
export default function LiveRideScreen({ navigation }) {
  const { routeResult, journeyId, setSafetyState } = useJourney();
  const [current, setCurrent] = useState(SURAT_REAL_TRACE[0]);
  const [checks, setChecks] = useState([]);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const stopRef = useRef(null);

  const expectedSegmentIds = (routeResult?.segments || []).map((s) => s.segment_id);

  async function handlePoint(pt) {
    setCurrent(pt);
    try {
      const res = await postRouteGuardCheck({
        journey_id: journeyId,
        expected_route_segment_ids: expectedSegmentIds,
        current: { lat: pt.lat, lon: pt.lon },
      });
      setChecks((prev) => [res, ...prev].slice(0, 5));
      if (res.response_level && res.response_level !== "normal") {
        setSafetyState(res.response_level);
        navigation.navigate("Deviation", { check: res });
      }
    } catch (e) {
      setChecks((prev) => [{ error: e.message, isTimeout: e.isTimeout }, ...prev].slice(0, 5));
    }
  }

  function start() {
    setRunning(true);
    setFinished(false);
    stopRef.current = replayGpsTrace(handlePoint, {
      speedFactor: 6,
      onComplete: () => {
        setRunning(false);
        setFinished(true);
      },
    });
  }

  useEffect(() => () => stopRef.current && stopRef.current(), []);

  const traceCoords = SURAT_REAL_TRACE.map((p) => ({ lat: p.lat, lon: p.lon }));

  return (
    <View style={s.screen}>
      <Text style={s.title}>Your ride, watched over</Text>
      <TripBar navigation={navigation} currentScreen="LiveRide" />
      <Text style={s.subtitle}>We check your vehicle's position against the route we expected, the whole way.</Text>

      <View style={{ marginBottom: 12 }}>
        <LeafletMap
          center={{ lat: current.lat, lon: current.lon }}
          zoom={15}
          polyline={traceCoords}
          markers={[{ lat: current.lat, lon: current.lon, color: "#8C6FF2", label: "Vehicle (real trace replay)" }]}
          height={260}
        />
      </View>

      {!running ? (
        <TouchableOpacity style={s.button} onPress={start}>
          <Text style={s.buttonText}>Start ride</Text>
        </TouchableOpacity>
      ) : (
        <TouchableOpacity style={s.buttonSecondary} onPress={() => { stopRef.current && stopRef.current(); setRunning(false); }}>
          <Text style={s.buttonSecondaryText}>Stop</Text>
        </TouchableOpacity>
      )}

      {checks[0] && !checks[0].error && (
        <View style={s.card}>
          <View style={s.row}>
            <Text style={{ color: colors.text, fontWeight: "700" }}>Latest check</Text>
            <View style={s.badge((LEVEL_INFO[checks[0].response_level] || LEVEL_INFO.normal).color)}>
              <Text style={s.badgeText}>{(LEVEL_INFO[checks[0].response_level] || LEVEL_INFO.normal).label}</Text>
            </View>
          </View>
          <Text style={s.muted}>{checks[0].reason}</Text>
          {checks[0].response_level !== "normal" && (
            <Text style={[s.muted, { marginTop: 4 }]}>
              Off the expected path by about {formatDistance(checks[0].deviation_distance_m)}.
            </Text>
          )}
        </View>
      )}
      {checks[0]?.error && (
        <View style={s.card}>
          <Text style={{ color: colors.text, fontWeight: "700" }}>Couldn't reach the server</Text>
          <Text style={[s.muted, { marginTop: 4 }]}>
            {checks[0].isTimeout ? "That check took too long — " : ""}We'll keep trying on the next update.
          </Text>
        </View>
      )}

      {finished && (
        <View style={s.card}>
          <Text style={{ color: colors.mint, fontWeight: "700" }}>You've arrived</Text>
          <Text style={[s.muted, { marginTop: 4 }]}>
            ABHAYA keeps watching for a few more minutes on your final walk.
          </Text>
          <TouchableOpacity style={[s.button, { marginTop: 10 }]} onPress={() => navigation.navigate("WalkGuard")}>
            <Text style={s.buttonText}>Continue: start WalkGuard</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}
