// ─────────────────────────────────────────────────────────────────────────────
// RSU TERMINAL — CARTERA
// Posiciones activas con precios live, P&L recalculado, hipervínculos a Research,
// sparklines, indicadores WS por fila, exportar CSV, panel de riesgo.
// ─────────────────────────────────────────────────────────────────────────────

import { errorMessage } from '/core/ui.js';

let _ws        = null;
let _wsRetries = 0;
let _wsReconnectTimer  = null;
let _wsClosedByCleanup = false;
let _carteraData = null;
let _sparklines   = {};   // { ticker: [closes...] }
let _sortActive   = { key: 'peso',  dir: -1 };
let _sortClosed   = { key: 'fecha_display', dir: -1 };
let _filterActive = '';
let _filterClosed = '';

// ── Helpers numéricos seguros (null/NaN → 0) ─────────────────────────────────
const n = (v, d=0) => (v == null || isNaN(v) ? d : Number(v));
const fix = (v, dec=2) => n(v).toFixed(dec);
const usd = (v) => n(v).toLocaleString('en-US', {minimumFractionDigits:2});

export async function render(container) {
    injectStyles();
    container.innerHTML = header() + '<div id="cartera-content">' + loadingHTML() + '</div>';
    await loadCartera(container);
}

// ── CARGA PRINCIPAL ───────────────────────────────────────────────────────────

async function loadCartera(container) {
    try {
        const res  = await fetch('/api/v1/cartera/', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        _carteraData = data;

        const m = data.metrics;
        const c = data.closed_stats;

        let html = topBar(data);

        if (m && m.total_inv > 0) html += metricsRow(m);

        if (data.history && data.history.length > 1) {
            html += sectionHeader('01 // EVOLUCIÓN DEL VALOR');
            html += historySection(data.history);
        }

        html += sectionHeader('02 // POSICIONES ACTIVAS', true);

        if (data.abiertas && data.abiertas.length > 0) {
            html += riskPanel(data.abiertas);
            html += '<div id="active-table-wrap"></div>';
        } else {
            html += emptyBox('Sin posiciones activas en este momento.');
        }

        html += sectionHeader('03 // ACTIVIDAD RECIENTE');
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
            + recentBox('ÚLTIMAS ENTRADAS', data.recent,    true)
            + recentBox('ÚLTIMAS SALIDAS',  data.recent_closed || [], false)
            + '</div>';

        if (c && c.total > 0) {
            html += sectionHeader('04 // HISTORIAL CERRADAS');
            html += closedStats(c);
            html += pnlHistogram(data.cerradas || []);
            html += '<div id="closed-table-wrap"></div>';
        }

        html += sectionHeader('05 // ASIGNACIÓN ESTRATÉGICA');
        html += allocationWidget();

        container.querySelector('#cartera-content').innerHTML = html;

        // Donut chart, gráfico de evolución
        renderDonut();
        if (data.history && data.history.length > 1) drawHistoryChart(data.history);

        // Tablas ordenables/filtrables
        if (data.abiertas && data.abiertas.length > 0) renderActiveSection();
        if (data.cerradas && data.cerradas.length > 0) renderClosedSection();

        // Conectar WebSocket
        connectWS(data.abiertas || []);

        // Sparklines (llamada aparte, no bloquea el render principal)
        loadSparklines(data.abiertas || []);

    } catch(e) {
        container.querySelector('#cartera-content').innerHTML =
            errorMessage(e.message, {padding: '1.5rem', fontSize: '13px', extraStyle: 'background:var(--color-surface);border:1px solid #f2364566;border-radius:var(--radius);'});
    }
}

// ── WEBSOCKET ─────────────────────────────────────────────────────────────────

function connectWS(abiertas) {
    if (_ws) { try { _ws.close(); } catch(_) {} }
    _wsClosedByCleanup = false;

    const token = sessionStorage.getItem('rsu_token');
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url   = `${proto}://${location.host}/ws/cartera` + (token ? `?token=${token}` : '');

    _ws = new WebSocket(url);

    _ws.onopen = () => {
        _wsRetries = 0;
        setWsStatus('live');
    };

    _ws.onmessage = (e) => {
        try {
            const msg = JSON.parse(e.data);
            if (msg.type !== 'cartera_update') return;
            applyLivePrices(msg.prices, abiertas);
        } catch(_) {}
    };

    _ws.onerror = () => _ws.close();

    _ws.onclose = (event) => {
        setWsStatus('off');

        // 4401 = el backend ha rechazado el token (ausente/inválido/caducado).
        // Reintentar no serviría de nada: mandamos a login directamente.
        if (event.code === 4401) {
            sessionStorage.removeItem('rsu_token');
            if (window.__navigate) window.__navigate('/login');
            return;
        }

        if (_wsClosedByCleanup) return;

        _wsRetries++;
        if (_wsRetries < 5) {
            _wsReconnectTimer = setTimeout(() => connectWS(abiertas), Math.min(5000 * _wsRetries, 30000));
        }
    };
}

// Llamado por el router justo antes de destruir el contenedor de Cartera
// (navegación real fuera) -- sin esto, el socket seguía recibiendo precios
// en vivo, y si se caía, el reintento automático podía reabrirlo más tarde
// sin que nadie estuviera mirando la página.
export function cleanup() {
    _wsClosedByCleanup = true;
    if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null; }
    if (_ws) { try { _ws.close(); } catch(_) {} _ws = null; }
}

function setWsStatus(state) {
    document.querySelectorAll('.ws-dot').forEach(el => {
        el.className = 'ws-dot ' + state;
        el.title = state === 'live' ? 'Precios en tiempo real' : 'Sin conexión live';
    });
}

