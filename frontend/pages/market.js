export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">MARKET</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Dashboard de mercado · Carga modular</div>'
        + '</div>'
        + '<div id="market-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem;">'
        + '<div id="widget-indices"></div>'
        + '<div id="widget-feargreed"></div>'
        + '<div id="widget-forex"></div>'
        + '<div id="widget-commodities"></div>'
        + '<div id="widget-sectors" style="grid-column:1/-1;"></div>'
        + '</div>';

    loadIndices(container.querySelector('#widget-indices'));
    loadFearGreed(container.querySelector('#widget-feargreed'));
    loadForex(container.querySelector('#widget-forex'));
    loadCommodities(container.querySelector('#widget-commodities'));
    loadSectors(container.querySelector('#widget-sectors'));
}

async function loadIndices(el) {
    el.innerHTML = widgetShell('INDICES', 'Mercados principales', loading());
    try {
        const res  = await fetch('/api/v1/market/indices', { headers: authHeader() });
        const data = await res.json();
        const rows = data.data.map(idx => {
            if (!idx.ok) return errorRow(idx.ticker, idx.name);
            const up    = idx.pct >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const arrow = up ? '▲' : '▼';
            return row(idx.ticker, idx.name,
                idx.price.toLocaleString('es-ES'),
                arrow + ' ' + Math.abs(idx.change).toLocaleString('es-ES') + ' (' + (idx.pct > 0 ? '+' : '') + idx.pct + '%)',
                color);
        }).join('');
        el.innerHTML = widgetShell('INDICES', 'Mercados principales', rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('INDICES', 'Mercados principales', widgetError(e.message));
    }
}

async function loadFearGreed(el) {
    el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', loading());
    try {
        const res  = await fetch('/api/v1/market/fear-greed', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        const color = fgColor(data.score);
        const content = '<div style="display:flex;flex-direction:column;align-items:center;padding:1rem;">'
            + buildGauge(data.score, color)
            + '<div style="color:' + color + ';font-size:18px;letter-spacing:0.1em;margin-top:8px;">' + data.score + '</div>'
            + '<div style="color:' + color + ';font-size:12px;margin-top:2px;">' + data.rating + '</div>'
            + '<div style="display:flex;gap:2rem;margin-top:1rem;font-size:11px;color:var(--color-muted);">'
            + '<div style="text-align:center;"><div>AYER</div><div style="color:var(--color-text);margin-top:2px;">' + data.prev + '</div></div>'
            + '<div style="text-align:center;"><div>HACE 1 SEM</div><div style="color:var(--color-text);margin-top:2px;">' + data.week_ago + '</div></div>'
            + '</div></div>';
        el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', content, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', widgetError(e.message));
    }
}

async function loadForex(el) {
    el.innerHTML = widgetShell('FOREX', 'Tipos de cambio', loading());
    try {
        const res  = await fetch('/api/v1/market/forex', { headers: authHeader() });
        const data = await res.json();
        const rows = data.data.map(fx => {
            if (!fx.ok) return errorRow(fx.ticker, fx.name);
            const up    = fx.pct >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const arrow = up ? '▲' : '▼';
            return row(fx.ticker, fx.name,
                fx.price.toFixed(4),
                arrow + ' ' + Math.abs(fx.change).toFixed(4) + ' (' + (fx.pct > 0 ? '+' : '') + fx.pct + '%)',
                color);
        }).join('');
        el.innerHTML = widgetShell('FOREX', 'Tipos de cambio', rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('FOREX', 'Tipos de cambio', widgetError(e.message));
    }
}

async function loadCommodities(el) {
    el.innerHTML = widgetShell('COMMODITIES', 'Futuros', loading());
    try {
        const res  = await fetch('/api/v1/market/commodities', { headers: authHeader() });
        const data = await res.json();
        const rows = data.data.map(c => {
            if (!c.ok) return errorRow(c.ticker, c.name);
            const up    = c.pct >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const arrow = up ? '▲' : '▼';
            return row(c.ticker, c.name,
                c.prefix + c.price.toLocaleString('es-ES'),
                arrow + ' ' + Math.abs(c.change).toFixed(2) + ' (' + (c.pct > 0 ? '+' : '') + c.pct + '%)',
                color);
        }).join('');
        el.innerHTML = widgetShell('COMMODITIES', 'Futuros', rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('COMMODITIES', 'Futuros', widgetError(e.message));
    }
}

async function loadSectors(el) {
    el.innerHTML = widgetShell('SECTOR PERFORMANCE', 'S&P 500 ETFs · Hoy', loading());
    try {
        const res  = await fetch('/api/v1/market/sectors', { headers: authHeader() });
        const data = await res.json();
        const max  = Math.max(...data.data.map(s => Math.abs(s.pct)));
        const bars = data.data.map(s => {
            const up    = s.pct >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const w     = max > 0 ? Math.abs(s.pct) / max * 100 : 0;
            const pctStr = (s.pct > 0 ? '+' : '') + s.pct + '%';
            return '<div style="display:flex;align-items:center;gap:10px;padding:7px 14px;border-bottom:1px solid var(--color-border);">'
                + '<div style="width:90px;font-size:12px;color:var(--color-text);flex-shrink:0;">' + s.name + '</div>'
                + '<div style="flex:1;background:var(--color-surface2);border-radius:2px;height:6px;overflow:hidden;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '<div style="width:60px;text-align:right;font-size:12px;color:' + color + ';flex-shrink:0;">' + pctStr + '</div>'
                + '</div>';
        }).join('');
        el.innerHTML = widgetShell('SECTOR PERFORMANCE', 'S&P 500 ETFs · Hoy', bars, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('SECTOR PERFORMANCE', 'S&P 500 ETFs · Hoy', widgetError(e.message));
    }
}

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function fgColor(score) {
    if (score >= 75) return '#00ffad';
    if (score >= 55) return '#90ee90';
    if (score >= 45) return '#ffb800';
    if (score >= 25) return '#ff8c00';
    return '#f23645';
}

function buildGauge(score, color) {
    const angle = -90 + (score / 100) * 180;
    const rad   = angle * Math.PI / 180;
    const cx = 80, cy = 80, r = 60;
    const nx = cx + r * Math.cos(rad);
    const ny = cy + r * Math.sin(rad);
    return '<svg width="160" height="90" viewBox="0 0 160 90">'
        + '<defs><linearGradient id="fg-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        + '<stop offset="0%" stop-color="#f23645"/>'
        + '<stop offset="25%" stop-color="#ff8c00"/>'
        + '<stop offset="50%" stop-color="#ffb800"/>'
        + '<stop offset="75%" stop-color="#90ee90"/>'
        + '<stop offset="100%" stop-color="#00ffad"/>'
        + '</linearGradient></defs>'
        + '<path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="#1a1a1a" stroke-width="12"/>'
        + '<path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="url(#fg-grad)" stroke-width="12"/>'
        + '<line x1="' + cx + '" y1="' + cy + '" x2="' + nx.toFixed(1) + '" y2="' + ny.toFixed(1) + '" stroke="' + color + '" stroke-width="2" stroke-linecap="round"/>'
        + '<circle cx="' + cx + '" cy="' + cy + '" r="3" fill="' + color + '"/>'
        + '</svg>';
}

function row(ticker, name, price, change, color) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div>'
        + '<div style="color:var(--color-text);font-size:13px;font-weight:500;">' + ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + name + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:14px;">' + price + '</div>'
        + '<div style="color:' + color + ';font-size:11px;">' + change + '</div>'
        + '</div>'
        + '</div>';
}

function widgetShell(title, subtitle, content, timestamp) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + title + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + subtitle + '</div>'
        + '</div>'
        + '<div>' + content + '</div>'
        + (timestamp ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);">Actualizado: ' + timestamp + '</div>' : '')
        + '</div>';
}

function loading() {
    return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando...</div>';
}

function widgetError(msg) {
    return '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + msg + '</div>';
}

function errorRow(ticker, name) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:13px;">' + ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + name + '</div>'
        + '</div>'
        + '<div style="color:#f23645;font-size:11px;">✗ Sin datos</div>'
        + '</div>';
}