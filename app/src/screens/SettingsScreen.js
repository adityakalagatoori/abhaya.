import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, Alert } from "react-native";
import { s, colors } from "../theme";
import { API_BASE_URL, setApiBaseUrl, getHealth } from "../api/client";
import AvatarBadge from "../components/AvatarBadge";

// Lets a real device tester point the app at the backend's LAN IP without
// rebuilding, since "localhost" on a phone means the phone itself.
export default function SettingsScreen({ navigation }) {
  const [url, setUrl] = useState(API_BASE_URL);
  const [status, setStatus] = useState(null);

  async function save() {
    setApiBaseUrl(url);
    try {
      const health = await getHealth();
      setStatus(`Connected. ${JSON.stringify(health)}`);
    } catch (e) {
      setStatus(`Could not reach backend: ${e.message}`);
    }
  }

  return (
    <View style={s.screen}>
      <View style={[s.card, { flexDirection: "row", alignItems: "center", justifyContent: "space-between" }]}>
        <View>
          <Text style={{ color: colors.text, fontWeight: "800", fontSize: 15 }}>Your avatar</Text>
          <Text style={s.muted}>Tap to customize your companion</Text>
        </View>
        <AvatarBadge size={44} onPress={() => navigation.navigate("AvatarCustomize")} />
      </View>

      {/* Dev-only: a shipped app should point at a fixed production backend,
          never expose a raw API-URL field to end users. */}
      {__DEV__ ? (
        <>
          <Text style={s.title}>Backend settings</Text>
          <Text style={s.subtitle}>
            On a real phone via Expo Go, "localhost" refers to the phone, not your computer.
            Use your computer's LAN IP, e.g. http://192.168.1.23:8000.
          </Text>
          <Text style={s.label}>API BASE URL</Text>
          <TextInput style={s.input} value={url} onChangeText={setUrl} autoCapitalize="none" />
          <TouchableOpacity style={s.button} onPress={save}>
            <Text style={s.buttonText}>Save & test connection</Text>
          </TouchableOpacity>
          {status && <Text style={[s.muted, { marginTop: 12 }]}>{status}</Text>}
        </>
      ) : (
        <>
          <Text style={s.title}>Settings</Text>
          <Text style={s.subtitle}>ABHAYA — your safety companion.</Text>
        </>
      )}
    </View>
  );
}
