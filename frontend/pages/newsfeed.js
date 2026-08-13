import { authHeader } from '/core/api.js';
import { tt } from '/components/tooltip.js';
import { errorMessage, esc, safeUrl } from '/core/ui.js';

// 'ALL' va PRIMERO y existe de verdad: el estado inicial ya era activeSector
// = 'ALL', pero no habia ningun boton con ese valor, asi que al pulsar
// cualquier sector no habia forma de volver a verlos todos sin recargar la
// pagina. Ver auditoria de Newsfeed, #6.
const SECTORS = ['ALL','GENERAL','TECH','FINANCE','ENERGY','HEALTH','MACRO','CRYPTO','POLICY','DEFENSE'];
const IMPACTS = ['ALL','HIGH','MED','LOW'];

let activeImpact = 'ALL';
let activeSector = 'ALL';
let activeSource = null;   // id de fuente, null = todas
let busqueda     = '';
let busquedaTimer = null;
let refreshTimer = null;
let countdownTimer = null;
let secondsLeft = 300;
let cachedData = null;

export async function render(container) {
    container.innerHTML =
        // Header
        '<div style="margin-bottom:1.5rem;">'
        + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);">NEWS FEED</div>'
        + '<div id="refresh-countdown" style="color:var(--color-muted);font-size:10px;padding:2px 8px;border:1px solid var(--color-border);border-radius:3px;font-family:var(--font-mono);">↻ 5:00</div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">RSS + Finnhub · Clasificación automática · Auto-refresh 5min</div>'
        + '</div>'

        // Ticker precios
        + '<div id="prices-bar" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;margin-bottom:1rem;display:flex;gap:1.5rem;overflow-x:auto;flex-wrap:nowrap;">'
        + '<span style="color:var(--color-muted);font-size:11px;">Cargando precios...</span>'
        + '</div>'

        // Filtros impacto
        + '<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;align-items:center;">'
        + IMPACTS.map(i => '<button class="impact-btn" data-impact="' + i + '" style="'
            + 'background:' + (i === activeImpact ? impactColor(i) : 'var(--color-surface)') + ';'
            + 'color:' + (i === activeImpact ? '#000' : 'var(--color-muted)') + ';'
            + 'border:1px solid ' + impactColor(i) + ';border-radius:var(--radius);padding:4px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;letter-spacing:0.05em;">'
            + i + '</button>').join('')
        + '<div style="flex:1;"></div>'
        + SECTORS.map(s => '<button class="sector-btn" data-sector="' + s + '" style="'
            + 'background:' + (s === activeSector ? 'var(--color-secondary)' : 'var(--color-surface)') + ';'
            + 'color:' + (s === activeSector ? '#000' : 'var(--color-muted)') + ';'
            + 'border:1px solid var(--color-border);border-radius:var(--radius);padding:4px 10px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">'
            + s + '</button>').join('')
        + '</div>'

        // Buscador
        + '<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">'
        + '<input id="news-buscar" type="search" placeholder="Buscar en titulares, descripciones y tickers..." '
        + 'style="flex:1;min-width:0;background:var(--color-surface);border:1px solid var(--color-border);'
        + 'border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;">'
        + '<span id="news-buscar-estado" style="color:var(--color-muted);font-size:10px;white-space:nowrap;"></span>'
        + '</div>'

        // Stats + source health
        + '<div id="news-stats" style="margin-bottom:8px;"></div>'
        + '<div id="source-health" style="margin-bottom:1rem;"></div>'

        // Layout: feed principal + panel Trump
        + '<div id="newsfeed-grid" style="display:grid;grid-template-columns:1fr 340px;gap:1rem;align-items:start;">'

        // Feed principal
        + '<div id="news-feed"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando noticias...</div></div>'

        // Panel Trump / Truth Social
        + '<div>'
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;position:sticky;top:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:8px;">'
        + '<div style="width:8px;height:8px;border-radius:50%;background:#e2231a;flex-shrink:0;"></div>'
        + '<div style="color:#e2231a;font-size:12px;letter-spacing:0.08em;font-family:var(--font-mono);">TRUTH SOCIAL ' + tt('trump-truth-social') + '</div>'
        + '</div>'
        + '<div style="padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">Trump · @realDonaldTrump · trumpstruth.org</div>'
        + '<div id="trump-feed" style="max-height:600px;overflow-y:auto;">Cargando...</div>'
        + '</div>'
        + '</div>'

        + '</div>';

    // Event listeners filtros
    container.querySelectorAll('.impact-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeImpact = btn.getAttribute('data-impact');
            updateFilterStyles(container);
            loadNews(container);   // el backend filtra sobre TODO, no sobre los 80 bajados
        });
    });
    container.querySelectorAll('.sector-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeSector = btn.getAttribute('data-sector');
            updateFilterStyles(container);
            loadNews(container);
        });
    });

    // Buscador. El texto viaja al backend igual que impacto y sector, no se
    // filtra aquí: el backend recorta a `limit` DESPUÉS de filtrar, así que
    // buscar sobre lo ya descargado dejaría fuera noticias que sí existen --
    // es el mismo error que se corrigió con el filtro de impacto (#7).
    //
    // 350ms de espera antes de pedir: sin ellos, escribir "tesla" son cinco
    // peticiones y las respuestas pueden llegar desordenadas, dejando en
    // pantalla el resultado de "tesl".
    const inputBuscar = container.querySelector('#news-buscar');
    if (inputBuscar) {
        inputBuscar.addEventListener('input', () => {
            clearTimeout(busquedaTimer);
            busquedaTimer = setTimeout(() => {
                busqueda = inputBuscar.value.trim();
                loadNews(container);
            }, 350);
        });
    }

    // Carga inicial
    loadPrices(container.querySelector('#prices-bar'));
    await loadNews(container);
    loadTrump(container.querySelector('#trump-feed'));

    // Auto-refresh cada 5 minutos
    startAutoRefresh(container);
}

