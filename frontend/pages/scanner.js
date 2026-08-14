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
        + '<div id="scanner-result"></div>';

    setupPanel(container);
    await loadUniverseMeta(container);
    runFilter(container); // primera carga sin filtros = universo completo ordenado por score
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

        + criterionBlock('rvol', 'RVOL ≥ ' + tt('rvol'), 'number', '1.5', '0.1')
        + criterionBlock('rs', 'RS Percentile ≥ ' + tt('rs-rating'), 'number', '70', '1')
        + criterionBlock('score', 'Score Técnico ≥ ' + tt('score-tecnico'), 'number', '60', '1')
        + criterionBlock('absorcion', 'Días de Absorción ≥ ' + tt('scanner-absorcion'), 'number', '3', '1')

        + selectCriterionBlock('phase', 'FASE WEINSTEIN ' + tt('market-phase'), PHASE_OPTIONS.map(o => '<option value="' + o.value + '">' + o.label + '</option>').join(''))
        + selectCriterionBlock('sector', 'SECTOR', '<option value="">Cargando sectores...</option>')
        + toggleCriterionBlock('newhigh', '🔥 MÁXIMOS 52 SEMANAS ' + tt('new-high-52w'), 'Aprox. a ATH')
        + toggleCriterionBlock('l3zona', 'ZONA BAJA DEL INDICADOR RSU ' + tt('rsu-flow'), 'Entre 10 y 20')

        + '</div>'
        + '<div style="display:flex;justify-content:space-between;align-items:center;">'
        + '<div style="color:var(--color-muted);font-size:11px;">Los criterios activados se combinan con AND (deben cumplirse todos). El resultado se ordena por Score Técnico.</div>'
        + '<button id="scanner-run-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ESCANEAR</button>'
        + '</div>'
        + '</div>';
}

function criterionBlock(id, label, type, placeholder, step) {
    return '<div id="scanner-' + id + '-card" class="scanner-crit-card" data-active="false" '
        + 'style="border:1px solid var(--color-border);border-radius:var(--radius);padding:10px;cursor:pointer;transition:border-color .15s,background .15s;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<span id="scanner-' + id + '-dot" style="width:9px;height:9px;border-radius:50%;border:1px solid var(--color-muted);flex-shrink:0;"></span>'
        + '<span style="color:var(--color-text);font-size:12px;letter-spacing:0.03em;">' + label + '</span>'
        + '<input type="checkbox" id="scanner-' + id + '-toggle" style="display:none;">'
        + '</div>'
        + '<input type="' + type + '" id="scanner-' + id + '-value" step="' + step + '" placeholder="' + placeholder + '" disabled '
        + 'style="width:100%;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:6px 8px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;box-sizing:border-box;cursor:not-allowed;">'
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
    ['rvol', 'rs', 'score', 'phase', 'sector'].forEach(id => {
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

    // Criterio booleano (máximos 52 semanas) — no tiene campo de valor, así
    // que el propio click en la card ya alterna el estado directamente.
    const newHighCard = container.querySelector('#scanner-newhigh-card');
    if (newHighCard) {
        newHighCard.addEventListener('click', (e) => {
            if (e.target.closest('.tt-trigger')) return;
            const isActive = newHighCard.dataset.active === 'true';
            const toggle = container.querySelector('#scanner-newhigh-toggle');
            const dot    = container.querySelector('#scanner-newhigh-dot');
            toggle.checked = !isActive;
            newHighCard.dataset.active = String(!isActive);
            newHighCard.style.borderColor = !isActive ? 'var(--color-accent)' : 'var(--color-border)';
            newHighCard.style.background  = !isActive ? 'var(--color-accent)11' : 'transparent';
            dot.style.background  = !isActive ? 'var(--color-accent)' : 'transparent';
            dot.style.borderColor = !isActive ? 'var(--color-accent)' : 'var(--color-muted)';
        });
    }

    const btn = container.querySelector('#scanner-run-btn');
    btn.addEventListener('click', () => runFilter(container));
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
    const params = new URLSearchParams();
    const rvolOn  = container.querySelector('#scanner-rvol-toggle').checked;
    const rsOn    = container.querySelector('#scanner-rs-toggle').checked;
    const scoreOn = container.querySelector('#scanner-score-toggle').checked;
    const phaseOn = container.querySelector('#scanner-phase-toggle').checked;
    const sectorOn = container.querySelector('#scanner-sector-toggle').checked;

    if (rvolOn) {
        const v = container.querySelector('#scanner-rvol-value').value;
        if (v !== '') params.set('rvol_min', v);
    }
    if (rsOn) {
        const v = container.querySelector('#scanner-rs-value').value;
        if (v !== '') params.set('rs_min', v);
    }
    if (scoreOn) {
        const v = container.querySelector('#scanner-score-value').value;
        if (v !== '') params.set('score_min', v);
    }
    const absorcionOn = container.querySelector('#scanner-absorcion-toggle').checked;
    if (absorcionOn) {
        const v = container.querySelector('#scanner-absorcion-value').value;
        if (v !== '') params.set('absorcion_min', v);
    }
    if (phaseOn) {
        const v = container.querySelector('#scanner-phase-value').value;
        if (v !== '') params.set('phase', v);
    }
    if (sectorOn) {
        const v = container.querySelector('#scanner-sector-value').value;
        if (v !== '') params.set('sector', v);
    }
    const newHighOn = container.querySelector('#scanner-newhigh-toggle').checked;
    if (newHighOn) {
        params.set('new_high_only', 'true');
    }
    const l3ZonaOn = container.querySelector('#scanner-l3zona-toggle').checked;
    if (l3ZonaOn) {
        params.set('l3_zona_baja', 'true');
    }
    params.set('limit', '200');
    return params.toString();
}

async function runFilter(container) {
    const result = container.querySelector('#scanner-result');
    const btn    = container.querySelector('#scanner-run-btn');
    if (btn) { btn.textContent = 'ESCANEANDO...'; btn.style.opacity = '0.7'; }
    result.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:0.5rem;">Aplicando criterios sobre el universo precomputado...</div>';

    try {
        const qs    = buildQuery(container);
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
            + '<div style="color:' + phaseClr + ';font-size:10px;">' + esc(r.phase_label || '—') + '</div>'
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