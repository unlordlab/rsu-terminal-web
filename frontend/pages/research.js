import { authHeader } from '/core/api.js';
import { tt } from '/components/tooltip.js';
import { errorMessage, esc, safeUrl, fmtFecha } from '/core/ui.js';

// Los 6 canvas de Chart.js de esta página, por id. Se destruyen desde
// cleanup(), que el router llama justo antes de tirar el contenedor
// (frontend/core/router.js, convención de la sesión 3).
//
// Ninguno se destruía: ni al navegar fuera, ni al buscar otro ticker dentro
// de la misma visita. Cada búsqueda dejaba atrás su gráfico anterior con sus
// listeners y su animación, y bastaba con mirar unos cuantos valores seguidos
// para ir acumulando. Market ya usa este mismo patrón desde la sesión 3;
// Research se quedó sin enganchar.
//
// Se destruye por ID y no guardando la instancia a propósito: renderResearch()
// reescribe el innerHTML entero, así que el <canvas> anterior desaparece del
// DOM y la referencia que hubiéramos guardado apuntaría a un elemento
// huérfano. Chart.getChart(id) resuelve siempre el gráfico realmente vivo.
const _RESEARCH_CHART_IDS = [
    'crypto-chart', 'sparkline-chart',
    'earnings-chart', 'income-statement-chart', 'insider-volume-chart',
];

function _destruirGraficos() {
    _destruirRsuCharts();
    _RESEARCH_CHART_IDS.forEach(id => {
        const c = window.Chart && window.Chart.getChart && window.Chart.getChart(id);
        if (c) { try { c.destroy(); } catch (_) {} }
    });
}

// Llamado por el router antes de destruir el contenedor de Research.
export function cleanup() {
    _destruirGraficos();
}

export async function render(container) {
    container.innerHTML = pageHeader();

    const input  = container.querySelector('#research-input');
    const btn    = container.querySelector('#research-btn');
    const result = container.querySelector('#research-result');

    async function doResearch() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;

        // Que la barra de direcciones diga qué estás mirando. Hasta ahora el
        // deep-link ?ticker= funcionaba al ENTRAR pero no al buscar: te
        // pasabas veinte minutos analizando un valor y no podías compartir el
        // enlace ni recargar sin perderlo. replaceState y no pushState a
        // propósito: cada búsqueda no es un paso de navegación, y llenar el
        // historial obligaría a dar 15 veces atrás para salir de Research.
        try {
            const url = new URL(window.location.href);
            if (url.searchParams.get('ticker') !== ticker) {
                url.searchParams.set('ticker', ticker);
                history.replaceState(history.state, '', url);
            }
        } catch (_) { /* si el navegador no deja, la búsqueda sigue igual */ }

        btn.textContent   = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando datos de ' + esc(ticker) + '...</div>';
        try {
            const res   = await fetch('/api/v1/research/' + ticker, {
                headers: authHeader()
            });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Sin datos');
            // Antes de reescribir el innerHTML: si no, los gráficos de la
            // búsqueda anterior quedan colgando aunque su <canvas> ya no exista.
            _destruirGraficos();
            result.innerHTML = renderResearch(data);
            renderSparkline(data);
            renderEarningsChart(data);
            renderIncomeStatementChart(data);
            renderInsiderVolumeChart(data);
            renderCryptoChart(data);
            renderRsuFlowChart(data);
            loadScoreEvolucion(data.ticker);
        } catch(e) {
            result.innerHTML = errorMessage(e.message);
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doResearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doResearch(); });

    // Auto-cargar ticker si viene en la URL
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        input.value = urlTicker.toUpperCase();
        setTimeout(() => doResearch(), 100);
    } else {
        input.focus();
        loadScoreTracking(container);
    }
}

// Vista vacía (antes de buscar un ticker): resumen de qué tan bien ha
// predicho el RSU Score hasta ahora, agregado por bucket -- ver
// TODO_RSU_TERMINAL.md 4.2. Se sobrescribe sin conflicto en cuanto el
// usuario busca un ticker real (mismo contenedor #research-result).
async function loadScoreTracking(container) {
    const result = container.querySelector('#research-result');
    if (!result) return;
    try {
        const res = await fetch('/api/v1/research/score-tracking/resumen', {
            headers: authHeader()
        });
        const data = await res.json();
        if (!data.ok) return;
        result.innerHTML = renderScoreTrackingSummary(data.resumen);
    } catch (e) { /* silencioso -- es contenido de la vista vacía, no un error de búsqueda */ }
}

function renderScoreTrackingSummary(resumen) {
    const rows = resumen.map(b => {
        const fmt = (v) => v == null ? '<span style="color:var(--color-muted);">—</span>'
            : '<span style="color:' + (v >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (v >= 0 ? '+' : '') + v.toFixed(2) + '%</span>';
        return '<div style="display:grid;grid-template-columns:1fr 70px 90px 90px 90px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;">'
            + '<div style="color:var(--color-text);">' + esc(b.bucket) + ' <span style="color:var(--color-muted);font-size:10px;">(' + esc(b.rango) + ')</span></div>'
            + '<div style="text-align:right;color:var(--color-muted);">' + esc(b.n) + '</div>'
            + '<div style="text-align:right;">' + fmt(b.avg_5d) + '</div>'
            + '<div style="text-align:right;">' + fmt(b.avg_10d) + '</div>'
            + '<div style="text-align:right;">' + fmt(b.avg_20d) + '</div>'
            + '<div style="text-align:right;">' + fmt(b.avg_60d) + '</div>'
            + '</div>';
    }).join('');
    const header = '<div style="display:grid;grid-template-columns:1fr 70px 90px 90px 90px 90px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>SCORE</div><div style="text-align:right;">N</div><div style="text-align:right;">+5D</div><div style="text-align:right;">+10D</div><div style="text-align:right;">+20D</div><div style="text-align:right;">+60D</div></div>';
    const total = resumen.reduce((s, b) => s + b.n, 0);
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">¿UN SCORE ALTO ACIERTA MÁS? · RETORNO MEDIO POR BUCKET</div>'
        + header + rows
        + (total === 0 ? '<div style="padding:1rem 14px;color:var(--color-muted);font-size:11px;">Sin historial todavía — se acumula con cada ticker investigado, resultados a partir de unas semanas.</div>' : '')
        + '</div>';
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RESEARCH ' + tt('rsu-score') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Análisis fundamental</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="research-input" type="text" placeholder="AAPL, NVDA, TSLA..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:14px;outline:none;">'
        + '<button id="research-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:13px;cursor:pointer;letter-spacing:0.05em;font-weight:500;">ANALIZAR</button>'
        + '</div>'
        + '<div id="research-result"></div>';
}

// ── FICHA CRIPTO ─────────────────────────────────────────────────────────────
// Nada de fundamentales de empresa aquí (no aplican) — en su lugar, perfil
// temático vía CoinGecko: categoría, descripción, suministro, ATH/ATL, enlaces.

function cryptoHeaderSection(data, chgColor, chgStr) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">'
        + '<div>'
        + '<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px;">'
        + '<span class="ticker-link" style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + esc(data.ticker) + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + esc(data.name) + '</span>'
        + (data.en_cartera   ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '')
        + (data.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '')
        + '<span style="background:#a855f722;color:#a855f7;border:1px solid #a855f755;border-radius:3px;padding:1px 8px;font-size:9px;letter-spacing:0.05em;">CRIPTO</span>'
        + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:28px;font-weight:500;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + data.mktcap_fmt + ' market cap</div>'
        + '<button onclick="window.__quickAddWatchlist(\'' + data.ticker + '\', this)" style="margin-top:8px;background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:5px 12px;font-size:11px;cursor:pointer;">＋ Watchlist</button>'
        + '</div>'
        + '</div>'
        + '<div style="display:flex;gap:2rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);font-size:11px;flex-wrap:wrap;">'
        + (data.week52_low  ? '<span style="color:var(--color-muted);">52w Low: <b style="color:var(--color-text);">$' + data.week52_low.toLocaleString('en-US') + '</b></span>' : '')
        + (data.week52_high ? '<span style="color:var(--color-muted);">52w High: <b style="color:var(--color-text);">$' + data.week52_high.toLocaleString('en-US') + '</b></span>' : '')
        + '</div>'
        + '</div>';
}

function cryptoChartSection(data) {
    const hasChart = data.crypto_chart && data.crypto_chart.length > 1;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">GRÁFICO · COINGECKO</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Diario · 1 año</div>'
        + '</div>'
        + '<div style="height:340px;padding:12px;">'
        + (hasChart
            ? '<canvas id="crypto-chart"></canvas>'
            : '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--color-muted);font-size:12px;">Sin histórico de precio disponible para este activo</div>')
        + '</div>'
        + '</div>';
}

function renderCryptoChart(data) {
    if (!data.crypto_chart || data.crypto_chart.length < 2) return;
    const up    = data.chg_pct >= 0;
    const color = up ? '#00ffad' : '#f23645';
    loadChartJs(() => {
        const ctx = document.getElementById('crypto-chart');
        if (!ctx) return;
        const points = data.crypto_chart;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: points.map(p => p.date.substring(5)),
                datasets: [{
                    data: points.map(p => p.price),
                    borderColor: color, backgroundColor: color + '18',
                    borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.25,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: c => ' $' + c.raw.toLocaleString('en-US', { maximumFractionDigits: 6 }) } },
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#555', font: { size: 9 }, callback: v => '$' + v.toLocaleString('en-US') }, grid: { color: 'rgba(255,255,255,0.04)' } },
                }
            }
        });
    });
}