// ── AUTO-REFRESH ──────────────────────────────────────────────────────────────

// Llamado por el router justo antes de destruir el contenedor de esta
// página (navegación real fuera de Newsfeed) -- sin esto, los dos timers
// seguían disparando peticiones y repintando el contador para siempre.
export function cleanup() {
    if (refreshTimer)   clearInterval(refreshTimer);
    if (countdownTimer) clearInterval(countdownTimer);
    if (busquedaTimer)  clearTimeout(busquedaTimer);
    refreshTimer = null;
    countdownTimer = null;
    busquedaTimer = null;
    // Estas dos viven en el módulo, así que sobreviven a salir de la página.
    // El campo de búsqueda, en cambio, se vuelve a pintar vacío al volver: sin
    // resetear, se volvería a un feed filtrado con la caja de búsqueda en
    // blanco y nada que explicara por qué faltan noticias.
    busqueda = '';
    activeSource = null;
}

function startAutoRefresh(container) {
    if (refreshTimer)  clearInterval(refreshTimer);
    if (countdownTimer) clearInterval(countdownTimer);

    secondsLeft = 300;
    updateCountdown(container);

    countdownTimer = setInterval(() => {
        secondsLeft--;
        updateCountdown(container);
        if (secondsLeft <= 0) secondsLeft = 300;
    }, 1000);

    refreshTimer = setInterval(async () => {
        secondsLeft = 300;
        await loadNews(container, { silencioso: true });
        loadTrump(container.querySelector('#trump-feed'));
    }, 300000); // 5 minutos
}

function updateCountdown(container) {
    const el = container.querySelector('#refresh-countdown');
    if (!el) return;
    const m = Math.floor(secondsLeft / 60);
    const s = secondsLeft % 60;
    el.textContent = '↻ ' + m + ':' + String(s).padStart(2, '0');
    el.style.color = secondsLeft < 60 ? 'var(--color-accent)' : 'var(--color-muted)';
}

// ── NEWS PRINCIPAL ────────────────────────────────────────────────────────────

