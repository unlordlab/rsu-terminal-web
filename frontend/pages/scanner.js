import { authHeader } from '/core/api.js';
import { isRateLimitMessage, errorMessage, esc } from '/core/ui.js';
import { tt } from '/components/tooltip.js';

const PHASE_OPTIONS = [
    { value: '', label: 'Todas' },
    { value: '2', label: 'Fase 2 · Avance' },
    { value: '1', label: 'Fase 1 · Acumulación/Giro' },
    { value: '3', label: 'Fase 3 · Distribución' },
    { value: '4', label: 'Fase 4 · Declive' },
];

// LOS CRITERIOS, DECLARADOS UNA SOLA VEZ.
//
// Antes había CUATRO listas paralelas que había que mantener a mano: la del
// panel, la del cableado de clics, la que construía la consulta y la que
// leía los valores. Se desincronizaron, y el resultado es que `absorcion` y
// `l3zona` estaban en el panel pero NO en el cableado: sus tarjetas no hacían
// absolutamente nada al pulsarlas.
//
// `l3zona` es además el filtro que el usuario pidió el 14/08 (la zona baja del
// indicador RSU). Se verificó el backend de punta a punta y nunca se comprobó
// que el botón se pudiera pulsar, así que llegó a producción inservible.
//
// Con una sola lista, añadir un criterio y olvidarse de cablearlo deja de ser
// posible: el panel y el cableado salen de aquí.
const CRITERIOS = [
    { id: 'rvol',      tipo: 'numero', param: 'rvol_min',      etiqueta: 'RVOL ≥',              tip: 'rvol',              ph: '1.5', paso: '0.1', min: '0' },
    { id: 'rs',        tipo: 'numero', param: 'rs_min',        etiqueta: 'RS Percentile ≥',     tip: 'rs-rating',         ph: '70',  paso: '1',   min: '0', max: '100' },
    { id: 'score',     tipo: 'numero', param: 'score_min',     etiqueta: 'Score Técnico ≥',     tip: 'score-tecnico',     ph: '60',  paso: '1',   min: '0', max: '100' },
    // Máximo 10 por construcción (la ventana son 10 sesiones), pero en 6.012
    // observaciones reales el máximo visto es 7 y solo una vez: pedir 8 o más
    // devuelve lista vacía siempre. El apunte de debajo lo dice para que un
    // resultado vacío no se confunda con un módulo roto.
    { id: 'absorcion', tipo: 'numero', param: 'absorcion_min', etiqueta: 'Días de Absorción ≥', tip: 'scanner-absorcion', ph: '3',   paso: '1',   min: '0', max: '10',
      nota: 'De 0 a 10; en la práctica casi nada pasa de 5' },
    { id: 'phase',     tipo: 'select', param: 'phase',         etiqueta: 'FASE WEINSTEIN',      tip: 'market-phase',
      opciones: () => PHASE_OPTIONS.map(o => '<option value="' + o.value + '">' + o.label + '</option>').join('') },
    { id: 'sector',    tipo: 'select', param: 'sector',        etiqueta: 'SECTOR',
      opciones: () => '<option value="">Cargando sectores...</option>' },
    { id: 'newhigh',   tipo: 'toggle', param: 'new_high_only', etiqueta: '🔥 MÁXIMOS 52 SEMANAS', tip: 'new-high-52w',    nota: 'Aprox. a ATH' },
    { id: 'l3zona',    tipo: 'toggle', param: 'l3_zona_baja',  etiqueta: 'ZONA BAJA DEL INDICADOR RSU', tip: 'rsu-flow',  nota: 'Entre 10 y 20' },
];

// ── Presets: combinaciones de criterios guardadas con nombre ────────────────
//
// Un preset ES una cadena de consulta, la misma que el deep-link. No hace
// falta serializar el estado del panel: aplicarlo es lo mismo que entrar por
// un enlace, y guardarlo es lo mismo que leer la URL.
//
// En localStorage y no en la base de usuarios a propósito: se quería tenerlo
// hoy, no tabla + endpoints + migración. Se pierden al cambiar de navegador,
// y eso se dice en pantalla en vez de dejar que el usuario lo descubra.
const PRESETS_KEY = 'rsu_scanner_presets';
const PRESETS_MAX = 12;
const PRESET_NOMBRE_MAX = 32;

function leerPresets() {
    try {
        const crudo = JSON.parse(localStorage.getItem(PRESETS_KEY) || '[]');
        // Se valida la forma: localStorage lo puede tocar cualquiera, y un
        // objeto raro aquí rompería el panel entero al pintarlo.
        return Array.isArray(crudo)
            ? crudo.filter(p => p && typeof p.nombre === 'string' && typeof p.qs === 'string')
                   .slice(0, PRESETS_MAX)
            : [];
    } catch (_) {
        return [];
    }
}

