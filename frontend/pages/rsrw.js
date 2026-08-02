import { tt } from '/components/tooltip.js';
import { isRateLimitMessage, errorMessage, esc } from '/core/ui.js';


// Gráficos vivos de Chart.js de esta página. Se destruyen desde cleanup(),
// que el router llama antes de tirar el contenedor (frontend/core/router.js,
// convención de la sesión 3), y al empezar cada análisis nuevo.
//
// Es el MISMO fallo que se corrigió en Market en la sesión 3 y en Research el
// 29/07/2026 (a1a0931): el gráfico se creaba y no se destruía nunca, ni al
// navegar fuera ni al volver a renderizar. RS/RW se quedó sin enganchar las
// dos veces. Ver auditoría RS/RW, #9.
//
// Se guardan las INSTANCIAS, no los ids -- y esa diferencia es la que hace que
// esto funcione. Chart.getChart(id) resuelve el id a través del DOM
// (document.getElementById por dentro), pero doAnalyze() vacía el contenedor
// con el mensaje "Calculando..." ANTES del fetch, así que para cuando toca
// limpiar el canvas anterior ya no está en el documento y getChart devuelve
// undefined -- el gráfico seguía vivo y huérfano. Verificado en navegador
// el 30/07/2026: con el registro por id quedaba 1 instancia huérfana por cada
// ticker analizado.
let _rsrwCharts = [];

function _destruirGraficos() {
    _rsrwCharts.forEach(c => { try { c.destroy(); } catch (_) {} });
    _rsrwCharts = [];
}

export function cleanup() {
    _destruirGraficos();
}

export async function render(container) {
    container.innerHTML = pageHeader()
        + '<div id="rsrw-sectors" style="margin-bottom:1.5rem;"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
        + '<div id="rsrw-leaders"></div>'
        + '<div id="rsrw-laggards"></div>'
        + '</div>'
        + '<div id="rsrw-cartera" style="margin-bottom:1.5rem;"></div>'
        + '<div id="rsrw-movimientos" style="margin-bottom:1.5rem;"></div>'
        + tickerPanel()
        + '<div id="rsrw-ticker-result"></div>';

    setupTicker(container);
    loadGist(container);
    loadCartera(container);
    loadMovimientos(container);
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RS/RW SCANNER ' + tt('rsrw') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Relative Strength · Relative Weakness · IBD Methodology · S&amp;P 500 completo (503 tickers) · Scan nocturno automático, sin scan on-demand</div>'
        + '</div>';
}

function tickerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS RS/RW INDIVIDUAL ' + tt('rs-rating') + '</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<input id="rsrw-ticker-input" type="text" placeholder="NVDA, AAPL, TSLA..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="rsrw-ticker-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ANALIZAR</button>'
        + '</div>'
        + '</div>';
}

async function loadGist(container) {
    const leadersEl  = container.querySelector('#rsrw-leaders');
    const laggardsEl = container.querySelector('#rsrw-laggards');
    const sectorsEl  = container.querySelector('#rsrw-sectors');

    if (leadersEl)  leadersEl.innerHTML  = loadingCard('LÍDERES RS');
    if (laggardsEl) laggardsEl.innerHTML = loadingCard('REZAGADOS RW');
    if (sectorsEl)  sectorsEl.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Cargando sectores...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/rsrw/gist', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data  = await res.json();

        if (!data.ok) {
            if (leadersEl)  leadersEl.innerHTML  = errorCard('LÍDERES RS', data.error);
            if (laggardsEl) laggardsEl.innerHTML = errorCard('REZAGADOS RW', data.error);
            return;
        }

        renderSectors(sectorsEl, data.sectors);
        renderTable(leadersEl, 'LÍDERES RS', data.leaders, true, data.freshness, data.total, 'leaders');
        renderTable(laggardsEl, 'REZAGADOS RW', data.laggards, false, data.freshness, data.total, 'laggards');

    } catch(e) {
        if (leadersEl)  leadersEl.innerHTML  = errorCard('LÍDERES RS', e.message);
        if (laggardsEl) laggardsEl.innerHTML = errorCard('REZAGADOS RW', e.message);
    }
}

