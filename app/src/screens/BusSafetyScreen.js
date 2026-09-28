import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, TextInput, ScrollView } from "react-native";
import { s, colors } from "../theme";
import { getBusSafetyStatus, postTransitGuardCheck } from "../api/client";
import ApiErrorRetry from "../components/ApiErrorRetry";
import TripBar from "../components/TripBar";

// ABHAYA TransitGuard (spec 31.3-31.9): shows available bus compliance
// evidence (tracking, panic button, visibility, lighting) before boarding,
// tied to the real Delhi bus-safety directive (see rag/corpus/008_...).
// Per-vehicle telemetry is honestly labeled demo data (see
// backend/app/demo_bus_data.py) since no public bus-operator API exists --
// this screen surfaces the backend's own data_source_status disclosure
// rather than hiding it.
const FACTOR_LABELS = {
  tracking_active: { label: "Vehicle location tracking", icon: "📡" },
  panic_button_functional: { label: "Panic button", icon: "🔴" },
  visibility_compliant: { label: "No obstructive curtains/film", icon: "👁️" },
  lighting_adequate: { label: "Internal lighting", icon: "💡" },
  authorised_stops: { label: "Authorised stops only", icon: "🚏" },
};

export default function BusSafetyScreen({ navigation }) {
  const [vehicleId, setVehicleId] = useState("DL1PC1234");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [checkResult, setCheckResult] = useState(null);

  async function checkBus() {
    if (!vehicleId.trim()) return;
    setLoading(true);
    setErr(null);
    setStatus(null);
    try {
      const res = await getBusSafetyStatus({ vehicle_id: vehicleId.trim() });
      setStatus(res);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  async function simulateCheck() {
    try {
      const res = await postTransitGuardCheck({
        vehicle_id: vehicleId.trim(),
        expected_route_segment_ids: [],
        current: { lat: 21.1854, lon: 72.8107 },
      });
      setCheckResult(res);
    } catch (e) {
      setErr(e);
    }
  }

  const evidenceEntries = status
    ? ["tracking", "panic_button", "visibility", "lighting", "authorised_stops"]
        .map((key) => status[key])
        .filter(Boolean)
    : [];

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={s.title}>Bus safety status</Text>
      <TripBar navigation={navigation} currentScreen="BusSafety" />
      <Text style={s.subtitle}>
        Check available safety evidence for your bus before boarding — real compliance categories from
        the actual Delhi bus-safety directive, applied here to demo vehicle records.
      </Text>

      <View style={s.card}>
        <Text style={s.label}>BUS / VEHICLE ID</Text>
        <TextInput style={s.input} value={vehicleId} onChangeText={setVehicleId} autoCapitalize="characters" />
        <TouchableOpacity style={[s.button, { marginTop: 10 }]} onPress={checkBus} disabled={loading}>
          {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={s.buttonText}>Check this bus</Text>}
        </TouchableOpacity>
      </View>

      <ApiErrorRetry error={err} onRetry={checkBus} />

      {status && !status.found && (
        <View style={s.card}>
          <Text style={{ color: colors.text, fontWeight: "700" }}>No record for this vehicle</Text>
          <Text style={[s.muted, { marginTop: 4 }]}>Try DL1PC1234, UP16XX9988, DL1PD5566, or HR26AB4321 (demo fleet).</Text>
        </View>
      )}

      {status && status.found && (
        <>
          <View style={s.card}>
            <View style={s.row}>
              <Text style={{ color: colors.text, fontWeight: "700" }}>{status.operator || "Unknown operator"}</Text>
              <View style={s.badge(status.overall_compliance_score >= 0.75 ? colors.mint : status.overall_compliance_score >= 0.4 ? colors.amber : colors.danger)}>
                <Text style={s.badgeText}>{Math.round(status.overall_compliance_score * 100)}% compliant</Text>
              </View>
            </View>
            {status.route_name && <Text style={s.muted}>{status.route_name}</Text>}
            <Text style={[s.muted, { marginTop: 6, fontStyle: "italic" }]}>{status.data_source_status}</Text>
          </View>

          {evidenceEntries.map((ev) => {
            const info = FACTOR_LABELS[ev.factor] || { label: ev.factor, icon: "📍" };
            const ok = ev.value >= 0.5;
            return (
              <View key={ev.factor} style={s.card}>
                <View style={s.row}>
                  <Text style={{ color: colors.text, fontWeight: "600" }}>{info.icon} {info.label}</Text>
                  <View style={s.badge(ok ? colors.mint : colors.danger)}>
                    <Text style={s.badgeText}>{ev.raw_value}</Text>
                  </View>
                </View>
              </View>
            );
          })}

          <TouchableOpacity style={[s.buttonSecondary, { marginTop: 4 }]} onPress={simulateCheck}>
            <Text style={s.buttonSecondaryText}>Check live route (TransitGuard)</Text>
          </TouchableOpacity>

          {checkResult && (
            <View style={s.card}>
              <View style={s.row}>
                <Text style={{ color: colors.text, fontWeight: "700" }}>Live route check</Text>
                <View style={s.badge(checkResult.response_level === "normal" ? colors.mint : colors.danger)}>
                  <Text style={s.badgeText}>{checkResult.response_level === "normal" ? "On track" : "Check needed"}</Text>
                </View>
              </View>
              <Text style={s.muted}>{checkResult.reason}</Text>
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
}