function applyLivePrices(prices, abiertas) {
    if (!prices || !abiertas) return;

    prices.forEach(p => {
        const { ticker, price, chg } = p;

        // Precio actual y cambio intradiario: son iguales para todos los lotes
        // del mismo ticker, así que sí se puede actualizar por ticker.
        document.querySelectorAll(`[data-live-price="${ticker}"]`).forEach(el => {
            el.textContent = '$' + usd(price);
        });
        document.querySelectorAll(`[data-live-chg="${ticker}"]`).forEach(el => {
            if (chg == null) return;
            const c = chg >= 0 ? 'var(--color-accent)' : '#f23645';
            el.style.color   = c;
            el.textContent   = (chg >= 0 ? '+' : '') + fix(chg) + '%';
        });

        // P&L % y $: se recalcula POR CADA POSICIÓN individual (id único), no por
        // ticker — si hay varios lotes del mismo ticker con precios de compra
        // distintos, cada uno debe llevar su propio P&L, no el del primero que
        // se encuentre.
        abiertas.filter(a => a.ticker === ticker).forEach(pos => {
            if (!(pos.compra > 0)) return;
            const pnl      = (price - pos.compra) / pos.compra * 100;
            const pnlUsd   = (price - pos.compra) * pos.shares;
            const pnlColor = pnl >= 0 ? 'var(--color-accent)' : '#f23645';

            // Persistir en el objeto (no solo pintar el DOM): si el usuario
            // ordena o filtra la tabla, renderActiveSection() repinta leyendo
            // estos mismos campos de _carteraData.abiertas -- sin esto,
            // revierte al snapshot de la carga inicial aunque el WS siga
            // activo (hallazgo A8).
            pos.actual = price;
            pos.pnl    = pnl;
            if (chg != null) pos.chg_hoy = chg;

            const pnlEl = document.querySelector(`[data-live-pnl-id="${pos.id}"]`);
            if (pnlEl) {
                pnlEl.style.color = pnlColor;
                pnlEl.textContent = (n(pnl) >= 0 ? '+' : '') + fix(pnl) + '%';
            }
            const pnlUsdEl = document.querySelector(`[data-live-pnl-usd-id="${pos.id}"]`);
            if (pnlUsdEl) {
                pnlUsdEl.style.color = pnlColor;
                pnlUsdEl.textContent = (pnlUsd >= 0 ? '+$' : '-$') + usd(Math.abs(n(pnlUsd)));
            }

            // Pulso e indicador live, también por posición individual
            const row = document.querySelector(`tr[data-row-id="${pos.id}"]`);
            if (row) {
                row.classList.remove('row-pulse');
                void row.offsetWidth;
                row.classList.add('row-pulse');
            }
            const dotEl = document.querySelector(`[data-live-dot-id="${pos.id}"]`);
            if (dotEl) dotEl.className = 'row-live-dot active';
        });
    });

    // P&L del día agregado: recalcula con el precio más reciente conocido
    // de cada ticker (el de este mensaje si vino, si no el de la carga
    // inicial) y el cierre de ayer que ya trae cada posición -- misma
    // fórmula que el backend, así el número no da saltos entre la carga
    // inicial y el primer tick.
    const priceMap = {};
    prices.forEach(p => { priceMap[p.ticker] = p.price; });
    let valHoy = 0, valAyer = 0;
    abiertas.forEach(pos => {
        if (!pos.prev_close || !pos.shares) return;
        const live = priceMap[pos.ticker] ?? pos.actual;
        if (!live) return;
        valHoy  += pos.shares * live;
        valAyer += pos.shares * pos.prev_close;
    });
    if (valAyer > 0) {
        // Redondeado a centavos antes de formatear -- sumar shares*precio de
        // 50+ posiciones acumula imprecisión de punto flotante (p.ej.
        // 5338.798 en vez de 5338.80) que usd() no recorta por sí solo.
        const pnlDiaUsd = Math.round((valHoy - valAyer) * 100) / 100;
        const pnlDiaPct = Math.round((valHoy - valAyer) / valAyer * 100 * 100) / 100;
        const color = pnlDiaUsd >= 0 ? 'var(--color-accent)' : '#f23645';
        const valueEl = document.getElementById('cartera-pnl-dia-value');
        const subEl   = document.getElementById('cartera-pnl-dia-sub');
        if (valueEl) {
            valueEl.style.color = color;
            valueEl.textContent = (pnlDiaUsd >= 0 ? '+$' : '-$') + usd(Math.abs(pnlDiaUsd));
        }
        if (subEl) {
            subEl.style.color   = color;
            subEl.textContent   = (pnlDiaPct >= 0 ? '+' : '') + fix(pnlDiaPct) + '% hoy';
        }
    }

    // Valor de Mercado y P&L Neto: mismo priceMap de arriba, pero contra el
    // coste de compra (total_inv/total_comis de la carga inicial, que no
    // cambian con el precio) en vez de contra el cierre de ayer -- antes
    // estas dos tarjetas se quedaban congeladas tras la carga inicial
    // mientras la tabla sí se movía en vivo.
    if (_carteraData && _carteraData.metrics && _carteraData.metrics.total_inv > 0) {
        const totalInv   = _carteraData.metrics.total_inv;
        const totalComis = _carteraData.metrics.total_comis || 0;

        let totalValLive = 0;
        abiertas.forEach(pos => {
            const live = priceMap[pos.ticker] ?? pos.actual;
            if (live && pos.shares) totalValLive += pos.shares * live;
        });
        totalValLive = Math.round(totalValLive * 100) / 100;

        const valPct  = Math.round((totalValLive - totalInv) / totalInv * 100 * 100) / 100;
        const pnlNeto = Math.round(((totalValLive - totalInv) - totalComis) * 100) / 100;
        const pnlPct  = Math.round(pnlNeto / totalInv * 100 * 100) / 100;

        const valColor = valPct >= 0 ? 'var(--color-accent)' : '#f23645';
        const valValueEl = document.getElementById('cartera-valor-mercado-value');
        const valSubEl   = document.getElementById('cartera-valor-mercado-sub');
        if (valValueEl) { valValueEl.style.color = valColor; valValueEl.textContent = '$' + usd(totalValLive); }
        if (valSubEl)   { valSubEl.style.color   = valColor; valSubEl.textContent   = (valPct >= 0 ? '+' : '') + fix(valPct) + '% vs compra'; }

        const pnlNetoColor = pnlNeto >= 0 ? 'var(--color-accent)' : '#f23645';
        const pnlValueEl = document.getElementById('cartera-pnl-neto-value');
        const pnlSubEl   = document.getElementById('cartera-pnl-neto-sub');
        if (pnlValueEl) { pnlValueEl.style.color = pnlNetoColor; pnlValueEl.textContent = (pnlNeto >= 0 ? '+' : '') + '$' + usd(Math.abs(pnlNeto)); }
        if (pnlSubEl)   { pnlSubEl.style.color   = pnlNetoColor; pnlSubEl.textContent   = (pnlPct >= 0 ? '+' : '') + fix(pnlPct) + '% sobre capital'; }
    }
}