// ── Fuerza relativa de tus posiciones ────────────────────────────────────────
//
// El scan nocturno recorre el S&P 500, y dos tercios de la cartera no están en
// el índice — así que la herramienta que mide fuerza relativa no decía nada de
// la mayoría de lo que hay comprado de verdad. Esta sección lo cubre.
//
// El percentil se calcula CONTRA el S&P 500, sin que estos valores formen
// parte de él: ampliar el universo cambiaría la vara de medir para todos.

async function loadCartera(container) {
    const el = container.querySelector('#rsrw-cartera');
    if (!el) return;
    el.innerHTML = loadingCard('TUS POSICIONES · FUERZA RELATIVA');
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/rsrw/cartera', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data = await res.json();
        if (!data.ok) {
            el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
                + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:6px;">TUS POSICIONES · FUERZA RELATIVA</div>'
                + '<div style="color:var(--color-muted);font-size:11px;">' + esc(data.error || 'Sin datos.') + '</div></div>';
            return;
        }
        el.innerHTML = renderCartera(data);
    } catch (e) {
        el.innerHTML = errorCard('TUS POSICIONES · FUERZA RELATIVA', e.message);
    }
}

function renderCartera(d) {
    const colorPct = (p) => p == null ? 'var(--color-muted)'
        : p >= 80 ? 'var(--color-accent)' : p <= 20 ? '#f23645' : '#ffb800';

    const filas = d.filas.map(f => {
        const mom = f.rs_mom ? '<span title="El ritmo reciente supera al de medio plazo" style="color:var(--color-accent);">▲</span>'
                             : '<span title="El ritmo reciente NO supera al de medio plazo" style="color:var(--color-muted);">·</span>';
        // Marcar los que no forman parte del índice: su percentil se calcula
        // contra el S&P 500 pero no compiten dentro de él, y decirlo evita que
        // alguien lo lea como "está entre las 500 mayores de EE.UU.".
        const fuera = f.en_indice ? ''
            : '<span title="No forma parte del S&P 500 — su percentil se calcula contra el índice, no dentro de él" style="color:var(--color-muted);font-size:9px;margin-left:4px;">ext</span>';
        const star = f.in_watchlist ? '<span title="En tu Watchlist" style="font-size:10px;">⭐</span>' : '';
        return '<div style="display:grid;grid-template-columns:1fr 54px 70px 70px 70px 24px;gap:6px;padding:5px 12px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span class="ticker-link" onclick="window.__navigate(\'/research?ticker=' + esc(f.ticker) + '\')" style="color:var(--color-accent);cursor:pointer;">' + esc(f.ticker) + star + fuera + '</span>'
            + '<span style="color:' + colorPct(f.rs_pct) + ';text-align:right;font-weight:500;">' + (f.rs_pct == null ? '—' : esc(f.rs_pct)) + '</span>'
            + '<span style="color:var(--color-muted);text-align:right;">' + esc(f.rs_21d) + '</span>'
            + '<span style="color:var(--color-muted);text-align:right;">' + esc(f.rs_63d) + '</span>'
            + '<span style="color:var(--color-muted);text-align:right;">' + esc(f.rs_126d) + '</span>'
            + '<span style="text-align:center;">' + mom + '</span>'
            + '</div>';
    }).join('');

    // Los que no se pudieron calcular se NOMBRAN. Omitirlos dejaría al usuario
    // creyendo que esa posición no tiene fuerza relativa, cuando lo que pasa
    // es que no hay histórico suficiente para medirla.
    const sinDatos = (d.sin_datos && d.sin_datos.length)
        ? '<div style="padding:7px 12px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;">'
          + 'Sin histórico suficiente para calcular su RS (hacen falta 63 sesiones): '
          + d.sin_datos.map(t => esc(t)).join(', ') + '</div>'
        : '';

    return '<div>'
        + '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">TUS POSICIONES · FUERZA RELATIVA ' + tt('rsrw-cartera') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">' + esc(d.calculadas) + ' de ' + esc(d.posiciones)
        + ' · ' + esc(d.fuera_indice) + ' fuera del índice · percentil contra ' + esc(d.referencia) + '</div>'
        + '</div>'
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="display:grid;grid-template-columns:1fr 54px 70px 70px 70px 24px;gap:6px;padding:7px 12px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>TICKER</span><span style="text-align:right;">RS%</span><span style="text-align:right;">21D</span>'
        + '<span style="text-align:right;">63D</span><span style="text-align:right;">126D</span><span></span></div>'
        + '<div style="max-height:420px;overflow-y:auto;">' + filas + '</div>'
        + sinDatos
        + '</div></div>';
}

