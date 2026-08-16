import { authHeader } from '/core/api.js';
import { tt } from '/components/tooltip.js';
import { errorMessage, esc, fmtFecha, panel } from '/core/ui.js';

/*
 * BTC Stratum. Hasta el 16/08/2026 esta página iba por libre estéticamente:
 * repetía a mano once veces la caja "surface + border + radius" (cada una con
 * su propio padding) y clavaba 49 colores hexadecimales, entre ellos 18
 * `#f23645` y 13 `#ffb800` teniendo los tokens `--color-danger` y
 * `--color-warning` definidos en themes/base.css. Con cualquier tema que no
 * fuera el oscuro por defecto -- y hay nueve -- se quedaba con la paleta
 * antigua. Ahora el envoltorio es el compartido (core/ui.js::panel) y los
 * colores salen del tema.
 */

// Única excepción deliberada: el naranja de bitcoin es color de marca del
// activo, no del tema, así que no debe cambiar con la piel de la terminal.
const BTC_NARANJA = '#f7931a';

const C = {
    ok:    'var(--color-accent)',
    info:  'var(--color-secondary)',
    warn:  'var(--color-warning)',
    bad:   'var(--color-danger)',
    muted: 'var(--color-muted)',
    text:  'var(--color-text)',
    fondo: 'var(--color-bg)',
};

/** Mismo recurso que ya usa components/sidebar.js para teñir sin clavar rgba(). */
function alpha(color, pct) {
    return 'color-mix(in srgb, ' + color + ' ' + pct + '%, transparent)';
}

/** Chart.js pinta sobre canvas y no entiende var(): hay que resolver el token
 *  en el momento de crear el gráfico. Mismo patrón que cartera.js:1299. */
function cssVar(nombre, respaldo) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
    return v || respaldo;
}

const usd = n => '$' + Number(n).toLocaleString('en-US');

// Instancias de Chart vivas, para poder destruirlas al salir de la página.
// Sin esto quedaban dos gráficos huérfanos por visita (el router destruye el
// contenedor, pero Chart.js mantiene sus propios listeners y su animación).
let _charts = [];

export function cleanup() {
    _charts.forEach(c => { try { c.destroy(); } catch (_) {} });
    _charts = [];
}

export async function render(container) {
    container.innerHTML = pageShell();
    const result = container.querySelector('#btc-result');
    const bDash  = container.querySelector('#btn-dashboard');
    const bBack  = container.querySelector('#btn-backtest');

    const activar = (activo, otro) => {
        activo.style.background = 'var(--color-accent)';
        activo.style.color      = 'var(--color-bg)';
        activo.style.border     = '1px solid var(--color-accent)';
        otro.style.background   = 'transparent';
        otro.style.color        = 'var(--color-muted)';
        otro.style.border       = '1px solid var(--color-border)';
    };

    loadDashboard(result);
    bDash.addEventListener('click', () => { activar(bDash, bBack); loadDashboard(result); });
    bBack.addEventListener('click', () => { activar(bBack, bDash); loadBacktest(result); });
}

