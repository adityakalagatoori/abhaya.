import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function ClayBadge({ label, bg = "#8C6FF2", color = "#FFFFFF", style }) {
  return (
    <View style={[styles.badge, { backgroundColor: bg }, style]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.7)",
    shadowColor: "#4B3B7A",
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 3,
  },
  text: { fontWeight: "800", fontSize: 12, letterSpacing: 0.3 },
});
