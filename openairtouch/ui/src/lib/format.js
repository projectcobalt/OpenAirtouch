export const finite = (value) => Number.isFinite(Number(value)) ? Number(value) : null;

export const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export const tempText = (value, digits = 0) => finite(value) === null ? "-" : `${Number(value).toFixed(digits)}°`;

export const percentText = (value) => finite(value) === null ? "-" : `${Math.round(Number(value))}%`;

export const title = (value) => String(value || "")
  .replace(/[_-]+/g, " ")
  .replace(/\b\w/g, (char) => char.toUpperCase());
