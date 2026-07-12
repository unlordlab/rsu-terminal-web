import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = pageHeader();

    const input  = container.querySelector('#research-input');
    const btn    = container.querySelector('#research-btn');
    const result = container.querySelector('#research-result');

    async function doResearch() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent   = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando datos de ' + ticker + '...</div>';
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
            renderIncomeStatementChart(data);
            renderInsiderVolumeChart(data);
            renderCryptoChart(data);
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
    }
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
        + '<span class="ticker-link" style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + data.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + data.name + '</span>'
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
        + chartSection(data)
        + technicalSection(data)
        + metricsSection(data)
        + incomeStatementSection(data)
        + consensoSection(data)
        + analystChangesSection(data)
        + institutionalSection(data)
        + seasonalitySection(data)
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
        + '<span onclick="goToResearch(\'' + data.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + data.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + data.name + '</span>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-bottom:4px;">' + data.sector + ' · ' + data.industry + ' · ' + data.country + '</div>'
        + (data.website ? '<a href="' + data.website + '" target="_blank" style="color:var(--color-secondary);font-size:11px;">' + data.website + '</a>' : '')
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
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">RSU SCORE ' + tt('rsu-score') + '</span>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span style="color:' + scoreColor + ';font-size:20px;font-weight:500;">' + score.score + '/100</span>'
        + '<span style="color:' + scoreColor + ';font-size:12px;padding:2px 10px;border:1px solid ' + scoreColor + '33;border-radius:4px;">' + score.label + '</span>'
        + '</div></div>'
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin-bottom:8px;">'
        + '<div style="height:100%;width:' + score.score + '%;background:' + scoreColor + ';border-radius:4px;transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="display:flex;gap:1rem;flex-wrap:wrap;">'
        + (score.breakdown || []).map(b => {
            const pct = b.max > 0 ? Math.round(b.pts / b.max * 100) : 0;
            return '<div style="font-size:10px;color:var(--color-muted);">'
                + b.label + ': <span style="color:' + (pct >= 75 ? 'var(--color-accent)' : pct >= 50 ? '#ffb800' : '#f23645') + ';">' + b.pts + '/' + b.max + '</span>'
                + ' <span style="color:var(--color-muted);">(' + b.val + ')</span>'
                + '</div>';
        }).join('')
        + '</div>'
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

function metricsSection(data) {
    const m = data.metrics;
    const p = data.profitability;
    const sc = (data.sector_comparison && data.sector_comparison.ok) ? data.sector_comparison.items : {};
    const sectorName = data.sector || 'el sector';

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

    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'
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
        + '</div>';
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
                + '<div style="color:var(--color-muted);">' + c.date + '</div>'
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
            + '<a href="' + n.url + '" target="_blank" style="color:var(--color-text);font-size:12px;line-height:1.4;display:block;">' + n.headline + '</a>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:3px;">' + n.source + (n.date ? ' · ' + n.date : '') + '</div>'
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
              + '<div style="color:#ffb800;font-size:14px;font-weight:500;">📅 ' + ne.date + '</div>'
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
    const max = Math.max(...season.map(s => Math.abs(s.avg)));
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">ESTACIONALIDAD · RENDIMIENTO MEDIO MENSUAL (5 AÑOS)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(12,1fr);gap:4px;">'
        + season.map(s => {
            const h = max > 0 ? Math.round(Math.abs(s.avg) / max * 60) : 0;
            return '<div style="text-align:center;">'
                + '<div style="font-size:9px;color:var(--color-muted);margin-bottom:4px;">' + s.month + '</div>'
                + '<div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:70px;">'
                + '<div style="width:100%;background:' + s.color + ';height:' + h + 'px;border-radius:2px;min-height:3px;"></div>'
                + '</div>'
                + '<div style="font-size:9px;color:' + s.color + ';margin-top:4px;">' + (s.avg > 0 ? '+' : '') + s.avg + '%</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
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
            + '<div style="color:var(--color-muted);">' + i.date + '</div>'
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