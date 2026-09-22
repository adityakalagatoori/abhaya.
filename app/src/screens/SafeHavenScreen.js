import React, { useEffect, useState } from "react";
import { View, Text, FlatList, ActivityIndicator, TouchableOpacity } from "react-native";
import { s, colors } from "../theme";
import { useDeviceLocation } from "../hooks/useDeviceLocation";
import { getSafeHavens } from "../api/client";
import { formatDistance } from "../utils/risk";
import ApiErrorRetry from "../components/ApiErrorRetry";
import TripBar from "../components/TripBar";

export default function SafeHavenScreen({ navigation }) {
  const { location } = useDeviceLocation();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  function load() {
    if (!location) return;
    setErr(null);
    getSafeHavens({ lat: location.coords.latitude, lon: location.coords.longitude, radius: 500 })
      .then(setData)
      .catch(setErr);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [location]);

  return (
    <View style={s.screen}>
      <Text style={s.title}>Somewhere safe to wait</Text>
      <TripBar navigation={navigation} currentScreen="SafeHaven" />
      <Text style={s.subtitle}>Real open, verified places nearby where you can wait for your ride.</Text>

      {!location && <ActivityIndicator color={colors.accent} />}
      <ApiErrorRetry error={err} onRetry={load} />

      {data && (
        <FlatList
          style={{ marginTop: 10 }}
          data={data.candidates}
          keyExtractor={(item, i) => `${item.name}-${i}`}
          ListEmptyComponent={
            <View style={s.card}>
              <Text style={{ color: colors.text, fontWeight: "700" }}>Nothing nearby right now</Text>
              <Text style={[s.muted, { marginTop: 4 }]}>
                We couldn't find a verified open place within 500m. Try again closer to your pickup spot.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <View style={s.card}>
              <View style={s.row}>
                <Text style={{ color: colors.text, fontWeight: "700" }}>{item.name}</Text>
                <View style={s.badge(item.open_now ? colors.mint : colors.textDim)}>
                  <Text style={s.badgeText}>{item.open_now ? "Open now" : "May be closed"}</Text>
                </View>
              </View>
              <Text style={s.muted}>
                {item.category.replace(/_/g, " ")} · {formatDistance(item.distance_m)} away
                {item.verified ? " · Verified" : ""}
              </Text>
            </View>
          )}
        />
      )}

      <TouchableOpacity style={[s.button, { marginTop: 12 }]} onPress={() => navigation.navigate("SafeDrop")}>
        <Text style={s.buttonText}>Continue: check my drop-off spot</Text>
      </TouchableOpacity>
    </View>
  );
}
