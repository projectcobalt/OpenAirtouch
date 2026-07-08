export const MODE_OPTIONS = [
  [0, "Auto", "auto"],
  [1, "Heat", "heat"],
  [2, "Dry", "dry"],
  [3, "Fan", "fan"],
  [4, "Cool", "cool"]
];

export const MODE_THEMES = {
  auto: {
    accent: "#5d927f",
    accentSoft: "#dfeae5",
    ink: "#22352f",
    muted: "rgba(34, 53, 47, .66)"
  },
  heat: {
    accent: "#b87049",
    accentSoft: "#efd9cb",
    ink: "#39261d",
    muted: "rgba(57, 38, 29, .68)"
  },
  dry: {
    accent: "#52938d",
    accentSoft: "#d9e9e7",
    ink: "#213836",
    muted: "rgba(33, 56, 54, .68)"
  },
  fan: {
    accent: "#78909d",
    accentSoft: "#dde7ec",
    ink: "#27343b",
    muted: "rgba(39, 52, 59, .68)"
  },
  cool: {
    accent: "#528fc1",
    accentSoft: "#dbe9f3",
    ink: "#21364a",
    muted: "rgba(33, 54, 74, .68)"
  }
};

export const modeName = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, value])[1] || "-";

export const modeKey = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, null, "auto"])[2] || "auto";

export const fanName = (value) => ({0: "Auto", 1: "Low", 2: "Med", 3: "High", 7: "-"}[Number(value)] || String(value ?? "-"));