function guardarPresets(lista) {
    try {
        localStorage.setItem(PRESETS_KEY, JSON.stringify(lista.slice(0, PRESETS_MAX)));
        return true;
    } catch (_) {
        return false;   // modo privado o cuota llena: se avisa, no se finge
    }
}

let _scannerData = null;
let _scannerSort = { key: 'score_tecnico', dir: -1 };

function sortRows(rows, sortState) {
    const { key, dir } = sortState;
    return [...rows].sort((a, b) => {
        let av = a[key], bv = b[key];
        if (typeof av === 'string') {
            av = (av || '').toLowerCase();
            bv = (bv || '').toLowerCase();
        } else {
            av = av == null ? -Infinity : av;
            bv = bv == null ? -Infinity : bv;
        }
        if (av < bv) return -1 * dir;
        if (av > bv) return  1 * dir;
        return 0;
    });
}

function sortArrow(key) {
    if (_scannerSort.key !== key) return '';
    return _scannerSort.dir === 1 ? ' ▲' : ' ▼';
}

window.__scannerSort = function(key) {
    if (_scannerSort.key === key) _scannerSort.dir *= -1;
    else { _scannerSort.key = key; _scannerSort.dir = -1; }
    const el = document.getElementById('scanner-result');
    if (el && _scannerData) renderResults(el, _scannerData);
};

export async function render(container) {
    container.innerHTML = pageHeader()
        + criteriaPanel()
        + '<div id="scanner-meta" style="color:var(--color-muted);font-size:11px;margin-bottom:0.75rem;"></div>'
        + '<div id="scanner-result"></div>'
        + '<div id="scanner-divergencia" style="margin-top:1.5rem;"></div>'
        + '<div id="scanner-transiciones" style="margin-top:1.5rem;"></div>';

    // Los filtros de la URL se LEEN AQUÍ, antes de cualquier await. Se APLICAN
    // después de cargar el universo, porque un ?sector=... necesita que sus
    // opciones existan ya. Leerlos después del await es frágil: cualquier
    // navegación que ocurra mientras tanto -- un redirect a /login si la
    // sesión ha caducado, por ejemplo -- reescribe la URL y se los lleva por
    // delante. Detectado al probarlo en el navegador, que hizo exactamente eso.
    const filtrosUrl = new URLSearchParams(window.location.search);

    setupPanel(container);
    await loadUniverseMeta(container);
    aplicarUrl(container, filtrosUrl);
    runFilter(container); // sin criterios = universo completo ordenado por score
    loadTransiciones(container);
    loadDivergencia(container);
}

// Grandes contra pequeñas.
//
// El scan ya calculaba amplitud, pero sobre el universo COMBINADO -- y ahí una
// mitad tapa a la otra por construcción. Separadas aparece la lectura clásica:
// cuando las grandes siguen fuertes y las pequeñas se deterioran, el liderazgo
// se está estrechando.
async function loadDivergencia(container) {
    const el = container.querySelector('#scanner-divergencia');
    if (!el) return;
    try {
        const res  = await fetch('/api/v1/scanner/divergencia', { headers: authHeader() });
        const data = await res.json();
        el.innerHTML = data.ok
            ? renderDivergencia(data)
            : shellTrans('Grandes contra pequeñas',
                '<div style="padding:0.9rem 1rem;color:var(--color-muted);font-size:12px;">'
                + esc(data.error || 'Sin datos.') + '</div>', 'divergencia-universos');
    } catch (e) {
        el.innerHTML = shellTrans('Grandes contra pequeñas', errorMessage(e.message), 'divergencia-universos');
    }
}

