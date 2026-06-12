const BASE_URL = '/api/v1';
const TOKEN_KEY = 'rsu_token';

function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}

async function request(endpoint, options = {}) {
    const token = getToken();

    const res = await fetch(BASE_URL + endpoint, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        },
    });

    if (res.status === 401) {
        clearToken();
        window.__navigate('/login');
        return null;
    }

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(error.detail || `HTTP ${res.status}`);
    }

    return res.json();
}

export const api = {
    get:    (endpoint)         => request(endpoint),
    post:   (endpoint, body)   => request(endpoint, { method: 'POST',   body: JSON.stringify(body) }),
    put:    (endpoint, body)   => request(endpoint, { method: 'PUT',    body: JSON.stringify(body) }),
    delete: (endpoint)         => request(endpoint, { method: 'DELETE' }),
};
