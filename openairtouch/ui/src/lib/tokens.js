import { MODE_THEMES } from "./openairtouch.js";
import { assetPath } from "./client.js";

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
    `--mode-bg: url("${assetPath(`mode-backgrounds/${modeKey}.png`)}")`,
    `--mode-accent: ${theme.accent}`,
    `--mode-accent-soft: ${theme.accentSoft}`,
    `--mode-ink: ${theme.ink}`,
    `--mode-muted: ${theme.muted}`,
    `--accent: ${theme.accent}`,
    `--accent-soft: ${theme.accentSoft}`,
    `--radius-card: ${APP_TOKENS.radiusCard}`,
    `--layout-gap: ${APP_TOKENS.controlGap}`,
    `--layout-sidebar-w: ${APP_TOKENS.sidebarWidth}`
  ].join("; ");
}
