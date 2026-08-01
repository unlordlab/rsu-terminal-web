import { tt } from '/components/tooltip.js';
import { errorMessage, esc } from '/core/ui.js';

let _lastScanData = null;
let _lastMinScore = 60;

window.__canslimBack = function() {
    if (!_lastScanData) return;
    const scanEl = document.querySelector('#canslim-scan-result');
    const resEl  = document.querySelector('#canslim-result');
    if (scanEl) scanEl.innerHTML = renderScanResults(_lastScanData, _lastMinScore);
    if (resEl)  resEl.innerHTML  = '';
    if (scanEl) scanEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

export async function render(container) {
    container.innerHTML =
        header()
        + '<div id="canslim-market" style="margin-bottom:1.5rem;"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">'
        + analyzerPanel()
        + scannerPanel()
        + '</div>'
        + '<div id="canslim-result"></div>'
        + '<div id="canslim-scan-result"></div>';

    loadMarket(container);
    setupAnalyzer(container);
    setupScanner(container);
    loadScan(container);
}

function header() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">CAN SLIM</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Screener IBD · Trend Template Minervini · S&P 500 completo (503 acciones)</div>'
        + '</div>';
}

// ── MARKET WIDGET ─────────────────────────────────────────────────────────────

async function loadMarket(container) {
    const el = container.querySelector('#canslim-market');
    el.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;"><div style="color:var(--color-muted);font-size:12px;">Cargando estado del mercado...</div></div>';
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/canslim/market', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Error');
        el.innerHTML = renderMarket(data);
    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderMarket(data) {
    const s    = data.spy;
    const color = data.color;
    const chgC  = s.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const vixC  = data.vix >= 30 ? '#f23645' : data.vix >= 20 ? '#ffb800' : 'var(--color-accent)';

    // Score bar
    const scoreBar = '<div style="height:6px;background:var(--color-border);border-radius:3px;overflow:hidden;margin-top:6px;">'
        + '<div style="height:100%;width:' + esc(data.score) + '%;background:' + color + ';border-radius:3px;"></div>'
        + '</div>';

    // Indicators row
    const indicators = [
        { label: 'SPY', val: '$' + esc(s.price), sub: (s.chg_pct >= 0 ? '+' : '') + esc(s.chg_pct) + '% hoy', color: chgC },
        { label: 'SPY vs MA50', val: s.above_ma50 ? '▲ SOBRE' : '▼ BAJO', sub: 'MA50: $' + esc(s.ma50), color: s.above_ma50 ? 'var(--color-accent)' : '#f23645' },
        { label: 'SPY vs MA200', val: s.above_ma200 ? '▲ SOBRE' : '▼ BAJO', sub: 'MA200: $' + esc(s.ma200), color: s.above_ma200 ? 'var(--color-accent)' : '#f23645' },
        { label: 'VIX', val: data.vix.toFixed(1), sub: 'Riesgo: ' + esc(data.vix_risk), color: vixC },
        { label: 'SPY 1M', val: (s.perf_1m >= 0 ? '+' : '') + esc(s.perf_1m) + '%', sub: 'Rendimiento', color: s.perf_1m >= 0 ? 'var(--color-accent)' : '#f23645' },
        { label: 'SPY 3M', val: (s.perf_3m >= 0 ? '+' : '') + esc(s.perf_3m) + '%', sub: 'Rendimiento', color: s.perf_3m >= 0 ? 'var(--color-accent)' : '#f23645' },
        { label: 'Del máximo', val: esc(s.pct_from_high) + '%', sub: 'vs máximo 52s', color: s.pct_from_high >= -5 ? 'var(--color-accent)' : s.pct_from_high >= -15 ? '#ffb800' : '#f23645' },
    ].map(i =>
        '<div style="background:var(--color-surface2,#111);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 14px;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:4px;">' + i.label + '</div>'
        + '<div style="color:' + i.color + ';font-size:14px;font-weight:500;">' + i.val + '</div>'
        + '<div style="color:' + i.color + ';font-size:10px;opacity:.7;margin-top:2px;">' + i.sub + '</div>'
        + '</div>'
    ).join('');

    return '<div style="background:var(--color-surface);border:2px solid ' + color + '44;border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div>'
        // La M sale de get_market_status(), que mira SPY + VIX + amplitud.
        // Ese detalle vive entero en la pantalla de Mercado y hasta ahora no
        // habia forma de llegar desde aqui: se veia el veredicto sin poder
        // ver en que se basa (hallazgo #18).
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:.1em;margin-bottom:4px;">'
        + 'M — MARKET DIRECTION (CAN SLIM)'
        + '<span onclick="window.__navigate(\'/market\')" title="Ver el detalle del mercado: amplitud, VIX, curva de tipos" '
        + 'style="margin-left:8px;color:var(--color-secondary);cursor:pointer;text-decoration:underline;letter-spacing:0;">ver en Mercado →</span>'
        + '</div>'
        + '<div style="display:flex;align-items:center;gap:12px;">'
        + '<span style="color:' + color + ';font-size:15px;letter-spacing:.06em;font-weight:500;">► ' + esc(data.status_es) + '</span>'
        + '<span style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44;border-radius:3px;padding:2px 10px;font-size:11px;">' + esc(data.score) + '/100</span>'
        + '</div>'
        + scoreBar
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:' + (data.can_buy ? 'var(--color-accent)' : '#f23645') + ';font-size:13px;font-weight:500;">'
        + (data.can_buy ? '✓ MERCADO OPERATIVO' : '✗ EVITAR NUEVAS ENTRADAS')
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">Actualizado: ' + esc(data.timestamp) + '</div>'
        + '</div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;">' + indicators + '</div>'
        + '</div>';
}

