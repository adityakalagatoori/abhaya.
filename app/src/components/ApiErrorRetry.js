import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { s, colors } from "../theme";

// Shared "something went wrong" card with a Retry button, used everywhere an
// API call can fail or time out, so no screen is left with a dead spinner
// and no way forward (see plan item #4).
export default function ApiErrorRetry({ error, onRetry }) {
  if (!error) return null;
  const message = typeof error === "string" ? error : error.message;
  const isTimeout = error?.isTimeout;

  return (
    <View style={s.card}>
      <Text style={{ color: colors.text, fontWeight: "700" }}>
        {isTimeout ? "That took too long" : "Something went wrong"}
      </Text>
      <Text style={[s.muted, { marginTop: 4 }]}>{message}</Text>
      {onRetry && (
        <TouchableOpacity style={[s.buttonSecondary, { marginTop: 10 }]} onPress={onRetry}>
          <Text style={s.buttonSecondaryText}>Try again</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