// ── ESTILOS ───────────────────────────────────────────────────────────────────

function injectStyles() {
    if (document.getElementById('cartera-styles')) return;
    const s = document.createElement('style');
    s.id = 'cartera-styles';
    s.textContent = `
        /* WS dot global */
        .ws-dot { width:7px;height:7px;border-radius:50%;background:#555;display:inline-block;transition:background .3s; }
        .ws-dot.live { background:var(--color-accent);box-shadow:0 0 6px var(--color-accent); }
        .ws-dot.off  { background:#555; }

        /* Row live dot */
        .row-live-dot { width:6px;height:6px;border-radius:50%;background:#333;flex-shrink:0;transition:all .3s; }
        .row-live-dot.active { background:var(--color-accent);box-shadow:0 0 5px var(--color-accent);animation:livePulse 2s ease-in-out; }
        @keyframes livePulse { 0%,100%{opacity:1} 50%{opacity:.4} }

        /* Row flash on update */
        .row-pulse { animation:rowFlash .6s ease-out; }
        @keyframes rowFlash { 0%{background:rgba(0,255,173,.08)} 100%{background:transparent} }

        /* Ticker link */
        .ticker-link {
            background:rgba(0,255,173,.1);color:var(--color-accent);
            border:1px solid rgba(0,255,173,.3);border-radius:3px;
            padding:2px 8px;font-size:12px;cursor:pointer;
            text-decoration:none;transition:all .15s;display:inline-block;
        }
        .ticker-link:hover { background:rgba(0,255,173,.2);border-color:var(--color-accent); }

        /* Table row hover */
        .cartera-tr:hover td { background:rgba(255,255,255,.02); }

        /* Row tint */
        .row-profit td { background:rgba(0,255,173,.025); }
        .row-loss   td { background:rgba(242,54,69,.025); }

        /* Sparkline */
        .sparkline { display:inline-block;vertical-align:middle;margin-left:6px; }

        /* Tooltip on hover */
        .pos-tooltip {
            display:none;position:absolute;z-index:200;background:var(--color-surface);
            border:1px solid var(--color-border);border-radius:var(--radius);
            padding:10px 14px;font-size:11px;color:var(--color-muted);
            min-width:200px;box-shadow:0 4px 20px rgba(0,0,0,.5);pointer-events:none;
            line-height:1.7;
        }
        tr:hover .pos-tooltip { display:block; }

        /* Peso bar */
        .peso-bar { height:3px;background:var(--color-accent);border-radius:2px;margin-top:3px;transition:width .3s; }

        /* Export btn */
        .export-btn {
            background:transparent;border:1px solid var(--color-border);
            color:var(--color-muted);border-radius:var(--radius);
            padding:4px 12px;font-family:var(--font-mono);font-size:11px;
            cursor:pointer;transition:all .15s;
        }
        .export-btn:hover { border-color:var(--color-accent);color:var(--color-accent); }
        .refresh-btn {
            background:rgba(0,255,173,.08);border:1px solid rgba(0,255,173,.3);
            color:var(--color-accent);border-radius:var(--radius);
            padding:4px 12px;font-family:var(--font-mono);font-size:11px;
            cursor:pointer;transition:all .15s;
        }
        .refresh-btn:hover { background:rgba(0,255,173,.15); }
    `;
    document.head.appendChild(s);
}

// ── COMPONENTES HTML ──────────────────────────────────────────────────────────

function header() {
    return `<div style="margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:flex-end;">
        <div>
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:.1em;text-shadow:var(--glow-text);margin-bottom:4px;">CARTERA</div>
            <div style="color:var(--color-muted);font-size:12px;">Portfolio tracker · Precios live · WebSocket</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <button class="export-btn" onclick="window.__carteraExportCSV()">↓ CSV</button>
            <button class="refresh-btn" onclick="window.__carteraRefresh()">⟳ Actualizar</button>
            <span class="ws-dot off" title="Sin conexión"></span>
        </div>
    </div>`;
}

function topBar(data) {
    const mktBadge = `<span style="background:${data.mkt_color}22;border:1px solid ${data.mkt_color}88;border-radius:4px;padding:2px 10px;font-size:11px;color:${data.mkt_color};letter-spacing:.1em;">● MKT: ${data.mkt_status}</span>`;
    return `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
        <div style="color:var(--color-muted);font-size:11px;">LAST UPDATE: ${data.last_update}</div>
        ${mktBadge}
    </div>`;
}