function renderDivergencia(d) {
    const h = d.hoy;
    const color = d.estado === 'GRANDES' ? '#ffb800'
                : d.estado === 'PEQUEÑAS' ? 'var(--color-accent)' : 'var(--color-muted)';
    const tarjeta = (etq, val, sub) =>
        '<div style="flex:1;min-width:150px;padding:0.9rem 1rem;border-right:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:5px;">' + etq + '</div>'
        + '<div style="color:var(--color-text);font-size:19px;">' + val + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + sub + '</div></div>';

    // La brecha con su signo: positiva = las grandes aguantan mejor.
    const signo = h.brecha > 0 ? '+' : '';
    const serie = d.serie.map(x => x.brecha);
    const max = Math.max(...serie.map(Math.abs), d.umbral);
    const W = 260, H = 40;
    const pts = serie.map((v, i) =>
        (i / Math.max(serie.length - 1, 1) * W).toFixed(1) + ',' + (H / 2 - v / max * (H / 2)).toFixed(1)).join(' ');
    const grafico = '<div style="padding:0.9rem 1rem;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:6px;">BRECHA, ÚLTIMAS ' + serie.length + ' SESIONES</div>'
        + '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="max-width:100%;" aria-hidden="true">'
        + '<line x1="0" y1="' + (H / 2) + '" x2="' + W + '" y2="' + (H / 2) + '" stroke="var(--color-border)" stroke-width="1"/>'
        + '<polyline points="' + pts + '" fill="none" stroke="' + color + '" stroke-width="1.4"/></svg></div>';

    return shellTrans('GRANDES CONTRA PEQUEÑAS',
        '<div style="display:flex;flex-wrap:wrap;border-bottom:1px solid var(--color-border);">'
        + tarjeta('S&amp;P 500 SOBRE SU SMA50', h.sp500 + '%', 'las 500 grandes')
        + tarjeta('RUSSELL 2000 SOBRE SU SMA50', h.russell + '%', 'las pequeñas')
        + tarjeta('BRECHA', '<span style="color:' + color + ';">' + signo + h.brecha + '</span>',
                  'notable a partir de ' + d.umbral)
        + '</div>'
        + '<div style="padding:0.8rem 1rem;color:' + color + ';font-size:11px;line-height:1.5;border-bottom:1px solid var(--color-border);">'
        + esc(d.lectura) + '</div>'
        + grafico
        + '<div style="padding:7px 14px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + 'Sesión del ' + esc(h.date) + ' · ' + d.sesiones + ' sesiones comparadas · ' + esc(d.freshness || '') + '</div>',
        'divergencia-universos');
}

// Quién ACABA de entrar en fase de avance, no quién está en ella.
//
// La tabla de arriba es una foto: un valor en fase 2 se ve igual lleve seis
// meses ahí o haya entrado ayer, y en Weinstein esa diferencia es casi todo --
// el recorrido grande está al principio del avance. Sale del histórico que
// snapshots.db ya venía guardando desde el 27/07/2026, así que no cuesta
// ninguna descarga.
async function loadTransiciones(container) {
    const el = container.querySelector('#scanner-transiciones');
    if (!el) return;
    try {
        const res  = await fetch('/api/v1/scanner/transiciones?sesiones=5', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) {
            el.innerHTML = shellTrans('Sin histórico suficiente todavía',
                '<div style="padding:0.9rem 1rem;color:var(--color-muted);font-size:12px;">'
                + esc(data.error || 'Hacen falta al menos dos sesiones guardadas.')
                + ' Se va acumulando solo, una fila por sesión.</div>', 'cambios-de-fase');
            return;
        }
        el.innerHTML = renderTransiciones(data);
    } catch (e) {
        el.innerHTML = shellTrans('Cambios de fase', errorMessage(e.message), 'cambios-de-fase');
    }
}

// Envoltorio de las dos secciones nuevas. La clave del tooltip va como
// parámetro: clavarla haría que la sección de divergencia mostrara la ayuda de
// los cambios de fase, que es peor que no tener ayuda.
function shellTrans(titulo, cuerpo, claveTooltip) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">'
        + esc(titulo) + (claveTooltip ? ' ' + tt(claveTooltip) : '') + '</div>' + cuerpo + '</div>';
}

function renderTransiciones(d) {
    const bloque = (titulo, filas, color, vacio) => {
        if (!filas.length) return '<div style="flex:1;min-width:260px;padding:0.9rem 1rem;">'
            + '<div style="color:' + color + ';font-size:11px;letter-spacing:0.06em;margin-bottom:0.5rem;">' + titulo + '</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">' + vacio + '</div></div>';
        return '<div style="flex:1;min-width:260px;padding:0.9rem 1rem;">'
            + '<div style="color:' + color + ';font-size:11px;letter-spacing:0.06em;margin-bottom:0.5rem;">' + titulo + ' (' + filas.length + ')</div>'
            + filas.slice(0, 10).map(r =>
                '<div style="display:grid;grid-template-columns:64px 1fr 46px;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                + '<span onclick="goToResearch(\'' + esc(r.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);">' + esc(r.ticker) + '</span>'
                + '<span style="color:var(--color-muted);font-size:10px;">' + esc(r.desde_label || '—') + ' → ' + esc(r.hasta_label || '—') + '</span>'
                + '<span style="color:var(--color-text);text-align:right;" title="Percentil de fuerza relativa">' + (r.rs_pct != null ? r.rs_pct : '—') + '</span>'
                + '</div>').join('')
            + '</div>';
    };
    // La ventana REAL, no la pedida: con el histórico a medio llenar, anunciar
    // "5 sesiones" cuando solo hay 3 sería mentir sobre el periodo mirado.
    const pie = '<div style="padding:7px 14px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + 'Comparando ' + esc(d.desde_fecha) + ' con ' + esc(d.hasta_fecha) + ' · ' + d.sesiones + ' '
        + (d.sesiones === 1 ? 'sesión' : 'sesiones') + ' · ' + d.comparables + ' valores con fase confirmada en las dos fechas'
        + (d.sesiones < d.sesiones_pedidas ? ' · el histórico todavía se está llenando' : '')
        + '</div>';
    return shellTrans('CAMBIOS DE FASE',
        '<div style="display:flex;flex-wrap:wrap;">'
        + bloque('ENTRAN EN AVANCE', d.entradas, 'var(--color-accent)', 'Ninguno en esta ventana.')
        + bloque('SALEN DE AVANCE', d.salidas, '#f23645', 'Ninguno en esta ventana.')
        + '</div>' + pie, 'cambios-de-fase');
}

