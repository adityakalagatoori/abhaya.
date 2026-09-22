import React from "react";
import { Circle, Line, Path } from "react-native-svg";

export default function Accessory({ type = "none" }) {
  switch (type) {
    case "earrings":
      return (
        <>
          <Circle cx="24" cy="63" r="2.4" fill="#FFD166" />
          <Circle cx="76" cy="63" r="2.4" fill="#FFD166" />
        </>
      );
    case "glasses":
      return (
        <>
          <Circle cx="40" cy="49" r="7" fill="none" stroke="#3B2E5A" strokeWidth="2" />
          <Circle cx="60" cy="49" r="7" fill="none" stroke="#3B2E5A" strokeWidth="2" />
          <Line x1="47" y1="49" x2="53" y2="49" stroke="#3B2E5A" strokeWidth="2" />
        </>
      );
    case "headband":
      return <Path d="M24 38 Q50 24 76 38" stroke="#FF8B6A" strokeWidth="4" fill="none" strokeLinecap="round" />;
    case "none":
    default:
      return null;
  }
}
