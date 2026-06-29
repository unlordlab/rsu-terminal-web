import { tt } from '/components/tooltip.js';
import { isRateLimitMessage, errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = pageHeader()
        + '<div id="rsrw-sectors" style="margin-bottom:1.5rem;"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
        + '<div id="rsrw-leaders"></div>'
        + '<div id="rsrw-laggards"></div>'
        + '</div>'
        + tickerPanel()
        + '<div id="rsrw-ticker-result"></div>'
        + scanPanel()
        + '<div id="rsrw-scan-result"></div>';

    setupTicker(container);
    setupScan(container);
    loadGist(container);
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RS/RW SCANNER ' + tt('rsrw') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Relative Strength · Relative Weakness · IBD Methodology · S&P 500</div>'
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

function scanPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1.5rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">SCAN ON-DEMAND</div>'
        + '<div style="display:flex;gap:8px;align-items:center;">'
        + '<label style="color:var(--color-muted);font-size:12px;">Tickers:</label>'
        + '<select id="rsrw-max-tickers" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">'
        + '<option value="100">100 — Rápido (~30s)</option>'
        + '<option value="150">150 — Estándar (~60s)</option>'
        + '<option value="250">250 — Amplio (~2min)</option>'
        + '<option value="500" selected>500 — S&amp;P 500 completo (~4-5min)</option>'
        + '</select>'
        + '<button id="rsrw-scan-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ESCANEAR AHORA</button>'
        + '</div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">El Gist se actualiza automáticamente cada noche via GitHub Actions. El scan on-demand usa datos en tiempo real.</div>'
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
        renderTable(leadersEl, 'LÍDERES RS', data.leaders, true, data.freshness, data.total);
        renderTable(laggardsEl, 'REZAGADOS RW', data.laggards, false, data.freshness, data.total);

    } catch(e) {
        if (leadersEl)  leadersEl.innerHTML  = errorCard('LÍDERES RS', e.message);
        if (laggardsEl) laggardsEl.innerHTML = errorCard('REZAGADOS RW', e.message);
    }
}

function renderSectors(el, sectors) {
    if (!el || !sectors || !sectors.length) return;
    const sorted = [...sectors].sort((a, b) => (b.rs || 0) - (a.rs || 0));
    const maxAbs = Math.max(...sorted.map(s => Math.abs(s.rs || 0)));

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ROTACIÓN SECTORIAL · RS vs SPY</div>'
        + '<div style="display:flex;flex-direction:column;gap:6px;">'
        + sorted.map(s => {
            const rs     = s.rs || 0;
            const name   = s.ticker || s.sector || s.index || 'N/A';
            const color  = rs > 0 ? 'var(--color-accent)' : '#f23645';
            const w      = maxAbs > 0 ? Math.abs(rs) / maxAbs * 100 : 0;
            const trendV = s.rs_trend || 0;
            const trend  = trendV > 0.01 ? '▲' : trendV < -0.01 ? '▼' : '→';
            const tColor = trend === '▲' ? 'var(--color-accent)' : trend === '▼' ? '#f23645' : 'var(--color-muted)';
            const ret63  = s.return_63d != null ? ((s.return_63d >= 0 ? '+' : '') + s.return_63d.toFixed(1) + '%') : '';
            return '<div style="display:grid;grid-template-columns:140px 1fr 50px 20px 60px;gap:8px;align-items:center;">'
                + '<div style="font-size:11px;color:var(--color-muted);">' + name + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:5px;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '<div style="color:' + color + ';font-size:11px;text-align:right;">' + rs.toFixed(2) + '</div>'
                + '<div style="color:' + tColor + ';font-size:11px;">' + trend + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;text-align:right;">' + ret63 + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function renderTable(el, title, rows, isLeaders, freshness, total) {
    if (!el) return;
    const color = isLeaders ? 'var(--color-accent)' : '#f23645';

    const header = '<div style="display:grid;grid-template-columns:70px 60px 60px 60px 60px 60px 60px 1fr;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<div>TICKER</div><div>RS%</div><div>21d</div><div>63d</div><div>126d</div><div>TREND</div><div>RVOL</div><div>SECTOR</div>'
        + '</div>';

    const tableRows = (rows || []).map(r => {
        const pct       = r.rs_pct || 0;
        const pctColor  = pct >= 80 ? 'var(--color-accent)' : pct <= 20 ? '#f23645' : '#ffb800';
        const trendVal  = r.rs_trend || 0;
        const trendIcon = trendVal > 0.01 ? '▲' : trendVal < -0.01 ? '▼' : '→';
        const trendClr  = trendVal > 0.01 ? 'var(--color-accent)' : trendVal < -0.01 ? '#f23645' : 'var(--color-muted)';
        const rvolClr   = (r.rvol || 0) >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)';

        return '<div style="display:grid;grid-template-columns:70px 60px 60px 60px 60px 60px 60px 1fr;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div onclick="goToResearch(\'' + (r.ticker || '') + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + (r.ticker || '') + '</div>'            + '<div style="color:' + pctColor + ';font-weight:500;">' + pct.toFixed(0) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_21d || 0).toFixed(1) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_63d || 0).toFixed(1) + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.rs_126d || 0).toFixed(1) + '</div>'
            + '<div style="color:' + trendClr + ';">' + trendIcon + '</div>'
            + '<div style="color:' + rvolClr + ';">' + (r.rvol || 0).toFixed(1) + 'x</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + (r.sector || '') + '</div>'
            + '</div>';
    }).join('');

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:' + color + ';font-size:13px;letter-spacing:0.08em;">' + title + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;">'
        + (freshness ? freshness + ' · ' : '') + (rows ? rows.length : 0) + ' de ' + (total || 0)
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
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Calculando RS/RW para ' + ticker + '...</div>';

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
}

