import { tt } from '/components/tooltip.js';
import { onMarketUpdate } from '/core/websocket.js';

if (!document.getElementById('market-live-css')) {
    const s = document.createElement('style');
    s.id = 'market-live-css';
    s.textContent = `
        @keyframes blink-green { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes blink-red   { 0%,100%{opacity:1} 50%{opacity:0.2} }
        .ws-blink-up   { animation: blink-green 0.6s ease 3; }
        .ws-blink-down { animation: blink-red   0.6s ease 3; }
    `;
    document.head.appendChild(s);
}

export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">MARKET</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Dashboard de mercado · Carga modular · Live WS</div>'
        + '</div>'

        // Fila 1 — 3 columnas
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">'
        + '<div id="widget-briefing" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-indices"     style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-feargreed"   style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-forex"       style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-commodities" style="display:flex;flex-direction:column;height:420px;"></div>'
        + '<div id="widget-earnings"    style="grid-column:2/4;display:flex;flex-direction:column;height:420px;"></div>'
        + '<div style="grid-column:1/-1;height:0;"></div>'
        + '</div>'

        // Fila 2 — 2 columnas
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="widget-vix"     style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-sectors" style="display:flex;flex-direction:column;"></div>'
        + '</div>'

        // Fila 2a2 — Composición Sectorial (breadth por sector, ancho completo)
        + '<div style="margin-bottom:1rem;">'
        + '<div id="widget-sector-composition" style="display:flex;flex-direction:column;"></div>'
        + '</div>'

        // Fila 2b — Amplitud de Mercado (Market Breadth + AD Line fusionados)
        + '<div style="margin-bottom:1rem;">'
        + '<div id="widget-breadth" style="display:flex;flex-direction:column;"></div>'
        + '</div>'

        // Fila 2c — VIX Niveles + Cripto
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="widget-vix-levels" style="display:flex;flex-direction:column;height:400px;"></div>'
        + '<div id="widget-crypto"     style="display:flex;flex-direction:column;height:400px;"></div>'
        + '</div>'

        // Fila 3 — 2 columnas altura fija con scroll
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="widget-spreads" style="display:flex;flex-direction:column;max-height:480px;"></div>'
        + '<div id="widget-reddit"  style="display:flex;flex-direction:column;max-height:480px;"></div>'
        + '</div>'

        // Fila 3b — Liquidez (Net Liquidity + M2 vs SPX)
        + '<div style="margin-bottom:1rem;">'
        + '<div id="widget-liquidity" style="display:flex;flex-direction:column;height:520px;"></div>'
        + '</div>'

        // Fila 4 — Fed & Macro
        + '<div style="margin-bottom:1rem;">'
        + '<div id="widget-fed-macro" style="display:flex;flex-direction:column;"></div>'
        + '</div>'

        // Fila 5 — full width
        + '<div style="margin-bottom:1rem;">'
        + '<div id="widget-calendar" style="display:flex;flex-direction:column;"></div>'
        + '</div>';

    loadBriefing(container.querySelector('#widget-briefing'));
    loadIndices(container.querySelector('#widget-indices'));
    loadFearGreed(container.querySelector('#widget-feargreed'));
    loadForex(container.querySelector('#widget-forex'));
    loadCommodities(container.querySelector('#widget-commodities'));
    loadEarnings(container.querySelector('#widget-earnings'));
    loadSectors(container.querySelector('#widget-sectors'), '1d');
    loadSectorComposition(container.querySelector('#widget-sector-composition'));
    loadVix(container.querySelector('#widget-vix'));
    loadBreadth(container.querySelector('#widget-breadth'));
    loadVixLevels(container.querySelector('#widget-vix-levels'));
    loadCrypto(container.querySelector('#widget-crypto'));
    loadSpreads(container.querySelector('#widget-spreads'));
    loadReddit(container.querySelector('#widget-reddit'));
    loadLiquidity(container.querySelector('#widget-liquidity'));
    loadFedMacro(container.querySelector('#widget-fed-macro'));
    loadCalendar(container.querySelector('#widget-calendar'));

    onMarketUpdate('market-page', (data) => {
        updateIndicesWS(data.indices);
        updatePricesWS(data.prices);
    });
}

// ── WS UPDATERS ───────────────────────────────────────────────────────────────

function updateIndicesWS(indices) {
    if (!indices || !indices.length) return;
    indices.forEach(idx => {
        const el = document.querySelector('[data-ws-ticker="' + idx.ticker + '"]');
        if (!el) return;
        const up      = idx.chg >= 0;
        const color   = up ? 'var(--color-accent)' : '#f23645';
        const arrow   = up ? '▲' : '▼';
        const priceEl = el.querySelector('[data-ws-price]');
        const chgEl   = el.querySelector('[data-ws-chg]');
        if (priceEl) {
            priceEl.textContent = idx.price.toLocaleString('en-US');
            priceEl.classList.remove('ws-blink-up','ws-blink-down');
            void priceEl.offsetWidth;
            priceEl.classList.add(up ? 'ws-blink-up' : 'ws-blink-down');
        }
        if (chgEl) {
            chgEl.textContent = arrow + ' ' + Math.abs(idx.chg).toFixed(2) + '%';
            chgEl.style.color = color;
            chgEl.classList.remove('ws-blink-up','ws-blink-down');
            void chgEl.offsetWidth;
            chgEl.classList.add(up ? 'ws-blink-up' : 'ws-blink-down');
        }
    });
}

function updatePricesWS(prices) {
    if (!prices || !prices.length) return;
    prices.forEach(p => {
        const el = document.querySelector('[data-ws-ticker="' + p.name + '"]');
        if (!el) return;
        const up      = p.chg >= 0;
        const color   = up ? 'var(--color-accent)' : '#f23645';
        const arrow   = up ? '▲' : '▼';
        const priceEl = el.querySelector('[data-ws-price]');
        const chgEl   = el.querySelector('[data-ws-chg]');
        if (priceEl) {
            priceEl.textContent = p.price.toLocaleString('en-US');
            priceEl.classList.remove('ws-blink-up','ws-blink-down');
            void priceEl.offsetWidth;
            priceEl.classList.add(up ? 'ws-blink-up' : 'ws-blink-down');
        }
        if (chgEl) {
            chgEl.textContent = arrow + ' ' + Math.abs(p.chg).toFixed(2) + '%';
            chgEl.style.color = color;
            chgEl.classList.remove('ws-blink-up','ws-blink-down');
            void chgEl.offsetWidth;
            chgEl.classList.add(up ? 'ws-blink-up' : 'ws-blink-down');
        }
    });
}

// ── WIDGETS ───────────────────────────────────────────────────────────────────

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
            return wsRow(idx.ticker, idx.name,
                idx.price.toLocaleString('en-US'),
                arrow + ' ' + Math.abs(idx.pct).toFixed(2) + '%',
                color);
        }).join('');
        el.innerHTML = widgetShell('INDICES ' + tt('market-indices'), 'Mercados principales', rows, data.timestamp);
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
        const color   = fgColor(data.score);
        const periodRow = (label, val) =>
            '<div style="text-align:center;"><div>' + label + '</div><div style="color:var(--color-text);margin-top:2px;font-size:13px;">' + (val != null ? val : '—') + '</div></div>';

        const components = data.components || [];
        const compRows = components.map(c => {
            const cColor = fgColor(c.score);
            return '<div style="margin-bottom:8px;">'
                + '<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                + '<span style="color:var(--color-muted);font-size:10px;">' + c.label + '</span>'
                + '<span style="color:' + cColor + ';font-size:10px;font-weight:600;">' + c.score.toFixed(0) + ' · ' + c.rating + '</span>'
                + '</div>'
                + '<div style="width:100%;height:6px;background:var(--color-border);border-radius:3px;overflow:hidden;">'
                + '<div style="height:100%;width:' + Math.min(Math.max(c.score, 0), 100) + '%;background:' + cColor + ';"></div>'
                + '</div>'
                + '<div style="font-size:9px;color:var(--color-muted);margin-top:2px;">' + c.desc + '</div>'
                + '</div>';
        }).join('');

        const content = '<div style="display:flex;flex-direction:column;align-items:center;padding:1rem;">'
            + buildGauge(data.score)
            + '<div style="color:' + color + ';font-size:22px;font-weight:500;letter-spacing:0.1em;margin-top:8px;">' + data.score + '</div>'
            + '<div style="color:' + color + ';font-size:12px;margin-top:2px;letter-spacing:0.05em;">' + data.rating + '</div>'
            + '<div style="display:flex;gap:2rem;margin-top:1rem;font-size:11px;color:var(--color-muted);flex-wrap:wrap;justify-content:center;">'
            + periodRow('AYER', data.prev)
            + periodRow('HACE 1 SEM', data.week_ago)
            + periodRow('HACE 1 MES', data.month_ago)
            + periodRow('HACE 1 AÑO', data.year_ago)
            + '</div>'
            + (components.length ? (
                '<div style="width:100%;margin-top:1.25rem;padding-top:1rem;border-top:1px solid var(--color-border);">'
                + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:10px;text-align:left;">LOS 7 COMPONENTES DEL ÍNDICE ' + tt('fear-greed-components') + '</div>'
                + compRows
                + '</div>'
            ) : '')
            + '</div>';
        el.innerHTML = widgetShell('FEAR & GREED ' + tt('fear-greed'), 'CNN Index', content, data.timestamp);
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
            return wsRow(fx.ticker, fx.name,
                fx.price.toFixed(4),
                arrow + ' ' + Math.abs(fx.pct).toFixed(2) + '%',
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
        if (!data || !data.data) throw new Error('Sin datos');
        const rows = data.data.map(c => {
            if (!c.ok) return errorRow(c.ticker || c.name, c.name);
            const up    = (c.pct || 0) >= 0;
            const color = up ? 'var(--color-accent)' : '#f23645';
            const arrow = up ? '▲' : '▼';
            const prefix = c.prefix || '$';
            const price  = c.price != null ? prefix + Number(c.price).toLocaleString('en-US') : '—';
            const change = arrow + ' ' + Math.abs(c.pct || 0).toFixed(2) + '%';
            return wsRow(c.ticker || c.name, c.name, price, change, color);
        }).join('');
        el.innerHTML = widgetShell('COMMODITIES', 'Futuros', rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('COMMODITIES', 'Futuros', widgetError(e.message));
    }
}

