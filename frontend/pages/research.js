export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RESEARCH</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Análisis fundamental · yfinance · Finnhub · Alpha Vantage</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="research-input" type="text" placeholder="AAPL, NVDA, TSLA..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:14px;outline:none;">'
        + '<button id="research-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:13px;cursor:pointer;letter-spacing:0.05em;font-weight:500;">ANALIZAR</button>'
        + '</div>'
        + '<div id="research-result"></div>';

    const input  = container.querySelector('#research-input');
    const btn    = container.querySelector('#research-btn');
    const result = container.querySelector('#research-result');

    // Auto-cargar ticker si viene en la URL
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        input.value = urlTicker.toUpperCase();
        setTimeout(() => doResearch(), 100);
    } else {
        input.focus();
    }

    input.focus();

    async function doResearch() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent  = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando datos de ' + ticker + '...</div>';

        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/research/' + ticker, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Sin datos');
            result.innerHTML = renderResearch(data);
            renderSparkline(data);
            renderEarningsChart(data);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doResearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doResearch(); });
}

function renderResearch(data) {
    const chgColor  = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr    = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';
    const score     = data.rsu_score;
    const scoreColor = score.color;

    // Header
    const header = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">'
        + '<div>'
        + '<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px;">'
        + '<span style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + data.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + data.name + '</span>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">' + data.sector + ' · ' + data.industry + ' · ' + data.country + '</div>'
        + (data.website ? '<a href="' + data.website + '" target="_blank" style="color:var(--color-secondary);font-size:11px;">' + data.website + '</a>' : '')
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:28px;font-weight:500;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + data.mktcap_fmt + ' market cap</div>'
        + '</div>'
        + '</div>'

        // RSU Score
        + '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">RSU SCORE</span>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span style="color:' + scoreColor + ';font-size:20px;font-weight:500;">' + score.score + '/100</span>'
        + '<span style="color:' + scoreColor + ';font-size:12px;letter-spacing:0.08em;padding:2px 10px;border:1px solid ' + scoreColor + '33;border-radius:4px;">' + score.label + '</span>'
        + '</div></div>'
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;">'
        + '<div style="height:100%;width:' + score.score + '%;background:' + scoreColor + ';border-radius:4px;transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="display:flex;gap:1rem;margin-top:8px;flex-wrap:wrap;">'
        + score.breakdown.map(b => {
            const pct = b.max > 0 ? Math.round(b.pts / b.max * 100) : 0;
            return '<div style="font-size:10px;color:var(--color-muted);">'
                + b.label + ': <span style="color:' + (pct >= 75 ? 'var(--color-accent)' : pct >= 50 ? '#ffb800' : '#f23645') + ';">' + b.pts + '/' + b.max + '</span>'
                + ' <span style="color:var(--color-muted);">(' + b.val + ')</span>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>'
        + '</div>';

    // Sparkline + 52w
    const sparklineSection = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">PRECIO · 3 MESES</div>'
        + '<div style="display:flex;gap:1.5rem;font-size:11px;color:var(--color-muted);">'
        + (data.week52_low  ? '<span>52w Low: <b style="color:var(--color-text);">$' + data.week52_low.toFixed(2)  + '</b></span>' : '')
        + (data.week52_high ? '<span>52w High: <b style="color:var(--color-text);">$' + data.week52_high.toFixed(2) + '</b></span>' : '')
        + (data.beta        ? '<span>Beta: <b style="color:var(--color-text);">' + data.beta.toFixed(2) + '</b></span>' : '')
        + '</div>'
        + '</div>'
        + '<div style="position:relative;height:80px;"><canvas id="sparkline-chart"></canvas></div>'
        + '</div>';

    // Grid métricas
    const metricsGrid = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + metricCard('VALORACIÓN', [
            ['P/E Trailing',  data.metrics.trailing_pe,    v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['P/E Forward',   data.metrics.forward_pe,     v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['P/S',           data.metrics.price_to_sales, v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['EV/EBITDA',     data.metrics.ev_ebitda,      v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['PEG',           data.metrics.peg_ratio,      v => v ? v.toFixed(2)        : 'N/A'],
            ['P/B',           data.metrics.price_to_book,  v => v ? v.toFixed(2) + 'x' : 'N/A'],
        ])
        + metricCard('RENTABILIDAD', [
            ['ROE',           data.profitability.roe,             v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['ROA',           data.profitability.roa,             v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Neto',   data.profitability.net_margin,      v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Op.',    data.profitability.op_margin,       v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Bruto',  data.profitability.gross_margin,    v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['D/E Ratio',     data.profitability.debt_to_equity,  v => v ? v.toFixed(0) + '%'        : 'N/A'],
        ])
        + metricCard('CRECIMIENTO', [
            ['Revenue Growth',  data.profitability.revenue_growth,  v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Earnings Growth', data.profitability.earnings_growth, v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Current Ratio',   data.profitability.current_ratio,   v => v ? v.toFixed(2) + 'x'        : 'N/A'],
            ['Dividend Yield',  data.dividend_yield,                v => v ? (v*100).toFixed(2) + '%' : 'N/A'],
            ['Analysts',        data.n_analysts,                    v => v ? v + ' analistas'           : 'N/A'],
        ])
        + '</div>';

    // Consenso analistas
    let consensoSection = '';
    if (data.recommendations && data.recommendations.total > 0) {
        const r    = data.recommendations;
        const total = r.total;
        const bars = [
            ['Strong Buy', r.strong_buy, '#00ffad'],
            ['Buy',        r.buy,        '#90ee90'],
            ['Hold',       r.hold,       '#ffb800'],
            ['Sell',       r.sell,       '#ff8c00'],
            ['Strong Sell',r.strong_sell,'#f23645'],
        ];
        consensoSection = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">CONSENSO ANALISTAS</div>'
            + '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">'
            + bars.map(([label, count, color]) => {
                const pct = total > 0 ? Math.round(count / total * 100) : 0;
                return '<div style="flex:1;min-width:80px;text-align:center;">'
                    + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + count + '</div>'
                    + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + label + '</div>'
                    + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:4px;margin-top:4px;">'
                    + '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:2px;"></div>'
                    + '</div>'
                    + '</div>';
            }).join('')
            + '</div>'
            + (data.target_data.mean ? '<div style="font-size:12px;color:var(--color-muted);">Precio objetivo: <span style="color:var(--color-text);">$' + data.target_data.mean.toFixed(2) + '</span> · Potencial: <span style="color:' + (data.target_data.upside >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.target_data.upside >= 0 ? '+' : '') + data.target_data.upside.toFixed(1) + '%</span></div>' : '')
            + '</div>';
    }

    // Sugerencias
    const suggestionsSection = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ANÁLISIS RSU</div>'
        + data.suggestions.map(s => '<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;color:var(--color-text);line-height:1.5;">' + s + '</div>').join('')
        + '</div>';

    // Earnings chart
    const earningsSection = data.quarterly_earnings && data.quarterly_earnings.length > 0
        ? '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
          + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">EPS TRIMESTRAL · HISTÓRICO</div>'
          + '<div style="position:relative;height:140px;"><canvas id="earnings-chart"></canvas></div>'
          + '</div>'
        : '';

    // Noticias
    let newsSection = '';
    if (data.news && data.news.length > 0) {
        newsSection = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">NOTICIAS RECIENTES</div>'
            + data.news.map(n => '<div style="padding:8px 0;border-bottom:1px solid var(--color-border);">'
                + '<a href="' + n.url + '" target="_blank" style="color:var(--color-text);font-size:12px;line-height:1.4;display:block;">' + n.headline + '</a>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-top:3px;">' + n.source + '</div>'
                + '</div>').join('')
            + '</div>';
    }

    // Descripción
    const descSection = data.description
        ? '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
          + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">DESCRIPCIÓN</div>'
          + '<div style="color:var(--color-muted);font-size:12px;line-height:1.7;">' + data.description.substring(0, 800) + (data.description.length > 800 ? '...' : '') + '</div>'
          + '</div>'
        : '';

    return header + sparklineSection + metricsGrid + consensoSection + suggestionsSection + earningsSection + newsSection + descSection;
}

function metricCard(title, rows) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:11px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
        + rows.map(([label, val, fmt]) => {
            const fmtVal = fmt(val);
            const isGood = fmtVal !== 'N/A';
            return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                + '<span style="color:var(--color-muted);">' + label + '</span>'
                + '<span style="color:' + (isGood ? 'var(--color-text)' : 'var(--color-muted)') + ';">' + fmtVal + '</span>'
                + '</div>';
        }).join('')
        + '</div>';
}

function renderSparkline(data) {
    if (!data.sparkline || data.sparkline.length < 2) return;
    const color = data.chg_pct >= 0 ? '#00ffad' : '#f23645';
    loadChartJs(() => {
        const ctx = document.getElementById('sparkline-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.sparkline.map((_, i) => i),
                datasets: [{
                    data: data.sparkline,
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
                    x: { display: false },
                    y: {
                        ticks: { color: '#555', font: { size: 9 } },
                        grid:  { color: 'rgba(255,255,255,0.04)' },
                        min:   Math.min(...data.sparkline) * 0.995,
                        max:   Math.max(...data.sparkline) * 1.005,
                    }
                }
            }
        });
    });
}

function renderEarningsChart(data) {
    if (!data.quarterly_earnings || data.quarterly_earnings.length === 0) return;
    const earnings = [...data.quarterly_earnings].reverse();
    loadChartJs(() => {
        const ctx = document.getElementById('earnings-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: earnings.map(e => e.date.substring(0, 7)),
                datasets: [
                    {
                        label: 'Reportado',
                        data: earnings.map(e => e.reported),
                        backgroundColor: earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad88' : '#f2364588'),
                        borderColor:     earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad' : '#f23645'),
                        borderWidth: 1,
                    },
                    {
                        label: 'Estimado',
                        data: earnings.map(e => e.estimated),
                        backgroundColor: 'transparent',
                        borderColor: '#ffb800',
                        borderWidth: 1.5,
                        type: 'line',
                        pointRadius: 3,
                        tension: 0.3,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#666', font: { size: 10 } } }
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }
                }
            }
        });
    });
}

function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = cb;
    document.head.appendChild(s);
}