import { tt } from '/components/tooltip.js';

let currentData = null;

export async function render(container) {
    container.innerHTML = pageHeader()
        + controlBar()
        + '<div id="options-high" style="margin-bottom:1.5rem;"></div>'
        + '<div id="options-top" style="margin-bottom:1.5rem;"></div>'
        + '<div id="options-tables" style="margin-bottom:1.5rem;"></div>'
        + tickerPanel()
        + '<div id="options-ticker-result" style="margin-bottom:1.5rem;"></div>'
        + repeatsPanel()
        + historyPanel()
        + '<div id="options-history-result"></div>';

    setupControls(container);
    setupTickerSearch(container);
    setupHistory(container);
    setupRepeats(container);
    loadStats(container);
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">OPTIONS FLOW ' + tt('options-flow') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Flujo inusual · ~150 tickers · Score multi-factor · EOD Data</div>'
        + '</div>';
}

function controlBar() {
    return '<div style="display:flex;gap:8px;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">'
        + '<label style="color:var(--color-muted);font-size:12px;">Prima mín:</label>'
        + '<select id="min-premium" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">'
        + '<option value="50000">$50K+</option>'
        + '<option value="100000" selected>$100K+</option>'
        + '<option value="250000">$250K+</option>'
        + '<option value="500000">$500K+</option>'
        + '<option value="1000000">$1M+</option>'
        + '</select>'
        + '<label style="color:var(--color-muted);font-size:12px;margin-left:8px;">Score mín:</label>'
        + '<select id="min-score" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">'
        + '<option value="3">3 — Amplio</option>'
        + '<option value="4" selected>4 — Estándar</option>'
        + '<option value="6">6 — Selectivo</option>'
        + '<option value="8">8 — Solo HIGH</option>'
        + '</select>'
        + '<button id="refresh-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:6px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ESCANEAR</button>'
        + '<button id="save-btn" style="background:transparent;border:1px solid var(--color-accent);color:var(--color-accent);border-radius:var(--radius);padding:6px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;display:none;">GUARDAR SCAN</button>'
        + '<div id="options-status" style="color:var(--color-muted);font-size:11px;margin-left:auto;"></div>'
        + '</div>'
        + '<div style="background:rgba(255,184,0,0.05);border:1px solid rgba(255,184,0,0.2);border-radius:var(--radius);padding:8px 14px;font-size:11px;color:#ffb800;margin-bottom:1.5rem;">'
        + '⚠ EOD DATA — Datos de cierre del día anterior. No refleja flujo intraday. Para tiempo real considera Unusual Whales.'
        + '</div>';
}

function tickerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS POR TICKER</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<input id="options-ticker-input" type="text" placeholder="NVDA, HOOD, AAPL..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="options-ticker-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">BUSCAR</button>'
        + '</div>'
        + '</div>';
}

function repeatsPanel() {
    return '<div style="background:var(--color-surface);border:1px solid rgba(255,184,0,0.3);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:#ffb800;font-size:13px;letter-spacing:0.08em;">🔁 SEÑALES REPETIDAS ' + tt('high-signal') + '</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<select id="repeat-days" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:5px 8px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;">'
        + '<option value="7">7 días</option>'
        + '<option value="14">14 días</option>'
        + '<option value="30">30 días</option>'
        + '</select>'
        + '<button id="repeats-btn" style="background:#ffb800;color:#000;border:none;border-radius:var(--radius);padding:5px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">BUSCAR</button>'
        + '</div>'
        + '</div>'
        + '<div id="repeats-result" style="color:var(--color-muted);font-size:12px;">Guarda varios scans primero para detectar señales repetidas.</div>'
        + '</div>';
}

function historyPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">HISTORIAL DE FLUJO · BASE DE DATOS</div>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        + '<input id="history-ticker" type="text" placeholder="Ticker (opcional)..." style="width:180px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<div style="display:flex;gap:4px;">'
        + ['1w','2w','1m','3m'].map(p =>
            '<button class="period-btn" data-period="' + p + '" style="background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">' + p.toUpperCase() + '</button>'
        ).join('')
        + '</div>'
        + '<button id="history-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">CONSULTAR</button>'
        + '<div id="db-stats" style="color:var(--color-muted);font-size:11px;display:flex;align-items:center;margin-left:auto;"></div>'
        + '</div>'
        + '</div>';
}