// La fase SEMANAL, que el scan nocturno ya calculaba y nadie pintaba.
//
// La diaria se voltea con ruido; la semanal es la escala en la que Weinstein
// trabajaba de verdad. Cuando COINCIDEN no se dice nada -- sería repetir el
// mismo dato en dos sitios. Solo se marca la DISCREPANCIA, que es lo
// informativo: normalmente significa que el giro diario aún no se ha
// consolidado en el marco largo.
function fasesemanal(r) {
    if (r.phase_weekly == null || r.phase_weekly === r.phase) return '';
    return '<span style="color:var(--color-muted);font-size:9px;" title="'
         + esc('En gráfico semanal sigue en ' + (r.phase_weekly_label || 'otra fase')
               + ' — el giro diario aún no se ha consolidado')
         + '"> · sem. ' + esc(r.phase_weekly) + '</span>';
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">SCANNER ' + tt('scanner') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">RVOL · RS Percentile · Fase Weinstein · Score Técnico · S&amp;P 500</div>'
        + '</div>';
}

function criteriaPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">CRITERIOS (activa los que quieras combinar)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:1rem;">'

        + CRITERIOS.map(c => {
            const etq = c.etiqueta + (c.tip ? ' ' + tt(c.tip) : '');
            if (c.tipo === 'toggle') return toggleCriterionBlock(c.id, etq, c.nota);
            if (c.tipo === 'select') return selectCriterionBlock(c.id, etq, c.opciones());
            return criterionBlock(c.id, etq, 'number', c.ph, c.paso, c);
        }).join('')

        + '</div>'
        + '<div style="display:flex;justify-content:space-between;align-items:center;">'
        + '<div style="color:var(--color-muted);font-size:11px;">Los criterios activados se combinan con AND (deben cumplirse todos). El resultado se ordena por Score Técnico.</div>'
        + '<div style="display:flex;gap:8px;align-items:center;">'
        + '<button id="scanner-save-preset" style="background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">GUARDAR COMBINACIÓN</button>'
        + '<button id="scanner-run-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ESCANEAR</button>'
        + '</div>'
        + '</div>'
        + '<div id="scanner-presets" style="margin-top:0.9rem;"></div>'
        + '</div>';
}

// Las combinaciones guardadas, en fila. Se repinta entera cada vez: son doce
// como mucho y así no hay que llevar la cuenta de qué chip cambió.
function renderPresets(container) {
    const el = container.querySelector('#scanner-presets');
    if (!el) return;
    const presets = leerPresets();
    if (!presets.length) {
        el.innerHTML = '<div style="color:var(--color-muted);font-size:10px;">'
            + 'Aún no has guardado ninguna combinación. Activa criterios y pulsa «Guardar combinación».</div>';
        return;
    }
    el.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-right:2px;">GUARDADAS</span>'
        + presets.map((p, i) =>
            '<span style="display:inline-flex;align-items:center;gap:6px;border:1px solid var(--color-border);border-radius:var(--radius);padding:3px 6px 3px 10px;font-size:11px;">'
            + '<span class="scanner-preset-apply" data-i="' + i + '" style="color:var(--color-accent);cursor:pointer;" title="'
            + esc(descripcionPreset(p.qs)) + '">' + esc(p.nombre) + '</span>'
            + '<span class="scanner-preset-del" data-i="' + i + '" title="Borrar" '
            + 'style="color:var(--color-muted);cursor:pointer;padding:0 2px;">×</span></span>').join('')
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:9px;margin-top:5px;">'
        + 'Se guardan en este navegador: no viajan a otro dispositivo.</div>';
}

// Qué criterios lleva un preset, en cristiano, para el tooltip del chip.
function descripcionPreset(qs) {
    const p = new URLSearchParams(qs);
    const partes = CRITERIOS
        .filter(c => p.has(c.param))
        .map(c => c.tipo === 'toggle' ? c.etiqueta : c.etiqueta + ' ' + p.get(c.param));
    return partes.length ? partes.join(' · ') : 'Sin criterios';
}

