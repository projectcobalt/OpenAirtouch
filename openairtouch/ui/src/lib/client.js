export const apiPath = (path) => `/api/${path}`;

export const wsPath = () => `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

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
