import React from "react";
import { View, StyleSheet } from "react-native";
import { colors } from "../theme";

// A "puffy clay" card: base View carries the dark bottom-right shadow +
// elevation, an absolutely-positioned overlay View carries a light
// top-left highlight shadow, faking the dual-shadow clay look that RN's
// single shadow model can't do on one node.
export default function ClayCard({ children, style, tint, radius = 28, ...rest }) {
  const bg = tint || colors.card;
  return (
    <View style={[styles.wrap, { borderRadius: radius }, style]} {...rest}>
      <View pointerEvents="none" style={[styles.highlight, { borderRadius: radius, backgroundColor: bg }]} />
      <View style={[styles.dark, { borderRadius: radius, backgroundColor: bg }]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginBottom: 14,
  },
  highlight: {
    position: "absolute",
    top: -3,
    left: -3,
    right: 3,
    bottom: 3,
    shadowColor: "#FFFFFF",
    shadowOffset: { width: -6, height: -6 },
    shadowOpacity: 0.9,
    shadowRadius: 10,
    elevation: 0,
  },
  dark: {
    padding: 16,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.7)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 7, height: 7 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 8,
  },
});
