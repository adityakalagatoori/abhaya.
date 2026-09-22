import React, { useEffect, useRef, useState } from "react";
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator } from "react-native";
import { s, colors } from "../theme";
import { searchPlaces } from "../api/geocode";

const DEBOUNCE_MS = 500;

// Real place-name search box backed by OpenStreetMap's Nominatim geocoder
// (see api/geocode.js). Replaces raw lat/lon text entry -- plan item #1.
//
// Props:
//   placeholder: string
//   biasLat/biasLon: optional coordinates to bias results toward
//   onSelect: (place: {label, lat, lon}) => void
//   value: currently selected place's label, for display when not editing
export default function PlaceSearchInput({ placeholder, biasLat, biasLon, onSelect, value }) {
  const [text, setText] = useState(value || "");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    setText(value || "");
  }, [value]);

  function handleChange(t) {
    setText(t);
    setOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (t.trim().length < 3) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setErr(null);
      try {
        const r = await searchPlaces(t, { biasLat, biasLon });
        setResults(r);
      } catch (e) {
        setErr("Couldn't search right now.");
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
  }

  function select(place) {
    setText(place.label);
    setResults([]);
    setOpen(false);
    onSelect(place);
  }

  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <TextInput
          style={[s.input, { flex: 1 }]}
          placeholder={placeholder}
          placeholderTextColor={colors.textDim}
          value={text}
          onChangeText={handleChange}
          onFocus={() => setOpen(true)}
        />
        {loading && <ActivityIndicator style={{ marginLeft: -36 }} color={colors.accent} />}
      </View>

      {open && (results.length > 0 || err) && (
        <View style={[s.card, { marginTop: -6, paddingVertical: 6 }]}>
          {err && <Text style={[s.muted, { padding: 8 }]}>{err}</Text>}
          {results.map((r, i) => (
            <TouchableOpacity
              key={i}
              onPress={() => select(r)}
              style={{ paddingVertical: 10, paddingHorizontal: 8, borderTopWidth: i > 0 ? 1 : 0, borderTopColor: colors.border }}
            >
              <Text style={{ color: colors.text }} numberOfLines={2}>{r.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );
}