// silencioso: no pinta el "Cargando..." ni mueve el scroll. Es lo que quiere
// el refresco automatico cada 5 minutos -- el placeholder colapsa la lista
// entera, la pagina se queda de golpe sin altura y el scroll salta arriba, en
// mitad de lo que estabas leyendo. En una carga normal o al cambiar de filtro
// SI se pinta, porque ahi el contenido cambia de verdad y sin aviso pareceria
// que la pagina se ha quedado colgada. Ver auditoria de Newsfeed, #8.
async function loadNews(container, { silencioso = false } = {}) {
    const feed  = container.querySelector('#news-feed');
    const stats = container.querySelector('#news-stats');
    const health = container.querySelector('#source-health');
    const scrollPrevio = window.scrollY;
    if (feed && !silencioso) feed.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div>';

    try {
        // El filtro viaja al backend. Antes se bajaban siempre los 80 mas
        // recientes y se filtraban en el navegador, pero el backend filtra
        // ANTES de recortar, asi que filtrar aqui deja fuera noticias que si
        // existen. Medido el 08/08 con 120 noticias en el ciclo: pedir HIGH
        // enseñaba 9 de las 22 que habia -- se perdian 13 de alto impacto,
        // que es justo el filtro que mas importa. Ver auditoria, #7.
        const q = new URLSearchParams({ limit: '80' });
        if (activeImpact !== 'ALL') q.set('impact', activeImpact);
        if (activeSector !== 'ALL') q.set('sector', activeSector);
        if (activeSource)           q.set('source', activeSource);
        if (busqueda)               q.set('q', busqueda.slice(0, 80));
        const res   = await fetch('/api/v1/newsfeed/?' + q, {
            headers: authHeader()
        });
        const data  = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        cachedData = data;

        // Stats
        if (stats) {
            const s = data.stats;
            stats.innerHTML = '<div style="display:flex;gap:1rem;font-size:11px;flex-wrap:wrap;">'
                + '<span style="color:var(--color-muted);">Total: <b style="color:var(--color-text);">' + data.total + '</b></span>'
                + '<span style="color:#f23645;">● HIGH: <b>' + s.high + '</b></span>'
                + '<span style="color:#ffb800;">● MED: <b>' + s.med + '</b></span>'
                + '<span style="color:var(--color-muted);">● LOW: <b>' + s.low + '</b></span>'
                + '<span style="color:var(--color-accent);">▲ Alcista: <b>' + s.bullish + '</b></span>'
                + '<span style="color:#f23645;">▼ Bajista: <b>' + s.bearish + '</b></span>'
                + '<span style="color:var(--color-muted);margin-left:auto;font-size:10px;">Actualizado: ' + data.timestamp + '</span>'
                + '</div>';
        }

        // Fuentes: estado (verde/gris) Y filtro. Antes el clic abría la web de
        // la fuente en otra pestaña; ese enlace ya está en cada noticia (el
        // nombre de la fuente bajo el titular), así que el clic aquí se dedica
        // a lo que no se podía hacer de ninguna otra forma: ver solo esa
        // fuente.
        //
        // El chip TODAS no es decorativo. Volver a ver el feed completo se
        // podía hacer desde el principio -- pulsando otra vez la fuente ya
        // activa, y el código lo hacía bien -- pero eso no lo dice nada en
        // pantalla: quien filtra por una fuente se queda encerrado sin ver la
        // salida. Es el MISMO fallo que el #6 de esta auditoría ("no hay botón
        // ALL para sectores"), que se arregló para sectores y para impacto con
        // una entrada 'ALL' explícita, y que aquí se quedó sin arreglar porque
        // la barra de fuentes se construye aparte. Reportado usándolo, 13/08.
        // Se conserva además el toggle sobre la fuente activa: quien ya lo
        // conocía no pierde el atajo.
        if (health && data.sources) {
            const active  = data.sources.filter(s => s.ok).length;
            const total   = data.sources.length;
            const todasSel = !activeSource;
            health.innerHTML = '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">'
                + '<span style="color:var(--color-muted);font-size:10px;">Fuentes activas: <b style="color:var(--color-accent);">' + active + '/' + total + '</b></span>'
                + '<span class="source-chip" data-source="" title="Ver las noticias de todas las fuentes"'
                + ' style="color:' + (todasSel ? '#000' : 'var(--color-accent)')
                + ';background:' + (todasSel ? 'var(--color-accent)' : 'transparent')
                + ';font-size:9px;padding:1px 5px;border:1px solid var(--color-accent)' + (todasSel ? '' : '33')
                + ';border-radius:2px;cursor:pointer;font-weight:700;">TODAS</span>'
                + data.sources.map(s => {
                    const sel   = s.id === activeSource;
                    const color = s.ok ? 'var(--color-accent)' : '#444';
                    return '<span class="source-chip" data-source="' + esc(s.id) + '" title="'
                        + (sel ? 'Quitar el filtro y ver todas las fuentes' : 'Ver solo ' + esc(s.label))
                        + '" style="color:' + (sel ? '#000' : color) + ';background:' + (sel ? color : 'transparent')
                        + ';font-size:9px;padding:1px 5px;border:1px solid ' + color + (sel ? '' : '33')
                        + ';border-radius:2px;cursor:pointer;">' + esc(s.label) + '</span>';
                }).join('')
                + (activeSource ? '<span style="color:var(--color-muted);font-size:10px;">· filtrando por fuente</span>' : '')
                + '</div>';

            health.querySelectorAll('.source-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    const id = chip.getAttribute('data-source');
                    // data-source vacío = el chip TODAS: quita el filtro pase
                    // lo que pase, sin depender de cuál esté activa ahora.
                    activeSource = !id ? null : (activeSource === id ? null : id);
                    loadNews(container);
                });
            });
        }

        // Cuántas quedan tras los filtros, sobre el total del ciclo. Sin esto,
        // buscar algo que no existe y quedarse sin resultados es indistinguible
        // de que el feed se haya roto.
        const estado = container.querySelector('#news-buscar-estado');
        if (estado) {
            const filtrando = busqueda || activeSource || activeImpact !== 'ALL' || activeSector !== 'ALL';
            const n = data.filtrados != null ? data.filtrados : data.items.length;
            estado.textContent = filtrando ? n + ' de ' + data.total : '';
        }

        renderFeedFromCache(container);
        // La lista nueva puede tener otra altura (una noticia mas, una menos),
        // asi que se restaura la posicion en vez de darla por intacta.
        if (silencioso) window.scrollTo({ top: scrollPrevio });

    } catch(e) {
        if (feed) feed.innerHTML = errorMessage(e.message);
    }
}

