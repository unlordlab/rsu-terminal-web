import { tt } from '/components/tooltip.js';
import { errorMessage, esc, fmtFecha } from '/core/ui.js';

// Esta página tenía su propia copia de este formateador, y su comentario decía
// que era "el mismo formato usado en el resto de la terminal" — no lo era: la
// mayoría de páginas pintaban el ISO crudo. Unificado en core/ui.js el
// 04/08/2026; el alias se mantiene para no tocar los 8 sitios que ya lo usaban.
const _fmtFecha = fmtFecha;

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

// Badges de cruce -- Fase 3 del roadmap: ⭐ si está en la Watchlist del
// usuario, ⚡ si además hay señal de compra insider simultánea en el mismo
// ticker (confluencia "dinero inteligente"). 💼 (Cartera) ya se pintaba a
// mano donde hacía falta antes de esta sesión, se deja igual.
function badges(row) {
    return (row.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '')
        + (row.is_confluence ? ' <span title="Señal alcista simultánea en Insider Flow">⚡</span>' : '');
}

let currentTicker = null;
let currentPeriod = '1w';

export async function render(container) {
    container.innerHTML = pageHeader() + '<div id="options-body"></div>';
    setupSearch(container);
    loadDashboard(container);
}

function pageHeader() {
    return `
    <div style="margin-bottom:1.5rem;">
        <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;margin-bottom:1rem;">OPTIONS FLOW ${tt('options-flow')}</div>
        <div style="display:flex;gap:8px;">
            <input id="opt-search-input" type="text" placeholder="Buscar ticker (NVDA, TSLA...)" style="flex:1;max-width:320px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;text-transform:uppercase;">
            <button id="opt-search-btn" style="background:var(--color-accent);color:var(--color-bg,#0a0a0a);border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">BUSCAR</button>
            <button id="opt-back-btn" style="display:none;background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← Volver</button>
        </div>
    </div>`;
}

function setupSearch(container) {
    const input   = container.querySelector('#opt-search-input');
    const btn     = container.querySelector('#opt-search-btn');
    const backBtn = container.querySelector('#opt-back-btn');
    const buscar  = () => {
        const t = input.value.trim().toUpperCase();
        if (!t) return;
        backBtn.style.display = 'inline-block';
        loadTicker(t, '1w');
    };
    btn.addEventListener('click', buscar);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') buscar(); });
    backBtn.addEventListener('click', () => {
        backBtn.style.display = 'none';
        input.value = '';
        currentTicker = null;
        loadDashboard(container);
    });
}

// ── DASHBOARD (vista por defecto) ───────────────────────────────────────────

async function loadDashboard(container) {
    const body = container.querySelector('#options-body');
    body.innerHTML = loading();
    try {
        const res  = await fetch('/api/v1/options/flow-simple', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) { body.innerHTML = errorMessage(data.error || 'Sin datos'); return; }
        body.innerHTML = renderDashboard(data);
    } catch (e) {
        body.innerHTML = errorMessage(e.message);
    }
}

// Marca de resultados. Se distinguen los dos casos porque significan casi lo
// contrario: si el vencimiento cae DESPUES del anuncio, la opcion sigue viva
// durante el evento (IV inflada antes, desplome despues); si cae ANTES, la
// opcion no recoge el movimiento en absoluto. Antes los dos compartian el
// mismo icono y el mismo texto, y ademas el segundo caso ni se detectaba.
function _marcaEarnings(r) {
    if (!r || !r.near_earnings) return '';
    if (r.earnings_rel === 'antes') {
        return ' <span title="Vence justo ANTES de la publicación de resultados: la opción no llega al anuncio, así que no recoge ese movimiento">🕐</span>';
    }
    return ' <span title="Vence justo DESPUÉS de la publicación de resultados: la opción sigue viva durante el anuncio">📅</span>';
}