// ── Movimientos del percentil RS ─────────────────────────────────────────────
//
// Las tablas de arriba son una FOTO: un valor con RS 88 aparece igual tanto si
// lleva seis meses ahí como si acaba de llegar desde 65. Esta sección compara
// la foto de hoy con la de hace unas sesiones y separa las dos cosas — que es
// la diferencia entre liderazgo consolidado y liderazgo emergente.
//
// El dato sale de los snapshots que la terminal ya venía guardando cada noche
// sin que nadie los leyera.

async function loadMovimientos(container) {
    const el = container.querySelector('#rsrw-movimientos');
    if (!el) return;
    el.innerHTML = loadingCard('MOVIMIENTOS DEL PERCENTIL RS');
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/rsrw/movimientos?ventana=10', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data = await res.json();
        if (!data.ok) {
            // Con menos de dos sesiones guardadas no hay nada que comparar, y
            // eso NO es un error: es que el histórico acaba de empezar.
            el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
                + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:6px;">MOVIMIENTOS DEL PERCENTIL RS</div>'
                + '<div style="color:var(--color-muted);font-size:11px;line-height:1.6;">' + esc(data.error || 'Sin datos todavía.')
                + ' El histórico se va formando con cada scan nocturno.</div></div>';
            return;
        }
        el.innerHTML = renderMovimientos(data);
    } catch (e) {
        el.innerHTML = errorCard('MOVIMIENTOS DEL PERCENTIL RS', e.message);
    }
}

