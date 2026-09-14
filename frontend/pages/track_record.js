import { authHeader } from '/core/api.js';
// ─────────────────────────────────────────────────────────────────────────────
// TRACK RECORD — qué hicieron de verdad las señales de la terminal
//
// Principio de esta página, y la razón de que exista: se muestran TODAS las
// señales, las que salieron bien y las que salieron mal, sin filtrar ninguna
// y sin ordenarlas para favorecer nada. Un backtest se puede reajustar hasta
// que dé bien; esto no.
//
// Cada retorno va acompañado del SPY en el mismo periodo. "+8%" no significa
// nada si el mercado hizo +12% — sin esa columna, un track record en un
// mercado alcista se vende solo y no dice nada.
// ─────────────────────────────────────────────────────────────────────────────

import { errorMessage, esc, fmtFecha } from '/core/ui.js';
import { PREVISIONES, VEREDICTOS, ultimaRevision, ROADMAP_ESCRITO_EL } from '/core/previsiones.js';

export async function render(container) {
    container.innerHTML = cabecera() + '<div id="tr-body">' + cargando() + '</div>';
    cargar(container);
}

function cabecera() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">📓 TRACK RECORD</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Lo que hicieron de verdad las señales — todas, las buenas y las malas</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">Resultados reales con precios de mercado, no un backtest · Cada retorno se compara con el S&P 500 del mismo periodo · No es asesoramiento de inversión</div>'
        + '</div>';
}

function cargando() {
    return '<div style="color:var(--color-muted);font-size:12px;padding:2rem;text-align:center;">Calculando resultados reales…</div>';
}

async function cargar(container) {
    const body = container.querySelector('#tr-body');
    try {
        const res   = await fetch('/api/v1/track-record/', {
            headers: authHeader()
        });
        const data = await res.json();
        if (!data.ok) { body.innerHTML = errorMessage(data.error || 'Sin datos'); return; }
        body.innerHTML = avisoVisitante(data)
                       + seccionCartera(data.cartera) + seccionBriefing(data.briefing)
                       + seccionAlgoritmo(data.algoritmo) + seccionCanslim(data.canslim)
                       + seccionRsuScore(data.rsu_score) + seccionOptions(data.options)
                       + seccionTesis(data.tesis, data) + seccionPrevisiones(data) + nota();
    } catch (e) {
        body.innerHTML = errorMessage(e.message);
    }
}

// ── Utilidades de formato ────────────────────────────────────────────────────

function color(v) {
    if (v === null || v === undefined) return 'var(--color-muted)';
    return v >= 0 ? 'var(--color-accent)' : '#f23645';
}

function pct(v, sufijo) {
    if (v === null || v === undefined) return '<span style="color:var(--color-muted);">—</span>';
    const s = (v >= 0 ? '+' : '') + v.toFixed(2) + (sufijo || '%');
    return '<span style="color:' + color(v) + ';">' + esc(s) + '</span>';
}

function caja(titulo, contenido, subtitulo) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1.5rem;">'
        + '<div style="padding:10px 16px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:11px;letter-spacing:0.08em;">' + esc(titulo) + '</div>'
        + (subtitulo ? '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + esc(subtitulo) + '</div>' : '')
        + '</div>' + contenido + '</div>';
}

function avisoMuestra(n) {
    // Se dice el tamaño de la muestra siempre, y se avisa cuando es pequeña.
    // Una media de 3 observaciones no es un resultado, es una anécdota.
    if (n === 0) return '';
    if (n >= 5) return '';
    return '<div style="background:rgba(255,152,0,.08);border-left:3px solid #ff9800;padding:8px 14px;margin:0;">'
        + '<span style="color:#ff9800;font-size:11px;">Muestra de ' + n + ' — demasiado pequeña para sacar conclusiones. Se muestra igual porque ocultarla sería peor.</span></div>';
}

