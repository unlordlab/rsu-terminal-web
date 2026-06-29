import { api } from '/core/api.js';
import { errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = `
        <div style="margin-bottom:2rem;">
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">DASHBOARD</div>
            <div style="color:var(--color-muted);font-size:12px;">Bienvenido a RSU Terminal v2.0</div>
        </div>
        <div id="daily-quote" style="margin-bottom:1.5rem;"></div>
        <div id="algoritmo-widget" style="margin-bottom:1.5rem;"></div>
        <div id="health-card" style="
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            font-size: 13px;
            color: var(--color-muted);
        ">Comprobando servidor...</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:1.5rem;">
            ${modules.map(m => `
                <div class="module-card" data-path="${m.path}" style="
                    background:var(--color-surface);
                    border:1px solid var(--color-border);
                    border-radius:var(--radius);
                    padding:1.25rem;
                    cursor:pointer;
                    transition:all var(--transition);
                ">
                    <div style="color:var(--color-accent);font-size:20px;margin-bottom:8px;">${m.icon}</div>
                    <div style="color:var(--color-text);font-size:13px;margin-bottom:4px;letter-spacing:0.05em;">${m.label}</div>
                    <div style="color:var(--color-muted);font-size:11px;">${m.desc}</div>
                </div>
            `).join('')}
        </div>
    `;

    const style = document.createElement('style');
    style.textContent = `.module-card:hover{border-color:var(--color-accent)!important;background:var(--color-surface2,#1a1a1a)!important;}`;
    document.head.appendChild(style);

    container.querySelectorAll('.module-card').forEach(card => {
        card.addEventListener('click', () => window.__navigate(card.getAttribute('data-path')));
    });

    loadAlgoritmo(container.querySelector('#algoritmo-widget'));
    renderDailyQuote(container.querySelector('#daily-quote'));

    try {
        const health = await fetch('/health').then(r => r.json());
        const card = container.querySelector('#health-card');
        if (card) {
            card.style.borderColor = 'var(--color-accent)';
            card.innerHTML = '<span style="color:var(--color-accent);">● SERVIDOR ONLINE</span><span style="margin-left:1rem;">' + health.app + '</span>';
        }
    } catch {
        const card = container.querySelector('#health-card');
        if (card) {
            card.style.borderColor = '#f23645';
            card.innerHTML = '<span style="color:#f23645;">✗ SERVIDOR OFFLINE</span>';
        }
    }
}

// ── FRASE DEL DÍA ────────────────────────────────────────────────────────────
// Adaptado del header de la antigua RSU Terminal (Streamlit). La frase se fija
// una vez por sesión de navegador (sessionStorage), igual que hacía session_state.

const DAILY_QUOTES = [
    ["En un mercado alcista, las malas noticias se ignoran y las buenas noticias se celebran; en un mercado bajista, las buenas noticias se ignoran y las malas noticias se exageran.", ""],
    ["Hay una guerra de clases, de acuerdo, pero es mi clase, la clase rica, la que está haciendo la guerra, y la estamos ganando.", "Warren Buffett"],
    ["El mercado de valores es un mecanismo para transferir dinero de los impacientes a los pacientes.", "Warren Buffett"],
    ["El mercado no te gana; te ganas tú mismo al no poder controlar tus emociones.", "Jesse Livermore"],
    ["Las manos fuertes no compran en la euforia, compran cuando las manos débiles ya no pueden soportar más dolor.", ""],
    ["Cuando el último escéptico se vuelve alcista, es hora de vender.", ""],
    ["El mercado puede permanecer irracional más tiempo del que tú puedes permanecer solvente.", "John Maynard Keynes"],
    ["El éxito en el trading consiste en comprarle a los pesimistas y venderle a los optimistas.", ""],
    ["La bolsa es un lugar donde las crisis se preparan... es el árbol donde los pequeños inversores son sacudidos para que sus ahorros caigan en los bolsillos de los grandes especuladores.", "Friedrich Engels"],
    ["He estado especulando... en acciones americanas, pero sobre todo en las inglesas... No requiere mucho tiempo y uno puede correr algún riesgo para quitarle el dinero a sus enemigos.", "Karl Marx"],
];