function renderDashboard(data) {
    const cob = data.cobertura;
    // Cuántos valores respondieron de los que se pidieron. Un escaneo corto
    // produce pocas señales, y sin este dato eso se lee como un día tranquilo
    // en vez de como un día sin datos, que es lo contrario.
    const coberturaTxt = cob && cob.cobertura_pct != null
        ? ` · <span style="color:${cob.incompleto ? '#ffb800' : 'var(--color-muted)'};">${esc(cob.respondidos)}/${esc(cob.pedidos)} valores leídos (${esc(cob.cobertura_pct)}%)</span>`
        : '';
    const fechaDatos = data.scan_date
        ? `<div style="color:var(--color-muted);font-size:11px;margin-bottom:10px;">📊 Datos del escaneo: <span style="color:var(--color-text);font-weight:600;">${esc(_fmtFecha(data.scan_date))}</span>${coberturaTxt}</div>`
        : '';

    // Dos motivos distintos por los que un escaneo no sirve, y se explican por
    // separado porque no significan lo mismo: uno es no haber podido leer los
    // valores, el otro es haberlos leído y que vinieran vacíos.
    let motivo = '';
    if (cob && cob.cobertura_baja) {
        motivo = `Solo se pudieron leer <strong>${esc(cob.respondidos)} de ${esc(cob.pedidos)}</strong> valores (${esc(cob.cobertura_pct)}%), así que faltan señales que sí pudieron existir.`;
    } else if (cob && cob.datos_vacios) {
        motivo = `Se leyeron ${esc(cob.respondidos)} valores, pero <strong>${esc(cob.oi_cero_pct)}% llegaron sin posiciones abiertas registradas</strong>. El proveedor de datos devolvió las cadenas vacías, así que la actividad de ese día no se pudo medir.`;
    }
    const avisoCobertura = motivo
        ? `<div style="background:rgba(255,184,0,0.10);border:1px solid #ffb800;border-radius:var(--radius);padding:10px 14px;margin-bottom:1rem;font-size:12px;color:var(--color-text);">
            ⚠️ <strong>Escaneo incompleto.</strong> ${motivo} Lo de abajo describe la parte que sí se pudo mirar, no el mercado entero — y el sesgo del día está calculado sobre esa muestra parcial.
        </div>`
        : '';

    const biasColor = data.dia_bias_label === 'ALCISTA' ? 'var(--color-accent)' : (data.dia_bias_label === 'BAJISTA' ? '#f23645' : 'var(--color-muted)');
    const biasBanner = data.dia_bias_pct != null
        ? `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:12px 16px;margin-bottom:1rem;font-size:13px;">
            <span style="color:var(--color-muted);">Hoy: </span><span style="color:${biasColor};font-weight:700;">${esc(data.dia_bias_pct)}% ${esc(data.dia_bias_label)}</span><span style="color:var(--color-muted);"> por prima (Calls Bought + Puts Sold vs. Puts Bought + Calls Sold) ${tt('options-dia-bias')}</span>
        </div>`
        : '';

    const tickerListBox = (title, items) => `
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:14px;flex:1;min-width:220px;">
            <div style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;margin-bottom:10px;">${title}</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
                ${items.length ? items.map(t => `<span onclick="window.__optionsSearchTicker('${esc(t.ticker)}')" style="cursor:pointer;color:var(--color-accent);font-size:12px;font-weight:600;padding:3px 8px;background:var(--color-bg,#0a0a0a);border-radius:3px;border:1px solid var(--color-border);">${esc(t.ticker)}${badges(t)}${t.premium_fmt ? ' <span style="color:var(--color-muted);font-weight:400;">' + esc(t.premium_fmt) + '</span>' : ''}</span>`).join('') : '<span style="color:var(--color-muted);font-size:11px;">Sin datos todavía</span>'}
            </div>
        </div>`;

    const topBoxes = `<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:1.5rem;">
        ${tickerListBox('TOP PREMIUM', data.top_premium)}
        ${tickerListBox('TOP BULLISH', data.top_bullish)}
        ${tickerListBox('TOP BEARISH', data.top_bearish)}
    </div>`;

    const flowTables = `<div class="rsu-grid-panels" style="gap:14px;margin-bottom:1.5rem;">
        ${flowTable(`CALLS BOUGHT ${tt('options-categories')}`, data.calls_bought, 'var(--color-accent)')}
        ${flowTable('PUTS SOLD', data.puts_sold, 'var(--color-accent)')}
        ${flowTable('PUTS BOUGHT', data.puts_bought, '#f23645')}
        ${flowTable('CALLS SOLD', data.calls_sold, '#f23645')}
    </div>`;

    const oiTables = `<div class="rsu-grid-panels" style="gap:14px;">
        ${oiTable(`LARGE OI INCREASE ${tt('options-large-oi')}`, data.large_oi_increase, 'var(--color-accent)', '▲')}
        ${oiTable('LARGE OI DECREASE', data.large_oi_decrease, '#f23645', '▼')}
    </div>`;

    const sinOi = data.large_oi_increase && data.large_oi_increase.length === 0 && data.large_oi_decrease.length === 0;
    // `oi_nota` llega cuando la comparación todavía va por el camino antiguo,
    // que solo ve contratos que además destacaron por prima. Decirlo importa:
    // sin el aviso, una lista corta se lee como "hubo pocos cambios" cuando en
    // realidad es "solo se pudo mirar una parte".
    const nota = sinOi
        ? '<div style="color:var(--color-muted);font-size:11px;margin-top:10px;">Los cambios de Open Interest necesitan al menos 2 días de histórico guardado — aparecerán a partir de mañana.</div>'
        : (data.oi_nota
            ? `<div style="color:#ffb800;font-size:11px;margin-top:10px;">⚠️ ${esc(data.oi_nota)}</div>`
            : (data.oi_comparados
                ? `<div style="color:var(--color-muted);font-size:11px;margin-top:10px;">Comparados ${esc(data.oi_comparados)} contratos entre las dos últimas sesiones.</div>`
                : ''));

    return fechaDatos + avisoCobertura + biasBanner + topBoxes + flowTables + oiTables + nota;
}