function renderMovimientos(d) {
    const fila = (m) => {
        const col = m.variacion >= 0 ? 'var(--color-accent)' : '#f23645';
        let mk = '';
        if (m.en_cartera)   mk += '<span title="En Cartera" style="font-size:10px;">💼</span>';
        if (m.in_watchlist) mk += '<span title="En tu Watchlist" style="font-size:10px;">⭐</span>';
        return '<div style="display:grid;grid-template-columns:1fr 62px 16px 62px 60px;gap:6px;padding:5px 12px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span class="ticker-link" onclick="window.__navigate(\'/research?ticker=' + esc(m.ticker) + '\')" style="color:var(--color-accent);cursor:pointer;">' + esc(m.ticker) + mk + '</span>'
            + '<span style="color:var(--color-muted);text-align:right;">' + esc(m.rs_previo) + '</span>'
            + '<span style="color:var(--color-muted);text-align:center;">→</span>'
            + '<span style="color:var(--color-text);text-align:right;">' + esc(m.rs_actual) + '</span>'
            + '<span style="color:' + col + ';text-align:right;">' + (m.variacion >= 0 ? '+' : '') + esc(m.variacion) + '</span>'
            + '</div>';
    };

    const bloque = (titulo, filas, vacio, color) =>
        '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:8px 12px;border-bottom:1px solid var(--color-border);color:' + color + ';font-size:11px;letter-spacing:0.06em;">'
        + esc(titulo) + ' <span style="color:var(--color-muted);">(' + filas.length + ')</span></div>'
        + (filas.length ? filas.map(fila).join('')
            : '<div style="padding:10px 12px;color:var(--color-muted);font-size:11px;">' + esc(vacio) + '</div>')
        + '</div>';

    // La ventana REAL puede ser más corta que la pedida: con pocas sesiones
    // guardadas se compara con lo que hay y se dice cuánto es, en vez de
    // presentar cuatro días como si fueran dos semanas.
    const avisoMuestra = d.fiable ? ''
        : '<div style="background:rgba(255,152,0,.08);border-left:3px solid #ff9800;padding:7px 12px;margin-bottom:10px;">'
          + '<span style="color:#ff9800;font-size:11px;">Solo hay ' + esc(d.sesiones) + ' sesiones guardadas. '
          + 'Con tan poco recorrido, una parte de estos movimientos es ruido: el percentil se mueve también cuando suben los demás. '
          + 'El histórico crece con cada scan nocturno.</span></div>';

    return '<div>'
        + '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">MOVIMIENTOS DEL PERCENTIL RS ' + tt('rsrw-movimientos') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">' + esc(d.desde) + ' → ' + esc(d.hasta)
        + ' · ' + esc(d.sesiones) + ' sesiones · ' + esc(d.comparados) + ' valores</div>'
        + '</div>'
        + avisoMuestra
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + bloque('NUEVOS LÍDERES · cruzan el ' + d.umbral_lider + ' al alza', d.nuevos_lideres,
                 'Ninguno ha entrado en el grupo de líderes en este periodo.', 'var(--color-accent)')
        + bloque('PIERDEN EL LIDERAZGO · caen por debajo del ' + d.umbral_lider, d.lideres_perdidos,
                 'Ninguno ha salido del grupo de líderes en este periodo.', '#f23645')
        + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
        + bloque('LOS QUE MÁS SUBEN', d.mas_suben, 'Sin datos.', 'var(--color-secondary)')
        + bloque('LOS QUE MÁS BAJAN', d.mas_bajan, 'Sin datos.', 'var(--color-secondary)')
        + '</div></div>';
}

