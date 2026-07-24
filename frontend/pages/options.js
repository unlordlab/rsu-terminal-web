import { tt } from '/components/tooltip.js';
import { errorMessage, esc } from '/core/ui.js';

function _fmtFecha(iso) {
    // "2026-07-14" -> "14/07/2026" — mismo formato d/m/a usado en el resto de la terminal
    if (!iso || typeof iso !== 'string' || iso.length < 10) return iso || '—';
    const [y, m, d] = iso.slice(0, 10).split('-');
    if (!y || !m || !d) return iso;
    return `${d}/${m}/${y}`;
}

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

// Badges de cruce -- Fase 3 del roadmap: ⭐ si está en la Watchlist del
// usuario, ⚡ si además hay señal de compra insider simultánea en el mismo
// ticker (confluencia "dinero inteligente"). 💼 (Cartera) ya se pintaba a
// mano donde hacía falta antes de esta sesión, se deja igual.
function badges(row) {
    return (row.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '')
        + (row.is_confluence ? ' <span title="Señal alcista simultánea en Insider Flow">⚡</span>' : '');
}

let currentTicker = null;
let currentPeriod = '1w';

export async function render(container) {
    container.innerHTML = pageHeader() + '<div id="options-body"></div>';
    setupSearch(container);
    loadDashboard(container);
}

function pageHeader() {
    return `
    <div style="margin-bottom:1.5rem;">
        <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;margin-bottom:1rem;">OPTIONS FLOW ${tt('options-flow')}</div>
        <div style="display:flex;gap:8px;">
            <input id="opt-search-input" type="text" placeholder="Buscar ticker (NVDA, TSLA...)" style="flex:1;max-width:320px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;text-transform:uppercase;">
            <button id="opt-search-btn" style="background:var(--color-accent);color:var(--color-bg,#0a0a0a);border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">BUSCAR</button>
            <button id="opt-back-btn" style="display:none;background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← Volver</button>
        </div>
    </div>`;
}

function setupSearch(container) {
    const input   = container.querySelector('#opt-search-input');
    const btn     = container.querySelector('#opt-search-btn');
    const backBtn = container.querySelector('#opt-back-btn');
    const buscar  = () => {
        const t = input.value.trim().toUpperCase();
        if (!t) return;
        backBtn.style.display = 'inline-block';
        loadTicker(t, '1w');
    };
    btn.addEventListener('click', buscar);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') buscar(); });
    backBtn.addEventListener('click', () => {
        backBtn.style.display = 'none';
        input.value = '';
        currentTicker = null;
        loadDashboard(container);
    });
}

// ── DASHBOARD (vista por defecto) ───────────────────────────────────────────

async function loadDashboard(container) {
    const body = container.querySelector('#options-body');
    body.innerHTML = loading();
    try {
        const res  = await fetch('/api/v1/options/flow-simple', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) { body.innerHTML = errorMessage(data.error || 'Sin datos'); return; }
        body.innerHTML = renderDashboard(data);
    } catch (e) {
        body.innerHTML = errorMessage(e.message);
    }
}

