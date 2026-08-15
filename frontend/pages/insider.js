import { authHeader } from '/core/api.js';
import { tt } from '/components/tooltip.js';
import { errorMessage, esc, fmtFecha, fmtFechaHora, panel } from '/core/ui.js';

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
        + '<div id="insider-diag" style="margin-bottom:0.75rem;"></div>'
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

    // Deep-link ?ticker= -- mismo patrón que research.js
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        searchInput.value = urlTicker.toUpperCase();
        loadTicker(urlTicker.toUpperCase(), tickerEl);
    }

    // Cargar feed y clusters en paralelo
    const headers = authHeader();

    try {
        const [feedRes, clusterRes] = await Promise.all([
            fetch('/api/v1/insider/feed',     { headers }),
            fetch('/api/v1/insider/clusters', { headers }),
        ]);
        const feed    = await feedRes.json();
        const clusters = await clusterRes.json();

        if (!feed.ok) throw new Error(feed.error || 'Sin datos');

        const coverage = 'Últimos ' + (feed.window_days || 10) + ' días · ' + (feed.total || 0)
            + ' transacciones acumuladas · más recientes primero';
        buyEl.innerHTML     = renderBuys(feed.buys || [], coverage);
        sellEl.innerHTML    = renderSells(feed.sells || [], coverage);
        clusterEl.innerHTML = renderClusters(clusters.clusters || []);

        const diagEl = container.querySelector('#insider-diag');
        if (diagEl) diagEl.innerHTML = renderDiagnostic(feed.last_ingest_log);

    } catch(e) {
        buyEl.innerHTML  = shell('COMPRAS RECIENTES', error(e.message));
        sellEl.innerHTML = shell('VENTAS RECIENTES', error(e.message));
        clusterEl.innerHTML = shell('CLUSTER BUYING', error(e.message));
    }
}