function setupControls(container) {
    const btn      = container.querySelector('#refresh-btn');
    const saveBtn  = container.querySelector('#save-btn');
    const minPrem  = container.querySelector('#min-premium');
    const minScore = container.querySelector('#min-score');

    btn.addEventListener('click', () => loadFlow(container, parseFloat(minPrem.value), parseInt(minScore.value)));

    saveBtn.addEventListener('click', async () => {
        if (!currentData) return;
        saveBtn.textContent   = 'GUARDANDO...';
        saveBtn.style.opacity = '0.7';
        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/options/save', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': 'Bearer ' + token } : {}) },
                body:    JSON.stringify(currentData),
            });
            const data  = await res.json();
            saveBtn.textContent = '✓ GUARDADO (' + data.inserted + ' nuevos)';
            setTimeout(() => { saveBtn.textContent = 'GUARDAR SCAN'; saveBtn.style.opacity = '1'; }, 3000);
            loadStats(container);
        } catch(e) {
            saveBtn.textContent   = '✗ ERROR';
            saveBtn.style.opacity = '1';
        }
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
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Analizando ' + ticker + '...</div>';
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

function setupHistory(container) {
    const btn    = container.querySelector('#history-btn');
    const input  = container.querySelector('#history-ticker');
    const result = container.querySelector('#options-history-result');
    let activePeriod = '1w';

    container.querySelectorAll('.period-btn').forEach(b => {
        b.addEventListener('click', () => {
            activePeriod = b.getAttribute('data-period');
            container.querySelectorAll('.period-btn').forEach(x => {
                x.style.background = 'var(--color-surface)';
                x.style.color      = 'var(--color-muted)';
            });
            b.style.background = 'var(--color-secondary)';
            b.style.color      = '#000';
        });
    });

    btn.addEventListener('click', async () => {
        const ticker = input.value.trim().toUpperCase() || null;
        btn.textContent   = 'CONSULTANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando historial...</div>';
        try {
            const token = sessionStorage.getItem('rsu_token');
            let url = '/api/v1/options/history?period=' + activePeriod;
            if (ticker) url += '&ticker=' + ticker;
            const res  = await fetch(url, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
            const data = await res.json();
            result.innerHTML = renderHistory(data, ticker, activePeriod);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'CONSULTAR';
            btn.style.opacity = '1';
        }
    });
}

function setupRepeats(container) {
    const btn    = container.querySelector('#repeats-btn');
    const select = container.querySelector('#repeat-days');
    const result = container.querySelector('#repeats-result');

    btn.addEventListener('click', async () => {
        const days = select.value;
        btn.textContent   = 'BUSCANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;">Buscando señales repetidas...</div>';
        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/options/repeats?days=' + days + '&min_repeats=2', {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data  = await res.json();
            if (!data.signals || !data.signals.length) {
                result.innerHTML = '<div style="color:var(--color-muted);font-size:12px;">Sin señales repetidas en ' + days + ' días. Necesitas más scans guardados.</div>';
                return;
            }
            result.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0.75rem;">'
                + data.signals.map(s => {
                    const isBull      = (s.type === 'call' && s.action === 'buy') || (s.type === 'put' && s.action === 'sell');
                    const color       = isBull ? 'var(--color-accent)' : '#f23645';
                    const repeatColor = s.repeat_count >= 4 ? '#ffb800' : s.repeat_count >= 3 ? 'var(--color-accent)' : 'var(--color-muted)';
                    return '<div style="background:var(--color-surface);border:1px solid ' + color + '33;border-radius:var(--radius);padding:1rem;">'
                        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
                        + '<span style="color:var(--color-accent);font-size:14px;font-weight:500;">' + s.ticker + '</span>'
                        + '<span style="color:' + repeatColor + ';font-size:12px;background:' + repeatColor + '22;padding:2px 8px;border-radius:3px;">🔁 x' + s.repeat_count + '</span>'
                        + '</div>'
                        + '<div style="color:' + color + ';font-size:11px;margin-bottom:4px;">' + s.type.toUpperCase() + ' ' + s.action.toUpperCase() + ' · $' + s.strike + '</div>'
                        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">Exp: ' + s.exp + ' · Score medio: ' + s.avg_score + '</div>'
                        + '<div style="display:flex;justify-content:space-between;">'
                        + '<span style="color:var(--color-text);font-size:12px;font-weight:500;">' + s.total_premium_fmt + ' total</span>'
                        + '<span style="color:var(--color-muted);font-size:10px;">' + s.first_seen + ' → ' + s.last_seen + '</span>'
                        + '</div>'
                        + '</div>';
                }).join('')
                + '</div>';
        } catch(e) {
            result.innerHTML = '<div style="padding:0.5rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'BUSCAR';
            btn.style.opacity = '1';
        }
    });
}

