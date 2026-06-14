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

        // Fila 3 — 2 columnas altura fija con scroll
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + '<div id="widget-spreads" style="display:flex;flex-direction:column;max-height:480px;"></div>'
        + '<div id="widget-reddit"  style="display:flex;flex-direction:column;max-height:480px;"></div>'
        + '</div>'

        // Fila 4 — full width
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
    loadVix(container.querySelector('#widget-vix'));
    loadSpreads(container.querySelector('#widget-spreads'));
    loadReddit(container.querySelector('#widget-reddit'));
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
        el.innerHTML = widgetShell('INDICES ' + tt('ad-line'), 'Mercados principales', rows, data.timestamp);
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
        const content = '<div style="display:flex;flex-direction:column;align-items:center;padding:1rem;">'
            + buildGauge(data.score)
            + '<div style="color:' + color + ';font-size:22px;font-weight:500;letter-spacing:0.1em;margin-top:8px;">' + data.score + '</div>'
            + '<div style="color:' + color + ';font-size:12px;margin-top:2px;letter-spacing:0.05em;">' + data.rating + '</div>'
            + '<div style="display:flex;gap:3rem;margin-top:1rem;font-size:11px;color:var(--color-muted);">'
            + '<div style="text-align:center;"><div>AYER</div><div style="color:var(--color-text);margin-top:2px;font-size:13px;">' + data.prev + '</div></div>'
            + '<div style="text-align:center;"><div>HACE 1 SEM</div><div style="color:var(--color-text);margin-top:2px;font-size:13px;">' + data.week_ago + '</div></div>'
            + '</div></div>';
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
        detail.innerHTML = '<div style="padding:0.75rem;color:#f23645;font-size:11px;">✗ ' + e.message + '</div>';
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

async function loadSpreads(el) {
    el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', loading());
    try {
        const res  = await fetch('/api/v1/market/credit-spreads', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos FRED');

        const chartId = 'spreads-chart-' + Date.now();
        const cards   = data.data.map(s => {
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

        const summary   = '<div style="display:flex;border-bottom:1px solid var(--color-border);">' + cards + '</div>';
        const chartHtml = '<div style="padding:12px;"><canvas id="' + chartId + '" height="100"></canvas></div>';

        el.innerHTML = widgetShell('CREDIT SPREADS ' + tt('credit-spreads'), 'OAS · FRED · ICE BofA', summary + chartHtml, data.timestamp);

        const script  = document.createElement('script');
        script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
        script.onload = function() {
            const ctx = document.getElementById(chartId);
            if (!ctx) return;
            const datasets = data.data.filter(s => s.ok && s.history && s.history.length > 0).map((s, i) => {
                const c = ['#f23645','#00d9ff'][i] || '#888';
                return { label: s.name, data: s.history.map(h => ({ x: h.date, y: h.value })), borderColor: c, backgroundColor: c + '18', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.3 };
            });
            new Chart(ctx, {
                type: 'line', data: { datasets },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: true, position: 'top', labels: { color: '#666', boxWidth: 12, font: { size: 10 } } },
                        tooltip: { backgroundColor: '#111', borderColor: '#333', borderWidth: 1, titleColor: '#aaa', bodyColor: '#ccc' }
                    },
                    scales: {
                        x: { type: 'category', ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 6, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                        y: { ticks: { color: '#555', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
                    }
                }
            });
        };
        document.head.appendChild(script);
    } catch(e) {
        el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', widgetError(e.message));
    }
}

async function loadReddit(el) {
    el.innerHTML = widgetShell('REDDIT PULSE', 'Social buzz · Reddit + StockTwits', loading());
    try {
        const res  = await fetch('/api/v1/market/reddit', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos');
        const sources = data.sources.join(' + ');
        const header  = '<div style="display:grid;grid-template-columns:30px 60px 80px 70px 1fr;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
            + '<div>#</div><div>TICKER</div><div>PRECIO</div><div>BUZZ</div><div>SEÑAL</div>'
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
        el.innerHTML = widgetShell('REDDIT PULSE', sources, header + rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('REDDIT PULSE', 'Social buzz', widgetError(e.message));
    }
}

async function loadBriefing(el) {
    el.innerHTML = widgetShell('NIGHTLY BRIEFING', 'Análisis de mercado · IA', loading());
    try {
        const res  = await fetch('/api/v1/market/briefing', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin briefing');
        const html = renderMarkdown(data.content);
        const updated = data.updated ? '<span style="color:var(--color-muted);font-size:11px;">Generado: ' + data.updated + '</span>' : '';
        el.innerHTML = widgetShell('NIGHTLY BRIEFING', updated, '<div style="padding:1rem 1.25rem;max-height:200px;overflow-y:auto;">' + html + '</div>', data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('NIGHTLY BRIEFING', 'Análisis de mercado · IA', widgetError(e.message));
    }
}

async function loadCalendar(el) {
    el.innerHTML = widgetShell('CALENDARIO ECONÓMICO', 'Esta semana · Hora Madrid', loading());
    try {
        const res  = await fetch('/api/v1/market/calendar', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok || !data.data.length) throw new Error(data.error || 'Sin eventos');
        const impColor = { High: '#f23645', Medium: '#ffb800', Low: '#555' };
        const impLabel = { High: '●●●', Medium: '●●○', Low: '●○○' };
        const header = '<div style="display:grid;grid-template-columns:60px 55px 1fr 50px 80px 80px 80px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
            + '<div>FECHA</div><div>HORA</div><div>EVENTO</div><div>IMP</div><div>ACTUAL</div><div>PREV.</div><div>ESTIMADO</div></div>';
        const rows = data.data.map(ev => {
            const ic = impColor[ev.impact] || '#555';
            const il = impLabel[ev.impact] || '●○○';
            const bg = ev.date === 'HOY' ? 'rgba(0,255,173,0.03)' : 'transparent';
            return '<div style="display:grid;grid-template-columns:60px 55px 1fr 50px 80px 80px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;background:' + bg + ';align-items:center;">'
                + '<div style="color:' + ev.date_color + ';font-size:10px;font-weight:500;">' + ev.date + '</div>'
                + '<div style="color:var(--color-muted);">' + ev.time + '</div>'
                + '<div style="color:var(--color-text);">' + ev.event + '</div>'
                + '<div style="color:' + ic + ';font-size:10px;">' + il + '</div>'
                + '<div style="color:var(--color-accent);text-align:right;">' + ev.actual + '</div>'
                + '<div style="color:var(--color-muted);text-align:right;">' + ev.previous + '</div>'
                + '<div style="color:var(--color-muted);text-align:right;">' + ev.forecast + '</div>'
                + '</div>';
        }).join('');
        el.innerHTML = widgetShell('CALENDARIO ECONÓMICO', 'Esta semana · Hora Madrid', header + rows, data.timestamp);
    } catch(e) {
        el.innerHTML = widgetShell('CALENDARIO ECONÓMICO', 'Esta semana · Hora Madrid', widgetError(e.message));
    }
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
function widgetError(msg) { return '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + msg + '</div>'; }

function errorRow(ticker, name) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div><div style="color:var(--color-muted);font-size:13px;">' + ticker + '</div><div style="color:var(--color-muted);font-size:11px;">' + name + '</div></div>'
        + '<div style="color:#f23645;font-size:11px;">✗ Sin datos</div>'
        + '</div>';
}