function pageShell() {
    const boton = (id, txt, activo) =>
        '<button id="' + id + '" style="background:' + (activo ? 'var(--color-accent)' : 'transparent')
        + ';color:' + (activo ? 'var(--color-bg)' : C.muted)
        + ';border:1px solid ' + (activo ? 'var(--color-accent)' : 'var(--color-border)')
        + ';border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;'
        + 'cursor:pointer;letter-spacing:0.05em;transition:var(--transition);">' + txt + '</button>';

    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">₿ BTC STRATUM ' + tt('btc-stratum') + '</div>'
        + '<div style="color:' + C.muted + ';font-size:12px;">Modelo de acumulación RSU · Precio frente a su media de 200 semanas</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + boton('btn-dashboard', '📊 DASHBOARD', true)
        + boton('btn-backtest',  '📈 BACKTEST',  false)
        + '</div>'
        + '<div id="btc-result"></div>';
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────

async function loadDashboard(el) {
    cleanup();
    el.innerHTML = loading('Cargando datos BTC...');
    try {
        const res  = await fetch('/api/v1/btc-stratum/dashboard', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderDashboard(data);
        renderChart(data);
    } catch (e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderDashboard(data) {
    return headerSection(data)
        + alertsSection(data)
        + scoreSection(data)
        + contextoSection(data)
        + curvaturaSection(data)
        + chartSection(data)
        + halvingSection(data)
        + macroSection(data)
        + levelsSection(data)
        + stressSection(data)
        + methodologySection();
}

/** Tarjeta compacta, mismo formato que kpiCard() de rsrw.js. */
function kpiCard(label, value, sub, color) {
    return '<div style="background:' + C.fondo + ';border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;">'
        + '<div style="color:' + C.muted + ';font-size:10px;letter-spacing:0.08em;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + value + '</div>'
        + (sub ? '<div style="color:' + C.muted + ';font-size:10px;margin-top:4px;line-height:1.35;">' + sub + '</div>' : '')
        + '</div>';
}

function headerSection(data) {
    const chgColor = data.chg_24h >= 0 ? C.ok : C.bad;
    const chgStr   = (data.chg_24h >= 0 ? '+' : '') + data.chg_24h + '%';
    const z        = data.zone;
    const devColor = data.deviation >= 0 ? C.bad : C.ok;

    const precio = '<div style="padding:1rem 1.25rem;">'
        + '<div style="color:' + C.text + ';font-size:32px;font-weight:500;">' + usd(data.price) + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;margin-top:4px;">' + chgStr + ' 24h</div>'
        + '<div style="color:' + C.muted + ';font-size:11px;margin-top:6px;">Máximo del periodo: ' + usd(data.ath)
        + ' · Desde ahí: <span style="color:' + C.bad + ';">' + data.drawdown + '%</span></div>'
        + sourcesBar(data.sources)
        + '</div>';

    const score = '<div style="padding:1rem 1.25rem;">'
        + '<div style="color:' + data.rsu_signal.color + ';font-size:36px;font-weight:500;">' + data.rsu_score + '</div>'
        + '<div style="background:' + C.fondo + ';border-radius:4px;height:6px;margin:8px 0;overflow:hidden;">'
        + '<div style="height:100%;width:' + Math.max(0, Math.min(100, data.rsu_score)) + '%;background:' + data.rsu_signal.color + ';transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="color:' + data.rsu_signal.color + ';font-size:12px;letter-spacing:0.08em;">' + esc(data.rsu_signal.label) + '</div>'
        + '</div>';

    const ev = z.evidencia;
    const zona = '<div style="padding:1rem 1.25rem;">'
        + '<div style="color:' + z.color + ';font-size:18px;font-weight:500;margin-bottom:8px;">' + esc(z.zone) + '</div>'
        + '<div style="color:' + C.muted + ';font-size:11px;">Asignación del modelo: <span style="color:' + z.color + ';font-size:16px;font-weight:500;">' + z.allocation + '%</span></div>'
        + '<div style="color:' + C.muted + ';font-size:11px;margin-top:4px;">vs MA200W: <span style="color:' + devColor + ';">' + (data.deviation >= 0 ? '+' : '') + data.deviation + '%</span></div>'
        // En qué se apoya el consejo, al lado del consejo. Los seis tramos
        // anteriores no ordenaban el retorno futuro; estos cuatro sí, y
        // aguantan al partir la muestra en dos -- así que el dato se enseña.
        + (ev ? '<div style="color:' + C.muted + ';font-size:10px;margin-top:8px;padding-top:8px;border-top:1px solid var(--color-border);line-height:1.5;">'
            + 'Históricamente, en esta zona: <span style="color:' + C.text + ';">'
            + (ev.retorno_1a >= 0 ? '+' : '') + ev.retorno_1a + '%</span> de media a un año, con un '
            + '<span style="color:' + (ev.pct_perdidas > 50 ? C.bad : ev.pct_perdidas > 20 ? C.warn : C.ok) + ';">'
            + ev.pct_perdidas + '%</span> de casos en pérdidas (' + ev.n + ' sesiones)</div>' : '')
        + '</div>';

    return '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;margin-bottom:1rem;">'
        + panel({ titulo: 'BITCOIN · BTC/USD', contenido: precio, avisos: data.avisos })
        + panel({ titulo: 'RSU SCORE ' + tt('rsu-btc-score'), contenido: score, escapar: false })
        + panel({ titulo: 'ZONA ACTUAL · URGENCIA', contenido: zona })
        + '</div>';
}

function alertsSection(data) {
    if (!data.alerts || !data.alerts.length) return '';
    const filas = data.alerts.map(a =>
        '<div style="display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid var(--color-border);font-size:12px;line-height:1.45;">'
        + '<span style="font-size:15px;flex-shrink:0;">' + esc(a.icon) + '</span>'
        + '<span style="color:' + a.color + ';">' + esc(a.msg) + '</span>'
        + '</div>').join('');
    return panel({ titulo: '⚡ ALERTAS ACTIVAS', contenido: filas });
}

/*
 * El desglose del score ya no son cuatro tarjetas con pesos. Lo era hasta el
 * 16/08/2026, y medido sobre 2.953 sesiones aquellas cuatro «señales» eran en
 * realidad una y media: el MVRV era la misma recta que la MA200W reescalada
 * (correlación 0,917) y el AHR999 valía 0 en el 97% de los días. Ahora se
 * explica el único número que hay, y en qué precios están sus fronteras --
 * que es como de verdad se entiende un score: «80» no dice nada, «$112.525» sí.
 */
function scoreSection(data) {
    const d = data.score_detalle;
    if (!d) return '';
    const ev = data.zone && data.zone.evidencia;

    const barra = '<div style="padding:1.25rem 1.25rem 0.5rem;">'
        + '<div style="position:relative;height:10px;background:' + C.fondo + ';border-radius:5px;overflow:hidden;">'
        + '<div style="position:absolute;left:0;top:0;bottom:0;width:' + Math.max(0, Math.min(100, data.rsu_score)) + '%;background:' + data.zone.color + ';"></div>'
        + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-size:9px;color:' + C.muted + ';margin-top:5px;">'
        + '<span>0 · más barato</span><span>50</span><span>80</span><span>90</span><span>100 · más caro</span>'
        + '</div></div>';

    const fronteras = (d.fronteras || []).map(f =>
        '<div style="display:flex;justify-content:space-between;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:' + C.muted + ';">Entra en <span style="color:' + C.text + ';">' + esc(f.zona) + '</span> (score ' + f.score + ')</span>'
        + '<span style="color:' + C.text + ';">' + (f.precio ? usd(f.precio) : 'N/D') + '</span>'
        + '</div>').join('');

    const explica = '<div style="padding:0 1.25rem 1rem;font-size:11px;color:' + C.muted + ';line-height:1.6;">'
        + 'Mide una sola cosa: lo lejos que está el precio de su media de 200 semanas ('
        + usd(d.ma200) + '). Ahora mismo, un <span style="color:' + C.text + ';">'
        + (d.desviacion >= 0 ? '+' : '') + d.desviacion + '%</span>.'
        + (ev ? ' En este tramo, de ' + esc(d.muestra) + ', el precio estaba más alto un año después en el '
            + (100 - ev.pct_perdidas).toFixed(1) + '% de los casos (media: '
            + (ev.retorno_1a >= 0 ? '+' : '') + ev.retorno_1a + '%, sobre ' + ev.n + ' sesiones).' : '')
        + '</div>';

    return panel({
        titulo:    'QUÉ MIDE EL RSU SCORE ' + tt('rsu-btc-score'),
        subtitulo: data.rsu_score + '/100',
        contenido: barra + explica + fronteras,
        escapar:   false,
    });
}

/*
 * MVRV, Puell y hashrate siguen aquí, pero fuera del score. Antes iban dentro
 * con pesos (30/20/10); medido el 16/08/2026, ninguno mejoraba su capacidad de
 * ordenar el retorno futuro y dos la empeoraban. Un dato que informa no tiene
 * por qué entrar en la fórmula. A cambio, el MVRV que se ve aquí es on-chain
 * de verdad por primera vez -- antes era el precio frente a su media larga
 * disfrazado de métrica de cadena.
 */
function contextoSection(data) {
    const c = data.contexto;
    if (!c) return '';
    const tarjetas = [];

    if (c.mvrv_z != null) {
        tarjetas.push(kpiCard('MVRV Z-SCORE ' + tt('mvrv-z'), c.mvrv_z.toFixed(2),
            'Por debajo de 0, el poseedor medio está en pérdidas'
            + (c.precio_realizado ? ' · Precio medio de compra: ' + usd(c.precio_realizado) : ''),
            c.mvrv_z < 0 ? C.ok : c.mvrv_z > 3 ? C.bad : C.text));
    }
    if (c.puell != null) {
        tarjetas.push(kpiCard('PUELL MULTIPLE ' + tt('puell-multiple'), c.puell,
            'Ingresos de mineros: $' + c.puell_ingresos + 'M frente a su media anual de $' + c.puell_media + 'M',
            c.puell < 0.5 ? C.ok : c.puell < 1 ? C.warn : C.text));
    }
    if (c.hashrate_ehs != null) {
        tarjetas.push(kpiCard('HASHRATE', c.hashrate_ehs + ' EH/s',
            c.hash_ribbon != null
                ? 'Frente a su media de 30 días: ' + c.hash_ribbon + (c.hash_ribbon < 1 ? ' · hay mineros apagando' : ' · red creciendo')
                : 'Potencia de cálculo de la red',
            c.hash_ribbon != null && c.hash_ribbon < 0.97 ? C.warn : C.text));
    }
    if (!tarjetas.length) return '';

    const fuentes = Object.entries(c.fuentes || {}).filter(([, v]) => v)
        .map(([k, v]) => esc(k.toUpperCase()) + ': ' + esc(v)).join(' · ');

    return panel({
        titulo:    'CONTEXTO ON-CHAIN',
        subtitulo: 'no entra en el score',
        contenido: '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;padding:1.25rem;">'
            + tarjetas.join('') + '</div>'
            + (fuentes ? '<div style="padding:0 1.25rem 1rem;font-size:10px;color:' + C.muted + ';">' + fuentes + '</div>' : ''),
        escapar:   false,
    });
}

function curvaturaSection(data) {
    const curv  = data.curvature;
    const color = curv.slope > 0.2 ? C.ok : curv.slope < -0.2 ? C.bad : C.warn;
    const dato  = (k, v, col) => '<div><span style="color:' + C.muted + ';">' + k + ': </span><span style="color:' + (col || C.text) + ';">' + v + '</span></div>';
    const cuerpo = '<div style="display:flex;gap:2rem;flex-wrap:wrap;font-size:12px;padding:1.25rem;">'
        + dato('MA200W', usd(curv.ma_value))
        + dato('Pendiente', curv.slope + '% (30d)', color)
        + dato('Tendencia', esc(curv.trend), color)
        + dato('Aceleración', esc(curv.acceleration), curv.acceleration === 'ACELERANDO' ? C.ok : C.warn)
        + '</div>';
    return panel({ titulo: 'CURVATURA MA200W', contenido: cuerpo });
}

function chartSection() {
    return panel({
        titulo:    'PRECIO BTC · MA200W · ZONAS (3 AÑOS)',
        subtitulo: 'Semanal',
        contenido: '<div style="padding:16px;"><canvas id="btc-chart" height="200"></canvas></div>',
    });
}

function halvingSection(data) {
    const h = data.halving;
    const phaseColor = h.phase === 'ACUMULACIÓN'  ? C.ok
        : h.phase === 'BULL TEMPRANO' ? C.info
        : h.phase === 'BULL AVANZADO' ? C.warn
        : h.phase === 'DISTRIBUCIÓN'  ? C.warn
        : C.bad;

    const cuerpo = '<div style="display:flex;gap:2rem;flex-wrap:wrap;align-items:center;padding:1.25rem;">'
        + '<div style="flex:1;min-width:200px;">'
        + '<div style="color:' + phaseColor + ';font-size:18px;font-weight:500;margin-bottom:4px;">' + esc(h.phase) + '</div>'
        + '<div style="color:' + C.muted + ';font-size:11px;">Progreso del ciclo: <span style="color:' + C.text + ';">' + h.progress_pct + '%</span></div>'
        + '<div style="color:' + C.muted + ';font-size:11px;">Días desde el halving: <span style="color:' + C.text + ';">' + h.days_since + '</span></div>'
        + '<div style="color:' + C.muted + ';font-size:11px;">Días hasta el próximo: <span style="color:' + C.warn + ';">' + h.days_to_next + '</span> (' + esc(h.next_halving) + ')</div>'
        + '</div>'
        + '<div style="flex:2;min-width:220px;">'
        + '<div style="background:' + C.fondo + ';border-radius:4px;height:8px;overflow:hidden;">'
        + '<div style="height:100%;width:' + Math.max(0, Math.min(100, h.progress_pct)) + '%;background:linear-gradient(90deg,' + C.ok + ',' + phaseColor + ');"></div>'
        + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-size:10px;color:' + C.muted + ';margin-top:4px;">'
        + '<span>' + esc(h.last_halving) + '</span><span>' + esc(h.next_halving) + '</span>'
        + '</div>'
        + '</div>'
        + '</div>';

    // La fecha del próximo halving no se puede saber de antemano: depende del
    // ritmo al que se minen los bloques que faltan. Antes estaba clavada a
    // mano y nada lo decía.
    const avisos = h.fuente
        ? [{ tipo: 'antiguo', mensaje: 'La fecha del próximo halving es una estimación: ' + h.fuente + '.' }]
        : null;

    return panel({ titulo: 'CICLO HALVING ' + tt('halving-cycle'), contenido: cuerpo, avisos, escapar: false });
}

function macroSection(data) {
    const m = data.macro;
    // m.dxy puede venir null si la fuente falló: se muestra "N/D" en gris, no
    // un color engañoso (null < 50 evaluaría true en JS por coerción a 0).
    const hay = m && m.dxy != null;
    const statusColor = !hay ? C.muted
        : m.status === 'EXPANSIVO' ? C.ok
        : m.status === 'NEUTRAL'   ? C.warn
        : C.bad;

    const anios = hay && m.liquidez_base ? (m.liquidez_base / 252).toFixed(0) : null;
    const cuerpo = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;padding:1.25rem;">'
        + kpiCard('DÓLAR (DXY)', hay ? m.dxy : 'N/D',
                  'Un dólar fuerte suele ir en contra de bitcoin',
                  hay ? (m.dxy_score < 50 ? C.ok : C.bad) : C.muted)
        + kpiCard('LIQUIDEZ', hay ? m.liquidity_score + '/100' : 'N/D',
                  hay ? ('Percentil del bono largo (TLT) frente a sus últimos ' + anios + ' años') : 'Sin datos ahora mismo',
                  hay ? statusColor : C.muted)
        + kpiCard('ENTORNO', hay ? esc(m.status) : 'Sin datos',
                  'Lectura combinada de las condiciones de financiación',
                  statusColor)
        + '</div>';
    return panel({ titulo: 'CONDICIONES MACRO', contenido: cuerpo });
}

/*
 * Los niveles son ahora las fronteras de zona REALES, las mismas que calcula
 * el backend y que enseña el desglose del score. Antes esta tabla listaba una
 * escalera de ±25%/±50% sobre la MA200W con los nombres de las zonas viejas
 * pegados encima -- así que decía que «OPORTUNIDAD MÁXIMA» estaba en $31.976
 * mientras el score situaba esa frontera en otro sitio. Dos precios distintos
 * para el mismo concepto, y ninguna forma de saber cuál valía.
 */
function levelsSection(data) {
    const price = data.price;
    const zonaColor = {
        'ACUMULACIÓN': alpha(C.ok, 70), 'PRECAUCIÓN': C.warn, 'RIESGO ALTO': C.bad,
    };
    const rows = [{ label: 'MEDIA DE 200 SEMANAS', value: data.ma200, color: C.info }]
        .concat(((data.score_detalle || {}).fronteras || []).map(f => ({
            label: 'ENTRA EN ' + f.zona + ' (score ' + f.score + ')',
            value: f.precio,
            color: zonaColor[f.zona] || C.muted,
        })))
        .filter(r => r.value)
        .sort((a, b) => a.value - b.value);
    const filas = rows.map(r => {
        const dist      = r.value ? ((price - r.value) / r.value * 100) : null;
        const esActual  = r.value && Math.abs(price - r.value) < r.value * 0.02;
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);'
            + (esActual ? 'background:' + alpha(r.color, 8) + ';' : '') + '">'
            + '<div style="color:' + r.color + ';font-size:11px;">' + r.label + (esActual ? ' · aquí' : '') + '</div>'
            + '<div style="text-align:right;">'
            + '<div style="color:' + C.text + ';font-size:13px;font-weight:500;">' + usd(r.value) + '</div>'
            // Se dice en qué dirección, no solo el signo: "+96,8%" a secas
            // sobre un nivel que está POR DEBAJO del precio se lee al revés.
            + (dist != null ? '<div style="color:' + (dist >= 0 ? C.bad : C.ok) + ';font-size:10px;">El precio está un '
                + Math.abs(dist).toFixed(1) + '% ' + (dist >= 0 ? 'por encima' : 'por debajo') + '</div>' : '')
            + '</div></div>';
    }).join('');
    return panel({ titulo: 'A QUÉ PRECIO CAMBIA DE ZONA', contenido: filas });
}

function stressSection(data) {
    const filas = (data.stress || []).map(sc => {
        const sev = sc.severity === 'extreme' ? C.bad : sc.severity === 'high' ? C.warn : alpha(C.warn, 70);
        return '<div style="padding:12px 14px;border-bottom:1px solid var(--color-border);">'
            + '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:6px;">'
            + '<div style="color:' + sev + ';font-size:12px;font-weight:500;">' + esc(sc.name) + '</div>'
            + '<div style="color:' + C.muted + ';font-size:10px;text-align:right;flex-shrink:0;">' + esc(sc.probability) + '</div>'
            + '</div>'
            + '<div style="color:' + C.muted + ';font-size:11px;margin-bottom:4px;">' + esc(sc.description) + '</div>'
            + '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:11px;">'
            + '<span style="color:' + C.muted + ';">Precio resultante: <span style="color:' + sev + ';">' + usd(sc.target) + '</span></span>'
            + '<span style="color:' + C.muted + ';">Caída: <span style="color:' + sev + ';">−' + sc.drop_pct + '%</span></span>'
            + '</div>'
            + '<div style="color:' + C.muted + ';font-size:10px;margin-top:4px;">💡 ' + esc(sc.hedge) + '</div>'
            + '</div>';
    }).join('');
    return panel({
        titulo:    'STRESS TEST · ESCENARIOS ADVERSOS ' + tt('stress-test'),
        contenido: filas,
        escapar:   false,
        avisos: [{ tipo: 'parcial', mensaje:
            'Las probabilidades de esta tabla son estimaciones subjetivas escritas a mano, no el resultado '
            + 'de ningún cálculo. Sirven para pensar en la gestión del riesgo, no como pronóstico.' }],
    });
}

function methodologySection() {
    const cuerpo = '<div style="color:' + C.muted + ';font-size:11px;line-height:1.8;padding:1.25rem;">'
        + '<strong style="color:' + C.text + ';">Qué mide.</strong> El RSU Score responde a una sola pregunta: ¿está bitcoin caro o barato frente a su media de 200 semanas? Esa media es su referencia de largo plazo más seguida, y la distancia a ella se convierte en una escala de 0 a 100 donde 0 es lo más barato que se ha visto y 100 lo más caro.<br><br>'
        + '<strong style="color:' + C.text + ';">Por qué un solo indicador y no cuatro.</strong> Hasta agosto de 2026 el score mezclaba cuatro medidas con pesos (media de 200 semanas, MVRV, Puell y AHR999). Al comprobarlo con casi ocho años de datos aparecieron dos cosas: el MVRV que se estaba usando no era un dato de la cadena de bloques, sino la misma distancia a la media multiplicada por una constante, y el AHR999 valía cero en el 97% de los días. Ordenar cuatro medidas de las que dos eran la misma daba un resultado <em>peor</em> que usar una sola bien construida. Se probaron además el Puell real, el hashrate y la posición en el ciclo de halving: ninguno mejoraba el resultado.<br><br>'
        + '<strong style="color:' + C.text + ';">Qué pasó con los otros indicadores.</strong> Siguen en la página, en «Contexto on-chain», pero fuera del número. Informan de cosas reales —si los mineros están bajo presión, a qué precio medio se movieron las monedas por última vez— y ahora el MVRV es un dato de cadena de verdad, no una estimación a partir del precio.<br><br>'
        + '<strong style="color:' + C.text + ';">Los tramos.</strong> Las cuatro zonas no son números redondos elegidos a ojo: salen de mirar qué pasó después, en 2.588 sesiones entre julio de 2018 y agosto de 2025. Para comprobar que no era casualidad, se partió la muestra por la mitad y se repitió el cálculo en cada trozo: el orden se mantiene en los dos. Aun así son unos dos ciclos de halving, que es poca historia para un activo que se mueve en ciclos: tómalos como una referencia, no como una regla.<br><br>'
        + '<strong style="color:' + C.bad + ';">Esto no es asesoramiento financiero. Bitcoin es un activo de alto riesgo: invierte solo lo que puedas permitirte perder.</strong>'
        + '</div>';
    return panel({ titulo: 'METODOLOGÍA RSU', contenido: cuerpo });
}

// ── BACKTEST ──────────────────────────────────────────────────────────────────

async function loadBacktest(el) {
    cleanup();
    el.innerHTML = loading('Ejecutando backtest histórico...');
    try {
        const res  = await fetch('/api/v1/btc-stratum/backtest', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderBacktest(data);
        renderBacktestChart(data);
    } catch (e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderBacktest(data) {
    const results = data.results || [];
    const bh      = results[0] ? results[0].bh_return : 0;
    const anios   = data.period_days ? (data.period_days / 365) : null;

    const tarjetas = results.map(r => {
        const color      = r.total_return > bh ? C.ok : r.total_return > 0 ? C.warn : C.bad;
        const alphaColor = r.alpha > 0 ? C.ok : C.bad;
        return '<div style="background:' + C.fondo + ';border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
            + '<div style="color:' + C.muted + ';font-size:10px;margin-bottom:6px;">' + esc(r.label) + '</div>'
            + '<div style="color:' + color + ';font-size:22px;font-weight:500;">' + (r.total_return >= 0 ? '+' : '') + r.total_return + '%</div>'
            + '<div style="color:' + C.muted + ';font-size:11px;margin-top:4px;">Capital final: <span style="color:' + C.text + ';">' + usd(r.final_value) + '</span></div>'
            + '<div style="color:' + C.muted + ';font-size:11px;">Frente a comprar y mantener: <span style="color:' + alphaColor + ';">' + (r.alpha > 0 ? '+' : '') + r.alpha + '%</span></div>'
            + '<div style="color:' + C.muted + ';font-size:11px;">Operaciones: ' + r.n_buys + ' compras · ' + r.n_sells + ' ventas</div>'
            + '</div>';
    }).join('');

    const cuerpo = '<div style="padding:1.25rem;">'
        + '<div style="color:' + C.muted + ';font-size:11px;margin-bottom:1rem;">Capital inicial: $10.000 · Estrategia: invertir la mitad del capital disponible cuando el RSU Score baje del umbral, y vender cuando supere ' + (data.venta_umbral || 90) + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;">' + tarjetas + '</div>'
        + '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);font-size:11px;color:' + C.muted + ';">'
        + 'Comprar y mantener bitcoin en el mismo periodo: <span style="color:' + C.text + ';">' + (bh >= 0 ? '+' : '') + bh + '%</span></div>'
        + '</div>';

    const avisos = [
        { tipo: 'parcial', mensaje:
            'El backtest supone ejecución perfecta: sin comisiones, sin deslizamiento de precio y operando '
            + 'siempre al cierre del día. En la práctica los resultados serían peores.' },
    ];
    if (data.period_start) {
        avisos.push({ tipo: 'antiguo', mensaje:
            'Periodo evaluado: desde ' + data.period_start + (anios ? ' (' + anios.toFixed(1) + ' años' : '')
            + (anios ? ', apenas dos ciclos de halving completos)' : '')
            + '. Antes de esa fecha la media de 200 semanas todavía no tenía histórico suficiente.' });
    }

    const resumen = panel({
        titulo:    'BACKTEST HISTÓRICO · RSU STRATUM ' + tt('btc-backtest'),
        contenido: cuerpo,
        avisos,
        escapar:   false,
    });

    const grafico = panel({
        titulo:    'RSU SCORE HISTÓRICO · SEÑALES DE COMPRA Y VENTA',
        contenido: '<div style="padding:16px;"><canvas id="backtest-chart" height="200"></canvas></div>',
    });

    const trades = results[1] ? (results[1].trades || []) : [];
    const cols   = 'grid-template-columns:minmax(90px,1fr) 70px minmax(90px,1fr) 60px;';
    const tabla  = trades.length ? panel({
        // Sin esc() aquí: panel() ya escapa el título por defecto, y hacerlo
        // dos veces convertía el "<" del umbral en un "&lt;" visible.
        titulo:    'ÚLTIMAS OPERACIONES · ' + ((results[1] || {}).label || ''),
        contenido: '<div style="display:grid;' + cols + 'gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:' + C.muted + ';">'
            + '<div>FECHA</div><div>TIPO</div><div>PRECIO</div><div>RSU</div></div>'
            + trades.map(t => '<div style="display:grid;' + cols + 'gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<div style="color:' + C.muted + ';">' + esc(fmtFecha(t.date)) + '</div>'
                + '<div style="color:' + (t.type === 'BUY' ? C.ok : C.bad) + ';font-weight:500;">' + (t.type === 'BUY' ? 'COMPRA' : 'VENTA') + '</div>'
                + '<div style="color:' + C.text + ';">' + usd(t.price) + '</div>'
                + '<div style="color:' + C.muted + ';">' + t.rsu + '</div>'
                + '</div>').join(''),
    }) : '';

    return resumen + grafico + tabla;
}

// ── GRÁFICOS ──────────────────────────────────────────────────────────────────

/** Ejes y rejilla, resueltos desde el tema en cada render. */
function ejes(opts = {}) {
    const tinta   = cssVar('--color-muted', '#555');
    const rejilla = alpha(tinta, 15);
    return {
        x: { ticks: { color: tinta, font: { size: 9 }, maxTicksLimit: 8, maxRotation: 0 }, grid: { color: rejilla } },
        y: Object.assign({ ticks: { color: tinta, font: { size: 9 } }, grid: { color: rejilla } }, opts.y || {}),
    };
}

function leyenda() {
    return { display: true, position: 'top', labels: { color: cssVar('--color-muted', '#666'), font: { size: 10 }, boxWidth: 12 } };
}

function renderChart(data) {
    loadChartJs(() => {
        const ctx = document.getElementById('btc-chart');
        if (!ctx || !data.chart_data || !data.chart_data.length) return;
        const d       = data.chart_data;
        const acento  = cssVar('--color-accent', '#00ffad');
        const aviso   = cssVar('--color-warning', '#ffb800');
        const linea = (label, campo, color, ancho, dash) => ({
            label, data: d.map(x => x[campo]), borderColor: color, borderWidth: ancho,
            pointRadius: 0, fill: false, tension: 0.3, borderDash: dash || [],
        });

        _charts.push(new Chart(ctx, {
            type: 'line',
            data: {
                labels: d.map(x => x.date),
                datasets: [
                    linea('BTC/USD', 'price',   BTC_NARANJA, 2),
                    linea('MA200W',  'ma200',   acento,      2),
                    linea('−25% MA', 'minus25', alpha(acento, 65), 1,   [4, 4]),
                    linea('−50% MA', 'minus50', alpha(acento, 40), 1.5, [2, 4]),
                    linea('+25% MA', 'plus25',  aviso,       1,   [4, 4]),
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: leyenda(),
                    tooltip: {
                        backgroundColor: cssVar('--color-surface', '#111'),
                        borderColor: cssVar('--color-border', '#333'), borderWidth: 1,
                        titleColor: cssVar('--color-muted', '#aaa'), bodyColor: cssVar('--color-text', '#ccc'),
                        callbacks: { label: item => item.dataset.label + ': ' + usd(item.parsed.y) },
                    },
                },
                scales: ejes({ y: { ticks: { color: cssVar('--color-muted', '#555'), font: { size: 9 }, callback: v => usd(v) } } }),
            },
        }));
    });
}

function renderBacktestChart(data) {
    loadChartJs(() => {
        const ctx = document.getElementById('backtest-chart');
        if (!ctx || !data.rsu_series || !data.rsu_series.length) return;
        const labels = data.rsu_series.map(d => d.date);
        const acento = cssVar('--color-accent', '#00ffad');
        const umbral = (valor, color) => ({
            label: 'Umbral ' + valor, data: labels.map(() => valor),
            borderColor: color, borderWidth: 1, pointRadius: 0, borderDash: [4, 4], fill: false,
        });

        _charts.push(new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'RSU Score', data: data.rsu_series.map(d => d.value),
                      borderColor: cssVar('--color-secondary', '#00d9ff'),
                      backgroundColor: alpha(cssVar('--color-secondary', '#00d9ff'), 8),
                      borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 },
                    umbral(20, acento),
                    umbral(40, cssVar('--color-warning', '#ffb800')),
                    umbral(80, cssVar('--color-danger', '#f23645')),
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: leyenda() },
                scales: ejes({ y: { min: 0, max: 100, ticks: { color: cssVar('--color-muted', '#555'), font: { size: 9 } } } }),
            },
        }));
    });
}

function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s  = document.createElement('script');
    s.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = cb;
    document.head.appendChild(s);
}

// ── AUXILIARES ────────────────────────────────────────────────────────────────

function sourcesBar(sources) {
    if (!sources) return '';
    return '<div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap;">'
        + Object.entries(sources).map(([k, v]) =>
            '<span style="font-size:9px;background:' + alpha(C.info, 8) + ';border:1px solid ' + alpha(C.info, 20)
            + ';border-radius:3px;padding:1px 6px;color:' + C.muted + ';">'
            + esc(k.toUpperCase()) + ': ' + esc(v) + '</span>').join('')
        + '</div>';
}

function loading(msg) {
    return '<div style="padding:2rem;color:' + C.muted + ';font-size:12px;text-align:center;">'
        + '<div style="font-size:24px;margin-bottom:8px;color:' + BTC_NARANJA + ';">₿</div>'
        + esc(msg) + '</div>';
}