function renderSectors(el, sectors) {
    if (!el || !sectors || !sectors.length) return;
    const sorted = [...sectors].sort((a, b) => (b.rs || 0) - (a.rs || 0));
    // Escala FIJA con suelo, no relativa al máximo del día.
    //
    // Antes el denominador era `maxAbs` a secas, así que el sector más extremo
    // llenaba la barra al 100% SIEMPRE: en una sesión de rotación plana, un
    // sector con RS 0,8 se veía idéntico a uno con RS 8 en un día de
    // dispersión fuerte. El número está al lado y no se perdía información,
    // pero la lectura visual —que es para lo que existe una barra— mentía
    // entre días. Ver auditoría RS/RW, #13.
    //
    // El suelo de 12 sale de medir el dato real, no de inventarlo: el 30/07 el
    // rango sectorial iba de 1,16 a 10,66. Con 12, un día normal deja la barra
    // del líder en torno al 85-90% y un día plano se ve corto, que es lo
    // correcto. Si algún día se supera, `Math.max` deja que la escala crezca en
    // vez de desbordar.
    const ESCALA_MIN_RS = 12;
    const maxAbs = Math.max(...sorted.map(s => Math.abs(s.rs || 0)));
    const escala = Math.max(maxAbs, ESCALA_MIN_RS);

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ROTACIÓN SECTORIAL · RS vs SPY ' + tt('rsrw-sector-rotation') + ' <span style="color:var(--color-muted);font-weight:normal;letter-spacing:0;">(blend 21/63/126d, igual que las acciones · barras a escala fija ±' + escala.toFixed(0) + ', comparables entre días)</span></div>'
        + '<div style="display:flex;flex-direction:column;gap:6px;">'
        + '<div style="display:grid;grid-template-columns:140px 1fr 50px 20px 60px;gap:8px;padding-bottom:2px;">'
        + '<div></div><div></div>'
        + '<div style="color:var(--color-muted);font-size:9px;text-align:right;">RS</div>'
        + '<div></div>'
        + '<div style="color:var(--color-muted);font-size:9px;text-align:right;">RET. 3M</div>'
        + '</div>'
        + sorted.map(s => {
            const rs     = s.rs || 0;
            const name   = s.ticker || s.sector || s.index || 'N/A';
            const color  = rs > 0 ? 'var(--color-accent)' : '#f23645';
            const w      = escala > 0 ? Math.abs(rs) / escala * 100 : 0;
            const trendV = s.rs_trend || 0;
            const trend  = trendV > 0.01 ? '▲' : trendV < -0.01 ? '▼' : '→';
            const tColor = trend === '▲' ? 'var(--color-accent)' : trend === '▼' ? '#f23645' : 'var(--color-muted)';
            const ret63  = s.return_63d != null ? ((s.return_63d >= 0 ? '+' : '') + s.return_63d.toFixed(1) + '%') : '';
            return '<div style="display:grid;grid-template-columns:140px 1fr 50px 20px 60px;gap:8px;align-items:center;">'
                + '<div style="font-size:11px;color:var(--color-muted);">' + esc(name) + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:5px;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '<div style="color:' + color + ';font-size:11px;text-align:right;">' + rs.toFixed(2) + '</div>'
                + '<div style="color:' + tColor + ';font-size:11px;">' + trend + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;text-align:right;">' + ret63 + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '<div style="margin-top:0.75rem;padding-top:0.6rem;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:9.5px;line-height:1.5;">'
        + 'La barra/número es el <b style="color:var(--color-text);">nivel</b> (RS combinada 1/3/6 meses vs SPY) — la flecha es la <b style="color:var(--color-text);">tendencia reciente</b> de la componente de 3 meses en las últimas ~4 semanas, son cosas distintas. RET. 3M es el retorno propio del sector en 3 meses, sin comparar con nada. '
        + 'Un sector en rojo con ▲ sigue por debajo de SPY en el combinado, pero está mejorando últimamente — posible rotación temprana.'
        + '</div>'
        + '</div>';
}

let _rsrwTables = { leaders: { el: null, rows: [], title: '', color: '', freshness: null, total: 0 },
                     laggards: { el: null, rows: [], title: '', color: '', freshness: null, total: 0 } };
let _rsrwSort = { leaders: { key: 'rs_pct', dir: -1 }, laggards: { key: 'rs_pct', dir: 1 } };

function sortRsrwRows(rows, sortState) {
    const { key, dir } = sortState;
    return [...rows].sort((a, b) => {
        let av = a[key], bv = b[key];
        if (typeof av === 'string') { av = (av || '').toLowerCase(); bv = (bv || '').toLowerCase(); }
        else { av = av == null ? -Infinity : av; bv = bv == null ? -Infinity : bv; }
        if (av < bv) return -1 * dir;
        if (av > bv) return  1 * dir;
        return 0;
    });
}

function rsrwSortArrow(tableId, key) {
    const s = _rsrwSort[tableId];
    if (!s || s.key !== key) return '';
    return s.dir === 1 ? ' ▲' : ' ▼';
}

window.__rsrwSort = function(tableId, key) {
    const s = _rsrwSort[tableId];
    if (!s) return;
    if (s.key === key) s.dir *= -1;
    else { s.key = key; s.dir = -1; }
    const t = _rsrwTables[tableId];
    if (t && t.el) renderTable(t.el, t.title, t.rows, t.color === 'var(--color-accent)', t.freshness, t.total, tableId);
};

function renderTable(el, title, rows, isLeaders, freshness, total, tableId) {
    if (!el) return;
    const color = isLeaders ? 'var(--color-accent)' : '#f23645';

    // Guardar estado para poder reordenar sin volver a pedir datos
    _rsrwTables[tableId] = { el, rows: rows || [], title, color, freshness, total };
    const sortState = _rsrwSort[tableId];
    const sortedRows = sortRsrwRows(rows || [], sortState);

    const cols = [
        { label: 'TICKER', key: 'ticker' },
        { label: 'RS%', key: 'rs_pct', tt: 'rs-rating' },
        { label: '21d', key: 'rs_21d' },
        { label: '63d', key: 'rs_63d' },
        { label: '126d', key: 'rs_126d' },
        { label: 'TREND', key: 'rs_trend', tt: 'rsrw-trend' },
        { label: 'RVOL', key: 'rvol', tt: 'rvol' },
        { label: 'SECTOR', key: 'sector' },
    ];
    const header = '<div style="display:grid;grid-template-columns:70px 60px 60px 60px 60px 60px 60px 1fr;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + cols.map(c =>
            '<div onclick="window.__rsrwSort(\'' + tableId + '\',\'' + c.key + '\')" style="cursor:pointer;user-select:none;">' + c.label + rsrwSortArrow(tableId, c.key) + (c.tt ? tt(c.tt) : '') + '</div>'
        ).join('')
        + '</div>';

    const tableRows = sortedRows.map(r => {
        const pct       = r.rs_pct || 0;
        const pctColor  = pct >= 80 ? 'var(--color-accent)' : pct <= 20 ? '#f23645' : '#ffb800';
        const trendVal  = r.rs_trend || 0;
        const trendIcon = trendVal > 0.01 ? '▲' : trendVal < -0.01 ? '▼' : '→';
        const trendClr  = trendVal > 0.01 ? 'var(--color-accent)' : trendVal < -0.01 ? '#f23645' : 'var(--color-muted)';
        const rvolClr   = (r.rvol || 0) >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)';
        const carteraTag   = r.en_cartera   ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '';
        const watchlistTag = r.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '';

        return '<div style="display:grid;grid-template-columns:70px 60px 60px 60px 60px 60px 60px 1fr;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div onclick="goToResearch(\'' + esc(r.ticker || '') + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(r.ticker || '') + carteraTag + watchlistTag + '</div>'
            + '<div style="color:' + pctColor + ';font-weight:500;">' + pct.toFixed(0) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_21d || 0).toFixed(1) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_63d || 0).toFixed(1) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_126d || 0).toFixed(1) + '</div>'
            + '<div style="color:' + trendClr + ';">' + trendIcon + '</div>'
            + '<div style="color:' + rvolClr + ';">' + (r.rvol || 0).toFixed(1) + 'x</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + esc(r.sector || '') + '</div>'
            + '</div>';
    }).join('');

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:' + color + ';font-size:13px;letter-spacing:0.08em;">' + esc(title) + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">'
        + (freshness ? esc(freshness) + ' · ' : '') + (rows ? rows.length : 0) + ' de ' + (total || 0)
        + '</div>'
        + '</div>'
        + header
        + '<div style="max-height:400px;overflow-y:auto;">' + tableRows + '</div>'
        + '</div>';
}

