export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">CARTERA</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Portfolio tracker · Google Sheets feed</div>'
        + '</div>'
        + '<div id="cartera-content"><div style="color:var(--color-muted);font-size:12px;padding:2rem 0;">Cargando...</div></div>';

    try {
        const res  = await fetch('/api/v1/cartera/', { headers: authHeader() });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const m = data.metrics;
        const c = data.closed_stats;

        const mktBadge = '<span style="background:' + data.mkt_color + '22;border:1px solid ' + data.mkt_color + '88;border-radius:4px;padding:2px 10px;font-size:11px;color:' + data.mkt_color + ';letter-spacing:0.1em;">● MKT: ' + data.mkt_status + '</span>';

        let html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">'
            + '<div style="color:var(--color-muted);font-size:11px;">LAST UPDATE: ' + data.last_update + '</div>'
            + mktBadge
            + '</div>';

        if (m) {
            const pnlColor = m.pnl_neto >= 0 ? 'var(--color-accent)' : '#f23645';
            const valColor = m.val_pct  >= 0 ? 'var(--color-accent)' : '#f23645';
            html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem;">'
                + metricCard('Capital Invertido', '$' + m.total_inv.toLocaleString('en-US', {minimumFractionDigits:2}), 'Base de referencia', 'var(--color-text)')
                + metricCard('Valor Mercado', '$' + m.total_val.toLocaleString('en-US', {minimumFractionDigits:2}), (m.val_pct >= 0 ? '+' : '') + m.val_pct.toFixed(2) + '% vs compra', valColor)
                + metricCard('P&L Real (Neto)', (m.pnl_neto >= 0 ? '+' : '') + '$' + Math.abs(m.pnl_neto).toLocaleString('en-US', {minimumFractionDigits:2}), (m.pnl_pct >= 0 ? '+' : '') + m.pnl_pct.toFixed(2) + '% sobre capital', pnlColor)
                + '</div>';
        }

        html += sectionHeader('01 // POSICIONES ACTIVAS');
        if (data.abiertas && data.abiertas.length > 0) {
            html += positionsTable(data.abiertas, false);
        } else {
            html += emptyBox('Sin posiciones activas en este momento.');
        }

        html += sectionHeader('02 // ACTIVIDAD RECIENTE');
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
            + recentBox('ÚLTIMAS ENTRADAS', data.recent, true)
            + recentBox('ÚLTIMAS SALIDAS', data.cerradas ? data.cerradas.slice(0,5) : [], false)
            + '</div>';

        if (c && c.total > 0) {
            html += sectionHeader('03 // HISTORIAL DE OPERACIONES CERRADAS');
            const wrColor  = c.win_rate >= 50 ? 'var(--color-accent)' : '#f23645';
            const pnlColor = c.avg_pnl  >= 0  ? 'var(--color-accent)' : '#f23645';
            html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1rem;">'
                + metricCard('Trades Cerrados', c.total, c.ganadas + 'W / ' + c.perdidas + 'L', 'var(--color-text)')
                + metricCard('Win Rate', c.win_rate.toFixed(1) + '%', 'Operaciones ganadoras', wrColor)
                + metricCard('P&L Total', (c.avg_pnl >= 0 ? '+' : '') + c.avg_pnl.toFixed(2) + '%', 'Suma de cerradas', pnlColor)
                + '</div>';
            html += positionsTable(data.cerradas, true);
        }

        html += sectionHeader('04 // ESTRATEGIA DE ASIGNACIÓN');
        html += allocationWidget();

        container.querySelector('#cartera-content').innerHTML = html;

        // WebSocket cartera — actualizar precios en tiempo real
        initCarteraWS();

    } catch(e) {
        container.querySelector('#cartera-content').innerHTML =
            '<div style="padding:1.5rem;background:var(--color-surface);border:1px solid #f2364566;border-radius:var(--radius);color:#f23645;font-size:13px;">⚠ ' + e.message + '</div>';
    }
}

function initCarteraWS() {
    const token = sessionStorage.getItem('rsu_token');
    const url   = 'ws://localhost:8000/ws/cartera' + (token ? '?token=' + token : '');
    const ws    = new WebSocket(url);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type !== 'cartera_update') return;
            updateCarteraPrices(data.prices);
        } catch(e) {}
    };

    ws.onerror = () => ws.close();

    // Indicador WS en cartera
    ws.onopen  = () => {
        const ind = document.getElementById('cartera-ws-indicator');
        if (ind) { ind.style.background = 'var(--color-accent)'; ind.title = 'Precios en tiempo real'; }
    };
    ws.onclose = () => {
        const ind = document.getElementById('cartera-ws-indicator');
        if (ind) { ind.style.background = '#555'; ind.title = 'Sin conexión en tiempo real'; }
    };
}

