export async function render(container) {
    container.innerHTML = header()
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
        + analyzerPanel()
        + scannerPanel()
        + '</div>'
        + '<div id="canslim-result"></div>'
        + '<div id="canslim-scan-result"></div>';

    setupAnalyzer(container);
    setupScanner(container);
}

function header() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">CAN SLIM</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Screener IBD · Trend Template Minervini · S&P 500</div>'
        + '</div>';
}

function analyzerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS INDIVIDUAL</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<input id="ticker-input" type="text" placeholder="AAPL, NVDA, MSFT..." style="flex:1;background:var(--color-bg);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="analyze-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ANALIZAR</button>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:8px;">Introduce cualquier ticker del mercado americano</div>'
        + '</div>';
}

function scannerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">SCANNER S&P 500</div>'
        + '<div style="display:flex;gap:8px;align-items:center;">'
        + '<div style="color:var(--color-muted);font-size:12px;">Score mínimo:</div>'
        + '<select id="min-score" style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">'
        + '<option value="40">40 — Amplio</option>'
        + '<option value="60" selected>60 — Estándar</option>'
        + '<option value="80">80 — Estricto</option>'
        + '</select>'
        + '<button id="scan-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;flex:1;">ESCANEAR S&P 500</button>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:8px;">Escanea las primeras 200 acciones del S&P 500 · ~60 segundos</div>'
        + '</div>';
}

function setupAnalyzer(container) {
    const input = container.querySelector('#ticker-input');
    const btn   = container.querySelector('#analyze-btn');
    const result = container.querySelector('#canslim-result');

    async function doAnalyze() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;

        btn.textContent  = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Analizando ' + ticker + '...</div>';

        try {
            const res  = await fetch('/api/v1/canslim/analyze/' + ticker, { headers: authHeader() });
            const data = await res.json();

            if (!data.ok) throw new Error(data.error || 'Error de análisis');

            result.innerHTML = renderAnalysis(data);
            renderChart(data);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doAnalyze);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doAnalyze(); });
}

function setupScanner(container) {
    const btn    = container.querySelector('#scan-btn');
    const select = container.querySelector('#min-score');
    const result = container.querySelector('#canslim-scan-result');

    btn.addEventListener('click', async () => {
        const minScore = select.value;
        btn.textContent  = 'ESCANEANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Escaneando S&P 500... esto puede tardar ~60 segundos</div>';

        try {
            const res  = await fetch('/api/v1/canslim/scan?min_score=' + minScore, { headers: authHeader() });
            const data = await res.json();

            if (!data.ok) throw new Error('Error en el scan');

            result.innerHTML = renderScanResults(data);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'ESCANEAR S&P 500';
            btn.style.opacity = '1';
        }
    });
}

