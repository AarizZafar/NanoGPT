const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

function joinUrl(baseUrl, path) {
  const cleanBase = baseUrl.replace(/\/$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

export function apiUrl(path) {
  return joinUrl(API_BASE_URL, path);
}

export function websocketUrl(path) {
  if (API_BASE_URL.startsWith('http')) {
    const url = new URL(apiUrl(path));
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString();
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${apiUrl(path)}`;
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new Error(formatError(detail));
  }
  return response.json();
}

export function formatError(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => `${item.loc?.at(-1) || 'field'}: ${item.msg}`).join('\n');
  }
  return String(detail);
}
