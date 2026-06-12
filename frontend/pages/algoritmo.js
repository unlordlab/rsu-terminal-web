export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ALGORITMO</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Detector de fondos · Multi-factor V2.1 · SPY</div>'
        + '</div>'
        + '<div id="algo-content"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div></div>';

    const el    = container.querySelector('#algo-content');
    const token = sessionStorage.getItem('rsu_token');

    try {
        const res  = await fetch('/api/v1/algoritmo/', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const chartId = 'algo-full-chart-' + Date.now();
        const isGreen = data.estado.startsWith('VERDE');
        const isAmbar = data.estado.startsWith('AMBAR');
        const isRed   = data.estado === 'ROJO';

        function luz(cls, on) {
            const cfg = {
                red: ['#ff6b6b,#f23645', '#f23645', '#f2364566'],
                yel: ['#ffb74d,#ff9800', '#ff9800', '#ff980066'],
                grn: ['#69f0ae,#00ffad', '#00ffad', '#00ffad66'],
            }[cls];
            return '<div style="width:80px;height:80px;border-radius:50%;margin:8px auto;transition:all 0.4s;'
                + 'border:4px solid ' + (on ? cfg[1] : 'var(--color-border)') + ';'
                + 'background:' + (on ? 'radial-gradient(circle at 30% 30%,' + cfg[0] + ')' : 'var(--color-bg,#0a0a0a)') + ';'
                + (on ? 'box-shadow:0 0 30px ' + cfg[2] + ';transform:scale(1.1);' : '')
                + '"></div>';
        }

        const semaforo = '<div style="text-align:center;padding:1.5rem 1rem;">'
            + luz('red', isRed)
            + luz('yel', isAmbar)
            + luz('grn', isGreen)
            + '<div style="color:' + data.color + ';font-size:16px;letter-spacing:0.12em;margin-top:12px;font-weight:500;">' + data.estado + '</div>'
            + '<div style="color:var(--color-muted);font-size:12px;margin-top:4px;">' + data.score + ' / 100</div>'
            + '</div>';

        const factores = Object.entries(data.metricas)
            .filter(([k]) => k !== 'SMA200')
            .map(([key, m]) => {
                const pct = m.max > 0 ? Math.round(m.score / m.max * 100) : 0;
                return '<div style="margin-bottom:10px;">'
                    + '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">'
                    + '<span style="color:var(--color-muted);">' + key + '</span>'
                    + '<span style="color:' + m.color + ';font-weight:500;">' + m.score + ' / ' + m.max + '</span>'
                    + '</div>'
                    + '<div style="background:var(--color-bg,#0a0a0a);border-radius:3px;height:6px;">'
                    + '<div style="height:100%;width:' + pct + '%;background:' + m.color + ';border-radius:3px;transition:width 0.8s;"></div>'
                    + '</div>'
                    + '</div>';
            }).join('');

        const detallesHtml = data.detalles.map(d => {
            const c = d.startsWith('✓') ? 'var(--color-accent)' : d.startsWith('~') ? '#ffb800' : d.startsWith('✗') ? '#f23645' : 'var(--color-muted)';
            return '<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;color:' + c + ';">' + d + '</div>';
        }).join('');

        const advertenciasHtml = data.advertencias.length > 0
            ? '<div style="margin-top:1rem;padding:1rem;background:rgba(255,184,0,0.05);border:1px solid rgba(255,184,0,0.2);border-radius:var(--radius);">'
              + '<div style="color:#ffb800;font-size:11px;letter-spacing:0.08em;margin-bottom:8px;">ADVERTENCIAS</div>'
              + data.advertencias.map(a => '<div style="color:#ffb800;font-size:12px;padding:3px 0;">' + a + '</div>').join('')
              + '</div>'
            : '';

        const mediasHtml = Object.entries(data.medias).map(([k, v]) =>
            '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
            + '<span style="color:var(--color-muted);">' + k.toUpperCase() + '</span>'
            + '<span style="color:var(--color-text);">$' + v.toLocaleString('en-US') + '</span>'
            + '</div>'
        ).join('');

        el.innerHTML =
            // Fila 1: semáforo + score + recomendación
            '<div style="display:grid;grid-template-columns:200px 1fr;gap:1rem;margin-bottom:1rem;">'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);">'
            + semaforo
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;">'
            + '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:0.75rem;">'
            + '<span style="color:' + data.color + ';font-size:56px;font-weight:500;line-height:1;">' + data.score + '</span>'
            + '<span style="color:var(--color-muted);font-size:18px;">/100</span>'
            + '</div>'
            + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:8px;margin-bottom:1rem;">'
            + '<div style="height:100%;width:' + data.score + '%;background:' + data.color + ';border-radius:4px;transition:width 1s;"></div>'
            + '</div>'
            + '<div style="color:' + data.color + ';font-size:18px;letter-spacing:0.15em;margin-bottom:0.75rem;font-weight:500;">' + data.senal + '</div>'
            + '<div style="color:var(--color-text);font-size:13px;line-height:1.7;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border-left:3px solid ' + data.color + ';">'
            + data.recomendacion
            + '</div>'
            + advertenciasHtml
            + '</div>'
            + '</div>'

            // Fila 2: factores + detalles + medias
            + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">FACTORES · SCORES</div>'
            + factores
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS DE CONDICIONES</div>'
            + detallesHtml
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">MEDIAS MÓVILES · SPY</div>'
            + mediasHtml
            + '</div>'

            + '</div>'

            // Fila 3: chart completo
            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">SPY · HISTÓRICO 60 DÍAS</div>'
            + '<div style="position:relative;height:200px;">'
            + '<canvas id="' + chartId + '"></canvas>'
            + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:8px;text-align:right;">Actualizado: ' + data.timestamp + ' · Ventana de condiciones: 10 días</div>'
            + '</div>';

        renderChart(chartId, data.chart, data.color);

    } catch(e) {
        el.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
    }
}

function renderChart(chartId, chart, color) {
    const closes = chart.closes;
    const sorted = [...closes].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.1)];
    const q3 = sorted[Math.floor(sorted.length * 0.9)];
    const filtered = {
        dates:  chart.dates.filter((_, i) => closes[i] >= q1 * 0.8 && closes[i] <= q3 * 1.2),
        closes: closes.filter(v => v >= q1 * 0.8 && v <= q3 * 1.2),
    };

    if (window.Chart) {
        drawChart(chartId, filtered, color);
        return;
    }
    const script  = document.createElement('script');
    script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    script.onload = () => drawChart(chartId, filtered, color);
    document.head.appendChild(script);
}

function drawChart(chartId, chart, color) {
    const ctx = document.getElementById(chartId);
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: chart.dates,
            datasets: [{
                data:            chart.closes,
                borderColor:     color,
                backgroundColor: color + '18',
                borderWidth:     2,
                pointRadius:     0,
                fill:            true,
                tension:         0.3,
            }]
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#555', font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                y: {
                    ticks: { color: '#555', font: { size: 10 } },
                    grid:  { color: 'rgba(255,255,255,0.04)' },
                    min:   Math.min(...chart.closes) * 0.995,
                    max:   Math.max(...chart.closes) * 1.005,
                }
            }
        }
    });
}