function setupTicker(container) {
    const input = container.querySelector('#rsrw-ticker-input');
    const btn   = container.querySelector('#rsrw-ticker-btn');
    const result = container.querySelector('#rsrw-ticker-result');

    async function doAnalyze() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent   = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        // Aquí, y no al pintar el resultado: la línea de abajo se lleva por
        // delante el canvas del análisis anterior, y hay que destruir su
        // gráfico antes. Además cubre el caso de que el fetch falle (se sale
        // por errorMessage y nunca se llega a repintar).
        _destruirGraficos();
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Calculando RS/RW para ' + esc(ticker) + '...</div>';

        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/rsrw/ticker/' + ticker, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Sin datos');
            result.innerHTML = renderTickerResult(data);
            renderTickerChart(data);
        } catch(e) {
            result.innerHTML = errorMessage(e.message);
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doAnalyze);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doAnalyze(); });

    // Deep-link ?ticker= -- mismo patrón que research.js
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        input.value = urlTicker.toUpperCase();
        doAnalyze();
    }
}

function renderTickerResult(data) {
    const score = data.rs_score || 0;
    const color = score >= 0 ? 'var(--color-accent)' : '#f23645';
    const trend = (data.rs_trend || 0) > 0.01 ? '▲ ALCISTA' : (data.rs_trend || 0) < -0.01 ? '▼ BAJISTA' : '→ LATERAL';
    const tColor = trend.includes('▲') ? 'var(--color-accent)' : trend.includes('▼') ? '#f23645' : 'var(--color-muted)';
    const chartId = 'rsrw-ticker-chart-' + Date.now();
    const pct = data.rs_pct;
    const pctColor = pct == null ? 'var(--color-muted)' : pct >= 80 ? 'var(--color-accent)' : pct <= 20 ? '#f23645' : '#ffb800';

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;">' + esc(data.ticker) + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Actualizado: ' + esc(data.timestamp) + '</div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;margin-bottom:1rem;">'
        + kpiCard('RS% ' + tt('rs-rating'), pct == null ? 'N/D' : pct.toFixed(1), pct == null ? 'sin scan reciente' : 'vs universo', pctColor)
        + kpiCard('RS SCORE', score.toFixed(1), 'vs SPY', color)
        + kpiCard('RS 21D', (data.rs_21d || 0).toFixed(2), '1 mes', 'var(--color-muted)')
        + kpiCard('RS 63D', (data.rs_63d || 0).toFixed(2), '3 meses', 'var(--color-muted)')
        + kpiCard('RS 126D', (data.rs_126d || 0).toFixed(2), '6 meses', 'var(--color-muted)')
        + '</div>'
        + '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">'
        + '<span style="color:var(--color-muted);font-size:12px;">TENDENCIA RS ' + tt('rsrw-trend') + ':</span>'
        + '<span style="color:' + tColor + ';font-size:13px;font-weight:500;">' + trend + '</span>'
        + '</div>'
        + '<div style="position:relative;height:100px;"><canvas id="' + chartId + '"></canvas></div>'
        + '</div>';
}