// 999 no es una edad: es el centinela que pone el backend cuando la noticia
// llega SIN fecha de publicacion. Se pintaba con la misma formula que las
// demas y salia un "16h" perfectamente creible (999 min = 16,6 h), asi que
// una noticia de antiguedad desconocida se presentaba como si se supiera.
// Ahora se dice que no se sabe. Ver auditoria de Newsfeed, #9.
const SIN_FECHA = 999;

function edadTexto(mins) {
    if (mins == null || mins === SIN_FECHA) return '—';
    if (mins < 60)   return mins + 'm';
    if (mins < 1440) return Math.floor(mins / 60) + 'h';
    return Math.floor(mins / 1440) + 'd';
}

function renderFeedFromCache(container) {
    const feed = container.querySelector('#news-feed');
    if (!feed || !cachedData) return;

    let items = cachedData.items || [];

    // Sin filtrar aqui: los items ya vienen filtrados del backend (ver
    // loadNews). Volver a filtrarlos no cambiaria nada y esconderia de
    // donde sale el recorte real.

    if (!items.length) {
        feed.innerHTML = '<div style="padding:2rem;color:var(--color-muted);font-size:12px;text-align:center;">No hay noticias con los filtros seleccionados.</div>';
        return;
    }
    feed.innerHTML = items.map(item => newsCard(item)).join('');
}

