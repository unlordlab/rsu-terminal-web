export async function render(container) {
    container.innerHTML = `
        <div style="margin-bottom:1.5rem;">
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">MARKET</div>
            <div style="color:var(--color-muted);font-size:12px;">Dashboard de mercado · Carga modular</div>
        </div>
        <div id="market-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem;">
            <div id="widget-indices"></div>
            <div id="widget-feargreed"></div>
        </div>
    `;

    // Carga en paralelo — cada widget es independiente
    loadIndices(container.querySelector('#widget-indices'));
    loadFearGreed(container.querySelector('#widget-feargreed'));
}

// ── WIDGET: ÍNDICES ───────────────────────────────────────────────────────────

async function loadIndices(el) {
    el.innerHTML = widgetShell('ÍNDICES', 'Mercados principales', '<div class="wloading">Cargando...</div>');

    try {
        const res  = await fetch('/api/v1/market/indices', { headers: authHeader() });
        const data = await res.json();
        const rows = data.data.map(idx => {
            if (!idx.ok) return errorRow(idx.ticker, idx.name);
            const up    = idx.pct >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const arrow = up ? '▲' : '▼';
            return `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">
                    <div>
                        <div style="color:var(--color-text);font-size:13px;font-weight:500;">${idx.ticker}</div>
                        <div style="color:var(--color-muted);font-size:11px;">${idx.name}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:var(--color-text);font-size:14px;">${idx.price.toLocaleString('es-ES')}</div>
                        <div style="color:${color};font-size:11px;">${arrow} ${Math.abs(idx.change).toLocaleString('es-ES')} (${idx.pct > 0 ? '+' : ''}${idx.pct}%)</div>
                    </div>
                </div>
            `;
        }).join('');

        el.innerHTML = widgetShell(
            'ÍNDICES',
            'Mercados principales',
            rows,
            data.timestamp
        );
    } catch(e) {
        el.innerHTML = widgetShell('ÍNDICES', 'Mercados principales', widgetError(e.message));
    }
}

// ── WIDGET: FEAR & GREED ──────────────────────────────────────────────────────

async function loadFearGreed(el) {
    el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', '<div class="wloading">Cargando...</div>');

    try {
        const res  = await fetch('/api/v1/market/fear-greed', { headers: authHeader() });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const score  = data.score;
        const color  = fgColor(score);
        const rating = data.rating;

        const gauge = buildGauge(score, color);

        const content = `
            <div style="display:flex;flex-direction:column;align-items:center;padding:1rem;">
                ${gauge}
                <div style="color:${color};font-size:18px;letter-spacing:0.1em;margin-top:8px;">${score}</div>
                <div style="color:${color};font-size:12px;margin-top:2px;">${rating}</div>
                <div style="display:flex;gap:2rem;margin-top:1rem;font-size:11px;color:var(--color-muted);">
                    <div style="text-align:center;">
                        <div>AYER</div>
                        <div style="color:var(--color-text);margin-top:2px;">${data.prev}</div>
                    </div>
                    <div style="text-align:center;">
                        <div>HACE 1 SEM</div>
                        <div style="color:var(--color-text);margin-top:2px;">${data.week_ago}</div>
                    </div>
                </div>
            </div>
        `;

        el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', content, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('FEAR & GREED', 'CNN Index', widgetError(e.message));
    }
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

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
    const angle   = -90 + (score / 100) * 180;
    const rad     = angle * Math.PI / 180;
    const cx = 80, cy = 80, r = 60;
    const nx = cx + r * Math.cos(rad);
    const ny = cy + r * Math.sin(rad);
    return `
        <svg width="160" height="90" viewBox="0 0 160 90">
            <path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="#1a1a1a" stroke-width="12"/>
            <path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="url(#fg-grad)" stroke-width="12"/>
            <defs>
                <linearGradient id="fg-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%"   stop-color="#f23645"/>
                    <stop offset="25%"  stop-color="#ff8c00"/>
                    <stop offset="50%"  stop-color="#ffb800"/>
                    <stop offset="75%"  stop-color="#90ee90"/>
                    <stop offset="100%" stop-color="#00ffad"/>
                </linearGradient>
            </defs>
            <line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}"
                  stroke="${color}" stroke-width="2" stroke-linecap="round"/>
            <circle cx="${cx}" cy="${cy}" r="3" fill="${color}"/>
        </svg>
    `;
}

function widgetShell(title, subtitle, content, timestamp = '') {
    return `
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">
                <div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">${title}</div>
                <div style="color:var(--color-muted);font-size:11px;">${subtitle}</div>
            </div>
            <div>${content}</div>
            ${timestamp ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);">Actualizado: ' + timestamp + '</div>' : ''}
        </div>
    `;
}

function widgetError(msg) {
    return `<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ${msg}</div>`;
}

function errorRow(ticker, name) {
    return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">
            <div>
                <div style="color:var(--color-muted);font-size:13px;">${ticker}</div>
                <div style="color:var(--color-muted);font-size:11px;">${name}</div>
            </div>
            <div style="color:#f23645;font-size:11px;">✗ Sin datos</div>
        </div>
    `;
}
