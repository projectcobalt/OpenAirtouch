export const MODE_OPTIONS = [
  [0, "Auto", "auto"],
  [1, "Heat", "heat"],
  [2, "Dry", "dry"],
  [3, "Fan", "fan"],
  [4, "Cool", "cool"]
];

export const MODE_THEMES = {
  auto: {
    accent: "#6f8984",
    accentSoft: "#dfe9e5",
    ink: "#24312f",
    muted: "rgba(36, 49, 47, .66)"
  },
  heat: {
    accent: "#c9784d",
    accentSoft: "#f1dccb",
    ink: "#3a261d",
    muted: "rgba(58, 38, 29, .68)"
  },
  dry: {
    accent: "#579997",
    accentSoft: "#d9ece9",
    ink: "#223837",
    muted: "rgba(34, 56, 55, .68)"
  },
  fan: {
    accent: "#7f916f",
    accentSoft: "#e1e8d8",
    ink: "#2b3324",
    muted: "rgba(43, 51, 36, .68)"
  },
  cool: {
    accent: "#5d8fb3",
    accentSoft: "#dce9f1",
    ink: "#243543",
    muted: "rgba(36, 53, 67, .68)"
  }
};

export const modeName = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, value])[1] || "-";

export const modeKey = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, null, "auto"])[2] || "auto";

export const fanName = (value) => ({0: "Auto", 1: "Low", 2: "Med", 3: "High", 7: "-"}[Number(value)] || String(value ?? "-"));