function metricsRow(m) {
    const pnlColor = m.pnl_neto >= 0 ? 'var(--color-accent)' : '#f23645';
    const valColor = m.val_pct  >= 0 ? 'var(--color-accent)' : '#f23645';
    const pnlSign  = m.pnl_neto >= 0 ? '+' : '';
    const valSign  = m.val_pct  >= 0 ? '+' : '';

    const hasSim = m.capital_disponible != null;
    const hasDia = m.pnl_dia_usd != null;
    const cols = (hasSim ? 4 : 3) + (hasDia ? 1 : 0);

    let cards = '';
    if (hasDia) {
        const diaColor = m.pnl_dia_usd >= 0 ? 'var(--color-accent)' : '#f23645';
        const diaSign  = m.pnl_dia_usd >= 0 ? '+' : '-';
        cards += metricCard('P&L Hoy',
            diaSign + '$' + usd(Math.abs(n(m.pnl_dia_usd))),
            (m.pnl_dia_pct >= 0 ? '+' : '') + fix(m.pnl_dia_pct) + '% hoy',
            diaColor, 'cartera-pnl-dia',
            { valueId: 'cartera-pnl-dia-value', subId: 'cartera-pnl-dia-sub' });
    }

    cards += metricCard('Capital Invertido',  '$' + usd(m.total_inv), 'Base de referencia', 'var(--color-text)', 'cartera-capital-invertido')
        + metricCard('Valor de Mercado',   '$' + usd(m.total_val), valSign + fix(m.val_pct) + '% vs compra', valColor, 'cartera-valor-mercado',
            { valueId: 'cartera-valor-mercado-value', subId: 'cartera-valor-mercado-sub' })
        + metricCard('P&L Neto (−comis.)', pnlSign + '$' + usd(Math.abs(n(m.pnl_neto))), pnlSign + fix(m.pnl_pct) + '% sobre capital', pnlColor, 'cartera-pnl-neto',
            { valueId: 'cartera-pnl-neto-value', subId: 'cartera-pnl-neto-sub' });

    if (hasSim) {
        const realColor = m.pnl_realizado_acum >= 0 ? 'var(--color-accent)' : '#f23645';
        const realSign  = m.pnl_realizado_acum >= 0 ? '+' : '';
        cards += metricCard('Capital Disponible', '$' + usd(m.capital_disponible),
            'Inicial $' + usd(m.capital_inicial) + ' ' + realSign + '$' + usd(Math.abs(n(m.pnl_realizado_acum))) + ' realiz.', realColor, 'cartera-capital-disponible');
    }

    return `<div style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:1rem;margin-bottom:.5rem;">${cards}</div>
    <p style="color:var(--color-muted);font-size:10px;margin:0 0 1.5rem;">Solo posiciones abiertas — las operaciones cerradas se calculan aparte, en la sección "Historial Cerradas" de más abajo.</p>`;
}

function metricCard(label, value, sub, color, tooltipKey, ids) {
    const tt = tooltipKey ? ` <span class="tt-trigger" data-tooltip="${tooltipKey}" title="¿Qué es esto?">?</span>` : '';
    const valueIdAttr = ids && ids.valueId ? ` id="${ids.valueId}"` : '';
    const subIdAttr   = ids && ids.subId   ? ` id="${ids.subId}"`   : '';
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;text-align:center;">
        <div style="color:var(--color-muted);font-size:11px;letter-spacing:.1em;margin-bottom:6px;">${label}${tt}</div>
        <div${valueIdAttr} style="color:${color};font-size:22px;font-weight:500;">${value}</div>
        <div${subIdAttr} style="color:${color};font-size:11px;margin-top:4px;opacity:.7;">${sub}</div>
    </div>`;
}

function sectionHeader(title, hasWsDot = false) {
    return `<div style="display:flex;align-items:center;gap:10px;color:var(--color-secondary);font-size:14px;letter-spacing:.1em;margin:1.5rem 0 .75rem;border-left:3px solid var(--color-accent);padding-left:10px;">
        ${title}
        ${hasWsDot ? '<span class="ws-dot off" title="Conectando..."></span>' : ''}
    </div>`;
}

function emptyBox(msg) {
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;color:var(--color-muted);font-size:12px;margin-bottom:1rem;">${msg}</div>`;
}

function loadingHTML() {
    return '<div style="color:var(--color-muted);font-size:12px;padding:2rem 0;">Cargando cartera y precios live...</div>';
}

// ── PANEL DE RIESGO ───────────────────────────────────────────────────────────

