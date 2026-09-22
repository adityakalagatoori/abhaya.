import React from "react";
import { View, Text, ScrollView, TouchableOpacity } from "react-native";
import LeafletMap from "../components/LeafletMap";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { riskLevel, averageRouteRisk, formatDistance, formatMinutes } from "../utils/risk";
import TripBar from "../components/TripBar";

// Note on backend contract: /route returns the full ABHAYA (safety-weighted)
// route geometry (segments[].from_latlon/to_latlon) plus only SCALAR summary
// stats for the alternative fastest route (alternative_fastest_time_s,
// alternative_fastest_risk) -- it does not return the fastest route's own
// geometry. So this screen draws the real ABHAYA route on the map and shows
// the fastest-route numbers as a comparison card rather than a second line.
export default function RouteComparisonScreen({ navigation }) {
  const { routeResult, origin, destination } = useJourney();

  if (!routeResult) {
    return (
      <View style={s.screen}>
        <Text style={s.title}>No route yet</Text>
        <Text style={s.subtitle}>Go back and search a destination first.</Text>
      </View>
    );
  }

  const coords = routeResult.segments.map((seg) => ({
    lat: seg.from_latlon.lat,
    lon: seg.from_latlon.lon,
  }));
  if (routeResult.segments.length) {
    const last = routeResult.segments[routeResult.segments.length - 1];
    coords.push({ lat: last.to_latlon.lat, lon: last.to_latlon.lon });
  }

  const mapCenter = {
    lat: origin?.lat ?? coords[0]?.lat ?? 21.1702,
    lon: origin?.lon ?? coords[0]?.lon ?? 72.8311,
  };
  const mapMarkers = [
    origin && { lat: origin.lat, lon: origin.lon, color: "#3DDC97", label: "Origin" },
    destination && { lat: destination.lat, lon: destination.lon, color: "#FF5C7A", label: "Destination" },
  ].filter(Boolean);

  const chosenLevel = riskLevel(averageRouteRisk(routeResult));
  const fastestLevel = routeResult.alternative_fastest_risk != null && routeResult.segments.length
    ? riskLevel(routeResult.alternative_fastest_risk / routeResult.segments.length)
    : null;

  const extraMinutes = routeResult.alternative_fastest_time_s
    ? Math.max(0, Math.round((routeResult.total_time_s - routeResult.alternative_fastest_time_s) / 60))
    : 0;

  return (
    <View style={s.screen}>
      <Text style={s.title}>Your route</Text>
      <TripBar navigation={navigation} currentScreen="RouteComparison" />
      <View style={{ marginBottom: 12 }}>
        <LeafletMap center={mapCenter} zoom={14} markers={mapMarkers} polyline={coords} height={260} />
      </View>

      <ScrollView>
        <View style={s.card}>
          <View style={s.row}>
            <Text style={{ color: colors.text, fontWeight: "700", fontSize: 16 }}>ABHAYA's pick</Text>
            <View style={s.badge(chosenLevel.color)}>
              <Text style={s.badgeText}>{chosenLevel.label}</Text>
            </View>
          </View>
          <Text style={s.muted}>
            {formatMinutes(routeResult.total_time_s)} · {formatDistance(routeResult.total_distance_m)}
          </Text>
        </View>

        {fastestLevel && (
          <View style={s.card}>
            <View style={s.row}>
              <Text style={{ color: colors.text, fontWeight: "700" }}>The quickest route</Text>
              <View style={s.badge(fastestLevel.color)}>
                <Text style={s.badgeText}>{fastestLevel.label}</Text>
              </View>
            </View>
            <Text style={s.muted}>
              {extraMinutes > 0
                ? `About ${extraMinutes} min faster, but rated riskier than the route ABHAYA chose.`
                : "Similar time to ABHAYA's pick."}
            </Text>
          </View>
        )}

        <View style={s.card}>
          <Text style={{ color: colors.text, fontWeight: "700", marginBottom: 6 }}>Why this route</Text>
          <Text style={s.muted}>{routeResult.explanation}</Text>
        </View>

        <Text style={[s.label, { marginTop: 4 }]}>CONTINUE YOUR TRIP</Text>
        <TouchableOpacity style={s.button} onPress={() => navigation.navigate("SafeHaven")}>
          <Text style={s.buttonText}>Find a safe place to wait</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("SafeDrop")}>
          <Text style={s.buttonSecondaryText}>Find a safer drop-off spot</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("LiveRide")}>
          <Text style={s.buttonSecondaryText}>Start my ride</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("WalkGuard")}>
          <Text style={s.buttonSecondaryText}>Set up WalkGuard for later</Text>
        </TouchableOpacity>

        <Text style={[s.label, { marginTop: 14 }]}>LEARN MORE</Text>
        <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("Infrastructure")}>
          <Text style={s.buttonSecondaryText}>Why do we think this is safe?</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("SafetyInsight")}>
          <Text style={s.buttonSecondaryText}>Ask about this route</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}
