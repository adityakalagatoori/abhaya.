import React, { useState } from "react";
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { useDeviceLocation } from "../hooks/useDeviceLocation";
import { postRoute } from "../api/client";
import AvatarBadge from "../components/AvatarBadge";
import ApiErrorRetry from "../components/ApiErrorRetry";
import PlaceSearchInput from "../components/PlaceSearchInput";

const MODES = ["walk", "ride_hailing", "drive"];
// ABHAYA's real data (road network, crime, POIs) only covers Surat -- bias
// destination search results toward it so a normal user typing a place name
// finds real, routable results instead of somewhere with no coverage.
const SURAT_CENTER = { lat: 21.1702, lon: 72.8311 };

export default function DestinationScreen({ navigation }) {
  const { setOrigin, setDestination, mode, setMode, setRouteResult, setJourneyId } = useJourney();
  const { location, error: gpsError, permissionGranted, start: startLocation, awaitingStart } =
    useDeviceLocation({ requireManualStart: true });

  const [destPlace, setDestPlace] = useState(null); // {label, lat, lon}
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  // Dev-only manual origin override: ABHAYA's real data only covers Surat. A
  // tester whose real device GPS is elsewhere has no real road graph to
  // route from at their actual location, so this lets a tester search a
  // Surat-area origin instead -- never shown in a release build, since a
  // safety app should never look like it lets you fake your location.
  const [useManualOrigin, setUseManualOrigin] = useState(false);
  const [manualOriginPlace, setManualOriginPlace] = useState(null);

  const haveOrigin = useManualOrigin ? manualOriginPlace != null : location != null;

  async function handleFindRoute() {
    if (!destPlace) {
      setErr("Search for and select a destination first.");
      return;
    }
    if (!useManualOrigin && !location) {
      Alert.alert("Waiting for GPS", "Real device location has not been acquired yet. Grant location permission and try again.");
      return;
    }
    const origin = useManualOrigin
      ? { lat: manualOriginPlace.lat, lon: manualOriginPlace.lon }
      : { lat: location.coords.latitude, lon: location.coords.longitude };
    const destination = { lat: destPlace.lat, lon: destPlace.lon };

    setOrigin({ ...origin, label: useManualOrigin ? manualOriginPlace.label : "Current location" });
    setDestination({ ...destination, label: destPlace.label });
    setLoading(true);
    setErr(null);
    try {
      const res = await postRoute({ origin, destination, mode });
      setRouteResult(res);
      setJourneyId(res.journey_id);
      navigation.navigate("RouteComparison");
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={{ flexDirection: "row", alignItems: "center", marginBottom: 4 }}>
        <View style={{ flex: 1 }}>
          <Text style={s.title}>Where are you headed?</Text>
        </View>
        <AvatarBadge size={44} onPress={() => navigation.navigate("AvatarCustomize")} />
      </View>
      <Text style={s.subtitle}>ABHAYA plans the safest reasonable route, not just the fastest one.</Text>

      {awaitingStart && (
        <View style={s.card}>
          <Text style={{ color: colors.text, fontWeight: "700" }}>We need your location</Text>
          <Text style={[s.muted, { marginTop: 6 }]}>
            ABHAYA uses your real GPS position to plan routes and start from where you actually are.
            We only use it while you're actively using the app.
          </Text>
          <TouchableOpacity style={[s.button, { marginTop: 12 }]} onPress={startLocation}>
            <Text style={s.buttonText}>Enable location</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={s.card}>
        <View style={[s.row, { marginBottom: 6 }]}>
          <Text style={s.label}>YOUR STARTING POINT</Text>
          {/* Dev-only, see comment above. */}
          {__DEV__ && (
            <TouchableOpacity onPress={() => setUseManualOrigin((v) => !v)}>
              <Text style={{ color: colors.accent, fontWeight: "700", fontSize: 12 }}>
                {useManualOrigin ? "Use real GPS instead" : "Search a different origin (testing)"}
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {useManualOrigin && __DEV__ ? (
          <PlaceSearchInput
            placeholder="Search a Surat-area starting point..."
            biasLat={SURAT_CENTER.lat}
            biasLon={SURAT_CENTER.lon}
            value={manualOriginPlace?.label}
            onSelect={setManualOriginPlace}
          />
        ) : location ? (
          <Text style={{ color: colors.text }}>Your current location</Text>
        ) : (
          <View style={{ flexDirection: "row", alignItems: "center" }}>
            <ActivityIndicator color={colors.accent} />
            <Text style={{ color: colors.textDim, marginLeft: 8 }}>
              {permissionGranted === false ? "Location permission denied" : "Waiting for your location..."}
            </Text>
          </View>
        )}
        {!useManualOrigin && gpsError ? <Text style={s.errorText}>{gpsError}</Text> : null}
      </View>

      <View style={s.card}>
        <Text style={s.label}>DESTINATION</Text>
        <PlaceSearchInput
          placeholder="Search for a place, e.g. Athwa Gate, Surat"
          biasLat={SURAT_CENTER.lat}
          biasLon={SURAT_CENTER.lon}
          value={destPlace?.label}
          onSelect={setDestPlace}
        />

        <Text style={[s.label, { marginTop: 14 }]}>HOW ARE YOU TRAVELING?</Text>
        <View style={{ flexDirection: "row", gap: 8 }}>
          {MODES.map((m) => (
            <TouchableOpacity
              key={m}
              onPress={() => setMode(m)}
              style={[
                s.buttonSecondary,
                { flex: 1, marginTop: 0, backgroundColor: mode === m ? colors.accent : "transparent" },
              ]}
            >
              <Text style={mode === m ? s.buttonText : s.buttonSecondaryText}>{m.replace("_", " ")}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <ApiErrorRetry error={err} onRetry={handleFindRoute} />

      <TouchableOpacity style={s.button} onPress={handleFindRoute} disabled={loading || !haveOrigin || !destPlace}>
        {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={s.buttonText}>Find safe route</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}
