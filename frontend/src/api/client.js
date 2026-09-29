const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError(
      'Backend unavailable — is the Spring Boot API running on ' + BASE_URL + '?',
      'BACKEND_UNAVAILABLE',
      0,
    );
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = body.error || {};
    throw new ApiError(
      err.message || `Request failed (${res.status})`,
      err.code || 'API_ERROR',
      res.status,
    );
  }
  return body;
}

function qs(params) {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') s.set(k, v);
  });
  const str = s.toString();
  return str ? `?${str}` : '';
}

export const api = {
  getDevices: (params = {}) => request(`/api/devices${qs(params)}`),
  getRepairCosts: (params = {}) =>
    request(`/api/repair-costs${qs(params)}`),
  postAcquisitionQuote: (payload) =>
    request('/api/acquisition/quote', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