function criterionBlock(id, label, type, placeholder, step, cfg) {
    cfg = cfg || {};
    const limites = (cfg.min != null ? ' min="' + cfg.min + '"' : '')
                  + (cfg.max != null ? ' max="' + cfg.max + '"' : '');
    const nota = cfg.nota
        ? '<div style="color:var(--color-muted);font-size:9px;margin-top:5px;">' + esc(cfg.nota) + '</div>'
        : '';
    return _criterionBlockHtml(id, label, type, placeholder, step, limites, nota);
}

function _criterionBlockHtml(id, label, type, placeholder, step, limites, nota) {
    return '<div id="scanner-' + id + '-card" class="scanner-crit-card" data-active="false" '
        + 'style="border:1px solid var(--color-border);border-radius:var(--radius);padding:10px;cursor:pointer;transition:border-color .15s,background .15s;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<span id="scanner-' + id + '-dot" style="width:9px;height:9px;border-radius:50%;border:1px solid var(--color-muted);flex-shrink:0;"></span>'
        + '<span style="color:var(--color-text);font-size:12px;letter-spacing:0.03em;">' + label + '</span>'
        + '<input type="checkbox" id="scanner-' + id + '-toggle" style="display:none;">'
        + '</div>'
        + '<input type="' + type + '" id="scanner-' + id + '-value" step="' + step + '"' + (limites || '') + ' placeholder="' + placeholder + '" disabled '
        + 'style="width:100%;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 8px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;box-sizing:border-box;cursor:not-allowed;">'
        + (nota || '')
        + '</div>';
}

function selectCriterionBlock(id, label, optionsHtml) {
    return '<div id="scanner-' + id + '-card" class="scanner-crit-card" data-active="false" '
        + 'style="border:1px solid var(--color-border);border-radius:var(--radius);padding:10px;cursor:pointer;transition:border-color .15s,background .15s;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<span id="scanner-' + id + '-dot" style="width:9px;height:9px;border-radius:50%;border:1px solid var(--color-muted);flex-shrink:0;"></span>'
        + '<span style="color:var(--color-text);font-size:12px;letter-spacing:0.03em;">' + label + '</span>'
        + '<input type="checkbox" id="scanner-' + id + '-toggle" style="display:none;">'
        + '</div>'
        + '<select id="scanner-' + id + '-value" disabled '
        + 'style="width:100%;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 8px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;box-sizing:border-box;cursor:not-allowed;">'
        + optionsHtml
        + '</select>'
        + '</div>';
}

function toggleCriterionBlock(id, label, sublabel) {
    // Variante sin campo de valor — el propio criterio es un sí/no (p.ej.
    // "solo tickers en máximos de 52 semanas"), así que activarlo ya basta.
    return '<div id="scanner-' + id + '-card" class="scanner-crit-card" data-active="false" '
        + 'style="border:1px solid var(--color-border);border-radius:var(--radius);padding:10px;cursor:pointer;transition:border-color .15s,background .15s;display:flex;flex-direction:column;justify-content:center;">'
        + '<div style="display:flex;align-items:center;gap:8px;">'
        + '<span id="scanner-' + id + '-dot" style="width:9px;height:9px;border-radius:50%;border:1px solid var(--color-muted);flex-shrink:0;"></span>'
        + '<span style="color:var(--color-text);font-size:12px;letter-spacing:0.03em;">' + label + '</span>'
        + '<input type="checkbox" id="scanner-' + id + '-toggle" style="display:none;">'
        + '</div>'
        + (sublabel ? '<div style="color:var(--color-muted);font-size:9px;margin-top:4px;margin-left:17px;">' + sublabel + '</div>' : '')
        + '</div>';
}

// Los booleanos no tienen `#scanner-<id>-value`, así que setActive() -- que lo
// exige y se sale si falta -- no les vale. Misma apariencia, sin campo.
function setActiveToggle(container, id, active) {
    const card   = container.querySelector('#scanner-' + id + '-card');
    const dot    = container.querySelector('#scanner-' + id + '-dot');
    const toggle = container.querySelector('#scanner-' + id + '-toggle');
    if (!card || !dot || !toggle) return;
    toggle.checked = active;
    card.dataset.active    = String(active);
    card.style.borderColor = active ? 'var(--color-accent)' : 'var(--color-border)';
    card.style.background  = active ? 'var(--color-accent)11' : 'transparent';
    dot.style.background   = active ? 'var(--color-accent)' : 'transparent';
    dot.style.borderColor  = active ? 'var(--color-accent)' : 'var(--color-muted)';
}

function setActive(container, id, active) {
    const card  = container.querySelector('#scanner-' + id + '-card');
    const dot   = container.querySelector('#scanner-' + id + '-dot');
    const toggle = container.querySelector('#scanner-' + id + '-toggle');
    const value = container.querySelector('#scanner-' + id + '-value');
    if (!card || !dot || !toggle || !value) return;

    toggle.checked = active;
    value.disabled = !active;
    value.style.cursor = active ? 'text' : 'not-allowed';
    card.dataset.active = String(active);
    card.style.borderColor = active ? 'var(--color-accent)' : 'var(--color-border)';
    card.style.background  = active ? 'var(--color-accent)11' : 'transparent';
    dot.style.background   = active ? 'var(--color-accent)' : 'transparent';
    dot.style.borderColor  = active ? 'var(--color-accent)' : 'var(--color-muted)';

    if (active) value.focus();
}