function tablaHorizontes(porHorizonte, titulo) {
    const filas = ['5d', '10d', '20d', '60d'].map(h => {
        const s = porHorizonte[h] || { n: 0 };
        return '<div style="display:grid;grid-template-columns:60px 60px 1fr 1fr 1fr 1fr;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span style="color:var(--color-text);">' + esc(h) + '</span>'
            + '<span style="color:var(--color-muted);">n=' + s.n + '</span>'
            + '<span>' + pct(s.media) + '</span>'
            + '<span>' + pct(s.mediana) + '</span>'
            + '<span style="color:var(--color-muted);">' + (s.pct_positivas === null || s.pct_positivas === undefined ? '—' : esc(s.pct_positivas + '% en verde')) + '</span>'
            + '<span style="color:var(--color-muted);font-size:10px;">' + (s.n ? esc('peor ' + s.peor + '%') : '') + '</span>'
            + '</div>';
    }).join('');
    return '<div style="display:grid;grid-template-columns:60px 60px 1fr 1fr 1fr 1fr;gap:8px;padding:7px 16px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>' + esc(titulo) + '</span><span>MUESTRA</span><span>MEDIA</span><span>MEDIANA</span><span>ACIERTO</span><span></span></div>'
        + filas;
}

// ── CANSLIM · candidatos del scan nocturno ──────────────────────────────────
//
// Es la única de las tres fuentes con GRUPO DE CONTROL: se guarda el universo
// entero de cada scan, no solo los que pasaban el filtro, así que la tabla
// permite comparar los de score alto contra los de score bajo. Sin esa última
// fila, lo único que se podría contestar es «¿subieron?», que en un mercado
// alcista se responde solo y no dice nada del módulo.

