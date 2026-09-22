import React, { useEffect, useRef, useState } from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { useMotionFeatures } from "../hooks/useMotionFeatures";
import { useDeviceLocation } from "../hooks/useDeviceLocation";
import { postWalkGuardEvent } from "../api/client";
import AvatarBadge from "../components/AvatarBadge";
import TripBar from "../components/TripBar";

const MONITOR_SECONDS = 300; // 5 minutes, per spec

// Post-ride WalkGuard: 5-minute monitoring window using REAL device
// accelerometer + gyroscope (via useMotionFeatures) and real GPS speed,
// sending real motion features to POST /walkguard/event every few seconds.
export default function WalkGuardScreen({ navigation }) {
  const { journeyId, setSafetyState } = useJourney();
  const { features, available } = useMotionFeatures();
  const { location } = useDeviceLocation({ watch: true });

  // Explicit per-activation consent, per spec section 18 ("use explicit
  // consent for sensor/biometric inputs and emergency sharing"). Re-asked
  // every time WalkGuard is opened rather than persisted, since consent
  // should be for this specific 5-minute monitoring session.
  const [consented, setConsented] = useState(false);
  const [active, setActive] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [remaining, setRemaining] = useState(MONITOR_SECONDS);
  const [lastResult, setLastResult] = useState(null);
  const [err, setErr] = useState(null);
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);

  useEffect(() => {
    return () => {
      intervalRef.current && clearInterval(intervalRef.current);
      countdownRef.current && clearInterval(countdownRef.current);
    };
  }, []);

  function start() {
    setActive(true);
    setHasStarted(true);
    setRemaining(MONITOR_SECONDS);

    countdownRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          stop({ completedNaturally: true });
          return 0;
        }
        return r - 1;
      });
    }, 1000);

    intervalRef.current = setInterval(async () => {
      if (!location?.coords) {
        setErr("Waiting for a real GPS fix before sending a WalkGuard event...");
        return;
      }
      try {
        const res = await postWalkGuardEvent({
          journey_id: journeyId,
          location: { lat: location.coords.latitude, lon: location.coords.longitude },
          timestamp: Date.now() / 1000,
          accel_magnitude: features.accel_magnitude,
          accel_variance: features.accel_variance,
          gyro_magnitude: features.gyro_magnitude,
          speed_mps: location?.coords?.speed ?? undefined,
          impact_detected: features.impact_detected,
          baseline_accel_magnitude: features.baseline_accel_magnitude,
        });
        setErr(null);
        setLastResult(res);
        if (res.response_level && res.response_level !== "normal") {
          setSafetyState(res.response_level);
          navigation.navigate("Deviation", { check: res });
        }
      } catch (e) {
        setErr(e.isTimeout ? "That check took a bit long — we'll try again shortly." : e.message);
      }
    }, 4000);
  }

  function stop({ completedNaturally = false } = {}) {
    setActive(false);
    intervalRef.current && clearInterval(intervalRef.current);
    countdownRef.current && clearInterval(countdownRef.current);
    // Only navigate to the trip-close screen when the full 5-minute window
    // genuinely finished, not when the user hits "Stop monitoring" early
    // (they might want to look at the last result before moving on).
    if (completedNaturally) navigation.navigate("TripComplete");
  }

  return (
    <View style={s.screen}>
      <View style={{ flexDirection: "row", alignItems: "center", marginBottom: 4 }}>
        <AvatarBadge size={44} />
        <View style={{ marginLeft: 12, flex: 1 }}>
          <Text style={s.title}>WalkGuard</Text>
          <Text style={[s.subtitle, { marginBottom: 0 }]}>I'm staying with you for the next 5 minutes.</Text>
        </View>
      </View>
      <TripBar navigation={navigation} currentScreen="WalkGuard" />
      <Text style={s.subtitle}>5-minute post-ride monitoring using your phone's real accelerometer and gyroscope.</Text>

      {available === false && (
        <Text style={s.errorText}>Motion sensors are not available on this device/simulator.</Text>
      )}

      {!consented ? (
        <View style={s.card}>
          <Text style={{ color: colors.text, fontWeight: "700" }}>Before we start</Text>
          <Text style={[s.muted, { marginTop: 6 }]}>
            WalkGuard will read your phone's real accelerometer, gyroscope, and GPS for the next 5
            minutes to watch for a sudden movement anomaly (e.g. a fall or sudden stop). Only coarse
            motion features are sent to the server — never a raw sensor recording. If a concerning
            pattern is detected, you decide whether to check in as safe or ask for help; nothing is
            shared automatically without your action.
          </Text>
          <TouchableOpacity style={[s.button, { marginTop: 14 }]} onPress={() => setConsented(true)}>
            <Text style={s.buttonText}>I consent — start monitoring my motion</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <View style={s.card}>
            <Text style={{ color: colors.text, fontWeight: "700" }}>Live sensor readout</Text>
            <Text style={s.muted}>accel magnitude: {features.accel_magnitude.toFixed(2)} m/s^2</Text>
            <Text style={s.muted}>accel variance: {features.accel_variance.toFixed(2)}</Text>
            <Text style={s.muted}>gyro magnitude: {features.gyro_magnitude.toFixed(2)} rad/s</Text>
            <Text style={s.muted}>impact detected: {String(features.impact_detected)}</Text>
          </View>

          {active ? (
            <>
              <View style={s.card}>
                <Text style={{ color: colors.accent, fontWeight: "700" }}>Monitoring... {remaining}s remaining</Text>
              </View>
              <TouchableOpacity style={s.buttonSecondary} onPress={() => stop()}>
                <Text style={s.buttonSecondaryText}>I'm home — stop monitoring</Text>
              </TouchableOpacity>
            </>
          ) : (
            <TouchableOpacity style={s.button} onPress={start}>
              <Text style={s.buttonText}>Start 5-min WalkGuard</Text>
            </TouchableOpacity>
          )}

          {err && <Text style={s.errorText}>{err}</Text>}

          {lastResult && (
            <View style={s.card}>
              <View style={s.row}>
                <Text style={{ color: colors.text, fontWeight: "700" }}>
                  {lastResult.anomaly_detected ? "Something changed" : "All calm"}
                </Text>
                <View style={s.badge(lastResult.response_level === "normal" ? colors.mint : colors.danger)}>
                  <Text style={s.badgeText}>
                    {lastResult.response_level === "normal" ? "Normal" : "Check needed"}
                  </Text>
                </View>
              </View>
              <Text style={s.muted}>{lastResult.reason}</Text>
            </View>
          )}

          {hasStarted && !active && (
            <TouchableOpacity style={[s.button, { marginTop: 8 }]} onPress={() => navigation.navigate("TripComplete")}>
              <Text style={s.buttonText}>Finish trip</Text>
            </TouchableOpacity>
          )}
        </>
      )}
    </View>
  );
}
