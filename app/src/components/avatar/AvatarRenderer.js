import React from "react";
import Svg, { ClipPath, Rect, Defs, G } from "react-native-svg";
import Face from "./Face";
import Eyes from "./Eyes";
import Hair from "./Hair";
import Outfit from "./Outfit";
import Accessory from "./Accessory";
import { colorFor, SKIN_TONES, HAIR_COLORS } from "./avatarOptions";

// Composes all layered SVG parts into one avatar. Pure presentational —
// takes a config object (as persisted to AsyncStorage) and renders it.
// Layer order (back to front): hair-back, face, eyes, hair-front, outfit,
// accessory.
export default function AvatarRenderer({ config, size = 96 }) {
  const skin = colorFor(SKIN_TONES, config?.skinTone);
  const hairColor = colorFor(HAIR_COLORS, config?.hairColor);
  const hairstyle = config?.hairstyle || "long";
  const outfitColor = config?.outfitColor || "#8C6FF2";
  const accessory = config?.accessory || "none";

  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Defs>
        <ClipPath id="clip">
          <Rect x="0" y="0" width="100" height="100" rx="50" ry="50" />
        </ClipPath>
      </Defs>
      <G clipPath="url(#clip)">
        <Rect x="0" y="0" width="100" height="100" fill="#F1E9FC" />
        <Hair style={hairstyle} color={hairColor} layer="back" />
        <Face skin={skin} />
        <Eyes />
        <Hair style={hairstyle} color={hairColor} layer="front" />
        <Outfit color={outfitColor} />
        <Accessory type={accessory} />
      </G>
    </Svg>
  );
}
