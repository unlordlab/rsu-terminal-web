import { tt } from '/components/tooltip.js';

let currentData = null;

export async function render(container) {
    container.innerHTML = pageHeader()
        + controlBar()
        + '<div id="options-top" style="margin-bottom:1.5rem;"></div>'
        + '<div id="options-tables" style="margin-bottom:1.5rem;"></div>'
        + tickerSearch()
        + '<div id="options-ticker-result"></div>';

    setupControls(container);
    setupTickerSearch(container);
    loadFlow(container, 50000);
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">OPTIONS FLOW</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Flujo de opciones inusual · yfinance + Massive · EOD Data · Datos con retraso</div>'
        + '</div>';
}

function controlBar() {
    return '<div style="display:flex;gap:8px;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;">'
        + '<label style="color:var(--color-muted);font-size:12px;">Prima mínima:</label>'
        + '<select id="min-premium" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">'
        + '<option value="25000">$25K+</option>'
        + '<option value="50000" selected>$50K+</option>'
        + '<option value="100000">$100K+</option>'
        + '<option value="500000">$500K+</option>'
        + '<option value="1000000">$1M+</option>'
        + '</select>'
        + '<button id="refresh-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:6px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ESCANEAR</button>'
        + '<div id="options-status" style="color:var(--color-muted);font-size:11px;margin-left:auto;"></div>'
        + '</div>';
}

function tickerSearch() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">BÚSQUEDA POR TICKER</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<input id="options-ticker-input" type="text" placeholder="NVDA, HOOD, AAPL..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="options-ticker-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">BUSCAR</button>'
        + '</div>'
        + '</div>';
}

function setupControls(container) {
    const btn    = container.querySelector('#refresh-btn');
    const select = container.querySelector('#min-premium');
    btn.addEventListener('click', () => {
        loadFlow(container, parseFloat(select.value));
    });
}

function setupTickerSearch(container) {
    const input  = container.querySelector('#options-ticker-input');
    const btn    = container.querySelector('#options-ticker-btn');
    const result = container.querySelector('#options-ticker-result');

    async function doSearch() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent   = 'BUSCANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Analizando opciones de ' + ticker + '...</div>';

        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/options/ticker/' + ticker, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Sin datos');
            result.innerHTML = renderTickerResult(data);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'BUSCAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doSearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
}

async function loadFlow(container, minPremium) {
    const status  = container.querySelector('#options-status');
    const topEl   = container.querySelector('#options-top');
    const tablesEl = container.querySelector('#options-tables');

    if (status)  status.textContent = 'Escaneando...';
    if (topEl)   topEl.innerHTML    = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando flow... (~30 segundos)</div>';
    if (tablesEl) tablesEl.innerHTML = '';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/options/flow?min_premium=' + minPremium, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        currentData = data;

        if (status) status.textContent = data.scanned + ' tickers · EOD · ' + data.timestamp;

        topEl.innerHTML   = renderTopSection(data);
        tablesEl.innerHTML = renderTables(data);

    } catch(e) {
        if (topEl) topEl.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
    }
}

function renderTopSection(data) {
    function topBox(title, items, color) {
        return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
            + '<div style="color:' + color + ';font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
            + '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
            + items.map(item =>
                '<span style="background:' + color + '18;color:' + color + ';border:1px solid ' + color + '33;border-radius:3px;padding:2px 8px;font-size:11px;cursor:pointer;" class="top-ticker" data-ticker="' + item.ticker + '">'
                + item.ticker
                + '</span>'
            ).join('')
            + '</div>'
            + '</div>';
    }

    const html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + topBox('$ TOP PREMIUM', data.top_premium, 'var(--color-text)')
        + topBox('▲ TOP BULLISH', data.top_bullish, 'var(--color-accent)')
        + topBox('▼ TOP BEARISH', data.top_bearish, '#f23645')
        + '</div>'
        + '<div style="background:rgba(255,184,0,0.05);border:1px solid rgba(255,184,0,0.2);border-radius:var(--radius);padding:8px 14px;font-size:11px;color:#ffb800;margin-bottom:1rem;">'
        + '⚠ DATOS EOD — Esta herramienta usa datos de cierre del día anterior. No refleja flujo intraday en tiempo real. Para flujo institucional en tiempo real considera Unusual Whales.'
        + '</div>';

    setTimeout(() => {
        document.querySelectorAll('.top-ticker').forEach(el => {
            el.addEventListener('click', () => {
                const ticker = el.getAttribute('data-ticker');
                document.querySelector('#options-ticker-input').value = ticker;
                document.querySelector('#options-ticker-btn').click();
                window.scrollTo({ top: document.querySelector('#options-ticker-result').offsetTop - 100, behavior: 'smooth' });
            });
        });
    }, 100);

    return html;
}

