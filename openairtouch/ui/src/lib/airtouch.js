export const MODE_OPTIONS = [
  [0, "Auto", "auto"],
  [1, "Heat", "heat"],
  [2, "Dry", "dry"],
  [3, "Fan", "fan"],
  [4, "Cool", "cool"]
];

export const MODE_THEMES = {
  auto: {
    accent: "#8a8178",
    accentSoft: "#ebe4da",
    tint: "#3d3832",
    ink: "#24211d",
    muted: "rgba(36, 33, 29, .66)",
    overlay: "linear-gradient(180deg, rgba(250,247,242,.70), rgba(232,225,216,.56) 48%, rgba(132,124,113,.42))",
    cool: "#8f9290",
    warm: "#b7a38f",
    glow: "rgba(138, 129, 120, .28)"
  },
  heat: {
    accent: "#c9784d",
    accentSoft: "#f0d1b8",
    tint: "#3b2118",
    ink: "#2d1b14",
    muted: "rgba(45, 27, 20, .68)",
    overlay: "linear-gradient(180deg, rgba(255,243,233,.76), rgba(240,207,184,.56) 52%, rgba(125,63,41,.45))",
    cool: "#b6a18e",
    warm: "#c9784d",
    glow: "rgba(201, 120, 77, .32)"
  },
  dry: {
    accent: "#9b879e",
    accentSoft: "#ded2df",
    tint: "#312833",
    ink: "#261f28",
    muted: "rgba(38, 31, 40, .68)",
    overlay: "linear-gradient(180deg, rgba(248,242,249,.74), rgba(222,210,223,.54) 52%, rgba(82,67,86,.46))",
    cool: "#9b879e",
    warm: "#b59a84",
    glow: "rgba(155, 135, 158, .28)"
  },
  fan: {
    accent: "#89937d",
    accentSoft: "#dce1d2",
    tint: "#252b21",
    ink: "#20261d",
    muted: "rgba(32, 38, 29, .68)",
    overlay: "linear-gradient(180deg, rgba(247,249,242,.74), rgba(220,225,210,.56) 52%, rgba(74,84,64,.44))",
    cool: "#89937d",
    warm: "#b4a389",
    glow: "rgba(137, 147, 125, .28)"
  },
  cool: {
    accent: "#8a9298",
    accentSoft: "#dde2e4",
    tint: "#262b2e",
    ink: "#202326",
    muted: "rgba(32, 35, 38, .68)",
    overlay: "linear-gradient(180deg, rgba(247,249,250,.74), rgba(221,226,228,.56) 52%, rgba(73,82,88,.44))",
    cool: "#8a9298",
    warm: "#c7b6a4",
    glow: "rgba(138, 146, 152, .30)"
  }
};

export const modeName = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, value])[1] || "-";

export const modeKey = (value) => (MODE_OPTIONS.find(([mode]) => Number(mode) === Number(value)) || [null, null, "auto"])[2] || "auto";

export const fanName = (value) => ({0: "Auto", 1: "Low", 2: "Med", 3: "High", 7: "-"}[Number(value)] || String(value ?? "-"));
