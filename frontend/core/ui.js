import { authHeader } from '/core/api.js';
// Helpers de UI compartidos entre páginas — evita duplicar HTML de error
// en cada módulo. Pensado para crecer con otros patrones comunes (loading,
// empty state, etc.) si hace falta en el futuro.

const RATE_LIMIT_PATTERN = /demasiadas peticiones|rate limit|máximo \d+ requests/i;

// ── FECHAS ───────────────────────────────────────────────────────────────────
//
// El backend y las fuentes externas (SEC, EDGAR, yfinance, los Gists de los
// scans) trabajan en ISO — 2026-07-14 — porque así se ordena alfabéticamente
// y se compara sin parsear. Pero al usuario se le enseña en el formato de
// aquí: 14/07/2026.
//
// Hasta el 04/08/2026 la terminal mezclaba los dos: Options Flow y el
// Algoritmo formateaban (cada uno por su cuenta) y otras diez páginas
// pintaban el ISO crudo. Estos dos helpers son el único sitio donde se
// decide el formato.
//
// IMPORTANTE: son solo para PINTAR. El valor ISO tiene que seguir siendo el
// que se use para ordenar tablas y comparar fechas — formatear antes de
// ordenar rompería el orden (31/01 iría después de 01/02).
const _ISO_FECHA = /^(\d{4})-(\d{2})-(\d{2})/;
const _ISO_FECHA_HORA = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)/;

/**
 * "2026-07-14" -> "14/07/2026". Vacío -> "—". Si no es una fecha ISO
 * reconocible se devuelve tal cual: mejor enseñar el dato original que
 * inventarse una fecha a partir de algo que no lo era.
 */
export function fmtFecha(iso) {
    if (!iso || typeof iso !== 'string') return '—';
    const m = iso.match(_ISO_FECHA);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

/**
 * Igual pero conservando la hora: "2026-07-14T16:22:28" -> "14/07/2026 16:22:28".
 * Si no trae hora, cae en fmtFecha().
 */
export function fmtFechaHora(iso) {
    if (!iso || typeof iso !== 'string') return '—';
    const m = iso.match(_ISO_FECHA_HORA);
    return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}` : fmtFecha(iso);
}

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
    try {
        const res = await fetch('/api/v1/watchlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeader(),
            },
            body: JSON.stringify({ ticker: (ticker || '').toUpperCase() }),
        });
        const data = await res.json();
        return data;
    } catch (e) {
        return { ok: false, error: 'Error de red: ' + e.message };
    }
}