function flowTable(title, rows, color) {
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${title}</span>
            <span style="color:var(--color-muted);font-size:11px;">${rows.length}</span>
        </div>
        <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);letter-spacing:0.05em;">
            <div>TICKER</div><div>STRIKE</div><div>EXP</div><div style="text-align:right;">PREMIUM</div>
        </div>
        <div style="max-height:340px;overflow-y:auto;">
            ${rows.length ? rows.map(r => `
            <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">
                <span onclick="window.__optionsSearchTicker('${esc(r.ticker)}')" style="cursor:pointer;color:${color};font-weight:600;">${esc(r.ticker)}${_marcaEarnings(r)}${badges(r)}${r.es_repetida ? ' <span title="Mismo contrato repetido en días anteriores">🔁</span>' : ''}</span>
                <span style="color:var(--color-text);">$${esc(r.strike)} <span style="color:var(--color-muted);">(${esc(r.strike_pct)})</span></span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(r.exp))}</span>
                <span style="color:var(--color-text);text-align:right;">${esc(r.premium_fmt)}</span>
            </div>`).join('') : '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin entradas hoy</div>'}
        </div>
    </div>`;
}

function oiTable(title, rows, color, arrow) {
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${title}</span>
            <span style="color:var(--color-muted);font-size:11px;">${rows.length}</span>
        </div>
        <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);letter-spacing:0.05em;">
            <div>TICKER</div><div>STRIKE</div><div>EXP</div><div style="text-align:right;">CAMBIO OI</div>
        </div>
        <div style="max-height:280px;overflow-y:auto;">
            ${rows.length ? rows.map(r => `
            <div style="display:grid;grid-template-columns:70px 1fr 90px 70px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">
                <span onclick="window.__optionsSearchTicker('${esc(r.ticker)}')" style="cursor:pointer;color:${color};font-weight:600;">${esc(r.ticker)}</span>
                <span style="color:var(--color-text);">$${esc(r.strike)}</span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(r.exp))}</span>
                <span style="color:${color};text-align:right;">${arrow} ${Math.abs(r.daily_pct)}%</span>
            </div>`).join('') : '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin datos todavía</div>'}
        </div>
    </div>`;
}

