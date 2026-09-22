import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import AvatarBadge from "../components/AvatarBadge";

// Real trip closure screen, shown when WalkGuard's monitoring window ends
// (naturally or by the user stopping it). Previously the journey just
// silently faded out with no closing moment -- see plan item #6.
export default function TripCompleteScreen({ navigation }) {
  const { destination, setOrigin, setDestination, setRouteResult, setJourneyId, setSafeDropResult, setSafetyState } =
    useJourney();

  function startNewTrip() {
    setOrigin(null);
    setDestination(null);
    setRouteResult(null);
    setJourneyId(null);
    setSafeDropResult(null);
    setSafetyState("normal");
    navigation.reset({ index: 0, routes: [{ name: "Destination" }] });
  }

  return (
    <View style={[s.screen, { justifyContent: "center", alignItems: "center" }]}>
      <AvatarBadge size={88} />
      <Text style={[s.title, { textAlign: "center", marginTop: 16 }]}>You're safely there</Text>
      <Text style={[s.subtitle, { textAlign: "center" }]}>
        {destination?.label ? `Trip to ${destination.label} complete.` : "Trip complete."} ABHAYA watched over
        your route, your ride, and your final walk.
      </Text>

      <View style={[s.card, { width: "100%", marginTop: 8 }]}>
        <Text style={{ color: colors.text, fontWeight: "700" }}>What ABHAYA did for this trip</Text>
        <Text style={[s.muted, { marginTop: 6 }]}>• Picked a safety-aware route, not just the fastest one</Text>
        <Text style={s.muted}>• Checked your ride against the expected route the whole way</Text>
        <Text style={s.muted}>• Watched your final walk for the last few minutes</Text>
      </View>

      <TouchableOpacity style={[s.button, { width: "100%", marginTop: 20 }]} onPress={startNewTrip}>
        <Text style={s.buttonText}>Start a new trip</Text>
      </TouchableOpacity>
    </View>
  );
}