function cryptoProfileSection(data) {
    const p = data.crypto_profile;
    if (!p || !p.ok) {
        return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-muted);font-size:12px;">No se encontró perfil temático para este activo en CoinGecko' + (p && p.error ? ' (' + p.error + ')' : '') + '.</div>'
            + '</div>';
    }

    const catBadges = (p.categories || []).map(c =>
        '<span style="background:#a855f722;color:#a855f7;border:1px solid #a855f755;border-radius:3px;padding:2px 9px;font-size:10px;margin-right:6px;margin-bottom:6px;display:inline-block;">' + c + '</span>'
    ).join('');

    const supplyBox = (label, value) => value == null ? '' :
        '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:6px;padding:8px 12px;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + label + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;font-weight:600;margin-top:2px;">' + Number(value).toLocaleString('en-US') + '</div>'
        + '</div>';

    const pctCirculating = (p.circulating_supply && p.max_supply)
        ? Math.round((p.circulating_supply / p.max_supply) * 100) : null;

    const athColor = (p.ath_change_pct != null && p.ath_change_pct >= 0) ? 'var(--color-accent)' : '#f23645';

    const links = p.links || {};
    const linkBtn = (label, url) => !url ? '' :
        '<a href="' + url + '" target="_blank" style="color:var(--color-secondary);font-size:11px;border:1px solid var(--color-border);border-radius:4px;padding:4px 10px;text-decoration:none;">' + label + ' ↗</a>';

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">PERFIL TEMÁTICO · COINGECKO</div>'
        + (catBadges ? '<div style="margin-bottom:1rem;">' + catBadges + '</div>' : '')

        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:1rem;">'
        + (p.market_cap_rank ? supplyBox('RANKING MKT CAP', '#' + p.market_cap_rank) : '')
        + supplyBox('SUMINISTRO CIRCULANTE', p.circulating_supply)
        + supplyBox('SUMINISTRO MÁXIMO', p.max_supply)
        + (pctCirculating != null ? supplyBox('% EN CIRCULACIÓN', pctCirculating + '%') : '')
        + '</div>'

        + (p.ath != null ? (
            '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:6px;padding:10px 12px;margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
            + '<div><span style="color:var(--color-muted);font-size:10px;">MÁXIMO HISTÓRICO (ATH)</span><br>'
            + '<span style="color:var(--color-text);font-size:15px;font-weight:600;">$' + Number(p.ath).toLocaleString('en-US') + '</span>'
            + (p.ath_date ? ' <span style="color:var(--color-muted);font-size:10px;">(' + p.ath_date + ')</span>' : '')
            + '</div>'
            + (p.ath_change_pct != null ? '<div style="color:' + athColor + ';font-size:13px;font-weight:600;">' + (p.ath_change_pct >= 0 ? '+' : '') + p.ath_change_pct.toFixed(1) + '% desde ATH</div>' : '')
            + '</div>'
        ) : '')

        + (links.homepage || links.whitepaper || links.github || links.subreddit || links.twitter ? (
            '<div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:0.75rem;border-top:1px solid var(--color-border);">'
            + linkBtn('Web oficial', links.homepage)
            + linkBtn('Whitepaper', links.whitepaper)
            + linkBtn('GitHub', links.github)
            + linkBtn('Reddit', links.subreddit)
            + linkBtn('Twitter/X', links.twitter)
            + '</div>'
        ) : '')
        + '</div>';
}

function renderCryptoResearch(data) {
    const chgColor = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr   = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';

    return cryptoHeaderSection(data, chgColor, chgStr)
        + descriptionSection(data)
        + cryptoChartSection(data)
        + cryptoProfileSection(data);
}

function renderResearch(data) {
    if (data.is_crypto) return renderCryptoResearch(data);

    const chgColor   = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr     = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';
    const score      = data.rsu_score;
    const scoreColor = score.color;

    return headerSection(data, chgColor, chgStr)
        + descriptionSection(data)
        + rsuScoreSection(score, scoreColor)
        + piotroskiSection(data)
        // Valoración, rentabilidad y crecimiento suben por encima del gráfico:
        // son lo que se mira antes de nada al abrir una ficha.
        + metricsSection(data)
        + chartSection(data)
        + rsuFlowSection(data)
        + technicalSection(data)
        + incomeStatementSection(data)
        + consensoSection(data)
        + analystChangesSection(data)
        + institutionalSection(data)
        + seasonalitySection(data)
        // Junto a Insider a propósito: las dos responden a la misma pregunta
        // —qué está haciendo el dinero grande con este valor— desde ángulos
        // distintos, y se leen mejor seguidas.
        + optionsFlowSection(data)
        + insiderSection(data)
        + earningsSection(data)
        + suggestionsSection(data)
        + newsSection(data);
}

// ── SECCIONES ─────────────────────────────────────────────────────────────────

// ── SECCIONES ─────────────────────────────────────────────────────────────────

function headerSection(data, chgColor, chgStr) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">'
        + '<div>'
        + '<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px;">'
        + '<span onclick="goToResearch(\'' + esc(data.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + esc(data.ticker) + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + esc(data.name) + '</span>'
        + (data.en_cartera   ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '')
        + (data.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '')
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-bottom:4px;">' + esc(data.sector) + ' · ' + esc(data.industry) + ' · ' + esc(data.country) + '</div>'
        + (data.website ? '<a href="' + safeUrl(data.website) + '" target="_blank" style="color:var(--color-secondary);font-size:11px;">' + esc(data.website) + '</a>' : '')
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:28px;font-weight:500;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + data.mktcap_fmt + ' market cap ' + tt('market-cap') + '</div>'
        + '<button onclick="window.__quickAddWatchlist(\'' + data.ticker + '\', this)" style="margin-top:8px;background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:5px 12px;font-size:11px;cursor:pointer;">＋ Watchlist</button>'
        + '</div>'
        + '</div>'
        + '<div style="display:flex;gap:2rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);font-size:11px;flex-wrap:wrap;">'
        + (data.week52_low  ? '<span style="color:var(--color-muted);">52w Low: <b style="color:var(--color-text);">$' + data.week52_low.toFixed(2) + '</b></span>' : '')
        + (data.week52_high ? '<span style="color:var(--color-muted);">52w High: <b style="color:var(--color-text);">$' + data.week52_high.toFixed(2) + '</b></span>' : '')
        + (data.beta        ? '<span style="color:var(--color-muted);">Beta: <b style="color:var(--color-text);">' + data.beta.toFixed(2) + '</b></span>' : '')
        + (data.dividend_yield ? '<span style="color:var(--color-muted);">Dividendo: <b style="color:var(--color-accent);">' + (data.dividend_yield * 100).toFixed(2) + '%</b></span>' : '')
        + '</div>'
        + '</div>';
}

function descriptionSection(data) {
    if (!data.description) return '';
    const short = data.description.substring(0, 300);
    const full  = data.description;
    const hasMore = full.length > 300;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">DESCRIPCIÓN</div>'
        + '<div id="desc-short" style="color:var(--color-muted);font-size:12px;line-height:1.7;">' + short + (hasMore ? '...' : '') + '</div>'
        + (hasMore
            ? '<div id="desc-full" style="color:var(--color-muted);font-size:12px;line-height:1.7;display:none;">' + full + '</div>'
              + '<button onclick="toggleDesc()" id="desc-btn" style="background:none;border:none;color:var(--color-secondary);font-size:11px;cursor:pointer;margin-top:6px;font-family:var(--font-mono);">▼ Ver más</button>'
            : '')
        + '</div>';
}

function rsuScoreSection(score, scoreColor) {
    // Sin score publicable (menos de 3 de las 5 categorías con datos) se
    // explica por qué en vez de enseñar un número. Pasa de verdad con los
    // ETF: SPY y QQQ salían con 100/100 "COMPRA FUERTE" sostenido por un
    // único indicador técnico, y GLD con un 0 "EVITAR" de la misma nada,
    // indistinguibles de un score construido con las 5. Ver sesión
    // 29/07/2026 y MIN_CATEGORIAS_RSU_SCORE en research_service.py.
    const sinScore = score.score == null;

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">RSU SCORE ' + tt('rsu-score') + '</span>'
        + (sinScore
            ? '<span style="color:var(--color-muted);font-size:12px;padding:2px 10px;border:1px solid var(--color-border);border-radius:4px;">No calculable</span>'
            : '<div style="display:flex;align-items:center;gap:10px;">'
              + '<span style="color:' + scoreColor + ';font-size:20px;font-weight:500;">' + esc(score.score) + '/100</span>'
              + '<span style="color:' + scoreColor + ';font-size:12px;padding:2px 10px;border:1px solid ' + scoreColor + '33;border-radius:4px;">' + esc(score.label) + '</span>'
              + '</div>')
        + '</div>'
        + (sinScore
            ? '<div style="color:#ffb800;font-size:11px;margin-bottom:8px;">' + esc(score.motivo || '') + '</div>'
            : '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin-bottom:8px;">'
              + '<div style="height:100%;width:' + score.score + '%;background:' + scoreColor + ';border-radius:4px;transition:width 0.8s;"></div>'
              + '</div>')
        // Con 3 o 4 categorías el score SÍ se publica, pero no es comparable
        // con uno medido sobre las 5 -- y hasta ahora se veían idénticos.
        + (!sinScore && score.n_categorias != null && score.n_categorias < 5
            ? '<div style="color:#ffb800;font-size:10px;margin-bottom:8px;">Calculado sobre '
              + esc(score.n_categorias) + ' de las 5 categorías: las demás no tienen datos para este activo, '
              + 'así que el score se reescala sobre lo medido y no es del todo comparable con el de un valor con las 5.</div>'
            : '')
        + '<div style="display:flex;gap:1rem;flex-wrap:wrap;">'
        + (score.breakdown || []).map(b => {
            const pct = b.max > 0 ? Math.round(b.pts / b.max * 100) : 0;
            return '<div style="font-size:10px;color:var(--color-muted);">'
                + b.label + ': <span style="color:' + (pct >= 75 ? 'var(--color-accent)' : pct >= 50 ? '#ffb800' : '#f23645') + ';">' + b.pts + '/' + b.max + '</span>'
                + ' <span style="color:var(--color-muted);">(' + b.val + ')</span>'
                + '</div>';
        }).join('')
        + '</div>'
        // Hueco para la evolución: se rellena aparte, tras su propia petición,
        // para que un problema del histórico no retrase ni rompa el score.
        + '<div id="rsu-score-evolucion"></div>'
        + '</div>';
}

