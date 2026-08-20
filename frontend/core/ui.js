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

/* ── El envoltorio de widget, y la banda de avisos ────────────────────────────
 *
 * POR QUÉ ESTÁ AQUÍ. Había CINCO copias del mismo envoltorio: `widgetShell`
 * dentro de market.js (53 usos, y solo servía a market.js) y un `shell()`
 * propio en insider.js, watchlist.js, congress.js y community.js -- los tres
 * primeros idénticos byte a byte, el cuarto igual salvo que no escapaba. Mismo
 * patrón ya resuelto cuatro veces en el backend (rsrw_engine, mcclellan,
 * weinstein_phases, time_utils): el duplicado se promueve, no se mantiene.
 *
 * PARA QUÉ SIRVE TENERLO EN UN SITIO. Sin un envoltorio común no existe ningún
 * punto donde pintar los avisos de "este dato no es lo que aparenta", así que
 * cada módulo se lo inventaba -- y a veces se le olvidaba. El caso que lo
 * destapó: insider_service.py, cuando la SEC no responde, sirve el histórico
 * guardado y devuelve el aviso ya redactado ("puede faltar lo más reciente").
 * El frontend nunca lo leía, así que el usuario veía una pantalla que parecía
 * completa. Con el envoltorio compartido, avisar es lo que pasa por defecto y
 * hay que esforzarse para NO hacerlo.
 */

const AVISO_ESTILOS = {
    // El dato es correcto pero no es de ahora (cortos de hace dos semanas,
    // beneficios de hace dos trimestres). Línea fina, sin alarmismo.
    antiguo: { fondo: 'transparent',            borde: 'var(--color-border)', color: 'var(--color-muted)', marca: '' },
    // El dato está incompleto o viene de un respaldo. Tiene que verse.
    parcial: { fondo: 'rgba(255,184,0,0.07)',   borde: '#ffb80033',           color: '#ffb800',            marca: '⚠ ' },
};

/**
 * Banda de avisos: `[{ tipo, mensaje }]`. Un `tipo` desconocido se pinta como
 * `parcial` a propósito -- ante la duda, un aviso se ve de más antes que
 * desaparecer sin que nadie se entere, que es justo el fallo que originó esto.
 */
export function avisosBanda(avisos) {
    if (!Array.isArray(avisos) || !avisos.length) return '';
    return avisos.filter(a => a && a.mensaje).map(a => {
        const e = AVISO_ESTILOS[a.tipo] || AVISO_ESTILOS.parcial;
        return '<div style="background:' + e.fondo + ';border-bottom:1px solid ' + e.borde
            + ';padding:7px 14px;color:' + e.color + ';font-size:11px;line-height:1.45;flex-shrink:0;">'
            + e.marca + esc(a.mensaje) + '</div>';
    }).join('');
}

/**
 * Envoltorio de widget. Dos variantes, que son las dos que ya existían:
 *
 *   'panel'   — market.js: ocupa el alto de su celda de rejilla, contenido con
 *               scroll propio y pie de "Actualizado:". No escapa el título,
 *               porque le llega HTML (el icono de tooltip de tt()).
 *   'tarjeta' — el resto: se apila con margen inferior, sin scroll ni pie.
 *
 * `avisos` se pinta entre la cabecera y el contenido, fuera del área con
 * scroll: en el camino de los ojos hacia el dato, no escondido en un tooltip
 * ni en un pie que nadie lee.
 */
export function panel({ titulo = '', subtitulo = '', contenido = '', timestamp = null,
                        avisos = null, variante = 'tarjeta', escapar = true } = {}) {
    const esPanel = variante === 'panel';
    const t = escapar ? esc(titulo)    : titulo;
    const s = escapar ? esc(subtitulo) : subtitulo;
    const caja = esPanel
        ? 'height:100%;display:flex;flex-direction:column;'
        : 'margin-bottom:1rem;';
    const sub = esPanel
        ? '<div style="color:var(--color-muted);font-size:11px;">' + s + '</div>'
        : (subtitulo ? '<div style="color:var(--color-muted);font-size:10px;">' + s + '</div>' : '');
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;' + caja + '">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);' + (esPanel ? 'flex-shrink:0;' : '') + '">'
        + '<div style="color:var(--color-accent);font-size:' + (esPanel ? '13' : '12') + 'px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + t + '</div>'
        + sub
        + '</div>'
        + avisosBanda(avisos)
        + (esPanel ? '<div style="flex:1;overflow-y:auto;">' + contenido + '</div>' : contenido)
        + (esPanel && timestamp
            ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);flex-shrink:0;">Actualizado: ' + timestamp + '</div>'
            : '')
        + '</div>';
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

/**
 * Carga Chart.js bajo demanda y ejecuta `cb` cuando está listo. Vivía como
 * `_loadChartJsThen` dentro de market.js; se promueve aquí al aparecer el
 * segundo consumidor (el gráfico de sesgo diario de Options Flow), mismo
 * criterio que ya se siguió con esc()/errorMessage(): la segunda copia es el
 * momento de compartir, no la quinta.
 *
 * Se carga aquí y no en index.html a propósito: la mayoría de páginas de la
 * terminal no tienen ningún gráfico y no deben pagar ~250 KB por si acaso.
 */
export function cargarChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const script  = document.createElement('script');
    script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    script.onload = cb;
    document.head.appendChild(script);
}