async function loadStats(container) {
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/options/stats', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data  = await res.json();
        const el    = container.querySelector('#db-stats');
        if (el) el.innerHTML = '🗄 ' + data.total_records + ' registros · ' + data.scan_days + ' días · Último: ' + (data.last_scan || 'Sin scans');
    } catch(e) {}
}

async function loadFlow(container, minPremium, minScore) {
    const status   = container.querySelector('#options-status');
    const highEl   = container.querySelector('#options-high');
    const topEl    = container.querySelector('#options-top');
    const tablesEl = container.querySelector('#options-tables');
    const saveBtn  = container.querySelector('#save-btn');

    if (status)   status.textContent    = 'Escaneando ~150 tickers...';
    if (highEl)   highEl.innerHTML      = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Escaneando... (~60-90 segundos)</div>';
    if (topEl)    topEl.innerHTML       = '';
    if (tablesEl) tablesEl.innerHTML    = '';
    if (saveBtn)  saveBtn.style.display = 'none';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/options/flow?min_premium=' + minPremium + '&min_score=' + minScore, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        currentData = data;

        if (status)  status.textContent    = data.scanned + ' escaneados · ' + data.matched + ' con señal · ' + data.timestamp;
        if (saveBtn) saveBtn.style.display  = 'inline-block';
        if (highEl)   highEl.innerHTML      = renderHighSignals(data.high_signals);
        if (topEl)    topEl.innerHTML       = renderTopSection(data);
        if (tablesEl) tablesEl.innerHTML    = renderTables(data);

    } catch(e) {
        if (highEl) highEl.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
    }
}

