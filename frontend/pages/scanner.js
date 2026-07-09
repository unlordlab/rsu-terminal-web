import { isRateLimitMessage, errorMessage } from '/core/ui.js';
import { tt } from '/components/tooltip.js';

const PHASE_OPTIONS = [
    { value: '', label: 'Todas' },
    { value: '2', label: 'Fase 2 · Avance' },
    { value: '1', label: 'Fase 1 · Acumulación/Giro' },
    { value: '3', label: 'Fase 3 · Distribución' },
    { value: '4', label: 'Fase 4 · Declive' },
];

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

        + selectCriterionBlock('phase', 'FASE WEINSTEIN ' + tt('market-phase'), PHASE_OPTIONS.map(o => '<option value="' + o.value + '">' + o.label + '</option>').join(''))
        + selectCriterionBlock('sector', 'SECTOR', '<option value="">Cargando sectores...</option>')

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

    const btn = container.querySelector('#scanner-run-btn');
    btn.addEventListener('click', () => runFilter(container));
}

async function loadUniverseMeta(container) {
    const metaEl   = container.querySelector('#scanner-meta');
    const sectorEl = container.querySelector('#scanner-sector-value');
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/scanner/universe', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data  = await res.json();
        if (!data.ok) {
            if (metaEl) metaEl.innerHTML = '<span style="color:#f23645;">' + (data.error || 'Error') + '</span>';
            return;
        }
        if (metaEl) {
            metaEl.textContent = 'Universo: ' + data.universe_size + ' tickers · Actualizado: ' + data.freshness;
        }
        if (sectorEl && data.sectors) {
            sectorEl.innerHTML = data.sectors.map(s => '<option value="' + s + '">' + s + '</option>').join('');
        }
    } catch (e) {
        if (metaEl) metaEl.innerHTML = '<span style="color:#f23645;">' + e.message + '</span>';
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
    if (phaseOn) {
        const v = container.querySelector('#scanner-phase-value').value;
        if (v !== '') params.set('phase', v);
    }
    if (sectorOn) {
        const v = container.querySelector('#scanner-sector-value').value;
        if (v !== '') params.set('sector', v);
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
        const token = sessionStorage.getItem('rsu_token');
        const qs    = buildQuery(container);
        const res   = await fetch('/api/v1/scanner/filter?' + qs, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
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
    const activeLabels = Object.entries(data.active_criteria || {}).map(([k, v]) => k + '=' + v);
    const criteriaLine = activeLabels.length
        ? activeLabels.join(' · ')
        : 'Sin criterios activos — mostrando universo completo ordenado por Score Técnico';

    const header = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;">' + data.matched + ' / ' + data.universe_size + ' tickers cumplen</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">' + criteriaLine + '</div>'
        + '</div>';

    const tableHeader = '<div style="display:grid;grid-template-columns:70px 90px 60px 60px 70px 1fr 1fr 34px;gap:6px;padding:7px 12px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<div>TICKER</div><div>PRECIO</div><div>RVOL</div><div>RS%</div><div>SCORE</div><div>FASE</div><div>SECTOR</div><div></div>'
        + '</div>';

    const rows = (data.results || []).map(r => {
        const rvolClr  = (r.rvol || 0) >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)';
        const rsClr    = (r.rs_pct || 0) >= 70 ? 'var(--color-accent)' : (r.rs_pct || 0) <= 30 ? '#f23645' : '#ffb800';
        const scoreClr = (r.score_tecnico || 0) >= 70 ? 'var(--color-accent)' : (r.score_tecnico || 0) >= 40 ? '#ffb800' : '#f23645';
        const phaseClr = r.phase === 2 ? 'var(--color-accent)' : r.phase === 4 ? '#f23645' : '#ffb800';

        return '<div style="display:grid;grid-template-columns:70px 90px 60px 60px 70px 1fr 1fr 34px;gap:6px;padding:8px 12px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div onclick="goToResearch(\'' + (r.ticker || '') + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;cursor:pointer;">' + (r.ticker || '') + '</div>'
            + '<div style="color:var(--color-muted);">' + (r.precio != null ? '$' + r.precio.toFixed(2) : '—') + '</div>'
            + '<div style="color:' + rvolClr + ';">' + (r.rvol != null ? r.rvol.toFixed(2) + 'x' : '—') + '</div>'
            + '<div style="color:' + rsClr + ';font-weight:500;">' + (r.rs_pct != null ? r.rs_pct.toFixed(0) : '—') + '</div>'
            + '<div style="color:' + scoreClr + ';font-weight:500;">' + (r.score_tecnico != null ? r.score_tecnico.toFixed(0) : '—') + '</div>'
            + '<div style="color:' + phaseClr + ';font-size:10px;">' + (r.phase_label || '—') + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + (r.sector || '—') + '</div>'
            + '<div style="text-align:center;"><button onclick="window.__quickAddWatchlist(\'' + (r.ticker || '') + '\', this)" title="Añadir a watchlist" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:3px;padding:2px 6px;font-size:11px;cursor:pointer;">＋</button></div>'
            + '</div>';
    }).join('');

    el.innerHTML = header
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + tableHeader
        + (rows || '<div style="padding:1.5rem;text-align:center;color:var(--color-muted);font-size:12px;">Ningún ticker cumple los criterios activados. Prueba a aflojar algún umbral.</div>')
        + '</div>';
}