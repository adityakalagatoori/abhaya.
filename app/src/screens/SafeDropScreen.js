import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, FlatList } from "react-native";
import LeafletMap from "../components/LeafletMap";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { postSafeDrop } from "../api/client";
import { riskLevel, formatDistance } from "../utils/risk";
import ApiErrorRetry from "../components/ApiErrorRetry";
import TripBar from "../components/TripBar";

// Backend candidate labels are internal ids like "road_node:21.2444,72.8445"
// or "destination_pin" -- translate them into something a user can read.
function friendlyLabel(rawLabel, index) {
  if (!rawLabel) return `Nearby spot ${index + 1}`;
  if (rawLabel === "destination_pin") return "Your exact destination";
  if (rawLabel.startsWith("road_node:")) return `Nearby spot ${index + 1}`;
  return rawLabel;
}

export default function SafeDropScreen({ navigation }) {
  const { destination, safeDropResult, setSafeDropResult } = useJourney();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  async function fetchSafeDrop() {
    if (!destination) return;
    setLoading(true);
    setErr(null);
    try {
      const res = await postSafeDrop({ destination: { lat: destination.lat, lon: destination.lon } });
      setSafeDropResult(res);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  if (!destination) {
    return (
      <View style={s.screen}>
        <Text style={s.title}>SafeDrop</Text>
        <Text style={s.subtitle}>Pick a destination first.</Text>
      </View>
    );
  }

  const mapMarkers = [
    { lat: destination.lat, lon: destination.lon, color: "#FF5C7A", label: "Destination" },
    safeDropResult && {
      lat: safeDropResult.recommended.lat, lon: safeDropResult.recommended.lon,
      color: "#3DDC97", label: "Recommended drop point",
    },
  ].filter(Boolean);

  const recLevel = safeDropResult ? riskLevel(safeDropResult.recommended.risk_score) : null;
  const otherCandidates = safeDropResult
    ? safeDropResult.all_candidates.filter((c) => c.label !== safeDropResult.recommended.label)
    : [];

  return (
    <View style={s.screen}>
      <Text style={s.title}>Where should you actually get out?</Text>
      <TripBar navigation={navigation} currentScreen="SafeDrop" />
      <Text style={s.subtitle}>Your destination pin might not be the safest spot to stop. Let's check nearby.</Text>

      <View style={{ marginBottom: 12 }}>
        <LeafletMap center={{ lat: destination.lat, lon: destination.lon }} zoom={16} markers={mapMarkers} height={220} />
      </View>

      {!safeDropResult && (
        <TouchableOpacity style={s.button} onPress={fetchSafeDrop} disabled={loading}>
          {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={s.buttonText}>Check my drop-off spot</Text>}
        </TouchableOpacity>
      )}
      <ApiErrorRetry error={err} onRetry={fetchSafeDrop} />

      {safeDropResult && (
        <>
          <View style={s.card}>
            <View style={s.row}>
              <Text style={{ color: colors.text, fontWeight: "700", flex: 1 }}>
                {friendlyLabel(safeDropResult.recommended.label, 0)}
              </Text>
              <View style={s.badge(recLevel.color)}>
                <Text style={s.badgeText}>{recLevel.label}</Text>
              </View>
            </View>
            <Text style={s.muted}>
              {safeDropResult.recommended.walk_distance_m > 0
                ? `About ${formatDistance(safeDropResult.recommended.walk_distance_m)} extra walk from your destination`
                : "Right at your destination"}
            </Text>
            <Text style={[s.muted, { marginTop: 6 }]}>{safeDropResult.reason}</Text>
          </View>

          {otherCandidates.length > 0 && (
            <Text style={[s.label, { marginTop: 4 }]}>OTHER NEARBY OPTIONS</Text>
          )}
          <FlatList
            data={otherCandidates}
            keyExtractor={(_, i) => String(i)}
            scrollEnabled={false}
            renderItem={({ item, index }) => {
              const lvl = riskLevel(item.risk_score);
              return (
                <View style={s.card}>
                  <View style={s.row}>
                    <Text style={{ color: colors.text }}>{friendlyLabel(item.label, index + 1)}</Text>
                    <View style={s.badge(lvl.color)}>
                      <Text style={s.badgeText}>{lvl.label}</Text>
                    </View>
                  </View>
                  <Text style={s.muted}>{formatDistance(item.walk_distance_m)} walk</Text>
                </View>
              );
            }}
          />
          <TouchableOpacity style={[s.button, { marginTop: 12 }]} onPress={() => navigation.navigate("LiveRide")}>
            <Text style={s.buttonText}>Continue: start my ride</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}
