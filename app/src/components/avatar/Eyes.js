import React from "react";
import { Ellipse, Circle } from "react-native-svg";

export default function Eyes() {
  return (
    <>
      <Ellipse cx="40" cy="49" rx="3.6" ry="4.6" fill="#2B2320" />
      <Ellipse cx="60" cy="49" rx="3.6" ry="4.6" fill="#2B2320" />
      <Circle cx="41.2" cy="47.3" r="1" fill="#FFFFFF" />
      <Circle cx="61.2" cy="47.3" r="1" fill="#FFFFFF" />
      {/* lashes */}
      <Ellipse cx="40" cy="44.5" rx="4.2" ry="1.1" fill="#2B2320" opacity="0.6" />
      <Ellipse cx="60" cy="44.5" rx="4.2" ry="1.1" fill="#2B2320" opacity="0.6" />
    </>
  );
}
