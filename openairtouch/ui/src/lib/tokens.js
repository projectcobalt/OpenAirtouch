import { MODE_THEMES } from "./airtouch.js";

export const APP_TOKENS = {
  radiusCard: "22px",
  controlGap: "clamp(12px, 1.2vw, 16px)",
  sidebarWidth: "clamp(340px, 25vw, 405px)"
};

export function modeThemeFor(modeKey = "auto") {
  return MODE_THEMES[modeKey] || MODE_THEMES.auto;
}

export function modeStyleFor(modeKey = "auto") {
  const theme = modeThemeFor(modeKey);
  return [
    `--mode-bg: url("/assets/mode-backgrounds/${modeKey}.png")`,
    `--mode-accent: ${theme.accent}`,
    `--mode-accent-soft: ${theme.accentSoft}`,
    `--mode-panel-tint: ${theme.tint}`,
    `--mode-tint: ${theme.tint}`,
    `--mode-ink: ${theme.ink}`,
    `--mode-muted: ${theme.muted}`,
    `--mode-overlay: ${theme.overlay}`,
    `--accent: ${theme.accent}`,
    `--accent-soft: ${theme.accentSoft}`,
    `--warm: ${theme.warm}`,
    `--cool: ${theme.cool}`,
    `--surface-glow: 0 0 42px ${theme.glow}`,
    `--radius-card: ${APP_TOKENS.radiusCard}`,
    `--layout-gap: ${APP_TOKENS.controlGap}`,
    `--layout-sidebar-w: ${APP_TOKENS.sidebarWidth}`
  ].join("; ");
}