async function loadEarnings(el) {
    if (!el) return;
    el.innerHTML = widgetShell('EARNINGS CALENDAR', 'Próximos 14 días · FMP + Finnhub', loading());
    try {
        const res  = await fetch('/api/v1/market/earnings', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok || !data.data || !data.data.length) throw new Error('Sin earnings próximos');

        const searchBar = '<div style="padding:8px 12px;border-bottom:1px solid var(--color-border);display:flex;gap:8px;">'
            + '<input id="earnings-search" type="text" placeholder="Buscar ticker (AAPL, NVDA...)" style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:5px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;outline:none;">'
            + '<button id="earnings-search-btn" style="background:var(--color-secondary);color:#000;border:none;border-radius:var(--radius);padding:5px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">BUSCAR</button>'
            + '</div>';

        const header = '<div style="display:grid;grid-template-columns:55px 90px 70px 80px 80px;gap:8px;padding:6px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
            + '<div>FECHA</div><div>HORA</div><div>TICKER</div><div>PRECIO</div><div>EPS EST</div>'
            + '</div>';

        const rows = data.data.map(e => {
            const isToday   = e.is_today;
            const bg        = isToday ? 'rgba(0,255,173,0.04)' : 'transparent';
            const dateColor = isToday ? 'var(--color-accent)' : (e.days_out <= 2 ? '#ffb800' : 'var(--color-muted)');
            const isBMO     = (e.time || '').includes('BMO');
            const isAMC     = (e.time || '').includes('AMC');
            const timeColor = isBMO ? '#ffb800' : isAMC ? '#00d9ff' : 'var(--color-muted)';
            const timeBg    = isBMO ? 'rgba(255,184,0,0.1)' : isAMC ? 'rgba(0,217,255,0.1)' : 'transparent';
            const epsStr    = e.eps_est != null ? '$' + Number(e.eps_est).toFixed(2) : '—';
            const priceStr  = e.price ? '$' + Number(e.price).toLocaleString('en-US') : '—';
            return '<div style="display:grid;grid-template-columns:55px 90px 70px 80px 80px;gap:8px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;background:' + bg + ';cursor:pointer;" class="earnings-row" data-ticker="' + e.ticker + '">'
                + '<div style="color:' + dateColor + ';font-weight:' + (isToday ? '600' : '400') + ';">' + (e.date_fmt || e.date || '—') + '</div>'
                + '<div style="background:' + timeBg + ';color:' + timeColor + ';font-size:10px;padding:2px 6px;border-radius:3px;display:inline-block;">' + (e.time || '—') + '</div>'
                + '<div style="color:var(--color-accent);font-weight:500;">' + e.ticker + '</div>'
                + '<div style="color:var(--color-text);">' + priceStr + '</div>'
                + '<div style="color:var(--color-muted);">' + epsStr + '</div>'
                + '</div>';
        }).join('');

        const content = searchBar
            + header
            + '<div style="overflow-y:auto;max-height:280px;" id="earnings-list">' + rows + '</div>'
            + '<div id="earnings-detail" style="border-top:1px solid var(--color-border);"></div>';

        el.innerHTML = widgetShell('EARNINGS CALENDAR', 'Próximos 14 días · FMP + Finnhub', content, data.timestamp);

        // Click en fila → cargar sorpresas
        el.querySelectorAll('.earnings-row').forEach(row => {
            row.addEventListener('mouseenter', () => row.style.background = 'var(--color-surface2,#1a1a1a)');
            row.addEventListener('mouseleave', () => row.style.background = 'transparent');
            row.addEventListener('click', () => loadEarningsSurprise(row.getAttribute('data-ticker'), el));
        });

        // Búsqueda manual
        const searchBtn = el.querySelector('#earnings-search-btn');
        const searchInput = el.querySelector('#earnings-search');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const t = searchInput.value.trim().toUpperCase();
                if (t) loadEarningsSurprise(t, el);
            });
        }
        if (searchInput) {
            searchInput.addEventListener('keydown', e => {
                if (e.key === 'Enter') {
                    const t = searchInput.value.trim().toUpperCase();
                    if (t) loadEarningsSurprise(t, el);
                }
            });
        }

    } catch(e) {
        el.innerHTML = widgetShell('EARNINGS CALENDAR', 'Próximos 14 días', widgetError(e.message));
    }
}

async function loadEarningsSurprise(ticker, container) {
    const detail = container.querySelector('#earnings-detail');
    if (!detail) return;
    detail.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando historial de ' + ticker + '...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/market/earnings/' + ticker, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        const history = data.surprise_history || [];
        const nextDate = data.next_date ? '<span style="color:var(--color-muted);font-size:10px;">Próximo: ' + data.next_date + '</span>' : '';
        const epsEst   = data.eps_est != null ? '<span style="color:var(--color-muted);font-size:10px;margin-left:1rem;">EPS Est: $' + Number(data.eps_est).toFixed(2) + '</span>' : '';

        let html = '<div style="padding:10px 12px;">'
            + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
            + '<span style="color:var(--color-accent);font-size:14px;font-weight:500;">' + ticker + '</span>'
            + nextDate + epsEst
            + '</div>';

        if (history.length) {
            html += '<div style="font-size:10px;color:var(--color-muted);margin-bottom:6px;letter-spacing:0.05em;">HISTORIAL EPS · ÚLTIMOS 4 TRIMESTRES</div>'
                + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">'
                + history.slice(0, 4).map(h => {
                    const beat    = h.actual >= h.estimate;
                    const color   = beat ? 'var(--color-accent)' : '#f23645';
                    const icon    = beat ? '▲ BEAT' : '▼ MISS';
                    const surpStr = (h.surprise > 0 ? '+' : '') + h.surprise + '%';
                    return '<div style="background:' + color + '11;border:1px solid ' + color + '33;border-radius:var(--radius);padding:8px;text-align:center;">'
                        + '<div style="color:var(--color-muted);font-size:9px;margin-bottom:4px;">' + (h.quarter || '') + '</div>'
                        + '<div style="color:' + color + ';font-size:10px;font-weight:500;">' + icon + '</div>'
                        + '<div style="color:var(--color-text);font-size:11px;margin-top:2px;">$' + h.actual + '</div>'
                        + '<div style="color:var(--color-muted);font-size:9px;">Est: $' + h.estimate + '</div>'
                        + '<div style="color:' + color + ';font-size:10px;margin-top:2px;">' + surpStr + '</div>'
                        + '</div>';
                }).join('')
                + '</div>';
        } else {
            html += '<div style="color:var(--color-muted);font-size:11px;">Sin historial de sorpresas disponible.</div>';
        }

        html += '</div>';
        detail.innerHTML = html;

    } catch(e) {
        detail.innerHTML = widgetError(e.message);
    }
}

async function loadSectors(el, period) {
    el.innerHTML = widgetShell('SECTOR PERFORMANCE', 'S&P 500 ETFs', loading());
    try {
        const res  = await fetch('/api/v1/market/sectors?period=' + period, { headers: authHeader() });
        const data = await res.json();
        const max  = Math.max(...data.data.map(s => Math.abs(s.pct)));

        const periodSelector = '<div style="display:flex;gap:4px;padding:8px 14px;border-bottom:1px solid var(--color-border);">'
            + ['1d','1w','1m'].map(p =>
                '<button class="sector-period" data-period="' + p + '" style="'
                + 'background:' + (p === period ? 'var(--color-accent)' : 'transparent') + ';'
                + 'color:' + (p === period ? '#000' : 'var(--color-muted)') + ';'
                + 'border:1px solid ' + (p === period ? 'var(--color-accent)' : 'var(--color-border)') + ';'
                + 'border-radius:3px;padding:3px 10px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">'
                + p.toUpperCase() + '</button>'
            ).join('')
            + '</div>';

        const bars = data.data.map(s => {
            const up     = s.pct >= 0;
            const color  = up ? 'var(--color-accent)' : '#f23645';
            const w      = max > 0 ? Math.abs(s.pct) / max * 100 : 0;
            const pctStr = (s.pct > 0 ? '+' : '') + s.pct + '%';
            return '<div style="display:flex;align-items:center;gap:10px;padding:7px 14px;border-bottom:1px solid var(--color-border);">'
                + '<div style="width:110px;font-size:11px;color:var(--color-text);flex-shrink:0;">' + s.name + '</div>'
                + '<div style="flex:1;background:var(--color-surface2);border-radius:2px;height:5px;overflow:hidden;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '<div style="width:55px;text-align:right;font-size:11px;color:' + color + ';flex-shrink:0;">' + pctStr + '</div>'
                + '</div>';
        }).join('');

        const shell = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);flex-shrink:0;">'
            + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">SECTOR PERFORMANCE</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">S&P 500 ETFs</div>'
            + '</div>'
            + periodSelector
            + '<div style="flex:1;overflow-y:auto;">' + bars + '</div>'
            + '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);flex-shrink:0;">Actualizado: ' + data.timestamp + '</div>'
            + '</div>';

        el.innerHTML = shell;
        el.querySelectorAll('.sector-period').forEach(btn => {
            btn.addEventListener('click', () => loadSectors(el, btn.getAttribute('data-period')));
        });
    } catch(e) {
        el.innerHTML = widgetShell('SECTOR PERFORMANCE', 'S&P 500 ETFs', widgetError(e.message));
    }
}

