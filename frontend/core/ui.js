// Helpers de UI compartidos entre páginas — evita duplicar HTML de error
// en cada módulo. Pensado para crecer con otros patrones comunes (loading,
// empty state, etc.) si hace falta en el futuro.

const RATE_LIMIT_PATTERN = /demasiadas peticiones|rate limit|máximo \d+ requests/i;

/**
 * Detecta si un mensaje de error corresponde a un rate limit (429),
 * para poder darle un tratamiento visual distinto del de un error real.
 */
export function isRateLimitMessage(msg) {
    return RATE_LIMIT_PATTERN.test(msg || '');
}

/**
 * HTML de error genérico para insertar en un contenedor de widget.
 * Si el mensaje es de rate limit, usa color ámbar + icono de reloj en vez
 * del rojo/✗ de un fallo real — comunica "espera un momento", no "algo falló".
 */
export function errorMessage(msg, opts = {}) {
    const padding = opts.padding || '1rem';
    const fontSize = opts.fontSize || '12px';
    const extraStyle = opts.extraStyle || '';
    const safeMsg = esc(msg);

    if (isRateLimitMessage(msg)) {
        return '<div style="padding:' + padding + ';color:#ffb800;font-size:' + fontSize + ';display:flex;align-items:center;gap:6px;' + extraStyle + '">'
            + '<span style="font-size:14px;">⏱</span><span>' + safeMsg + '</span></div>';
    }
    return '<div style="padding:' + padding + ';color:#f23645;font-size:' + fontSize + ';' + extraStyle + '">✗ ' + safeMsg + '</div>';
}

/**
 * Escapa HTML antes de insertar texto de terceros (RSS, LLMs, tickers de la
 * URL, etc.) en innerHTML. Vía DOM (textContent -> innerHTML) en vez de
 * reemplazos manuales para cubrir comillas y casos raros que un replace a
 * mano se deja -- mismo enfoque ya probado en components/chat_widget.js.
 */
export function esc(str) {
    if (str == null) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

/**
 * Valida que una URL de terceros use http(s) antes de usarla en href --
 * evita que un feed externo cuele un esquema javascript:.
 */
export function safeUrl(url) {
    return /^https?:\/\//i.test(url || '') ? url : '#';
}

/**
 * Añade un ticker a la Watchlist del usuario. Compartido entre Research y
 * Scanner (y cualquier otra página que quiera un botón "＋ Watchlist" rápido)
 * para no duplicar la llamada al endpoint en cada sitio.
 * Devuelve { ok, error? } — quien llama decide cómo dar feedback visual
 * (cambiar texto de un botón, mostrar un toast, etc.).
 */
export async function addToWatchlist(ticker) {
    const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
    try {
        const res = await fetch('/api/v1/watchlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
            },
            body: JSON.stringify({ ticker: (ticker || '').toUpperCase() }),
        });
        const data = await res.json();
        return data;
    } catch (e) {
        return { ok: false, error: 'Error de red: ' + e.message };
    }
}