function setupPanel(container) {
    // Los criterios con valor salen de CRITERIOS, no de una lista aparte: es
    // lo que impide volver a dejar una tarjeta sin cablear.
    CRITERIOS.filter(c => c.tipo !== 'toggle').forEach(({ id }) => {
        const card  = container.querySelector('#scanner-' + id + '-card');
        const value = container.querySelector('#scanner-' + id + '-value');
        if (!card || !value) return;

        // Click en cualquier parte de la card activa/desactiva el criterio.
        card.addEventListener('click', (e) => {
            if (e.target === value) return; // escribir/seleccionar no debe alternar el estado
            if (e.target.closest('.tt-trigger')) return; // abrir el tooltip no debe alternar el estado
            const isActive = card.dataset.active === 'true';
            setActive(container, id, !isActive);
        });

        // Si el criterio está activo, escribir dentro del campo no debe desactivarlo.
        value.addEventListener('click', (e) => e.stopPropagation());
    });

    // Criterios booleanos: no tienen campo de valor, así que el propio clic en
    // la tarjeta ya alterna el estado. Antes esto estaba escrito a mano SOLO
    // para «máximos 52 semanas», y por eso «zona baja del indicador RSU» nació
    // sin cablear.
    CRITERIOS.filter(c => c.tipo === 'toggle').forEach(({ id }) => {
        const card = container.querySelector('#scanner-' + id + '-card');
        if (!card) return;
        card.addEventListener('click', (e) => {
            if (e.target.closest('.tt-trigger')) return;
            setActiveToggle(container, id, card.dataset.active !== 'true');
        });
    });

    const btn = container.querySelector('#scanner-run-btn');
    btn.addEventListener('click', () => runFilter(container));

    // ── Presets ────────────────────────────────────────────────────────────
    const guardar = container.querySelector('#scanner-save-preset');
    if (guardar) guardar.addEventListener('click', () => {
        const qs = new URLSearchParams(buildQuery(container));
        qs.delete('limit');
        if (![...qs.keys()].length) {
            avisoPreset(container, 'Activa algún criterio antes de guardar la combinación.');
            return;
        }
        const nombre = (window.prompt('Nombre para esta combinación:', '') || '').trim().slice(0, PRESET_NOMBRE_MAX);
        if (!nombre) return;
        const lista = leerPresets().filter(p => p.nombre !== nombre);   // mismo nombre = se reemplaza
        lista.unshift({ nombre, qs: qs.toString() });
        if (lista.length > PRESETS_MAX) {
            avisoPreset(container, 'Solo caben ' + PRESETS_MAX + ' combinaciones: se ha quitado la más antigua.');
        }
        if (!guardarPresets(lista)) {
            avisoPreset(container, 'Este navegador no deja guardar (¿modo privado?). La combinación no se ha conservado.');
            return;
        }
        renderPresets(container);
    });

    // Delegación: los chips se repintan enteros, así que escuchar en el
    // contenedor evita tener que recablear listeners en cada repintado.
    const zona = container.querySelector('#scanner-presets');
    if (zona) zona.addEventListener('click', (e) => {
        const aplicar = e.target.closest('.scanner-preset-apply');
        const borrar  = e.target.closest('.scanner-preset-del');
        const lista   = leerPresets();
        if (aplicar) {
            const p = lista[Number(aplicar.dataset.i)];
            if (!p) return;
            // Se limpia ANTES: aplicar un preset encima de los criterios que ya
            // estaban activos daría una combinación que el usuario no ha
            // pedido y que además no coincide con el nombre del chip.
            limpiarCriterios(container);
            aplicarUrl(container, new URLSearchParams(p.qs));
            runFilter(container);
        } else if (borrar) {
            const i = Number(borrar.dataset.i);
            if (!lista[i]) return;
            lista.splice(i, 1);
            guardarPresets(lista);
            renderPresets(container);
        }
    });
    renderPresets(container);
}

async function loadUniverseMeta(container) {
    const metaEl   = container.querySelector('#scanner-meta');
    const sectorEl = container.querySelector('#scanner-sector-value');
    try {
        const res   = await fetch('/api/v1/scanner/universe', { headers: authHeader() });
        const data  = await res.json();
        if (!data.ok) {
            if (metaEl) metaEl.innerHTML = '<span style="color:#f23645;">' + esc(data.error || 'Error') + '</span>';
            return;
        }
        if (metaEl) {
            // textContent, no innerHTML -- no necesita esc()
            metaEl.textContent = 'Universo: ' + data.universe_size + ' tickers · Actualizado: ' + data.freshness;
        }
        if (sectorEl && data.sectors) {
            sectorEl.innerHTML = data.sectors.map(s => '<option value="' + esc(s) + '">' + esc(s) + '</option>').join('');
        }
    } catch (e) {
        if (metaEl) metaEl.innerHTML = '<span style="color:#f23645;">' + esc(e.message) + '</span>';
    }
}