async function loadSectorComposition(el) {
    el.innerHTML = widgetShell('COMPOSICIÓN SECTORIAL', 'Cestas temáticas · Scan independiente', loading());
    try {
        const res  = await fetch('/api/v1/market/sector-composition', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const s = data.sectors;
        const scoredOnly = s.filter(r => r.avg_score != null);
        const maxScore = Math.max(...scoredOnly.map(r => r.avg_score), 1);

        // ── 4 tarjetas resumen ───────────────────────────────────────────────
        const statCard = (label, value, sub, color) =>
            '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.85rem 1rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:6px;">' + label + '</div>'
            + '<div style="color:' + color + ';font-size:20px;font-weight:500;">' + value + '</div>'
            + (sub ? '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + sub + '</div>' : '')
            + '</div>';

        const stats = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1rem;">'
            + statCard('SECTOR MÁS FUERTE', data.strongest ? data.strongest.sector : '—', data.strongest ? 'Avg score ' + data.strongest.avg_score : '', 'var(--color-accent)')
            + statCard('SECTOR MÁS DÉBIL', data.weakest ? data.weakest.sector : '—', data.weakest ? 'Avg score ' + data.weakest.avg_score : '', '#f23645')
            + statCard('SECTORES MONITORIZADOS', data.sectors_tracked, (data.sectors_empty ? data.sectors_empty + ' sin datos suficientes' : 'Todas con datos'), 'var(--color-secondary)')
            + statCard('UNIVERSO', data.universe_size, 'Tickers con score', 'var(--color-text)')
            + '</div>';

        // ── Tabla principal ──────────────────────────────────────────────────
        const heads = ['#', 'SECTOR', 'CESTA', 'EN TOP 20%', 'AVG SCORE', 'MOMENTUM'];
        const th = heads.map(h =>
            '<th style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;padding:7px 10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap;">' + h + '</th>'
        ).join('');

        const trs = s.map(r => {
            const noData = r.avg_score == null;
            const scoreColor = noData ? 'var(--color-muted)' : (r.avg_score >= 60 ? 'var(--color-accent)' : r.avg_score >= 45 ? '#ffb800' : '#f23645');
            const w = (!noData && maxScore > 0) ? (r.avg_score / maxScore * 100) : 0;
            const momTxt = r.avg_momentum == null ? '—' : (r.avg_momentum >= 0 ? '+' : '') + r.avg_momentum;
            const momColor = r.avg_momentum == null ? 'var(--color-muted)' : r.avg_momentum >= 0 ? 'var(--color-accent)' : '#f23645';
            return '<tr style="border-bottom:1px solid var(--color-border);' + (noData ? 'opacity:0.5;' : '') + '">'
                + '<td style="padding:6px 10px;color:var(--color-muted);font-size:11px;">' + (r.rank || '—') + '</td>'
                + '<td style="padding:6px 10px;color:var(--color-text);font-size:11px;white-space:nowrap;">' + r.sector + '</td>'
                + '<td style="padding:6px 10px;color:var(--color-muted);font-size:11px;">' + r.basket + '</td>'
                + '<td style="padding:6px 10px;color:var(--color-muted);font-size:11px;white-space:nowrap;">' + (noData ? 'Sin datos' : (r.leaders + '/' + r.basket + ' · ' + r.leaders_pct + '%')) + '</td>'
                + '<td style="padding:6px 10px;min-width:90px;">'
                + '<div style="display:flex;align-items:center;gap:6px;">'
                + '<div style="flex:1;background:var(--color-surface2);border-radius:2px;height:5px;overflow:hidden;min-width:50px;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + scoreColor + ';border-radius:2px;"></div>'
                + '</div>'
                + '<span style="color:' + scoreColor + ';font-size:11px;width:30px;text-align:right;">' + (noData ? '—' : r.avg_score) + '</span>'
                + '</div></td>'
                + '<td style="padding:6px 10px;color:' + momColor + ';font-size:11px;">' + momTxt + '</td>'
                + '</tr>';
        }).join('');

        const table = '<div style="overflow-x:auto;max-height:480px;overflow-y:auto;">'
            + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">'
            + '<thead style="position:sticky;top:0;background:var(--color-surface);z-index:1;"><tr>' + th + '</tr></thead>'
            + '<tbody>' + trs + '</tbody>'
            + '</table></div>';

        // ── Top 5 acelerando / desacelerando (por momentum medio del sector) ──
        function trendBox(title, rows, color) {
            if (!rows.length) return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;"><div style="color:' + color + ';font-size:11px;letter-spacing:0.08em;margin-bottom:0.5rem;">' + title + '</div><div style="color:var(--color-muted);font-size:11px;">Sin datos de momentum.</div></div>';
            return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
                + '<div style="color:' + color + ';font-size:11px;letter-spacing:0.08em;margin-bottom:0.5rem;">' + title + '</div>'
                + rows.map(r => {
                    const mc = r.avg_momentum >= 0 ? 'var(--color-accent)' : '#f23645';
                    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                        + '<span style="color:var(--color-text);">' + r.sector + '</span>'
                        + '<span style="color:' + mc + ';">' + (r.avg_momentum >= 0 ? '+' : '') + r.avg_momentum + '</span>'
                        + '</div>';
                }).join('')
                + '</div>';
        }

        const trendRow = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem;">'
            + trendBox('TOP 5 SECTORES ACELERANDO', data.accelerating, 'var(--color-accent)')
            + trendBox('TOP 5 SECTORES DESACELERANDO', data.decelerating, '#f23645')
            + '</div>';

        const note = '<div style="padding:8px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);margin-top:0.75rem;">'
            + 'EN TOP 20% = nº de nombres de la cesta con RS Percentile ≥ 80 sobre el universo temático combinado (~290 tickers) · MOMENTUM = fracción de la cesta acelerando (RS 21d > RS 63d) · Scan independiente, no limitado al S&P 500 · Actualizado: ' + data.timestamp
            + '</div>';

        const shell = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">COMPOSICIÓN SECTORIAL ' + tt('sector-composition') + '</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">29 cestas temáticas</div>'
            + '</div>'
            + stats
            + table
            + trendRow
            + note
            + '</div>';

        el.innerHTML = shell;
    } catch(e) {
        el.innerHTML = widgetShell('COMPOSICIÓN SECTORIAL', 'Breadth por sector', widgetError(e.message));
    }
}

async function loadVix(el) {
    el.innerHTML = widgetShell('VIX TERM STRUCTURE ' + tt('vix-term-structure'), 'Curva de futuros · Volatilidad implícita', loading());
    try {
        const res  = await fetch('/api/v1/market/vix', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const labels      = data.data.map(d => d.label);
        const values      = data.data.map(d => d.value);
        const isContango  = data.structure === 'contango';
        const lineColor   = isContango ? '#00ffad' : '#f23645';
        const structLabel = isContango ? 'Contango' : 'Backwardation';
        const structColor = isContango ? '#00ffad' : '#f23645';
        const structDesc  = isContango
            ? 'Típico en mercados tranquilos · Favorable para dip buying'
            : 'Señal de estrés · Posible suelo de mercado';

        const header = '<div style="display:flex;align-items:center;gap:1.5rem;padding:10px 16px;border-bottom:1px solid var(--color-border);font-size:12px;flex-wrap:wrap;">'
            + '<span style="color:var(--color-muted);">VIX SPOT</span>'
            + '<span style="color:var(--color-text);font-size:20px;font-weight:500;">' + data.spot + '</span>'
            + '<span style="color:var(--color-muted);margin-left:0.5rem;">ESTRUCTURA</span>'
            + '<span style="color:' + structColor + ';font-weight:500;">' + structLabel.toUpperCase() + '</span>'
            + '<span style="color:var(--color-muted);margin-left:0.5rem;">SPREAD</span>'
            + '<span style="color:' + (data.contango > 0 ? '#f23645' : '#00ffad') + ';font-weight:500;">' + (data.contango > 0 ? '+' : '') + data.contango + '</span>'
            + '</div>';

        const chartId = 'vix-chart-' + Date.now();
        const footer  = '<div style="text-align:center;padding:8px;font-size:11px;color:' + structColor + ';border-top:1px solid var(--color-border);">'
            + structLabel + ': ' + structDesc
            + '</div>';

        const content = header
            + '<div style="padding:16px 16px 8px;flex:1;"><canvas id="' + chartId + '" height="180"></canvas></div>'
            + footer;

        el.innerHTML = widgetShell('VIX TERM STRUCTURE ' + tt('vix-term-structure'), 'Curva de futuros · Volatilidad implícita', content, data.timestamp);

        const script  = document.createElement('script');
        script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
        script.onload = function() {
            const ctx = document.getElementById(chartId);
            if (!ctx) return;
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label:                'VIX',
                        data:                 values,
                        borderColor:          lineColor,
                        backgroundColor:      lineColor + '22',
                        borderWidth:          2.5,
                        pointBackgroundColor: lineColor,
                        pointBorderColor:     '#0d0d0d',
                        pointBorderWidth:     2,
                        pointRadius:          6,
                        pointHoverRadius:     9,
                        fill:                 true,
                        tension:              0.4,
                    }]
                },
                options: {
                    responsive:          true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#0d0d0d',
                            borderColor:     lineColor,
                            borderWidth:     1,
                            titleColor:      '#888',
                            bodyColor:       lineColor,
                            padding:         10,
                            callbacks: {
                                title: items => items[0].label,
                                label: item  => 'VIX: ' + item.parsed.y.toFixed(2),
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#666', font: { size: 11 } },
                            grid:  { color: 'rgba(255,255,255,0.05)' },
                        },
                        y: {
                            ticks: { color: '#666', font: { size: 11 } },
                            grid:  { color: 'rgba(255,255,255,0.05)' },
                            suggestedMin: Math.min(...values) - 1,
                            suggestedMax: Math.max(...values) + 1,
                        }
                    }
                }
            });
        };
        document.head.appendChild(script);
    } catch(e) {
        el.innerHTML = widgetShell('VIX TERM STRUCTURE', 'Curva de futuros · Volatilidad implícita', widgetError(e.message));
    }
}