function renderDailyQuote(el) {
    if (!el) return;

    let stored = null;
    try { stored = JSON.parse(sessionStorage.getItem('rsu_daily_quote') || 'null'); } catch {}

    let quote = stored;
    if (!quote || !Array.isArray(quote) || quote.length !== 2) {
        quote = DAILY_QUOTES[Math.floor(Math.random() * DAILY_QUOTES.length)];
        try { sessionStorage.setItem('rsu_daily_quote', JSON.stringify(quote)); } catch {}
    }

    const [text, author] = quote;
    const attribution = author ? ' — ' + author : '';

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:14px 20px;text-align:center;">'
        + '<div style="display:inline-block;font-family:var(--font-mono);font-size:12px;color:var(--color-muted);'
        + 'letter-spacing:0.02em;font-style:italic;line-height:1.6;max-width:760px;'
        + 'border-left:2px solid var(--color-accent);border-right:2px solid var(--color-accent);'
        + 'padding:4px 16px;">'
        + '\u201C' + text + '\u201D' + attribution
        + '</div>'
        + '</div>';
}

async function loadAlgoritmo(el) {
    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;color:var(--color-muted);font-size:12px;">Cargando algoritmo RSU...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/algoritmo/', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const chartId = 'algo-chart-' + Date.now();
        const isGreen = data.estado.startsWith('VERDE');
        const isAmbar = data.estado.startsWith('AMBAR');
        const isRed   = data.estado === 'ROJO';

        function luz(cls, on) {
            const cfg = {
                red: ['#ff6b6b,#f23645', '#f23645', '#f2364566'],
                yel: ['#ffb74d,#ff9800', '#ff9800', '#ff980066'],
                grn: ['#69f0ae,#00ffad', '#00ffad', '#00ffad66'],
            }[cls];
            return '<div style="width:56px;height:56px;border-radius:50%;margin:5px auto;transition:all 0.4s;'
                + 'border:3px solid ' + (on ? cfg[1] : 'var(--color-border)') + ';'
                + 'background:' + (on ? 'radial-gradient(circle at 30% 30%,' + cfg[0] + ')' : 'var(--color-bg,#0a0a0a)') + ';'
                + (on ? 'box-shadow:0 0 20px ' + cfg[2] + ';transform:scale(1.08);' : '')
                + '"></div>';
        }

        const semaforo = '<div style="text-align:center;">'
            + luz('red', isRed)
            + luz('yel', isAmbar)
            + luz('grn', isGreen)
            + '<div style="color:' + data.color + ';font-size:11px;letter-spacing:0.08em;margin-top:8px;">' + data.estado + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + data.score + '/100</div>'
            + '</div>';

        const factores = Object.entries(data.metricas)
            .filter(([k]) => k !== 'SMA200')
            .map(([key, m]) => {
                const pct = m.max > 0 ? Math.round(m.score / m.max * 100) : 0;
                return '<div style="margin-bottom:7px;">'
                    + '<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--color-muted);margin-bottom:2px;">'
                    + '<span>' + key + '</span><span style="color:' + m.color + ';">' + m.score + '/' + m.max + '</span>'
                    + '</div>'
                    + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:4px;">'
                    + '<div style="height:100%;width:' + pct + '%;background:' + m.color + ';border-radius:2px;"></div>'
                    + '</div>'
                    + '</div>';
            }).join('');

        el.innerHTML =
            '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'

            // Header
            + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
            + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">RSU ALGORITMO · DETECTOR DE FONDOS</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">SPY · Multi-factor V2.1</div>'
            + '</div>'

            // Body — tabla de 3 columnas con anchos fijos
            + '<table style="width:100%;border-collapse:collapse;"><tbody><tr style="vertical-align:top;">'

            // Col semáforo
            + '<td style="width:160px;padding:1.25rem;border-right:1px solid var(--color-border);text-align:center;">'
            + semaforo
            + '</td>'

            // Col score + detalles
            + '<td style="padding:1.25rem;border-right:1px solid var(--color-border);">'
            + '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:0.5rem;">'
            + '<span style="color:' + data.color + ';font-size:44px;font-weight:500;line-height:1;">' + data.score + '</span>'
            + '<span style="color:var(--color-muted);font-size:14px;">/100</span>'
            + '</div>'
            + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin-bottom:0.75rem;">'
            + '<div style="height:100%;width:' + data.score + '%;background:' + data.color + ';border-radius:4px;"></div>'
            + '</div>'
            + '<div style="color:' + data.color + ';font-size:14px;letter-spacing:0.12em;margin-bottom:0.5rem;">' + data.senal + '</div>'
            + '<div style="color:var(--color-muted);font-size:12px;line-height:1.6;margin-bottom:0.75rem;">' + data.recomendacion + '</div>'
            + '<div style="border-top:1px solid var(--color-border);padding-top:0.75rem;">'
            + data.detalles.map(d => {
                const c = d.startsWith('✓') ? 'var(--color-accent)' : d.startsWith('~') ? '#ffb800' : d.startsWith('✗') ? '#f23645' : 'var(--color-muted)';
                return '<div style="font-size:11px;color:' + c + ';padding:2px 0;">' + d + '</div>';
            }).join('')
            + '</div>'
            + (data.advertencias.length > 0
                ? '<div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--color-border);">'
                  + data.advertencias.map(a => '<div style="color:#ffb800;font-size:10px;padding:2px 0;">' + a + '</div>').join('')
                  + '</div>'
                : '')
            + '</td>'

            // Col factores + chart
            + '<td style="width:260px;padding:1.25rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:0.75rem;">FACTORES</div>'
            + factores
            + '<div style="margin-top:0.75rem;border-top:1px solid var(--color-border);padding-top:0.75rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">SPY · 60 DÍAS</div>'
            + '<div style="position:relative;height:80px;"><canvas id="' + chartId + '"></canvas></div>'
            + '</div>'
            + '</td>'

            + '</tr></tbody></table>'

            // Footer
            + '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);display:flex;justify-content:space-between;">'
            + '<span>Ventana: ' + VENTANA + ' días</span>'
            + '<span>Actualizado: ' + data.timestamp + '</span>'
            + '</div>'
            + '</div>';

        renderAlgoChart(chartId, data.chart, data.color);

    } catch(e) {
        el.innerHTML = '<div style="background:var(--color-surface);border:1px solid #f2364544;border-radius:var(--radius);">' + errorMessage('Error: ' + e.message, {padding: '1rem 1.25rem'}) + '</div>';
    }
}

