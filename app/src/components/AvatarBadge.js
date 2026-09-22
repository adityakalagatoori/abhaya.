import React from "react";
import { View, TouchableOpacity, StyleSheet } from "react-native";
import AvatarRenderer from "./avatar/AvatarRenderer";
import { useAvatar } from "../context/AvatarContext";
import { colors } from "../theme";

// Small circular clay-framed avatar, meant for the nav header / home screen.
export default function AvatarBadge({ size = 40, onPress }) {
  const { avatar } = useAvatar();
  const frame = (
    <View style={[styles.frame, { width: size + 10, height: size + 10, borderRadius: (size + 10) / 2 }]}>
      <View style={{ width: size, height: size, borderRadius: size / 2, overflow: "hidden" }}>
        <AvatarRenderer config={avatar} size={size} />
      </View>
    </View>
  );
  if (!onPress) return frame;
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.8}>
      {frame}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  frame: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.cardAlt,
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.85)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 4, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 6,
    elevation: 5,
  },
});
