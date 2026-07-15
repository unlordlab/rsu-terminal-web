// ── VISTA MÓVIL ──────────────────────────────────────────────────────────────
//
// Pensada para PWA instalada en el móvil (ver /manifest.json) — una sola
// columna, texto grande, solo lo esencial: Algoritmo RSU, Mercado, Cartera y
// Watchlist. Reutiliza los mismos endpoints que ya usa la terminal de
// escritorio (/api/v1/algoritmo, /api/v1/market/breadth, /api/v1/market/indices,
// /api/v1/cartera, /api/v1/watchlist) — cero backend nuevo.

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

export async function render(container) {
    container.innerHTML = `
        <div style="max-width:480px;margin:0 auto;padding:12px;font-family:var(--font-mono);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <div style="color:var(--color-accent);font-size:16px;letter-spacing:0.08em;">RSU TERMINAL</div>
                <button id="mobile-refresh-btn" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 12px;font-size:12px;cursor:pointer;">↻ Actualizar</button>
            </div>
            <div id="mobile-algoritmo" style="margin-bottom:14px;"></div>
            <div id="mobile-mercado" style="margin-bottom:14px;"></div>
            <div id="mobile-cartera" style="margin-bottom:14px;"></div>
            <div id="mobile-watchlist"></div>
        </div>
    `;
    container.querySelector('#mobile-refresh-btn').addEventListener('click', () => cargarTodo(container));
    cargarTodo(container);
}

function cargarTodo(container) {
    cargarAlgoritmo(container);
    cargarMercado(container);
    cargarCartera(container);
    cargarWatchlist(container);
}