function riskPanel(abiertas) {
    if (!abiertas.length) return '';

    const byPeso    = [...abiertas].sort((a,b) => b.peso - a.peso);
    const byPnl     = [...abiertas].sort((a,b) => b.pnl - a.pnl);
    const biggest   = byPeso[0];
    const smallest  = byPeso[byPeso.length-1];
    const bestPnl   = byPnl[0];
    const worstPnl  = byPnl[byPnl.length-1];

    function rCard(label, ticker, val, color) {
        return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:.85rem 1rem;">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:5px;">${label}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span class="ticker-link" onclick="window.__navigate('/research?ticker=${ticker}')">${ticker}</span>
                <span style="color:${color};font-size:13px;font-weight:500;">${val}</span>
            </div>
        </div>`;
    }

    const sectorMap = {};
    abiertas.forEach(r => {
        const sec = r.sector || 'Sin clasificar';
        sectorMap[sec] = (sectorMap[sec] || 0) + (r.peso || 0);
    });
    const sectorList = Object.entries(sectorMap).sort((a,b) => b[1]-a[1]);
    const topSector  = sectorList[0];

    // Concentración por sector: agrupa peso% por sector y calcula un índice de
    // concentración 0-100% (HHI normalizado: suma de pesos% al cuadrado / 100).
    // 100% = toda la cartera en un solo sector, 0% = perfectamente repartida.
    const hhi = Object.values(sectorMap).reduce((acc, p) => acc + Math.pow(p, 2), 0) / 100;
    const hhiLabel = hhi > 25 ? 'Alta' : hhi > 15 ? 'Moderada' : 'Baja';
    const hhiColor = hhi > 25 ? '#f23645' : hhi > 15 ? '#ff9800' : 'var(--color-accent)';

    const sectorBars = sectorList.slice(0,5).map(([sec, pct]) =>
        `<div style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--color-muted);margin-bottom:2px;">
                <span>${sec}</span><span>${fix(pct,1)}%</span>
            </div>
            <div style="height:4px;background:var(--color-border);border-radius:2px;overflow:hidden;">
                <div style="height:100%;width:${Math.min(pct,100)}%;background:var(--color-secondary);"></div>
            </div>
        </div>`
    ).join('');

    return `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:.75rem;">
        ${rCard('Mayor posición', biggest.ticker, biggest.peso + '% cartera', 'var(--color-text)')}
        ${rCard('Menor posición', smallest.ticker, smallest.peso + '% cartera', 'var(--color-muted)')}
        ${rCard('Mejor P&L', bestPnl.ticker, (bestPnl.pnl >= 0 ? '+' : '') + fix(bestPnl.pnl) + '%', 'var(--color-accent)')}
        ${rCard('Peor P&L', worstPnl.ticker, (worstPnl.pnl >= 0 ? '+' : '') + fix(worstPnl.pnl) + '%', '#f23645')}
    </div>
    <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:.75rem;margin-bottom:1rem;">
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:.85rem 1rem;">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:8px;">EXPOSICIÓN POR SECTOR</div>
            ${sectorBars || '<div style="color:var(--color-muted);font-size:11px;">Sin datos de sector.</div>'}
        </div>
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:.85rem 1rem;">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:5px;">CONCENTRACIÓN POR SECTOR <span class="tt-trigger" data-tooltip="cartera-concentracion-sector" title="¿Qué es esto?">?</span></div>
            <div style="color:${hhiColor};font-size:20px;font-weight:500;">${fix(hhi,1)}%</div>
            <div style="color:${hhiColor};font-size:11px;margin-top:2px;">${hhiLabel} · sector top: ${topSector ? topSector[0] : '—'} (${topSector ? fix(topSector[1],1) : 0}%)</div>
        </div>
    </div>`;
}

// ── TABLA DE POSICIONES ACTIVAS ───────────────────────────────────────────────

function sortRows(rows, sortState) {
    const { key, dir } = sortState;
    return [...rows].sort((a, b) => {
        let av = a[key], bv = b[key];
        if (key === 'fecha' || key === 'fecha_display') {
            const af = a.fecha_display || a.fecha, bf = b.fecha_display || b.fecha;
            av = new Date(af.split('/').reverse().join('-'));
            bv = new Date(bf.split('/').reverse().join('-'));
        } else if (typeof av === 'string') {
            av = (av || '').toLowerCase();
            bv = (bv || '').toLowerCase();
        } else {
            av = n(av); bv = n(bv);
        }
        if (av < bv) return -1 * dir;
        if (av > bv) return  1 * dir;
        return 0;
    });
}

function sortArrow(sortState, key) {
    if (sortState.key !== key) return '';
    return sortState.dir === 1 ? ' ▲' : ' ▼';
}

function renderActiveSection() {
    if (!_carteraData) return;
    const wrap = document.getElementById('active-table-wrap');
    if (!wrap) return;
    let rows = _carteraData.abiertas || [];
    if (_filterActive.trim()) {
        const f = _filterActive.trim().toLowerCase();
        rows = rows.filter(r => r.ticker.toLowerCase().includes(f) || (r.comment||'').toLowerCase().includes(f) || (r.sector||'').toLowerCase().includes(f) || (r.tier||'').toLowerCase().includes(f));
    }
    rows = sortRows(rows, _sortActive);
    wrap.innerHTML = tableControls('active', _filterActive, rows.length, (_carteraData.abiertas||[]).length) + activeTable(rows);
    rows.forEach((r, i) => drawSparklineFor(`spark-active-${i}-${r.ticker}`, r.ticker));
}

function renderClosedSection() {
    if (!_carteraData) return;
    const wrap = document.getElementById('closed-table-wrap');
    if (!wrap) return;
    let rows = _carteraData.cerradas || [];
    if (_filterClosed.trim()) {
        const f = _filterClosed.trim().toLowerCase();
        rows = rows.filter(r => r.ticker.toLowerCase().includes(f) || (r.comment||'').toLowerCase().includes(f));
    }
    rows = sortRows(rows, _sortClosed);
    wrap.innerHTML = tableControls('closed', _filterClosed, rows.length, (_carteraData.cerradas||[]).length) + closedTable(rows);
}

function tableControls(scope, filterVal, shown, total) {
    return `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
        <input type="text" placeholder="Filtrar por ticker, sector o comentario…" value="${filterVal}"
            oninput="window.__carteraFilter('${scope}', this.value)"
            style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);color:var(--color-text);font-family:var(--font-mono);font-size:11px;padding:5px 10px;width:280px;">
        <span style="color:var(--color-muted);font-size:10px;">${shown} / ${total}</span>
    </div>`;
}

window.__carteraFilter = function(scope, value) {
    if (scope === 'active') { _filterActive = value; renderActiveSection(); }
    else { _filterClosed = value; renderClosedSection(); }
};

window.__carteraSort = function(scope, key) {
    const state = scope === 'active' ? _sortActive : _sortClosed;
    if (state.key === key) state.dir *= -1;
    else { state.key = key; state.dir = 1; }
    if (scope === 'active') renderActiveSection(); else renderClosedSection();
};

function activeTable(rows) {
    const cols = [
        { label: '',            key: null },
        { label: 'FECHA',       key: 'fecha' },
        { label: 'TICKER',      key: 'ticker' },
        { label: 'NIVEL <span class="tt-trigger" data-tooltip="cartera-nivel" title="¿Qué es esto?">?</span>', key: 'tier' },
        { label: 'SECTOR',      key: 'sector' },
        { label: 'P. COMPRA',   key: 'compra' },
        { label: 'P. ACTUAL',   key: 'actual' },
        { label: 'HOY %',       key: 'chg_hoy' },
        { label: 'P&L %',       key: 'pnl' },
        { label: 'PESO',        key: 'peso' },
        { label: '7D',          key: null },
        { label: 'COMENTARIO',  key: null },
    ];
    const th = cols.map(c => {
        const arrow = c.key ? sortArrow(_sortActive, c.key) : '';
        const clickable = c.key ? `cursor:pointer;user-select:none;` : '';
        const onclick = c.key ? `onclick="window.__carteraSort('active','${c.key}')"` : '';
        return `<th ${onclick} style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;padding:8px 10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap;${clickable}">${c.label}${arrow}</th>`;
    }).join('');

    if (!rows.length) {
        return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;padding:1.25rem;color:var(--color-muted);font-size:12px;">Sin resultados para el filtro actual.</div>`;
    }

    const trs = rows.map((r, i) => {
        const pnlColor = r.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
        const rowClass = r.pnl >= 0 ? 'cartera-tr row-profit' : 'cartera-tr row-loss';
        const chgColor = r.chg_hoy == null ? 'var(--color-muted)' : r.chg_hoy >= 0 ? 'var(--color-accent)' : '#f23645';
        const chgTxt   = r.chg_hoy == null ? '—' : (r.chg_hoy >= 0 ? '+' : '') + fix(r.chg_hoy) + '%';
        const comment  = r.comment || '—';
        const sparkId  = `spark-active-${i}-${r.ticker}`;
        const tierColors = { CORE: '#00ffad', HIGH: '#00d9ff', LOTTERY: '#b044ff' };
        const tierColor = tierColors[r.tier] || 'var(--color-muted)';
        const tierBadge = r.tier
            ? `<span style="background:${tierColor}22;border:1px solid ${tierColor}88;color:${tierColor};border-radius:3px;padding:1px 6px;font-size:10px;letter-spacing:.05em;">${r.tier}</span>`
            : `<span style="color:var(--color-muted);font-size:10px;">—</span>`;

        return `<tr class="${rowClass}" data-row-ticker="${r.ticker}" data-row-id="${r.id}" style="border-bottom:1px solid var(--color-border);position:relative;">
            <td style="padding:8px 10px;text-align:center;">
                <span class="row-live-dot" data-live-dot="${r.ticker}" data-live-dot-id="${r.id}" title="Sin datos live"></span>
            </td>
            <td style="padding:8px 10px;color:var(--color-muted);font-size:11px;white-space:nowrap;">${r.fecha_display || r.fecha}</td>
            <td style="padding:8px 10px;">
                <span class="ticker-link" onclick="window.__navigate('/research?ticker=${r.ticker}')" title="Ver análisis en Research">${r.ticker}</span>
            </td>
            <td style="padding:8px 10px;">${tierBadge}</td>
            <td style="padding:8px 10px;color:var(--color-muted);font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.sector || 'Sin clasificar'}</td>
            <td style="padding:8px 10px;color:var(--color-text);font-size:12px;">$${usd(r.compra)}</td>
            <td style="padding:8px 10px;color:var(--color-text);font-size:12px;" data-live-price="${r.ticker}">$${usd(r.actual)}</td>
            <td style="padding:8px 10px;font-size:11px;color:${chgColor};" data-live-chg="${r.ticker}">${chgTxt}</td>
            <td style="padding:8px 10px;font-size:12px;font-weight:500;" data-live-pnl-id="${r.id}">
                <span style="color:${pnlColor};">${r.pnl >= 0 ? '+' : ''}${fix(r.pnl)}%</span>
            </td>
            <td style="padding:8px 10px;min-width:80px;">
                <div style="color:var(--color-muted);font-size:10px;">${r.peso}%</div>
                <div class="peso-bar" style="width:${Math.min(r.peso * 3, 100)}%"></div>
            </td>
            <td style="padding:8px 10px;"><canvas class="sparkline" id="${sparkId}" width="60" height="20"></canvas></td>
            <td style="padding:8px 10px;color:var(--color-muted);font-size:11px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${comment}">${comment}</td>
        </tr>`;
    }).join('');

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">
            <thead><tr>${th}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    </div>`;
}

// ── TABLA CERRADAS ────────────────────────────────────────────────────────────

function pnlHistogram(cerradas) {
    if (!cerradas || !cerradas.length) return '';

    const buckets = [
        { label: '< -25%',      min: -Infinity, max: -25, color: '#f23645' },
        { label: '-25% a -10%', min: -25,       max: -10, color: '#f23645' },
        { label: '-10% a 0%',   min: -10,       max: 0,   color: '#f23645' },
        { label: '0% a 10%',    min: 0,         max: 10,  color: 'var(--color-accent)' },
        { label: '10% a 25%',   min: 10,        max: 25,  color: 'var(--color-accent)' },
        { label: '25%+',        min: 25,        max: Infinity, color: 'var(--color-accent)' },
    ];

    buckets.forEach(b => { b.count = 0; });
    cerradas.forEach(r => {
        const pnl = n(r.pnl);
        const bucket = buckets.find(b => pnl >= b.min && pnl < b.max) || buckets[buckets.length - 1];
        bucket.count++;
    });

    const maxCount = Math.max(...buckets.map(b => b.count), 1);

    const bars = buckets.map(b => `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
            <span style="color:var(--color-muted);font-size:10px;width:90px;flex-shrink:0;">${b.label}</span>
            <div style="flex:1;height:14px;background:var(--color-border);border-radius:3px;overflow:hidden;">
                <div style="height:100%;width:${(b.count / maxCount * 100)}%;background:${b.color};opacity:.75;"></div>
            </div>
            <span style="color:var(--color-text);font-size:10px;width:20px;text-align:right;flex-shrink:0;">${b.count}</span>
        </div>`
    ).join('');

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;margin-bottom:1rem;">
        <div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:10px;">DISTRIBUCIÓN DE P&L% (CERRADAS)</div>
        ${bars}
    </div>`;
}

