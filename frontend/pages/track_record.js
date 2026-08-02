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

import { errorMessage, esc } from '/core/ui.js';

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
        const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/track-record/', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data = await res.json();
        if (!data.ok) { body.innerHTML = errorMessage(data.error || 'Sin datos'); return; }
        body.innerHTML = seccionAlgoritmo(data.algoritmo) + seccionCanslim(data.canslim)
                       + seccionTesis(data.tesis) + nota();
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

function seccionTesis(t) {
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
                + '<span style="color:var(--color-text);">' + esc(x.ticker || '') + '</span>'
                + '<span style="color:var(--color-muted);">' + esc((x.fecha || '').slice(0, 10)) + '</span>'
                + '<span style="color:var(--color-muted);grid-column:span 4;font-size:10px;">Sin precios disponibles para este ticker</span>'
                + '</div>';
        }
        const objTxt = x.objetivo_alcanzado === null || x.objetivo_alcanzado === undefined
            ? '<span style="color:var(--color-muted);">—</span>'
            : (x.objetivo_alcanzado
                ? '<span style="color:var(--color-accent);">✓ tocado</span>'
                : '<span style="color:var(--color-muted);">no</span>');
        return '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr 90px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<span style="color:var(--color-text);cursor:pointer;" onclick="window.__navigate(\'/research?ticker=' + encodeURIComponent(x.ticker) + '\')">' + esc(x.ticker || '') + '</span>'
            + '<span style="color:var(--color-muted);">' + esc((x.fecha || '').slice(0, 10)) + '</span>'
            + '<span>' + pct(x.retorno_pct) + '</span>'
            + '<span style="color:var(--color-muted);">' + (x.spy_mismo_periodo_pct === null || x.spy_mismo_periodo_pct === undefined ? '—' : esc((x.spy_mismo_periodo_pct >= 0 ? '+' : '') + x.spy_mismo_periodo_pct + '%')) + '</span>'
            + '<span>' + pct(x.vs_spy_pp, ' pp') + '</span>'
            + '<span>' + objTxt + '</span>'
            + '</div>';
    }).join('');

    const cabeceraTabla = '<div style="display:grid;grid-template-columns:70px 90px 1fr 1fr 1fr 90px;gap:8px;padding:7px 16px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<span>TICKER</span><span>PUBLICADA</span><span>RETORNO</span><span>S&P 500</span><span>DIFERENCIA</span><span>OBJETIVO</span></div>';

    return caja('TESIS PUBLICADAS', resumen + avisoMuestra(r.n || 0) + cabeceraTabla + filas,
        'Retorno desde la fecha de publicación, con precios reales · ' + t.n_tesis + ' tesis');
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