function tarjeta(titulo, contenidoHtml) {
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${titulo}</div>
        <div style="padding:14px;">${contenidoHtml}</div>
    </div>`;
}

function cargando(titulo) {
    return tarjeta(titulo, '<div style="color:var(--color-muted);font-size:12px;text-align:center;">Cargando...</div>');
}

// ── ALGORITMO RSU ────────────────────────────────────────────────────────────

async function cargarAlgoritmo(container) {
    const el = container.querySelector('#mobile-algoritmo');
    el.innerHTML = cargando('ALGORITMO RSU');
    try {
        const res  = await fetch('/api/v1/algoritmo/', { headers: authHeader() });
        const data = await res.json();
        el.innerHTML = tarjeta('ALGORITMO RSU', `
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                <div style="width:16px;height:16px;border-radius:50%;background:${data.color};flex-shrink:0;"></div>
                <div>
                    <div style="color:var(--color-text);font-size:16px;font-weight:700;">${data.senal || data.estado}</div>
                    <div style="color:var(--color-muted);font-size:11px;">Score: ${data.score}/${data.umbral_verde ? '100' : '?'} (umbral VERDE: ${data.umbral_verde})</div>
                </div>
            </div>
            <div style="color:var(--color-muted);font-size:12px;line-height:1.5;">${(data.recomendacion || '').slice(0, 160)}${(data.recomendacion || '').length > 160 ? '…' : ''}</div>
        `);
    } catch (e) {
        el.innerHTML = tarjeta('ALGORITMO RSU', '<div style="color:#f23645;font-size:12px;">Error cargando datos</div>');
    }
}

// ── MERCADO ───────────────────────────────────────────────────────────────────

async function cargarMercado(container) {
    const el = container.querySelector('#mobile-mercado');
    el.innerHTML = cargando('MERCADO');
    try {
        const [resIdx, resBreadth] = await Promise.all([
            fetch('/api/v1/market/indices', { headers: authHeader() }),
            fetch('/api/v1/market/breadth', { headers: authHeader() }),
        ]);
        const idx     = await resIdx.json();
        const breadth = await resBreadth.json();

        const indicesHtml = (idx.data || []).slice(0, 4).map(i => {
            const color = i.pct >= 0 ? 'var(--color-accent)' : '#f23645';
            return `<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:12px;">
                <span style="color:var(--color-muted);">${i.ticker}</span>
                <span style="color:var(--color-text);">${i.price ?? '—'}</span>
                <span style="color:${color};">${i.pct != null ? (i.pct >= 0 ? '+' : '') + i.pct + '%' : '—'}</span>
            </div>`;
        }).join('');

        const breadthHtml = breadth.ok ? `
            <div style="display:flex;justify-content:space-between;padding-top:8px;margin-top:8px;border-top:1px solid var(--color-border);font-size:11px;color:var(--color-muted);">
                <span>Tendencia: <span style="color:var(--color-text);">${breadth.trend}</span></span>
                <span>RSI: <span style="color:var(--color-text);">${breadth.rsi}</span></span>
                <span>% &gt;SMA50: <span style="color:var(--color-text);">${breadth.pct_above_sma50 ?? '—'}%</span></span>
            </div>` : '';

        el.innerHTML = tarjeta('MERCADO', indicesHtml + breadthHtml);
    } catch (e) {
        el.innerHTML = tarjeta('MERCADO', '<div style="color:#f23645;font-size:12px;">Error cargando datos</div>');
    }
}

// ── CARTERA ───────────────────────────────────────────────────────────────────

async function cargarCartera(container) {
    const el = container.querySelector('#mobile-cartera');
    el.innerHTML = cargando('CARTERA');
    try {
        const res  = await fetch('/api/v1/cartera/', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) { el.innerHTML = tarjeta('CARTERA', '<div style="color:var(--color-muted);font-size:12px;">Sin datos</div>'); return; }

        const m = data.metrics || {};
        const pnlColor = (m.pnl_pct || 0) >= 0 ? 'var(--color-accent)' : '#f23645';
        const resumen = `
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <div>
                    <div style="color:var(--color-muted);font-size:10px;">VALOR ACTUAL</div>
                    <div style="color:var(--color-text);font-size:16px;font-weight:700;">$${(m.total_val ?? 0).toLocaleString()}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:var(--color-muted);font-size:10px;">P&amp;L</div>
                    <div style="color:${pnlColor};font-size:16px;font-weight:700;">${(m.pnl_pct || 0) >= 0 ? '+' : ''}${m.pnl_pct ?? 0}%</div>
                </div>
            </div>`;

        const posiciones = (data.abiertas || []).slice(0, 8).map(p => {
            const color = p.pnl >= 0 ? 'var(--color-accent)' : '#f23645';
            return `<div style="display:flex;justify-content:space-between;padding:5px 0;border-top:1px solid var(--color-border);font-size:12px;">
                <span onclick="window.__navigate('/research?ticker=${p.ticker}')" style="cursor:pointer;color:var(--color-text);">${p.ticker}</span>
                <span style="color:${color};">${p.pnl >= 0 ? '+' : ''}${p.pnl}%</span>
            </div>`;
        }).join('');

        el.innerHTML = tarjeta('CARTERA', resumen + posiciones);
    } catch (e) {
        el.innerHTML = tarjeta('CARTERA', '<div style="color:#f23645;font-size:12px;">Error cargando datos</div>');
    }
}

// ── WATCHLIST ─────────────────────────────────────────────────────────────────

async function cargarWatchlist(container) {
    const el = container.querySelector('#mobile-watchlist');
    el.innerHTML = cargando('WATCHLIST');
    try {
        const res  = await fetch('/api/v1/watchlist', { headers: authHeader() });
        const data = await res.json();
        const rows = data.data || [];
        if (!rows.length) { el.innerHTML = tarjeta('WATCHLIST', '<div style="color:var(--color-muted);font-size:12px;">Sin tickers seguidos</div>'); return; }

        const filas = rows.map(r => {
            const color = (r.chg || 0) >= 0 ? 'var(--color-accent)' : '#f23645';
            return `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;">
                <span onclick="window.__navigate('/research?ticker=${r.ticker}')" style="cursor:pointer;color:var(--color-text);">${r.ticker}</span>
                <span style="color:var(--color-muted);">${r.price != null ? '$' + r.price : '—'}</span>
                <span style="color:${color};">${r.chg != null ? (r.chg >= 0 ? '+' : '') + r.chg + '%' : '—'}</span>
            </div>`;
        }).join('');

        el.innerHTML = tarjeta('WATCHLIST', filas);
    } catch (e) {
        el.innerHTML = tarjeta('WATCHLIST', '<div style="color:#f23645;font-size:12px;">Error cargando datos</div>');
    }
}