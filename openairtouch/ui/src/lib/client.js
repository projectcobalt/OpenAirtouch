function serviceBasePath() {
  const path = window.location.pathname;
  const normalized = path.endsWith("/") ? path : `${path}/`;
  return normalized.replace(/\/ui\/$/, "/");
}

export function servicePath(path) {
  const base = `${window.location.origin}${serviceBasePath()}`;
  return new URL(path, base).pathname;
}

export const apiPath = (path) => servicePath(`api/${path}`);

export const assetPath = (path) => servicePath(`assets/${path}`);

export const wsPath = () => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${servicePath("ws")}`;
};

export async function fetchJson(path) {
  const response = await fetch(apiPath(path));
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

export async function postCommand(action, data) {
  const response = await fetch(apiPath("command"), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({action, data})
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Command failed: ${response.status}`);
  }
  return response.json();
}