function buildQuery(container) {
    // Sale de CRITERIOS, igual que el panel y el cableado. Antes era una
    // tercera lista escrita a mano.
    const params = new URLSearchParams();
    CRITERIOS.forEach(c => {
        const toggle = container.querySelector('#scanner-' + c.id + '-toggle');
        if (!toggle || !toggle.checked) return;
        if (c.tipo === 'toggle') { params.set(c.param, 'true'); return; }
        const el = container.querySelector('#scanner-' + c.id + '-value');
        if (el && el.value !== '') params.set(c.param, el.value);
    });
    params.set('limit', '200');
    return params.toString();
}

// ── Deep-link: el estado de los filtros vive en la URL ──────────────────────
//
// Un scan con seis criterios puestos no se podía compartir ni guardar: la URL
// era siempre la misma. Ahora se escribe al escanear y se lee al entrar, así
// que un enlace reproduce exactamente la misma búsqueda.
//
// Se usa replaceState y no pushState a propósito: cada escaneo no debería
// añadir una entrada al historial, o volver atrás obligaría a deshacer filtro
// a filtro.
function guardarEnUrl(qs) {
    try {
        const p = new URLSearchParams(qs);
        p.delete('limit');                       // detalle interno, no del usuario
        const url = window.location.pathname + (p.toString() ? '?' + p.toString() : '');
        window.history.replaceState(null, '', url);
    } catch (_) { /* si el navegador no deja, el scan funciona igual */ }
}

// Apaga todos los criterios y vacía sus campos. Hace falta antes de aplicar un
// preset: si no, se sumaría a lo que ya estuviera activo.
function limpiarCriterios(container) {
    CRITERIOS.forEach(c => {
        if (c.tipo === 'toggle') { setActiveToggle(container, c.id, false); return; }
        const el = container.querySelector('#scanner-' + c.id + '-value');
        setActive(container, c.id, false);
        if (el) el.value = '';
    });
}

// Aviso breve bajo el panel. No usa alert() para no cortar el flujo por algo
// que no es un error.
function avisoPreset(container, texto) {
    const el = container.querySelector('#scanner-presets');
    if (!el) return;
    const antes = el.innerHTML;
    el.innerHTML = '<div style="color:#ffb800;font-size:11px;">' + esc(texto) + '</div>' + antes;
    setTimeout(() => renderPresets(container), 4000);
}

function aplicarUrl(container, p) {
    p = p || new URLSearchParams(window.location.search);
    let alguno = false;
    CRITERIOS.forEach(c => {
        if (!p.has(c.param)) return;
        const valor = p.get(c.param);
        if (c.tipo === 'toggle') {
            if (valor === 'true') { setActiveToggle(container, c.id, true); alguno = true; }
            return;
        }
        const el = container.querySelector('#scanner-' + c.id + '-value');
        if (!el) return;
        // El valor se pone ANTES de activar: setActive() hace focus() al final,
        // y escribir después dejaría el campo con el cursor pero vacío.
        el.value = valor;
        setActive(container, c.id, true);
        alguno = true;
    });
    return alguno;
}

async function runFilter(container) {
    const result = container.querySelector('#scanner-result');
    const btn    = container.querySelector('#scanner-run-btn');
    if (btn) { btn.textContent = 'ESCANEANDO...'; btn.style.opacity = '0.7'; }
    result.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Aplicando criterios sobre el universo precomputado...</div>';

    try {
        const qs    = buildQuery(container);
        guardarEnUrl(qs);
        const res   = await fetch('/api/v1/scanner/filter?' + qs, { headers: authHeader() });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Error en el scan');

        renderResults(result, data);
    } catch (e) {
        result.innerHTML = errorMessage(e.message);
    } finally {
        if (btn) { btn.textContent = 'ESCANEAR'; btn.style.opacity = '1'; }
    }
}

