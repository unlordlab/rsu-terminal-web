import { tt } from '/components/tooltip.js';
import { errorMessage, esc } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = pageShell();
    loadAll(container);
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">🏛️ CONGRESS TRADING</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Operaciones bursátiles declaradas por el Congreso de EE.UU. · Datos públicos bajo el STOCK Act</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">Fuente: kadoa-org/congress-trading-monitor (agrega Senado eFD + Cámara Clerk + OGE) · No es asesoramiento de inversión</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="congress-search" type="text" placeholder="Buscar ticker (NVDA, AAPL...)" style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="congress-search-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">BUSCAR</button>'
        + '</div>'
        + '<div id="congress-ticker-result"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="congress-clusters"></div>'
        + '<div id="congress-sells"></div>'
        + '</div>'
        + '<div id="congress-buys"></div>';
}

async function loadAll(container) {
    const buyEl     = container.querySelector('#congress-buys');
    const sellEl    = container.querySelector('#congress-sells');
    const clusterEl = container.querySelector('#congress-clusters');
    const searchBtn = container.querySelector('#congress-search-btn');
    const searchInput = container.querySelector('#congress-search');
    const tickerEl  = container.querySelector('#congress-ticker-result');

    buyEl.innerHTML     = shell('COMPRAS RECIENTES', loading());
    sellEl.innerHTML    = shell('VENTAS RECIENTES', loading());
    clusterEl.innerHTML = shell('CLUSTER BUYING · SEÑAL FUERTE', loading());

    searchBtn.addEventListener('click', () => {
        const t = searchInput.value.trim().toUpperCase();
        if (t) loadTicker(t, tickerEl);
    });
    searchInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            const t = searchInput.value.trim().toUpperCase();
            if (t) loadTicker(t, tickerEl);
        }
    });

    // Deep-link ?ticker= -- mismo patrón que research.js/insider.js
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        searchInput.value = urlTicker.toUpperCase();
        loadTicker(urlTicker.toUpperCase(), tickerEl);
    }

    const token = sessionStorage.getItem('rsu_token');
    const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

    try {
        const [feedRes, clusterRes] = await Promise.all([
            fetch('/api/v1/congress/feed',     { headers }),
            fetch('/api/v1/congress/clusters', { headers }),
        ]);
        const feed     = await feedRes.json();
        const clusters = await clusterRes.json();

        if (!feed.ok) throw new Error(feed.error || 'Sin datos');

        const coverage = 'Últimos ' + (feed.window_days || 90) + ' días · ' + (feed.total || 0) + ' operaciones';
        buyEl.innerHTML     = renderBuys(feed.buys || [], coverage);
        sellEl.innerHTML    = renderSells(feed.sells || [], coverage);
        clusterEl.innerHTML = renderClusters(clusters.clusters || []);
    } catch(e) {
        buyEl.innerHTML     = shell('COMPRAS RECIENTES', error(e.message));
        sellEl.innerHTML    = shell('VENTAS RECIENTES', error(e.message));
        clusterEl.innerHTML = shell('CLUSTER BUYING', error(e.message));
    }
}

async function loadTicker(ticker, el) {
    el.innerHTML = shell('CONGRESS TRADING · ' + ticker, loading());
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/congress/ticker/' + ticker, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderTickerResult(ticker, data);
    } catch(e) {
        el.innerHTML = shell('CONGRESS TRADING · ' + ticker, error(e.message));
    }
}

// ── RENDERS ───────────────────────────────────────────────────────────────────

function chamberLabel(c) {
    if (c === 'senate') return 'Senado';
    if (c === 'house')  return 'Cámara';
    return '—';
}

function partyState(row) {
    const p = row.party || '';
    const s = row.state || '';
    if (!p && !s) return '—';
    return (p + (s ? '-' + s : '')).trim();
}

function daysLabel(row) {
    const d = (row.days_to_file != null) ? row.days_to_file + 'd' : '—';
    return row.is_late ? d + ' ⚠️' : d;
}