function seccionCanslim(c) {
    if (!c) return caja('CANSLIM · CANDIDATOS', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');

    if (!c.n_filas) {
        return caja('CANSLIM · CANDIDATOS DEL SCAN NOCTURNO',
            '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;line-height:1.6;">'
            + 'Todavía sin datos. El registro empieza con el primer scan tras activarlo: el Gist del scan se sobrescribe cada noche, '
            + 'así que el pasado no se puede reconstruir. Los primeros resultados a 5 días aparecen en una semana; los de 60 días, en unos tres meses.'
            + '</div>');
    }

    const filas = (c.por_tramo || []).map(t => {
        const control = t.tramo.indexOf('<60') === 0;
        const h20 = (t.por_horizonte || {})['20d'] || { n: 0 };
        const v20 = (t.por_horizonte_vs_spy || {})['20d'] || { n: 0 };
        const h60 = (t.por_horizonte || {})['60d'] || { n: 0 };
        const v60 = (t.por_horizonte_vs_spy || {})['60d'] || { n: 0 };
        return '<div style="display:grid;grid-template-columns:170px 70px 1fr 1fr 1fr 1fr;gap:8px;padding:8px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;'
            + (control ? 'opacity:.75;' : '') + '">'
            + '<span style="color:' + (control ? 'var(--color-muted)' : 'var(--color-text)') + ';">' + esc(t.tramo) + (control ? ' <span style="font-size:9px;">(control)</span>' : '') + '</span>'
            + '<span style="color:var(--color-muted);">n=' + esc(t.n_filas) + '</span>'
            + '<span>' + pct(h20.media) + '</span>'
            + '<span>' + pct(v20.media) + '</span>'
            + '<span>' + pct(h60.media) + '</span>'
            + '<span>' + pct(v60.media) + '</span>'
            + '</div>';
    }).join('');

    const cabeceraTabla = '<div style="display:grid;grid-template-columns:170px 70px 1fr 1fr 1fr 1fr;gap:8px;padding:7px 16px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>TRAMO DE SCORE</span><span>MUESTRA</span><span>20D MEDIA</span><span>20D vs SPY</span><span>60D MEDIA</span><span>60D vs SPY</span></div>';

    // El aviso de baseline ausente NO es decorativo: sin él, un "+6%" se lee
    // como si ya estuviera comparado con el mercado, y no lo estaría. Se
    // distingue la causa: que falle la descarga es una avería, que el scan
    // sea de hoy y aún no haya sesión es lo normal el primer día.
    let avisoBaseline = '';
    if (!c.baseline_disponible) {
        const esAveria = c.baseline_motivo === 'sin_spy';
        const texto = esAveria
            ? 'No se ha podido descargar el SPY, así que las columnas «vs SPY» están vacías. Los retornos de al lado NO están comparados con el mercado.'
            : 'Todavía no hay una sesión de mercado posterior al scan a la que anclar el SPY, así que las columnas «vs SPY» están vacías. Se rellenarán con el próximo cierre.';
        avisoBaseline = '<div style="background:rgba(255,152,0,.08);border-left:3px solid #ff9800;padding:8px 14px;">'
            + '<span style="color:#ff9800;font-size:11px;">' + esc(texto) + '</span></div>';
    }

    const pendientes = c.n_pendientes
        ? '<div style="padding:8px 16px;color:var(--color-muted);font-size:10px;border-top:1px solid var(--color-border);">'
          + esc(c.n_pendientes) + ' de ' + esc(c.n_filas) + ' filas todavía sin cumplir los 60 días — la muestra de los horizontes largos irá creciendo sola.</div>'
        : '';

    const sub = esc(c.n_scans + (c.n_scans === 1 ? ' scan registrado' : ' scans registrados')
        + (c.primera_fecha ? ' · desde ' + c.primera_fecha : '')
        + ' · universo completo, no solo los candidatos');

    return caja('CANSLIM · CANDIDATOS DEL SCAN NOCTURNO', avisoBaseline + cabeceraTabla + filas + pendientes, sub);
}

// ── RSU Algoritmo ────────────────────────────────────────────────────────────

function seccionAlgoritmo(a) {
    if (!a) return caja('RSU ALGORITMO', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    if (!a.n_senales) {
        return caja('RSU ALGORITMO · SEÑALES REALES',
            '<div style="padding:1.25rem 16px;color:var(--color-muted);font-size:12px;line-height:1.6;">'
            + 'Todavía no se ha registrado ninguna señal VERDE desde que se activó el seguimiento en vivo. '
            + 'Esto empieza vacío a propósito: solo cuenta lo que ocurre a partir de ahora, no un recálculo del pasado.'
            + '</div>', 'Registradas en vivo, fuera de muestra');
    }

    const pendientes = a.n_pendientes
        ? '<div style="padding:8px 16px;color:var(--color-muted);font-size:11px;border-top:1px solid var(--color-border);">'
          + a.n_pendientes + ' de ' + a.n_senales + ' señales aún no han cumplido los 60 días — su resultado a ese plazo todavía no existe.</div>'
        : '';

    const filas = a.senales.map(s => {
        const stop = s.stopeada_dia
            ? '<span style="color:#f23645;font-size:10px;" title="El stop del -7% se disparó el día ' + s.stopeada_dia + '">STOP d' + s.stopeada_dia + '</span>'
            : '';
        return '<div style="display:grid;grid-template-columns:90px 90px 60px 1fr 1fr 1fr 1fr 70px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span style="color:var(--color-text);">' + esc(s.fecha || '') + '</span>'
            + '<span style="color:' + (s.estado === 'VERDE' ? 'var(--color-accent)' : '#ffb800') + ';">' + esc(s.estado || '') + '</span>'
            + '<span style="color:var(--color-muted);">' + esc(s.score === null || s.score === undefined ? '—' : s.score) + '</span>'
            + '<span>' + pct(s.resultado_5d) + '</span>'
            + '<span>' + pct(s.resultado_10d) + '</span>'
            + '<span>' + pct(s.resultado_20d) + '</span>'
            + '<span>' + pct(s.resultado_60d) + '</span>'
            + '<span>' + stop + '</span>'
            + '</div>';
    }).join('');

    const cabeceraTabla = '<div style="display:grid;grid-template-columns:90px 90px 60px 1fr 1fr 1fr 1fr 70px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>FECHA</span><span>ESTADO</span><span>SCORE</span><span>+5D</span><span>+10D</span><span>+20D</span><span>+60D</span><span></span></div>';

    return caja('RSU ALGORITMO · SEÑALES REALES',
        avisoMuestra(a.por_horizonte['20d'] ? a.por_horizonte['20d'].n : 0)
        + tablaHorizontes(a.por_horizonte, 'AGREGADO')
        + '<div style="padding:8px 16px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;">Lo mismo, pero aplicando el stop del -7% que define la metodología — es lo que habría vivido alguien siguiendo la señal con salida definida:</div>'
        + tablaHorizontes(a.por_horizonte_con_stop, 'CON STOP')
        + cabeceraTabla + filas + pendientes,
        a.n_senales + ' señales registradas en vivo desde que se activó el seguimiento · fuera de muestra');
}

// ── Tesis ────────────────────────────────────────────────────────────────────

function seccionTesis(t, data) {
    if (!t) return caja('TESIS PUBLICADAS', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    if (!t.n_tesis) {
        return caja('TESIS PUBLICADAS',
            '<div style="padding:1.25rem 16px;color:var(--color-muted);font-size:12px;">Todavía no hay tesis aprobadas que medir.</div>');
    }

    const r  = t.resumen || {};
    const vs = t.resumen_vs_spy || {};
    const obj = t.objetivo_alcanzado || { n: 0, alcanzados: 0 };

    const resumen = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--color-border);">'
        + kpi('RETORNO MEDIO', r.media === null || r.media === undefined ? '—' : (r.media >= 0 ? '+' : '') + r.media + '%', color(r.media), 'desde publicación')
        + kpi('VS S&P 500', vs.media === null || vs.media === undefined ? '—' : (vs.media >= 0 ? '+' : '') + vs.media + ' pp', color(vs.media), 'lo que aportó de verdad')
        + kpi('EN VERDE', r.pct_positivas === null || r.pct_positivas === undefined ? '—' : r.pct_positivas + '%', 'var(--color-text)', r.n + ' tesis medidas')
        + kpi('OBJETIVO ALCANZADO', obj.n ? obj.alcanzados + '/' + obj.n : '—', 'var(--color-text)', 'llegó a tocarse')
        + '</div>';

    const filas = t.tesis.map(x => {
        if (x.estado_dato !== 'ok') {
            return '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr 90px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<span style="color:var(--color-text);">' + esc(x.ticker || '🔒') + '</span>'
                + '<span style="color:var(--color-muted);">' + esc((x.fecha || '').slice(0, 10)) + '</span>'
                + '<span style="color:var(--color-muted);grid-column:span 4;font-size:10px;">Sin precios disponibles para este ticker</span>'
                + '</div>';
        }
        // Tesis de menos de un mes, vista sin suscripción: la fila y su
        // resultado se ven (y cuentan en los totales), pero no de qué valor es.
        const tickerHtml = x.ticker
            ? '<span style="color:var(--color-text);cursor:pointer;" data-research="' + esc(x.ticker) + '">' + esc(x.ticker) + '</span>'
            : '<span style="color:var(--color-muted);font-size:10px;" title="Solo para suscriptores hasta el ' + esc(fmtFecha(x.reservada_hasta)) + '">🔒 reservada</span>';
        const objTxt = x.objetivo_alcanzado === null || x.objetivo_alcanzado === undefined
            ? '<span style="color:var(--color-muted);">—</span>'
            : (x.objetivo_alcanzado
                ? '<span style="color:var(--color-accent);">✓ tocado</span>'
                : '<span style="color:var(--color-muted);">no</span>');
        return '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr 90px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + tickerHtml
            + '<span style="color:var(--color-muted);">' + esc((x.fecha || '').slice(0, 10)) + '</span>'
            + '<span>' + pct(x.retorno_pct) + '</span>'
            + '<span style="color:var(--color-muted);">' + (x.spy_mismo_periodo_pct === null || x.spy_mismo_periodo_pct === undefined ? '—' : esc((x.spy_mismo_periodo_pct >= 0 ? '+' : '') + x.spy_mismo_periodo_pct + '%')) + '</span>'
            + '<span>' + pct(x.vs_spy_pp, ' pp') + '</span>'
            + '<span>' + objTxt + '</span>'
            + '</div>';
    }).join('');

    const cabeceraTabla = '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr 90px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>TICKER</span><span>PUBLICADA</span><span>RETORNO</span><span>S&P 500</span><span>DIFERENCIA</span><span>OBJETIVO</span></div>';

    const reservadas = t.tesis.filter(x => x.reservada_hasta).length;
    const avisoReserva = reservadas
        ? '<div style="padding:8px 16px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;">'
          + esc(reservadas + (reservadas === 1 ? ' tesis tiene' : ' tesis tienen') + ' menos de ' + ((data && data.dias_reserva_tesis) || 30)
                + ' días: su resultado cuenta en los totales, pero el valor solo lo ven los suscriptores hasta que cumpla ese plazo.')
          + '</div>'
        : '';
    return caja('TESIS PUBLICADAS', resumen + avisoMuestra(r.n || 0) + cabeceraTabla + filas + avisoReserva,
        'Retorno desde la fecha de publicación, con precios reales · ' + t.n_tesis + ' tesis');
}

// ── Quién mira ───────────────────────────────────────────────────────────────
//
// Esta página es PÚBLICA desde el 14/09/2026: la prueba de que las
// herramientas funcionan no puede verla solo quien ya ha pagado. A quien entra
// sin cuenta se le dice qué está viendo y cómo seguir, sin tapar nada.

function avisoVisitante(data) {
    if (data.visitante !== 'anonimo') return '';
    return '<div style="background:rgba(0,255,173,0.05);border:1px solid var(--color-accent);border-radius:var(--radius);padding:12px 16px;margin-bottom:1.5rem;font-size:12px;line-height:1.6;color:var(--color-text);">'
        + 'Esta página es abierta: cualquiera puede comprobar qué hicieron las señales de RSU Terminal, las buenas y las malas. '
        + 'Las herramientas que las generan están dentro. '
        + '<a href="/register" data-ir="/register" style="color:var(--color-accent);">Crear cuenta</a> · '
        + '<a href="/login" data-ir="/login" style="color:var(--color-accent);">Entrar</a>'
        + '</div>';
}

// ── RSU Score · ¿una nota alta acierta más? ─────────────────────────────────
//
// Sin comparar con el SPY todavía (la tabla de seguimiento no guarda el índice),
// y se dice. Lo que sí se puede leer es la comparación ENTRE tramos: todos
// comparten mercado, así que si la nota alta no se separa de la baja, no aporta.

function seccionRsuScore(s) {
    if (!s) return caja('RSU SCORE', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    if (!s.n_registros) {
        return caja('RSU SCORE · ¿UNA NOTA ALTA ACIERTA MÁS?',
            '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">Todavía sin registros: se acumulan con cada valor analizado en Research.</div>');
    }
    const cab = '<div style="display:grid;grid-template-columns:190px 70px 1fr 1fr 1fr 1fr;gap:8px;padding:7px 16px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>NOTA</span><span>MUESTRA</span><span>20D MEDIA</span><span>20D vs S&amp;P 500</span><span>60D MEDIA</span><span>60D vs S&amp;P 500</span></div>';
    const filas = s.tramos.map(b =>
        '<div style="display:grid;grid-template-columns:190px 70px 1fr 1fr 1fr 1fr;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
        + '<span style="color:var(--color-text);">' + esc(b.bucket) + ' <span style="color:var(--color-muted);font-size:10px;">(' + esc(b.rango) + ')</span></span>'
        + '<span style="color:var(--color-muted);" title="Con resultado a 20 días: ' + esc(b.n_20d || 0) + '">n=' + esc(b.n) + '</span>'
        + '<span>' + pct(b.avg_20d) + '</span><span>' + pct(b.vs_spy_20d, ' pp') + '</span>'
        + '<span>' + pct(b.avg_60d) + '</span><span>' + pct(b.vs_spy_60d, ' pp') + '</span>'
        + '</div>').join('');
    // «vs S&P 500» = retorno del valor menos el del índice en la misma
    // ventana. Si todavía no hay ninguna fila comparada, se dice.
    const aviso = s.comparado_con_spy
        ? ''
        : '<div style="background:rgba(255,152,0,.08);border-left:3px solid #ff9800;padding:8px 14px;">'
          + '<span style="color:#ff9800;font-size:11px;">Todavía no hay resultados comparados con el S&amp;P 500: aparecen cuando las notas cumplen su plazo.</span></div>';
    return caja('RSU SCORE · ¿UNA NOTA ALTA ACIERTA MÁS?', aviso + cab + filas + avisoMuestra(s.n_con_20d),
        s.n_registros + ' notas registradas · ' + s.n_con_20d + ' con resultado a 20 días');
}

// ── Options Flow · ¿acierta el dinero inusual? ──────────────────────────────

function seccionOptions(o) {
    if (!o || !o.ok) return caja('OPTIONS FLOW', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    if (!o.senales) {
        return caja('OPTIONS FLOW · ¿ACIERTA EL DINERO INUSUAL?',
            '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">Todavía sin señales medidas.</div>');
    }
    const cab = '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr;gap:8px;padding:7px 16px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>PLAZO</span><span>MUESTRA</span><span>ACIERTOS</span><span>SIGUIENDO LA SEÑAL</span><span>SIN MIRAR DIRECCIÓN</span></div>';
    const filas = Object.keys(o.horizontes || {}).map(d => {
        const b = o.horizontes[d].todas || { n: 0 };
        return '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span style="color:var(--color-text);">' + esc(d) + 'd</span>'
            + '<span style="color:var(--color-muted);">n=' + esc(b.n) + (b.suficiente ? '' : ' <span style="color:#ff9800;" title="Por debajo de ' + esc(o.min_muestra) + ' casos no es concluyente">·</span>') + '</span>'
            + '<span style="color:var(--color-text);">' + (b.aciertos_pct === null || b.aciertos_pct === undefined ? '—' : esc(b.aciertos_pct + '%')) + '</span>'
            + '<span>' + pct(b.exceso_dirigido, ' pp') + '</span>'
            + '<span>' + pct(b.exceso_universo, ' pp') + '</span>'
            + '</div>';
    }).join('');
    const nota = '<div style="padding:8px 16px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;line-height:1.6;">'
        + 'Todo frente al S&amp;P 500 en la misma ventana. «Siguiendo la señal» es lo que se habría ganado haciendo caso a la dirección del flujo; '
        + '«sin mirar dirección» es cómo lo hicieron esos valores en general. Si las dos se parecen, la dirección no aporta nada. '
        + 'Por debajo de ' + esc(o.min_muestra) + ' casos, ningún porcentaje es concluyente.</div>';
    return caja('OPTIONS FLOW · ¿ACIERTA EL DINERO INUSUAL?', cab + filas + nota,
        o.senales + ' señales en ' + o.sesiones + ' sesiones');
}

// ── Previsiones del Roadmap ─────────────────────────────────────────────────
//
// Del registro compartido con la página del Roadmap (core/previsiones.js): la
// previsión tal como se escribió, y cada revisión con su fecha.

function seccionPrevisiones(data) {
    const filas = PREVISIONES.map(p => {
        const r = ultimaRevision(p);
        const v = VEREDICTOS[r.veredicto];
        return '<div style="display:grid;grid-template-columns:120px 1fr;gap:12px;padding:10px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:start;">'
            + '<span style="color:' + v.color + ';">' + v.icono + ' ' + esc(v.texto)
            + (r.fecha ? '<br><span style="color:var(--color-muted);font-size:10px;">revisada ' + esc(fmtFecha(r.fecha)) + '</span>' : '') + '</span>'
            + '<span><span style="color:var(--color-text);">' + esc(p.prevision) + '</span>'
            + '<br><span style="color:var(--color-muted);">' + esc(r.detalle) + '</span></span>'
            + '</div>';
    }).join('');
    const pie = '<div style="padding:8px 16px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;">'
        + 'Previsiones copiadas tal cual del Roadmap 2026, escrito el ' + esc(ROADMAP_ESCRITO_EL) + '. No se retocan: cada revisión nueva se añade con su fecha.'
        + (data.visitante === 'anonimo' ? '' : ' <a href="/roadmap" data-ir="/roadmap" style="color:var(--color-accent);">Ver el Roadmap completo</a>')
        + '</div>';
    return caja('PREVISIONES DEL ROADMAP 2026', filas + pie, 'Escritas antes de que pasara · con su veredicto y su fecha');
}

// ── Cartera RSU contra el S&P 500 ───────────────────────────────────────────
//
// Solo porcentajes. Ni patrimonio en dólares, ni capital, ni posiciones: cómo
// lo hizo frente a comprar el índice en las mismas fechas. La rentabilidad es
// la ponderada por tiempo, que descuenta el dinero que entra.

function seccionCartera(c) {
    if (!c) return caja('CARTERA RSU', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    if (!c.serie || c.serie.length < 2) {
        return caja('CARTERA RSU · CONTRA EL S&P 500',
            '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">Todavía sin historia suficiente para comparar.</div>');
    }
    const kpis = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--color-border);">'
        + kpi('CARTERA RSU', (c.cartera_pct >= 0 ? '+' : '') + c.cartera_pct + '%', color(c.cartera_pct), 'rentabilidad ponderada por tiempo')
        + kpi('S&P 500', c.spy_pct === null || c.spy_pct === undefined ? '—' : (c.spy_pct >= 0 ? '+' : '') + c.spy_pct + '%', color(c.spy_pct), 'mismas fechas')
        + kpi('DIFERENCIA', c.diferencia_pp === null || c.diferencia_pp === undefined ? '—' : (c.diferencia_pp >= 0 ? '+' : '') + c.diferencia_pp + ' pp', color(c.diferencia_pp), 'lo que aportó frente al índice')
        + kpi('PEOR CAÍDA', c.peor_caida_cartera === null ? '—' : c.peor_caida_cartera + '%', '#f23645', 'S&P 500: ' + (c.peor_caida_spy === null ? '—' : c.peor_caida_spy + '%'))
        + '</div>';
    return caja('CARTERA RSU · CONTRA EL S&P 500', kpis + graficoCurvas(c.serie)
        + '<div style="padding:8px 16px;border-top:1px solid var(--color-border);color:var(--color-muted);font-size:10px;line-height:1.6;">'
        + 'Las dos líneas parten de 100 el primer día. La de la cartera es la rentabilidad ponderada por tiempo: descuenta el dinero que se va aportando, así que mide rendimiento y no ingresos. '
        + 'Incluye las posiciones cerradas, también las que salieron mal. Sin cifras en dólares ni posiciones.</div>',
        'Del ' + fmtFecha(c.desde) + ' al ' + fmtFecha(c.hasta) + ' · ' + c.n_dias + ' días con datos');
}

function graficoCurvas(serie) {
    const W = 600, H = 150, pad = 6;
    const valores = serie.flatMap(p => [p.cartera, p.spy]).filter(v => v !== null && v !== undefined);
    const min = Math.min(...valores), max = Math.max(...valores);
    const rango = (max - min) || 1;
    const x = i => (pad + i / (serie.length - 1) * (W - 2 * pad)).toFixed(1);
    const y = v => (H - pad - (v - min) / rango * (H - 2 * pad)).toFixed(1);
    const linea = (campo) => serie.map((p, i) => p[campo] === null || p[campo] === undefined ? '' : x(i) + ',' + y(p[campo])).filter(Boolean).join(' ');
    const cien = y(100);
    return '<div style="padding:12px 16px 4px;">'
        + '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;height:auto;display:block;" role="img" aria-label="Curva de la Cartera RSU frente al S&amp;P 500, las dos desde 100">'
        + '<line x1="0" x2="' + W + '" y1="' + cien + '" y2="' + cien + '" stroke="var(--color-border)" stroke-dasharray="3 3"/>'
        + '<polyline points="' + linea('spy') + '" fill="none" stroke="var(--color-muted)" stroke-width="1.5"/>'
        + '<polyline points="' + linea('cartera') + '" fill="none" stroke="var(--color-accent)" stroke-width="2"/>'
        + '</svg>'
        + '<div style="display:flex;gap:16px;font-size:10px;color:var(--color-muted);margin-top:4px;">'
        + '<span><span style="color:var(--color-accent);">━</span> Cartera RSU</span>'
        + '<span><span style="color:var(--color-muted);">━</span> S&amp;P 500</span>'
        + '<span>┄ 100 = punto de partida</span></div></div>';
}

// ── Sesgo del briefing ──────────────────────────────────────────────────────
//
// Al lado de cada acierto, lo que habría acertado decir ALCISTA siempre: en un
// mercado que sube, eso ya acierta mucho sin aportar nada. Y si todos los días
// fueron del mismo sesgo, se dice: entonces el acierto solo mide hacia dónde
// fue el mercado, no si el briefing lo leyó bien.

function seccionBriefing(b) {
    if (!b) return caja('SESGO DEL BRIEFING', '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">No disponible.</div>');
    const h1 = (b.horizontes || {})['1'] || { n: 0 };
    if (!h1.n) {
        return caja('SESGO DEL BRIEFING · ¿ACIERTA LA DIRECCIÓN?',
            '<div style="padding:1rem 16px;color:var(--color-muted);font-size:12px;">Todavía sin días evaluados.</div>');
    }
    const filaH = (etq, h) => {
        const d = h.por_direccion || {};
        return '<div style="display:grid;grid-template-columns:90px 70px 1fr 1fr 1fr;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span style="color:var(--color-text);">' + esc(etq) + '</span>'
            + '<span style="color:var(--color-muted);">n=' + esc(h.n) + '</span>'
            + '<span style="color:var(--color-text);">' + (h.aciertos_pct === null || h.aciertos_pct === undefined ? '—' : esc(h.aciertos_pct + '%')) + '</span>'
            + '<span style="color:var(--color-muted);">' + (h.siempre_alcista_pct === null || h.siempre_alcista_pct === undefined ? '—' : esc(h.siempre_alcista_pct + '%')) + '</span>'
            + '<span style="color:var(--color-muted);font-size:10px;">' + esc((d.alcista ? d.alcista.n : 0) + ' alcistas · ' + (d.bajista ? d.bajista.n : 0) + ' bajistas') + '</span>'
            + '</div>';
    };
    const cab = '<div style="display:grid;grid-template-columns:90px 70px 1fr 1fr 1fr;gap:8px;padding:7px 16px;font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>PLAZO</span><span>MUESTRA</span><span>ACIERTOS</span><span>DECIR SIEMPRE «ALCISTA»</span><span>REPARTO</span></div>';
    const d1 = h1.por_direccion || {};
    const unSoloSesgo = (d1.alcista && d1.alcista.n === 0) || (d1.bajista && d1.bajista.n === 0);
    const avisos = [];
    if (unSoloSesgo) {
        avisos.push('Todos los días evaluados tuvieron el mismo sesgo, así que el acierto solo refleja hacia dónde fue el mercado en ese periodo, no si el briefing lo leyó mejor que nadie.');
    }
    if (!h1.suficiente) {
        avisos.push('Con ' + h1.n + ' días (mínimo ' + b.min_muestra + ') ningún porcentaje es concluyente.');
    }
    const aviso = avisos.length
        ? '<div style="background:rgba(255,152,0,.08);border-left:3px solid #ff9800;padding:8px 14px;"><span style="color:#ff9800;font-size:11px;">' + esc(avisos.join(' ')) + '</span></div>'
        : '';
    const dias = (b.ultimos || []).map(u =>
        '<span title="' + esc(fmtFecha(u.fecha) + ': ' + u.sesgo + ', S&P 500 ' + (u.ret_1d >= 0 ? '+' : '') + u.ret_1d + '% al día siguiente') + '" style="display:inline-block;margin:2px;padding:2px 6px;border-radius:3px;font-size:10px;'
        + 'border:1px solid ' + (u.acierto_1d ? 'var(--color-accent)' : '#f23645') + ';color:' + (u.acierto_1d ? 'var(--color-accent)' : '#f23645') + ';">'
        + esc((u.fecha || '').slice(5).split('-').reverse().join('/')) + ' ' + (u.sesgo === 'ALCISTA' ? '▲' : '▼') + (u.acierto_1d ? ' ✓' : ' ✗') + '</span>').join('');
    return caja('SESGO DEL BRIEFING · ¿ACIERTA LA DIRECCIÓN?',
        aviso + cab + filaH('1 sesión', h1) + filaH('5 sesiones', (b.horizontes || {})['5'] || { n: 0 })
        + (dias ? '<div style="padding:8px 16px;border-top:1px solid var(--color-border);"><div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">ÚLTIMOS DÍAS · sesgo publicado y si acertó al día siguiente</div>' + dias + '</div>' : ''),
        b.dias_registrados + ' días registrados · ' + b.neutrales + ' neutrales (no se evalúan) · ' + b.pendientes + ' pendientes');
}

function kpi(label, valor, col, sub) {
    return '<div style="background:var(--color-surface);padding:12px 16px;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:4px;">' + esc(label) + '</div>'
        + '<div style="color:' + col + ';font-size:17px;">' + esc(valor) + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + esc(sub) + '</div>'
        + '</div>';
}

function nota() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem 16px;color:var(--color-muted);font-size:11px;line-height:1.7;">'
        + '<div style="color:var(--color-secondary);font-size:11px;letter-spacing:0.08em;margin-bottom:8px;">CÓMO LEER ESTA PÁGINA</div>'
        + 'Las señales del <b style="color:var(--color-text);">Algoritmo</b> se registran en vivo: ninguna existía cuando se calibraron sus umbrales, así que su resultado es genuinamente fuera de muestra. Empezó vacío y crece solo con el tiempo.<br><br>'
        + 'Las <b style="color:var(--color-text);">tesis</b> se miden hacia atrás con precios históricos reales desde su fecha de publicación. La columna <b style="color:var(--color-text);">diferencia</b> es la única que importa: cuánto aportó la tesis frente a haber comprado el índice y no hacer nada.<br><br>'
        + 'Nada de esto está filtrado. Las que salieron mal están en la misma tabla que las que salieron bien, y cuando la muestra es pequeña se dice.'
        + '</div>';
}