function renderDashboard(data) {
    const fechaDatos = data.scan_date
        ? `<div style="color:var(--color-muted);font-size:11px;margin-bottom:10px;">📊 Datos del escaneo: <span style="color:var(--color-text);font-weight:600;">${esc(_fmtFecha(data.scan_date))}</span></div>`
        : '';

    const biasColor = data.dia_bias_label === 'ALCISTA' ? 'var(--color-accent)' : (data.dia_bias_label === 'BAJISTA' ? '#f23645' : 'var(--color-muted)');
    const biasBanner = data.dia_bias_pct != null
        ? `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:12px 16px;margin-bottom:1rem;font-size:13px;">
            <span style="color:var(--color-muted);">Hoy: </span><span style="color:${biasColor};font-weight:700;">${esc(data.dia_bias_pct)}% ${esc(data.dia_bias_label)}</span><span style="color:var(--color-muted);"> por prima (Calls Bought + Puts Sold vs. Puts Bought + Calls Sold) ${tt('options-dia-bias')}</span>
        </div>`
        : '';

    const tickerListBox = (title, items) => `
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:14px;flex:1;min-width:220px;">
            <div style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;margin-bottom:10px;">${title}</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
                ${items.length ? items.map(t => `<span onclick="window.__optionsSearchTicker('${esc(t.ticker)}')" style="cursor:pointer;color:var(--color-accent);font-size:12px;font-weight:600;padding:3px 8px;background:var(--color-bg,#0a0a0a);border-radius:3px;border:1px solid var(--color-border);">${esc(t.ticker)}${badges(t)}${t.premium_fmt ? ' <span style="color:var(--color-muted);font-weight:400;">' + esc(t.premium_fmt) + '</span>' : ''}</span>`).join('') : '<span style="color:var(--color-muted);font-size:11px;">Sin datos todavía</span>'}
            </div>
        </div>`;

    const topBoxes = `<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:1.5rem;">
        ${tickerListBox('TOP PREMIUM', data.top_premium)}
        ${tickerListBox('TOP BULLISH', data.top_bullish)}
        ${tickerListBox('TOP BEARISH', data.top_bearish)}
    </div>`;

    const flowTables = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:1.5rem;">
        ${flowTable(`CALLS BOUGHT ${tt('options-categories')}`, data.calls_bought, 'var(--color-accent)')}
        ${flowTable('PUTS SOLD', data.puts_sold, 'var(--color-accent)')}
        ${flowTable('PUTS BOUGHT', data.puts_bought, '#f23645')}
        ${flowTable('CALLS SOLD', data.calls_sold, '#f23645')}
    </div>`;

    const oiTables = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        ${oiTable(`LARGE OI INCREASE ${tt('options-large-oi')}`, data.large_oi_increase, 'var(--color-accent)', '▲')}
        ${oiTable('LARGE OI DECREASE', data.large_oi_decrease, '#f23645', '▼')}
    </div>`;

    const nota = data.large_oi_increase && data.large_oi_increase.length === 0 && data.large_oi_decrease.length === 0
        ? '<div style="color:var(--color-muted);font-size:11px;margin-top:10px;">Los cambios de Open Interest necesitan al menos 2 días de histórico guardado — aparecerán a partir de mañana.</div>'
        : '';

    return fechaDatos + biasBanner + topBoxes + flowTables + oiTables + nota;
}

function flowTable(title, rows, color) {
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${title}</span>
            <span style="color:var(--color-muted);font-size:11px;">${rows.length}</span>
        </div>
        <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);letter-spacing:0.05em;">
            <div>TICKER</div><div>STRIKE</div><div>EXP</div><div style="text-align:right;">PREMIUM</div>
        </div>
        <div style="max-height:340px;overflow-y:auto;">
            ${rows.length ? rows.map(r => `
            <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">
                <span onclick="window.__optionsSearchTicker('${esc(r.ticker)}')" style="cursor:pointer;color:${color};font-weight:600;">${esc(r.ticker)}${r.near_earnings ? ' <span title="Vencimiento cerca de la fecha de earnings">📅</span>' : ''}${badges(r)}${r.es_repetida ? ' <span title="Mismo contrato repetido en días anteriores">🔁</span>' : ''}</span>
                <span style="color:var(--color-text);">$${esc(r.strike)} <span style="color:var(--color-muted);">(${esc(r.strike_pct)})</span></span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(r.exp))}</span>
                <span style="color:var(--color-text);text-align:right;">${esc(r.premium_fmt)}</span>
            </div>`).join('') : '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin entradas hoy</div>'}
        </div>
    </div>`;
}

function oiTable(title, rows, color, arrow) {
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${title}</span>
            <span style="color:var(--color-muted);font-size:11px;">${rows.length}</span>
        </div>
        <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);letter-spacing:0.05em;">
            <div>TICKER</div><div>STRIKE</div><div>EXP</div><div style="text-align:right;">CAMBIO OI</div>
        </div>
        <div style="max-height:280px;overflow-y:auto;">
            ${rows.length ? rows.map(r => `
            <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">
                <span onclick="window.__optionsSearchTicker('${esc(r.ticker)}')" style="cursor:pointer;color:${color};font-weight:600;">${esc(r.ticker)}</span>
                <span style="color:var(--color-text);">$${esc(r.strike)}</span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(r.exp))}</span>
                <span style="color:${color};text-align:right;">${arrow} ${Math.abs(r.daily_pct)}%</span>
            </div>`).join('') : '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin datos todavía</div>'}
        </div>
    </div>`;
}