// Los símbolos que el backend haya reconocido en el titular, enlazados a
// Research. La mayoría de noticias no llevan ninguno (los titulares nombran a
// las empresas por su nombre, no por su símbolo) y entonces esto no pinta
// nada: es un atajo cuando aparece, no una columna que rellenar.
//
// `encodeURIComponent` y no solo esc(): el ticker acaba dentro de una URL, y
// ahí escapar entidades HTML no basta -- un valor con `&` o `#` cortaría la
// query. El backend ya solo devuelve símbolos de 1-5 letras, pero esto no
// depende de eso.
function tickerChips(tickers) {
    if (!tickers || !tickers.length) return '';
    return tickers.map(t =>
        '<a href="/research?ticker=' + encodeURIComponent(t) + '" '
        + 'onclick="event.preventDefault();window.__navigate(\'/research?ticker=' + encodeURIComponent(t) + '\')" '
        + 'title="Ver ' + esc(t) + ' en Research" '
        + 'style="color:var(--color-accent);font-size:10px;padding:1px 6px;border:1px solid var(--color-accent)33;'
        + 'border-radius:3px;text-decoration:none;cursor:pointer;">' + esc(t) + '</a>'
    ).join('');
}

function newsCard(item) {
    const ic = impactColor(item.impact);
    const sc = sentimentColor(item.sentiment);
    const timeStr = edadTexto(item.mins_ago);

    // Badge especial para Finnhub
    const isFinnhub = item.source_id === 'finnhub';
    const sourceBadge = item.source_url
        ? '<a href="' + safeUrl(item.source_url) + '" target="_blank" style="color:' + (isFinnhub ? 'var(--color-secondary)' : 'var(--color-muted)') + ';font-size:10px;text-decoration:none;" title="Ir a ' + esc(item.source) + '">'
          + (isFinnhub ? '★ ' : '') + esc(item.source) + '</a>'
        : '<span style="color:var(--color-muted);font-size:10px;">' + esc(item.source) + '</span>';

    return '<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--color-border);align-items:flex-start;">'
        + '<div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;padding-top:2px;">'
        + '<div style="width:3px;height:32px;background:' + ic + ';border-radius:2px;"></div>'
        + '</div>'
        + '<div style="flex:1;min-width:0;">'
        + '<a href="' + safeUrl(item.url) + '" target="_blank" rel="noopener" style="color:var(--color-text);font-size:13px;line-height:1.4;display:block;margin-bottom:4px;text-decoration:none;" onmouseover="this.style.color=\'var(--color-accent)\'" onmouseout="this.style.color=\'var(--color-text)\'">'
        + esc(item.title)
        + '</a>'
        + (item.desc ? '<div style="color:var(--color-muted);font-size:11px;line-height:1.4;margin-bottom:4px;">' + esc(item.desc.substring(0, 120)) + '...</div>' : '')
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        + '<span style="color:' + ic + ';font-size:10px;border:1px solid ' + ic + '33;padding:1px 6px;border-radius:3px;">' + item.impact + '</span>'
        + '<span style="color:' + sc + ';font-size:10px;">' + sentimentIcon(item.sentiment) + ' ' + item.sentiment + '</span>'
        + '<span style="color:var(--color-secondary);font-size:10px;padding:1px 6px;background:rgba(0,217,255,0.08);border-radius:3px;">' + esc(item.sector) + '</span>'
        + tickerChips(item.tickers)
        + sourceBadge
        + '<span style="color:var(--color-muted);font-size:10px;margin-left:auto;">' + timeStr + '</span>'
        + '</div>'
        + '</div>'
        + '</div>';
}

// ── TRUMP FEED ────────────────────────────────────────────────────────────────