async function loadBreadth(el) {
    el.innerHTML = widgetShell('AMPLITUD DE MERCADO ' + tt('market-breadth'), 'SMA50/200 · RSI · McClellan · % S&amp;P500 · NH-NL · A/D NYSE', loading());
    try {
        const res  = await fetch('/api/v1/market/breadth', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok && data.price == null) throw new Error(data.error || 'Sin datos');

        // Guarda defensiva: _sanitize_breadth() en el backend convierte NaN/Inf en null
        // incluso cuando ok=True (p.ej. si rolling(50).mean() produce NaN por huecos en
        // el histórico de yfinance), así que cualquiera de estos campos puede llegar null
        // sin que la guarda anterior lo capture. Sin esto, .toFixed() sobre null rompe el widget.
        // Nota: mcclellan puede ser null legítimamente (histórico A/D insuficiente para
        // EMA39) sin que eso invalide el resto del widget — se muestra "N/D" en ese caso.
        if (data.price == null || data.sma50 == null || data.rsi == null || data.pct_above_sma50 == null) {
            throw new Error('Datos incompletos de mercado (posible hueco en histórico). Reintentando en el próximo ciclo.');
        }

        const trendColor    = data.trend === 'ALCISTA' ? '#00ffad' : '#f23645';
        const strengthColor = data.strength === 'FUERTE' ? '#00ffad' : '#ff9800';
        const sma50Color    = data.above_sma50 ? '#00ffad' : '#f23645';
        const sma200Color   = data.above_sma200 ? '#00ffad' : '#f23645';
        const goldenColor   = data.golden_cross ? '#00ffad' : '#f23645';
        const goldenText    = data.golden_cross ? 'GOLDEN CROSS ✓' : 'DEATH CROSS ✗';
        const rsi           = data.rsi;
        const rsiColor      = rsi > 70 ? '#f23645' : (rsi < 30 ? '#00ffad' : '#ff9800');
        const mcAvailable   = data.mcclellan != null;
        const mcColor       = mcAvailable ? (data.mcclellan > 0 ? '#00ffad' : '#f23645') : 'var(--color-muted)';
        const mcRealData    = data.ad_real_data === true;
        const mcBadge       = !mcAvailable ? ''
            : (mcRealData
                ? '<span style="color:#00ffad;font-size:9px;">[REAL]</span>'
                : '<span style="color:#ff9800;font-size:9px;">[PROXY SPY]</span>');
        const pctColor      = data.pct_above_sma50 >= 60 ? '#00ffad' : (data.pct_above_sma50 <= 40 ? '#f23645' : '#ff9800');
        const sma200Str     = data.sma200 == null ? 'N/D (insuf. datos)' : '$' + data.sma200.toFixed(2);
        const sma200ColorUse= data.sma200 == null ? 'var(--color-muted)' : sma200Color;
        const isRealBreadth = data.breadth_source === 'sp500';
        const breadthBadge  = isRealBreadth
            ? '<span style="color:#00ffad;font-size:9px;">[S&amp;P 500 REAL]</span>'
            : '<span style="color:#ff9800;font-size:9px;">[PROXY 11 ETFs]</span>';
        const nhNlAvailable = data.nh_nl != null;
        const nhNlColor     = nhNlAvailable ? (data.nh_nl >= 0 ? '#00ffad' : '#f23645') : 'var(--color-muted)';

        // Variación semanal — helper genérico para los tres indicadores con
        // histórico suficiente (McClellan, % sobre SMA50, NH-NL)
        const wowBadge = (value, suffix) => {
            if (value == null) return '';
            const up    = value >= 0;
            const color = up ? '#00ffad' : '#f23645';
            const arrow = up ? '▲' : '▼';
            return '<span style="color:' + color + ';font-size:9px;margin-left:6px;">' + arrow + ' ' + (up ? '+' : '') + value + (suffix || '') + ' sem.</span>';
        };

        const metricBox = (label, valueHtml) =>
            '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
            + '<span style="color:var(--color-muted);font-size:11px;">' + label + '</span>'
            + '<span style="font-size:12px;font-weight:600;">' + valueHtml + '</span>'
            + '</div>';

        const content = '<div style="padding:12px 14px;">'
            + metricBox('Precio SPY', '<span style="color:var(--color-text);cursor:pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'" onclick="window.__navigate(\'/research?ticker=SPY\')">$' + data.price.toFixed(2) + '</span>')
            + metricBox('SMA 50', '<span style="color:' + sma50Color + ';">$' + data.sma50.toFixed(2) + '</span>')
            + metricBox('SMA 200', '<span style="color:' + sma200ColorUse + ';">' + sma200Str + '</span>')
            + '<div style="background:' + goldenColor + '11;border:1px solid ' + goldenColor + '44;border-radius:6px;padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
            + '<span style="color:var(--color-muted);font-size:11px;">Señal</span>'
            + '<span style="color:' + goldenColor + ';font-size:12px;font-weight:600;">' + goldenText + '</span>'
            + '</div>'

            // McClellan (real cuando A/D es real — EMA19/EMA39 sobre avance/declive neto NYSE)
            + '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px 12px;margin-bottom:6px;">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            + '<span style="color:var(--color-muted);font-size:11px;">Oscilador McClellan ' + tt('mcclellan-oscillator') + '</span>'
            + '<span style="color:' + mcColor + ';font-size:11px;font-weight:600;">' + (mcAvailable ? ((data.mcclellan >= 0 ? '+' : '') + data.mcclellan.toFixed(1) + ' · ' + data.mcclellan_state) : 'N/D') + wowBadge(data.mcclellan_wow, '') + '</span>'
            + '</div>'
            + '<div style="width:100%;height:8px;background:var(--color-border);border-radius:4px;overflow:hidden;">'
            + '<div style="height:100%;width:' + (mcAvailable ? Math.min(Math.abs(data.mcclellan)/100*100, 100) : 0) + '%;background:' + mcColor + ';"></div>'
            + '</div>'
            + '<div style="font-size:9px;color:var(--color-muted);margin-top:3px;">&gt;+70 sobrecompra de amplitud · &lt;-70 sobreventa de amplitud ' + mcBadge + '</div>'
            + '</div>'

            // % S&P 500 sobre SMA50 (real, desde el scan nocturno de 500 tickers)
            + '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px 12px;margin-bottom:6px;">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            + '<span style="color:var(--color-muted);font-size:11px;">% S&amp;P 500 sobre SMA50 ' + tt('breadth-pct-sma50') + '</span>'
            + '<span style="color:' + pctColor + ';font-size:12px;font-weight:600;">' + data.pct_above_sma50.toFixed(0) + '%' + wowBadge(data.pct_above_sma50_wow, 'pp') + '</span>'
            + '</div>'
            + '<div style="width:100%;height:8px;background:var(--color-border);border-radius:4px;overflow:hidden;">'
            + '<div style="height:100%;width:' + data.pct_above_sma50 + '%;background:' + pctColor + ';"></div>'
            + '</div>'
            + '<div style="font-size:9px;color:var(--color-muted);margin-top:3px;">' + data.sectors_checked + ' tickers evaluados ' + breadthBadge + '</div>'
            + '</div>'

            // New Highs - New Lows (52 semanas, desde el scan nocturno de 500 tickers)
            + '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px 12px;margin-bottom:10px;">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            + '<span style="color:var(--color-muted);font-size:11px;">New Highs − New Lows ' + tt('nh-nl') + '</span>'
            + '<span style="color:' + nhNlColor + ';font-size:12px;font-weight:600;">' + (nhNlAvailable ? ((data.nh_nl >= 0 ? '+' : '') + data.nh_nl) : 'N/D') + wowBadge(data.nh_nl_wow, '') + '</span>'
            + '</div>'
            + '<div style="font-size:9px;color:var(--color-muted);margin-top:3px;">' + (nhNlAvailable ? (data.new_highs + ' nuevos máximos · ' + data.new_lows + ' nuevos mínimos (52 semanas) <span style="color:#00ffad;">[S&amp;P 500 REAL]</span>') : 'Requiere el scan nocturno del Scanner — no disponible todavía') + '</div>'
            + '</div>'

            // RSI gauge
            + '<div style="margin-bottom:14px;">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            + '<span style="color:var(--color-muted);font-size:11px;">RSI (14)</span>'
            + '<span style="color:' + rsiColor + ';font-size:11px;font-weight:600;">' + rsi.toFixed(1) + ' — ' + data.rsi_state + '</span>'
            + '</div>'
            + '<div style="width:100%;height:10px;border-radius:5px;background:linear-gradient(to right, #00ffad 0%, #ff9800 50%, #f23645 100%);position:relative;">'
            + '<div style="position:absolute;top:-3px;left:' + Math.min(rsi,100) + '%;width:3px;height:16px;background:#fff;border-radius:2px;transform:translateX(-50%);"></div>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;font-size:8px;color:var(--color-muted);margin-top:2px;"><span>0</span><span>30</span><span>50</span><span>70</span><span>100</span></div>'
            + '</div>'

            + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px;">'
            + '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;">Tendencia</div>'
            + '<div style="color:' + trendColor + ';font-size:12px;font-weight:600;">' + data.trend + '</div>'
            + '</div>'
            + '<div style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:8px;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;">Fuerza</div>'
            + '<div style="color:' + strengthColor + ';font-size:12px;font-weight:600;">' + data.strength + '</div>'
            + '</div>'
            + '</div>';

        // ── Línea A/D (fusionada aquí — antes era un widget separado) ──────────
        let adSectionHtml = '';
        let chartId = null;
        if (data.ad_ok) {
            const isReal   = data.ad_real_data;
            const badgeText  = isReal ? '[NYSE REAL]' : '[PROXY SPY]';
            const badgeColor = isReal ? '#00ffad' : '#ff9800';
            const netColor   = data.current_net >= 0 ? '#00ffad' : '#f23645';
            const netArrow   = data.current_net >= 0 ? '▲' : '▼';
            chartId = 'ad-chart-' + Date.now();

            const pill = (label, valueHtml) =>
                '<span style="display:inline-flex;align-items:center;gap:4px;background:var(--color-bg);border:1px solid var(--color-border);border-radius:4px;padding:3px 8px;font-size:10px;font-family:var(--font-mono);margin-right:6px;margin-bottom:6px;">'
                + label + ' ' + valueHtml + '</span>';

            adSectionHtml = '<div style="padding:0 14px 14px;border-top:1px solid var(--color-border);padding-top:12px;">'
                + '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
                + '<span style="color:var(--color-muted);font-size:11px;">Línea A/D ' + tt('ad-line') + '</span>'
                + '<span style="font-size:10px;color:' + badgeColor + ';font-family:var(--font-mono);">' + badgeText + '</span>'
                + '</div>'
                + '<div style="margin-bottom:10px;">'
                + pill('AVANZAN', '<span style="color:#00ffad;font-weight:600;">▲' + data.current_adv.toLocaleString('en-US') + '</span>')
                + pill('DECLINAN', '<span style="color:#f23645;font-weight:600;">▼' + data.current_dec.toLocaleString('en-US') + '</span>')
                + pill('NETO', '<span style="color:' + netColor + ';font-weight:600;">' + netArrow + (data.current_net >= 0 ? '+' : '') + data.current_net.toLocaleString('en-US') + '</span>')
                + '</div>'
                + '<div style="position:relative;height:200px;"><canvas id="' + chartId + '"></canvas></div>'
                + '</div>';
        }

        el.innerHTML = widgetShell('AMPLITUD DE MERCADO ' + tt('market-breadth'), 'SMA50/200 · RSI · McClellan · % S&amp;P500 · NH-NL · A/D NYSE', content + adSectionHtml, data.timestamp);

        if (chartId) {
            const history = data.ad_history || [];
            const buildAdChart = function() {
                const ctx = document.getElementById(chartId);
                if (!ctx || !window.Chart) return;
                const labels  = history.map(h => h.date.slice(5));
                const adVals  = history.map(h => h.ad);
                const spyVals = history.map(h => h.spy);
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            { label: 'S&P 500', data: spyVals, yAxisID: 'y1', borderColor: '#3b82f6', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
                            { label: 'Línea A/D (K)', data: adVals, yAxisID: 'y2', borderColor: '#f23645', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
                        ]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, labels: { color: '#888', font: { size: 9 }, boxWidth: 14 } },
                            tooltip: { backgroundColor: '#0d0d0d', borderWidth: 1 },
                        },
                        scales: {
                            x:  { ticks: { color: '#666', font: { size: 8 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                            y1: { position: 'left',  ticks: { color: '#3b82f6', font: { size: 8 } }, grid: { display: false } },
                            y2: { position: 'right', ticks: { color: '#f23645', font: { size: 8 } }, grid: { display: false } },
                        }
                    }
                });
            };
            if (window.Chart) {
                buildAdChart();
            } else {
                const script  = document.createElement('script');
                script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
                script.onload = buildAdChart;
                document.head.appendChild(script);
            }
        }
    } catch(e) {
        el.innerHTML = widgetShell('AMPLITUD DE MERCADO', 'SMA50/200 · RSI · McClellan · % S&amp;P500 · NH-NL · A/D NYSE', widgetError(e.message));
    }
}