function updateCarteraPrices(prices) {
    (prices || []).forEach(p => {
        // Actualizar precio actual
        document.querySelectorAll('[data-price="' + p.ticker + '"]').forEach(el => {
            el.textContent = '$' + p.price.toLocaleString('en-US', {minimumFractionDigits:2});
        });
        // Actualizar % cambio hoy
        document.querySelectorAll('[data-chg="' + p.ticker + '"]').forEach(el => {
            const color = p.chg >= 0 ? 'var(--color-accent)' : '#f23645';
            el.style.color  = color;
            el.textContent  = (p.chg >= 0 ? '+' : '') + p.chg.toFixed(2) + '% hoy';
        });
    });
}

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function metricCard(label, value, sub, color) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.1em;margin-bottom:6px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:22px;font-weight:500;">' + value + '</div>'
        + '<div style="color:' + color + ';font-size:11px;margin-top:4px;opacity:0.7;">' + sub + '</div>'
        + '</div>';
}

function sectionHeader(title) {
    return '<div style="display:flex;align-items:center;gap:10px;color:var(--color-secondary);font-size:14px;letter-spacing:0.1em;margin:1.5rem 0 0.75rem;border-left:3px solid var(--color-accent);padding-left:10px;">'
        + title
        + '<span id="cartera-ws-indicator" style="width:6px;height:6px;border-radius:50%;background:#555;margin-left:6px;" title="Conectando..."></span>'
        + '</div>';
}

function emptyBox(msg) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;color:var(--color-muted);font-size:12px;margin-bottom:1rem;">' + msg + '</div>';
}

function positionsTable(rows, closed) {
    const headers = closed
        ? ['Fecha', 'Ticker', 'P. Compra', 'P. Salida', 'P&L %', 'Comentarios']
        : ['Fecha', 'Ticker', 'P. Compra', 'P. Actual', 'Hoy', 'P&L %', 'Comentarios'];

    const th = headers.map(h =>
        '<th style="color:var(--color-secondary);font-size:11px;letter-spacing:0.08em;padding:8px 12px;border-bottom:1px solid var(--color-border);text-align:left;">' + h + '</th>'
    ).join('');

    const trs = rows.map(r => {
        const pnlColor = r.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
        const pnlStr   = (r.pnl >= 0 ? '+' : '') + r.pnl.toFixed(2) + '%';
        const comment  = (r.comment && r.comment !== 'nan') ? r.comment : '—';

        if (closed) {
            return '<tr style="border-bottom:1px solid var(--color-border);">'
                + '<td style="padding:9px 12px;color:var(--color-muted);font-size:12px;">' + r.fecha + '</td>'
                + '<td style="padding:9px 12px;"><span style="background:rgba(0,255,173,0.1);color:var(--color-accent);border:1px solid rgba(0,255,173,0.3);border-radius:3px;padding:2px 8px;font-size:12px;">' + r.ticker + '</span></td>'
                + '<td style="padding:9px 12px;color:var(--color-text);font-size:12px;">$' + r.compra.toLocaleString('en-US', {minimumFractionDigits:2}) + '</td>'
                + '<td style="padding:9px 12px;color:var(--color-text);font-size:12px;">$' + r.actual.toLocaleString('en-US', {minimumFractionDigits:2}) + '</td>'
                + '<td style="padding:9px 12px;color:' + pnlColor + ';font-size:12px;font-weight:500;">' + pnlStr + '</td>'
                + '<td style="padding:9px 12px;color:var(--color-muted);font-size:11px;">' + comment + '</td>'
                + '</tr>';
        }

        return '<tr style="border-bottom:1px solid var(--color-border);">'
            + '<td style="padding:9px 12px;color:var(--color-muted);font-size:12px;">' + r.fecha + '</td>'
            + '<td style="padding:9px 12px;"><span style="background:rgba(0,255,173,0.1);color:var(--color-accent);border:1px solid rgba(0,255,173,0.3);border-radius:3px;padding:2px 8px;font-size:12px;">' + r.ticker + '</span></td>'
            + '<td style="padding:9px 12px;color:var(--color-text);font-size:12px;">$' + r.compra.toLocaleString('en-US', {minimumFractionDigits:2}) + '</td>'
            + '<td style="padding:9px 12px;color:var(--color-text);font-size:12px;" data-price="' + r.ticker + '">$' + r.actual.toLocaleString('en-US', {minimumFractionDigits:2}) + '</td>'
            + '<td style="padding:9px 12px;font-size:11px;color:var(--color-muted);" data-chg="' + r.ticker + '">—</td>'
            + '<td style="padding:9px 12px;color:' + pnlColor + ';font-size:12px;font-weight:500;">' + pnlStr + '</td>'
            + '<td style="padding:9px 12px;color:var(--color-muted);font-size:11px;">' + comment + '</td>'
            + '</tr>';
    }).join('');

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;max-height:400px;overflow-y:auto;">'
        + '<table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">'
        + '<thead><tr>' + th + '</tr></thead>'
        + '<tbody>' + trs + '</tbody>'
        + '</table></div>';
}

