import React, { useState } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, FlatList } from "react-native";
import { s, colors } from "../theme";
import { useJourney } from "../context/JourneyContext";
import { postCompanionsMatch, postCompanionsRequest } from "../api/client";
import ApiErrorRetry from "../components/ApiErrorRetry";
import TripBar from "../components/TripBar";

// Journey Companion (spec 31.1/31.2/31.8): matches the USER'S JOURNEY against
// other overlapping journeys, not people socially. Real matching algorithm
// (route overlap, time overlap, meeting-point practicality, verification)
// runs against honestly-labeled demo traveller records, since ABHAYA has no
// other real users yet -- see backend/app/companion_seed.py. Never shows a
// candidate's exact home/origin address.
export default function CompanionScreen({ navigation }) {
  const { origin, destination, mode, journeyId } = useJourney();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [requestedId, setRequestedId] = useState(null);
  const [requestStatus, setRequestStatus] = useState(null);

  async function findCompanions() {
    if (!origin || !destination) return;
    setLoading(true);
    setErr(null);
    try {
      const res = await postCompanionsMatch({
        origin: { lat: origin.lat, lon: origin.lon },
        destination: { lat: destination.lat, lon: destination.lon },
        mode,
      });
      setResult(res);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  async function requestCompanion(candidateId) {
    if (!journeyId) return;
    setRequestedId(candidateId);
    try {
      const res = await postCompanionsRequest({ journey_id: journeyId, candidate_id: candidateId });
      setRequestStatus(res.companion_status);
    } catch (e) {
      setErr(e);
    }
  }

  if (!origin || !destination) {
    return (
      <View style={s.screen}>
        <Text style={s.title}>Journey companion</Text>
        <Text style={s.subtitle}>Get a route first, then look for a fellow traveller on the same journey.</Text>
      </View>
    );
  }

  return (
    <View style={s.screen}>
      <Text style={s.title}>Travel with someone</Text>
      <TripBar navigation={navigation} currentScreen="Companion" />
      <Text style={s.subtitle}>
        We match your journey against other people already travelling the same route around the same
        time — never a general social search. Your exact starting point is never shared.
      </Text>

      {!result && (
        <TouchableOpacity style={s.button} onPress={findCompanions} disabled={loading}>
          {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={s.buttonText}>Find a fellow traveller</Text>}
        </TouchableOpacity>
      )}
      <ApiErrorRetry error={err} onRetry={findCompanions} />

      {result && (
        <>
          {result.data_source_status && (
            <View style={[s.card, { marginBottom: 10 }]}>
              <Text style={s.muted}>{result.data_source_status}</Text>
            </View>
          )}
          <FlatList
            data={result.candidates}
            keyExtractor={(c) => c.candidate_id}
            ListEmptyComponent={
              <View style={s.card}>
                <Text style={{ color: colors.text, fontWeight: "700" }}>No overlapping travellers right now</Text>
                <Text style={[s.muted, { marginTop: 4 }]}>Nobody else's journey matched yours closely enough this time.</Text>
              </View>
            }
            renderItem={({ item }) => (
              <View style={s.card}>
                <View style={s.row}>
                  <Text style={{ color: colors.text, fontWeight: "700" }}>Traveller {item.first_name_or_initial}</Text>
                  <View style={s.badge(item.verification_evidence.phone_verified ? colors.mint : colors.textDim)}>
                    <Text style={s.badgeText}>{item.verification_evidence.phone_verified ? "Phone verified" : "Unverified"}</Text>
                  </View>
                </View>
                <Text style={s.muted}>
                  {item.route_overlap_pct.toFixed(0)}% of your route overlaps · {item.time_overlap_minutes.toFixed(0)} min time overlap
                </Text>
                <Text style={s.muted}>Suggested meeting point: {item.meeting_point_label}</Text>
                {requestedId === item.candidate_id && requestStatus ? (
                  <View style={[s.badge(colors.accent), { marginTop: 8, alignSelf: "flex-start" }]}>
                    <Text style={s.badgeText}>Request sent</Text>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={[s.buttonSecondary, { marginTop: 8 }]}
                    onPress={() => requestCompanion(item.candidate_id)}
                  >
                    <Text style={s.buttonSecondaryText}>Request to travel together</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
          />
        </>
      )}
    </View>
  );
}