// ── VISTA POR TICKER ─────────────────────────────────────────────────────────

window.__optionsSearchTicker = function(ticker) {
    const input   = document.querySelector('#opt-search-input');
    const backBtn = document.querySelector('#opt-back-btn');
    if (input) input.value = ticker;
    if (backBtn) backBtn.style.display = 'inline-block';
    loadTicker(ticker, '1w');
};

async function loadTicker(ticker, period) {
    currentTicker = ticker;
    currentPeriod = period;
    const body = document.querySelector('#options-body');
    if (!body) return;
    body.innerHTML = loading();
    try {
        // GEX en paralelo, sin bloquear el render de flujo si falla o
        // tarda -- es una sección adicional, no crítica para la vista
        // principal (mismo criterio de resiliencia que el resto del proyecto).
        const gexQs = new URLSearchParams({ max_dte: _gexParams.max_dte });
        if (_gexParams.strike_range) gexQs.set('strike_range', _gexParams.strike_range);
        const [flowRes, gexRes] = await Promise.all([
            fetch('/api/v1/options/ticker-flow/' + ticker + '?period=' + period, { headers: authHeader() }),
            fetch(`/api/v1/options/gex/${ticker}?${gexQs}`, { headers: authHeader() }).catch(() => null),
        ]);
        const data = await flowRes.json();
        const gex  = gexRes ? await gexRes.json().catch(() => ({ ok: false })) : { ok: false };
        // GEX/DEX se pintan AUNQUE no haya histórico de flujo para el ticker:
        // se calculan sobre la cadena de opciones en vivo, no sobre lo que el
        // escaneo nocturno haya llegado a registrar. Antes un `return` aquí
        // escondía toda la sección para cualquier ticker sin señales
        // guardadas, que es justo cuando más útil es tener el perfil.
        const cabecera = data.ok ? renderTicker(data) : errorMessage(data.error || 'Sin datos de flujo');
        // El bloque GEX/DEX va en su propio contenedor para poder recargarlo
        // solo a él al cambiar Max DTE o el rango de strikes, sin volver a
        // pedir todo el flujo del ticker.
        body.innerHTML = cabecera + '<div id="gex-block">' + renderGex(gex) + '</div>';
        if (data.ok) wireTickerPeriods(body);
        wireGex(body.querySelector('#gex-block'), ticker);
    } catch (e) {
        body.innerHTML = errorMessage(e.message);
    }
}

// Parámetros de la vista GEX/DEX, equivalentes a los controles de
// tradingedge.club. strike_range vacío = rango automático (±12% del spot,
// lo decide el backend) -- un ±15 fijo no significa lo mismo en un ticker
// de $5 que en uno de $900.
let _gexParams = { max_dte: 50, strike_range: '' };

function _fmtExp(v) {
    if (!v) return '$0';          // sin signo: un "+$0" no significa nada
    const s = v > 0 ? '+' : '-';
    const a = Math.abs(v);
    if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(2)}B`;
    if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(1)}M`;
    if (a >= 1e3) return `${s}$${(a / 1e3).toFixed(0)}K`;
    return `${s}$${a.toFixed(0)}`;
}

/** Gráfico de barras divergentes por strike: puts a la izquierda, calls a la
 *  derecha, el strike en el centro. Mismo reparto visual que la herramienta
 *  del PDF -- calls y puts SEPARADAS, no neteadas, que es justo lo que se
 *  pierde al mostrar solo el neto. */