function closedStats(c) {
    const wrColor  = c.win_rate >= 50 ? 'var(--color-accent)' : '#f23645';
    const pnlColor = c.avg_pnl  >= 0  ? 'var(--color-accent)' : '#f23645';
    return `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">
        ${metricCard('Trades Cerrados', c.total, c.ganadas + 'W / ' + c.perdidas + 'L', 'var(--color-text)')}
        ${metricCard('Win Rate', fix(c.win_rate,1) + '%', 'Operaciones ganadoras', wrColor)}
        ${metricCard('P&L Total Acum.', (c.avg_pnl >= 0 ? '+' : '') + fix(c.avg_pnl) + '%', 'Media ponderada por capital', pnlColor)}
    </div>`;
}

function closedTable(rows) {
    const cols = [
        { label: 'FECHA CIERRE', key: 'fecha_display' },
        { label: 'TICKER',     key: 'ticker' },
        { label: 'P. COMPRA',  key: 'compra' },
        { label: 'P. SALIDA',  key: 'actual' },
        { label: 'P&L %',      key: 'pnl' },
        { label: 'COMENTARIO', key: null },
    ];
    const th = cols.map(c => {
        const arrow = c.key ? sortArrow(_sortClosed, c.key) : '';
        const clickable = c.key ? `cursor:pointer;user-select:none;` : '';
        const onclick = c.key ? `onclick="window.__carteraSort('closed','${c.key}')"` : '';
        return `<th ${onclick} style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;padding:8px 12px;border-bottom:1px solid var(--color-border);text-align:left;${clickable}">${c.label}${arrow}</th>`;
    }).join('');

    if (!rows.length) {
        return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;padding:1.25rem;color:var(--color-muted);font-size:12px;">Sin resultados para el filtro actual.</div>`;
    }

    const trs = rows.map(r => {
        const c = r.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
        return `<tr class="cartera-tr" style="border-bottom:1px solid var(--color-border);">
            <td style="padding:8px 12px;color:var(--color-muted);font-size:11px;">${r.fecha_display || r.fecha}</td>
            <td style="padding:8px 12px;">
                <span class="ticker-link" onclick="window.__navigate('/research?ticker=${r.ticker}')">${r.ticker}</span>
            </td>
            <td style="padding:8px 12px;color:var(--color-text);font-size:12px;">$${usd(r.compra)}</td>
            <td style="padding:8px 12px;color:var(--color-text);font-size:12px;">$${usd(r.actual)}</td>
            <td style="padding:8px 12px;color:${c};font-size:12px;font-weight:500;">${r.pnl >= 0 ? '+' : ''}${fix(r.pnl)}%</td>
            <td style="padding:8px 12px;color:var(--color-muted);font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.comment || ''}">${r.comment || '—'}</td>
        </tr>`;
    }).join('');

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;max-height:360px;overflow-y:auto;">
        <table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">
            <thead style="position:sticky;top:0;background:var(--color-surface);z-index:1;"><tr>${th}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    </div>`;
}

// ── CAJAS RECIENTES ───────────────────────────────────────────────────────────

function recentBox(title, rows, isEntradas) {
    const color = isEntradas ? 'var(--color-accent)' : '#f23645';
    const items = (rows || []).slice(0,5).map(r => {
        const val = isEntradas
            ? `<span style="color:var(--color-text);">$${usd(r.compra)}</span>`
            : `<span style="color:${r.pnl >= 0 ? 'var(--color-accent)' : '#f23645'};">${r.pnl >= 0 ? '+' : ''}${fix(r.pnl)}%</span>`;
        return `<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">
            <span style="color:var(--color-muted);">${r.fecha_display || r.fecha}</span>
            <span class="ticker-link" onclick="window.__navigate('/research?ticker=${r.ticker}')">${r.ticker}</span>
            ${val}
        </div>`;
    }).join('') || `<div style="color:var(--color-muted);font-size:12px;padding:.5rem 0;">Sin datos.</div>`;

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;">
        <div style="color:${color};font-size:12px;letter-spacing:.08em;margin-bottom:.75rem;">${title}</div>
        ${items}
    </div>`;
}

