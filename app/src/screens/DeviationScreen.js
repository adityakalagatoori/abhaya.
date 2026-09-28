import React, { useState } from "react";
import { View, Text, TouchableOpacity, Alert, ScrollView } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import AvatarBadge from "../components/AvatarBadge";
import { formatDistance } from "../utils/risk";

// Shown when POST /routeguard/check returns response_level "level1" or
// "level2". Level1: discreet, low-friction check-in. Level2: escalated,
// assumes urgency, offers direct contact / emergency options.
export default function DeviationScreen({ route, navigation }) {
  const check = route?.params?.check;
  const { setSafetyState } = useJourney();
  const [checkedIn, setCheckedIn] = useState(false);

  const level = check?.response_level || "level1_subtle_checkin";
  const isLevel2 = level === "level2_critical_escalation";

  function confirmSafe() {
    setCheckedIn(true);
    setSafetyState("normal");
  }

  function escalate() {
    Alert.alert(
      "Emergency contacts notified",
      "In production this calls the emergency-contact / authorities flow. This demo only shows the UI state."
    );
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={{ alignItems: "center", marginBottom: 8 }}>
        <AvatarBadge size={64} />
      </View>
      <Text style={[s.title, { textAlign: "center" }]}>{isLevel2 ? "Are you okay?" : "Quick check-in"}</Text>
      <Text style={s.subtitle}>
        {isLevel2
          ? "Your route has deviated significantly and risk has increased. Please confirm you're safe."
          : "We noticed a small deviation from your expected route. Just checking in."}
      </Text>

      {check && (
        <View style={s.card}>
          {check.deviation_distance_m != null && (
            <Text style={s.muted}>You've moved about {formatDistance(check.deviation_distance_m)} off the expected path.</Text>
          )}
          <Text style={[s.muted, { marginTop: 6 }]}>{check.reason}</Text>
        </View>
      )}

      {checkedIn ? (
        <View style={s.card}>
          <Text style={{ color: colors.accent, fontWeight: "700" }}>Thanks, marked safe.</Text>
        </View>
      ) : (
        <>
          <TouchableOpacity style={s.button} onPress={confirmSafe}>
            <Text style={s.buttonText}>I'm safe</Text>
          </TouchableOpacity>
          {isLevel2 && (
            <TouchableOpacity style={[s.button, { backgroundColor: colors.danger }]} onPress={escalate}>
              <Text style={s.buttonText}>I need help</Text>
            </TouchableOpacity>
          )}
        </>
      )}

      <TouchableOpacity style={s.buttonSecondary} onPress={() => navigation.navigate("LiveRide")}>
        <Text style={s.buttonSecondaryText}>Back to ride</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
