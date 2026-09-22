import React from "react";
import { Path } from "react-native-svg";

export default function Outfit({ color = "#8C6FF2" }) {
  const collar = shade(color, -25);
  return (
    <>
      <Path d="M18 100 Q50 82 82 100 L84 118 L16 118 Z" fill={color} />
      <Path d="M40 92 L50 102 L60 92 L58 86 L50 90 L42 86 Z" fill={collar} />
    </>
  );
}

function shade(hex, amt) {
  const c = hex.replace("#", "");
  const num = parseInt(c, 16);
  let r = Math.max(Math.min(255, (num >> 16) + amt), 0);
  let g = Math.max(Math.min(255, ((num >> 8) & 0x00ff) + amt), 0);
  let b = Math.max(Math.min(255, (num & 0x0000ff) + amt), 0);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}
