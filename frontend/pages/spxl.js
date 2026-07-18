import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';
export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">SPXL STRATEGY ' + tt('spxl') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Estrategia DCA apalancada · 6 fases · 3x S&P 500</div>'
        + '</div>'
        + '<div id="spxl-live" style="margin-bottom:1.5rem;"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando datos en vivo...</div></div>'
        + '<div id="spxl-phases" style="margin-bottom:1.5rem;"></div>'
        + '<div id="spxl-backtest-section">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.08em;border-left:3px solid var(--color-accent);padding-left:10px;">BACKTEST · SPXL 2008 → HOY</div>'
        + '<div style="display:flex;gap:8px;align-items:center;">'
        + '<label style="color:var(--color-muted);font-size:12px;">Capital:</label>'
        + '<input id="bt-capital" type="number" value="100000" min="1000" step="1000" style="width:120px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<button id="bt-run" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:6px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">EJECUTAR</button>'
        + '</div>'
        + '</div>'
        + '<div id="spxl-backtest"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Haz clic en EJECUTAR para correr el backtest (~10 segundos).</div></div>'
        + '</div>';

    loadLive(container);

    container.querySelector('#bt-run')?.addEventListener('click', () => {
        const capital = parseFloat(container.querySelector('#bt-capital').value) || 100000;
        loadBacktest(container, capital);
    });
}

