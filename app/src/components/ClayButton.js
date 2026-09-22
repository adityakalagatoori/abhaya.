import React from "react";
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet, View } from "react-native";
import { colors } from "../theme";

const VARIANTS = {
  primary: { bg: colors.accent, dark: colors.accentDark, text: "#FFFFFF" },
  coral: { bg: colors.coral, dark: "#E06A4A", text: "#FFFFFF" },
  mint: { bg: colors.mint, dark: "#1FAE71", text: "#06281c" },
  danger: { bg: colors.danger, dark: "#D8385A", text: "#FFFFFF" },
  soft: { bg: colors.cardAlt, dark: colors.shadowDark, text: colors.text },
};

export default function ClayButton({ title, onPress, variant = "primary", loading, disabled, style, textStyle }) {
  const v = VARIANTS[variant] || VARIANTS.primary;
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.base,
        { backgroundColor: v.bg, shadowColor: v.dark, opacity: disabled ? 0.55 : 1 },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.text} />
      ) : (
        <Text style={[styles.text, { color: v.text }, textStyle]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 26,
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.55)",
    shadowOffset: { width: 6, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 6,
  },
  text: { fontWeight: "800", fontSize: 15.5, letterSpacing: 0.3 },
});