function renderBuys(buys, coverage) {
    if (!buys.length) return shell('COMPRAS RECIENTES', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin compras registradas todavía en la ventana actual</div>', coverage);

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 60px 100px 60px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>CONGRESISTA</div><div>PARTIDO</div><div>IMPORTE ' + tt('congress-amount-range') + '</div><div>PLAZO ' + tt('congress-days-to-file') + '</div>'
        + '</div>';

    const rows = buys.map(b => '<div style="display:grid;grid-template-columns:80px 70px 1fr 60px 100px 60px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + esc(b.transaction_date || '—') + '</div>'
        + '<div onclick="goToResearch(\'' + esc(b.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(b.ticker) + badges(b) + '</div>'
        + '<div style="color:var(--color-text);">' + esc(b.filer_name || '—') + ' <span style="color:var(--color-muted);font-size:10px;">(' + esc(chamberLabel(b.chamber)) + ')</span></div>'
        + '<div style="color:var(--color-muted);font-size:10px;">' + esc(partyState(b)) + '</div>'
        + '<div style="color:var(--color-accent);font-weight:500;">' + esc(b.amount_range_label || '—') + '</div>'
        + '<div style="color:' + (b.is_late ? '#f23645' : 'var(--color-muted)') + ';">' + daysLabel(b) + '</div>'
        + '</div>'
    ).join('');

    return shell('COMPRAS RECIENTES', header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', coverage);
}

function renderSells(sells, coverage) {
    if (!sells.length) return shell('VENTAS RECIENTES', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin ventas registradas todavía en la ventana actual</div>', coverage);

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 100px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>CONGRESISTA</div><div>IMPORTE</div>'
        + '</div>';

    const rows = sells.map(s => '<div style="display:grid;grid-template-columns:80px 70px 1fr 100px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + esc(s.transaction_date || '—') + '</div>'
        + '<div onclick="goToResearch(\'' + esc(s.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(s.ticker) + badges(s) + '</div>'
        + '<div style="color:var(--color-text);">' + esc(s.filer_name || '—') + ' <span style="color:var(--color-muted);font-size:10px;">(' + esc(chamberLabel(s.chamber)) + ')</span></div>'
        + '<div style="color:#f23645;font-weight:500;">' + esc(s.amount_range_label || '—') + '</div>'
        + '</div>'
    ).join('');

    return shell('VENTAS RECIENTES', header + '<div style="overflow-y:auto;max-height:300px;">' + rows + '</div>', coverage);
}

function renderClusters(clusters) {
    if (!clusters.length) return shell('CLUSTER BUYING · SEÑAL FUERTE', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin clusters detectados — todos los congresistas actúan individualmente</div>');

    const rows = clusters.map(c => '<div style="padding:12px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span onclick="goToResearch(\'' + esc(c.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-size:16px;font-weight:500;">' + esc(c.ticker) + badges(c) + '</span>'
        + '<span style="color:var(--color-muted);font-size:11px;">' + esc(c.asset_name || '') + '</span>'
        + '</div>'
        + '<span style="background:' + (c.signal === 'FUERTE' ? '#00ffad' : '#ffb800') + '22;color:' + (c.signal === 'FUERTE' ? 'var(--color-accent)' : '#ffb800') + ';border:1px solid;border-radius:3px;padding:2px 8px;font-size:10px;">' + esc(c.signal) + '</span> ' + tt('congress-cluster')
        + '</div>'
        + '<div style="display:flex;gap:2rem;font-size:11px;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);">' + esc(c.n_filers) + ' congresistas · <span style="color:var(--color-accent);">mín. ' + fmtVal(c.min_total_usd) + '</span></span>'
        + '</div>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        + c.filers.map(f => '<span style="background:var(--color-surface2);border-radius:3px;padding:2px 8px;font-size:10px;color:var(--color-muted);">' + esc(f) + '</span>').join('')
        + '</div>'
        + '</div>'
    ).join('');

    return shell('CLUSTER BUYING · SEÑAL FUERTE', rows);
}

function renderTickerResult(ticker, data) {
    if (!data.trades || !data.trades.length) {
        return shell('CONGRESS TRADING · ' + ticker, '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin operaciones recientes de congresistas</div>');
    }

    const header = '<div style="display:grid;grid-template-columns:80px 1fr 70px 60px 100px 60px 40px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>CONGRESISTA</div><div>CÁMARA</div><div>TIPO</div><div>IMPORTE</div><div>PLAZO</div><div>DOC</div>'
        + '</div>';

    const rows = data.trades.map(t => {
        const isBuy = t.direction === 'buy';
        return '<div style="display:grid;grid-template-columns:80px 1fr 70px 60px 100px 60px 40px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + esc(t.transaction_date || '—') + '</div>'
            + '<div style="color:var(--color-text);">' + esc(t.filer_name || '—') + ' <span style="color:var(--color-muted);font-size:10px;">(' + esc(partyState(t)) + ')</span></div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + esc(chamberLabel(t.chamber)) + '</div>'
            + '<div style="background:' + (isBuy ? 'rgba(0,255,173,0.1)' : 'rgba(242,54,69,0.1)') + ';color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';border-radius:3px;padding:2px 6px;font-size:10px;text-align:center;">' + esc(isBuy ? 'COMPRA' : 'VENTA') + '</div>'
            + '<div style="color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';font-weight:500;">' + esc(t.amount_range_label || '—') + '</div>'
            + '<div style="color:' + (t.is_late ? '#f23645' : 'var(--color-muted)') + ';">' + daysLabel(t) + '</div>'
            + '<div>' + (t.doc_url ? '<a href="' + esc(t.doc_url) + '" target="_blank" rel="noopener noreferrer" style="color:var(--color-muted);">↗</a>' : '—') + '</div>'
            + '</div>';
    }).join('');

    return shell('CONGRESS TRADING · ' + ticker, header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', data.total + ' operaciones en la ventana disponible');
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function shell(title, content, subtitle) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + esc(title) + '</div>'
        + (subtitle ? '<div style="color:var(--color-muted);font-size:10px;">' + esc(subtitle) + '</div>' : '')
        + '</div>'
        + content
        + '</div>';
}

function fmtVal(val) {
    if (!val) return '—';
    const v = Number(val);
    if (v >= 1e9) return '$' + (v/1e9).toFixed(1) + 'B';
    if (v >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v.toLocaleString('en-US');
}

// Badges de cruce -- mismo criterio que insider.js/rsrw.js (Fase 3 del
// roadmap). Sin ⚡ de confluencia en esta v1 (fuera de alcance).
function badges(row) {
    return (row.en_cartera ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '')
        + (row.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '');
}

function loading() { return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando datos del Congreso...</div>'; }
function error(msg) { return errorMessage(msg); }
