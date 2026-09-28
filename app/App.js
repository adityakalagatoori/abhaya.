import React, { useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import { View, ActivityIndicator } from "react-native";

import { JourneyProvider } from "./src/context/JourneyContext";
import { AvatarProvider } from "./src/context/AvatarContext";
import { colors } from "./src/theme";
import AvatarBadge from "./src/components/AvatarBadge";
import ClayIconButton from "./src/components/ClayIconButton";

import DestinationScreen from "./src/screens/DestinationScreen";
import RouteComparisonScreen from "./src/screens/RouteComparisonScreen";
import InfrastructureScreen from "./src/screens/InfrastructureScreen";
import SafeDropScreen from "./src/screens/SafeDropScreen";
import LiveRideScreen from "./src/screens/LiveRideScreen";
import DeviationScreen from "./src/screens/DeviationScreen";
import WalkGuardScreen from "./src/screens/WalkGuardScreen";
import SafeHavenScreen from "./src/screens/SafeHavenScreen";
import SafetyInsightScreen from "./src/screens/SafetyInsightScreen";
import SettingsScreen from "./src/screens/SettingsScreen";
import AvatarCustomizeScreen from "./src/screens/AvatarCustomizeScreen";
import TripCompleteScreen from "./src/screens/TripCompleteScreen";
import OnboardingScreen, { hasSeenOnboarding } from "./src/screens/OnboardingScreen";
import CompanionScreen from "./src/screens/CompanionScreen";
import BusSafetyScreen from "./src/screens/BusSafetyScreen";

const Stack = createNativeStackNavigator();

const screenOptions = ({ navigation }) => ({
  headerStyle: { backgroundColor: colors.bg },
  headerShadowVisible: false,
  headerTintColor: colors.text,
  headerTitleStyle: { fontWeight: "800" },
  headerRight: () => (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
      <ClayIconButton
        name="settings-outline"
        diameter={38}
        onPress={() => navigation.navigate("Settings")}
      />
      <AvatarBadge size={32} onPress={() => navigation.navigate("AvatarCustomize")} />
    </View>
  ),
});

export default function App() {
  // Real AsyncStorage check on launch, so onboarding shows exactly once
  // (plan item #5) instead of dropping first-time users straight into
  // "Where are you headed?" with no context.
  const [initialRoute, setInitialRoute] = useState(null);

  useEffect(() => {
    hasSeenOnboarding().then((seen) => setInitialRoute(seen ? "Destination" : "Onboarding"));
  }, []);

  if (!initialRoute) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg }}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <AvatarProvider>
      <JourneyProvider>
        <StatusBar style="dark" />
        <NavigationContainer>
          <Stack.Navigator screenOptions={screenOptions} initialRouteName={initialRoute}>
            <Stack.Screen name="Onboarding" component={OnboardingScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Destination" component={DestinationScreen} options={{ title: "ABHAYA" }} />
            <Stack.Screen name="RouteComparison" component={RouteComparisonScreen} options={{ title: "Route" }} />
            <Stack.Screen name="Infrastructure" component={InfrastructureScreen} options={{ title: "Infrastructure" }} />
            <Stack.Screen name="SafeDrop" component={SafeDropScreen} options={{ title: "SafeDrop" }} />
            <Stack.Screen name="LiveRide" component={LiveRideScreen} options={{ title: "Live ride" }} />
            <Stack.Screen name="Deviation" component={DeviationScreen} options={{ title: "Check-in" }} />
            <Stack.Screen name="WalkGuard" component={WalkGuardScreen} options={{ title: "WalkGuard" }} />
            <Stack.Screen name="TripComplete" component={TripCompleteScreen} options={{ title: "Trip complete", headerBackVisible: false }} />
            <Stack.Screen name="SafeHaven" component={SafeHavenScreen} options={{ title: "Safe havens" }} />
            <Stack.Screen name="SafetyInsight" component={SafetyInsightScreen} options={{ title: "Insight" }} />
            <Stack.Screen name="Companion" component={CompanionScreen} options={{ title: "Companion" }} />
            <Stack.Screen name="BusSafety" component={BusSafetyScreen} options={{ title: "Bus safety" }} />
            <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Backend settings" }} />
            <Stack.Screen name="AvatarCustomize" component={AvatarCustomizeScreen} options={{ title: "Your avatar" }} />
          </Stack.Navigator>
        </NavigationContainer>
      </JourneyProvider>
    </AvatarProvider>
  );
}
