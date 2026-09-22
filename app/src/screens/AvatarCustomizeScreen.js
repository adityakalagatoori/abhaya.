import React from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from "react-native";
import { colors, s } from "../theme";
import ClayCard from "../components/ClayCard";
import AvatarRenderer from "../components/avatar/AvatarRenderer";
import { useAvatar } from "../context/AvatarContext";
import {
  SKIN_TONES,
  HAIR_COLORS,
  HAIRSTYLES,
  OUTFIT_COLORS,
  ACCESSORIES,
} from "../components/avatar/avatarOptions";

function SwatchRow({ label, children }) {
  return (
    <View style={{ marginBottom: 18 }}>
      <Text style={s.label}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingVertical: 4 }}>
        {children}
      </ScrollView>
    </View>
  );
}

function ColorSwatch({ color, selected, onPress }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.swatch, { backgroundColor: color }, selected && styles.swatchSelected]} />
  );
}

function ChipSwatch({ label, selected, onPress }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.chip, selected && styles.chipSelected]}>
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function AvatarCustomizeScreen() {
  const { avatar, updateAvatar } = useAvatar();

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={s.title}>Your ABHAYA companion</Text>
      <Text style={s.subtitle}>Customize your avatar. It travels with you on WalkGuard and check-in screens.</Text>

      <ClayCard style={{ alignItems: "center", marginBottom: 20 }}>
        <AvatarRenderer config={avatar} size={140} />
      </ClayCard>

      <SwatchRow label="SKIN TONE">
        {SKIN_TONES.map((t) => (
          <ColorSwatch key={t.id} color={t.color} selected={avatar.skinTone === t.id} onPress={() => updateAvatar({ skinTone: t.id })} />
        ))}
      </SwatchRow>

      <SwatchRow label="HAIRSTYLE">
        {HAIRSTYLES.map((h) => (
          <ChipSwatch key={h} label={h} selected={avatar.hairstyle === h} onPress={() => updateAvatar({ hairstyle: h })} />
        ))}
      </SwatchRow>

      <SwatchRow label="HAIR COLOR">
        {HAIR_COLORS.map((c) => (
          <ColorSwatch key={c.id} color={c.color} selected={avatar.hairColor === c.id} onPress={() => updateAvatar({ hairColor: c.id })} />
        ))}
      </SwatchRow>

      <SwatchRow label="OUTFIT COLOR">
        {OUTFIT_COLORS.map((c) => (
          <ColorSwatch key={c.id} color={c.color} selected={avatar.outfitColor === c.id} onPress={() => updateAvatar({ outfitColor: c.id })} />
        ))}
      </SwatchRow>

      <SwatchRow label="ACCESSORY">
        {ACCESSORIES.map((a) => (
          <ChipSwatch key={a} label={a} selected={avatar.accessory === a} onPress={() => updateAvatar({ accessory: a })} />
        ))}
      </SwatchRow>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  swatch: {
    width: 44,
    height: 44,
    borderRadius: 22,
    marginRight: 10,
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.8)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 3,
  },
  swatchSelected: {
    borderColor: colors.accentDark,
    borderWidth: 3,
  },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: colors.cardAlt,
    marginRight: 10,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.8)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 5,
    elevation: 3,
  },
  chipSelected: {
    backgroundColor: colors.accent,
  },
  chipText: { color: colors.text, fontWeight: "700", fontSize: 13, textTransform: "capitalize" },
  chipTextSelected: { color: "#FFFFFF" },
});