function recentBox(title, rows, isEntradas) {
    const color = isEntradas ? 'var(--color-accent)' : '#f23645';
    const items = (rows || []).slice(0,5).map(r => {
        const val = isEntradas
            ? '<span style="color:var(--color-text);">$' + r.compra.toLocaleString('en-US', {minimumFractionDigits:2}) + '</span>'
            : '<span style="color:' + (r.pnl >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (r.pnl >= 0 ? '+' : '') + r.pnl.toFixed(2) + '%</span>';
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
            + '<span style="color:var(--color-muted);">' + r.fecha + '</span>'
            + '<span style="background:rgba(0,255,173,0.1);color:var(--color-accent);border:1px solid rgba(0,255,173,0.3);border-radius:3px;padding:1px 6px;">' + r.ticker + '</span>'
            + val
            + '</div>';
    }).join('') || '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem 0;">Sin datos.</div>';

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 1.25rem;">'
        + '<div style="color:' + color + ';font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
        + items
        + '</div>';
}

function allocationWidget() {
    const buckets = [
        { name: 'SPXL Strategy', pct: 40, color: '#00ffad', desc: 'Núcleo de la cartera. Exposición apalancada 3x al S&P 500. Largo plazo.' },
        { name: 'RSU Stocks',    pct: 30, color: '#00d9ff', desc: 'Acciones líderes de sectores con crecimiento explosivo.' },
        { name: 'Cryptos',       pct: 20, color: '#ff9800', desc: 'Asignación especulativa. BTC y ETH como activos de reserva digital.' },
        { name: 'Beta Stocks',   pct: 10, color: '#b044ff', desc: 'Acciones de alto beta para capturar movimientos amplificados.' },
    ];

    const chartId = 'donut-' + Date.now();

    const legend = buckets.map(b =>
        '<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid var(--color-border);">'
        + '<div style="width:10px;height:10px;background:' + b.color + ';border-radius:2px;margin-top:3px;flex-shrink:0;"></div>'
        + '<div>'
        + '<span style="color:' + b.color + ';font-size:13px;">' + b.name + '</span>'
        + '<span style="color:' + b.color + ';font-size:14px;margin-left:8px;">' + b.pct + '%</span>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;line-height:1.4;">' + b.desc + '</div>'
        + '</div></div>'
    ).join('');

    const widget = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">'
        + '<canvas id="' + chartId + '" width="260" height="260"></canvas>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:8px;letter-spacing:0.08em;">Asignación objetivo · Estrategia RSU</div>'
        + '</div>'
        + '<div>' + legend + '</div>'
        + '</div>';

    setTimeout(() => {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        const ctx  = canvas.getContext('2d');
        const cx   = 130, cy = 130, ro = 100, ri = 60;
        let angle  = -Math.PI / 2;
        buckets.forEach(b => {
            const slice = (b.pct / 100) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(cx + ro * Math.cos(angle), cy + ro * Math.sin(angle));
            ctx.arc(cx, cy, ro, angle, angle + slice);
            ctx.arc(cx, cy, ri, angle + slice, angle, true);
            ctx.closePath();
            ctx.fillStyle = b.color;
            ctx.fill();
            angle += slice;
        });
        ctx.beginPath();
        ctx.arc(cx, cy, ri, 0, 2 * Math.PI);
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim() || '#111';
        ctx.fill();
        ctx.fillStyle = '#00ffad';
        ctx.font = 'bold 14px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('RSU', cx, cy - 8);
        ctx.fillText('PORTFOLIO', cx, cy + 10);
    }, 100);

    return widget;
}