function renderHighSignals(signals) {
    if (!signals || !signals.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid rgba(255,184,0,0.4);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:8px;">'
        + '<span style="color:#ffb800;font-size:13px;letter-spacing:0.08em;">⚡ SEÑALES HIGH ' + tt('high-signal') + '</span>'
        + '<span style="background:#ffb80022;color:#ffb800;border:1px solid #ffb80044;border-radius:3px;padding:1px 8px;font-size:10px;">' + signals.length + '</span>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0;">'
        + signals.slice(0, 12).map(s => {
            const isBull = s.color === 'bullish';
            const color  = isBull ? 'var(--color-accent)' : '#f23645';
            const bg     = isBull ? 'rgba(0,255,173,0.03)' : 'rgba(242,54,69,0.03)';
            return '<div style="padding:10px 14px;border:1px solid var(--color-border);background:' + bg + ';">'
                + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                + '<span style="color:var(--color-accent);font-weight:500;font-size:13px;">' + s.ticker + '</span>'
                + '<span style="color:#ffb800;font-size:10px;background:#ffb80022;padding:1px 6px;border-radius:3px;">SCORE ' + s.score + '</span>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;">' + s.type.toUpperCase() + ' · $' + s.strike + ' ' + s.strike_pct + ' · ' + s.exp + '</div>'
                + '<div style="display:flex;justify-content:space-between;margin-top:4px;">'
                + '<span style="color:' + color + ';font-size:12px;font-weight:500;">' + s.premium_fmt + '</span>'
                + '<span style="color:var(--color-muted);font-size:10px;">Vol/OI: ' + s.vol_oi_ratio + 'x</span>'
                + '</div>'
                + '</div>';
        }).join('')
        + '</div></div>';
}

function renderTopSection(data) {
    function topBox(title, items, color) {
        return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
            + '<div style="color:' + color + ';font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
            + '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
            + items.map(item =>
                '<span style="background:' + color + '18;color:' + color + ';border:1px solid ' + color + '33;border-radius:3px;padding:3px 10px;font-size:11px;cursor:pointer;" class="top-ticker" data-ticker="' + item.ticker + '">'
                + item.ticker + ' <span style="opacity:0.7;">' + item.premium_fmt + '</span>'
                + '</span>'
            ).join('')
            + '</div>'
            + '</div>';
    }

    const html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">'
        + topBox('$ TOP PREMIUM', data.top_premium, 'var(--color-text)')
        + topBox('▲ TOP BULLISH', data.top_bullish, 'var(--color-accent)')
        + topBox('▼ TOP BEARISH', data.top_bearish, '#f23645')
        + '</div>';

    setTimeout(() => {
        document.querySelectorAll('.top-ticker').forEach(el => {
            el.addEventListener('click', () => {
                const ticker = el.getAttribute('data-ticker');
                document.querySelector('#options-ticker-input').value = ticker;
                document.querySelector('#options-ticker-btn').click();
                document.querySelector('#options-ticker-result').scrollIntoView({ behavior: 'smooth' });
            });
        });
    }, 100);

    return html;
}

function renderTables(data) {
    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-top:1rem;">'
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
    const tooltipMap = {
        'Calls Bought': tt('calls-bought'),
        'Puts Sold':    tt('puts-sold'),
        'Puts Bought':  tt('puts-bought'),
        'Calls Sold':   tt('calls-sold'),
    };
    const tooltip = tooltipMap[title] || '';

    if (!rows || !rows.length) {
        return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
            + '<div style="color:' + color + ';font-size:12px;margin-bottom:0.5rem;">' + title + ' ' + tooltip + '</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">Sin señales.</div>'
            + '</div>';
    }

    const header = '<div style="display:grid;grid-template-columns:60px 1fr 70px 55px 40px;gap:4px;padding:6px 10px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>TICKER</div>'
        + '<div>STRIKE ' + tt('otm-strike') + ' · EXP</div>'
        + '<div>PRIMA</div>'
        + '<div>VOL/OI ' + tt('vol-oi-ratio') + '</div>'
        + '<div>SC ' + tt('options-score') + '</div>'
        + '</div>';

    const tableRows = rows.slice(0, 15).map(r => {
        const scoreColor = r.score >= 7 ? '#ffb800' : r.score >= 5 ? 'var(--color-accent)' : 'var(--color-muted)';
        const expShort   = r.exp ? r.exp.substring(2).replace(/-/g, '/') : '';
        return '<div style="display:grid;grid-template-columns:60px 1fr 70px 55px 40px;gap:4px;padding:7px 10px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;cursor:pointer;" class="flow-row" data-ticker="' + r.ticker + '">'
            + '<div onclick="goToResearch(\'' + r.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + r.ticker + '</div>'
            + '<div style="color:var(--color-muted);">$' + r.strike + ' ' + r.strike_pct + '<br><span style="font-size:10px;">' + expShort + '</span></div>'
            + '<div style="color:var(--color-text);">' + r.premium_fmt + '</div>'
            + '<div style="color:var(--color-muted);">' + r.vol_oi_ratio + 'x</div>'
            + '<div style="color:' + scoreColor + ';font-weight:500;">' + r.score + '</div>'
            + '</div>';
    }).join('');

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

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:8px 10px;border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:6px;">'
        + '<span style="color:' + color + ';font-size:12px;letter-spacing:0.05em;">' + title + ' ' + tooltip + '</span>'
        + '<span style="color:var(--color-muted);font-size:10px;background:var(--color-bg,#0a0a0a);padding:1px 6px;border-radius:3px;">' + rows.length + '</span>'
        + '</div>'
        + header
        + '<div style="max-height:380px;overflow-y:auto;">' + tableRows + '</div>'
        + '</div>';
}

function renderTickerResult(data) {
    const sentColor  = data.sentiment === 'bullish' ? 'var(--color-accent)' : data.sentiment === 'bearish' ? '#f23645' : '#ffb800';
    const sentIcon   = data.sentiment === 'bullish' ? '▲' : data.sentiment === 'bearish' ? '▼' : '→';
    const scoreColor = data.net_score > 0 ? 'var(--color-accent)' : data.net_score < 0 ? '#f23645' : '#ffb800';

    const flowRows = (data.flow || []).map(r => {
        const isBull   = r.color === 'bullish';
        const color    = isBull ? '#00ffad' : '#f23645';
        const bg       = isBull ? 'rgba(0,255,173,0.03)' : 'rgba(242,54,69,0.03)';
        const expShort = r.exp ? r.exp.substring(2).replace(/-/g, '/') : '';
        const scoreC   = r.score >= 7 ? '#ffb800' : r.score >= 5 ? 'var(--color-accent)' : 'var(--color-muted)';
        return '<tr style="border-bottom:1px solid var(--color-border);background:' + bg + ';">'
            + '<td style="padding:8px 10px;"><span style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44;border-radius:3px;padding:2px 7px;font-size:10px;">' + r.order_type + '</span></td>'
            + '<td style="padding:8px 10px;color:var(--color-text);font-size:12px;">$' + r.strike + ' <span style="color:var(--color-muted);font-size:10px;">' + r.strike_pct + '</span></td>'
            + '<td style="padding:8px 10px;color:var(--color-muted);font-size:11px;">' + expShort + ' <span style="font-size:10px;">(' + r.exp_days + 'd)</span></td>'
            + '<td style="padding:8px 10px;color:var(--color-muted);font-size:11px;">' + r.oi.toLocaleString() + '</td>'
            + '<td style="padding:8px 10px;color:var(--color-muted);font-size:11px;">' + r.vol_oi_ratio + 'x</td>'
            + '<td style="padding:8px 10px;color:var(--color-text);font-size:12px;font-weight:500;">' + r.premium_fmt + '</td>'
            + '<td style="padding:8px 10px;color:' + scoreC + ';font-weight:500;">' + r.score + '</td>'
            + '</tr>';
    }).join('');

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--color-border);">'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:20px;letter-spacing:0.1em;">' + data.ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">$' + data.price + ' · ' + data.timestamp + '</div>'
        + '</div>'
        + '<div style="display:flex;gap:1rem;">'
        + kpi('NET SCORE ' + tt('net-score-options'),   (data.net_score > 0 ? '+' : '') + data.net_score, scoreColor)
        + kpi('CALLS PREM',  data.total_call_prem,  'var(--color-accent)')
        + kpi('PUTS PREM',   data.total_put_prem,   '#f23645')
        + kpi('SENTIMIENTO', sentIcon + ' ' + data.sentiment.toUpperCase(), sentColor)
        + '</div>'
        + '</div>'
        + '<div style="overflow:auto;">'
        + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">'
        + '<thead><tr style="border-bottom:1px solid var(--color-border);">'
        + ['Tipo','Strike','Exp','OI','Vol/OI','Prima','Score'].map(h =>
            '<th style="padding:7px 10px;text-align:left;color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">' + h + '</th>'
        ).join('')
        + '</tr></thead>'
        + '<tbody>' + flowRows + '</tbody>'
        + '</table>'
        + '</div>'
        + '</div>';
}