function expChart(titulo, rows, keyCall, keyPut, spot, tooltipKey) {
    const maxAbs = Math.max(...rows.map(r => Math.max(Math.abs(r[keyCall]), Math.abs(r[keyPut]))), 1);
    // El strike más cercano al spot se resalta: es la referencia para leer
    // todo el perfil y a ojo no siempre es evidente cuál es.
    let iSpot = 0;
    rows.forEach((r, i) => { if (Math.abs(r.strike - spot) < Math.abs(rows[iSpot].strike - spot)) iSpot = i; });
    const barras = rows.map((r, i) => {
        const pc = Math.abs(r[keyCall]) / maxAbs * 100;
        const pp = Math.abs(r[keyPut])  / maxAbs * 100;
        const esSpot = i === iSpot;
        const bg = esSpot ? 'background:rgba(128,128,128,0.14);' : '';
        return `<div style="display:grid;grid-template-columns:1fr 66px 1fr;gap:6px;align-items:center;padding:2px 14px;font-size:10px;${bg}">
            <div style="display:flex;justify-content:flex-end;"><div title="Puts ${esc(_fmtExp(r[keyPut]))}" style="height:9px;width:${pp}%;background:#f23645;border-radius:2px 0 0 2px;"></div></div>
            <span style="text-align:center;color:${esSpot ? 'var(--color-text)' : 'var(--color-muted)'};font-weight:${esSpot ? '700' : '400'};">${esc(r.strike)}${esSpot ? ' ◄' : ''}</span>
            <div><div title="Calls ${esc(_fmtExp(r[keyCall]))}" style="height:9px;width:${pc}%;background:var(--color-accent);border-radius:0 2px 2px 0;"></div></div>
        </div>`;
    }).join('');
    return `
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-top:1rem;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">${esc(titulo)} ${tooltipKey ? tt(tooltipKey) : ''}</span>
            <span style="font-size:10px;color:var(--color-muted);">
                <span style="color:#f23645;">■</span> PUTS &nbsp; <span style="color:var(--color-accent);">■</span> CALLS
            </span>
        </div>
        <div style="padding:6px 0;">${barras}</div>
    </div>`;
}

