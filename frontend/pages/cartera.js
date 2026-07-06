// ─────────────────────────────────────────────────────────────────────────────
// RSU TERMINAL — CARTERA
// Posiciones activas con precios live, P&L recalculado, hipervínculos a Research,
// sparklines, indicadores WS por fila, exportar CSV, panel de riesgo.
// ─────────────────────────────────────────────────────────────────────────────

import { errorMessage } from '/core/ui.js';

let _ws        = null;
let _wsRetries = 0;
let _carteraData = null;

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

        html += sectionHeader('01 // POSICIONES ACTIVAS', true);

        if (data.abiertas && data.abiertas.length > 0) {
            html += riskPanel(data.abiertas);
            html += activeTable(data.abiertas);
        } else {
            html += emptyBox('Sin posiciones activas en este momento.');
        }

        html += sectionHeader('02 // ACTIVIDAD RECIENTE');
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
            + recentBox('ÚLTIMAS ENTRADAS', data.recent,    true)
            + recentBox('ÚLTIMAS SALIDAS',  data.cerradas ? data.cerradas.slice(0,5) : [], false)
            + '</div>';

        if (c && c.total > 0) {
            html += sectionHeader('03 // HISTORIAL CERRADAS');
            html += closedStats(c);
            html += closedTable(data.cerradas);
        }

        html += sectionHeader('04 // ASIGNACIÓN ESTRATÉGICA');
        html += allocationWidget();

        container.querySelector('#cartera-content').innerHTML = html;

        // Donut chart
        renderDonut();

        // Conectar WebSocket
        connectWS(data.abiertas || []);

    } catch(e) {
        container.querySelector('#cartera-content').innerHTML =
            errorMessage(e.message, {padding: '1.5rem', fontSize: '13px', extraStyle: 'background:var(--color-surface);border:1px solid #f2364566;border-radius:var(--radius);'});
    }
}

// ── WEBSOCKET ─────────────────────────────────────────────────────────────────

function connectWS(abiertas) {
    if (_ws) { try { _ws.close(); } catch(_) {} }

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

        _wsRetries++;
        if (_wsRetries < 5) {
            setTimeout(() => connectWS(abiertas), Math.min(5000 * _wsRetries, 30000));
        }
    };
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

        // Precio actual
        document.querySelectorAll(`[data-live-price="${ticker}"]`).forEach(el => {
            el.textContent = '$' + usd(price);
        });

        // Cambio intradiario
        document.querySelectorAll(`[data-live-chg="${ticker}"]`).forEach(el => {
            if (chg == null) return;
            const c = chg >= 0 ? 'var(--color-accent)' : '#f23645';
            el.style.color   = c;
            el.textContent   = (chg >= 0 ? '+' : '') + fix(chg) + '%';
        });

        // P&L % recalculado
        const pos = abiertas.find(a => a.ticker === ticker);
        if (pos && pos.compra > 0) {
            const pnl     = (price - pos.compra) / pos.compra * 100;
            const pnlUsd  = (price - pos.compra) * pos.shares;
            const pnlColor = pnl >= 0 ? 'var(--color-accent)' : '#f23645';

            document.querySelectorAll(`[data-live-pnl="${ticker}"]`).forEach(el => {
                el.style.color   = pnlColor;
                el.textContent   = (n(pnl) >= 0 ? '+' : '') + fix(pnl) + '%';
            });
            document.querySelectorAll(`[data-live-pnl-usd="${ticker}"]`).forEach(el => {
                el.style.color   = pnlColor;
                el.textContent   = (pnlUsd >= 0 ? '+$' : '-$') + usd(Math.abs(n(pnlUsd)));
            });
        }

        // Pulso en la fila
        const row = document.querySelector(`tr[data-row-ticker="${ticker}"]`);
        if (row) {
            row.classList.remove('row-pulse');
            void row.offsetWidth;
            row.classList.add('row-pulse');
        }

        // Indicador live por fila
        document.querySelectorAll(`[data-live-dot="${ticker}"]`).forEach(el => {
            el.className = 'row-live-dot active';
        });
    });
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
    return `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem;">
        ${metricCard('Capital Invertido',  '$' + usd(m.total_inv), 'Base de referencia', 'var(--color-text)')}
        ${metricCard('Valor de Mercado',   '$' + usd(m.total_val), valSign + fix(m.val_pct) + '% vs compra', valColor)}
        ${metricCard('P&L Neto (−comis.)', pnlSign + '$' + usd(Math.abs(n(m.pnl_neto))), pnlSign + fix(m.pnl_pct) + '% sobre capital', pnlColor)}
    </div>`;
}

function metricCard(label, value, sub, color) {
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;text-align:center;">
        <div style="color:var(--color-muted);font-size:11px;letter-spacing:.1em;margin-bottom:6px;">${label}</div>
        <div style="color:${color};font-size:22px;font-weight:500;">${value}</div>
        <div style="color:${color};font-size:11px;margin-top:4px;opacity:.7;">${sub}</div>
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

    return `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:1rem;">
        ${rCard('Mayor posición', biggest.ticker, biggest.peso + '% cartera', 'var(--color-text)')}
        ${rCard('Menor posición', smallest.ticker, smallest.peso + '% cartera', 'var(--color-muted)')}
        ${rCard('Mejor P&L', bestPnl.ticker, (bestPnl.pnl >= 0 ? '+' : '') + fix(bestPnl.pnl) + '%', 'var(--color-accent)')}
        ${rCard('Peor P&L', worstPnl.ticker, (worstPnl.pnl >= 0 ? '+' : '') + fix(worstPnl.pnl) + '%', '#f23645')}
    </div>`;
}