async function loadTrump(el) {
    if (!el) return;
    try {
        const res   = await fetch('/api/v1/newsfeed/trump?limit=15', {
            headers: authHeader()
        });
        const data  = await res.json();

        if (!data.ok || !data.posts.length) {
            el.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:11px;">Sin posts disponibles.</div>';
            return;
        }

        el.innerHTML = data.posts.map(post => trumpCard(post)).join('')
            + '<div style="padding:8px 14px;font-size:10px;color:#555;border-top:1px solid var(--color-border);">Fuente: ' + data.source + '</div>';

    } catch(e) {
        el.innerHTML = errorMessage(e.message, {fontSize: '11px'});
    }
}

function trumpCard(post) {
    const timeStr = edadTexto(post.mins_ago);
    const ic     = impactColor(post.impact);
    const text   = post.content || post.title || '';
    const isHigh = post.impact === 'HIGH';

    return '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);'
        + (isHigh ? 'background:rgba(242,54,69,0.04);' : '') + '">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<div style="display:flex;gap:6px;align-items:center;">'
        + (isHigh ? '<span style="color:#f23645;font-size:9px;border:1px solid #f2364544;padding:1px 5px;border-radius:2px;">HIGH IMPACT</span>' : '')
        + '<span style="color:var(--color-secondary);font-size:9px;padding:1px 5px;background:rgba(0,217,255,0.08);border-radius:2px;">' + esc(post.sector) + '</span>'
        + '</div>'
        + '<span style="color:var(--color-muted);font-size:10px;">' + timeStr + '</span>'
        + '</div>'
        + '<div style="color:var(--color-text);font-size:12px;line-height:1.5;margin-bottom:6px;">' + esc(text.substring(0, 280)) + (text.length > 280 ? '...' : '') + '</div>'
        + (post.url ? '<a href="' + safeUrl(post.url) + '" target="_blank" rel="noopener" style="color:var(--color-muted);font-size:10px;text-decoration:none;" onmouseover="this.style.color=\'#e2231a\'" onmouseout="this.style.color=\'var(--color-muted)\'">Ver post original ↗</a>' : '')
        + '</div>';
}

// ── PRICES ────────────────────────────────────────────────────────────────────

async function loadPrices(el) {
    try {
        const res   = await fetch('/api/v1/newsfeed/prices', {
            headers: authHeader()
        });
        const data  = await res.json();
        el.innerHTML = data.map(p => {
            const up    = p.chg >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            return '<div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
                + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + p.name + '</div>'
                + '<div style="color:var(--color-text);font-size:12px;">' + p.price.toLocaleString('en-US') + '</div>'
                + '<div style="color:' + color + ';font-size:10px;">' + (up ? '+' : '') + p.chg.toFixed(2) + '%</div>'
                + '</div>';
        }).join('<div style="width:1px;background:var(--color-border);flex-shrink:0;"></div>');
    } catch(e) {
        el.innerHTML = '<span style="color:var(--color-muted);font-size:11px;">Sin precios</span>';
    }
}

// ── UTILS ─────────────────────────────────────────────────────────────────────

function updateFilterStyles(container) {
    container.querySelectorAll('.impact-btn').forEach(btn => {
        const i = btn.getAttribute('data-impact');
        const active = i === activeImpact;
        btn.style.background = active ? impactColor(i) : 'var(--color-surface)';
        btn.style.color      = active ? '#000' : 'var(--color-muted)';
    });
    container.querySelectorAll('.sector-btn').forEach(btn => {
        const s = btn.getAttribute('data-sector');
        const active = s === activeSector;
        btn.style.background = active ? 'var(--color-secondary)' : 'var(--color-surface)';
        btn.style.color      = active ? '#000' : 'var(--color-muted)';
    });
}

function impactColor(impact) {
    if (impact === 'HIGH') return '#f23645';
    if (impact === 'MED')  return '#ffb800';
    return 'var(--color-muted)';
}

function sentimentColor(s) {
    if (s === 'bullish') return 'var(--color-accent)';
    if (s === 'bearish') return '#f23645';
    return 'var(--color-muted)';
}

function sentimentIcon(s) {
    if (s === 'bullish') return '▲';
    if (s === 'bearish') return '▼';
    return '—';
}