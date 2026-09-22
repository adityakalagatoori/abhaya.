import React from "react";
import { Ellipse, Path } from "react-native-svg";

// Base head/neck/face shape + eyebrows + a soft smile, all tinted by skin color.
export default function Face({ skin = "#F5C6A0" }) {
  const shade = shadeColor(skin, -18);
  return (
    <>
      {/* neck */}
      <Path d="M42 78 Q50 90 58 78 L58 95 Q50 100 42 95 Z" fill={skin} />
      {/* head */}
      <Ellipse cx="50" cy="50" rx="26" ry="28" fill={skin} />
      {/* cheeks blush */}
      <Ellipse cx="34" cy="56" rx="4.5" ry="3" fill="#FF9E9E" opacity="0.35" />
      <Ellipse cx="66" cy="56" rx="4.5" ry="3" fill="#FF9E9E" opacity="0.35" />
      {/* eyebrows */}
      <Path d="M32 40 Q37 36 43 39" stroke={shade} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <Path d="M57 39 Q63 36 68 40" stroke={shade} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* smile */}
      <Path d="M40 62 Q50 70 60 62" stroke="#7A4A45" strokeWidth="2.2" strokeLinecap="round" fill="none" />
    </>
  );
}

function shadeColor(hex, amt) {
  const c = hex.replace("#", "");
  const num = parseInt(c, 16);
  let r = (num >> 16) + amt;
  let g = ((num >> 8) & 0x00ff) + amt;
  let b = (num & 0x0000ff) + amt;
  r = Math.max(Math.min(255, r), 0);
  g = Math.max(Math.min(255, g), 0);
  b = Math.max(Math.min(255, b), 0);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}