// ── TABLA DE POSICIONES ACTIVAS ───────────────────────────────────────────────

function activeTable(rows) {
    const heads = ['', 'FECHA', 'TICKER', 'P. COMPRA', 'P. ACTUAL', 'HOY %', 'P&L %', 'PESO', 'COMENTARIO'];
    const th = heads.map(h =>
        `<th style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;padding:8px 10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap;">${h}</th>`
    ).join('');

    const trs = rows.map(r => {
        const pnlColor = r.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
        const rowClass = r.pnl >= 0 ? 'cartera-tr row-profit' : 'cartera-tr row-loss';
        const chgColor = r.chg_hoy == null ? 'var(--color-muted)' : r.chg_hoy >= 0 ? 'var(--color-accent)' : '#f23645';
        const chgTxt   = r.chg_hoy == null ? '—' : (r.chg_hoy >= 0 ? '+' : '') + fix(r.chg_hoy) + '%';
        const comment  = r.comment || '—';
        const days     = Math.round((Date.now() - new Date(r.fecha.split('/').reverse().join('-'))) / 86400000);

        return `<tr class="${rowClass}" data-row-ticker="${r.ticker}" style="border-bottom:1px solid var(--color-border);position:relative;">
            <td style="padding:8px 10px;text-align:center;">
                <span class="row-live-dot" data-live-dot="${r.ticker}" title="Sin datos live"></span>
            </td>
            <td style="padding:8px 10px;color:var(--color-muted);font-size:11px;white-space:nowrap;">${r.fecha}</td>
            <td style="padding:8px 10px;">
                <span class="ticker-link" onclick="window.__navigate('/research?ticker=${r.ticker}')" title="Ver análisis en Research">${r.ticker}</span>
            </td>
            <td style="padding:8px 10px;color:var(--color-text);font-size:12px;">$${usd(r.compra)}</td>
            <td style="padding:8px 10px;color:var(--color-text);font-size:12px;" data-live-price="${r.ticker}">$${usd(r.actual)}</td>
            <td style="padding:8px 10px;font-size:11px;color:${chgColor};" data-live-chg="${r.ticker}">${chgTxt}</td>
            <td style="padding:8px 10px;font-size:12px;font-weight:500;" data-live-pnl="${r.ticker}">
                <span style="color:${pnlColor};">${r.pnl >= 0 ? '+' : ''}${fix(r.pnl)}%</span>
            </td>
            <td style="padding:8px 10px;min-width:80px;">
                <div style="color:var(--color-muted);font-size:10px;">${r.peso}%</div>
                <div class="peso-bar" style="width:${Math.min(r.peso * 3, 100)}%"></div>
            </td>
            <td style="padding:8px 10px;color:var(--color-muted);font-size:11px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${comment}">${comment}</td>
        </tr>`;
    }).join('');

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">
        <table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">
            <thead><tr>${th}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    </div>`;
}

// ── TABLA CERRADAS ────────────────────────────────────────────────────────────

function closedStats(c) {
    const wrColor  = c.win_rate >= 50 ? 'var(--color-accent)' : '#f23645';
    const pnlColor = c.avg_pnl  >= 0  ? 'var(--color-accent)' : '#f23645';
    return `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">
        ${metricCard('Trades Cerrados', c.total, c.ganadas + 'W / ' + c.perdidas + 'L', 'var(--color-text)')}
        ${metricCard('Win Rate', fix(c.win_rate,1) + '%', 'Operaciones ganadoras', wrColor)}
        ${metricCard('P&L Total Acum.', (c.avg_pnl >= 0 ? '+' : '') + fix(c.avg_pnl) + '%', 'Suma de cerradas', pnlColor)}
    </div>`;
}

function closedTable(rows) {
    const heads = ['FECHA', 'TICKER', 'P. COMPRA', 'P. SALIDA', 'P&L %', 'COMENTARIO'];
    const th = heads.map(h =>
        `<th style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;padding:8px 12px;border-bottom:1px solid var(--color-border);text-align:left;">${h}</th>`
    ).join('');

    const trs = rows.map(r => {
        const c = r.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
        return `<tr class="cartera-tr" style="border-bottom:1px solid var(--color-border);">
            <td style="padding:8px 12px;color:var(--color-muted);font-size:11px;">${r.fecha}</td>
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
            <span style="color:var(--color-muted);">${r.fecha}</span>
            <span class="ticker-link" onclick="window.__navigate('/research?ticker=${r.ticker}')">${r.ticker}</span>
            ${val}
        </div>`;
    }).join('') || `<div style="color:var(--color-muted);font-size:12px;padding:.5rem 0;">Sin datos.</div>`;

    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;">
        <div style="color:${color};font-size:12px;letter-spacing:.08em;margin-bottom:.75rem;">${title}</div>
        ${items}
    </div>`;
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