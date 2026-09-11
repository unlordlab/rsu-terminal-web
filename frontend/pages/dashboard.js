import { api, authHeader, hasTier } from '/core/api.js';
import { errorMessage, esc } from '/core/ui.js';
import { NAV_ITEMS } from '/components/sidebar.js';
import { fraseDelDia } from '/pages/dashboard_frases.js';
import { MODULES, PHASES, leccionesDe } from '/pages/academy_modulos.js';
import { siguientePaso } from '/pages/academy_continuar.js';

export async function render(container) {
    container.innerHTML = `
        <div style="margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
                <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">DASHBOARD</div>
                <div style="color:var(--color-muted);font-size:12px;">Bienvenido a RSU Terminal v2.0</div>
            </div>
            <div id="health-badge" style="font-size:10px;color:var(--color-muted);padding:4px 10px;border:1px solid var(--color-border);border-radius:12px;">● comprobando...</div>
        </div>
        <div id="shortcuts-tip"></div>
        <div id="daily-quote" style="margin-bottom:1.5rem;"></div>
        <div id="pulse-strip" style="margin-bottom:1.5rem;"></div>
        <div id="academy-continuar"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
            <div id="briefing-preview"></div>
            <div id="watchlist-summary"></div>
        </div>
        <div id="algoritmo-widget" style="margin-bottom:1.5rem;"></div>
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
                    <div style="color:var(--color-text);font-size:13px;margin-bottom:4px;letter-spacing:0.05em;"${bloqueado(m.path) ? ' title="Requiere plan Tier 1 o superior"' : ''}>${m.label}${bloqueado(m.path) ? ' <span style="font-size:10px;opacity:0.6;">🔒</span>' : ''}</div>
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
    renderShortcutsTip(container.querySelector('#shortcuts-tip'));
    loadPulseStrip(container.querySelector('#pulse-strip'));
    loadAcademyContinuar(container.querySelector('#academy-continuar'));
    loadBriefingPreview(container.querySelector('#briefing-preview'));
    loadWatchlistSummary(container.querySelector('#watchlist-summary'));

    try {
        const health = await fetch('/health').then(r => r.json());
        const badge = container.querySelector('#health-badge');
        if (badge) {
            badge.style.borderColor = 'var(--color-accent)';
            badge.style.color = 'var(--color-accent)';
            badge.innerHTML = '● online';
            badge.title = health.app || '';
        }
    } catch {
        const badge = container.querySelector('#health-badge');
        if (badge) {
            badge.style.borderColor = '#f23645';
            badge.style.color = '#f23645';
            badge.innerHTML = '✗ offline';
        }
    }
}


// ── PULSO DE MERCADO ─────────────────────────────────────────────────────────

async function loadPulseStrip(el) {
    if (!el) return;
    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.8rem 1rem;color:var(--color-muted);font-size:11px;">Cargando pulso de mercado...</div>';
    try {
        const [idxRes, fgRes] = await Promise.all([
            fetch('/api/v1/market/indices', { headers: authHeader() }),
            fetch('/api/v1/market/fear-greed', { headers: authHeader() }),
        ]);
        const idx = await idxRes.json();
        const fg  = await fgRes.json();

        const spy = (idx.data || []).find(i => i.ticker === 'SPX') || (idx.data || [])[0];
        const vix = (idx.data || []).find(i => i.ticker === 'VIX');

        const pill = (label, valueHtml) =>
            '<div style="flex:1;min-width:120px;text-align:center;padding:0.6rem;">'
            + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;margin-bottom:3px;">' + label + '</div>'
            + '<div style="font-size:15px;font-weight:500;">' + valueHtml + '</div>'
            + '</div>';

        let html = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);display:flex;flex-wrap:wrap;divide-x:1px;">';
        if (spy && spy.ok) {
            const c = spy.pct >= 0 ? 'var(--color-accent)' : '#f23645';
            html += pill('S&amp;P 500', '<span style="color:' + c + ';cursor:pointer;" onclick="window.__navigate(\'/market\')">' + spy.price.toLocaleString('en-US') + ' (' + (spy.pct >= 0 ? '+' : '') + spy.pct.toFixed(2) + '%)</span>');
        }
        if (vix && vix.ok) {
            const c = vix.pct >= 0 ? '#f23645' : 'var(--color-accent)';
            html += pill('VIX', '<span style="color:' + c + ';">' + vix.price.toFixed(2) + '</span>');
        }
        if (fg && fg.ok) {
            const c = fg.score >= 55 ? 'var(--color-accent)' : fg.score <= 45 ? '#f23645' : '#ffb800';
            html += pill('FEAR &amp; GREED', '<span style="color:' + c + ';cursor:pointer;" onclick="window.__navigate(\'/market\')">' + fg.score + ' · ' + fg.rating + '</span>');
        }
        html += '</div>';
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = '';
    }
}

// ── VISTA PREVIA DEL DAILY BRIEFING ──────────────────────────────────────────

const BIAS_COLOR = { ALCISTA: 'var(--color-accent)', BAJISTA: '#f23645', NEUTRAL: '#ffb800' };

function briefingShell(inner) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;text-shadow:var(--glow-text);">DAILY BRIEFING</div>'
        + '</div>' + inner + '</div>';
}

async function loadBriefingPreview(el) {
    if (!el) return;
    el.innerHTML = briefingShell('<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando...</div>');
    try {
        const res  = await fetch('/api/v1/market/briefing', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok || !data.content) throw new Error('Sin briefing disponible todavía');

        const bias = (data.bias || '').toUpperCase();
        const biasColor = BIAS_COLOR[bias] || 'var(--color-muted)';
        const biasBadge = bias
            ? '<span style="color:' + biasColor + ';border:1px solid ' + biasColor + '55;border-radius:3px;padding:1px 8px;font-size:10px;">' + bias + '</span>'
            : '';

        // Primeras ~280 caracteres de texto plano, saltando la línea de título en negrita
        const plain  = data.content.replace(/\*\*/g, '').replace(/^#.*\n/, '').trim();
        const preview = plain.length > 280 ? plain.substring(0, 280).trim() + '…' : plain;

        el.innerHTML = briefingShell(
            '<div style="padding:1rem;display:flex;flex-direction:column;flex:1;">'
            + '<div style="margin-bottom:8px;">' + biasBadge + '</div>'
            + '<div style="color:var(--color-text);font-size:12px;line-height:1.6;flex:1;">' + preview + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:10px;border-top:1px solid var(--color-border);">'
            + '<span style="color:var(--color-muted);font-size:10px;">' + (data.updated || '') + '</span>'
            + '<span onclick="window.__navigate(\'/market\')" style="color:var(--color-secondary);font-size:11px;cursor:pointer;">Leer completo →</span>'
            + '</div>'
            + '</div>'
        );
    } catch (e) {
        el.innerHTML = briefingShell('<div style="padding:1rem;color:var(--color-muted);font-size:12px;">' + e.message + '</div>');
    }
}

// ── RESUMEN DE WATCHLIST + ALERTAS ───────────────────────────────────────────

function watchlistShell(inner) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;text-shadow:var(--glow-text);">WATCHLIST</div>'
        + '<span onclick="window.__navigate(\'/watchlist\')" style="color:var(--color-secondary);font-size:11px;cursor:pointer;">Ver todo →</span>'
        + '</div>' + inner + '</div>';
}

async function loadWatchlistSummary(el) {
    if (!el) return;
    el.innerHTML = watchlistShell('<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando...</div>');
    try {
        const [wlRes, countRes] = await Promise.all([
            fetch('/api/v1/watchlist', { headers: authHeader() }),
            fetch('/api/v1/watchlist/alerts/unseen-count', { headers: authHeader() }),
        ]);
        const wl    = await wlRes.json();
        const count = await countRes.json();

        const alertLine = count.count > 0
            ? '<div style="background:rgba(242,54,69,0.08);border:1px solid #f2364544;border-radius:6px;padding:6px 10px;margin-bottom:10px;color:#f23645;font-size:11px;cursor:pointer;" onclick="window.__navigate(\'/watchlist\')">🔔 ' + count.count + ' alerta' + (count.count > 1 ? 's' : '') + ' disparada' + (count.count > 1 ? 's' : '') + ' sin ver</div>'
            : '';

        if (!wl.ok || !wl.data.length) {
            el.innerHTML = watchlistShell(
                '<div style="padding:1rem;flex:1;">' + alertLine
                + '<div style="color:var(--color-muted);font-size:12px;text-align:center;padding:0.5rem 0;">Sin tickers en watchlist todavía</div></div>'
            );
            return;
        }

        const rows = wl.data.slice(0, 4).map(w => {
            // `w.chg` puede ser null cuando todavía no hay cotización de hoy.
            // Con `w.chg || 0` eso se pintaba como un "▲ 0.00%" inventado, que
            // es justo lo contrario de lo que hay que enseñar: sin dato, "—".
            const sinChg = w.chg == null;
            const up     = !sinChg && w.chg >= 0;
            const color  = (w.ok && !sinChg) ? (up ? 'var(--color-accent)' : '#f23645') : 'var(--color-muted)';
            return '<div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid var(--color-border);">'
                + '<span class="ticker-link" style="color:var(--color-accent);cursor:pointer;" onclick="window.__navigate(\'/research?ticker=' + w.ticker + '\')">' + w.ticker + '</span>'
                + '<span style="color:' + color + ';"' + (sinChg ? ' title="Todavía no hay cotización de hoy para este valor."' : '') + '>'
                + ((w.ok && !sinChg) ? (up ? '▲' : '▼') + ' ' + Math.abs(w.chg).toFixed(2) + '%' : '—') + '</span>'
                + '</div>';
        }).join('');

        el.innerHTML = watchlistShell('<div style="padding:1rem;flex:1;">' + alertLine + rows + '</div>');
    } catch (e) {
        el.innerHTML = watchlistShell('<div style="padding:1rem;color:var(--color-muted);font-size:12px;">' + e.message + '</div>');
    }
}

const SHORTCUTS_TIP_KEY = 'rsu_shortcuts_tip_dismissed';

function renderShortcutsTip(el) {
    if (!el) return;
    if (localStorage.getItem(SHORTCUTS_TIP_KEY)) return; // ya lo vio, no insistir

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 14px;margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:12px;">'
        + '<span style="color:var(--color-muted);">💡 Pulsa <span style="color:var(--color-accent);background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:4px;padding:1px 7px;">Ctrl/Cmd + K</span> para ir a cualquier sección al instante, o <span style="color:var(--color-accent);background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:4px;padding:1px 7px;">?</span> para ver todos los atajos.</span>'
        + '<button id="shortcuts-tip-dismiss" style="background:transparent;border:none;color:var(--color-muted);cursor:pointer;font-size:16px;line-height:1;flex-shrink:0;">✕</button>'
        + '</div>';

    el.querySelector('#shortcuts-tip-dismiss').addEventListener('click', () => {
        localStorage.setItem(SHORTCUTS_TIP_KEY, '1');
        el.innerHTML = '';
    });
}

// ── FRASE DEL DÍA ────────────────────────────────────────────────────────────
// Adaptado del header de la antigua RSU Terminal (Streamlit). Las frases y cómo
// se elige la de hoy viven en dashboard_frases.js.

function renderDailyQuote(el) {
    if (!el) return;

    const { texto, autor, fuente } = fraseDelDia();
    const firma = autor
        ? ' — ' + esc(autor)
          + (fuente ? '<div style="font-style:normal;font-size:10px;opacity:0.75;margin-top:4px;">' + esc(fuente) + '</div>' : '')
        : '';

    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:14px 20px;text-align:center;">'
        + '<div style="display:inline-block;font-family:var(--font-mono);font-size:12px;color:var(--color-muted);'
        + 'letter-spacing:0.02em;font-style:italic;line-height:1.6;max-width:760px;'
        + 'border-left:2px solid var(--color-accent);border-right:2px solid var(--color-accent);'
        + 'padding:4px 16px;">'
        + '“' + esc(texto) + '”' + firma
        + '</div>'
        + '</div>';
}

async function loadAlgoritmo(el) {
    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;color:var(--color-muted);font-size:12px;">Cargando algoritmo RSU...</div>';

    try {
        const res   = await fetch('/api/v1/algoritmo/', { headers: authHeader() });
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

// Una tarjeta por cada sección del menú lateral (NAV_ITEMS), salvo el propio
// Dashboard. Faltaban seis —Congress Trading, Track Record, Roadmap,
// Manifiesto, Equipo y Disclaimer— y un test obliga ahora a que cada sección
// nueva del menú tenga también su tarjeta aquí.
const modules = [
    { path: '/market',     icon: '◈', label: 'MARKET',        desc: 'Dashboard de mercado' },
    { path: '/cartera',    icon: '◎', label: 'CARTERA',       desc: 'Portfolio tracker' },
    { path: '/scanner',    icon: '⚡', label: 'SCANNER',       desc: 'Filtro S&P 500' },
    { path: '/watchlist',  icon: '★', label: 'WATCHLIST',     desc: 'Seguimiento + alertas' },
    { path: '/rsrw',       icon: '◆', label: 'RS/RW',         desc: 'Scanner fuerza relativa' },
    { path: '/research',   icon: '◉', label: 'RESEARCH',      desc: 'Análisis con IA' },
    { path: '/insider',    icon: '🔍', label: 'INSIDER FLOW',  desc: 'Compras/ventas de directivos' },
    { path: '/congress',   icon: '🏛️', label: 'CONGRESS TRADING', desc: 'Operaciones del Congreso de EE. UU.' },
    { path: '/options',    icon: '◐', label: 'OPTIONS FLOW',  desc: 'Actividad institucional' },
    { path: '/canslim',    icon: '◈', label: 'CANSLIM',       desc: 'Screener CAN SLIM' },
    { path: '/algoritmo',  icon: 'A', label: 'RSU ALGORITMO', desc: 'Detector de fondos' },
    { path: '/track-record', icon: '📓', label: 'TRACK RECORD', desc: 'Lo que hicieron de verdad las señales' },
    { path: '/tesis',      icon: '📄', label: 'TESIS',         desc: 'Análisis de inversión RSU' },
    { path: '/spxl',       icon: '▲', label: 'SPXL',          desc: 'Estrategia DCA apalancada' },
    { path: '/btc-stratum', icon: '₿', label: 'BTC STRATUM',  desc: 'On-chain Bitcoin' },
    { path: '/newsfeed',   icon: '📰', label: 'NEWS FEED',     desc: 'Noticias de mercado' },
    { path: '/academy',    icon: '🎓', label: 'ACADEMIA',      desc: MODULES.length + ' módulos de formación' },
    { path: '/roadmap',    icon: '🗺️', label: 'ROADMAP 2026',  desc: 'Escenario de mercado y su revisión' },
    { path: '/manifiesto', icon: '📜', label: 'MANIFIESTO',    desc: 'Por qué existe RSU' },
    { path: '/equipo',     icon: '🤖', label: 'EQUIPO RSU',    desc: 'Los agentes de la terminal' },
    { path: '/community',  icon: '👥', label: 'COMUNIDAD',     desc: 'Discord + soporte' },
    { path: '/disclaimer', icon: '⚖', label: 'DISCLAIMER',    desc: 'Aviso legal y condiciones' },
];

// El mismo candado que pinta el menú lateral para las secciones de pago.
function bloqueado(path) {
    const item = NAV_ITEMS.find(i => i.path === path);
    return !!(item && item.minTier && !hasTier(item.minTier));
}

// ── ACADEMY: SIGUE DONDE LO DEJASTE ──────────────────────────────────────────
// Qué está completo lo dice el servidor (la misma regla que el certificado);
// por dónde seguir, academy_continuar.js. Sin datos no se pinta nada: una
// tarjeta con un progreso inventado es peor que ninguna.

function catalogoAcademy() {
    const modulos = {};
    for (const m of MODULES) modulos[m.id] = { title: m.title, lecciones: leccionesDe(m.id) };
    return { orden: PHASES.flatMap(p => p.modules), modulos };
}

async function loadAcademyContinuar(el) {
    if (!el) return;
    try {
        const [pRes, cRes] = await Promise.all([
            fetch('/api/v1/academy/progress',    { headers: authHeader() }),
            fetch('/api/v1/academy/certificado', { headers: authHeader() }),
        ]);
        const progreso = await pRes.json();
        const cert     = await cRes.json();
        if (!progreso || !progreso.ok || !cert || !cert.ok) return;
        const paso = siguientePaso(progreso, cert, catalogoAcademy());
        if (!paso) return;
        el.innerHTML = tarjetaAcademy(paso);
        const boton = el.querySelector('[data-ir]');
        if (boton) boton.addEventListener('click', () => window.__navigate(boton.getAttribute('data-ir')));
    } catch (_) { /* el Dashboard se usa igual sin la tarjeta */ }
}

function tarjetaAcademy(p) {
    const modulo = p.modulo ? 'Módulo ' + p.modulo.id + ' · ' + esc(p.modulo.title) : '';
    const leccion = p.leccion ? '«' + esc(p.leccion.title) + '»' : '';
    const irLeccion = p.leccion ? '/academy?leccion=' + encodeURIComponent(p.leccion.key) : '/academy';
    const completos = p.completos + ' de ' + p.modulosTotal + ' módulos completos';
    const barra = (hechas, total) => '<div style="height:4px;background:var(--color-border);border-radius:2px;margin-top:8px;overflow:hidden;max-width:420px;">'
        + '<div style="height:100%;width:' + (total ? Math.round(hechas / total * 100) : 0) + '%;background:var(--color-accent);"></div></div>';

    let etiqueta, linea, detalle, boton, destino;
    if (p.tipo === 'empezar') {
        etiqueta = 'ACADEMY';
        linea    = 'Formación en ' + p.modulosTotal + ' módulos, incluida en tu cuenta.';
        detalle  = 'Empieza por ' + leccion + '.';
        boton    = 'Empezar →';          destino = irLeccion;
    } else if (p.tipo === 'seguir') {
        etiqueta = 'ACADEMY · SIGUE DONDE LO DEJASTE';
        linea    = modulo + ' — ' + p.leidas + ' de ' + p.total + ' lecciones leídas' + barra(p.leidas, p.total);
        detalle  = 'Siguiente: ' + leccion + ' · ' + completos;
        boton    = 'Seguir →';           destino = irLeccion;
    } else if (p.tipo === 'quiz') {
        etiqueta = 'ACADEMY · TE FALTA EL QUIZ';
        linea    = 'Has leído todo el ' + modulo.replace('Módulo', 'módulo') + '.';
        detalle  = (p.quiz === 'sin hacer' ? 'Solo te queda su quiz para darlo por completo.' : 'Su quiz: ' + esc(p.quiz) + '.') + ' · ' + completos;
        boton    = 'Ir al quiz →';       destino = '/academy?modulo=' + p.modulo.id;
    } else if (p.tipo === 'nuevo') {
        etiqueta = 'ACADEMY · MÓDULO NUEVO';
        linea    = modulo + ' — ' + p.total + ' ' + (p.total === 1 ? 'lección' : 'lecciones');
        detalle  = 'Se ha añadido después de tu certificado. Empieza por ' + leccion + '.';
        boton    = 'Leer →';             destino = irLeccion;
    } else {
        etiqueta = 'ACADEMY · COMPLETADA';
        linea    = 'Has completado los ' + p.modulosTotal + ' módulos de Academy.';
        detalle  = 'Ya puedes pedir tu certificado.';
        boton    = 'Pedir certificado →'; destino = '/academy';
    }

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:12px 16px;margin-bottom:1.5rem;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">'
        + '<div style="font-size:22px;" aria-hidden="true">🎓</div>'
        + '<div style="flex:1;min-width:220px;">'
        + '<div style="color:var(--color-accent);font-size:11px;letter-spacing:0.08em;">' + etiqueta + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;margin-top:3px;">' + linea + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:6px;">' + detalle + '</div>'
        + '</div>'
        + '<button type="button" data-ir="' + esc(destino) + '" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;flex-shrink:0;">' + boton + '</button>'
        + '</div>';
}