async function loadLive(container) {
    const el    = container.querySelector('#spxl-live');
    const token = sessionStorage.getItem('rsu_token');

    try {
        const res  = await fetch('/api/v1/spxl/live', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);

        const chgColor  = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
        const ddColor   = data.dd_pct  < -30 ? '#f23645' : data.dd_pct < -15 ? '#ff9800' : 'var(--color-accent)';
        const mktColor  = data.market_open ? 'var(--color-accent)' : '#f23645';
        const mktLabel  = data.market_open ? '● OPEN' : '● CLOSED';

        // Header KPIs
        el.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:1rem;">'
            + kpiCard('SPXL PRECIO', '$' + data.price.toLocaleString('en-US'), (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '% hoy', chgColor)
            + kpiCard('DRAWDOWN ' + tt('spxl-phases'), data.dd_pct.toFixed(1) + '%', 'vs máximo histórico', ddColor)
            + kpiCard('MÁXIMO', '$' + data.spxl_high.toLocaleString('en-US'), 'Referencia', 'var(--color-muted)')
            + kpiCard('MERCADO', mktLabel, 'NYSE', mktColor)
            + (data.vix     ? kpiCard('VIX', data.vix.toFixed(2), (data.vix_chg >= 0 ? '+' : '') + data.vix_chg.toFixed(2), data.vix_chg >= 0 ? '#f23645' : 'var(--color-accent)') : '')
            + (data.bond10y ? kpiCard('10Y UST', data.bond10y.toFixed(2) + '%', (data.bond10y_chg >= 0 ? '+' : '') + data.bond10y_chg.toFixed(2), 'var(--color-muted)') : '')
            + (data.cds     ? kpiCard('HY SPREAD ' + tt('spxl-cds'), data.cds.toFixed(2) + '%', 'Credit Spreads', data.cds > 5 ? '#f23645' : data.cds > 4 ? '#ff9800' : 'var(--color-accent)') : '')
            + '</div>'

            // Fase actual
            + '<div style="background:var(--color-surface);border:1px solid ' + data.phase_color + '44;border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;">'
            + '<div>'
            + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.1em;margin-bottom:4px;">FASE ACTUAL ' + tt('spxl-phases') + '</div>'
            + '<div style="color:' + data.phase_color + ';font-size:28px;font-weight:500;letter-spacing:0.1em;">' + data.phase + '</div>'
            + '</div>'
            + '<div style="text-align:right;">'
            + '<div style="color:var(--color-muted);font-size:11px;">SPX: <span style="color:var(--color-text);">' + (data.spx_price ? '$' + data.spx_price.toLocaleString('en-US') : 'N/A') + '</span></div>'
            + (data.spx_chg ? '<div style="color:' + (data.spx_chg >= 0 ? 'var(--color-accent)' : '#f23645') + ';font-size:11px;">' + (data.spx_chg >= 0 ? '+' : '') + data.spx_chg.toFixed(2) + '% hoy</div>' : '')
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">Actualizado: ' + data.timestamp + '</div>'
            + '</div>'
            + '</div>'
            + '</div>'

            // Gráfico con las 6 fases marcadas
            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:8px;">SPXL · ÚLTIMOS 90 DÍAS · NIVELES DE FASE MARCADOS</div>'
            + '<div style="position:relative;height:280px;"><canvas id="spxl-spark"></canvas></div>'
            + '</div>';

        // Fases
        renderPhases(container, data);
        renderSparkline(data);

    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderPhases(container, data) {
    const el = container.querySelector('#spxl-phases');
    if (!el) return;

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">PLAN DE COMPRAS · 6 FASES DCA ' + tt('spxl-phases') + '</div>'
        + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:12px;">'
        + '<thead><tr style="border-bottom:1px solid var(--color-border);">'
        + ['FASE','CAÍDA REQUERIDA','PRECIO OBJETIVO','ASIGNACIÓN'].map(h =>
            '<th style="padding:8px 14px;text-align:left;color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">' + h + '</th>'
        ).join('')
        + '</tr></thead>'
        + '<tbody>'
        + data.phases.map(p => {
            const active = p.active;
            const bg     = active ? 'rgba(0,255,173,0.05)' : 'transparent';
            const tc     = active ? 'var(--color-accent)' : 'var(--color-text)';
            return '<tr style="border-bottom:1px solid var(--color-border);background:' + bg + ';">'
                + '<td style="padding:9px 14px;color:' + tc + ';font-weight:' + (active ? '500' : 'normal') + ';">FASE ' + p.phase + (active ? ' ◄' : '') + '</td>'
                + '<td style="padding:9px 14px;color:var(--color-muted);">-' + p.drop.toFixed(0) + '%</td>'
                + '<td style="padding:9px 14px;color:' + tc + ';">$' + p.target.toLocaleString('en-US') + '</td>'
                + '<td style="padding:9px 14px;color:var(--color-accent);">' + p.alloc.toFixed(0) + '%</td>'
                + '</tr>';
        }).join('')
        + '</tbody></table>'

        // Escenarios de salida
        + '<div style="padding:1rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-secondary);font-size:11px;letter-spacing:0.08em;margin-bottom:0.75rem;">ESCENARIOS DE SALIDA</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem;">'
        + scenarioCard('A', '≤3 fases', ['+20% → vender 95%', 'Runner 5% trailing 11%'])
        + scenarioCard('B', '4-5 fases', ['+10% → vender 80%', 'Runner 20% trailing 11%'])
        + scenarioCard('C', '6 fases', ['+5% → trim 65%', '+10% → trim 15%', '+20% → cierre final'])
        + '</div>'
        + '</div>'
        + '</div>';
}

async function loadBacktest(container, capital) {
    const el    = container.querySelector('#spxl-backtest');
    const btn   = container.querySelector('#bt-run');
    const token = sessionStorage.getItem('rsu_token');

    btn.textContent  = 'EJECUTANDO...';
    btn.style.opacity = '0.7';
    el.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Ejecutando backtest desde 2008... esto puede tardar ~15 segundos.</div>';

    try {
        const res  = await fetch('/api/v1/spxl/backtest?capital=' + capital, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);

        const s = data.stats;
        const stratColor = s.total_return >= s.bnh_return ? 'var(--color-accent)' : '#ff9800';

        el.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin-bottom:1rem;">'
            + kpiCard('Equity Final', '$' + s.final_equity.toLocaleString('en-US', {maximumFractionDigits:0}), 'Estrategia RSU', stratColor)
            + kpiCard('B&H Final',   '$' + s.final_bnh.toLocaleString('en-US', {maximumFractionDigits:0}),   'Buy & Hold',    'var(--color-muted)')
            + kpiCard('CAGR',        s.cagr.toFixed(1) + '%',      'Estrategia', stratColor)
            + kpiCard('CAGR B&H',    s.bnh_cagr.toFixed(1) + '%',  'Buy & Hold', 'var(--color-muted)')
            + kpiCard('Win Rate',    s.win_rate.toFixed(1) + '%',   s.total_trades + ' trades', 'var(--color-accent)')
            + kpiCard('Max DD',      '-' + s.max_dd.toFixed(1) + '%', 'Drawdown máximo', '#f23645')
            + kpiCard('Avg Win',     '+' + s.avg_win.toFixed(1) + '%', 'Por trade', 'var(--color-accent)')
            + kpiCard('Años',        s.years.toFixed(1), '2008 → hoy', 'var(--color-muted)')
            + '</div>'

            // Equity chart
            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">CURVA DE EQUITY</div>'
            + '<div style="position:relative;height:200px;"><canvas id="equity-chart"></canvas></div>'
            + '</div>'

            // Últimos trades
            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
            + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">ÚLTIMOS TRADES</div>'
            + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:11px;">'
            + '<thead><tr style="border-bottom:1px solid var(--color-border);">'
            + ['Fecha','Precio','Avg Cost','P&L','P&L %','Fases','Escenario','Hold días'].map(h =>
                '<th style="padding:7px 12px;text-align:left;color:var(--color-muted);font-size:10px;">' + h + '</th>'
            ).join('')
            + '</tr></thead><tbody>'
            + [...data.trades].reverse().slice(0, 20).map(t => {
                const c = t.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
                return '<tr style="border-bottom:1px solid var(--color-border);">'
                    + '<td style="padding:7px 12px;color:var(--color-muted);">' + t.date + '</td>'
                    + '<td style="padding:7px 12px;color:var(--color-text);">$' + t.exit_price + '</td>'
                    + '<td style="padding:7px 12px;color:var(--color-muted);">$' + t.avg_cost + '</td>'
                    + '<td style="padding:7px 12px;color:' + c + ';">' + (t.pnl >= 0 ? '+' : '') + '$' + t.pnl.toLocaleString('en-US', {maximumFractionDigits:0}) + '</td>'
                    + '<td style="padding:7px 12px;color:' + c + ';">' + (t.pnl_pct >= 0 ? '+' : '') + t.pnl_pct.toFixed(1) + '%</td>'
                    + '<td style="padding:7px 12px;color:var(--color-muted);">' + t.phases + '</td>'
                    + '<td style="padding:7px 12px;color:var(--color-secondary);">' + t.scenario + '</td>'
                    + '<td style="padding:7px 12px;color:var(--color-muted);">' + t.hold_days + 'd</td>'
                    + '</tr>';
            }).join('')
            + '</tbody></table></div>';

        renderEquityChart(data);

    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    } finally {
        btn.textContent   = 'EJECUTAR';
        btn.style.opacity = '1';
    }
}

function renderSparkline(data) {
    if (!data.chart || !data.chart.closes.length) return;
    loadChartJs(() => {
        const ctx = document.getElementById('spxl-spark');
        if (!ctx) return;
        const color = data.chg_pct >= 0 ? '#00ffad' : '#f23645';
        const labels = data.chart.dates;

        // Líneas horizontales de nivel — una por fase, solo las que caen
        // dentro del rango visible del gráfico (si no, solo añaden ruido
        // y aplastan la escala del precio real).
        const phaseColors = ['#00ffad', '#00ffad', '#ff9800', '#ff9800', '#f23645', '#f23645'];
        const priceMin = Math.min(...data.chart.closes);
        const priceMax = Math.max(...data.chart.closes);
        const visibleRange = [priceMin * 0.85, priceMax * 1.05]; // margen para que se vean fases cercanas aunque no esten exactamente dentro

        const phaseDatasets = (data.phases || [])
            .filter(p => p.target >= visibleRange[0] && p.target <= visibleRange[1])
            .map(p => ({
                label: 'Fase ' + p.phase + (p.active ? ' (activa)' : ''),
                data: labels.map(() => p.target),
                borderColor: phaseColors[p.phase - 1] || '#666',
                borderWidth: p.active ? 2 : 1,
                borderDash: p.active ? [] : [4, 4],
                pointRadius: 0,
                fill: false,
            }));

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'SPXL', data: data.chart.closes, borderColor: color, backgroundColor: color + '18', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3 },
                    ...phaseDatasets,
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#666', font: { size: 9 }, boxWidth: 10 } },
                    tooltip: { backgroundColor: '#111', borderColor: '#333', borderWidth: 1, titleColor: '#aaa', bodyColor: '#ccc',
                        callbacks: { label: item => item.dataset.label + ': $' + Number(item.parsed.y).toLocaleString('en-US') }
                    }
                },
                scales: {
                    x: { ticks: { color: '#444', font: { size: 9 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#444', font: { size: 9 }, callback: v => '$' + Number(v).toLocaleString('en-US') }, grid: { color: 'rgba(255,255,255,0.03)' } }
                }
            }
        });
    });
}

function renderEquityChart(data) {
    loadChartJs(() => {
        const ctx = document.getElementById('equity-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.equity_chart.map(p => p.date),
                datasets: [
                    { label: 'Estrategia RSU', data: data.equity_chart.map(p => p.equity), borderColor: '#00ffad', backgroundColor: '#00ffad18', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 },
                    { label: 'Buy & Hold',      data: data.bnh_chart.map(p => p.equity),    borderColor: '#555',    backgroundColor: 'transparent', borderWidth: 1, pointRadius: 0, fill: false, tension: 0.3 },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#666', font: { size: 10 } } } },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#555', font: { size: 9 }, callback: v => '$' + (v/1000).toFixed(0) + 'k' }, grid: { color: 'rgba(255,255,255,0.03)' } }
                }
            }
        });
    });
}

function kpiCard(label, value, sub, color) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + value + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + sub + '</div>'
        + '</div>';
}

function scenarioCard(id, label, rules) {
    const colors = { A: 'var(--color-accent)', B: '#ffb800', C: '#f23645' };
    const c = colors[id] || 'var(--color-muted)';
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid ' + c + '33;border-radius:var(--radius);padding:0.75rem;">'
        + '<div style="color:' + c + ';font-size:13px;font-weight:500;margin-bottom:2px;">Escenario ' + id + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">' + label + '</div>'
        + rules.map(r => '<div style="color:var(--color-text);font-size:11px;padding:2px 0;">▸ ' + r + '</div>').join('')
        + '</div>';
}

function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = cb;
    document.head.appendChild(s);
}