// ── PANELS ────────────────────────────────────────────────────────────────────

function analyzerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS INDIVIDUAL ' + tt('canslim') + '</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<input id="ticker-input" type="text" placeholder="AAPL, NVDA, KTOS..." style="flex:1;background:var(--color-bg);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<button id="analyze-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">ANALIZAR</button>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:8px;">Cualquier ticker del mercado americano</div>'
        + '</div>';
}

function scannerPanel() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.08em;margin-bottom:1rem;">SCANNER S&P 500 COMPLETO</div>'
        + '<div style="display:flex;gap:8px;align-items:center;">'
        + '<div style="color:var(--color-muted);font-size:12px;">Score mínimo:</div>'
        // Umbrales recalibrados el 01/08/2026, al unificar el score con el del
        // análisis individual (hallazgo #6). Con la fórmula nueva el score
        // medio sube 18 puntos, así que los antiguos 40/60/80 seleccionaban
        // 297/148/33 en vez de los 159/58/12 de antes: las etiquetas dejaban
        // de describir lo que hacían.
        //
        // Los números NO se eligen para que salga un recuento concreto, sino
        // por el PERFIL que dejan pasar (ver tooltip): 85 es el suelo de
        // "fuerte en todo", 75 exige RS alto + tendencia + estar cerca de
        // máximos, y 60 es red de arrastre. Que el recuento suba o baje con
        // el mercado es justo lo que debe hacer un umbral absoluto.
        + '<select id="min-score" style="background:var(--color-bg);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;flex:1;">'
        + '<option value="60">60 — Amplio</option>'
        + '<option value="75" selected>75 — Estándar</option>'
        + '<option value="85">85 — Estricto</option>'
        + '</select>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:8px;">RS real calculado como percentil vs universo · Scan nocturno automático, sin scan on-demand</div>'
        + '</div>';
}

// ── SETUP ──────────────────────────────────────────────────────────────────────

function setupAnalyzer(container) {
    const input  = container.querySelector('#ticker-input');
    const btn    = container.querySelector('#analyze-btn');
    const result = container.querySelector('#canslim-result');

    async function doAnalyze() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent   = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Analizando ' + esc(ticker) + '...</div>';
        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/canslim/analyze/' + ticker, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Error de análisis');
            result.innerHTML = renderAnalysis(data);
            renderChart(data);
        } catch(e) {
            result.innerHTML = errorMessage(e.message);
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doAnalyze);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doAnalyze(); });

    // Deep-link ?ticker= -- mismo patrón que research.js
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        input.value = urlTicker.toUpperCase();
        doAnalyze();
    }
}

function setupScanner(container) {
    const select = container.querySelector('#min-score');
    const result = container.querySelector('#canslim-scan-result');

    // El scan ya viene completo del Gist nocturno (loadScan) -- cambiar el
    // score mínimo solo refiltra en el cliente, sin nueva petición. Mismo
    // patrón que RS/RW, que ya no tiene botón de scan on-demand (sesión 32).
    select.addEventListener('change', () => {
        _lastMinScore = parseInt(select.value, 10);
        if (_lastScanData) result.innerHTML = renderScanResults(_lastScanData, _lastMinScore);
    });
}

