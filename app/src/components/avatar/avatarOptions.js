// Central source of truth for every choosable avatar trait. Screens and the
// renderer both import from here so the picker UI and the SVG composition
// can never drift out of sync.

export const SKIN_TONES = [
  { id: "porcelain", color: "#FFE0C7" },
  { id: "fair", color: "#F5C6A0" },
  { id: "honey", color: "#E0A878" },
  { id: "caramel", color: "#C58452" },
  { id: "umber", color: "#9C6236" },
  { id: "deep", color: "#6B3F22" },
];

export const HAIR_COLORS = [
  { id: "jetblack", color: "#2B2320" },
  { id: "brown", color: "#5B3A29" },
  { id: "chestnut", color: "#7A4A2C" },
  { id: "auburn", color: "#A9522C" },
  { id: "blonde", color: "#E4C078" },
  { id: "violet", color: "#8C6FF2" },
];

export const HAIRSTYLES = ["long", "bob", "bun", "ponytail", "curly", "pixie"];

export const OUTFIT_COLORS = [
  { id: "violet", color: "#8C6FF2" },
  { id: "coral", color: "#FF8B6A" },
  { id: "mint", color: "#3DDC97" },
  { id: "amber", color: "#FFB020" },
  { id: "rose", color: "#FF6FA5" },
];

export const ACCESSORIES = ["none", "earrings", "glasses", "headband"];

export const DEFAULT_AVATAR = {
  skinTone: SKIN_TONES[1].id,
  hairstyle: "long",
  hairColor: HAIR_COLORS[1].id,
  outfitColor: OUTFIT_COLORS[0].id,
  accessory: "earrings",
};

export function colorFor(list, id) {
  const found = list.find((x) => x.id === id);
  return found ? found.color : list[0].color;
}