// Evolución del RSU Score del ticker. El score se guarda desde que alguien
// consulta la ficha, así que empieza vacío para cada valor nuevo y se llena a
// razón de un punto por día consultado.
async function loadScoreEvolucion(ticker) {
    const el = document.getElementById('rsu-score-evolucion');
    if (!el) return;
    let h;
    try {
        // Mismo patrón que el resto del fichero: aquí no hay authHeader(),
        // la cabecera se construye a mano.
        const res = await fetch('/api/v1/research/score-tracking/' + encodeURIComponent(ticker),
                                { headers: authHeader() });
        h = await res.json();
    } catch (e) {
        // Silencioso de cara al usuario -- esto es contexto, no el dato
        // principal -- pero al log sí: la primera versión llamaba a una
        // función que no existe en este fichero y el catch se tragó el
        // ReferenceError, dejando el hueco vacío sin ninguna pista.
        console.warn('[Research] No se pudo cargar la evolución del score:', e);
        return;
    }
    if (!h) return;

    if (!h.ok) {
        const n = h.dias || 0;
        el.innerHTML = '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--color-border);'
            + 'color:var(--color-muted);font-size:9px;">'
            + 'Evolución del score: ' + n + ' de ' + (h.minimo || 5) + ' días registrados. '
            + 'Se guarda un punto cada día que consultas este valor.'
            + '</div>';
        return;
    }

    // Escala fija 0-100: el score vive en ese rango y dejar que la línea se
    // reescale sola haría parecer enorme un movimiento de tres puntos.
    const pts = h.serie.map((p, i) =>
        (i / (h.serie.length - 1) * 100).toFixed(2) + ',' + (30 - p.score / 100 * 28).toFixed(2)
    ).join(' ');
    const col = h.cambio > 0 ? 'var(--color-accent)' : h.cambio < 0 ? '#f23645' : 'var(--color-muted)';
    const signo = h.cambio > 0 ? '+' : '';

    el.innerHTML = '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;font-size:9px;color:var(--color-muted);margin-bottom:2px;">'
        + '<span>EVOLUCIÓN DEL SCORE · ' + h.n + ' días registrados</span>'
        + '<span style="color:' + col + ';">' + signo + h.cambio + ' desde el registro anterior'
        + ' <span style="color:var(--color-muted);">· entre ' + h.min + ' y ' + h.max + '</span></span>'
        + '</div>'
        + '<svg viewBox="0 0 100 32" preserveAspectRatio="none" style="width:100%;height:30px;display:block;">'
        + '<polyline points="' + pts + '" fill="none" stroke="' + col + '" stroke-width="0.9" vector-effect="non-scaling-stroke"/>'
        + '</svg>'
        + '</div>';
}

