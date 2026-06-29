import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = pageShell();
    loadAll(container);
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">🔍 INSIDER FLOW</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Transacciones de directivos · SEC EDGAR Form 4 · Datos oficiales</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="insider-search" type="text" placeholder="Buscar ticker (NVDA, AAPL...)" style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="insider-search-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">BUSCAR</button>'
        + '</div>'
        + '<div id="insider-ticker-result"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="insider-clusters"></div>'
        + '<div id="insider-sells"></div>'
        + '</div>'
        + '<div id="insider-buys"></div>';
}

async function loadAll(container) {
    const buyEl      = container.querySelector('#insider-buys');
    const sellEl     = container.querySelector('#insider-sells');
    const clusterEl  = container.querySelector('#insider-clusters');
    const searchBtn  = container.querySelector('#insider-search-btn');
    const searchInput = container.querySelector('#insider-search');
    const tickerEl   = container.querySelector('#insider-ticker-result');

    buyEl.innerHTML     = shell('COMPRAS RECIENTES · TOP DIRECTIVOS', loading());
    sellEl.innerHTML    = shell('VENTAS RECIENTES', loading());
    clusterEl.innerHTML = shell('CLUSTER BUYING · SEÑAL FUERTE', loading());

    // Búsqueda por ticker
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

    // Cargar feed y clusters en paralelo
    const token = sessionStorage.getItem('rsu_token');
    const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

    try {
        const [feedRes, clusterRes] = await Promise.all([
            fetch('/api/v1/insider/feed',     { headers }),
            fetch('/api/v1/insider/clusters', { headers }),
        ]);
        const feed    = await feedRes.json();
        const clusters = await clusterRes.json();

        if (!feed.ok) throw new Error(feed.error || 'Sin datos');

        buyEl.innerHTML     = renderBuys(feed.buys || []);
        sellEl.innerHTML    = renderSells(feed.sells || []);
        clusterEl.innerHTML = renderClusters(clusters.clusters || []);

    } catch(e) {
        buyEl.innerHTML  = shell('COMPRAS RECIENTES', error(e.message));
        sellEl.innerHTML = shell('VENTAS RECIENTES', error(e.message));
        clusterEl.innerHTML = shell('CLUSTER BUYING', error(e.message));
    }
}

async function loadTicker(ticker, el) {
    el.innerHTML = shell('INSIDER TRANSACTIONS · ' + ticker, loading());
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/insider/ticker/' + ticker, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderTickerResult(ticker, data);
    } catch(e) {
        el.innerHTML = shell('INSIDER · ' + ticker, error(e.message));
    }
}

// ── RENDERS ───────────────────────────────────────────────────────────────────