function renderTables(data) {
    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">'
        + flowTable('Calls Bought', data.calls_bought, '#00ffad')
        + flowTable('Puts Sold',    data.puts_sold,    '#00ffad')
        + flowTable('Puts Bought',  data.puts_bought,  '#f23645')
        + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-top:1rem;">'
        + flowTable('Calls Sold',   data.calls_sold,   '#f23645')
        + '<div></div><div></div>'
        + '</div>';
}

function flowTable(title, rows, color) {
    if (!rows || !rows.length) {
        return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
            + '<div style="color:' + color + ';font-size:12px;margin-bottom:0.5rem;">' + title + ' <span style="color:var(--color-muted);font-size:10px;">0</span></div>'
            + '<div style="color:var(--color-muted);font-size:11px;">Sin datos con los filtros actuales.</div>'
            + '</div>';
    }

    const header = '<div style="display:grid;grid-template-columns:60px 1fr 70px 70px;gap:4px;padding:6px 10px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>TICKER</div><div>STRIKE · EXP</div><div>PRIMA</div><div>VOL</div>'
        + '</div>';

    const tableRows = rows.slice(0, 15).map(r => {
        const strikeStr = '$' + r.strike + ' (' + r.strike_pct + ')';
        const expShort  = r.exp ? r.exp.substring(2).replace(/-/g, '/') : '';
        return '<div style="display:grid;grid-template-columns:60px 1fr 70px 70px;gap:4px;padding:7px 10px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;cursor:pointer;" class="flow-row" data-ticker="' + r.ticker + '">'
            + '<div style="color:var(--color-accent);font-weight:500;">' + r.ticker + '</div>'
            + '<div style="color:var(--color-muted);">' + strikeStr + '<br><span style="font-size:10px;">' + expShort + '</span></div>'
            + '<div style="color:var(--color-text);">' + r.premium_fmt + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.volume >= 1000 ? (r.volume/1000).toFixed(0) + 'K' : r.volume) + '</div>'
            + '</div>';
    }).join('');

    const result = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:8px 10px;border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:6px;">'
        + '<span style="color:' + color + ';font-size:12px;letter-spacing:0.05em;">' + title + '</span>'
        + '<span style="color:var(--color-muted);font-size:10px;background:var(--color-bg,#0a0a0a);padding:1px 6px;border-radius:3px;">' + rows.length + '</span>'
        + '</div>'
        + header
        + '<div style="max-height:350px;overflow-y:auto;">' + tableRows + '</div>'
        + '</div>';

    setTimeout(() => {
        document.querySelectorAll('.flow-row').forEach(el => {
            el.addEventListener('mouseenter', () => el.style.background = 'var(--color-surface2,#1a1a1a)');
            el.addEventListener('mouseleave', () => el.style.background = 'transparent');
            el.addEventListener('click', () => {
                const ticker = el.getAttribute('data-ticker');
                document.querySelector('#options-ticker-input').value = ticker;
                document.querySelector('#options-ticker-btn').click();
            });
        });
    }, 200);

    return result;
}