// ── VISTA POR TICKER ─────────────────────────────────────────────────────────

window.__optionsSearchTicker = function(ticker) {
    const input   = document.querySelector('#opt-search-input');
    const backBtn = document.querySelector('#opt-back-btn');
    if (input) input.value = ticker;
    if (backBtn) backBtn.style.display = 'inline-block';
    loadTicker(ticker, '1w');
};

async function loadTicker(ticker, period) {
    currentTicker = ticker;
    currentPeriod = period;
    const body = document.querySelector('#options-body');
    if (!body) return;
    body.innerHTML = loading();
    try {
        // GEX en paralelo, sin bloquear el render de flujo si falla o
        // tarda -- es una sección adicional, no crítica para la vista
        // principal (mismo criterio de resiliencia que el resto del proyecto).
        const [flowRes, gexRes] = await Promise.all([
            fetch('/api/v1/options/ticker-flow/' + ticker + '?period=' + period, { headers: authHeader() }),
            fetch('/api/v1/options/gex/' + ticker, { headers: authHeader() }).catch(() => null),
        ]);
        const data = await flowRes.json();
        const gex  = gexRes ? await gexRes.json().catch(() => ({ ok: false })) : { ok: false };
        if (!data.ok) { body.innerHTML = errorMessage(data.error || 'Sin datos'); return; }
        body.innerHTML = renderTicker(data) + renderGex(gex);
        wireTickerPeriods(body);
    } catch (e) {
        body.innerHTML = errorMessage(e.message);
    }
}