function renderTickerChart(data) {
    const chartId = document.querySelector('[id^="rsrw-ticker-chart"]')?.id;
    if (!chartId || !data.chart) return;

    function draw() {
        const ctx = document.getElementById(chartId);
        if (!ctx) return;
        const color = (data.rs_score || 0) >= 0 ? '#00ffad' : '#f23645';
        _rsrwCharts.push(new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.chart.dates,
                datasets: [{
                    data: data.chart.values,
                    borderColor: color,
                    backgroundColor: color + '18',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }
                }
            }
        }));
    }

    if (window.Chart) { draw(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = draw;
    document.head.appendChild(s);
}

function kpiCard(label, value, sub, color) {
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:16px;font-weight:500;">' + value + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + sub + '</div>'
        + '</div>';
}

function loadingCard(title) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;margin-bottom:0.5rem;">' + title + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Cargando desde Gist...</div>'
        + '</div>';
}

function errorCard(title, msg) {
    const rateLimited = isRateLimitMessage(msg);
    const color = rateLimited ? '#ffb800' : '#f23645';
    const icon  = rateLimited ? '⏱' : '✗';
    return '<div style="background:var(--color-surface);border:1px solid ' + color + '44;border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:' + color + ';font-size:13px;margin-bottom:0.5rem;">' + esc(title) + '</div>'
        + '<div style="color:' + color + ';font-size:12px;">' + icon + ' ' + esc(msg || 'Error') + '</div>'
        + '</div>';
}