function renderBuys(buys) {
    if (!buys.length) return shell('COMPRAS RECIENTES · TOP DIRECTIVOS', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin compras significativas recientes</div>');

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 120px 90px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>INSIDER</div><div>CARGO</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = buys.map(b => '<div style="display:grid;grid-template-columns:80px 70px 1fr 120px 90px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + (b.date || '—') + '</div>'
        + '<div onclick="goToResearch(\'' + b.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + b.ticker + '</div>'
        + '<div style="color:var(--color-text);">' + (b.insider_name || '—') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">' + (b.title || '—').substring(0, 20) + '</div>'
        + '<div style="color:var(--color-text);">' + Number(b.shares || 0).toLocaleString('en-US') + '</div>'
        + '<div style="color:var(--color-accent);font-weight:500;">' + fmtVal(b.value) + '</div>'
        + '</div>'
    ).join('');

    return shell('COMPRAS RECIENTES · TOP DIRECTIVOS', header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', 'SEC EDGAR Form 4');
}

function renderSells(sells) {
    if (!sells.length) return shell('VENTAS RECIENTES', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin ventas significativas recientes</div>');

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 90px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>INSIDER</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = sells.map(s => '<div style="display:grid;grid-template-columns:80px 70px 1fr 90px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + (s.date || '—') + '</div>'
        + '<div onclick="goToResearch(\'' + s.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + s.ticker + '</div>'
        + '<div style="color:var(--color-text);">' + (s.insider_name || '—') + '</div>'
        + '<div style="color:var(--color-text);">' + Number(s.shares || 0).toLocaleString('en-US') + '</div>'
        + '<div style="color:#f23645;font-weight:500;">' + fmtVal(s.value) + '</div>'
        + '</div>'
    ).join('');

    return shell('VENTAS RECIENTES', header + '<div style="overflow-y:auto;max-height:300px;">' + rows + '</div>', 'SEC EDGAR Form 4');
}

function renderClusters(clusters) {
    if (!clusters.length) return shell('CLUSTER BUYING · SEÑAL FUERTE', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin clusters detectados — todos los insiders actúan individualmente</div>');

    const rows = clusters.map(c => '<div style="padding:12px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span onclick="goToResearch(\'' + c.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-size:16px;font-weight:500;">' + c.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:11px;">' + c.company + '</span>'
        + '</div>'
        + '<span style="background:' + c.signal_color + '22;color:' + c.signal_color + ';border:1px solid ' + c.signal_color + '44;border-radius:3px;padding:2px 8px;font-size:10px;">' + c.signal + '</span>'
        + '</div>'
        + '<div style="display:flex;gap:2rem;font-size:11px;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);">' + c.n_insiders + ' insiders · <span style="color:var(--color-accent);">' + fmtVal(c.total_value) + ' total</span></span>'
        + '<span style="color:var(--color-muted);">' + Number(c.total_shares).toLocaleString('en-US') + ' acciones</span>'
        + '</div>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        + c.insiders.map(i => '<span style="background:var(--color-surface2);border-radius:3px;padding:2px 8px;font-size:10px;color:var(--color-muted);">' + i.name + ' · ' + fmtVal(i.value) + '</span>').join('')
        + '</div>'
        + '</div>'
    ).join('');

    return shell('CLUSTER BUYING · SEÑAL FUERTE', rows);
}

function renderTickerResult(ticker, data) {
    if (!data.transactions || !data.transactions.length) {
        return shell('INSIDER · ' + ticker, '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin transacciones recientes (últimos 6 meses)</div>');
    }

    const summary = '<div style="display:flex;gap:2rem;padding:10px 14px;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:var(--color-muted);">Compras: <span style="color:var(--color-accent);">' + data.buys + '</span></span>'
        + '<span style="color:var(--color-muted);">Ventas: <span style="color:#f23645;">' + data.sells + '</span></span>'
        + '<span style="color:var(--color-muted);">Total: ' + data.transactions.length + ' transacciones</span>'
        + '</div>';

    const header = '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 70px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>INSIDER</div><div>CARGO</div><div>TIPO</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = data.transactions.map(t => {
        const isBuy = t.type_code === 'P';
        return '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 70px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + (t.date || '—') + '</div>'
            + '<div style="color:var(--color-text);">' + (t.insider_name || '—') + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + (t.title || '—').substring(0, 20) + '</div>'
            + '<div style="background:' + (isBuy ? 'rgba(0,255,173,0.1)' : 'rgba(242,54,69,0.1)') + ';color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';border-radius:3px;padding:2px 6px;font-size:10px;text-align:center;">' + t.type + '</div>'
            + '<div style="color:var(--color-text);">' + Number(t.shares || 0).toLocaleString('en-US') + '</div>'
            + '<div style="color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';font-weight:500;">' + fmtVal(t.value) + '</div>'
            + '</div>';
    }).join('');

    return shell('INSIDER TRANSACTIONS · ' + ticker, summary + header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', 'SEC EDGAR Form 4 · Últimos 6 meses');
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function shell(title, content, subtitle) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + title + '</div>'
        + (subtitle ? '<div style="color:var(--color-muted);font-size:10px;">' + subtitle + '</div>' : '')
        + '</div>'
        + content
        + '</div>';
}

function fmtVal(val) {
    if (!val) return '—';
    const v = Number(val);
    if (v >= 1e9)  return '$' + (v/1e9).toFixed(1) + 'B';
    if (v >= 1e6)  return '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3)  return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v.toLocaleString('en-US');
}

function loading() { return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando datos SEC EDGAR...</div>'; }
function error(msg) { return errorMessage(msg); }