function renderResults(el, data) {
    _scannerData = data;
    const activeLabels = Object.entries(data.active_criteria || {}).map(([k, v]) => k + '=' + esc(v));
    const criteriaLine = activeLabels.length
        ? activeLabels.join(' · ')
        : 'Sin criterios activos — mostrando universo completo ordenado por Score Técnico';

    const header = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;">' + esc(data.matched) + ' / ' + esc(data.universe_size) + ' tickers cumplen</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + criteriaLine + '</div>'
        + '</div>';

    const cols = [
        { label: 'TICKER', key: 'ticker' },
        { label: 'PRECIO',  key: 'precio' },
        { label: 'RVOL',    key: 'rvol' },
        { label: 'RS%',     key: 'rs_pct' },
        { label: 'SCORE TÉC. ' + tt('score-tecnico'), key: 'score_tecnico' },
        { label: 'ABSORC',  key: 'dias_absorcion' },
        { label: 'RSU ' + tt('rsu-flow'), key: 'l3_fundtrend' },
        { label: 'FASE',    key: 'phase' },
        { label: 'SECTOR',  key: 'sector' },
        { label: '',        key: null },
    ];
    const tableHeader = '<div style="display:grid;grid-template-columns:70px 90px 60px 60px 70px 60px 62px 1fr 1fr 34px;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + cols.map(c => c.key
            ? '<div onclick="window.__scannerSort(\'' + c.key + '\')" style="cursor:pointer;user-select:none;">' + c.label + sortArrow(c.key) + '</div>'
            : '<div></div>'
        ).join('')
        + '</div>';

    const sortedResults = sortRows(data.results || [], _scannerSort);

    const rows = sortedResults.map(r => {
        const rvolClr  = (r.rvol || 0) >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)';
        const rsClr    = (r.rs_pct || 0) >= 70 ? 'var(--color-accent)' : (r.rs_pct || 0) <= 30 ? '#f23645' : '#ffb800';
        const scoreClr = (r.score_tecnico || 0) >= 70 ? 'var(--color-accent)' : (r.score_tecnico || 0) >= 40 ? '#ffb800' : '#f23645';
        const phaseClr = r.phase === 2 ? 'var(--color-accent)' : r.phase === 4 ? '#f23645' : '#ffb800';
        const athTag   = r.new_high ? ' <span title="Máximo de 52 semanas" style="font-size:9px;">🔥</span>' : '';
        const carteraTag   = r.en_cartera   ? ' <span title="Ya tienes esta acción en Cartera">💼</span>' : '';
        const watchlistTag = r.in_watchlist ? ' <span title="En tu Watchlist">⭐</span>' : '';
        const absorcClr = (r.dias_absorcion || 0) >= 5 ? '#00ffad' : (r.dias_absorcion || 0) >= 2 ? '#ff9800' : 'var(--color-muted)';
        // Mismo amarillo que la franja del indicador en Research, para que
        // se reconozca como la misma zona sin tener que leer el número.
        const l3 = r.l3_fundtrend;
        const l3Clr = l3 == null ? 'var(--color-muted)'
                    : (l3 >= 10 && l3 <= 20) ? '#ffd700'
                    : l3 >= 80 ? '#c77dff'
                    : 'var(--color-muted)';

        return '<div style="display:grid;grid-template-columns:70px 90px 60px 60px 70px 60px 62px 1fr 1fr 34px;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;' + (r.new_high ? 'background:rgba(255,152,0,0.04);' : '') + '">'
            + '<div onclick="goToResearch(\'' + esc(r.ticker || '') + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;cursor:pointer;">' + esc(r.ticker || '') + athTag + carteraTag + watchlistTag + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.precio != null ? '$' + r.precio.toFixed(2) : '—') + '</div>'
            + '<div style="color:' + rvolClr + ';">' + (r.rvol != null ? r.rvol.toFixed(2) + 'x' : '—') + '</div>'
            + '<div style="color:' + rsClr + ';font-weight:500;">' + (r.rs_pct != null ? r.rs_pct.toFixed(0) : '—') + '</div>'
            + '<div style="color:' + scoreClr + ';font-weight:500;">' + (r.score_tecnico != null ? r.score_tecnico.toFixed(0) : '—') + '</div>'
            + '<div style="color:' + absorcClr + ';font-weight:500;">' + esc(r.dias_absorcion || 0) + '/10</div>'
            + '<div style="color:' + l3Clr + ';font-weight:500;" title="' + esc(r.l3_estado || 'sin lectura') + '">' + (l3 != null ? l3.toFixed(0) : '—') + '</div>'
            + '<div style="color:' + phaseClr + ';font-size:10px;">' + esc(r.phase_label || '—') + fasesemanal(r) + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + esc(r.sector || '—') + '</div>'
            + '<div style="text-align:center;"><button onclick="window.__quickAddWatchlist(\'' + esc(r.ticker || '') + '\', this)" title="Añadir a watchlist" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:3px;padding:2px 6px;font-size:11px;cursor:pointer;">＋</button></div>'
            + '</div>';
    }).join('');

    el.innerHTML = header
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + tableHeader
        + (rows || '<div style="padding:1.5rem;text-align:center;color:var(--color-muted);font-size:12px;">Ningún ticker cumple los criterios activados. Prueba a aflojar algún umbral.</div>')
        + '</div>';
}