function renderGex(gex) {
    // Los controles se pintan SIEMPRE, aunque la consulta falle: si un
    // Max DTE o un rango demasiado estrecho deja la cadena vacía, el usuario
    // tiene que poder ampliarlo sin recargar la página.
    const controles = `
    <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;padding:10px 14px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);margin-top:1rem;">
        <label style="font-size:10px;color:var(--color-muted);display:flex;flex-direction:column;gap:3px;">MAX DTE (días)
            <input id="gex-dte" type="number" min="1" max="365" value="${esc(_gexParams.max_dte)}" style="width:80px;padding:4px 6px;background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:3px;font-size:11px;">
        </label>
        <label style="font-size:10px;color:var(--color-muted);display:flex;flex-direction:column;gap:3px;">RANGO STRIKES (± $)
            <input id="gex-range" type="number" min="0.5" step="0.5" placeholder="auto" value="${esc(_gexParams.strike_range)}" style="width:90px;padding:4px 6px;background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:3px;font-size:11px;">
        </label>
        <button id="gex-go" style="padding:5px 14px;background:var(--color-accent);color:var(--color-bg);border:none;border-radius:3px;font-size:11px;font-weight:700;cursor:pointer;">GENERAR</button>
    </div>`;

    if (!gex || !gex.ok) {
        return controles + `<div style="padding:12px 14px;font-size:11px;color:var(--color-muted);">${esc(gex && gex.error ? gex.error : 'Sin datos de GEX/DEX para este ticker.')}</div>`;
    }

    const gexColor = gex.total_gex >= 0 ? 'var(--color-accent)' : '#f23645';
    const regimenTxt = gex.regimen === 'POSITIVO'
        ? 'GEX positivo: los dealers tienden a amortiguar el movimiento (compran en caídas, venden en subidas)'
        : 'GEX negativo: los dealers tienden a amplificar el movimiento (venden en caídas, compran en subidas)';
    const kpi = (label, valor, color, nota) => `
        <div style="flex:1;min-width:120px;">
            <div style="font-size:9px;color:var(--color-muted);letter-spacing:0.06em;">${esc(label)}</div>
            <div style="font-size:15px;font-weight:700;color:${color};">${esc(valor)}</div>
            ${nota ? `<div style="font-size:9px;color:var(--color-muted);">${esc(nota)}</div>` : ''}
        </div>`;
    const dte = gex.exp_days_range ? `${gex.exp_days_range[0]}-${gex.exp_days_range[1]} días` : '';

    const cabecera = `
    <div style="display:flex;gap:14px;flex-wrap:wrap;padding:12px 14px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);margin-top:1rem;">
        ${kpi('SPOT', '$' + gex.price, 'var(--color-text)', gex.ticker)}
        ${kpi('GEX TOTAL', gex.total_gex_fmt, gexColor, 'por 1% de movimiento')}
        ${kpi('DEX TOTAL', gex.total_dex_fmt, gex.total_dex >= 0 ? 'var(--color-accent)' : '#f23645', 'delta neta del OI')}
        ${kpi('CALL/PUT', gex.call_put_ratio != null ? gex.call_put_ratio : 'N/D', 'var(--color-text)', 'sobre open interest')}
        ${kpi('VENCIMIENTOS', dte || 'N/D', 'var(--color-text)', '± $' + gex.strike_range + ' en strikes')}
    </div>
    <div style="padding:8px 14px;font-size:11px;color:var(--color-muted);">${esc(regimenTxt)}</div>`;

    return controles + cabecera
        + expChart('GAMMA EXPOSURE (GEX)', gex.by_strike, 'gex_call', 'gex_put', gex.price, 'options-gex')
        + expChart('DELTA EXPOSURE (DEX)', gex.by_strike, 'dex_call', 'dex_put', gex.price, 'options-dex');
}

async function loadGex(ticker) {
    const bloque = document.querySelector('#gex-block');
    if (!bloque) return;
    const qs = new URLSearchParams({ max_dte: _gexParams.max_dte });
    if (_gexParams.strike_range) qs.set('strike_range', _gexParams.strike_range);
    let gex = { ok: false };
    try {
        const res = await fetch(`/api/v1/options/gex/${ticker}?${qs}`, { headers: authHeader() });
        gex = await res.json();
    } catch (e) {
        gex = { ok: false, error: e.message };
    }
    bloque.innerHTML = renderGex(gex);
    wireGex(bloque, ticker);
}

function wireGex(scope, ticker) {
    const go = scope.querySelector('#gex-go');
    if (!go) return;
    go.addEventListener('click', () => {
        const dte = parseInt(scope.querySelector('#gex-dte').value, 10);
        const rng = scope.querySelector('#gex-range').value.trim();
        _gexParams.max_dte      = (dte >= 1 && dte <= 365) ? dte : 50;
        _gexParams.strike_range = rng;
        go.textContent = 'CARGANDO…';
        loadGex(ticker);
    });
}

function wireTickerPeriods(scope) {
    scope.querySelectorAll('.opt-period-btn').forEach(btn => {
        btn.addEventListener('click', () => loadTicker(currentTicker, btn.dataset.period));
    });
}

const PERIODS = [
    { key: '1w', label: '1 Semana' }, { key: '2w', label: '2 Semanas' },
    { key: '1m', label: '1 Mes' }, { key: '3m', label: '3 Meses' }, { key: '4m', label: '4 Meses' },
];

