import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';

const SECTORS = ['GENERAL','TECH','FINANCE','ENERGY','HEALTH','MACRO','CRYPTO','POLICY','DEFENSE'];
const IMPACTS = ['ALL','HIGH','MED','LOW'];

let activeImpact = 'ALL';
let activeSector = 'ALL';
let refreshTimer = null;
let countdownTimer = null;
let secondsLeft = 300;
let cachedData = null;

export async function render(container) {
    container.innerHTML =
        // Header
        '<div style="margin-bottom:1.5rem;">'
        + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);">NEWS FEED</div>'
        + '<div id="refresh-countdown" style="color:var(--color-muted);font-size:10px;padding:2px 8px;border:1px solid var(--color-border);border-radius:3px;font-family:var(--font-mono);">↻ 5:00</div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">RSS + Finnhub · Clasificación automática · Auto-refresh 5min</div>'
        + '</div>'

        // Ticker precios
        + '<div id="prices-bar" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;margin-bottom:1rem;display:flex;gap:1.5rem;overflow-x:auto;flex-wrap:nowrap;">'
        + '<span style="color:var(--color-muted);font-size:11px;">Cargando precios...</span>'
        + '</div>'

        // Filtros impacto
        + '<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;align-items:center;">'
        + IMPACTS.map(i => '<button class="impact-btn" data-impact="' + i + '" style="'
            + 'background:' + (i === activeImpact ? impactColor(i) : 'var(--color-surface)') + ';'
            + 'color:' + (i === activeImpact ? '#000' : 'var(--color-muted)') + ';'
            + 'border:1px solid ' + impactColor(i) + ';border-radius:var(--radius);padding:4px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;letter-spacing:0.05em;">'
            + i + '</button>').join('')
        + '<div style="flex:1;"></div>'
        + SECTORS.map(s => '<button class="sector-btn" data-sector="' + s + '" style="'
            + 'background:' + (s === activeSector ? 'var(--color-secondary)' : 'var(--color-surface)') + ';'
            + 'color:' + (s === activeSector ? '#000' : 'var(--color-muted)') + ';'
            + 'border:1px solid var(--color-border);border-radius:var(--radius);padding:4px 10px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">'
            + s + '</button>').join('')
        + '</div>'

        // Stats + source health
        + '<div id="news-stats" style="margin-bottom:8px;"></div>'
        + '<div id="source-health" style="margin-bottom:1rem;"></div>'

        // Layout: feed principal + panel Trump
        + '<div style="display:grid;grid-template-columns:1fr 340px;gap:1rem;align-items:start;">'

        // Feed principal
        + '<div id="news-feed"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando noticias...</div></div>'

        // Panel Trump / Truth Social
        + '<div>'
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;position:sticky;top:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:8px;">'
        + '<div style="width:8px;height:8px;border-radius:50%;background:#e2231a;flex-shrink:0;"></div>'
        + '<div style="color:#e2231a;font-size:12px;letter-spacing:0.08em;font-family:var(--font-mono);">TRUTH SOCIAL ' + tt('trump-truth-social') + '</div>'
        + '</div>'
        + '<div style="padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">Trump · @realDonaldTrump · trumpstruth.org</div>'
        + '<div id="trump-feed" style="max-height:600px;overflow-y:auto;">Cargando...</div>'
        + '</div>'
        + '</div>'

        + '</div>';

    // Event listeners filtros
    container.querySelectorAll('.impact-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeImpact = btn.getAttribute('data-impact');
            renderFeedFromCache(container);
            updateFilterStyles(container);
        });
    });
    container.querySelectorAll('.sector-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeSector = btn.getAttribute('data-sector');
            renderFeedFromCache(container);
            updateFilterStyles(container);
        });
    });

    // Carga inicial
    loadPrices(container.querySelector('#prices-bar'));
    await loadNews(container);
    loadTrump(container.querySelector('#trump-feed'));

    // Auto-refresh cada 5 minutos
    startAutoRefresh(container);
}

// ── AUTO-REFRESH ──────────────────────────────────────────────────────────────

function startAutoRefresh(container) {
    if (refreshTimer)  clearInterval(refreshTimer);
    if (countdownTimer) clearInterval(countdownTimer);

    secondsLeft = 300;
    updateCountdown(container);

    countdownTimer = setInterval(() => {
        secondsLeft--;
        updateCountdown(container);
        if (secondsLeft <= 0) secondsLeft = 300;
    }, 1000);

    refreshTimer = setInterval(async () => {
        secondsLeft = 300;
        await loadNews(container);
        loadTrump(container.querySelector('#trump-feed'));
    }, 300000); // 5 minutos
}

function updateCountdown(container) {
    const el = container.querySelector('#refresh-countdown');
    if (!el) return;
    const m = Math.floor(secondsLeft / 60);
    const s = secondsLeft % 60;
    el.textContent = '↻ ' + m + ':' + String(s).padStart(2, '0');
    el.style.color = secondsLeft < 60 ? 'var(--color-accent)' : 'var(--color-muted)';
}

