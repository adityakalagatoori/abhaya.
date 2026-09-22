import React, { useEffect, useState } from "react";
import { View, Text, FlatList, ActivityIndicator } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { getInfrastructure } from "../api/client";
import ApiErrorRetry from "../components/ApiErrorRetry";

const FACTOR_INFO = {
  streetlight_working: { label: "Good lighting", icon: "💡" },
  streetlight_broken: { label: "Poor lighting", icon: "⚠️" },
  visibility_barrier: { label: "Blocked visibility", icon: "🚧" },
  open_establishment: { label: "Open business nearby", icon: "🏪" },
};

export default function InfrastructureScreen() {
  const { destination, origin } = useJourney();
  const point = destination || origin;
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  function load() {
    if (!point) return;
    setErr(null);
    getInfrastructure({ lat: point.lat, lon: point.lon, radius: 300 })
      .then(setData)
      .catch(setErr);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [point]);

  if (!point) {
    return (
      <View style={s.screen}>
        <Text style={s.title}>Infrastructure</Text>
        <Text style={s.subtitle}>Pick a destination first.</Text>
      </View>
    );
  }

  const hasDetections = data?.detections?.length > 0;

  return (
    <View style={s.screen}>
      <Text style={s.title}>What we can see nearby</Text>
      <Text style={s.subtitle}>Real streetlight, visibility, and nearby-business evidence, spotted from street photos.</Text>

      <ApiErrorRetry error={err} onRetry={load} />
      {!data && !err && <ActivityIndicator color={colors.accent} />}

      {data && (
        <>
          {!hasDetections ? (
            <View style={s.card}>
              <Text style={{ color: colors.text, fontWeight: "700" }}>Nothing spotted here yet</Text>
              <Text style={[s.muted, { marginTop: 4 }]}>
                We don't have street-level photos covering this exact spot yet. This doesn't mean it's
                unsafe — we just don't have evidence for it.
              </Text>
            </View>
          ) : (
            <FlatList
              data={data.detections}
              keyExtractor={(item) => item.evidence_id}
              renderItem={({ item }) => {
                const info = FACTOR_INFO[item.factor] || { label: item.factor.replace(/_/g, " "), icon: "📍" };
                const confidencePct = Math.round((item.confidence || 0) * 100);
                return (
                  <View style={s.card}>
                    <View style={s.row}>
                      <Text style={{ color: colors.text, fontWeight: "700" }}>{info.icon} {info.label}</Text>
                      <Text style={s.muted}>{confidencePct}% sure</Text>
                    </View>
                  </View>
                );
              }}
            />
          )}
        </>
      )}
    </View>
  );
}