// ── SPARKLINES POR FILA ────────────────────────────────────────────────────────

async function loadSparklines(abiertas) {
    if (!abiertas.length) return;
    try {
        const res  = await fetch('/api/v1/cartera/sparklines?days=30', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) return;
        _sparklines = data.sparklines || {};
        // Redibuja los sparklines ya presentes en el DOM con los datos recién llegados
        Object.keys(_sparklines).forEach(ticker => {
            document.querySelectorAll(`canvas.sparkline[id*="-${ticker}"]`).forEach(c => drawSparkline(c.id, _sparklines[ticker]));
        });
    } catch(_) {}
}

function drawSparklineFor(canvasId, ticker) {
    const closes = _sparklines[ticker];
    if (closes) drawSparkline(canvasId, closes);
}

function drawSparkline(canvasId, closes) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !closes || closes.length < 2) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const min = Math.min(...closes), max = Math.max(...closes);
    const range = (max - min) || 1;
    const rising = closes[closes.length - 1] >= closes[0];
    ctx.strokeStyle = rising ? '#00ffad' : '#f23645';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    closes.forEach((v, i) => {
        const x = (i / (closes.length - 1)) * (w - 2) + 1;
        const y = h - 1 - ((v - min) / range) * (h - 2);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
}

// ── GRÁFICO DE EVOLUCIÓN HISTÓRICA ─────────────────────────────────────────────

function historySection(history) {
    const first = history[0], last = history[history.length - 1];
    const pnlPct = first.valor > 0 ? ((last.valor - first.valor) / first.valor * 100) : 0;
    const pnlColor = pnlPct >= 0 ? 'var(--color-accent)' : '#f23645';
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;margin-bottom:1rem;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;">VALOR DE MERCADO · ÚLTIMOS ${history.length} DÍAS CON DATOS</div>
            <div style="color:${pnlColor};font-size:13px;font-weight:500;">${pnlPct >= 0 ? '+' : ''}${fix(pnlPct)}% en el periodo</div>
        </div>
        <canvas id="cartera-history-chart" width="900" height="220" style="width:100%;height:220px;display:block;"></canvas>
        <div style="display:flex;justify-content:space-between;color:var(--color-muted);font-size:10px;margin-top:6px;">
            <span>${first.fecha}</span><span>${last.fecha}</span>
        </div>
    </div>`;
}

function drawHistoryChart(history) {
    const canvas = document.getElementById('cartera-history-chart');
    if (!canvas || !history.length) return;
    // Ajustamos el buffer interno al tamaño real en pantalla para que no se vea borroso
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = Math.max(rect.width, 300) * dpr;
    canvas.height = 220 * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    const w = rect.width || 900, h = 220;
    const padL = 55, padR = 10, padT = 10, padB = 10;

    const valores    = history.map(p => p.valor);
    const invertidos = history.map(p => p.invertido);
    const allVals    = valores.concat(invertidos.filter(v => v > 0));
    const min = Math.min(...allVals) * 0.98;
    const max = Math.max(...allVals) * 1.02;
    const range = (max - min) || 1;

    const xAt = i => padL + (i / (history.length - 1)) * (w - padL - padR);
    const yAt = v => padT + (1 - (v - min) / range) * (h - padT - padB);

    ctx.clearRect(0, 0, w, h);

    // Grid + etiquetas del eje Y
    ctx.strokeStyle = 'rgba(255,255,255,.06)';
    ctx.fillStyle   = 'var(--color-muted)';
    ctx.font        = '9px monospace';
    ctx.textAlign   = 'right';
    for (let k = 0; k <= 3; k++) {
        const v = min + (range * k / 3);
        const y = yAt(v);
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
        ctx.fillText('$' + Math.round(v).toLocaleString('en-US'), padL - 6, y + 3);
    }

    // Línea de capital invertido (referencia, discontinua)
    ctx.strokeStyle = 'var(--color-muted)';
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    invertidos.forEach((v, i) => { const x = xAt(i), y = yAt(v || valores[i]); i === 0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y); });
    ctx.stroke();
    ctx.setLineDash([]);

    // Línea de valor de mercado
    const rising = valores[valores.length-1] >= valores[0];
    ctx.strokeStyle = rising ? '#00ffad' : '#f23645';
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    valores.forEach((v, i) => { const x = xAt(i), y = yAt(v); i === 0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y); });
    ctx.stroke();

    // Relleno suave bajo la curva
    ctx.lineTo(xAt(valores.length-1), h - padB);
    ctx.lineTo(xAt(0), h - padB);
    ctx.closePath();
    ctx.fillStyle = rising ? 'rgba(0,255,173,.06)' : 'rgba(242,54,69,.06)';
    ctx.fill();
}

// ── ALLOCATION WIDGET ─────────────────────────────────────────────────────────

function allocationWidget() {
    const buckets = [
        { name:'SPXL Strategy', pct:40, color:'#00ffad', desc:'Núcleo de la cartera. Exposición apalancada 3x al S&P 500.' },
        { name:'RSU Stocks',    pct:30, color:'#00d9ff', desc:'Acciones líderes de sectores con crecimiento explosivo.' },
        { name:'Cryptos',       pct:20, color:'#ff9800', desc:'Asignación especulativa. BTC y ETH como reserva digital.' },
        { name:'Beta Stocks',   pct:10, color:'#b044ff', desc:'Acciones de alto beta para movimientos amplificados.' },
    ];
    const legend = buckets.map(b =>
        `<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid var(--color-border);">
            <div style="width:10px;height:10px;background:${b.color};border-radius:2px;margin-top:3px;flex-shrink:0;"></div>
            <div>
                <span style="color:${b.color};font-size:13px;">${b.name}</span>
                <span style="color:${b.color};font-size:14px;margin-left:8px;">${b.pct}%</span>
                <div style="color:var(--color-muted);font-size:11px;margin-top:2px;line-height:1.4;">${b.desc}</div>
            </div>
        </div>`
    ).join('');

    return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
            <canvas id="cartera-donut" width="220" height="220"></canvas>
            <div style="color:var(--color-muted);font-size:10px;margin-top:8px;letter-spacing:.08em;">Asignación objetivo · Estrategia RSU</div>
        </div>
        <div>${legend}</div>
    </div>`;
}

function renderDonut() {
    const canvas = document.getElementById('cartera-donut');
    if (!canvas) return;
    const ctx   = canvas.getContext('2d');
    const cx    = 110, cy = 110, ro = 90, ri = 55;
    const data  = [
        { pct:40, color:'#00ffad' }, { pct:30, color:'#00d9ff' },
        { pct:20, color:'#ff9800' }, { pct:10, color:'#b044ff' },
    ];
    let angle = -Math.PI / 2;
    data.forEach(b => {
        const slice = (b.pct / 100) * 2 * Math.PI;
        ctx.beginPath();
        ctx.moveTo(cx + ro * Math.cos(angle), cy + ro * Math.sin(angle));
        ctx.arc(cx, cy, ro, angle, angle + slice);
        ctx.arc(cx, cy, ri, angle + slice, angle, true);
        ctx.closePath();
        ctx.fillStyle = b.color;
        ctx.fill();
        angle += slice;
    });
    ctx.beginPath();
    ctx.arc(cx, cy, ri, 0, 2 * Math.PI);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim() || '#111';
    ctx.fill();
    ctx.fillStyle   = '#00ffad';
    ctx.font        = 'bold 13px monospace';
    ctx.textAlign   = 'center';
    ctx.fillText('RSU', cx, cy - 7);
    ctx.fillText('PORTFOLIO', cx, cy + 9);
}

// ── UTILIDADES ────────────────────────────────────────────────────────────────

function authHeader() {
    const t = sessionStorage.getItem('rsu_token');
    return t ? { 'Authorization': 'Bearer ' + t } : {};
}

// Exportar CSV
window.__carteraExportCSV = function() {
    if (!_carteraData) return;
    const rows = _carteraData.abiertas || [];
    const headers = ['Ticker','Fecha','P.Compra','P.Actual','P&L%','P&L$','Inversión','Valor Actual','Peso%','Comentario'];
    const lines = [headers.join(',')];
    rows.forEach(r => {
        lines.push([r.ticker, r.fecha, r.compra, r.actual, fix(r.pnl), fix(r.pnl_usd), r.inv, r.val_act, r.peso, '"' + (r.comment || '') + '"'].join(','));
    });
    const blob = new Blob([lines.join('\n')], { type:'text/csv' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = 'cartera_' + new Date().toISOString().slice(0,10) + '.csv';
    a.click();
};

// Refrescar precios manualmente
window.__carteraRefresh = async function() {
    const btn = document.querySelector('.refresh-btn');
    if (btn) btn.textContent = '⟳ Actualizando...';
    try {
        const res  = await fetch('/api/v1/cartera/prices', { headers: authHeader() });
        const data = await res.json();
        if (data.ok) applyLivePrices(data.prices, _carteraData?.abiertas || []);
    } catch(_) {}
    if (btn) btn.textContent = '⟳ Actualizar';
};