async function loadTicker(ticker, el) {
    // Nota: shell() ya escapa `title` internamente -- no escapar `ticker` aquí
    // también, o se doble-escaparía (p.ej. "&" -> "&amp;" -> "&amp;amp;").
    el.innerHTML = shell('INSIDER TRANSACTIONS · ' + ticker, loading());
    try {
        const res   = await fetch('/api/v1/insider/ticker/' + ticker, {
            headers: authHeader()
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderTickerResult(ticker, data);
    } catch(e) {
        el.innerHTML = shell('INSIDER · ' + ticker, error(e.message));
    }
}

// ── RENDERS ───────────────────────────────────────────────────────────────────

function renderBuys(buys, coverage) {
    if (!buys.length) return shell('COMPRAS RECIENTES · TOP DIRECTIVOS', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin compras significativas registradas todavía — el histórico se va acumulando cada 20 min</div>', coverage);

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 120px 90px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>INSIDER</div><div>CARGO</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = buys.map(b => '<div style="display:grid;grid-template-columns:80px 70px 1fr 120px 90px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + esc(fmtFecha(b.date)) + '</div>'
        + '<div onclick="goToResearch(\'' + esc(b.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(b.ticker) + badges(b) + '</div>'
        + '<div style="color:var(--color-text);">' + esc(b.insider_name || '—') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">' + esc((b.title || '—').substring(0, 20)) + '</div>'
        + '<div style="color:var(--color-text);">' + Number(b.shares || 0).toLocaleString('en-US') + '</div>'
        + '<div style="color:var(--color-accent);font-weight:500;">' + fmtVal(b.value) + '</div>'
        + '</div>'
    ).join('');

    return shell('COMPRAS RECIENTES · TOP DIRECTIVOS', header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', coverage);
}

function renderSells(sells, coverage) {
    if (!sells.length) return shell('VENTAS RECIENTES', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin ventas significativas registradas todavía — el histórico se va acumulando cada 20 min</div>', coverage);

    const header = '<div style="display:grid;grid-template-columns:80px 70px 1fr 90px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>INSIDER</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = sells.map(s => '<div style="display:grid;grid-template-columns:80px 70px 1fr 90px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<div style="color:var(--color-muted);">' + esc(fmtFecha(s.date)) + '</div>'
        + '<div onclick="goToResearch(\'' + esc(s.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(s.ticker) + badges(s) + '</div>'
        + '<div style="color:var(--color-text);">' + esc(s.insider_name || '—') + '</div>'
        + '<div style="color:var(--color-text);">' + Number(s.shares || 0).toLocaleString('en-US') + '</div>'
        + '<div style="color:#f23645;font-weight:500;">' + fmtVal(s.value) + '</div>'
        + '</div>'
    ).join('');

    return shell('VENTAS RECIENTES', header + '<div style="overflow-y:auto;max-height:300px;">' + rows + '</div>', coverage);
}

function renderClusters(clusters) {
    if (!clusters.length) return shell('CLUSTER BUYING · SEÑAL FUERTE', '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin clusters detectados — todos los insiders actúan individualmente</div>');

    const rows = clusters.map(c => '<div style="padding:12px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span onclick="goToResearch(\'' + esc(c.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-size:16px;font-weight:500;">' + esc(c.ticker) + badges(c) + '</span>'
        + '<span style="color:var(--color-muted);font-size:11px;">' + esc(c.company) + '</span>'
        + '</div>'
        + '<span style="background:' + esc(c.signal_color) + '22;color:' + esc(c.signal_color) + ';border:1px solid ' + esc(c.signal_color) + '44;border-radius:3px;padding:2px 8px;font-size:10px;">' + esc(c.signal) + '</span>'
        + '</div>'
        + '<div style="display:flex;gap:2rem;font-size:11px;margin-bottom:6px;">'
        // Personas y operaciones son cifras distintas y ahora se dicen las dos:
        // un cluster son directivos DISTINTOS comprando, no compras sueltas.
        + '<span style="color:var(--color-muted);">' + esc(c.n_insiders) + (c.n_insiders === 1 ? ' directivo' : ' directivos')
        + (c.n_operaciones && c.n_operaciones !== c.n_insiders ? ' <span style="color:var(--color-muted);">(' + esc(c.n_operaciones) + ' compras)</span>' : '')
        + ' · <span style="color:var(--color-accent);">' + esc(fmtVal(c.total_value)) + ' total</span></span>'
        + '<span style="color:var(--color-muted);">' + Number(c.total_shares).toLocaleString('en-US') + ' acciones</span>'
        + '</div>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        + c.insiders.map(i => '<span style="background:var(--color-surface2);border-radius:3px;padding:2px 8px;font-size:10px;color:var(--color-muted);">' + esc(i.name) + ' · ' + esc(fmtVal(i.value))
            + (i.n_ops > 1 ? ' <span style="color:var(--color-muted);">×' + esc(i.n_ops) + '</span>' : '') + '</span>').join('')
        + '</div>'
        + '</div>'
    ).join('');

    return shell('CLUSTER BUYING · SEÑAL FUERTE', rows);
}

function renderTickerResult(ticker, data) {
    if (!data.transactions || !data.transactions.length) {
        return shell('INSIDER · ' + ticker, '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin transacciones recientes (últimos 6 meses)</div>');
    }

    const summary = '<div style="display:flex;gap:2rem;padding:10px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<span style="color:var(--color-muted);">Compras: <span style="color:var(--color-accent);">' + esc(data.buys) + '</span></span>'
        + '<span style="color:var(--color-muted);">Ventas: <span style="color:#f23645;">' + esc(data.sells) + '</span></span>'
        + '<span style="color:var(--color-muted);">Total: ' + data.transactions.length + ' transacciones</span>'
        + badges(data)
        + '</div>';

    const header = '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 70px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>INSIDER</div><div>CARGO</div><div>TIPO</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>';

    const rows = data.transactions.map(t => {
        const isBuy = t.type_code === 'P';
        return '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 70px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + esc(fmtFecha(t.date)) + '</div>'
            + '<div style="color:var(--color-text);">' + esc(t.insider_name || '—') + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + esc((t.title || '—').substring(0, 20)) + '</div>'
            + '<div style="background:' + (isBuy ? 'rgba(0,255,173,0.1)' : 'rgba(242,54,69,0.1)') + ';color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';border-radius:3px;padding:2px 6px;font-size:10px;text-align:center;">' + esc(t.type) + '</div>'
            + '<div style="color:var(--color-text);">' + Number(t.shares || 0).toLocaleString('en-US') + '</div>'
            + '<div style="color:' + (isBuy ? 'var(--color-accent)' : '#f23645') + ';font-weight:500;">' + fmtVal(t.value) + '</div>'
            + '</div>';
    }).join('');

    return shell('INSIDER TRANSACTIONS · ' + ticker, summary + header + '<div style="overflow-y:auto;max-height:400px;">' + rows + '</div>', 'SEC EDGAR Form 4 · Últimos 6 meses');
}

function renderDiagnostic(log) {
    if (!log) return '';
    const ok = !!log.ok;
    const color = ok ? 'var(--color-muted)' : '#f23645';
    const icon  = ok ? '✓' : '✗';
    const when  = fmtFechaHora(log.ran_at);
    let text;
    if (ok) {
        text = 'Última ingesta ' + when + ' — ' + log.scanned + ' filings escaneados, ' + log.found + ' transacciones válidas, ' + log.new_rows + ' nuevas guardadas';
    } else {
        text = 'La última ingesta (' + when + ') falló: ' + (log.error || 'error desconocido');
    }
    return '<div style="font-size:10px;color:' + color + ';padding:4px 2px;">' + icon + ' ' + esc(text) + '</div>';
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

// El cuerpo vive en core/ui.js::panel() -- este mismo envoltorio estaba
// copiado en cinco paginas. `avisos` es opcional: las llamadas de siempre no
// cambian.
function shell(title, content, subtitle, avisos) {
    return panel({ titulo: title, contenido: content, subtitulo: subtitle,
                   avisos, escapar: true });
}

function fmtVal(val) {
    if (!val) return '—';
    const v = Number(val);
    if (v >= 1e9)  return '$' + (v/1e9).toFixed(1) + 'B';
    if (v >= 1e6)  return '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3)  return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v.toLocaleString('en-US');
}

// Badges de cruce -- Fase 3 del roadmap: 💼 si el ticker ya está en
// Cartera, ⭐ si está en la Watchlist del usuario, ⚡ si además tiene señal
// alcista simultánea en Options Flow (confluencia "dinero inteligente").
function badges(row) {
    return (row.en_cartera ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '')
        + (row.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '')
        + (row.is_confluence ? ' <span title="Señal alcista simultánea en Options Flow">⚡</span>' : '');
}

function loading() { return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando datos SEC EDGAR...</div>'; }
function error(msg) { return errorMessage(msg); }