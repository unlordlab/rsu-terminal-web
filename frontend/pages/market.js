export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">MARKET</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Dashboard de mercado · Carga modular</div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'
        + '<div id="widget-briefing" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-indices" style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-feargreed" style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-forex" style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-commodities" style="display:flex;flex-direction:column;"></div>'
        + '<div id="widget-sectors" style="grid-column:2/4;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-vix" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-spreads" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-reddit" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '<div id="widget-calendar" style="grid-column:1/-1;display:flex;flex-direction:column;"></div>'
        + '</div>';

    loadBriefing(container.querySelector('#widget-briefing'));
    loadIndices(container.querySelector('#widget-indices'));
    loadFearGreed(container.querySelector('#widget-feargreed'));
    loadForex(container.querySelector('#widget-forex'));
    loadCommodities(container.querySelector('#widget-commodities'));
    loadSectors(container.querySelector('#widget-sectors'));
    loadVix(container.querySelector('#widget-vix'));
    loadSpreads(container.querySelector('#widget-spreads'));
    loadReddit(container.querySelector('#widget-reddit'));
    loadCalendar(container.querySelector('#widget-calendar'));
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
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;height:100%;display:flex;flex-direction:column;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);flex-shrink:0;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + title + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + subtitle + '</div>'
        + '</div>'
        + '<div style="flex:1;overflow-y:auto;">' + content + '</div>'
        + (timestamp ? '<div style="padding:6px 14px;font-size:10px;color:var(--color-muted);border-top:1px solid var(--color-border);flex-shrink:0;">Actualizado: ' + timestamp + '</div>' : '')
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
async function loadCalendar(el) {
    el.innerHTML = widgetShell('CALENDARIO ECONÓMICO', 'Esta semana · Hora Madrid', loading());
    try {
        const res  = await fetch('/api/v1/market/calendar', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok || !data.data.length) throw new Error(data.error || 'Sin eventos');

        const impColor = { High: '#f23645', Medium: '#ffb800', Low: '#555' };
        const impLabel = { High: '●●●', Medium: '●●○', Low: '●○○' };

        const header = '<div style="display:grid;grid-template-columns:60px 55px 1fr 60px 80px 80px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
            + '<div>FECHA</div><div>HORA</div><div>EVENTO</div><div>IMP</div><div>ACTUAL</div><div>PREV.</div><div>ESTIMADO</div>'
            + '</div>';

        const rows = data.data.map(ev => {
            const ic = impColor[ev.impact] || '#555';
            const il = impLabel[ev.impact] || '●○○';
            const isToday = ev.date === 'HOY';
            const bg = isToday ? 'rgba(0,255,173,0.03)' : 'transparent';
            return '<div style="display:grid;grid-template-columns:60px 55px 1fr 60px 80px 80px 80px;gap:8px;padding:9px 14px;border-bottom:1px solid var(--color-border);font-size:12px;background:' + bg + ';align-items:center;">'
                + '<div style="color:' + ev.date_color + ';font-size:11px;font-weight:500;">' + ev.date + '</div>'
                + '<div style="color:var(--color-muted);">' + ev.time + '</div>'
                + '<div style="color:var(--color-text);">' + ev.event + '</div>'
                + '<div style="color:' + ic + ';font-size:10px;letter-spacing:1px;">' + il + '</div>'
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
async function loadVix(el) {
    el.innerHTML = widgetShell('VIX TERM STRUCTURE', 'Curva de futuros · Volatilidad implícita', loading());
    try {
        const res  = await fetch('/api/v1/market/vix', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const labels = data.data.map(d => d.label);
        const values = data.data.map(d => d.value);
        const isContango = data.structure === 'contango';
        const lineColor  = isContango ? '#f23645' : '#00ffad';
        const structureLabel = isContango ? 'CONTANGO' : 'BACKWARDATION';
        const structureColor = isContango ? '#f23645' : '#00ffad';
        const spot = data.spot;
        const diff = data.contango;

        const summary = '<div style="display:flex;gap:2rem;padding:12px 16px;border-bottom:1px solid var(--color-border);font-size:12px;">'
            + '<div><span style="color:var(--color-muted);">VIX SPOT  </span><span style="color:var(--color-text);font-size:16px;margin-left:6px;">' + spot + '</span></div>'
            + '<div><span style="color:var(--color-muted);">ESTRUCTURA  </span><span style="color:' + structureColor + ';margin-left:6px;letter-spacing:0.08em;">' + structureLabel + '</span></div>'
            + '<div><span style="color:var(--color-muted);">SPREAD SPOT-ÚLTIMO  </span><span style="color:' + (diff > 0 ? '#f23645' : '#00ffad') + ';margin-left:6px;">' + (diff > 0 ? '+' : '') + diff + '</span></div>'
            + '</div>';

        const chartId = 'vix-chart-' + Date.now();
        const chartHtml = '<div style="padding:16px;"><canvas id="' + chartId + '" height="120"></canvas></div>';

        el.innerHTML = widgetShell('VIX TERM STRUCTURE', 'Curva de futuros · Volatilidad implícita', summary + chartHtml, data.timestamp);

        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
        script.onload = function() {
            const ctx = document.getElementById(chartId);
            if (!ctx) return;
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'VIX',
                        data: values,
                        borderColor: lineColor,
                        backgroundColor: lineColor + '18',
                        borderWidth: 2,
                        pointBackgroundColor: lineColor,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        fill: true,
                        tension: 0.3,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#111',
                            borderColor: lineColor,
                            borderWidth: 1,
                            titleColor: '#aaa',
                            bodyColor: lineColor,
                            callbacks: {
                                label: ctx => 'VIX: ' + ctx.parsed.y.toFixed(2)
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#555', font: { size: 11 } },
                            grid:  { color: 'rgba(255,255,255,0.04)' }
                        },
                        y: {
                            ticks: { color: '#555', font: { size: 11 } },
                            grid:  { color: 'rgba(255,255,255,0.04)' }
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
async function loadReddit(el) {
    el.innerHTML = widgetShell('REDDIT PULSE', 'Social buzz · Reddit + StockTwits', loading());
    try {
        const res  = await fetch('/api/v1/market/reddit', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos');

        const sources = data.sources.join(' + ');

        const header = '<div style="display:grid;grid-template-columns:40px 70px 90px 80px 1fr 1fr;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
            + '<div>#</div><div>TICKER</div><div>PRECIO</div><div>BUZZ</div><div>SOCIAL HYPE</div><div>SMART MONEY</div>'
            + '</div>';

        const rows = data.data.map((item, i) => {
            const up      = item.change >= 0;
            const chgColor = up ? 'var(--color-accent)' : '#f23645';
            const chgStr  = (up ? '+' : '') + item.change.toFixed(2) + '%';
            const priceStr = item.price ? '$' + item.price.toLocaleString('en-US') : '-';
            const buzzW   = item.buzz + '%';
            const rank    = i + 1;
            const rankColor = rank <= 3 ? 'var(--color-accent)' : 'var(--color-muted)';

            return '<div style="display:grid;grid-template-columns:40px 70px 90px 80px 1fr 1fr;gap:8px;padding:9px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;">'
                + '<div style="color:' + rankColor + ';font-weight:500;">' + rank + '</div>'
                + '<div style="color:var(--color-accent);font-weight:500;letter-spacing:0.05em;">' + item.ticker + '</div>'
                + '<div>'
                + '<div style="color:var(--color-text);">' + priceStr + '</div>'
                + '<div style="color:' + chgColor + ';font-size:10px;">' + chgStr + '</div>'
                + '</div>'
                + '<div>'
                + '<div style="background:var(--color-surface2);border-radius:2px;height:4px;margin-bottom:3px;">'
                + '<div style="height:100%;width:' + buzzW + ';background:var(--color-accent);border-radius:2px;"></div>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;">' + item.buzz + '</div>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;">' + item.social_hype + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;">' + item.smart_money + '</div>'
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

        const lines = data.content.split('\n').filter(l => l.trim());
        const html  = lines.map(line => {
            const t = line.trim();
            if (t.startsWith('# ')) {
                return '<div style="color:var(--color-accent);font-size:15px;font-weight:500;letter-spacing:0.05em;margin:12px 0 6px;text-shadow:var(--glow-text);">'
                    + t.replace(/^#+\s*/, '') + '</div>';
            }
            if (t.startsWith('## ') || t.startsWith('### ')) {
                return '<div style="color:var(--color-secondary);font-size:13px;font-weight:500;margin:10px 0 4px;letter-spacing:0.05em;">'
                    + t.replace(/^#+\s*/, '') + '</div>';
            }
            if (t.startsWith('- ') || t.startsWith('* ')) {
                return '<div style="color:var(--color-text);font-size:12px;padding:3px 0 3px 12px;border-left:2px solid var(--color-border);margin:2px 0;">'
                    + t.replace(/^[-*]\s*/, '') + '</div>';
            }
            if (t.startsWith('**') || t.match(/^[A-Z]{2,}:/)) {
                return '<div style="color:var(--color-text);font-size:12px;font-weight:500;margin:4px 0;">'
                    + t.replace(/\*\*/g, '') + '</div>';
            }
            if (t === '---' || t === '***') {
                return '<div style="border-top:1px solid var(--color-border);margin:10px 0;"></div>';
            }
            if (t.length > 0) {
                return '<div style="color:var(--color-muted);font-size:12px;line-height:1.6;margin:2px 0;">'
                    + t + '</div>';
            }
            return '';
        }).join('');

        const updated = data.updated
            ? '<span style="color:var(--color-muted);font-size:11px;">Generado: ' + data.updated + '</span>'
            : '';

        const content = '<div style="padding:1rem 1.25rem;max-height:300px;overflow-y:auto;">'
            + html
            + '</div>';

        el.innerHTML = widgetShell('NIGHTLY BRIEFING', updated, content, data.timestamp);

    } catch(e) {
        el.innerHTML = widgetShell('NIGHTLY BRIEFING', 'Análisis de mercado · IA', widgetError(e.message));
    }
}
async function loadSpreads(el) {
    el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', loading());
    try {
        const res  = await fetch('/api/v1/market/credit-spreads', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error('Sin datos FRED');

        const chartId = 'spreads-chart-' + Date.now();

        const cards = data.data.map(s => {
            if (!s.ok) return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">' + s.label + ': Sin datos</div>';
            const up    = s.change >= 0;
            const color = up ? '#f23645' : '#00ffad';
            const arrow = up ? '▲' : '▼';
            return '<div style="flex:1;padding:1rem 1.25rem;border-right:1px solid var(--color-border);">'
                + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:6px;letter-spacing:0.05em;">' + s.name + ' · ' + s.label + '</div>'
                + '<div style="display:flex;align-items:baseline;gap:8px;">'
                + '<div style="color:var(--color-text);font-size:22px;">' + s.current.toFixed(2) + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;">%</div>'
                + '</div>'
                + '<div style="color:' + color + ';font-size:11px;margin-top:2px;">' + arrow + ' ' + Math.abs(s.change).toFixed(2) + ' vs anterior</div>'
                + '<div style="margin-top:8px;display:inline-block;padding:2px 8px;border-radius:4px;background:' + s.level_color + '22;color:' + s.level_color + ';font-size:10px;letter-spacing:0.08em;">' + s.level + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">' + s.date + '</div>'
                + '</div>';
        }).join('');

        const summary = '<div style="display:flex;border-bottom:1px solid var(--color-border);">' + cards + '</div>';
        const chartHtml = '<div style="padding:16px;"><canvas id="' + chartId + '" height="120"></canvas></div>';

        el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', summary + chartHtml, data.timestamp);

        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
        script.onload = function() {
            const ctx = document.getElementById(chartId);
            if (!ctx) return;

            const datasets = data.data
                .filter(s => s.ok && s.history && s.history.length > 0)
                .map((s, i) => {
                    const colors = ['#f23645', '#00d9ff'];
                    const c = colors[i] || '#888';
                    return {
                        label:           s.name,
                        data:            s.history.map(h => ({ x: h.date, y: h.value })),
                        borderColor:     c,
                        backgroundColor: c + '18',
                        borderWidth:     1.5,
                        pointRadius:     0,
                        fill:            false,
                        tension:         0.3,
                    };
                });

            new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: {
                    responsive:           true,
                    maintainAspectRatio:  false,
                    interaction:          { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            display:   true,
                            position:  'top',
                            labels: {
                                color:    '#666',
                                boxWidth: 12,
                                font:     { size: 11 },
                            }
                        },
                        tooltip: {
                            backgroundColor: '#111',
                            borderColor:     '#333',
                            borderWidth:     1,
                            titleColor:      '#aaa',
                            bodyColor:       '#ccc',
                        }
                    },
                    scales: {
                        x: {
                            type:   'category',
                            ticks: {
                                color:       '#555',
                                font:        { size: 10 },
                                maxTicksLimit: 8,
                                maxRotation:  0,
                            },
                            grid: { color: 'rgba(255,255,255,0.04)' }
                        },
                        y: {
                            ticks: { color: '#555', font: { size: 11 } },
                            grid:  { color: 'rgba(255,255,255,0.04)' }
                        }
                    }
                }
            });
        };
        document.head.appendChild(script);

    } catch(e) {
        el.innerHTML = widgetShell('CREDIT SPREADS', 'OAS · FRED · ICE BofA', widgetError(e.message));
    }
}