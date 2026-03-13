const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://vrachiapp-production.up.railway.app';

export function getCsrfToken() {
  return (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)') || []).pop() || '';
}

async function request(path, { method = 'GET', body, headers = {}, csrf = false, signal } = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE_URL.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`;

  const finalHeaders = {
    ...(body ? { 'Content-Type': 'application/json' } : {}),
    ...(csrf ? { 'X-CSRFToken': getCsrfToken() } : {}),
    ...headers,
  };

  const resp = await fetch(url, {
    method,
    credentials: 'include',
    headers: finalHeaders,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  const contentType = resp.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await resp.json().catch(() => null) : await resp.text().catch(() => null);

  if (!resp.ok) {
    const error = new Error((data && (data.error || data.detail)) || `Request failed with status ${resp.status}`);
    error.status = resp.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const apiClient = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  put: (path, body, opts) => request(path, { ...opts, method: 'PUT', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  del: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
};

export { API_BASE_URL };