const VENTANA = 10;

function renderAlgoChart(chartId, chart, color) {
    const closes = chart.closes;
    const sorted = [...closes].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.1)];
    const q3 = sorted[Math.floor(sorted.length * 0.9)];
    const filtered = {
        dates:  chart.dates.filter((_, i) => closes[i] >= q1 * 0.8 && closes[i] <= q3 * 1.2),
        closes: closes.filter(v => v >= q1 * 0.8 && v <= q3 * 1.2),
    };
    if (window.Chart) {
        drawAlgoChart(chartId, filtered, color);
        return;
    }
    const script  = document.createElement('script');
    script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    script.onload = () => drawAlgoChart(chartId, filtered, color);
    document.head.appendChild(script);
}

function drawAlgoChart(chartId, chart, color) {
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
                borderWidth:     1.5,
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
                x: { ticks: { color: '#444', font: { size: 9 }, maxTicksLimit: 5 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                y: { ticks: { color: '#444', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }
            }
        }
    });
}

const modules = [
    { path: '/market',    icon: '◈', label: 'MARKET',        desc: 'Dashboard de mercado' },
    { path: '/cartera',   icon: '◎', label: 'CARTERA',       desc: 'Portfolio tracker' },
    { path: '/rsrw',      icon: '◆', label: 'RS/RW',         desc: 'Scanner fuerza relativa' },
    { path: '/spxl',      icon: '▲', label: 'SPXL',          desc: 'Estrategia DCA apalancada' },
    { path: '/research',  icon: '◉', label: 'RESEARCH',      desc: 'Análisis con IA' },
    { path: '/canslim',   icon: '◈', label: 'CANSLIM',       desc: 'Screener CAN SLIM' },
    { path: '/algoritmo', icon: 'A', label: 'RSU ALGORITMO', desc: 'Detector de fondos' },
];