const BASE_URL = '/api/v1';
const TOKEN_KEY   = 'rsu_token';    // solo restos de antes de la cookie, ver abajo
const SESSION_KEY = 'rsu_session';
const TIER_KEY    = 'rsu_tier';
const EMAIL_KEY   = 'rsu_email';

// El token de sesión YA NO VIVE AQUÍ. Está en una cookie httpOnly que pone
// el backend, que el navegador reenvía sola en cada petición y que este
// código no puede leer -- que es justo el objetivo: si algún día se cuela un
// XSS en cualquier página de la terminal, no hay sesión que robar.
//
// Lo que sí se guarda aquí son tres datos que no son credenciales y que solo
// sirven para pintar la interfaz sin tener que esperar a una llamada al
// backend: un marcador de "hay sesión", el plan y el email. Falsificarlos a
// mano no da acceso a nada -- cada endpoint comprueba la cookie de verdad.
//
// TOKEN_KEY es transición, no diseño: quien ya estuviera usando la terminal
// antes de este cambio tiene un token guardado en el navegador, y se sigue
// enviando como Bearer para no echar a nadie el día del despliegue. En
// cuanto esa gente vuelva a iniciar sesión pasa a cookie, y este resto se
// puede borrar (el backend ya da prioridad a la cookie sobre la cabecera).

function legacyToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function authHeader() {
    const t = legacyToken();
    return t ? { 'Authorization': 'Bearer ' + t } : {};
}

export function isLoggedIn() {
    return !!(localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY) || legacyToken());
}

export function clearToken() {
    for (const store of [localStorage, sessionStorage]) {
        store.removeItem(TOKEN_KEY);
        store.removeItem(SESSION_KEY);
        store.removeItem(TIER_KEY);
        store.removeItem(EMAIL_KEY);
    }
}

export function setSession(tier, email, remember = false) {
    // "Mantener sesión" ya no decide dónde va el token (eso lo lleva la
    // cookie, y su duración la fija el backend) -- aquí solo decide si estos
    // datos de interfaz sobreviven a cerrar el navegador, para que al volver
    // se pinte el plan correcto desde el primer render.
    const store = remember ? localStorage : sessionStorage;
    store.setItem(SESSION_KEY, '1');
    if (tier)  store.setItem(TIER_KEY, tier);
    if (email) store.setItem(EMAIL_KEY, email);
}

export async function logout() {
    // Borrar la cookie es cosa del backend: httpOnly implica que este código
    // no puede tocarla. Si la llamada falla (sin red), se limpia igualmente
    // lo local para no dejar la interfaz diciendo que hay sesión.
    try { await fetch(BASE_URL + '/auth/logout', { method: 'POST' }); } catch (e) { /* offline */ }
    clearToken();
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
    const res = await fetch(BASE_URL + endpoint, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeader(),
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