function renderTickerResult(data) {
    const sentColor = data.sentiment === 'bullish' ? 'var(--color-accent)' : data.sentiment === 'bearish' ? '#f23645' : '#ffb800';
    const sentIcon  = data.sentiment === 'bullish' ? '▲' : data.sentiment === 'bearish' ? '▼' : '→';
    const scoreColor = data.net_score > 0 ? 'var(--color-accent)' : data.net_score < 0 ? '#f23645' : '#ffb800';

    const flowRows = (data.flow || []).map(r => {
        const isBull = r.color === 'bullish';
        const color  = isBull ? '#00ffad' : '#f23645';
        const bg     = isBull ? 'rgba(0,255,173,0.05)' : 'rgba(242,54,69,0.05)';
        const expShort = r.exp ? r.exp.substring(2).replace(/-/g, '/') : '';
        return '<tr style="border-bottom:1px solid var(--color-border);background:' + bg + ';">'
            + '<td style="padding:8px 12px;font-size:11px;color:var(--color-muted);">' + (r.exp || '') + '</td>'
            + '<td style="padding:8px 12px;">'
            + '<span style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44;border-radius:3px;padding:2px 8px;font-size:11px;">' + r.order_type + '</span>'
            + '</td>'
            + '<td style="padding:8px 12px;color:var(--color-text);font-size:12px;">$' + r.strike + ' <span style="color:var(--color-muted);font-size:10px;">(' + r.strike_pct + ')</span></td>'
            + '<td style="padding:8px 12px;color:var(--color-muted);font-size:11px;">' + expShort + '</td>'
            + '<td style="padding:8px 12px;color:var(--color-muted);font-size:11px;">' + (r.oi || 0).toLocaleString() + '</td>'
            + '<td style="padding:8px 12px;color:var(--color-text);font-size:12px;font-weight:500;">' + r.premium_fmt + '</td>'
            + '</tr>';
    }).join('');

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-top:1rem;">'

        // Header
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--color-border);">'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:20px;letter-spacing:0.1em;">' + data.ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">$' + data.price + ' · Actualizado: ' + data.timestamp + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:4px;">NET SCORE</div>'
        + '<div style="color:' + scoreColor + ';font-size:28px;font-weight:500;">' + (data.net_score > 0 ? '+' : '') + data.net_score + '</div>'
        + '</div>'
        + '</div>'

        // KPIs
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">'
        + kpi('Prima Calls', data.total_call_prem, 'var(--color-accent)')
        + kpi('Prima Puts',  data.total_put_prem,  '#f23645')
        + kpi('Sentimiento', sentIcon + ' ' + data.sentiment.toUpperCase(), sentColor)
        + '</div>'

        // Tabla de flow
        + '<div style="overflow:hidden;border-radius:var(--radius);border:1px solid var(--color-border);">'
        + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:12px;">'
        + '<thead><tr style="border-bottom:1px solid var(--color-border);">'
        + ['Fecha', 'Tipo', 'Strike', 'Exp', 'OI', 'Prima'].map(h =>
            '<th style="padding:8px 12px;text-align:left;color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">' + h + '</th>'
        ).join('')
        + '</tr></thead>'
        + '<tbody>' + flowRows + '</tbody>'
        + '</table>'
        + '</div>'

        // Historial Massive
        + (data.history && data.history.length > 0
            ? '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);">'
              + '<div style="color:var(--color-secondary);font-size:11px;letter-spacing:0.08em;margin-bottom:0.5rem;">HISTORIAL RECIENTE · MASSIVE EOD</div>'
              + data.history.map(h =>
                  '<div style="display:flex;gap:1rem;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                  + '<span style="color:var(--color-muted);">' + h.date + '</span>'
                  + '<span style="color:' + (h.type === 'call' ? 'var(--color-accent)' : '#f23645') + ';">' + h.type.toUpperCase() + '</span>'
                  + '<span style="color:var(--color-text);">$' + h.strike + '</span>'
                  + '<span style="color:var(--color-muted);">' + h.exp + '</span>'
                  + '<span style="color:var(--color-muted);">Vol: ' + h.volume + '</span>'
                  + '<span style="color:var(--color-text);margin-left:auto;">' + h.premium_fmt + '</span>'
                  + '</div>'
              ).join('')
              + '</div>'
            : '')
        + '</div>';
}

function kpi(label, value, color) {
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:16px;font-weight:500;">' + value + '</div>'
        + '</div>';
}