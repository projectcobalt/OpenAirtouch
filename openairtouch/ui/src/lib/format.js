export const finite = (value) => Number.isFinite(Number(value)) ? Number(value) : null;

export const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const DEGREE = "\u00b0";

export function tempText(value, digits = "auto") {
  const number = finite(value);
  if (number === null) return "-";
  if (Number.isInteger(digits)) return `${number.toFixed(digits)}${DEGREE}`;

  const rounded = Math.round(number * 10) / 10;
  const whole = Math.round(rounded);
  const text = Math.abs(rounded - whole) < 0.0001 ? String(whole) : rounded.toFixed(1);
  return `${text}${DEGREE}`;
}

export const percentText = (value) => finite(value) === null ? "-" : `${Math.round(Number(value))}%`;

export const title = (value) => String(value || "")
  .replace(/[_-]+/g, " ")
  .replace(/\b\w/g, (char) => char.toUpperCase());
