import React, { useState } from "react";
import { View, Text, TouchableOpacity } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { s, colors } from "../theme";

const ONBOARDING_KEY = "abhaya.onboardingComplete.v1";

const CARDS = [
  {
    title: "Meet ABHAYA",
    body: "A safety companion that plans your route, watches your ride, and stays with you on the final walk home.",
  },
  {
    title: "Not just the fastest route",
    body: "ABHAYA balances safety and time using real infrastructure, crime, and activity evidence — and explains why.",
  },
  {
    title: "With you the whole way",
    body: "SafeDrop finds a safer stopping point. RouteGuard watches your ride. WalkGuard stays with you after you're dropped off.",
  },
  {
    title: "One thing before we start",
    body: "We'll ask for location access to plan routes, and (later) motion sensor access for WalkGuard. You're always asked first, and you're always in control of what gets shared.",
  },
];

export async function hasSeenOnboarding() {
  try {
    return (await AsyncStorage.getItem(ONBOARDING_KEY)) === "true";
  } catch {
    return true; // fail open -- never block app usage over storage issues
  }
}

export default function OnboardingScreen({ navigation }) {
  const [index, setIndex] = useState(0);
  const card = CARDS[index];
  const isLast = index === CARDS.length - 1;

  async function finish() {
    try {
      await AsyncStorage.setItem(ONBOARDING_KEY, "true");
    } catch {
      // Non-fatal -- worst case onboarding shows again next launch.
    }
    navigation.replace("Destination");
  }

  return (
    <View style={[s.screen, { justifyContent: "center" }]}>
      <View style={s.card}>
        <Text style={s.title}>{card.title}</Text>
        <Text style={s.subtitle}>{card.body}</Text>
      </View>

      <View style={{ flexDirection: "row", justifyContent: "center", marginVertical: 16, gap: 8 }}>
        {CARDS.map((_, i) => (
          <View
            key={i}
            style={{
              width: 8, height: 8, borderRadius: 4,
              backgroundColor: i === index ? colors.accent : colors.border,
            }}
          />
        ))}
      </View>

      <TouchableOpacity style={s.button} onPress={() => (isLast ? finish() : setIndex((i) => i + 1))}>
        <Text style={s.buttonText}>{isLast ? "Get started" : "Next"}</Text>
      </TouchableOpacity>
      {!isLast && (
        <TouchableOpacity style={s.buttonSecondary} onPress={finish}>
          <Text style={s.buttonSecondaryText}>Skip</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
