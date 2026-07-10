const WIDTH = 160;
const TOP = 8;
const HEIGHT = 32;

const finite = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export const lineClass = (kind = "") => `chart-line chart-line-${kind || "actual"}`;

const chartValues = (chart = {}) => [
  ...(Array.isArray(chart.lines) ? chart.lines.flatMap((line) => (line.points || []).map((point) => finite(point.y)).filter((value) => value !== null)) : []),
  ...(Array.isArray(chart.bands) ? chart.bands.flatMap((band) => [finite(band.min), finite(band.max)]).filter((value) => value !== null) : [])
];

const chartXs = (chart = {}) => [
  ...(Array.isArray(chart.lines) ? chart.lines.flatMap((line) => (line.points || []).map((point) => finite(point.x)).filter((value) => value !== null)) : []),
  ...(Array.isArray(chart.windows) ? chart.windows.flatMap((window) => [finite(window.start), finite(window.end)]).filter((value) => value !== null) : [])
];

const mixedXDomains = (xs) => {
  if (xs.length < 3) return false;
  const min = Math.min(...xs);
  const max = Math.max(...xs);
  return min <= 1000 && max >= 10000;
};

const ordinalXScale = (chart = {}) => {
  const positions = new Map();
  let next = 0;
  for (const line of Array.isArray(chart.lines) ? chart.lines : []) {
    for (const point of Array.isArray(line.points) ? line.points : []) {
      const x = finite(point.x);
      if (x === null) continue;
      const key = String(x);
      if (!positions.has(key)) positions.set(key, next++);
    }
  }
  for (const window of Array.isArray(chart.windows) ? chart.windows : []) {
    for (const x of [finite(window.start), finite(window.end)]) {
      if (x === null) continue;
      const key = String(x);
      if (!positions.has(key)) positions.set(key, next++);
    }
  }
  const maxPosition = Math.max(1, next - 1);
  return (value) => {
    const position = positions.get(String(value));
    return ((position ?? 0) / maxPosition) * WIDTH;
  };
};

export function analyticsChartData(chart = {}) {
  const values = chartValues(chart);
  const xs = chartXs(chart);
  const minY = values.length ? Math.min(...values) : 0;
  const maxY = values.length ? Math.max(...values) : 1;
  const pad = Math.max(0.5, (maxY - minY) * 0.18);
  const y0 = minY - pad;
  const y1 = maxY + pad;
  const minX = xs.length ? Math.min(...xs) : 0;
  const maxX = xs.length ? Math.max(...xs) : 1;
  const yScale = (value) => TOP + HEIGHT - (((value - y0) / Math.max(1, y1 - y0)) * HEIGHT);
  const numericXScale = (value) => ((value - minX) / Math.max(1, maxX - minX)) * WIDTH;
  const xScale = mixedXDomains(xs) ? ordinalXScale(chart) : numericXScale;
  const linePaths = (Array.isArray(chart.lines) ? chart.lines : []).map((line) => ({
    ...line,
    path: (line.points || [])
      .map((point, index) => {
        const x = finite(point.x);
        const y = finite(point.y);
        if (x === null || y === null) return "";
        return `${index ? "L" : "M"}${xScale(x).toFixed(1)} ${yScale(y).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ")
  })).filter((line) => line.path);
  const bands = (Array.isArray(chart.bands) ? chart.bands : []).map((band) => {
    const top = yScale(finite(band.max) ?? finite(band.min) ?? 0);
    const bottom = yScale(finite(band.min) ?? finite(band.max) ?? 0);
    return {...band, y: Math.min(top, bottom), height: Math.max(1, Math.abs(bottom - top))};
  });
  const windows = (Array.isArray(chart.windows) ? chart.windows : []).map((window) => {
    const start = xScale(finite(window.start) ?? minX);
    const end = xScale(finite(window.end) ?? minX);
    return {...window, x: Math.min(start, end), width: Math.max(1, Math.abs(end - start))};
  });
  const hasData = chart.has_data === true && linePaths.length > 0;
  const meaningful = hasData && chart.meaningful !== false;
  return {
    title: chart.title || "Analytics",
    summary: meaningful ? (chart.summary || "Trend available") : (chart.summary || chart.empty_reason || "No meaningful chart data"),
    hasData,
    meaningful,
    linePaths,
    bands: meaningful ? bands : [],
    windows: meaningful ? windows : []
  };
}