async function loadScan(container) {
    const result = container.querySelector('#canslim-scan-result');
    result.innerHTML = '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando scan nocturno...</div>';
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/canslim/gist', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Scan nocturno no disponible todavía');
        _lastScanData = data;
        const select = container.querySelector('#min-score');
        etiquetarOpciones(select, data.candidates || []);
        _lastMinScore = parseInt(select.value, 10);
        result.innerHTML = renderScanResults(data, _lastMinScore);
    } catch(e) {
        result.innerHTML = errorMessage(e.message);
    }
}

// ── RENDER ANALYSIS ───────────────────────────────────────────────────────────

function renderAnalysis(data) {
    const chgColor   = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr     = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';
    const mktcapStr  = !data.mktcap ? 'N/A'
                     : data.mktcap >= 1e12 ? '$' + (data.mktcap/1e12).toFixed(1) + 'T'
                     : data.mktcap >= 1e9  ? '$' + (data.mktcap/1e9).toFixed(1)  + 'B'
                     : '$' + (data.mktcap/1e6).toFixed(0) + 'M';

    const scores = data.scores || {};
    const techScore  = scores.tech  || 0;
    const fundScore  = scores.fundamental || 0;
    const combined   = data.canslim_score || 0;
    const fundAvail  = scores.fund_available !== false;

    const techColor  = techScore  >= 70 ? 'var(--color-accent)' : techScore  >= 50 ? '#ffb800' : '#f23645';
    const fundColor  = !fundAvail ? '#555' : fundScore  >= 70 ? 'var(--color-accent)' : fundScore  >= 40 ? '#ffb800' : '#f23645';
    const combColor  = combined   >= 70 ? 'var(--color-accent)' : combined   >= 50 ? '#ffb800' : '#f23645';

    // Badges CAN SLIM
    const letters   = data.can_slim_letters || {};
    const letterKeys = ['C','A','N','S','L','I','M'];
    const letterMap  = Object.entries(letters);
    const badges = letterKeys.map((l, i) => {
        const entry = letterMap[i];
        const val   = entry ? entry[1] : false;
        const noData = val === null;
        const ok    = val === true;
        const bg     = ok ? 'var(--color-accent)' : noData ? '#333' : 'transparent';
        const border = ok ? 'var(--color-accent)' : noData ? '#555' : '#f23645';
        const color  = ok ? '#000' : noData ? '#888' : '#f23645';
        const title  = entry ? entry[0] : l;
        return '<div style="width:32px;height:32px;border-radius:4px;background:' + bg + ';border:2px solid ' + border + ';display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:13px;font-weight:bold;color:' + color + ';" title="' + esc(title) + '">' + l + '</div>';
    }).join('');

    // Por qué cumple o falla cada letra. Hasta ahora el badge solo llevaba el
    // criterio en el `title`: se veía una "A" en rojo sin saber si había
    // fallado por un 24% o por un -3%. El backend ya calculaba el número.
    // Se distingue "no cumple" (rojo, con su valor) de "sin dato" (gris, y
    // se dice que no hay dato en vez de pintarlo como un suspenso).
    const detalleLetras = (data.can_slim_detalle || []).map(d => {
        const sinDato = d.cumple === null || d.valor == null;
        const col   = sinDato ? '#888' : d.cumple ? 'var(--color-accent)' : '#f23645';
        const icono = sinDato ? '·' : d.cumple ? '✓' : '✗';
        const valor = d.valor == null ? 'sin dato' : d.valor;
        return '<div style="display:grid;grid-template-columns:20px 1fr auto auto;gap:10px;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;align-items:baseline;">'
            + '<span style="color:' + col + ';font-weight:bold;">' + esc(d.letra) + '</span>'
            + '<span style="color:var(--color-muted);">' + esc(d.criterio) + '</span>'
            + '<span style="color:var(--color-muted);opacity:.7;">objetivo ' + esc(d.objetivo) + '</span>'
            + '<span style="color:' + col + ';min-width:82px;text-align:right;">' + icono + ' ' + esc(valor) + '</span>'
            + '</div>';
    }).join('');

    const detalleBloque = detalleLetras
        ? '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:.85rem 1rem;margin-top:.75rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:.08em;margin-bottom:6px;">POR QUÉ CUMPLE O FALLA CADA LETRA</div>'
            + detalleLetras
          + '</div>'
        : '';

    const ibdRows = [
        // data.ibd.rs puede ser null (sin universo de referencia para el
        // percentil real -- ver canslim_service.py _rs_rating_real). Antes
        // el backend rellenaba con una aproximación; ahora se muestra
        // "N/D" en vez de un número inventado.
        ['RS Rating ' + tt('rs-rating'),  data.ibd.rs != null ? data.ibd.rs : 'N/D', data.ibd.rs != null ? ratingColor(data.ibd.rs, 80, 60) : '#555'],
        ['EPS Rating',     data.ibd.eps,       ratingColor(data.ibd.eps, 80, 60)],
        ['Composite ' + tt('ibd-composite'), data.ibd.composite, ratingColor(data.ibd.composite, 80, 60)],
        ['SMR Rating',     data.ibd.smr,       gradeColor(data.ibd.smr)],
        ['Acc/Dis Rating', data.ibd.acc_dis,   gradeColor(data.ibd.acc_dis)],
    ].map(([label, val, color]) =>
        '<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
        + '<span style="color:var(--color-muted);">' + label + '</span>'
        + '<span style="color:' + color + ';font-weight:500;">' + esc(val) + '</span>'
        + '</div>'
    ).join('');

    const trendRows = Object.entries(data.trend.conditions || {}).map(([label, ok]) =>
        '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:var(--color-muted);">' + esc(label) + '</span>'
        + '<span style="color:' + (ok ? 'var(--color-accent)' : '#f23645') + ';">' + (ok ? '✓' : '✗') + '</span>'
        + '</div>'
    ).join('');

    // Fundamentales + institucional
    const f = data.fundamentals || {};
    const instPct    = f.inst_pct || 0;
    const instOk     = f.inst_data_ok;
    const instSource = f.inst_pct_source || 'N/A';
    const instColor  = !instOk ? '#555' : instPct > 60 ? 'var(--color-accent)' : instPct > 40 ? '#ffb800' : '#f23645';
    const instVal    = instOk ? instPct.toFixed(1) + '%' : 'Sin dato';

    const fundRows = [
        ['EPS Growth',    (f.eps_growth   || 0).toFixed(1) + '%', f.eps_growth   >= 25 ? 'var(--color-accent)' : f.eps_growth >= 10 ? '#ffb800' : '#f23645'],
        ['Sales Growth',  (f.sales_growth || 0).toFixed(1) + '%', f.sales_growth >= 25 ? 'var(--color-accent)' : f.sales_growth >= 10 ? '#ffb800' : '#f23645'],
        ['ROE',           (f.roe          || 0).toFixed(1) + '%', f.roe >= 20 ? 'var(--color-accent)' : f.roe >= 10 ? '#ffb800' : '#f23645'],
        ['Profit Margin', (f.margins      || 0).toFixed(1) + '%', f.margins >= 15 ? 'var(--color-accent)' : f.margins >= 5 ? '#ffb800' : '#f23645'],
    ].map(([label, val, c]) =>
        '<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
        + '<span style="color:var(--color-muted);">' + label + '</span>'
        + '<span style="color:' + c + ';">' + val + '</span>'
        + '</div>'
    ).join('');

    // Inst holders table
    const holders    = f.inst_holders || [];
    const holdersHtml = holders.length
        ? '<div style="margin-top:8px;border-top:1px solid var(--color-border);padding-top:8px;">'
          + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:.06em;margin-bottom:6px;">TOP HOLDERS INSTITUCIONALES ' + (instSource === 'major_holders' ? '✓' : '≈') + '</div>'
          + holders.map(h =>
              '<div style="display:flex;justify-content:space-between;font-size:10px;padding:3px 0;color:var(--color-muted);">'
              + '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:65%;">' + esc(h.name) + '</span>'
              + '<span style="color:var(--color-text);">' + (h.pct_out > 0 ? h.pct_out.toFixed(2) + '%' : (h.shares/1e6).toFixed(1) + 'M sh') + '</span>'
              + '</div>'
          ).join('')
          + '</div>'
        : '';

    // Score doble barra
    const scoreBars = '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);">'
        // Score técnico
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:.06em;">SCORE TÉCNICO <span style="font-size:9px;opacity:.6;">(RS + Trend + Vol)</span></span>'
        + '<span style="color:' + techColor + ';font-size:13px;font-weight:500;">' + techScore + '/100</span>'
        + '</div>'
        + '<div style="background:var(--color-border);border-radius:3px;height:5px;margin-bottom:10px;">'
        + '<div style="height:100%;width:' + techScore + '%;background:' + techColor + ';border-radius:3px;"></div>'
        + '</div>'
        // Score fundamental
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:.06em;">SCORE FUNDAMENTAL <span style="font-size:9px;opacity:.6;">(EPS + Sales + ROE + Margin)</span></span>'
        + '<span style="color:' + fundColor + ';font-size:13px;font-weight:500;">' + (fundAvail ? fundScore + '/100' : 'Sin datos') + '</span>'
        + '</div>'
        + '<div style="background:var(--color-border);border-radius:3px;height:5px;margin-bottom:10px;">'
        + '<div style="height:100%;width:' + (fundAvail ? fundScore : 0) + '%;background:' + fundColor + ';border-radius:3px;"></div>'
        + '</div>'
        // Score combinado
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        + '<span style="color:var(--color-muted);font-size:10px;letter-spacing:.06em;">CAN SLIM SCORE ' + (fundAvail ? '(60% Téc + 40% Fund)' : '(solo técnico · sin fundamentales)') + '</span>'
        + '<span style="color:' + combColor + ';font-size:16px;font-weight:500;">' + combined + '/100</span>'
        + '</div>'
        + '<div style="background:var(--color-border);border-radius:3px;height:7px;">'
        + '<div style="height:100%;width:' + combined + '%;background:' + combColor + ';border-radius:3px;transition:width .5s;"></div>'
        + '</div>'
        + (!fundAvail ? '<div style="color:#888;font-size:10px;margin-top:6px;">⚠ yfinance no devuelve fundamentales para este ticker. Score calculado solo sobre criterios técnicos.</div>' : '')
        + '</div>';

    const nearHighColor = data.near_new_high ? 'var(--color-accent)' : '#ffb800';

    return '<div style="margin-top:1.5rem;">'
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        + '<div>'
        + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">'
        + '<span style="color:var(--color-accent);font-size:22px;letter-spacing:0.1em;cursor:pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'" onclick="window.__navigate(\'/research?ticker=' + esc(data.ticker) + '\')">' + esc(data.ticker) + '</span>'
        + marcas(data)
        + '<span style="color:var(--color-muted);font-size:13px;">' + esc(data.name) + '</span>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:6px;">' + esc(data.sector) + ' · ' + esc(data.industry) + '</div>'
        // Enlaces cruzados. El ticker de arriba ya llevaba a Research, pero no
        // habia forma de saltar a RS/RW -- que es justo donde vive el detalle
        // del RS Rating que esta pantalla resume en un numero (hallazgo #20).
        // Los dos destinos aceptan ?ticker= desde la sesion 16.
        + '<div style="font-size:11px;color:var(--color-muted);margin-bottom:10px;">Ver este valor en: '
        + enlaceTicker('/research', data.ticker, 'Research', 'Ficha completa: fundamentales, noticias y RSU Score')
        + '<span style="opacity:.4;"> · </span>'
        + enlaceTicker('/rsrw', data.ticker, 'RS/RW', 'Fuerza relativa frente al mercado y a su sector')
        + '</div>'
        + '<div style="display:flex;gap:6px;align-items:center;">'
        + badges
        + '<span style="color:var(--color-muted);font-size:11px;margin-left:4px;">IBD: <span style="color:' + ratingColor(data.ibd.composite, 80, 60) + ';">' + esc(data.ibd.composite) + '</span></span>'
        + tt('ibd-composite')
        + '</div>'
        + '<div style="margin-top:6px;display:flex;gap:12px;">'
        + '<span style="color:var(--color-muted);font-size:11px;">Stage: <span style="color:' + (data.trend.passed ? 'var(--color-accent)' : '#f23645') + ';">' + (data.trend.passed ? '✅ ' + esc(data.trend.score) + '/7' : '✗ ' + esc(data.trend.score) + '/7') + '</span></span>'
        + '<span style="color:var(--color-muted);font-size:11px;">Del máx: <span style="color:' + nearHighColor + ';">' + esc(data.pct_from_high || 0) + '%</span></span>'
        + '<span style="color:var(--color-muted);font-size:11px;">Inst: <span style="color:' + instColor + ';">' + instVal + '</span></span>'
        + '</div>'
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:20px;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:12px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + mktcapStr + ' market cap ' + tt('market-cap') + '</div>'
        + '</div>'
        + '</div>'
        + scoreBars
        + detalleBloque
        + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        // IBD
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">IBD RATINGS</div>'
        + ibdRows
        + '</div>'
        // Trend
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">TREND TEMPLATE ' + tt('trend-template') + '</div>'
        + '<div style="color:' + (data.trend.passed ? 'var(--color-accent)' : '#f23645') + ';font-size:11px;">' + data.trend.score + '/7 ' + (data.trend.passed ? '✓' : '✗') + '</div>'
        + '</div>'
        + trendRows
        + '</div>'
        // Fundamentales
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">FUNDAMENTALES</div>'
        + '<div style="color:' + instColor + ';font-size:10px;">' + instVal + ' inst ' + tt('canslim-i') + '</div>'
        + '</div>'
        + fundRows
        + holdersHtml
        + '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:4px;">RENDIMIENTO</div>'
        + '<div style="display:flex;gap:1rem;font-size:12px;">'
        + '<div><span style="color:var(--color-muted);">3M </span><span style="color:' + (data.perf['3m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['3m'] >= 0 ? '+' : '') + data.perf['3m'].toFixed(1) + '%</span></div>'
        + '<div><span style="color:var(--color-muted);">6M </span><span style="color:' + (data.perf['6m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['6m'] >= 0 ? '+' : '') + data.perf['6m'].toFixed(1) + '%</span></div>'
        + '<div><span style="color:var(--color-muted);">12M </span><span style="color:' + (data.perf['12m'] >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.perf['12m'] >= 0 ? '+' : '') + data.perf['12m'].toFixed(1) + '%</span></div>'
        + '</div>'
        + '</div>'
        + '</div>'
        + '</div>'
        // Chart
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">PRECIO · MAs 50/200 · ÚLTIMOS 60 DÍAS</div>'
        + '<div style="position:relative;width:100%;height:340px;overflow:hidden;">'
        + '<canvas id="canslim-chart"></canvas>'
        + '</div>'
        + '</div>'
        // Botón volver
        + '<div style="margin-top:0.75rem;">'
        + '<button onclick="window.__canslimBack()" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;transition:all .15s;" onmouseover="this.style.borderColor=\'var(--color-accent)\';this.style.color=\'var(--color-accent)\'" onmouseout="this.style.borderColor=\'var(--color-border)\';this.style.color=\'var(--color-muted)\'">← Volver a resultados del scan</button>'
        + '</div>'
        + '</div>';
}

function renderChart(data) {
    // Destroy previous chart if exists
    if (window._canslimChart) {
        try { window._canslimChart.destroy(); } catch(_) {}
        window._canslimChart = null;
    }

    function buildChart() {
        const ctx = document.getElementById('canslim-chart');
        if (!ctx) return;
        const color = data.chg_pct >= 0 ? '#00ffad' : '#f23645';

        const datasets = [
            {
                label:           'Precio',
                data:            data.chart.closes,
                borderColor:     color,
                backgroundColor: color + '18',
                borderWidth:     1.5,
                pointRadius:     0,
                fill:            true,
                tension:         0.3,
                yAxisID:         'y',
            }
        ];

        if (data.chart.ma50 && data.chart.ma50.some(v => v !== null)) {
            datasets.push({
                label:       'MA50',
                data:        data.chart.ma50,
                borderColor: '#ffb800',
                borderWidth: 1,
                pointRadius: 0,
                fill:        false,
                tension:     0.3,
                yAxisID:     'y',
                spanGaps:    true,
            });
        }
        if (data.chart.ma200 && data.chart.ma200.some(v => v !== null)) {
            datasets.push({
                label:       'MA200',
                data:        data.chart.ma200,
                borderColor: '#888',
                borderWidth: 1,
                pointRadius: 0,
                fill:        false,
                tension:     0.3,
                yAxisID:     'y',
                spanGaps:    true,
            });
        }

        window._canslimChart = new Chart(ctx, {
            type: 'line',
            data: { labels: data.chart.dates, datasets },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                animation:           false,
                plugins: {
                    legend: {
                        display: true,
                        labels:  { color: '#666', font: { size: 10 }, boxWidth: 20 }
                    }
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
                }
            }
        });
    }

    if (window.Chart) {
        buildChart();
    } else {
        const script  = document.createElement('script');
        script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
        script.onload = buildChart;
        document.head.appendChild(script);
    }
}

// ── SCAN RESULTS ──────────────────────────────────────────────────────────────

// Desde el 01/08/2026 el scan usa el mismo Trend Template de 7 condiciones
// que el análisis individual, y publica cuántas cumple cada ticker. Se pinta
// "5/7" en vez de un tick: así se ve la diferencia entre un aprobado raspado
// y uno perfecto, y el umbral (5 de 7) deja de ser invisible.
//
// El `trend_score == null` no es defensivo por si acaso: entre que se
// despliega esto y corre el primer scan nocturno, el Gist todavía trae los
// datos del scan anterior, que no tienen ese campo. Durante esas horas se
// sigue pintando el tick de siempre en vez de un "undefined/7".
// Badges 💼 (posición abierta en Cartera) y ⭐ (en tu Watchlist), los mismos
// que ya llevan Scanner, RS/RW, Insider, Research y Options Flow. CANSLIM era
// el único módulo de listado sin ellos.
//
// `en_cartera` lo calcula el servicio (la Cartera es global); `in_watchlist`
// lo pone el router con el usuario de la petición, nunca dentro de la caché.
function marcas(r) {
    let out = '';
    if (r.en_cartera)   out += '<span title="Tienes una posición abierta en Cartera" style="font-size:11px;">💼</span>';
    if (r.in_watchlist) out += '<span title="Está en tu Watchlist" style="font-size:11px;">⭐</span>';
    return out ? '<span style="margin-left:5px;">' + out + '</span>' : '';
}

// Escribe cuántos candidatos deja pasar cada umbral en la propia opción del
// desplegable ("75 — Estándar · 66 candidatos").
//
// No es adorno: la razón por la que los umbrales se descalibraron sin que
// nadie lo notara es que el efecto de cada uno era invisible hasta pulsarlo.
// Con el recuento delante, si un cambio futuro de la fórmula vuelve a mover
// la escala, se ve al abrir el desplegable. Y en un mercado malo el número
// bajará -- eso es información, no una avería (ver el tooltip del SCORE).
function etiquetarOpciones(select, candidatos) {
    if (!select) return;
    [...select.options].forEach(op => {
        const umbral = parseInt(op.value, 10);
        const n = candidatos.filter(c => c.score >= umbral).length;
        const base = op.textContent.split(' · ')[0];
        op.textContent = base + ' · ' + n + (n === 1 ? ' candidato' : ' candidatos');
    });
}

// Enlace a otra pantalla de la terminal con el ticker ya cargado. El ticker
// se escapa con esc() aunque venga del backend: acaba dentro de un atributo
// onclick, que es el contexto donde un valor sin sanear duele más.
function enlaceTicker(ruta, ticker, texto, titulo) {
    return '<span onclick="window.__navigate(\'' + ruta + '?ticker=' + esc(ticker) + '\')" title="' + esc(titulo) + '" '
        + 'style="color:var(--color-secondary);cursor:pointer;text-decoration:underline;">' + esc(texto) + '</span>';
}

function trendCelda(c) {
    if (c.trend_score == null) return c.trend ? '✓' : '✗';
    return esc(c.trend_score) + '/7';
}

function renderScanResults(data, minScore) {
    // El Gist nocturno trae TODOS los candidatos ya puntuados (sesión 32) --
    // el filtro por score mínimo, antes resuelto en el backend vía query
    // param, ahora se aplica aquí, al cliente, sin nueva petición.
    const filtered = (data.candidates || []).filter(c => c.score >= (minScore || 0));
    const shown     = filtered.slice(0, 50);

    if (shown.length === 0) {
        return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;margin-top:1rem;">No se encontraron candidatos con ese score mínimo.</div>';
    }

    const cols = 'grid-template-columns:80px 80px 90px 60px 70px 70px 80px 70px 55px 80px';

    const header = '<div style="display:grid;' + cols + ';gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);letter-spacing:0.05em;">'
        + '<div>TICKER</div><div>PRECIO</div>'
        + '<div>12M PERF ' + tt('canslim-perf-12m') + '</div>'
        + '<div>RS ' + tt('rs-rating') + '</div>'
        + '<div>ACC/DIS ' + tt('canslim-acc-dis') + '</div>'
        + '<div>NEAR HIGH ' + tt('canslim-near-high') + '</div>'
        + '<div>VOL RATIO ' + tt('canslim-vol-ratio') + '</div>'
        + '<div>TREND ' + tt('canslim-scan-trend') + '</div>'
        + '<div>3WT ' + tt('canslim-3wt') + '</div>'
        + '<div>SCORE ' + tt('canslim-scan-score') + '</div>'
        + '</div>';

    const rows = shown.map(c => {
        const perfColor  = c.perf_12m >= 0 ? 'var(--color-accent)' : '#f23645';
        const scoreColor = c.score >= 70 ? 'var(--color-accent)' : c.score >= 50 ? '#ffb800' : '#f23645';
        const nearColor  = c.near_new_high ? 'var(--color-accent)' : '#ffb800';
        return '<div style="display:grid;' + cols + ';gap:8px;padding:9px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;cursor:pointer;" class="scan-row" data-ticker="' + esc(c.ticker) + '">'
            + '<div style="color:var(--color-accent);font-weight:500;">' + esc(c.ticker) + marcas(c) + '</div>'
            + '<div style="color:var(--color-text);">$' + c.price.toLocaleString('en-US') + '</div>'
            + '<div style="color:' + perfColor + ';">' + (c.perf_12m >= 0 ? '+' : '') + c.perf_12m.toFixed(1) + '%</div>'
            + '<div style="color:' + ratingColor(c.rs, 80, 60) + ';">' + esc(c.rs) + '</div>'
            + '<div style="color:' + gradeColor(c.acc_dis) + ';">' + esc(c.acc_dis) + '</div>'
            + '<div style="color:' + nearColor + ';">' + (c.near_new_high ? '✓' : esc(c.pct_from_high) + '%') + '</div>'
            + '<div style="color:' + (c.vol_ratio >= 1.5 ? 'var(--color-accent)' : 'var(--color-muted)') + ';">' + c.vol_ratio.toFixed(1) + 'x</div>'
            + '<div style="color:' + (c.trend ? 'var(--color-accent)' : '#f23645') + ';">' + trendCelda(c) + '</div>'
            + '<div style="color:' + (c.is_3wt ? 'var(--color-accent)' : 'var(--color-muted)') + ';">' + (c.is_3wt ? '✓' : '—') + '</div>'
            + '<div style="color:' + scoreColor + ';font-weight:500;">' + esc(c.score) + '</div>'
            + '</div>';
    }).join('');

    const summary = '<div style="display:flex;gap:1.5rem;padding:8px 14px;font-size:11px;color:var(--color-muted);border-bottom:1px solid var(--color-border);">'
        + '<span>Escaneados: <b style="color:var(--color-text);">' + esc(data.scanned) + '</b></span>'
        + '<span>Candidatos: <b style="color:var(--color-accent);">' + esc(filtered.length) + '</b></span>'
        + '<span>Mostrando: <b style="color:var(--color-text);">' + shown.length + '</b></span>'
        + '<span style="margin-left:auto;">' + esc(data.timestamp) + '</span>'
        + '</div>';

    const html = '<div style="margin-top:1.5rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:13px;letter-spacing:0.08em;">RESULTADOS — RS REAL (PERCENTIL vs UNIVERSO)</div>'
        + summary + header + '<div style="max-height:600px;overflow-y:auto;">' + rows + '</div>'
        + '</div>';

    setTimeout(() => {
        document.querySelectorAll('.scan-row').forEach(row => {
            row.addEventListener('mouseenter', () => row.style.background = 'rgba(255,255,255,0.02)');
            row.addEventListener('mouseleave', () => row.style.background = 'transparent');
            row.addEventListener('click', () => {
                const ticker = row.getAttribute('data-ticker');
                document.getElementById('ticker-input').value = ticker;
                document.getElementById('analyze-btn').click();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }, 100);

    return html;
}

// ── UTILS ─────────────────────────────────────────────────────────────────────

function ratingColor(val, high, mid) {
    if (val >= high) return 'var(--color-accent)';
    if (val >= mid)  return '#ffb800';
    return '#f23645';
}

function gradeColor(grade) {
    if (grade === 'A') return 'var(--color-accent)';
    if (grade === 'B') return '#90ee90';
    if (grade === 'C') return '#ffb800';
    if (grade === 'D') return '#ff8c00';
    return '#f23645';
}

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}