function renderGex(gex) {
    if (!gex || !gex.ok) return '';   // silencioso si falla -- GEX es un extra, no rompe la vista principal
    const color = gex.total_gex >= 0 ? 'var(--color-accent)' : '#f23645';
    const regimenTxt = gex.regimen === 'POSITIVO'
        ? 'Dealers tienden a amortiguar el movimiento (compran en caídas, venden en subidas)'
        : 'Dealers tienden a amplificar el movimiento (venden en caídas, compran en subidas)';
    const maxAbs = Math.max(...gex.by_strike.map(x => Math.abs(x.gex)), 1);
    const rows = gex.by_strike.map(r => {
        const barColor = r.gex >= 0 ? 'var(--color-accent)' : '#f23645';
        const pct = Math.abs(r.gex) / maxAbs * 100;
        return `<div style="display:grid;grid-template-columns:80px 1fr 90px;gap:8px;padding:5px 14px;align-items:center;font-size:11px;">
            <span style="color:var(--color-text);">$${esc(r.strike)}</span>
            <div style="background:var(--color-bg,#0a0a0a);border-radius:3px;height:6px;"><div style="height:100%;width:${pct}%;background:${barColor};border-radius:3px;"></div></div>
            <span style="color:${barColor};text-align:right;">${esc(r.gex_fmt)}</span>
        </div>`;
    }).join('');
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-top:1rem;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;align-items:center;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">GAMMA EXPOSURE (GEX) ${tt('options-gex')}</span>
            <span style="color:${color};font-size:16px;font-weight:700;">${esc(gex.total_gex_fmt)} <span style="font-size:10px;color:var(--color-muted);font-weight:400;">/ 1% mov.</span></span>
        </div>
        <div style="padding:8px 14px;font-size:11px;color:var(--color-muted);border-bottom:1px solid var(--color-border);">${esc(regimenTxt)}</div>
        ${rows}
    </div>`;
}

function wireTickerPeriods(scope) {
    scope.querySelectorAll('.opt-period-btn').forEach(btn => {
        btn.addEventListener('click', () => loadTicker(currentTicker, btn.dataset.period));
    });
}

const PERIODS = [
    { key: '1w', label: '1 Semana' }, { key: '2w', label: '2 Semanas' },
    { key: '1m', label: '1 Mes' }, { key: '3m', label: '3 Meses' }, { key: '4m', label: '4 Meses' },
];

function renderTicker(data) {
    const scoreColor = data.net_score > 0 ? 'var(--color-accent)' : (data.net_score < 0 ? '#f23645' : 'var(--color-muted)');
    const periodBtns = PERIODS.map(p => `
        <button class="opt-period-btn" data-period="${p.key}" style="background:${p.key === currentPeriod ? 'var(--color-accent)' : 'transparent'};color:${p.key === currentPeriod ? 'var(--color-bg,#0a0a0a)' : 'var(--color-muted)'};border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">${p.label}</button>
    `).join('');

    return `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;flex-wrap:wrap;gap:12px;">
        <div>
            <div style="color:var(--color-text);font-size:24px;font-weight:700;margin-bottom:10px;">${esc(data.ticker)} <span onclick="window.__navigate('/research?ticker=${esc(data.ticker)}')" style="cursor:pointer;color:var(--color-accent);font-size:12px;font-weight:400;text-decoration:underline;vertical-align:middle;" title="Ver análisis completo en Research">→ Research</span>${data.en_cartera ? ' <span style="font-size:12px;background:var(--color-accent);color:var(--color-bg,#0a0a0a);padding:3px 8px;border-radius:3px;vertical-align:middle;">💼 EN CARTERA</span>' : ''}${data.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : ''}${data.is_confluence ? ' <span title="Señal alcista simultánea en Insider Flow">⚡</span>' : ''}</div>
            <div style="display:flex;gap:6px;">${periodBtns}</div>
        </div>
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);min-width:180px;overflow:hidden;">
            <div style="padding:8px 14px;border-bottom:1px solid var(--color-border);color:var(--color-muted);font-size:11px;text-align:center;">NET SCORE ${tt('options-net-score')}</div>
            <div style="padding:14px;color:${scoreColor};font-size:22px;font-weight:700;text-align:center;">${data.net_score > 0 ? '+' : ''}${esc(data.net_score)}</div>
        </div>
    </div>
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">TOTAL</span>
            <span style="color:var(--color-muted);font-size:11px;">${esc(data.total)}</span>
        </div>
        <div style="display:grid;grid-template-columns:90px 100px 90px 90px 60px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">
            <div>TRADE DATE</div><div>ORDER TYPE</div><div>STRIKE</div><div>EXP</div><div>OI</div><div style="text-align:right;">PREMIUM</div>
        </div>
        ${data.entradas.map(e => {
            const bullish = e.order_type === 'Buy Call' || e.order_type === 'Sell Put';
            const badgeColor = bullish ? 'var(--color-accent)' : '#f23645';
            return `<div style="display:grid;grid-template-columns:90px 100px 90px 90px 60px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;">
                <span style="color:var(--color-muted);">${esc(_fmtFecha(e.fecha))}</span>
                <span style="background:${badgeColor}22;border:1px solid ${badgeColor}88;color:${badgeColor};border-radius:3px;padding:2px 7px;font-size:10px;text-align:center;">${esc(e.order_type)}${e.es_repetida ? ' <span title="Mismo contrato repetido en días anteriores">🔁</span>' : ''}</span>
                <span style="color:var(--color-text);">$${esc(e.strike)}</span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(e.exp))}${e.near_earnings ? ' <span title="Vencimiento cerca de la fecha de earnings">📅</span>' : ''}</span>
                <span style="color:var(--color-text);">${esc(e.oi)}</span>
                <span style="color:var(--color-text);text-align:right;">${esc(e.premium_fmt)}</span>
            </div>`;
        }).join('') || '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin entradas guardadas en este periodo</div>'}
    </div>`;
}

function loading() {
    return '<div style="padding:2rem;text-align:center;color:var(--color-muted);font-size:12px;">Cargando...</div>';
}