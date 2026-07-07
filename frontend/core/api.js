const BASE_URL = '/api/v1';
const TOKEN_KEY = 'rsu_token';
const TIER_KEY  = 'rsu_tier';
const EMAIL_KEY = 'rsu_email';

// Por defecto la sesión vive en sessionStorage (se pierde al cerrar la
// pestaña). Si el usuario marca "mantener sesión" al hacer login, se guarda
// en localStorage en su lugar, que persiste entre reinicios del navegador.
// getToken()/clearToken() comprueban ambos sitios para no depender de saber
// cuál se usó.

export function getToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token, remember = false) {
    const store = remember ? localStorage : sessionStorage;
    store.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    for (const store of [localStorage, sessionStorage]) {
        store.removeItem(TOKEN_KEY);
        store.removeItem(TIER_KEY);
        store.removeItem(EMAIL_KEY);
    }
}

export function setSession(token, tier, email, remember = false) {
    setToken(token, remember);
    const store = remember ? localStorage : sessionStorage;
    if (tier)  store.setItem(TIER_KEY, tier);
    if (email) store.setItem(EMAIL_KEY, email);
}

export function getTier() {
    return localStorage.getItem(TIER_KEY) || sessionStorage.getItem(TIER_KEY) || 'free';
}

export function getEmail() {
    return localStorage.getItem(EMAIL_KEY) || sessionStorage.getItem(EMAIL_KEY) || '';
}

// Nivel numérico del tier actual, para comparar en el front (p.ej. mostrar
// candados en el sidebar) sin tener que llamar al backend para cada check.
const TIER_ORDER = { free: 0, tier1: 1, tiers: 2 };

export function hasTier(minTier) {
    return (TIER_ORDER[getTier()] ?? 0) >= (TIER_ORDER[minTier] ?? 0);
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