function renderTicker(data) {
    const scoreColor = data.net_score > 0 ? 'var(--color-accent)' : (data.net_score < 0 ? '#f23645' : 'var(--color-muted)');
    const periodBtns = PERIODS.map(p => `
        <button class="opt-period-btn" data-period="${p.key}" style="background:${p.key === currentPeriod ? 'var(--color-accent)' : 'transparent'};color:${p.key === currentPeriod ? 'var(--color-bg,#0a0a0a)' : 'var(--color-muted)'};border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">${p.label}</button>
    `).join('');

    return `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;flex-wrap:wrap;gap:12px;">
        <div>
            <div style="color:var(--color-text);font-size:24px;font-weight:700;margin-bottom:10px;">${esc(data.ticker)} <span onclick="window.__navigate('/research?ticker=${esc(data.ticker)}')" style="cursor:pointer;color:var(--color-accent);font-size:12px;font-weight:400;text-decoration:underline;vertical-align:middle;" title="Ver análisis completo en Research">→ Research</span>${data.en_cartera ? ' <span style="font-size:12px;background:var(--color-accent);color:var(--color-bg,#0a0a0a);padding:3px 8px;border-radius:3px;vertical-align:middle;">💼 EN CARTERA</span>' : ''}${data.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : ''}${data.is_confluence ? ' <span title="Señal alcista simultánea en Insider Flow">⚡</span>' : ''}</div>
            <div style="display:flex;gap:6px;">${periodBtns}</div>
        </div>
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);min-width:180px;overflow:hidden;">
            <div style="padding:8px 14px;border-bottom:1px solid var(--color-border);color:var(--color-muted);font-size:11px;text-align:center;">NET SCORE ${tt('options-net-score')}</div>
            <div style="padding:14px;color:${scoreColor};font-size:22px;font-weight:700;text-align:center;">${data.net_score > 0 ? '+' : ''}${esc(data.net_score)}</div>
        </div>
    </div>
    <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="padding:10px 14px;border-bottom:1px solid var(--color-border);display:flex;justify-content:space-between;">
            <span style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;">TOTAL</span>
            <span style="color:var(--color-muted);font-size:11px;">${esc(data.total)}</span>
        </div>
        <div style="display:grid;grid-template-columns:90px 100px 90px 90px 60px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">
            <div>TRADE DATE</div><div>ORDER TYPE</div><div>STRIKE</div><div>EXP</div><div>OI</div><div style="text-align:right;">PREMIUM</div>
        </div>
        ${data.entradas.map(e => {
            const bullish = e.order_type === 'Buy Call' || e.order_type === 'Sell Put';
            const badgeColor = bullish ? 'var(--color-accent)' : '#f23645';
            return `<div style="display:grid;grid-template-columns:90px 100px 90px 90px 60px 90px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;">
                <span style="color:var(--color-muted);">${esc(_fmtFecha(e.fecha))}</span>
                <span style="background:${badgeColor}22;border:1px solid ${badgeColor}88;color:${badgeColor};border-radius:3px;padding:2px 7px;font-size:10px;text-align:center;">${esc(e.order_type)}${e.es_repetida ? ' <span title="Mismo contrato repetido en días anteriores">🔁</span>' : ''}</span>
                <span style="color:var(--color-text);">$${esc(e.strike)}</span>
                <span style="color:var(--color-muted);">${esc(_fmtFecha(e.exp))}${_marcaEarnings(e)}</span>
                <span style="color:var(--color-text);">${esc(e.oi)}</span>
                <span style="color:var(--color-text);text-align:right;">${esc(e.premium_fmt)}</span>
            </div>`;
        }).join('') || '<div style="padding:14px;color:var(--color-muted);font-size:11px;text-align:center;">Sin entradas guardadas en este periodo</div>'}
    </div>`;
}

function loading() {
    return '<div style="padding:2rem;text-align:center;color:var(--color-muted);font-size:12px;">Cargando...</div>';
}