function renderAnalysis(data) {
    const chgColor = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr   = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';
    const scoreColor = data.canslim_score >= 70 ? 'var(--color-accent)' : data.canslim_score >= 50 ? '#ffb800' : '#f23645';
    const mktcapStr = data.mktcap >= 1e12 ? '$' + (data.mktcap/1e12).toFixed(1) + 'T' : data.mktcap >= 1e9 ? '$' + (data.mktcap/1e9).toFixed(1) + 'B' : '$' + (data.mktcap/1e6).toFixed(0) + 'M';

    const ibdRows = [
        ['RS Rating',        data.ibd.rs,        ratingColor(data.ibd.rs, 80, 60)],
        ['EPS Rating',       data.ibd.eps,       ratingColor(data.ibd.eps, 80, 60)],
        ['Composite',        data.ibd.composite, ratingColor(data.ibd.composite, 80, 60)],
        ['SMR Rating',       data.ibd.smr,       gradeColor(data.ibd.smr)],
        ['Acc/Dis Rating',   data.ibd.acc_dis,   gradeColor(data.ibd.acc_dis)],
    ].map(([label, val, color]) =>
        '<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
        + '<span style="color:var(--color-muted);">' + label + '</span>'
        + '<span style="color:' + color + ';font-weight:500;">' + val + '</span>'
        + '</div>'
    ).join('');

    const trendRows = Object.entries(data.trend.conditions).map(([label, ok]) =>
        '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:var(--color-muted);">' + label + '</span>'
        + '<span style="color:' + (ok ? 'var(--color-accent)' : '#f23645') + ';">' + (ok ? '✓' : '✗') + '</span>'
        + '</div>'
    ).join('');

    const fundRows = [
        ['EPS Growth',    data.fundamentals.eps_growth.toFixed(1) + '%'],
        ['Sales Growth',  data.fundamentals.sales_growth.toFixed(1) + '%'],
        ['ROE',           data.fundamentals.roe.toFixed(1) + '%'],
        ['Profit Margin', data.fundamentals.margins.toFixed(1) + '%'],
    ].map(([label, val]) =>
        '<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
        + '<span style="color:var(--color-muted);">' + label + '</span>'
        + '<span style="color:var(--color-text);">' + val + '</span>'
        + '</div>'
    ).join('');

    return '<div style="margin-top:1.5rem;">'

        // Header ticker
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        + '<div>'
        + '<div style="display:flex;align-items:baseline;gap:12px;">'
        + '<span style="color:var(--color-accent);font-size:22px;letter-spacing:0.1em;">' + data.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:13px;">' + data.name + '</span>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:4px;">' + data.sector + ' · ' + data.industry + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:20px;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:12px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + mktcapStr + ' market cap</div>'
        + '</div>'
        + '</div>'

        // Score bar
        + '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">CAN SLIM SCORE</span>'
        + '<span style="color:' + scoreColor + ';font-size:18px;font-weight:500;">' + data.canslim_score + '/100</span>'
        + '</div>'
        + '<div style="background:var(--color-surface2, #1a1a1a);border-radius:4px;height:8px;">'
        + '<div style="height:100%;width:' + data.canslim_score + '%;background:' + scoreColor + ';border-radius:4px;transition:width 0.5s;"></div>'
        + '</div>'
        + '</div>'
        + '</div>'

        // Grid 3 columnas
        + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'

        // IBD Ratings
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">IBD RATINGS</div>'
        + ibdRows
        + '</div>'

        // Trend Template
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">TREND TEMPLATE</div>'
        + '<div style="color:' + (data.trend.passed ? 'var(--color-accent)' : '#f23645') + ';font-size:11px;">' + data.trend.score + '/7 ' + (data.trend.passed ? '✓ PASS' : '✗ FAIL') + '</div>'
        + '</div>'
        + trendRows
        + '</div>'

        // Fundamentales
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">FUNDAMENTALES</div>'
        + fundRows
        + '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:4px;">RENDIMIENTO</div>'
        + '<div style="display:flex;gap:1rem;font-size:12px;">'
        + '<div><span style="color:var(--color-muted);">3M </span><span style="color:' + (data.perf['3m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['3m'] >= 0 ? '+' : '') + data.perf['3m'].toFixed(1) + '%</span></div>'
        + '<div><span style="color:var(--color-muted);">6M </span><span style="color:' + (data.perf['6m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['6m'] >= 0 ? '+' : '') + data.perf['6m'].toFixed(1) + '%</span></div>'
        + '<div><span style="color:var(--color-muted);">12M </span><span style="color:' + (data.perf['12m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['12m'] >= 0 ? '+' : '') + data.perf['12m'].toFixed(1) + '%</span></div>'
        + '</div>'
        + '</div>'
        + '</div>'

        + '</div>'

        // Chart
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">PRECIO — ÚLTIMOS 60 DÍAS</div>'
        + '<canvas id="canslim-chart" height="80"></canvas>'
        + '</div>'

        + '</div>';
}

function renderChart(data) {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    script.onload = function() {
        const ctx = document.getElementById('canslim-chart');
        if (!ctx) return;
        const color = data.chg_pct >= 0 ? '#00ffad' : '#f23645';
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.chart.dates,
                datasets: [{
                    data:            data.chart.closes,
                    borderColor:     color,
                    backgroundColor: color + '18',
                    borderWidth:     1.5,
                    pointRadius:     0,
                    fill:            true,
                    tension:         0.3,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 10 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: { ticks: { color: '#555', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
                }
            }
        });
    };
    document.head.appendChild(script);
}

function renderScanResults(data) {
    if (!data.candidates || data.candidates.length === 0) {
        return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;margin-top:1rem;">No se encontraron candidatos con el score mínimo seleccionado.</div>';
    }

    const header = '<div style="display:grid;grid-template-columns:80px 80px 90px 70px 70px 80px 80px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<div>TICKER</div><div>PRECIO</div><div>12M PERF</div><div>RS</div><div>ACC/DIS</div><div>VOL RATIO</div><div>TREND</div><div>SCORE</div>'
        + '</div>';

    const rows = data.candidates.map(c => {
        const perfColor  = c.perf_12m >= 0 ? 'var(--color-accent)' : '#f23645';
        const scoreColor = c.score >= 70 ? 'var(--color-accent)' : c.score >= 50 ? '#ffb800' : '#f23645';
        return '<div style="display:grid;grid-template-columns:80px 80px 90px 70px 70px 80px 80px 80px;gap:8px;padding:9px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;cursor:pointer;" class="scan-row" data-ticker="' + c.ticker + '">'
            + '<div style="color:var(--color-accent);font-weight:500;">' + c.ticker + '</div>'
            + '<div style="color:var(--color-text);">$' + c.price.toLocaleString('en-US') + '</div>'
            + '<div style="color:' + perfColor + ';">' + (c.perf_12m >= 0 ? '+' : '') + c.perf_12m.toFixed(1) + '%</div>'
            + '<div style="color:' + ratingColor(c.rs, 80, 60) + ';">' + c.rs + '</div>'
            + '<div style="color:' + gradeColor(c.acc_dis) + ';">' + c.acc_dis + '</div>'
            + '<div style="color:' + (c.vol_ratio >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)') + ';">' + c.vol_ratio.toFixed(1) + 'x</div>'
            + '<div style="color:' + (c.trend ? 'var(--color-accent)' : '#f23645') + ';">' + (c.trend ? '✓' : '✗') + '</div>'
            + '<div style="color:' + scoreColor + ';font-weight:500;">' + c.score + '</div>'
            + '</div>';
    }).join('');

    const summary = '<div style="display:flex;gap:1.5rem;padding:8px 14px;font-size:11px;color:var(--color-muted);border-bottom:1px solid var(--color-border);">'
        + '<span>Escaneados: <b style="color:var(--color-text);">' + data.scanned + '</b></span>'
        + '<span>Candidatos: <b style="color:var(--color-accent);">' + data.total + '</b></span>'
        + '<span>Mostrando: <b style="color:var(--color-text);">' + data.candidates.length + '</b></span>'
        + '<span style="margin-left:auto;">Actualizado: ' + data.timestamp + '</span>'
        + '</div>';

    const html = '<div style="margin-top:1.5rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">RESULTADOS DEL SCAN</div>'
        + summary
        + header
        + rows
        + '</div>';

    setTimeout(() => {
        document.querySelectorAll('.scan-row').forEach(row => {
            row.addEventListener('mouseenter', () => row.style.background = 'var(--color-surface2, #1a1a1a)');
            row.addEventListener('mouseleave', () => row.style.background = 'transparent');
            row.addEventListener('click', () => {
                const ticker = row.getAttribute('data-ticker');
                document.getElementById('ticker-input').value = ticker;
                document.getElementById('analyze-btn').click();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }, 100);

    return html;
}

function ratingColor(val, high, mid) {
    if (val >= high) return 'var(--color-accent)';
    if (val >= mid)  return '#ffb800';
    return '#f23645';
}

function gradeColor(grade) {
    if (grade === 'A') return 'var(--color-accent)';
    if (grade === 'B') return '#90ee90';
    if (grade === 'C') return '#ffb800';
    if (grade === 'D') return '#ff8c00';
    return '#f23645';
}

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}