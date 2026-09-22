import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { colors } from "../theme";
import { JOURNEY_STEPS } from "../journeySteps";
import { useJourney } from "../context/JourneyContext";

// Persistent "where am I in this trip" bar, shown across every in-journey
// screen -- plan item #3. Tapping a dot jumps directly to that step (the
// app still allows non-linear access, since RouteGuard/WalkGuard genuinely
// depend on user timing, not a hard gate), but the dots make the overall
// journey order visible at a glance instead of an unordered wall of buttons.
export default function TripBar({ navigation, currentScreen }) {
  const { destination } = useJourney();
  if (!destination) return null;

  const currentIndex = JOURNEY_STEPS.findIndex((s) => s.screen === currentScreen);

  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={{ color: colors.textDim, fontSize: 12, fontWeight: "700", marginBottom: 8 }}>
        TRIP TO {(destination.label || "your destination").toUpperCase()}
      </Text>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        {JOURNEY_STEPS.map((step, i) => {
          const isCurrent = i === currentIndex;
          const isPast = currentIndex >= 0 && i < currentIndex;
          const color = isCurrent ? colors.accent : isPast ? colors.mint : colors.border;
          return (
            <React.Fragment key={step.key}>
              <TouchableOpacity
                onPress={() => navigation.navigate(step.screen)}
                style={{ alignItems: "center", width: 56 }}
              >
                <View
                  style={{
                    width: 14, height: 14, borderRadius: 7, backgroundColor: color,
                    borderWidth: isCurrent ? 2 : 0, borderColor: colors.accentDark,
                  }}
                />
                <Text
                  numberOfLines={1}
                  style={{ color: isCurrent ? colors.text : colors.textDim, fontSize: 10, marginTop: 4, fontWeight: isCurrent ? "700" : "500" }}
                >
                  {step.label}
                </Text>
              </TouchableOpacity>
              {i < JOURNEY_STEPS.length - 1 && (
                <View style={{ flex: 1, height: 2, backgroundColor: isPast ? colors.mint : colors.border, marginBottom: 14 }} />
              )}
            </React.Fragment>
          );
        })}
      </View>
    </View>
  );
}
