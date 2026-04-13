export async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  let body = {};
  try {
    body = await res.json();
  } catch (_) {
    body = {};
  }

  if (!res.ok || body.ok === false) {
    throw new Error(body.error || `Request failed (${res.status})`);
  }

  return body;
}

export function post(path, data) {
  return api(path, { method: 'POST', body: JSON.stringify(data) });
}

export function patch(path, data) {
  return api(path, { method: 'PATCH', body: JSON.stringify(data) });
}

export function del(path) {
  return api(path, { method: 'DELETE' });
}