function renderTickerResult(data) {
    const score = data.rs_score || 0;
    const color = score >= 0 ? 'var(--color-accent)' : '#f23645';
    const trend = (data.rs_trend || 0) > 0.01 ? '▲ ALCISTA' : (data.rs_trend || 0) < -0.01 ? '▼ BAJISTA' : '→ LATERAL';
    const tColor = trend.includes('▲') ? 'var(--color-accent)' : trend.includes('▼') ? '#f23645' : 'var(--color-muted)';
    const chartId = 'rsrw-ticker-chart-' + Date.now();

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;">' + data.ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Actualizado: ' + data.timestamp + '</div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem;">'
        + kpiCard('RS SCORE', score.toFixed(1), 'vs SPY', color)
        + kpiCard('RS 21D', (data.rs_21d || 0).toFixed(2), '1 mes', 'var(--color-muted)')
        + kpiCard('RS 63D', (data.rs_63d || 0).toFixed(2), '3 meses', 'var(--color-muted)')
        + kpiCard('RS 126D', (data.rs_126d || 0).toFixed(2), '6 meses', 'var(--color-muted)')
        + '</div>'
        + '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">'
        + '<span style="color:var(--color-muted);font-size:12px;">TENDENCIA RS:</span>'
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
        new Chart(ctx, {
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
        });
    }

    if (window.Chart) { draw(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = draw;
    document.head.appendChild(s);
}

function setupScan(container) {
    const btn    = container.querySelector('#rsrw-scan-btn');
    const select = container.querySelector('#rsrw-max-tickers');
    const result = container.querySelector('#rsrw-scan-result');

    btn.addEventListener('click', async () => {
        const max = select.value;
        btn.textContent   = 'ESCANEANDO...';
        btn.style.opacity = '0.7';
        const estimate    = max >= 500 ? '4-5 minutos' : (max >= 250 ? '2 minutos' : '1 minuto');
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Escaneando ' + max + ' tickers... puede tardar hasta ' + estimate + '.</div>';

        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/rsrw/scan?max_tickers=' + max, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Error en el scan');

            const requested = data.meta && data.meta.n_requested;
            const got       = data.total;
            let coverageHtml = '';
            if (requested && got) {
                const pct = Math.round((got / requested) * 100);
                const color = pct >= 90 ? 'var(--color-accent)' : (pct >= 70 ? '#ff9800' : '#f23645');
                coverageHtml = '<div style="color:' + color + ';font-size:11px;padding:0.4rem 0.5rem;">'
                    + '✓ ' + got + ' / ' + requested + ' tickers con histórico suficiente (' + pct + '%)'
                    + (pct < 90 ? ' — Yahoo puede haber limitado parte de la descarga; revisa la consola del backend para detalle.' : '')
                    + '</div>';
            }

            const tempContainer  = document.createElement('div');
            const sectorsBox     = document.createElement('div');
            const leadersBox     = document.createElement('div');
            const laggardsBox    = document.createElement('div');
            leadersBox.style.marginTop  = '1rem';
            laggardsBox.style.marginTop = '1rem';

            renderSectors(sectorsBox, data.sectors);
            renderTable(leadersBox, 'LÍDERES RS (SCAN LIVE)', data.leaders, true, null, data.total);
            renderTable(laggardsBox, 'REZAGADOS RW (SCAN LIVE)', data.laggards, false, null, data.total);

            tempContainer.appendChild(sectorsBox);
            tempContainer.appendChild(leadersBox);
            tempContainer.appendChild(laggardsBox);

            result.innerHTML = coverageHtml;
            result.appendChild(tempContainer);
        } catch(e) {
            result.innerHTML = errorMessage(e.message);
        } finally {
            btn.textContent   = 'ESCANEAR AHORA';
            btn.style.opacity = '1';
        }
    });
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
        + '<div style="color:' + color + ';font-size:13px;margin-bottom:0.5rem;">' + title + '</div>'
        + '<div style="color:' + color + ';font-size:12px;">' + icon + ' ' + (msg || 'Error') + '</div>'
        + '</div>';
}