function piotroskiSection(data) {
    const p = data.piotroski;
    if (!p || !p.criteria || !p.criteria.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">PIOTROSKI F-SCORE ' + tt('piotroski-score') + '</span>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span style="color:' + p.color + ';font-size:20px;font-weight:500;">' + p.score + '/' + p.max + '</span>'
        + '<span style="color:' + p.color + ';font-size:12px;padding:2px 10px;border:1px solid ' + p.color + '33;border-radius:4px;">' + p.label + '</span>'
        + '</div></div>'
        + '<div style="color:var(--color-muted);font-size:9px;margin-bottom:10px;">Este score es uno de los 5 componentes que forman el RSU Score (20% del total).</div>'
        // Un 5/9 medido sobre 9 criterios y un 5/9 medido sobre 7 no son
        // comparables, y hasta ahora se veían idénticos. Pasa en todo el
        // sector financiero: bancos y aseguradoras presentan el balance sin
        // clasificar (sin activo/pasivo corriente) y sin margen bruto, así
        // que 2 de los 9 criterios no se pueden calcular -- Piotroski diseñó
        // el F-Score para empresas no financieras. Ver sesión 29/07/2026.
        + (p.evaluables != null && p.evaluables < p.max
            ? '<div style="color:#ffb800;font-size:10px;margin-bottom:10px;">Solo ' + esc(p.evaluables) + ' de los ' + esc(p.max)
              + ' criterios son evaluables con las cuentas publicadas de esta empresa — habitual en bancos y aseguradoras, '
              + 'que presentan el balance sin separar corriente de no corriente. El score se compara con eso en mente.</div>'
            : '')
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin-bottom:10px;">'
        + '<div style="height:100%;width:' + (p.score / p.max * 100) + '%;background:' + p.color + ';border-radius:4px;transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">'
        + p.criteria.map(c => {
            let icon, color;
            if (c.pass === true)       { icon = '✓'; color = 'var(--color-accent)'; }
            else if (c.pass === false) { icon = '✗'; color = '#f23645'; }
            else                       { icon = '–'; color = '#666'; }
            return '<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--color-muted);">'
                + '<span style="color:' + color + ';font-weight:600;">' + icon + '</span>' + c.label
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function institutionalSection(data) {
    const inst = data.institutional;
    if (!inst || (inst.pct_institutions == null && (!inst.holders || !inst.holders.length))) return '';
    const chg = inst.price_change_since_report_pct;
    const chgColor = chg == null ? 'var(--color-muted)' : (chg >= 0 ? 'var(--color-accent)' : '#f23645');
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<span style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">PROPIEDAD INSTITUCIONAL</span>'
        + (inst.pct_institutions != null
            ? '<span style="color:var(--color-text);font-size:16px;font-weight:500;">' + inst.pct_institutions + '% <span style="color:var(--color-muted);font-size:11px;font-weight:400;">en manos institucionales</span></span>'
            : '')
        + '</div>'
        + (inst.report_price != null
            ? '<div style="padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;color:var(--color-muted);">'
              + 'Datos del 13F al cierre del trimestre reportado (' + (inst.report_date || 'N/D') + '), cuando la acción cotizaba a <span style="color:var(--color-text);">$' + inst.report_price.toFixed(2) + '</span>.'
              + (chg != null ? ' Desde entonces, el precio ha ' + (chg >= 0 ? 'subido ' : 'bajado ') + '<span style="color:' + chgColor + ';">' + (chg >= 0 ? '+' : '') + chg + '%</span>.' : '')
              + tt('institutional-ref-price')
              + '</div>'
            : '')
        + (inst.holders && inst.holders.length
            ? '<div style="display:grid;grid-template-columns:1fr 100px 70px 90px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
              + '<div>INSTITUCIÓN</div><div>ACCIONES</div><div>% FLOAT</div><div>VALOR</div>'
              + '</div>'
              + inst.holders.map(h => '<div style="display:grid;grid-template-columns:1fr 100px 70px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                  + '<div style="color:var(--color-text);">' + h.holder + '</div>'
                  + '<div style="color:var(--color-muted);">' + h.shares.toLocaleString('en-US') + '</div>'
                  + '<div style="color:var(--color-muted);">' + (h.pct_out != null ? h.pct_out + '%' : 'N/A') + '</div>'
                  + '<div style="color:var(--color-muted);">' + h.value + '</div>'
                  + '</div>').join('')
            : '<div style="padding:10px 14px;color:var(--color-muted);font-size:11px;">Sin desglose de accionistas disponible.</div>')
        + '</div>';
}

function chartSection(data) {
    const tvSymbol = data.ticker;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">GRÁFICO · TRADINGVIEW</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Diario · 1 año</div>'
        + '</div>'
        + '<div style="height:400px;">'
        + '<iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tv_chart&symbol=' + tvSymbol
        + '&interval=D&hidesidetoolbar=1&hidetoptoolbar=0&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es"'
        + ' style="width:100%;height:100%;border:none;" allowtransparency="true" frameborder="0" scrolling="no"></iframe>'
        + '</div>'
        + '</div>';
}

// Colores de los cinco estados del oscilador. Se dejan literales, como el
// resto de gráficos de la terminal: la librería necesita colores reales, no
// variables CSS.
const _L3_COLOR = {
    entrada:    '#ffd700',   // amarillo: el cruce al alza desde zona baja
    salida:     '#c77dff',   // violeta: el cruce a la baja desde zona alta
    alta:       '#00ffad',
    baja:       '#f23645',
    debil_alta: '#4a9eff',
    debil_baja: '#9e9e9e',
};
const _L3_NOMBRE = {
    entrada:    'entrada — cruce al alza desde la zona baja',
    salida:     'salida — cruce a la baja desde la zona alta',
    alta:       'por encima de su línea',
    baja:       'por debajo de su línea',
    debil_alta: 'perdiendo fuerza',
    debil_baja: 'débil, sin caer más',
};

function rsuFlowSection(data) {
    const f = (data.technical_levels || {}).rsu_flow;
    if (!f || !f.ok) return '';
    const col = _L3_COLOR[f.estado_actual] || 'var(--color-muted)';
    const leyenda = ['entrada', 'salida', 'alta', 'baja', 'debil_alta', 'debil_baja']
        .map(k => '<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;">'
            + '<span style="width:9px;height:9px;background:' + _L3_COLOR[k] + ';border-radius:1px;display:inline-block;"></span>'
            + esc(_L3_NOMBRE[k]) + '</span>').join('');
    const vol = f.flujo_volumen == null ? '' :
        '<span style="color:var(--color-muted);font-size:11px;">Flujo con volumen ' + tt('rsu-flow-volumen')
        + ' <span style="color:var(--color-text);">' + f.flujo_volumen.toFixed(0) + '/100</span></span>';

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap;margin-bottom:0.75rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">INDICADOR RSU ' + tt('rsu-flow') + '</div>'
        + vol
        + '</div>'
        // Dos paneles pegados: el precio arriba y el oscilador debajo,
        // compartiendo eje de tiempo para poder leerlos a la misma altura.
        + '<div id="rsu-panel-precio" style="height:210px;"></div>'
        + '<div id="rsu-panel-osc" style="height:150px;"></div>'
        + '<div style="color:' + col + ';font-size:11px;margin-top:0.5rem;">Hoy: ' + esc(_L3_NOMBRE[f.estado_actual] || '—') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:0.5rem;line-height:1.7;">' + leyenda + '</div>'
        + '</div>';
}

let _rsuCharts = [];

function _destruirRsuCharts() {
    _rsuCharts.forEach(c => { try { c.remove(); } catch (_) {} });
    _rsuCharts = [];
}

function loadLightweightCharts(cb) {
    if (window.LightweightCharts) { cb(); return; }
    const s = document.createElement('script');
    // Servida por la propia terminal, no por un CDN: es la librería
    // open-source de TradingView y no cambia, así que no hace falta
    // depender de que un tercero esté disponible.
    s.src = '/assets/lightweight-charts-4.2.3.js';
    s.onload = cb;
    document.head.appendChild(s);
}

function renderRsuFlowChart(data) {
    const f = (data.technical_levels || {}).rsu_flow;
    if (!f || !f.ok) return;
    loadLightweightCharts(() => {
        const elP = document.getElementById('rsu-panel-precio');
        const elO = document.getElementById('rsu-panel-osc');
        if (!elP || !elO || !window.LightweightCharts) return;
        _destruirRsuCharts();

        const base = {
            layout: { background: { color: 'transparent' }, textColor: '#666', fontSize: 9 },
            grid: { vertLines: { color: 'rgba(255,255,255,0.03)' }, horzLines: { color: 'rgba(255,255,255,0.03)' } },
            rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)' },
            timeScale: { borderColor: 'rgba(255,255,255,0.08)' },
            crosshair: { mode: 0 },   // libre, para poder cruzar los dos paneles a ojo
        };

        const chartP = LightweightCharts.createChart(elP, {
            ...base, height: elP.clientHeight, width: elP.clientWidth,
            timeScale: { ...base.timeScale, visible: false },
        });
        const chartO = LightweightCharts.createChart(elO, {
            ...base, height: elO.clientHeight, width: elO.clientWidth,
        });
        _rsuCharts = [chartP, chartO];

        chartP.addCandlestickSeries({
            upColor: '#00ffad', downColor: '#f23645',
            borderUpColor: '#00ffad', borderDownColor: '#f23645',
            wickUpColor: '#00ffad', wickDownColor: '#f23645',
        }).setData(f.velas);

        // ── Las dos BANDAS del original ────────────────────────────────────
        //
        // Antes se pintaban dos líneas de puntos, en 25 y en 80, y eso mezclaba
        // dos cosas distintas: 25 y 75 son los umbrales que la FÓRMULA exige
        // para dar entrada o salida (la línea lenta por debajo de 25 / por
        // encima de 75), mientras que lo que el indicador original DIBUJA son
        // dos franjas rellenas — amarilla del 10 al 20 y magenta del 80 al 90.
        // No coincidían, así que el panel se leía distinto al de TradingView
        // aunque los números fueran los mismos.
        //
        // Se dibujan con histogramas de base fija (base 10 y valor 20) porque
        // la librería no tiene relleno entre dos niveles; el resultado es una
        // franja continua. Van ANTES que las barras para quedar por detrás.
        const banda = (desde, hasta, color) => {
            const s = chartO.addHistogramSeries({ base: desde, color, priceLineVisible: false, lastValueVisible: false });
            s.setData(f.osc.map(p => ({ time: p.time, value: hasta })));
            return s;
        };
        banda(10, 20, 'rgba(157,157,0,0.55)');    // zona baja  — la "amarilla"
        banda(80, 90, 'rgba(157,0,157,0.45)');    // zona alta

        // Entrada y salida como barra de altura completa (0→100), igual que el
        // original: así se ven de un vistazo en todo el histórico sin tener que
        // buscar una barra suelta de color entre cientos.
        const vertical = (estado, color) => {
            const puntos = f.osc.filter(p => p.estado === estado);
            if (!puntos.length) return;
            const s = chartO.addHistogramSeries({ base: 0, color, priceLineVisible: false, lastValueVisible: false });
            s.setData(puntos.map(p => ({ time: p.time, value: 100 })));
        };
        vertical('entrada', 'rgba(255,215,0,0.45)');
        vertical('salida',  'rgba(199,125,255,0.40)');

        // El oscilador se dibuja como VELAS de sí mismo, no como histograma:
        // cada barra va del valor de AYER al de HOY, así que encadena con la
        // anterior. Es lo que da la sensación de continuidad del original —
        // con un histograma todas las barras nacen del 0 y el panel se lee
        // como una sucesión de columnas sueltas en vez de como un recorrido.
        // Reportado por el usuario el 14/08/2026 comparando las dos capturas.
        //
        // No se dibujan mechas: `open` y `close` son los dos únicos valores
        // que se conocen de cada sesión (el oscilador da un número por día, no
        // un rango intradía), así que inventar un máximo y un mínimo sería
        // dibujar un dato que no existe.
        const barras = chartO.addCandlestickSeries({ priceLineVisible: false });
        barras.setData(f.osc.map((p, i) => {
            const previo = i > 0 ? f.osc[i - 1].value : p.value;
            const color  = _L3_COLOR[p.estado] || '#666';
            return {
                time: p.time,
                open: previo, close: p.value,
                high: Math.max(previo, p.value), low: Math.min(previo, p.value),
                color, borderColor: color, wickColor: color,
            };
        }));
        chartO.addLineSeries({ color: 'rgba(255,255,255,0.45)', lineWidth: 1, priceLineVisible: false })
              .setData(f.linea);

        // Línea media, gris oscuro, como en el original.
        barras.createPriceLine({ price: 50, color: 'rgba(255,255,255,0.18)', lineWidth: 1, lineStyle: 0, title: '' });

        // Sincronía en los dos sentidos. El rebote infinito se corta
        // comparando: si el destino ya está donde se le pide, no se le toca,
        // así que la cadena se agota sola en un salto.
        //
        // La alternativa evidente —un cerrojo -de "estoy sincronizando"— tiene
        // un modo de fallo desagradable: si algo lanza mientras está cerrado,
        // se queda cerrado para siempre y los dos paneles dejan de seguirse
        // sin que nada lo indique. Comparar no puede quedarse "a medias".
        const MISMO = 0.01;
        const enlazar = (origen, destino) => {
            origen.timeScale().subscribeVisibleLogicalRangeChange(r => {
                if (!r) return;
                const actual = destino.timeScale().getVisibleLogicalRange();
                if (actual && Math.abs(actual.from - r.from) < MISMO
                           && Math.abs(actual.to - r.to) < MISMO) return;
                destino.timeScale().setVisibleLogicalRange(r);
            });
        };
        enlazar(chartP, chartO);
        enlazar(chartO, chartP);
        chartP.timeScale().fitContent();
        chartO.timeScale().fitContent();

        const alRedimensionar = () => {
            chartP.applyOptions({ width: elP.clientWidth });
            chartO.applyOptions({ width: elO.clientWidth });
        };
        window.addEventListener('resize', alRedimensionar);
        _rsuCharts.push({ remove: () => window.removeEventListener('resize', alRedimensionar) });
    });
}

function metricsSection(data) {
    const m = data.metrics;
    const p = data.profitability;
    const sc = (data.sector_comparison && data.sector_comparison.ok) ? data.sector_comparison.items : {};
    const sectorName = data.sector || 'el sector';
    const scMeta = data.sector_comparison || {};

    // Construye el objeto de comparación para una métrica, con tooltip legible.
    // Si no hay benchmark para esa métrica (ej. Current Ratio, FCF), devuelve undefined
    // y metricCard se comporta exactamente como antes (sin color condicional).
    function sec(key, fmt) {
        const item = sc[key];
        if (!item || item.diff_pct == null) return undefined;
        const avgStr = fmt(item.sector_avg);
        return {
            favorable: item.favorable,
            diff_pct:  item.diff_pct,
            tooltip:   'Mediana de ' + sectorName + ': ' + avgStr + (item.favorable ? ' · Mejor que el sector' : ' · Peor que el sector'),
        };
    }

    const pctFmt = v => v ? (v*100).toFixed(1) + '%' : 'N/A';
    const xFmt   = v => v ? v.toFixed(1) + 'x' : 'N/A';

    return '<div class="rsu-grid-cards" style="gap:1rem;margin-bottom:1rem;">'
        + metricCard('VALORACIÓN ' + tt('sector-valuation'), [
            ['P/E Trailing ' + tt('pe-ratio'),  m.trailing_pe,    v => v ? v.toFixed(1) + 'x' : 'N/A', sec('trailing_pe', xFmt)],
            ['P/E Forward',   m.forward_pe,     v => v ? v.toFixed(1) + 'x' : 'N/A', sec('forward_pe', xFmt)],
            ['P/S',           m.price_to_sales, v => v ? v.toFixed(1) + 'x' : 'N/A', sec('price_to_sales', xFmt)],
            ['EV/EBITDA',     m.ev_ebitda,      v => v ? v.toFixed(1) + 'x' : 'N/A', sec('ev_ebitda', xFmt)],
            ['PEG',           m.peg_ratio,      v => v ? v.toFixed(2)        : 'N/A', sec('peg_ratio', v => v.toFixed(2))],
            ['P/B',           m.price_to_book,  v => v ? v.toFixed(2) + 'x' : 'N/A', sec('price_to_book', xFmt)],
            ['FCF Yield' + tt('fcf-yield'), p.fcf_yield, v => v != null ? v.toFixed(2) + '%' : 'N/A'],
        ])
        + metricCard('RENTABILIDAD ' + tt('sector-profitability'), [
            ['ROE',           p.roe,            pctFmt, sec('roe', pctFmt)],
            ['ROA',           p.roa,            pctFmt, sec('roa', pctFmt)],
            ['Margen Neto',   p.net_margin,     pctFmt, sec('net_margin', pctFmt)],
            ['Margen Op.',    p.op_margin,      pctFmt, sec('op_margin', pctFmt)],
            ['Margen Bruto',  p.gross_margin,   pctFmt, sec('gross_margin', pctFmt)],
            ['D/E Ratio',     p.debt_to_equity, v => v ? v.toFixed(0) + '%'       : 'N/A', sec('debt_to_equity', v => v.toFixed(0) + '%')],
        ])
        + metricCard('CRECIMIENTO ' + tt('sector-growth'), [
            ['Revenue Growth',  p.revenue_growth,  pctFmt, sec('revenue_growth', pctFmt)],
            ['Earnings Growth', p.earnings_growth, pctFmt, sec('earnings_growth', pctFmt)],
            ['Current Ratio',   p.current_ratio,   v => v ? v.toFixed(2) + 'x'       : 'N/A'],
            ['Free Cash Flow',  p.free_cashflow,   v => v ? _fmtVal(v)                : 'N/A'],
            ['Div. Yield',      data.dividend_yield, v => v ? (v*100).toFixed(2) + '%' : 'N/A'],
            ['Payout Ratio' + tt('payout-ratio'), p.payout_ratio, v => v != null ? payoutFmt(v) : 'N/A'],
            ['N. Analistas' + tt('n-analysts'), data.n_analysts, v => v ? v + ' analistas' + (data.latest_rating_date ? ' (últ. ' + data.latest_rating_date + ')' : '') : 'N/A'],
        ])
        + '</div>'
        + sectorSourceNote(scMeta, sectorName);
}

// De dónde salen los "vs sector" que colorean cada métrica de arriba. Mismo
// criterio de transparencia que el método del Breadth en Algoritmo o el
// periodo evaluado del backtest de BTC Stratum: cuando hay dos fuentes de
// distinta calidad, se dice cuál se está usando. Sin esta línea, unas
// medianas reales calculadas sobre las 503 empresas del S&P 500 y unos
// valores de referencia escritos a mano se veían exactamente igual -- y así
// pasaron semanas comparando contra los estáticos sin que nadie lo notara
// (el job semanal escribía en un Gist distinto del que leía el backend,
// 29/07/2026).
function sectorSourceNote(meta, sectorName) {
    if (!meta.fuente) return '';
    const base = 'font-size:10px;color:var(--color-muted);margin:-0.5rem 0 1rem;';
    if (meta.fuente === 'real') {
        const n     = meta.n_tickers ? esc(meta.n_tickers) + ' empresas del sector' : 'el sector';
        const fecha = meta.generated_at ? esc(String(meta.generated_at).slice(0, 10)) : null;
        const edad  = meta.edad_dias === 0 ? 'hoy'
                     : meta.edad_dias === 1 ? 'ayer'
                     : meta.edad_dias != null ? 'hace ' + esc(meta.edad_dias) + ' días' : null;
        return '<div style="' + base + '">Comparado con medianas <span style="color:var(--color-accent);">reales</span> de '
            + esc(sectorName) + ', calculadas sobre ' + n
            + (fecha ? ' · actualizadas ' + (edad || '') + ' (' + fecha + ')' : '')
            + '</div>';
    }
    return '<div style="' + base + '">Comparado con valores de referencia <span style="color:#ffb800;">estáticos</span> de '
        + esc(sectorName) + ' — aproximados y sin fecha. Las medianas reales del sector no están disponibles '
        + 'ahora mismo (el cálculo semanal no ha llegado a publicarse o está caducado).</div>';
}

function payoutFmt(v) {
    const color = v > 100 ? '#f23645' : v > 80 ? '#ffb800' : 'inherit';
    return '<span style="color:' + color + ';">' + v.toFixed(0) + '%</span>';
}

function consensoSection(data) {
    if (!data.recommendations || !data.recommendations.total) return '';
    const r     = data.recommendations;
    const total = r.total;
    const bars  = [
        ['Strong Buy',  r.strong_buy,  '#00ffad'],
        ['Buy',         r.buy,         '#90ee90'],
        ['Hold',        r.hold,        '#ffb800'],
        ['Sell',        r.sell,        '#ff8c00'],
        ['Strong Sell', r.strong_sell, '#f23645'],
    ];
    const buyPct = total > 0 ? Math.round((r.strong_buy + r.buy) / total * 100) : 0;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">CONSENSO ANALISTAS</div>'
        + (data.target_data.mean ? '<div style="font-size:12px;color:var(--color-muted);">Objetivo: <span style="color:var(--color-text);">$' + data.target_data.mean.toFixed(2) + '</span> · <span style="color:' + (data.target_data.upside >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.target_data.upside >= 0 ? '+' : '') + data.target_data.upside.toFixed(1) + '%</span></div>' : '')
        + '</div>'
        + '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">'
        + bars.map(([label, count, color]) => {
            const pct = total > 0 ? Math.round(count / total * 100) : 0;
            return '<div style="flex:1;min-width:70px;text-align:center;">'
                + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + count + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + label + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:4px;margin-top:4px;">'
                + '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + consensusTrendBlock(data.recommendations_trend)
        + '</div>';
}

function consensusTrendBlock(trend) {
    if (!trend || trend.length < 2) return '';
    // El histórico de yfinance viene ordenado 0m, -1m, -2m, -3m (más reciente primero).
    // Lo invertimos para mostrarlo cronológicamente: izquierda = más antiguo, derecha = actual.
    const chrono = [...trend].reverse();
    const current = chrono[chrono.length - 1].buy_pct;
    const oldest   = chrono[0].buy_pct;
    const deltaPts = Math.round((current - oldest) * 10) / 10;
    const deltaColor = deltaPts > 0 ? 'var(--color-accent)' : deltaPts < 0 ? '#f23645' : 'var(--color-muted)';
    const deltaIcon  = deltaPts > 0 ? '▲' : deltaPts < 0 ? '▼' : '—';
    const maxPct = Math.max(...chrono.map(c => c.buy_pct), 1);

    return '<div style="padding-top:0.75rem;border-top:1px solid var(--color-border);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">TENDENCIA % ALCISTA (' + chrono.length + ' MESES)</span>'
        + '<span style="color:' + deltaColor + ';font-size:11px;">' + deltaIcon + ' ' + (deltaPts > 0 ? '+' : '') + deltaPts + ' pts vs hace ' + (chrono.length - 1) + ' meses</span>'
        + '</div>'
        + '<div style="display:flex;gap:6px;align-items:flex-end;height:50px;">'
        + chrono.map((c, i) => {
            const h = Math.max(Math.round(c.buy_pct / maxPct * 42), 3);
            const isLast = i === chrono.length - 1;
            const barColor = isLast ? 'var(--color-accent)' : 'var(--color-secondary)';
            return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:50px;">'
                + '<div style="font-size:9px;color:var(--color-muted);margin-bottom:2px;">' + c.buy_pct + '%</div>'
                + '<div style="width:100%;max-width:28px;background:' + barColor + (isLast ? '' : '88') + ';height:' + h + 'px;border-radius:2px;"></div>'
                + '<div style="font-size:8px;color:var(--color-muted);margin-top:3px;">' + c.period_label + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function analystChangesSection(data) {
    const rh = data.ratings_history || {};
    const changes = rh.history || [];
    if (!changes.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">CAMBIOS DE RATING ANALISTAS ' + tt('analyst-ratings-history') + '</div>'
        + '<div style="display:grid;grid-template-columns:80px 1fr 130px 1fr 90px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>FIRMA</div><div>ACCIÓN</div><div>CAMBIO DE GRADO</div><div style="text-align:right;">P. OBJETIVO</div>'
        + '</div>'
        + changes.map(c => {
            const arrow = (c.from_grade !== '—' && c.to_grade !== '—' && c.from_grade !== c.to_grade)
                ? c.from_grade + ' → ' + c.to_grade
                : c.to_grade;
            const ptStr = c.cur_price_target
                ? c.prior_price_target && c.prior_price_target !== c.cur_price_target
                    ? '<span style="color:var(--color-muted);text-decoration:line-through;margin-right:4px;">' + c.prior_price_target + '</span>'
                      + '<span style="color:var(--color-text);">' + c.cur_price_target + '</span>'
                    : '<span style="color:var(--color-text);">' + c.cur_price_target + '</span>'
                : '<span style="color:var(--color-muted);">—</span>';
            return '<div style="display:grid;grid-template-columns:80px 1fr 130px 1fr 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<div style="color:var(--color-muted);">' + esc(fmtFecha(c.date)) + '</div>'
                + '<div style="color:var(--color-text);">' + c.firm + '</div>'
                + '<div style="background:' + c.action_color + '22;color:' + c.action_color + ';border:1px solid ' + c.action_color + '44;border-radius:3px;padding:2px 8px;font-size:10px;text-align:center;">' + c.action + '</div>'
                + '<div style="color:var(--color-muted);">' + arrow + '</div>'
                + '<div style="text-align:right;">' + ptStr + '</div>'
                + '</div>';
        }).join('')
        + '</div>';
}

function earningsSection(data) {
    if (!data.quarterly_earnings || !data.quarterly_earnings.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">EPS TRIMESTRAL · HISTÓRICO</div>'
        + '<div style="position:relative;height:140px;"><canvas id="earnings-chart"></canvas></div>'
        + '</div>';
}

function incomeStatementSection(data) {
    const inc = data.income_statement;
    if (!inc || !inc.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">CUENTA DE RESULTADOS · TRIMESTRAL' + tt('income-statement') + '</div>'
        + '<div style="position:relative;height:280px;"><canvas id="income-statement-chart"></canvas></div>'
        + '</div>';
}

function suggestionsSection(data) {
    if (!data.suggestions || !data.suggestions.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ANÁLISIS RSU</div>'
        + data.suggestions.map(s => '<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;color:var(--color-text);line-height:1.5;">' + s + '</div>').join('')
        + '</div>';
}

function newsSection(data) {
    if (!data.news || !data.news.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">NOTICIAS RECIENTES</div>'
        + data.news.map(n => '<div style="padding:8px 0;border-bottom:1px solid var(--color-border);">'
            + '<a href="' + safeUrl(n.url) + '" target="_blank" style="color:var(--color-text);font-size:12px;line-height:1.4;display:block;">' + esc(n.headline) + '</a>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:3px;">' + esc(n.source) + (n.date ? ' · ' + esc(fmtFecha(n.date)) : '') + '</div>'
            + '</div>').join('')
        + '</div>';
}

function technicalSection(data) {
    const t = data.technical_levels;
    const s = data.short_interest;
    const ne = data.next_earnings;
    if (!t || Object.keys(t).length === 0) return '';

    function vsColor(val) {
        if (val == null) return 'var(--color-muted)';
        return val >= 0 ? 'var(--color-accent)' : '#f23645';
    }
    function vsStr(val) {
        if (val == null) return 'N/A';
        return (val >= 0 ? '+' : '') + val + '%';
    }

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">NIVELES TÉCNICOS · CORTO INTERÉS · PRÓXIMO EARNINGS</div>'

        // Banner de Tendencia + Fase de mercado + Fuerza Relativa
        + (t.trend ? trendPhaseBanner(t, data.relative_strength) : '')

        + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;">'

        // Medias móviles simples
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">SMA (CLÁSICAS)</div>'
        + techRow('SMA 20',  t.sma20,  t.vs_sma20)
        + techRow('SMA 50',  t.sma50,  t.vs_sma50)
        + techRow('SMA 200', t.sma200, t.vs_sma200)
        + '</div>'

        // EMAs con pendiente
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">EMAs · PENDIENTE' + tt('ema-slope') + '</div>'
        + (t.emas ? emaRow('EMA 10',  t.emas.ema10)
                  + emaRow('EMA 20',  t.emas.ema20)
                  + emaRow('EMA 50',  t.emas.ema50)
                  + emaRow('EMA 200', t.emas.ema200)
           : '<div style="color:var(--color-muted);font-size:11px;">Sin datos</div>')
        + '</div>'

        // 52 semanas
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">RANGO 52 SEMANAS</div>'
        + techRow('Máx 52w', null, t.vs_52h)
        + techRow('Mín 52w', null, t.vs_52l)
        + (t.above_sma50 != null ? '<div style="font-size:11px;margin-top:8px;color:' + (t.above_sma50 ? 'var(--color-accent)' : '#f23645') + ';">' + (t.above_sma50 ? '✓ Sobre SMA50' : '✗ Bajo SMA50') + '</div>' : '')
        + (t.above_sma200 != null ? '<div style="font-size:11px;color:' + (t.above_sma200 ? 'var(--color-accent)' : '#f23645') + ';">' + (t.above_sma200 ? '✓ Sobre SMA200' : '✗ Bajo SMA200') + '</div>' : '')
        + '</div>'

        // Short interest + next earnings
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">SHORT INTEREST' + tt('short-interest-pct') + '</div>'
        + (s && s.short_pct != null
            ? '<div style="font-size:20px;color:' + (s.short_pct > 20 ? '#f23645' : s.short_pct > 10 ? '#ffb800' : 'var(--color-text)') + ';font-weight:500;">' + s.short_pct + '%</div>'
              + '<div style="color:var(--color-muted);font-size:10px;">del float · ' + (s.date || '') + '</div>'
            : '<div style="color:var(--color-muted);font-size:11px;">Sin datos</div>')
        + (s && s.short_ratio != null
            ? '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:11px;">'
              + '<span style="color:var(--color-muted);">Days to Cover' + tt('days-to-cover') + '</span>'
              + '<span style="color:' + (s.short_ratio > 10 ? '#f23645' : s.short_ratio > 5 ? '#ffb800' : 'var(--color-text)') + ';">' + s.short_ratio + 'd</span>'
              + '</div>'
            : '')
        + (s && s.squeeze_score != null ? squeezeGauge(s) : '')
        + (ne && ne.date
            ? '<div style="margin-top:12px;"><div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;letter-spacing:0.05em;">PRÓXIMO EARNINGS</div>'
              + '<div style="color:#ffb800;font-size:14px;font-weight:500;">📅 ' + esc(fmtFecha(ne.date)) + '</div>'
              + (ne.eps_est != null ? '<div style="color:var(--color-muted);font-size:11px;">EPS Est: $' + ne.eps_est.toFixed(2) + '</div>' : '')
              + (ne.hour ? '<div style="color:var(--color-muted);font-size:10px;">' + (ne.hour.toLowerCase().includes('bmo') ? 'BMO 🌅' : 'AMC 🌙') + '</div>' : '')
              + '</div>'
            : '')
        + '</div>'
        + '</div>'
        + '</div>';
}

function trendPhaseBanner(t, rs) {
    const trendColors = { ALCISTA: '#00ffad', BAJISTA: '#f23645', RANGO: '#ffb800' };
    const trendIcons  = { ALCISTA: '▲', BAJISTA: '▼', RANGO: '↔' };
    const tColor = trendColors[t.trend] || 'var(--color-muted)';
    const tIcon  = trendIcons[t.trend] || '';
    const phaseColors = { 1: '#00d9ff', 2: '#00ffad', 3: '#ffb800', 4: '#f23645' };
    const pColor = phaseColors[t.market_phase] || 'var(--color-muted)';

    return '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">'
        + '<div style="background:' + tColor + '11;border:1px solid ' + tColor + '44;border-radius:var(--radius);padding:8px 14px;flex:1;min-width:140px;">'
        + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:2px;">TENDENCIA' + tt('asset-trend') + '</div>'
        + '<div style="color:' + tColor + ';font-size:14px;font-weight:600;letter-spacing:0.05em;">' + tIcon + ' ' + t.trend + '</div>'
        + '</div>'
        + '<div style="background:' + pColor + '11;border:1px solid ' + pColor + '44;border-radius:var(--radius);padding:8px 14px;flex:1;min-width:180px;">'
        + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:2px;">FASE DE MERCADO (DIARIA)' + tt('market-phase') + '</div>'
        + '<div style="color:' + pColor + ';font-size:14px;font-weight:600;letter-spacing:0.05em;">' + (t.phase_label || ('Fase ' + t.market_phase)) + '</div>'
        + (t.phase_confirmed === false ? '<div style="color:var(--color-muted);font-size:9px;margin-top:2px;">⚠ cambio reciente, sin confirmar aún</div>' : '')
        + '</div>'
        + (t.phase_weekly_label
            ? '<div style="background:' + (phaseColors[t.phase_weekly] || 'var(--color-muted)') + '11;border:1px solid ' + (phaseColors[t.phase_weekly] || 'var(--color-muted)') + '44;border-radius:var(--radius);padding:8px 14px;flex:1;min-width:180px;">'
              + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:2px;">FASE SEMANAL (CONFIRMACIÓN)' + tt('market-phase') + '</div>'
              + '<div style="color:' + (phaseColors[t.phase_weekly] || 'var(--color-muted)') + ';font-size:14px;font-weight:600;letter-spacing:0.05em;">' + t.phase_weekly_label + '</div>'
              + '</div>'
            : '')
        + (rs && rs.rs_vs_spy != null
            ? '<div style="background:' + rs.rs_vs_spy_color + '11;border:1px solid ' + rs.rs_vs_spy_color + '44;border-radius:var(--radius);padding:8px 14px;flex:1;min-width:160px;">'
              + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:2px;">FUERZA VS SPY (S&P500)' + tt('relative-strength') + '</div>'
              + '<div style="color:' + rs.rs_vs_spy_color + ';font-size:14px;font-weight:600;letter-spacing:0.05em;">' + rs.rs_vs_spy_label + ' (' + (rs.rs_vs_spy >= 0 ? '+' : '') + rs.rs_vs_spy + 'pp)</div>'
              + '</div>'
            : '')
        + (rs && rs.rs_vs_sector != null
            ? '<div style="background:' + rs.rs_vs_sector_color + '11;border:1px solid ' + rs.rs_vs_sector_color + '44;border-radius:var(--radius);padding:8px 14px;flex:1;min-width:160px;">'
              + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.08em;margin-bottom:2px;">FUERZA VS ' + (rs.is_industry_level ? 'INDUSTRIA' : 'SECTOR') + ' (' + (rs.sector_etf || '—') + ')</div>'
              + '<div style="color:' + rs.rs_vs_sector_color + ';font-size:14px;font-weight:600;letter-spacing:0.05em;">' + rs.rs_vs_sector_label + ' (' + (rs.rs_vs_sector >= 0 ? '+' : '') + rs.rs_vs_sector + 'pp)</div>'
              + (rs.benchmark_label ? '<div style="color:var(--color-muted);font-size:9px;margin-top:2px;">' + rs.benchmark_label + '</div>' : '')
              + '</div>'
            : '')
        + '</div>';
}

function emaRow(label, ema) {
    if (!ema || ema.value == null) {
        return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
            + '<span style="color:var(--color-muted);">' + label + '</span>'
            + '<span style="color:var(--color-muted);">N/A</span>'
            + '</div>';
    }
    const slopeIcons  = { alcista: '↗', bajista: '↘', plana: '→' };
    const slopeColors = { alcista: '#00ffad', bajista: '#f23645', plana: 'var(--color-muted)' };
    const sIcon  = slopeIcons[ema.slope] || '';
    const sColor = slopeColors[ema.slope] || 'var(--color-muted)';
    const vp     = ema.vs_price;
    const vpColor = vp == null ? 'var(--color-muted)' : vp >= 0 ? 'var(--color-accent)' : '#f23645';
    const vpStr   = vp == null ? 'N/A' : (vp >= 0 ? '+' : '') + vp + '%';
    return '<div style="padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<div style="display:flex;justify-content:space-between;">'
        + '<span style="color:var(--color-muted);">' + label + ' $' + ema.value + '</span>'
        + '<span style="color:' + vpColor + ';">' + vpStr + ' vs precio</span>'
        + '</div>'
        + '<div style="text-align:right;font-size:9px;color:' + sColor + ';margin-top:1px;">'
        + sIcon + ' EMA ' + (ema.slope_pct != null ? (ema.slope_pct >= 0 ? '+' : '') + ema.slope_pct + '%' : 'N/A') + ' pendiente'
        + '</div>'
        + '</div>';
}

function squeezeGauge(s) {
    const score = s.squeeze_score;
    const label = s.squeeze_label;
    const color = score >= 75 ? '#f23645' : score >= 50 ? '#ffb800' : score >= 25 ? '#00d9ff' : 'var(--color-muted)';
    const pct   = Math.min(score, 100);
    return '<div style="margin-top:10px;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">SQUEEZE GAUGE' + tt('squeeze-gauge') + '</span>'
        + '<span style="color:' + color + ';font-size:10px;font-weight:600;letter-spacing:0.05em;">' + label + '</span>'
        + '</div>'
        + '<div style="position:relative;height:6px;background:var(--color-border);border-radius:3px;overflow:hidden;">'
        + '<div style="position:absolute;left:0;top:0;height:100%;width:' + pct + '%;background:' + color + ';border-radius:3px;transition:width 0.4s;"></div>'
        + '</div>'
        + '<div style="text-align:right;color:' + color + ';font-size:10px;margin-top:2px;">' + score + '/100</div>'
        + '</div>';
}

function techRow(label, price, vs) {
    const color = vs == null ? 'var(--color-muted)' : vs >= 0 ? 'var(--color-accent)' : '#f23645';
    const vsStr = vs == null ? 'N/A' : (vs >= 0 ? '+' : '') + vs + '%';
    return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:var(--color-muted);">' + label + (price ? ' $' + price : '') + '</span>'
        + '<span style="color:' + color + ';">' + vsStr + '</span>'
        + '</div>';
}

function seasonalitySection(data) {
    const season = data.seasonality;
    if (!season || !season.length) return '';
    const valoresValidos = season.filter(s => s.avg !== null).map(s => Math.abs(s.avg));
    const max = valoresValidos.length ? Math.max(...valoresValidos) : 0;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">ESTACIONALIDAD · RENDIMIENTO MEDIO MENSUAL (5 AÑOS)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(12,1fr);gap:4px;">'
        + season.map(s => {
            const sinDato = s.avg === null;
            const h = (!sinDato && max > 0) ? Math.round(Math.abs(s.avg) / max * 60) : 0;
            const color = sinDato ? 'var(--color-muted)' : s.color;
            const texto = sinDato ? '—' : ((s.avg > 0 ? '+' : '') + s.avg + '%');
            const titulo = sinDato ? 'Sin histórico suficiente para este mes' : (s.years + (s.years === 1 ? ' año' : ' años') + ' de histórico');
            return '<div style="text-align:center;" title="' + titulo + '">'
                + '<div style="font-size:9px;color:var(--color-muted);margin-bottom:4px;">' + s.month + '</div>'
                + '<div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:70px;">'
                + (sinDato ? '' : '<div style="width:100%;background:' + color + ';height:' + h + 'px;border-radius:2px;min-height:3px;"></div>')
                + '</div>'
                + '<div style="font-size:9px;color:' + color + ';margin-top:4px;">' + texto + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

// Flujo de opciones del ticker, si el escaneo nocturno vio algo. La mayoría
// de tickers no tienen nada la mayoría de los días —el escaneo solo guarda lo
// que pasa sus filtros— y entonces esta sección no se pinta: es un aviso
// cuando lo hay, no una fila más que rellenar con ceros.
function optionsFlowSection(data) {
    const f = data.options_flow;
    if (!f) return '';
    const color = f.sesgo === 'ALCISTA' ? 'var(--color-accent)'
                : f.sesgo === 'BAJISTA' ? '#f23645' : '#ffb800';
    // El NPS va de -1 a +1; la barra lo mapea a 0-100% con el centro en 50.
    const pos = Math.round((f.nps + 1) / 2 * 100);
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">'
        + '<span style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">FLUJO DE OPCIONES ' + tt('research-options-flow') + '</span>'
        + '<span style="color:' + color + ';font-size:13px;font-weight:500;">' + esc(f.sesgo) + '</span>'
        + '</div>'
        + '<div style="padding:12px 14px;">'
        + '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:11px;margin-bottom:10px;">'
        + '<span style="color:var(--color-muted);">Operaciones detectadas: <b style="color:var(--color-text);">' + esc(f.n_señales) + '</b></span>'
        + '<span style="color:var(--color-muted);">Prima total: <b style="color:var(--color-text);">' + esc(f.prima_fmt) + '</b></span>'
        + '<span style="color:var(--color-muted);">Señal más fuerte: <b style="color:var(--color-text);">' + esc(f.score_max) + '/12</b></span>'
        + '<span style="color:var(--color-muted);margin-left:auto;">Últimos ' + esc(f.dias) + ' días · visto el ' + esc(f.ultimo_scan) + '</span>'
        + '</div>'
        // Barra con el centro marcado: sin la referencia del cero, un 0,15 y
        // un 0,55 se ven casi igual de "llenos".
        + '<div style="position:relative;background:var(--color-bg,#0a0a0a);border-radius:3px;height:8px;">'
        + '<div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--color-border);"></div>'
        + '<div style="position:absolute;top:0;bottom:0;border-radius:3px;background:' + color + ';'
        + (f.nps >= 0 ? 'left:50%;width:' + (pos - 50) + '%;' : 'right:50%;width:' + (50 - pos) + '%;') + '"></div>'
        + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-size:9px;color:var(--color-muted);margin-top:4px;">'
        + '<span>Todo en puts</span><span>Equilibrado</span><span>Todo en calls</span></div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:8px;line-height:1.5;">'
        + 'Compara el dinero que se ha movido apostando al alza con el que apuesta a la baja (' + esc(f.nps) + ' sobre un máximo de ±1). '
        + 'Solo cuenta operaciones grandes o inusuales, no toda la actividad del valor.'
        + '</div>'
        + '</div></div>';
}

function insiderSection(data) {
    const insider = data.insider_trading;
    const summary = data.insider_summary;
    const monthlyVol = data.insider_monthly_volume;
    if (!insider || !insider.length) return '';
    const hasVolChart = monthlyVol && monthlyVol.length && monthlyVol.some(m => m.buy_shares || m.sell_shares);
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">INSIDER TRADING · TRANSACCIONES DIRECTIVOS</div>'
        + (summary ? insiderSummaryBar(summary) : '')
        + (hasVolChart
            ? '<div style="padding:14px 14px 4px;border-bottom:1px solid var(--color-border);">'
              + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:8px;">VOLUMEN MENSUAL DE TRANSACCIONES' + tt('insider-monthly-volume') + '</div>'
              + '<div style="position:relative;height:180px;"><canvas id="insider-volume-chart"></canvas></div>'
              + '</div>'
            : '')
        + '<div style="display:grid;grid-template-columns:85px 1fr 110px 65px 75px 70px 75px 1fr;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>NOMBRE</div><div>CARGO</div><div>TIPO</div><div>ACCIONES</div><div>PRECIO</div><div>VALOR</div><div>NATURALEZA</div>'
        + '</div>'
        + insider.map(i => '<div style="display:grid;grid-template-columns:85px 1fr 110px 65px 75px 70px 75px 1fr;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + esc(fmtFecha(i.date)) + '</div>'
            + '<div style="color:var(--color-text);">' + i.name + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + i.title + '</div>'
            + '<div style="background:' + i.type_color + '22;color:' + i.type_color + ';border:1px solid ' + i.type_color + '44;border-radius:3px;padding:2px 6px;font-size:10px;text-align:center;">' + i.type + '</div>'
            + '<div style="color:var(--color-text);">' + i.shares.toLocaleString('en-US') + '</div>'
            + '<div style="color:var(--color-text);">' + (i.price ? '$' + i.price.toFixed(2) : 'N/A') + '</div>'
            + '<div style="color:var(--color-text);">' + i.value + '</div>'
            + '<div style="font-size:10px;">'
            + '<span style="color:' + (i.flag_color || 'var(--color-muted)') + ';">' + (i.flag || '') + '</span>'
            + '<div style="color:var(--color-muted);font-size:9px;margin-top:2px;">' + (i.nature || '') + '</div>'
            + '</div>'
            + '</div>').join('')
        + '</div>';
}

function insiderSummaryBar(summary) {
    return '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);background:rgba(255,255,255,0.02);">'
        + '<div>'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">SENTIMIENTO ' + summary.months + 'M' + tt('insider-summary') + '</span> '
        + '<span style="color:' + summary.sentiment_color + ';font-size:12px;font-weight:600;letter-spacing:0.05em;">' + summary.sentiment + '</span>'
        + '</div>'
        + '<div style="font-size:11px;color:var(--color-muted);">'
        + '<span style="color:#00ffad;">' + summary.buy_count + ' compras</span> (' + summary.buy_value + ') · '
        + '<span style="color:#f23645;">' + summary.sell_count + ' ventas</span> (' + summary.sell_value + ')'
        + '</div>'
        + '<div style="font-size:11px;color:' + (summary.net_is_buy ? '#00ffad' : '#f23645') + ';">'
        + 'Neto: ' + (summary.net_is_buy ? '+' : '−') + summary.net_value
        + '</div>'
        + '</div>';
}
// ── HELPERS ───────────────────────────────────────────────────────────────────

function metricCard(title, rows) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:11px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
        + rows.map(([label, val, fmt, sectorInfo]) => {
            const fmtVal = fmt(val);
            // Color por defecto (comportamiento original, sin cambios si no hay sectorInfo)
            let valColor = fmtVal !== 'N/A' ? 'var(--color-text)' : 'var(--color-muted)';
            let sectorBadge = '';
            if (sectorInfo && fmtVal !== 'N/A') {
                valColor = sectorInfo.favorable ? '#00ffad' : '#f23645';
                const diffSign = sectorInfo.diff_pct >= 0 ? '+' : '';
                sectorBadge = ' <span title="' + sectorInfo.tooltip + '" style="color:' + valColor + ';font-size:9px;opacity:0.75;cursor:help;">('
                    + diffSign + sectorInfo.diff_pct.toFixed(0) + '% vs sector)</span>';
            }
            return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                + '<span style="color:var(--color-muted);">' + label + '</span>'
                + '<span style="color:' + valColor + ';">' + fmtVal + sectorBadge + '</span>'
                + '</div>';
        }).join('')
        + '</div>';
}

function _fmtVal(val) {
    if (val == null) return 'N/A';
    try {
        const v = parseFloat(val);
        if (Math.abs(v) >= 1e12) return '$' + (v/1e12).toFixed(2) + 'T';
        if (Math.abs(v) >= 1e9)  return '$' + (v/1e9).toFixed(2) + 'B';
        if (Math.abs(v) >= 1e6)  return '$' + (v/1e6).toFixed(2) + 'M';
        return '$' + v.toFixed(2);
    } catch(e) { return 'N/A'; }
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
                datasets: [{ data: data.sparkline, borderColor: color, backgroundColor: color + '18', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { display: false }, y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.04)' }, min: Math.min(...data.sparkline) * 0.995, max: Math.max(...data.sparkline) * 1.005 } }
            }
        });
    });
}

function renderEarningsChart(data) {
    if (!data.quarterly_earnings || !data.quarterly_earnings.length) return;
    const earnings = [...data.quarterly_earnings].reverse();
    loadChartJs(() => {
        const ctx = document.getElementById('earnings-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: earnings.map(e => e.date.substring(0, 7)),
                datasets: [
                    { label: 'Reportado', data: earnings.map(e => e.reported), backgroundColor: earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad88' : '#f2364588'), borderColor: earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad' : '#f23645'), borderWidth: 1 },
                    { label: 'Estimado', data: earnings.map(e => e.estimated), backgroundColor: 'transparent', borderColor: '#ffb800', borderWidth: 1.5, type: 'line', pointRadius: 3, tension: 0.3 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#666', font: { size: 10 } } } },
                scales: { x: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }, y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } } }
            }
        });
    });
}

function _fmtAxisVal(v) {
    if (v == null) return '';
    const av = Math.abs(v);
    if (av >= 1e9) return '$' + (v/1e9).toFixed(2) + 'B';
    if (av >= 1e6) return '$' + (v/1e6).toFixed(2) + 'M';
    if (av >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v.toFixed(0);
}

function renderIncomeStatementChart(data) {
    const inc = data.income_statement;
    if (!inc || !inc.length) return;
    loadChartJs(() => {
        const ctx = document.getElementById('income-statement-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: inc.map(r => r.date.substring(0, 7)),
                datasets: [
                    { label: 'Ingresos',           data: inc.map(r => r.revenue),          borderColor: '#3b82f6', backgroundColor: '#3b82f622', fill: true,  tension: 0.3, pointRadius: 2, borderWidth: 2 },
                    { label: 'Beneficio Bruto',     data: inc.map(r => r.gross_profit),     borderColor: '#00ffad', backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 2, borderWidth: 2 },
                    { label: 'Beneficio Operativo', data: inc.map(r => r.operating_income), borderColor: '#ffb800', backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 2, borderWidth: 2 },
                    { label: 'Beneficio Neto',      data: inc.map(r => r.net_income),       borderColor: '#a855f7', backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 2, borderWidth: 2 },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { color: '#999', font: { size: 10 }, boxWidth: 10, usePointStyle: true } },
                    tooltip: { callbacks: { label: c => ' ' + c.dataset.label + ': ' + _fmtAxisVal(c.raw) } }
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
                    y: { ticks: { color: '#555', font: { size: 9 }, callback: v => _fmtAxisVal(v) }, grid: { color: 'rgba(255,255,255,0.04)' } }
                }
            }
        });
    });
}

function renderInsiderVolumeChart(data) {
    const monthlyVol = data.insider_monthly_volume;
    if (!monthlyVol || !monthlyVol.length) return;
    loadChartJs(() => {
        const ctx = document.getElementById('insider-volume-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: monthlyVol.map(m => m.month),
                datasets: [
                    { label: 'Compras', data: monthlyVol.map(m => m.buy_shares),  backgroundColor: '#00ffad', borderRadius: 2 },
                    { label: 'Ventas',  data: monthlyVol.map(m => -m.sell_shares), backgroundColor: '#f23645', borderRadius: 2 },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#999', font: { size: 10 }, boxWidth: 10, usePointStyle: true } },
                    tooltip: { callbacks: { label: c => ' ' + c.dataset.label + ': ' + Math.abs(c.raw).toLocaleString('en-US') + ' acciones' } }
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 } }, grid: { display: false } },
                    y: { ticks: { color: '#555', font: { size: 9 }, callback: v => Math.abs(v).toLocaleString('en-US') }, grid: { color: 'rgba(255,255,255,0.04)' } }
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

// Toggle descripción
window.toggleDesc = function() {
    const short = document.getElementById('desc-short');
    const full  = document.getElementById('desc-full');
    const btn   = document.getElementById('desc-btn');
    if (!short || !full || !btn) return;
    const isShowing = full.style.display === 'none';
    short.style.display = isShowing ? 'none' : 'block';
    full.style.display  = isShowing ? 'block' : 'none';
    btn.textContent     = isShowing ? '▲ Ver menos' : '▼ Ver más';
};