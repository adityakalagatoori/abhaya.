import React from "react";
import { Path, Ellipse, Circle } from "react-native-svg";

// Six feminine hairstyle variants built from simple SVG paths, all tinted
// by the chosen hair color. Drawn behind (back layer) and in front (bangs/
// fringe layer) of the face by AvatarRenderer.
export default function Hair({ style = "long", color = "#5B3A29", layer = "back" }) {
  if (layer === "back") {
    switch (style) {
      case "long":
        return <Path d="M22 48 Q18 90 30 100 L34 100 Q26 70 30 46 Z M78 48 Q82 90 70 100 L66 100 Q74 70 70 46 Z" fill={color} />;
      case "ponytail":
        return (
          <>
            <Path d="M74 40 Q92 55 82 90 Q78 92 75 88 Q84 58 68 42 Z" fill={color} />
          </>
        );
      case "bun":
        return <Circle cx="50" cy="20" r="9" fill={color} />;
      case "curly":
        return (
          <>
            <Circle cx="20" cy="55" r="9" fill={color} />
            <Circle cx="22" cy="70" r="8" fill={color} />
            <Circle cx="80" cy="55" r="9" fill={color} />
            <Circle cx="78" cy="70" r="8" fill={color} />
            <Circle cx="50" cy="24" r="10" fill={color} />
          </>
        );
      case "bob":
      case "pixie":
      default:
        return null;
    }
  }

  // front / bangs layer
  switch (style) {
    case "long":
      return <Path d="M24 44 Q26 16 50 15 Q74 16 76 44 Q68 30 50 30 Q32 30 24 44 Z" fill={color} />;
    case "bob":
      return <Path d="M22 46 Q20 14 50 13 Q80 14 78 46 Q76 62 70 60 Q73 34 50 32 Q27 34 30 60 Q24 62 22 46 Z" fill={color} />;
    case "bun":
      return <Path d="M24 44 Q26 17 50 16 Q74 17 76 44 Q68 28 50 28 Q32 28 24 44 Z" fill={color} />;
    case "ponytail":
      return <Path d="M24 44 Q26 16 50 15 Q72 16 75 40 Q65 26 50 27 Q33 27 24 44 Z" fill={color} />;
    case "curly":
      return (
        <>
          <Path d="M25 42 Q28 16 50 15 Q72 16 75 42 Q65 27 50 27 Q35 27 25 42 Z" fill={color} />
        </>
      );
    case "pixie":
      return <Path d="M26 42 Q28 22 50 20 Q72 22 74 42 Q68 30 50 30 Q32 30 26 42 Z" fill={color} />;
    default:
      return null;
  }
}
