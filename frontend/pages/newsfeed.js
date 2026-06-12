const SECTORS = ['GENERAL','TECH','FINANCE','ENERGY','HEALTH','MACRO','CRYPTO','POLICY','DEFENSE'];
const IMPACTS = ['ALL','HIGH','MED','LOW'];

let activeImpact = 'ALL';
let activeSector = 'ALL';

export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">NEWS FEED</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">~15 fuentes · RSS · Clasificación automática · Tiempo real</div>'
        + '</div>'

        // Ticker precios
        + '<div id="prices-bar" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;margin-bottom:1rem;display:flex;gap:1.5rem;overflow-x:auto;flex-wrap:nowrap;">'
        + '<span style="color:var(--color-muted);font-size:11px;">Cargando precios...</span>'
        + '</div>'

        // Filtros
        + '<div style="display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;">'
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

        // Stats
        + '<div id="news-stats" style="margin-bottom:1rem;"></div>'

        // Feed
        + '<div id="news-feed"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando noticias...</div></div>';

    // Event listeners filtros
    container.querySelectorAll('.impact-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeImpact = btn.getAttribute('data-impact');
            renderNews(container);
            updateFilterStyles(container);
        });
    });
    container.querySelectorAll('.sector-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeSector = btn.getAttribute('data-sector');
            renderNews(container);
            updateFilterStyles(container);
        });
    });

    // Cargar precios y noticias en paralelo
    loadPrices(container.querySelector('#prices-bar'));
    await renderNews(container);
}

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

async function renderNews(container) {
    const feed  = container.querySelector('#news-feed');
    const stats = container.querySelector('#news-stats');
    if (feed) feed.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div>';

    try {
        const token  = sessionStorage.getItem('rsu_token');
        let   url    = '/api/v1/newsfeed/?limit=80';
        if (activeImpact !== 'ALL') url += '&impact=' + activeImpact;
        if (activeSector !== 'ALL') url += '&sector=' + activeSector;

        const res  = await fetch(url, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();

        if (!data.ok) throw new Error('Sin datos');

        // Stats bar
        if (stats) {
            const s = data.stats;
            stats.innerHTML = '<div style="display:flex;gap:1rem;font-size:11px;flex-wrap:wrap;">'
                + '<span style="color:var(--color-muted);">Total: <b style="color:var(--color-text);">' + data.total + '</b></span>'
                + '<span style="color:#f23645;">● HIGH: <b>' + s.high + '</b></span>'
                + '<span style="color:#ffb800;">● MED: <b>' + s.med + '</b></span>'
                + '<span style="color:var(--color-muted);">● LOW: <b>' + s.low + '</b></span>'
                + '<span style="color:var(--color-accent);">▲ Alcista: <b>' + s.bullish + '</b></span>'
                + '<span style="color:#f23645;">▼ Bajista: <b>' + s.bearish + '</b></span>'
                + '<span style="color:var(--color-muted);margin-left:auto;">Actualizado: ' + data.timestamp + '</span>'
                + '</div>';
        }

        if (!data.items.length) {
            feed.innerHTML = '<div style="padding:2rem;color:var(--color-muted);font-size:12px;text-align:center;">No hay noticias con los filtros seleccionados.</div>';
            return;
        }

        feed.innerHTML = data.items.map(item => newsCard(item)).join('');

    } catch(e) {
        if (feed) feed.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
    }
}

function newsCard(item) {
    const ic = impactColor(item.impact);
    const sc = sentimentColor(item.sentiment);
    const timeStr = item.mins_ago < 60
        ? item.mins_ago + 'm'
        : item.mins_ago < 1440
        ? Math.floor(item.mins_ago / 60) + 'h'
        : Math.floor(item.mins_ago / 1440) + 'd';

    return '<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--color-border);align-items:flex-start;">'

        // Indicadores laterales
        + '<div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;padding-top:2px;">'
        + '<div style="width:3px;height:32px;background:' + ic + ';border-radius:2px;" title="' + item.impact + '"></div>'
        + '</div>'

        // Contenido
        + '<div style="flex:1;min-width:0;">'
        + '<a href="' + item.url + '" target="_blank" style="color:var(--color-text);font-size:13px;line-height:1.4;display:block;margin-bottom:4px;text-decoration:none;">'
        + item.title
        + '</a>'
        + (item.desc ? '<div style="color:var(--color-muted);font-size:11px;line-height:1.4;margin-bottom:4px;">' + item.desc.substring(0, 120) + '...</div>' : '')
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        + '<span style="color:' + ic + ';font-size:10px;border:1px solid ' + ic + '33;padding:1px 6px;border-radius:3px;">' + item.impact + '</span>'
        + '<span style="color:' + sc + ';font-size:10px;">' + sentimentIcon(item.sentiment) + ' ' + item.sentiment + '</span>'
        + '<span style="color:var(--color-secondary);font-size:10px;padding:1px 6px;background:rgba(0,217,255,0.08);border-radius:3px;">' + item.sector + '</span>'
        + '<span style="color:var(--color-muted);font-size:10px;">' + item.source + '</span>'
        + '<span style="color:var(--color-muted);font-size:10px;margin-left:auto;">' + timeStr + '</span>'
        + '</div>'
        + '</div>'
        + '</div>';
}

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