async function loadVixLevels(el) {
    el.innerHTML = widgetShell('VIX NIVELES ' + tt('vix-levels'), 'Gauge de zonas · Histórico 6 meses', loading());
    try {
        const res  = await fetch('/api/v1/market/vix-levels', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const changeColor = data.change >= 0 ? '#f23645' : '#00ffad';
        const chartId = 'vixlvl-chart-' + Date.now();

        // 5 zone gauge: <12 / 12-20 / 20-25 / 25-35 / 35+
        const zones = [
            { max: 12, color: '#3b82f6', label: 'Complacencia' },
            { max: 20, color: '#00ffad', label: 'Normal' },
            { max: 25, color: '#ff9800', label: 'Precaución' },
            { max: 35, color: '#ff6b35', label: 'Miedo' },
            { max: 60, color: '#f23645', label: 'Pánico' },
        ];
        const gaugeMax = 60;
        const markerPct = Math.min(data.current / gaugeMax, 1) * 100;

        let gaugeBands = '';
        let prevPct = 0;
        zones.forEach(z => {
            const pct = Math.min(z.max / gaugeMax, 1) * 100;
            gaugeBands += '<div style="position:absolute;left:' + prevPct + '%;width:' + (pct - prevPct) + '%;height:100%;background:' + z.color + ';opacity:0.55;"></div>';
            prevPct = pct;
        });

        const content = '<div style="padding:12px 14px;">'
            + '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:4px;">'
            + '<span style="font-size:28px;font-weight:600;color:' + data.zone_color + ';cursor:pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'" onclick="window.__navigate(\'/research?ticker=%5EVIX\')">' + data.current.toFixed(2) + '</span>'
            + '<span style="color:' + changeColor + ';font-size:13px;font-weight:600;">' + (data.change >= 0 ? '+' : '') + data.change.toFixed(2) + ' (' + (data.pct >= 0 ? '+' : '') + data.pct.toFixed(2) + '%)</span>'
            + '<span style="background:' + data.zone_color + '18;color:' + data.zone_color + ';border:1px solid ' + data.zone_color + '50;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;margin-left:auto;">' + data.zone + '</span>'
            + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:10px;">' + data.zone_label + '</div>'

            // Gauge
            + '<div style="position:relative;width:100%;height:16px;border-radius:8px;overflow:hidden;margin-bottom:4px;">' + gaugeBands
            + '<div style="position:absolute;top:-3px;left:' + markerPct + '%;width:3px;height:22px;background:#fff;border-radius:2px;transform:translateX(-50%);box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;font-size:8px;color:var(--color-muted);margin-bottom:14px;"><span>0</span><span>12</span><span>20</span><span>25</span><span>35</span><span>60+</span></div>'

            + '<div style="position:relative;height:170px;"><canvas id="' + chartId + '"></canvas></div>'
            + '</div>';

        el.innerHTML = widgetShell('VIX NIVELES ' + tt('vix-levels'), 'Gauge de zonas · Histórico 6 meses', content, data.timestamp);

        function buildChart() {
            const ctx = document.getElementById(chartId);
            if (!ctx || !window.Chart) return;
            const labels = data.history.map(h => h.date.slice(5));
            const values = data.history.map(h => h.value);
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'VIX', data: values,
                        borderColor: data.zone_color, backgroundColor: data.zone_color + '15',
                        borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.25,
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#666', font: { size: 8 }, maxTicksLimit: 6 }, grid: { display: false } },
                        y: { ticks: { color: '#666', font: { size: 8 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    }
                }
            });
        }

        if (window.Chart) { buildChart(); }
        else {
            const script  = document.createElement('script');
            script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
            script.onload = buildChart;
            document.head.appendChild(script);
        }
    } catch(e) {
        el.innerHTML = widgetShell('VIX NIVELES', 'Gauge de zonas · Histórico 6 meses', widgetError(e.message));
    }
}

async function loadCrypto(el) {
    el.innerHTML = widgetShell('CRIPTOMONEDAS ' + tt('crypto-prices'), 'Top 6 · Fear &amp; Greed cripto', loading());
    try {
        const [cryptoRes, fgRes] = await Promise.all([
            fetch('/api/v1/market/crypto', { headers: authHeader() }),
            fetch('/api/v1/market/crypto-fear-greed', { headers: authHeader() }),
        ]);
        const cryptoData = await cryptoRes.json();
        const fgData      = await fgRes.json();
        if (!cryptoData.ok) throw new Error('Sin datos');

        // Aislado en su propio try/catch: si el endpoint de fuerza relativa falla
        // (ej. CoinGecko no responde, ruta no desplegada aún), el resto del
        // widget (Fear&Greed + lista fija de 6) sigue funcionando igual.
        let rsData = null;
        try {
            const rsRes = await fetch('/api/v1/market/crypto-rs?top_n=5', { headers: authHeader() });
            rsData = await rsRes.json();
        } catch (rsErr) {
            rsData = { ok: false, error: 'No se pudo contactar con /crypto-rs: ' + rsErr.message };
        }

        const fgColor = fgData.value >= 75 ? '#00ffad' : fgData.value >= 55 ? '#7fd858' : fgData.value >= 45 ? '#ff9800' : fgData.value >= 25 ? '#ff6b35' : '#f23645';
        const fgChangeColor = fgData.change >= 0 ? '#00ffad' : '#f23645';

        const rows = cryptoData.data.map(c => {
            if (!c.ok) return errorRow(c.ticker, c.name);
            const up         = c.pct >= 0;
            const color      = up ? 'var(--color-accent)' : '#f23645';
            const arrow      = up ? '▲' : '▼';
            const priceStr   = c.price >= 1
                ? '$' + c.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : '$' + c.price.toFixed(4);
            const fullTicker = c.ticker + '-USD'; // research espera el par completo (ej. BTC-USD), igual que Forex muestra EUR/USD
            return wsRow(fullTicker, c.name,
                priceStr,
                arrow + ' ' + Math.abs(c.pct).toFixed(2) + '%',
                color);
        }).join('');

        const fgBlock = '<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
            + '<div style="width:48px;height:48px;border-radius:50%;border:3px solid ' + fgColor + ';display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
            + '<span style="color:' + fgColor + ';font-size:15px;font-weight:700;">' + fgData.value + '</span>'
            + '</div>'
            + '<div>'
            + '<div style="color:' + fgColor + ';font-size:12px;font-weight:600;">' + fgData.classification + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">Fear &amp; Greed Cripto ' + tt('crypto-fear-greed')
            + ' · <span style="color:' + fgChangeColor + ';">' + (fgData.change >= 0 ? '+' : '') + fgData.change + ' vs ayer</span></div>'
            + '</div>'
            + '</div>';

        const rsBlock = (() => {
            if (!rsData || !rsData.ok) {
                const errMsg = (rsData && rsData.error) ? rsData.error : 'Sin respuesta del servidor';
                return '<div style="padding:8px 14px;border-bottom:1px solid var(--color-border);">'
                    + '<div style="color:var(--color-secondary);font-size:10px;letter-spacing:.08em;margin-bottom:4px;">🔥 TOP 5 FUERZA RELATIVA · 30D</div>'
                    + '<div style="color:#f23645;font-size:11px;">Error: ' + errMsg + '</div>'
                    + '</div>';
            }
            if (!rsData.data || !rsData.data.length) {
                return '<div style="padding:8px 14px;border-bottom:1px solid var(--color-border);">'
                    + '<div style="color:var(--color-secondary);font-size:10px;letter-spacing:.08em;margin-bottom:4px;">🔥 TOP 5 FUERZA RELATIVA · 30D</div>'
                    + '<div style="color:var(--color-muted);font-size:11px;">Sin datos disponibles.</div>'
                    + '</div>';
            }
            return '<div style="padding:8px 14px;border-bottom:1px solid var(--color-border);">'
            + '<div style="color:var(--color-secondary);font-size:10px;letter-spacing:.08em;margin-bottom:6px;">🔥 TOP 5 FUERZA RELATIVA · 30D</div>'
            + rsData.data.map(c => {
                const color = c.pct_30d >= 0 ? 'var(--color-accent)' : '#f23645';
                const arrow = c.pct_30d >= 0 ? '▲' : '▼';
                const priceStr = c.price >= 1
                    ? '$' + c.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : c.price >= 0.01
                        ? '$' + c.price.toFixed(4)
                        : '$' + c.price.toFixed(8);
                return '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:11px;">'
                    + '<span style="color:var(--color-muted);width:16px;display:inline-block;">' + c.rank + '</span>'
                    + '<span class="ticker-link" style="flex:1;margin:0 6px;" onclick="window.__navigate(\'/research?ticker=' + c.ticker + '-USD\')">' + c.ticker + '</span>'
                    + '<span style="color:var(--color-text);margin-right:8px;">' + priceStr + '</span>'
                    + '<span style="color:' + color + ';font-weight:500;">' + arrow + ' ' + Math.abs(c.pct_30d).toFixed(2) + '%</span>'
                    + '</div>';
            }).join('')
            + '</div>';
        })();

        const content = fgBlock + rows + rsBlock;

        el.innerHTML = widgetShell('CRIPTOMONEDAS ' + tt('crypto-prices'), 'Top 6 · Fear &amp; Greed cripto', content, cryptoData.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('CRIPTOMONEDAS', 'Top 6 · Fear &amp; Greed cripto', widgetError(e.message));
    }
}

async function loadSpreads(el) {
    el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', loading());
    try {
        const res  = await fetch('/api/v1/market/credit-spreads', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos FRED');

        const cards = data.data.map(s => {
            if (!s.ok) return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">' + s.label + ': Sin datos</div>';
            const up    = s.change >= 0;
            const color = up ? '#f23645' : '#00ffad';
            const arrow = up ? '▲' : '▼';
            return '<div style="flex:1;padding:0.75rem 1rem;border-right:1px solid var(--color-border);">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">' + s.name + ' · ' + s.label + '</div>'
                + '<div style="color:var(--color-text);font-size:20px;">' + s.current.toFixed(2) + '<span style="color:var(--color-muted);font-size:10px;margin-left:2px;">%</span></div>'
                + '<div style="color:' + color + ';font-size:10px;margin-top:2px;">' + arrow + ' ' + Math.abs(s.change).toFixed(2) + ' vs anterior</div>'
                + '<div style="margin-top:6px;display:inline-block;padding:1px 6px;border-radius:3px;background:' + s.level_color + '22;color:' + s.level_color + ';font-size:10px;">' + s.level + '</div>'
                + '</div>';
        }).join('');

        const summary = '<div style="display:flex;border-bottom:1px solid var(--color-border);">' + cards + '</div>';

        const frameId  = 'spreads-tv-' + Date.now();
        const tvUrl    = function(symbol) {
            return 'https://s.tradingview.com/widgetembed/?frameElementId=' + frameId
                + '&symbol=' + symbol
                + '&interval=D&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es';
        };

        const tabs = '<div style="display:flex;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);">'
            + '<button class="spreads-tab" data-symbol="FRED:BAMLH0A0HYM2" onclick="window.__spreadsSwitch(this,\'' + frameId + '\')" style="background:var(--color-accent);color:#000;border:none;border-radius:3px;padding:3px 10px;font-size:10px;cursor:pointer;">HIGH YIELD</button>'
            + '<button class="spreads-tab" data-symbol="FRED:BAMLC0A0CM" onclick="window.__spreadsSwitch(this,\'' + frameId + '\')" style="background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:3px;padding:3px 10px;font-size:10px;cursor:pointer;">INVESTMENT GRADE</button>'
            + '</div>';

        const chartHtml = '<div style="height:260px;">'
            + '<iframe id="' + frameId + '" src="' + tvUrl('FRED:BAMLH0A0HYM2') + '"'
            + ' style="width:100%;height:100%;border:none;" allowtransparency="true" frameborder="0" scrolling="no"></iframe>'
            + '</div>';

        el.innerHTML = widgetShell('CREDIT SPREADS ' + tt('credit-spreads'), 'OAS · FRED · ICE BofA', summary + tabs + chartHtml, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', widgetError(e.message));
    }
}

window.__spreadsSwitch = function(btn, frameId) {
    const symbol = btn.getAttribute('data-symbol');
    const iframe = document.getElementById(frameId);
    if (iframe) {
        iframe.src = 'https://s.tradingview.com/widgetembed/?frameElementId=' + frameId
            + '&symbol=' + symbol
            + '&interval=D&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es';
    }
    const siblings = btn.parentElement.querySelectorAll('.spreads-tab');
    siblings.forEach(function(b) {
        b.style.background = 'transparent';
        b.style.color = 'var(--color-muted)';
        b.style.border = '1px solid var(--color-border)';
    });
    btn.style.background = 'var(--color-accent)';
    btn.style.color = '#000';
    btn.style.border = 'none';
};

window.__fedMacroTvSwitch = function(btn, frameId) {
    const symbol = btn.getAttribute('data-symbol');
    const iframe = document.getElementById(frameId);
    if (iframe) {
        iframe.src = 'https://s.tradingview.com/widgetembed/?frameElementId=' + frameId
            + '&symbol=' + symbol
            + '&interval=M&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es';
    }
    const siblings = btn.parentElement.querySelectorAll('.fedmacro-tv-tab');
    siblings.forEach(function(b) {
        b.style.background = 'transparent';
        b.style.color = 'var(--color-muted)';
        b.style.border = '1px solid var(--color-border)';
    });
    btn.style.background = 'var(--color-accent)';
    btn.style.color = '#000';
    btn.style.border = 'none';
};

async function loadReddit(el) {
    el.innerHTML = widgetShell('REDDIT PULSE ' + tt('reddit-pulse'), 'Social buzz · Reddit + StockTwits', loading());
    try {
        const res  = await fetch('/api/v1/market/reddit', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos');
        const sources = data.sources.join(' + ');
        const header  = '<div style="display:grid;grid-template-columns:30px 60px 80px 70px 1fr;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
            + '<div>#</div><div>TICKER</div><div>PRECIO</div><div>BUZZ ' + tt('social-buzz') + '</div><div>SEÑAL ' + tt('social-signal') + '</div>'
            + '</div>';
        const rows = data.data.map((item, i) => {
            const up       = item.change >= 0;
            const chgColor = up ? 'var(--color-accent)' : '#f23645';
            const chgStr   = (up ? '+' : '') + item.change.toFixed(2) + '%';
            const priceStr = item.price ? '$' + item.price.toLocaleString('en-US') : '-';
            const rank     = i + 1;
            return '<div style="display:grid;grid-template-columns:30px 60px 80px 70px 1fr;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<div style="color:' + (rank <= 3 ? 'var(--color-accent)' : 'var(--color-muted)') + ';font-weight:500;">' + rank + '</div>'
                + '<div onclick="goToResearch(\'' + item.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + item.ticker + '</div>'
                + '<div><div style="color:var(--color-text);">' + priceStr + '</div><div style="color:' + chgColor + ';font-size:10px;">' + chgStr + '</div></div>'
                + '<div><div style="background:var(--color-surface2);border-radius:2px;height:4px;margin-bottom:2px;"><div style="height:100%;width:' + item.buzz + '%;background:var(--color-accent);border-radius:2px;"></div></div><div style="color:var(--color-muted);font-size:10px;">' + item.buzz + '</div></div>'
                + '<div style="color:var(--color-muted);font-size:10px;">' + item.social_hype + '</div>'
                + '</div>';
        }).join('');
        el.innerHTML = widgetShell('REDDIT PULSE ' + tt('reddit-pulse'), sources, header + rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('REDDIT PULSE ' + tt('reddit-pulse'), 'Social buzz', widgetError(e.message));
    }
}

async function loadBriefing(el) {
    el.innerHTML = widgetShell('RESUMEN DE MERCADO DIARIO', 'Análisis de mercado · IA', loading());
    try {
        const res  = await fetch('/api/v1/market/briefing', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin briefing');
        const html    = renderMarkdown(data.content);
        const updated = data.updated ? 'Generado: ' + data.updated : '';

        // Header con botón expandir
        const header = '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);flex-shrink:0;">'
            + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">RESUMEN DE MERCADO DIARIO</div>'
            + '<div style="display:flex;align-items:center;gap:10px;">'
            + '<span style="color:var(--color-muted);font-size:11px;">' + updated + '</span>'
            + '<button id="briefing-expand-btn" title="Leer completo" style="'
            +   'background:rgba(0,255,173,0.08);border:1px solid rgba(0,255,173,0.3);'
            +   'color:var(--color-accent);border-radius:50%;width:22px;height:22px;'
            +   'cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;'
            +   'transition:all 0.2s;font-family:var(--font-mono);line-height:1;padding:0;flex-shrink:0;">+</button>'
            + '</div>'
            + '</div>';

        el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
            + header
            + '<div style="flex:1;overflow:hidden;">'
            + '<div style="padding:1rem 1.25rem;max-height:200px;overflow-y:auto;mask-image:linear-gradient(to bottom,black 60%,transparent 100%);-webkit-mask-image:linear-gradient(to bottom,black 60%,transparent 100%);">' + html + '</div>'
            + '</div>'
            + (data.timestamp ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);flex-shrink:0;">Actualizado: ' + data.timestamp + '</div>' : '')
            + '</div>';

        // Bind expand button → open tooltip modal with full briefing
        const btn = el.querySelector('#briefing-expand-btn');
        if (btn) {
            btn.addEventListener('mouseenter', () => { btn.style.background = 'rgba(0,255,173,0.18)'; btn.style.borderColor = 'var(--color-accent)'; });
            btn.addEventListener('mouseleave', () => { btn.style.background = 'rgba(0,255,173,0.08)'; btn.style.borderColor = 'rgba(0,255,173,0.3)'; });
            btn.addEventListener('click', () => {
                // Re-use the tooltip modal system
                if (window.Tooltip && typeof window.Tooltip.openModal === 'function') {
                    window.Tooltip.openModal({ title: 'RESUMEN DE MERCADO DIARIO — Análisis completo', long: data.content });
                } else {
                    // Fallback: inject modal directly
                    openBriefingModal(data.content, html);
                }
            });
        }
    } catch(e) {
        el.innerHTML = widgetShell('RESUMEN DE MERCADO DIARIO', 'Análisis de mercado · IA', widgetError(e.message));
    }
}

function openBriefingModal(rawContent, htmlContent) {
    let overlay = document.getElementById('briefing-modal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'briefing-modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;padding:1.5rem;';
        overlay.innerHTML = '<div id="briefing-modal" style="background:var(--color-surface);border:1px solid var(--color-secondary,#00d9ff);border-radius:10px;padding:1.5rem;max-width:720px;width:100%;max-height:85vh;display:flex;flex-direction:column;box-shadow:0 0 40px rgba(0,217,255,0.15);">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;padding-bottom:0.75rem;border-bottom:1px solid var(--color-border);">'
            + '<div style="color:var(--color-secondary,#00d9ff);font-size:15px;letter-spacing:0.08em;font-family:var(--font-mono);">RESUMEN DE MERCADO DIARIO — Análisis completo</div>'
            + '<button id="briefing-modal-close" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:all 0.2s;">✕</button>'
            + '</div>'
            + '<div id="briefing-modal-body" style="overflow-y:auto;flex:1;color:var(--color-muted);font-size:13px;line-height:1.8;"></div>'
            + '</div>';
        document.body.appendChild(overlay);
        document.getElementById('briefing-modal-close').addEventListener('click', () => { overlay.remove(); document.body.style.overflow = ''; });
        overlay.addEventListener('click', e => { if (e.target === overlay) { overlay.remove(); document.body.style.overflow = ''; } });
        document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { overlay.remove(); document.body.style.overflow = ''; document.removeEventListener('keydown', esc); } });
    }
    document.getElementById('briefing-modal-body').innerHTML = htmlContent;
    document.body.style.overflow = 'hidden';
}
async function loadLiquidity(el) {
    el.innerHTML = widgetShell('LIQUIDEZ ' + tt('liquidity-overview'), 'Net Liquidity · M2 · Overlay SPX', loading());
    try {
        const res  = await fetch('/api/v1/market/liquidity', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos de liquidez');

        const nl  = data.net_liquidity || {};
        const m2  = data.m2 || {};
        const spx = data.spx || [];
        const corr = data.correlation;

        const nlChgColor = (nl.w_change || 0) >= 0 ? 'var(--color-accent)' : '#f23645';
        const nlChgStr   = nl.w_change != null ? (nl.w_change > 0 ? '+' : '') + nl.w_change + 'B' : 'N/D';
        const m2ChgColor = (m2.yoy_pct || 0) >= 0 ? 'var(--color-accent)' : '#f23645';
        const m2YoyStr   = m2.yoy_pct != null ? (m2.yoy_pct > 0 ? '+' : '') + m2.yoy_pct + '% YoY' : 'N/D';
        const corrColor  = corr == null ? 'var(--color-muted)' : (corr >= 0.5 ? 'var(--color-accent)' : (corr <= -0.2 ? '#f23645' : '#ffb800'));
        const corrStr    = corr != null ? corr.toFixed(2) : 'N/D';

        const cardsSection = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;padding:1rem;border-bottom:1px solid var(--color-border);">'

            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">NET LIQUIDITY ' + tt('fed-net-liquidity') + '</div>'
            + '<div style="color:var(--color-text);font-size:20px;font-weight:500;">$' + (nl.current != null ? nl.current.toFixed(2) + 'T' : 'N/D') + '</div>'
            + '<div style="color:' + nlChgColor + ';font-size:10px;margin-top:4px;">Δ Semanal: ' + nlChgStr + '</div>'
            + '</div>'

            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">M2 MONEY SUPPLY ' + tt('m2-money-supply') + '</div>'
            + '<div style="color:var(--color-text);font-size:20px;font-weight:500;">$' + (m2.current != null ? m2.current.toFixed(2) + 'T' : 'N/D') + '</div>'
            + '<div style="color:' + m2ChgColor + ';font-size:10px;margin-top:4px;">' + m2YoyStr + '</div>'
            + '</div>'

            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">CORRELACIÓN NET LIQ. ↔ SPX ' + tt('liquidity-correlation') + '</div>'
            + '<div style="color:' + corrColor + ';font-size:20px;font-weight:500;">' + corrStr + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">Últimos ~2 años, semanal</div>'
            + '</div>'

            + '</div>';

        const chartId = 'liquidity-chart-' + Date.now();
        const chartSection = '<div style="padding:1rem;flex:1;display:flex;flex-direction:column;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:0.5rem;">NET LIQUIDITY (verde) · M2 (cian, escala propia) · S&P 500 (ámbar, eje der) — cada serie con su propia escala para ver la variación real de cada una</div>'
            + '<div style="flex:1;min-height:0;position:relative;"><canvas id="' + chartId + '"></canvas></div>'
            + '</div>';

        const footerNote = '<div style="padding:0.6rem 1rem;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);">'
            + '⚡ Fuente: FRED (WALCL, WTREGEN, RRPONTSYD, WM2NS) + Yahoo Finance (^GSPC) · Net Liquidity y M2 semanal/mensual, alineados por fecha más cercana'
            + '</div>';

        el.innerHTML = widgetShell('LIQUIDEZ ' + tt('liquidity-overview'), 'Net Liquidity · M2 · Overlay SPX', cardsSection + chartSection + footerNote, data.timestamp);

        // Renderizar gráfico de doble eje
        const renderChart = () => {
            const ctx = document.getElementById(chartId);
            if (!ctx || !window.Chart) return;

            // Unificar fechas: usamos las fechas de Net Liquidity como eje base (más granular, semanal)
            const nlHist  = nl.history || [];
            const m2Hist  = m2.history || [];
            const m2Map   = {};
            m2Hist.forEach(h => { m2Map[h.date] = h.value; });
            const spxMap  = {};
            spx.forEach(s => { spxMap[s.date] = s.value; });

            const labels = nlHist.map(h => h.date);
            const nlData = nlHist.map(h => h.value);

            // Para M2 (mensual) y SPX (semanal), buscar el valor más cercano hacia atrás por cada fecha de NL
            function nearestValue(map, sortedDates, targetDate) {
                if (map[targetDate] != null) return map[targetDate];
                let best = null;
                for (const d of sortedDates) {
                    if (d <= targetDate) best = map[d];
                    else break;
                }
                return best;
            }
            const m2Dates  = Object.keys(m2Map).sort();
            const spxDates = Object.keys(spxMap).sort();
            const m2Data   = labels.map(d => nearestValue(m2Map, m2Dates, d));
            const spxData  = labels.map(d => nearestValue(spxMap, spxDates, d));

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels.map(d => d.substring(5)),
                    datasets: [
                        { label: 'Net Liquidity ($T)', data: nlData,  borderColor: '#00ffad', backgroundColor: 'transparent', borderWidth: 1.8, pointRadius: 0, yAxisID: 'yLeft', tension: 0.25 },
                        { label: 'M2 ($T)',             data: m2Data,  borderColor: '#00d9ff', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, yAxisID: 'yMid',  tension: 0.25, borderDash: [4,3] },
                        { label: 'S&P 500',              data: spxData, borderColor: '#ffb800', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, yAxisID: 'yRight', tension: 0.25 },
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#888', font: { size: 10 } } },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { ticks: { color: '#555', font: { size: 8 }, maxTicksLimit: 10, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                        // Net Liquidity (~$5-7T) y M2 (~$20-23T) difieren ~4x en magnitud — comparten
                        // escala los aplanaría visualmente, así que cada uno tiene su propio eje autoescalado.
                        yLeft:  { position: 'left',  ticks: { color: '#00ffad', font: { size: 9 }, callback: v => '$' + v.toFixed(1) + 'T' }, grid: { color: 'rgba(255,255,255,0.03)' } },
                        yMid:   { display: false },
                        yRight: { position: 'right', ticks: { color: '#ffb800', font: { size: 9 } }, grid: { display: false } },
                    }
                }
            });
        };

        if (!window.Chart) {
            const s = document.createElement('script');
            s.src   = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
            s.onload = renderChart;
            document.head.appendChild(s);
        } else {
            setTimeout(renderChart, 50);
        }

    } catch(e) {
        el.innerHTML = widgetShell('LIQUIDEZ ' + tt('liquidity-overview'), 'Net Liquidity · M2 · Overlay SPX', widgetError(e.message));
    }
}

async function loadFedMacro(el) {
    el.innerHTML = widgetShell('FED & MACRO', 'Balance Fed · Curva de Tipos · Indicadores FRED', loading());
    try {
        const res  = await fetch('/api/v1/market/fed-macro', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const b = data.balance    || {};
        const y = data.yields     || {};
        const ind = data.indicators || {};

        // ── BALANCE FED ───────────────────────────────────────────────────────
        const balColor  = b.color || '#ffb800';
        const wChgColor = (b.w_change || 0) > 0 ? '#00ffad' : (b.w_change || 0) < 0 ? '#f23645' : '#888';
        const wChgStr   = b.w_change != null ? (b.w_change > 0 ? '+' : '') + b.w_change + 'B' : 'N/D';
        const mChgStr   = b.m_change != null ? (b.m_change > 0 ? '+' : '') + b.m_change + 'B' : 'N/D';

        const balSection = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;padding:1rem;border-bottom:1px solid var(--color-border);">'

            // Status
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid ' + balColor + '44;border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">POLÍTICA FED ' + tt('fed-balance') + '</div>'
            + '<div style="color:' + balColor + ';font-size:20px;font-weight:500;">' + (b.status || 'N/D') + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">' + (b.date || '') + '</div>'
            + '</div>'

            // Balance total
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">BALANCE TOTAL (WALCL) ' + tt('fed-balance-total') + '</div>'
            + '<div style="color:var(--color-text);font-size:18px;font-weight:500;">' + (b.total || 'N/D') + '</div>'
            + '<div style="color:' + wChgColor + ';font-size:10px;margin-top:4px;">Δ Semanal: ' + wChgStr + '</div>'
            + '</div>'

            // Liquidez neta
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">LIQ. NETA (Bal−TGA−RRP) ' + tt('fed-net-liquidity') + '</div>'
            + '<div style="color:var(--color-text);font-size:18px;font-weight:500;">' + (b.net_liq || 'N/D') + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">TGA: ' + (b.tga || 'N/D') + ' · RRP: ' + (b.rrp || 'N/D') + '</div>'
            + '</div>'

            // Cambio mensual
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">Δ MENSUAL BALANCE ' + tt('fed-monthly-change') + '</div>'
            + '<div style="color:' + wChgColor + ';font-size:18px;font-weight:500;">' + mChgStr + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">vs hace 5 semanas</div>'
            + '</div>'

            + '</div>';

        // Sparkline balance
        const history = b.history || [];
        let sparkHtml = '';
        if (history.length >= 4) {
            const chartId = 'fed-bal-chart-' + Date.now();
            sparkHtml = '<div style="padding:0 1rem 0.5rem;">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">Balance Fed últimas 24 semanas (Trillones $)</div>'
                + '<div style="height:60px;"><canvas id="' + chartId + '" height="60"></canvas></div>'
                + '</div>';
            setTimeout(() => {
                const ctx = document.getElementById(chartId);
                if (!ctx || !window.Chart) return;
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels:   history.map(h => h.date.substring(5)),
                        datasets: [{ data: history.map(h => h.value), borderColor: balColor, backgroundColor: balColor + '22', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: true, aspectRatio: 5,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#555', font: { size: 8 }, maxTicksLimit: 6, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                            y: { ticks: { color: '#555', font: { size: 8 }, callback: v => '$' + v.toFixed(1) + 'T' }, grid: { color: 'rgba(255,255,255,0.03)' } }
                        }
                    }
                });
            }, 300);
        }

        // ── CURVA DE TIPOS ────────────────────────────────────────────────────
        const sp10_2  = y.spread_10_2;
        const inverted = y.inverted;
        const spColor  = inverted ? '#f23645' : '#00ffad';
        const spLabel  = inverted ? '⚠ INVERTIDA' : '✓ NORMAL';
        const spDesc   = inverted
            ? 'Curva invertida — históricamente precede recesión 6-18 meses'
            : 'Curva normal — expectativas de crecimiento económico saludable';

        const yieldPoints = [
            { label: '3M', val: y.Y3M },
            { label: '2Y', val: y.Y2Y },
            { label: '5Y', val: y.Y5Y },
            { label: '10Y', val: y.Y10Y },
            { label: '30Y', val: y.Y30Y },
        ].filter(p => p.val);

        const yieldBars = yieldPoints.map(p => {
            const maxY = Math.max(...yieldPoints.map(x => x.val));
            const w    = maxY > 0 ? (p.val / maxY) * 100 : 0;
            return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">'
                + '<div style="width:28px;color:var(--color-muted);font-size:10px;text-align:right;flex-shrink:0;">' + p.label + '</div>'
                + '<div style="flex:1;background:var(--color-bg,#0a0a0a);border-radius:2px;height:8px;">'
                + '<div style="height:100%;width:' + w.toFixed(1) + '%;background:' + spColor + ';border-radius:2px;"></div>'
                + '</div>'
                + '<div style="width:40px;color:var(--color-text);font-size:11px;text-align:right;flex-shrink:0;">' + p.val.toFixed(2) + '%</div>'
                + '</div>';
        }).join('');

        const yieldsSection = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;padding:1rem;border-bottom:1px solid var(--color-border);">'

            // Curva visual
            + '<div>'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:0.75rem;">CURVA DE TIPOS US TREASURY ' + tt('yield-curve') + '</div>'
            + yieldBars
            + '</div>'

            // Spread + estado
            + '<div style="display:flex;flex-direction:column;gap:8px;">'
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid ' + spColor + '44;border-radius:var(--radius);padding:0.75rem;text-align:center;">'
            + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">SPREAD 10Y − 2Y ' + tt('treasury-spread') + '</div>'
            + '<div style="color:' + spColor + ';font-size:22px;font-weight:500;">' + (sp10_2 != null ? (sp10_2 >= 0 ? '+' : '') + sp10_2.toFixed(2) + '%' : 'N/D') + '</div>'
            + '<div style="color:' + spColor + ';font-size:10px;font-weight:500;margin-top:4px;">' + spLabel + '</div>'
            + '</div>'
            + '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;line-height:1.6;">' + spDesc + '</div>'
            + '</div>'
            + '</div>'

            + '</div>';

        // ── INDICADORES FRED ──────────────────────────────────────────────────
        const fedFunds    = ind.fed_funds;
        const cpi         = ind.cpi_yoy;
        const unemployment = ind.unemployment;
        const corePce     = ind.core_pce;

        function indCard(label, obj, unit, tooltip_key) {
            if (!obj) return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">' + label + '</div>'
                + '<div style="color:var(--color-muted);font-size:14px;">N/D</div>'
                + '</div>';
            const val   = obj.value;
            const chg   = obj.chg;
            const yoy   = obj.yoy;
            const date  = (obj.date || '').substring(0, 7);
            const up    = chg >= 0;
            const color = up ? '#f23645' : '#00ffad'; // para macro: subida = malo generalmente
            const arrow = up ? '▲' : '▼';
            return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">' + label + (tooltip_key ? ' ' + tt(tooltip_key) : '') + '</div>'
                + '<div style="color:var(--color-text);font-size:18px;font-weight:500;">' + val.toFixed(2) + '<span style="color:var(--color-muted);font-size:10px;"> ' + unit + '</span></div>'
                + (yoy != null ? '<div style="color:' + color + ';font-size:10px;margin-top:2px;">' + arrow + ' ' + Math.abs(yoy).toFixed(2) + '% YoY</div>' : '<div style="color:' + color + ';font-size:10px;margin-top:2px;">' + arrow + ' ' + Math.abs(chg).toFixed(3) + '</div>')
                + '<div style="color:var(--color-muted);font-size:9px;margin-top:2px;">' + date + '</div>'
                + '</div>';
        }

        // Fed Funds tiene color inverso (subida de tipos no es siempre malo)
        function fedFundsCard(obj) {
            if (!obj) return indCard('FED FUNDS RATE', null, '%', null);
            const postura = obj.value >= 4.5 ? 'RESTRICTIVA' : obj.value >= 3 ? 'NEUTRAL' : 'EXPANSIVA';
            const pColor  = obj.value >= 4.5 ? '#f23645' : obj.value >= 3 ? '#ffb800' : '#00ffad';
            return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid ' + pColor + '44;border-radius:var(--radius);padding:0.75rem;text-align:center;">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">FED FUNDS RATE ' + tt('fed-funds-rate') + '</div>'
                + '<div style="color:var(--color-text);font-size:18px;font-weight:500;">' + obj.value.toFixed(2) + '<span style="color:var(--color-muted);font-size:10px;"> %</span></div>'
                + '<div style="color:' + pColor + ';font-size:10px;font-weight:500;margin-top:4px;">' + postura + '</div>'
                + '<div style="color:var(--color-muted);font-size:9px;margin-top:2px;">' + (obj.date || '').substring(0, 7) + '</div>'
                + '</div>';
        }

        const indicatorsSection = '<div style="padding:1rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:0.75rem;">INDICADORES MACROECONÓMICOS · FRED</div>'
            + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;">'
            + fedFundsCard(fedFunds)
            + indCard('IPC YoY', cpi, 'Index', 'cpi-yoy')
            + indCard('DESEMPLEO', unemployment, '%', 'unemployment-rate')
            + indCard('PCE CORE', corePce, 'Index', 'core-pce')
            + '</div>'
            + '<div style="margin-top:0.75rem;padding:0.6rem 0.75rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);font-size:10px;color:var(--color-muted);">'
            + '⚡ Fuente: FRED (Federal Reserve Bank of St. Louis) · CSV público sin API key · Actualizado cada 30 min'
            + '</div>'
            + '</div>';

        // ── GRÁFICO TRADINGVIEW — series FRED con pestañas ──────────────────────
        const tvFrameId = 'fedmacro-tv-' + Date.now();
        const tvSeries = [
            { symbol: 'FRED:FEDFUNDS',  label: 'FED FUNDS' },
            { symbol: 'FRED:CPIAUCSL',  label: 'IPC' },
            { symbol: 'FRED:UNRATE',    label: 'DESEMPLEO' },
            { symbol: 'FRED:PCEPI',     label: 'PCE' },
        ];
        const tvUrl = (symbol) => 'https://s.tradingview.com/widgetembed/?frameElementId=' + tvFrameId
            + '&symbol=' + symbol
            + '&interval=M&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es';
        const tvTabs = tvSeries.map((s, i) =>
            '<button class="fedmacro-tv-tab" data-symbol="' + s.symbol + '" onclick="window.__fedMacroTvSwitch(this,\'' + tvFrameId + '\')" style="background:' + (i === 0 ? 'var(--color-accent)' : 'transparent') + ';color:' + (i === 0 ? '#000' : 'var(--color-muted)') + ';border:' + (i === 0 ? 'none' : '1px solid var(--color-border)') + ';border-radius:3px;padding:3px 10px;font-size:10px;cursor:pointer;margin-right:6px;">' + s.label + '</button>'
        ).join('');
        const tvSection = '<div style="padding:0 1rem 1rem;border-top:1px solid var(--color-border);padding-top:1rem;">'
            + '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
            + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">GRÁFICO HISTÓRICO · TRADINGVIEW ' + tt('fed-macro-chart') + '</span>'
            + '</div>'
            + '<div style="margin-bottom:8px;">' + tvTabs + '</div>'
            + '<div style="height:280px;">'
            + '<iframe id="' + tvFrameId + '" src="' + tvUrl(tvSeries[0].symbol) + '" style="width:100%;height:100%;border:none;" allowtransparency="true" frameborder="0" scrolling="no"></iframe>'
            + '</div>'
            + '</div>';

        const content = balSection + sparkHtml + yieldsSection + indicatorsSection + tvSection;
        el.innerHTML  = widgetShell('FED & MACRO', 'Balance Fed · Curva de Tipos · Indicadores FRED', content, data.timestamp);

        // Cargar Chart.js si no está y renderizar sparkline
        if (history.length >= 4 && !window.Chart) {
            const s  = document.createElement('script');
            s.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
            document.head.appendChild(s);
        }

    } catch(e) {
        el.innerHTML = widgetShell('FED & MACRO', 'Balance Fed · Curva de Tipos · FRED', widgetError(e.message));
    }
}
function flagEmoji(countryCode) {
    if (!countryCode || countryCode.length !== 2) return '';
    const cc = countryCode.toUpperCase();
    if (!/^[A-Z]{2}$/.test(cc)) return '';
    const points = [...cc].map(c => 127397 + c.charCodeAt(0));
    return String.fromCodePoint(...points);
}

function loadCalendar(el) {
    el.innerHTML = widgetShell('CALENDARIO ECONÓMICO ' + tt('economic-calendar'), 'TradingView · Hora local', '<div id="tv-events-container" style="height:600px;"></div>');
    const container = el.querySelector('#tv-events-container');
    if (!container) return;

    const widgetWrap = document.createElement('div');
    widgetWrap.className = 'tradingview-widget-container';
    widgetWrap.style.height = '100%';

    const widgetInner = document.createElement('div');
    widgetInner.className = 'tradingview-widget-container__widget';
    widgetWrap.appendChild(widgetInner);

    const script = document.createElement('script');
    script.type  = 'text/javascript';
    script.src   = 'https://s3.tradingview.com/external-embedding/embed-widget-events.js';
    script.async = true;
    script.text  = JSON.stringify({
        colorTheme: 'dark',
        isTransparent: true,
        width: '100%',
        height: '100%',
        locale: 'es',
        importanceFilter: '-1,0,1',
        countryFilter: 'us,eu,gb,jp,cn,de,fr,ca,au,ch,es'
    });
    widgetWrap.appendChild(script);

    container.appendChild(widgetWrap);
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function wsRow(ticker, name, price, change, color) {
    return '<div data-ws-ticker="' + ticker + '" style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div>'
        + '<div onclick="goToResearch(\'' + ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-size:13px;font-weight:500;">' + ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + name + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div data-ws-price style="color:var(--color-text);font-size:14px;">' + price + '</div>'
        + '<div data-ws-chg  style="color:' + color + ';font-size:11px;">' + change + '</div>'
        + '</div>'
        + '</div>';
}

function widgetShell(title, subtitle, content, timestamp) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);flex-shrink:0;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + title + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + subtitle + '</div>'
        + '</div>'
        + '<div style="flex:1;overflow-y:auto;">' + content + '</div>'
        + (timestamp ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);flex-shrink:0;">Actualizado: ' + timestamp + '</div>' : '')
        + '</div>';
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

function buildGauge(score) {
    // El arco va de 180° (izquierda, score=0) a 0° (derecha, score=100)
    // Usamos coordenadas polares desde el centro (80,80), radio 60
    // Ángulo en radianes: 180° - (score/100 * 180°) convertido a rad
    const deg = 180 - (score / 100) * 180;  // 0→180°, 100→0°
    const rad = deg * Math.PI / 180;
    const cx  = 80, cy = 80, r = 60;
    const nx  = cx + r * Math.cos(rad);
    const ny  = cy - r * Math.sin(rad);  // invertir Y porque SVG Y crece hacia abajo

    // Color de la aguja según score
    const needleColor = fgColor(score);

    return '<svg width="180" height="100" viewBox="0 0 180 100">'
        + '<defs>'
        + '<linearGradient id="fg-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        + '<stop offset="0%"   stop-color="#f23645"/>'
        + '<stop offset="25%"  stop-color="#ff8c00"/>'
        + '<stop offset="50%"  stop-color="#ffb800"/>'
        + '<stop offset="75%"  stop-color="#90ee90"/>'
        + '<stop offset="100%" stop-color="#00ffad"/>'
        + '</linearGradient>'
        + '</defs>'
        // Arco de fondo
        + '<path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="#1a1a1a" stroke-width="14" stroke-linecap="round"/>'
        // Arco de color
        + '<path d="M20,80 A60,60 0 0,1 140,80" fill="none" stroke="url(#fg-grad)" stroke-width="14" stroke-linecap="round"/>'
        // Aguja
        + '<line x1="' + cx + '" y1="' + cy + '" x2="' + nx.toFixed(1) + '" y2="' + ny.toFixed(1) + '" stroke="' + needleColor + '" stroke-width="2.5" stroke-linecap="round"/>'
        // Centro
        + '<circle cx="' + cx + '" cy="' + cy + '" r="4" fill="' + needleColor + '"/>'
        // Labels extremos
        + '<text x="14" y="95" fill="#f23645" font-size="9" font-family="monospace">0</text>'
        + '<text x="136" y="95" fill="#00ffad" font-size="9" font-family="monospace">100</text>'
        + '</svg>';
}
function renderMarkdown(text) {
    if (!text) return '';
    const lines  = text.split('\n');
    let html     = '';
    let inTable  = false;
    let tableRows = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const t    = line.trim();

        // Tablas
        if (t.startsWith('|')) {
            if (!inTable) { inTable = true; tableRows = []; }
            tableRows.push(t);
            continue;
        } else if (inTable) {
            inTable = false;
            html += renderTable(tableRows);
            tableRows = [];
        }

        // Headers
        if (t.startsWith('### ')) {
            html += '<div style="color:var(--color-secondary);font-size:12px;font-weight:600;margin:10px 0 4px;letter-spacing:0.05em;">' + escMD(t.replace(/^###\s*/,'')) + '</div>';
        } else if (t.startsWith('## ')) {
            html += '<div style="color:var(--color-accent);font-size:13px;font-weight:600;margin:14px 0 5px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + escMD(t.replace(/^##\s*/,'')) + '</div>';
        } else if (t.startsWith('# ')) {
            html += '<div style="color:var(--color-accent);font-size:15px;font-weight:600;margin:16px 0 6px;letter-spacing:0.1em;text-shadow:var(--glow-text);">' + escMD(t.replace(/^#\s*/,'')) + '</div>';
        }
        // Bullets
        else if (t.startsWith('- ') || t.startsWith('* ')) {
            html += '<div style="display:flex;gap:8px;padding:3px 0 3px 8px;font-size:11px;">'
                + '<span style="color:var(--color-accent);flex-shrink:0;">▸</span>'
                + '<span style="color:var(--color-text);line-height:1.6;">' + formatInline(t.replace(/^[-*]\s*/,'')) + '</span>'
                + '</div>';
        }
        // Numerados
        else if (/^\d+\.\s/.test(t)) {
            const num = t.match(/^(\d+)\./)[1];
            html += '<div style="display:flex;gap:8px;padding:3px 0 3px 8px;font-size:11px;">'
                + '<span style="color:var(--color-accent);flex-shrink:0;min-width:16px;">' + num + '.</span>'
                + '<span style="color:var(--color-text);line-height:1.6;">' + formatInline(t.replace(/^\d+\.\s*/,'')) + '</span>'
                + '</div>';
        }
        // Separador
        else if (t === '---' || t === '***') {
            html += '<div style="border-top:1px solid var(--color-border);margin:10px 0;"></div>';
        }
        // Línea vacía
        else if (t === '') {
            html += '<div style="height:6px;"></div>';
        }
        // Párrafo normal
        else {
            html += '<div style="color:var(--color-muted);font-size:11px;line-height:1.7;margin:2px 0;">' + formatInline(t) + '</div>';
        }
    }

    // Cerrar tabla si queda abierta
    if (inTable && tableRows.length) html += renderTable(tableRows);

    return html;
}

function renderTable(rows) {
    if (rows.length < 2) return '';
    const headers = rows[0].split('|').filter(c => c.trim()).map(c => c.trim());
    const dataRows = rows.slice(2); // skip separator row

    let html = '<div style="overflow-x:auto;margin:8px 0;">'
        + '<table style="width:100%;border-collapse:collapse;font-size:10px;">'
        + '<thead><tr>'
        + headers.map(h => '<th style="padding:6px 10px;border-bottom:1px solid var(--color-accent);color:var(--color-accent);text-align:left;letter-spacing:0.05em;white-space:nowrap;">' + escMD(h) + '</th>').join('')
        + '</tr></thead><tbody>';

    dataRows.forEach((row, i) => {
        const cells = row.split('|').filter(c => c.trim() !== undefined).slice(1, -1).map(c => c.trim());
        if (!cells.length) return;
        const bg = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)';
        html += '<tr style="background:' + bg + ';">'
            + cells.map(c => '<td style="padding:5px 10px;border-bottom:1px solid var(--color-border);color:var(--color-text);line-height:1.5;">' + formatInline(c) + '</td>').join('')
            + '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
}

function formatInline(text) {
    return escMD(text)
        .replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--color-text);">$1</strong>')
        .replace(/\*(.+?)\*/g,     '<em style="color:var(--color-secondary);">$1</em>')
        .replace(/`(.+?)`/g,       '<code style="background:var(--color-surface2);padding:1px 4px;border-radius:3px;font-size:10px;color:var(--color-accent);">$1</code>');
}

function escMD(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
function loading()        { return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando...</div>'; }
function widgetError(msg) {
    const isRateLimit = /demasiadas peticiones|rate limit|máximo \d+ requests/i.test(msg || '');
    if (isRateLimit) {
        return '<div style="padding:1rem;color:#ffb800;font-size:12px;display:flex;align-items:center;gap:6px;">'
            + '<span style="font-size:14px;">⏱</span><span>' + msg + '</span></div>';
    }
    return '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + msg + '</div>';
}

function errorRow(ticker, name) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div><div style="color:var(--color-muted);font-size:13px;">' + ticker + '</div><div style="color:var(--color-muted);font-size:11px;">' + name + '</div></div>'
        + '<div style="color:#f23645;font-size:11px;">✗ Sin datos</div>'
        + '</div>';
}