function renderHistory(data, ticker, period) {
    if (!data.records || !data.records.length) {
        return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Sin registros para ' + (ticker || 'todos') + ' en el período ' + period + '. Haz un scan y guárdalo primero.</div>';
    }

    const header = '<div style="display:grid;grid-template-columns:90px 70px 60px 80px 60px 60px 70px 60px 50px;gap:4px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>TICKER</div><div>TIPO</div><div>STRIKE</div><div>EXP</div><div>PRIMA</div><div>VOL/OI</div><div>SEÑAL</div><div>SCORE</div>'
        + '</div>';

    const rows = data.records.map(r => {
        const isBull   = (r.action === 'buy' && r.type === 'call') || (r.action === 'sell' && r.type === 'put');
        const color    = isBull ? 'var(--color-accent)' : '#f23645';
        const sigColor = r.signal === 'HIGH' ? '#ffb800' : r.signal === 'MEDIUM' ? 'var(--color-accent)' : 'var(--color-muted)';
        const expShort = r.exp ? r.exp.substring(2).replace(/-/g, '/') : '';
        return '<div style="display:grid;grid-template-columns:90px 70px 60px 80px 60px 60px 70px 60px 50px;gap:4px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + r.scan_date + '</div>'
            + '<div onclick="goToResearch(\'' + r.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + r.ticker + '</div>'
            + '<div style="color:' + color + ';">' + r.type.toUpperCase() + ' ' + r.action.toUpperCase() + '</div>'
            + '<div style="color:var(--color-text);">$' + r.strike + ' <span style="color:var(--color-muted);font-size:10px;">' + (r.strike_pct || '') + '</span></div>'
            + '<div style="color:var(--color-muted);">' + expShort + '</div>'
            + '<div style="color:var(--color-text);font-weight:500;">' + (r.premium_fmt || '') + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.vol_oi_ratio || 0) + 'x</div>'
            + '<div style="color:' + sigColor + ';font-size:10px;font-weight:500;">' + (r.signal || '') + '</div>'
            + '<div style="color:' + sigColor + ';font-weight:500;">' + (r.score || 0) + '</div>'
            + '</div>';
    }).join('');

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-top:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">'
        + '<span style="color:var(--color-secondary);font-size:12px;letter-spacing:0.08em;">HISTORIAL · ' + period.toUpperCase() + (ticker ? ' · ' + ticker : '') + '</span>'
        + '<span style="color:var(--color-muted);font-size:11px;">' + data.total + ' registros</span>'
        + '</div>'
        + header
        + '<div style="max-height:500px;overflow-y:auto;">' + rows + '</div>'
        + '</div>';
}

function kpi(label, value, color) {
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;min-width:90px;">'
        + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:14px;font-weight:500;">' + value + '</div>'
        + '</div>';
}