import React from "react";
import { TextInput, StyleSheet } from "react-native";
import { colors } from "../theme";

export default function ClayInput(props) {
  return <TextInput placeholderTextColor={colors.textDim} {...props} style={[styles.input, props.style]} />;
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.cardAlt,
    color: colors.text,
    borderRadius: 20,
    padding: 14,
    fontSize: 15,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.8)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
    elevation: 2,
  },
});