// ── NEWS PRINCIPAL ────────────────────────────────────────────────────────────

async function loadNews(container) {
    const feed  = container.querySelector('#news-feed');
    const stats = container.querySelector('#news-stats');
    const health = container.querySelector('#source-health');
    if (feed) feed.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/newsfeed/?limit=80', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        cachedData = data;

        // Stats
        if (stats) {
            const s = data.stats;
            stats.innerHTML = '<div style="display:flex;gap:1rem;font-size:11px;flex-wrap:wrap;">'
                + '<span style="color:var(--color-muted);">Total: <b style="color:var(--color-text);">' + data.total + '</b></span>'
                + '<span style="color:#f23645;">● HIGH: <b>' + s.high + '</b></span>'
                + '<span style="color:#ffb800;">● MED: <b>' + s.med + '</b></span>'
                + '<span style="color:var(--color-muted);">● LOW: <b>' + s.low + '</b></span>'
                + '<span style="color:var(--color-accent);">▲ Alcista: <b>' + s.bullish + '</b></span>'
                + '<span style="color:#f23645;">▼ Bajista: <b>' + s.bearish + '</b></span>'
                + '<span style="color:var(--color-muted);margin-left:auto;font-size:10px;">Actualizado: ' + data.timestamp + '</span>'
                + '</div>';
        }

        // Source health indicator
        if (health && data.sources) {
            const active  = data.sources.filter(s => s.ok).length;
            const total   = data.sources.length;
            health.innerHTML = '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">'
                + '<span style="color:var(--color-muted);font-size:10px;">Fuentes activas: <b style="color:var(--color-accent);">' + active + '/' + total + '</b></span>'
                + data.sources.map(s => {
                    const color = s.ok ? 'var(--color-accent)' : '#444';
                    const href  = s.url ? ' onclick="window.open(\'' + s.url + '\',\'_blank\')"' : '';
                    return '<span style="color:' + color + ';font-size:9px;padding:1px 5px;border:1px solid ' + color + '33;border-radius:2px;cursor:' + (s.url ? 'pointer' : 'default') + ';"'
                        + (s.url ? href : '') + '>' + s.label + '</span>';
                }).join('')
                + '</div>';
        }

        renderFeedFromCache(container);

    } catch(e) {
        if (feed) feed.innerHTML = errorMessage(e.message);
    }
}

function renderFeedFromCache(container) {
    const feed = container.querySelector('#news-feed');
    if (!feed || !cachedData) return;

    let items = cachedData.items || [];

    if (activeImpact !== 'ALL') items = items.filter(i => i.impact === activeImpact);
    if (activeSector !== 'ALL') items = items.filter(i => i.sector === activeSector);

    if (!items.length) {
        feed.innerHTML = '<div style="padding:2rem;color:var(--color-muted);font-size:12px;text-align:center;">No hay noticias con los filtros seleccionados.</div>';
        return;
    }
    feed.innerHTML = items.map(item => newsCard(item)).join('');
}

function newsCard(item) {
    const ic = impactColor(item.impact);
    const sc = sentimentColor(item.sentiment);
    const timeStr = item.mins_ago < 60
        ? item.mins_ago + 'm'
        : item.mins_ago < 1440
        ? Math.floor(item.mins_ago / 60) + 'h'
        : Math.floor(item.mins_ago / 1440) + 'd';

    // Badge especial para Finnhub
    const isFinnhub = item.source_id === 'finnhub';
    const sourceBadge = item.source_url
        ? '<a href="' + item.source_url + '" target="_blank" style="color:' + (isFinnhub ? 'var(--color-secondary)' : 'var(--color-muted)') + ';font-size:10px;text-decoration:none;" title="Ir a ' + item.source + '">'
          + (isFinnhub ? '★ ' : '') + item.source + '</a>'
        : '<span style="color:var(--color-muted);font-size:10px;">' + item.source + '</span>';

    return '<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--color-border);align-items:flex-start;">'
        + '<div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;padding-top:2px;">'
        + '<div style="width:3px;height:32px;background:' + ic + ';border-radius:2px;"></div>'
        + '</div>'
        + '<div style="flex:1;min-width:0;">'
        + '<a href="' + item.url + '" target="_blank" rel="noopener" style="color:var(--color-text);font-size:13px;line-height:1.4;display:block;margin-bottom:4px;text-decoration:none;" onmouseover="this.style.color=\'var(--color-accent)\'" onmouseout="this.style.color=\'var(--color-text)\'">'
        + item.title
        + '</a>'
        + (item.desc ? '<div style="color:var(--color-muted);font-size:11px;line-height:1.4;margin-bottom:4px;">' + item.desc.substring(0, 120) + '...</div>' : '')
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        + '<span style="color:' + ic + ';font-size:10px;border:1px solid ' + ic + '33;padding:1px 6px;border-radius:3px;">' + item.impact + '</span>'
        + '<span style="color:' + sc + ';font-size:10px;">' + sentimentIcon(item.sentiment) + ' ' + item.sentiment + '</span>'
        + '<span style="color:var(--color-secondary);font-size:10px;padding:1px 6px;background:rgba(0,217,255,0.08);border-radius:3px;">' + item.sector + '</span>'
        + sourceBadge
        + '<span style="color:var(--color-muted);font-size:10px;margin-left:auto;">' + timeStr + '</span>'
        + '</div>'
        + '</div>'
        + '</div>';
}

