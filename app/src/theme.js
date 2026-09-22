// ABHAYA claymorphism design system.
// Soft, puffy "inflated clay" look: large radii, vivid pastel colors, and a
// dual light/dark shadow that fakes a raised 3D dough shape. React Native
// doesn't support multiple box-shadows on a single node, so simple flat
// style objects here use one strong soft shadow + a light top border to
// suggest the highlight; the src/components/Clay* library layers real
// separate Views for the full dual-shadow effect where it matters most
// (cards, buttons, avatar frame, etc).

export const colors = {
  // Warm, soft, trustworthy — lavender/cream base with vivid clay accents.
  bg: "#F3EEFB",
  bgAlt: "#ECE3FA",
  card: "#FBF8FF",
  cardAlt: "#F1E9FC",

  // Primary accent: soft violet (trust/safety)
  accent: "#8C6FF2",
  accentDark: "#6F52D8",
  accentSoft: "#E4DBFB",

  // Secondary accent: warm coral (warmth/companion)
  coral: "#FF8B6A",
  coralSoft: "#FFE1D6",

  // Tertiary: mint (calm/safe confirmation)
  mint: "#3DDC97",
  mintSoft: "#D6F7E9",

  // Amber (caution)
  amber: "#FFB020",
  amberSoft: "#FFEBC7",

  danger: "#FF5C7A",
  dangerSoft: "#FFDCE4",
  warning: "#FFB020",

  text: "#3B2E5A",
  textDim: "#8577A6",
  border: "#E2D6F7",

  // Clay shadow pair
  shadowDark: "#B9A6E8",
  shadowLight: "#FFFFFF",
};

const claySurface = {
  backgroundColor: colors.card,
  borderRadius: 28,
  borderWidth: 1.5,
  borderColor: "rgba(255,255,255,0.7)",
  shadowColor: colors.shadowDark,
  shadowOffset: { width: 8, height: 8 },
  shadowOpacity: 0.35,
  shadowRadius: 14,
  elevation: 8,
};

export const s = {
  screen: { flex: 1, backgroundColor: colors.bg, padding: 16 },
  title: { color: colors.text, fontSize: 24, fontWeight: "800", marginBottom: 4, letterSpacing: 0.2 },
  subtitle: { color: colors.textDim, fontSize: 13.5, marginBottom: 16, lineHeight: 19 },
  card: {
    ...claySurface,
    padding: 16,
    marginBottom: 14,
  },
  label: { color: colors.textDim, fontSize: 12, fontWeight: "700", marginBottom: 6, marginTop: 10, letterSpacing: 0.4 },
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
  button: {
    backgroundColor: colors.accent,
    borderRadius: 26,
    padding: 16,
    alignItems: "center",
    marginTop: 16,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.5)",
    shadowColor: colors.accentDark,
    shadowOffset: { width: 6, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 6,
  },
  buttonText: { color: "#FFFFFF", fontWeight: "800", fontSize: 15.5, letterSpacing: 0.3 },
  buttonSecondary: {
    backgroundColor: colors.cardAlt,
    borderRadius: 26,
    padding: 16,
    alignItems: "center",
    marginTop: 10,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.8)",
    shadowColor: colors.shadowDark,
    shadowOffset: { width: 4, height: 4 },
    shadowOpacity: 0.22,
    shadowRadius: 7,
    elevation: 3,
  },
  buttonSecondaryText: { color: colors.text, fontWeight: "700" },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  badge: (bg) => ({
    backgroundColor: bg,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.6)",
  }),
  badgeText: { color: "#FFFFFF", fontWeight: "800", fontSize: 12 },
  errorText: { color: colors.danger, marginTop: 10, fontWeight: "600" },
  muted: { color: colors.textDim, fontSize: 13 },
};
