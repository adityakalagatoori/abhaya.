import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, TextInput, ScrollView } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { postSafetyInsight } from "../api/client";
import ApiErrorRetry from "../components/ApiErrorRetry";

export default function SafetyInsightScreen() {
  const { routeResult } = useJourney();
  const [question, setQuestion] = useState("Why was this route chosen over the fastest one?");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  async function ask() {
    setLoading(true);
    setErr(null);
    try {
      const route_context = routeResult
        ? {
            segments: routeResult.segments.map((s) => ({
              segment_id: s.segment_id,
              risk_score: s.risk_score,
            })),
            total_risk: routeResult.total_risk,
            high_risk_factors: routeResult.segments
              .filter((s) => s.risk_score > 0.5)
              .map((s) => s.segment_id),
          }
        : { segments: [], total_risk: 0, high_risk_factors: [] };

      const res = await postSafetyInsight({ route_context, retrieved_passages: [], question });
      setResult(res);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={s.title}>Ask ABHAYA</Text>
      <Text style={s.subtitle}>Get a plain-language explanation of why this route was chosen.</Text>

      <TextInput style={s.input} value={question} onChangeText={setQuestion} multiline />

      <TouchableOpacity style={s.button} onPress={ask} disabled={loading}>
        {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={s.buttonText}>Ask</Text>}
      </TouchableOpacity>

      <ApiErrorRetry error={err} onRetry={ask} />

      {result && (
        <View style={s.card}>
          <Text style={{ color: colors.text }}>{result.explanation}</Text>
          {!result.grounded && (
            <Text style={[s.muted, { marginTop: 8 }]}>
              We don't have specific local reports for this exact spot, so take this as a general
              estimate rather than a confirmed fact.
            </Text>
          )}
        </View>
      )}
    </ScrollView>
  );
}