// ── TRUMP FEED ────────────────────────────────────────────────────────────────

async function loadTrump(el) {
    if (!el) return;
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/newsfeed/trump?limit=15', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();

        if (!data.ok || !data.posts.length) {
            el.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:11px;">Sin posts disponibles.</div>';
            return;
        }

        el.innerHTML = data.posts.map(post => trumpCard(post)).join('')
            + '<div style="padding:8px 14px;font-size:10px;color:#555;border-top:1px solid var(--color-border);">Fuente: ' + data.source + '</div>';

    } catch(e) {
        el.innerHTML = errorMessage(e.message, {fontSize: '11px'});
    }
}

function trumpCard(post) {
    const timeStr = post.mins_ago < 60
        ? post.mins_ago + 'm'
        : post.mins_ago < 1440
        ? Math.floor(post.mins_ago / 60) + 'h'
        : Math.floor(post.mins_ago / 1440) + 'd';
    const ic     = impactColor(post.impact);
    const text   = post.content || post.title || '';
    const isHigh = post.impact === 'HIGH';

    return '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);'
        + (isHigh ? 'background:rgba(242,54,69,0.04);' : '') + '">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<div style="display:flex;gap:6px;align-items:center;">'
        + (isHigh ? '<span style="color:#f23645;font-size:9px;border:1px solid #f2364544;padding:1px 5px;border-radius:2px;">HIGH IMPACT</span>' : '')
        + '<span style="color:var(--color-secondary);font-size:9px;padding:1px 5px;background:rgba(0,217,255,0.08);border-radius:2px;">' + post.sector + '</span>'
        + '</div>'
        + '<span style="color:var(--color-muted);font-size:10px;">' + timeStr + '</span>'
        + '</div>'
        + '<div style="color:var(--color-text);font-size:12px;line-height:1.5;margin-bottom:6px;">' + text.substring(0, 280) + (text.length > 280 ? '...' : '') + '</div>'
        + (post.url ? '<a href="' + post.url + '" target="_blank" rel="noopener" style="color:var(--color-muted);font-size:10px;text-decoration:none;" onmouseover="this.style.color=\'#e2231a\'" onmouseout="this.style.color=\'var(--color-muted)\'">Ver post original ↗</a>' : '')
        + '</div>';
}

// ── PRICES ────────────────────────────────────────────────────────────────────

async function loadPrices(el) {
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/newsfeed/prices', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        el.innerHTML = data.map(p => {
            const up    = p.chg >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            return '<div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
                + '<div style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + p.name + '</div>'
                + '<div style="color:var(--color-text);font-size:12px;">' + p.price.toLocaleString('en-US') + '</div>'
                + '<div style="color:' + color + ';font-size:10px;">' + (up ? '+' : '') + p.chg.toFixed(2) + '%</div>'
                + '</div>';
        }).join('<div style="width:1px;background:var(--color-border);flex-shrink:0;"></div>');
    } catch(e) {
        el.innerHTML = '<span style="color:var(--color-muted);font-size:11px;">Sin precios</span>';
    }
}

// ── UTILS ─────────────────────────────────────────────────────────────────────

function updateFilterStyles(container) {
    container.querySelectorAll('.impact-btn').forEach(btn => {
        const i = btn.getAttribute('data-impact');
        const active = i === activeImpact;
        btn.style.background = active ? impactColor(i) : 'var(--color-surface)';
        btn.style.color      = active ? '#000' : 'var(--color-muted)';
    });
    container.querySelectorAll('.sector-btn').forEach(btn => {
        const s = btn.getAttribute('data-sector');
        const active = s === activeSector;
        btn.style.background = active ? 'var(--color-secondary)' : 'var(--color-surface)';
        btn.style.color      = active ? '#000' : 'var(--color-muted)';
    });
}

function impactColor(impact) {
    if (impact === 'HIGH') return '#f23645';
    if (impact === 'MED')  return '#ffb800';
    return 'var(--color-muted)';
}

function sentimentColor(s) {
    if (s === 'bullish') return 'var(--color-accent)';
    if (s === 'bearish') return '#f23645';
    return 'var(--color-muted)';
}

function sentimentIcon(s) {
    if (s === 'bullish') return '▲';
    if (s === 'bearish') return '▼';
    return '—';
}