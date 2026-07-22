import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = pageShell();
    const result = container.querySelector('#btc-result');

    // Cargar dashboard y backtest en paralelo
    loadDashboard(result);

    container.querySelector('#btn-backtest').addEventListener('click', () => {
        loadBacktest(result);
    });
    container.querySelector('#btn-dashboard').addEventListener('click', () => {
        loadDashboard(result);
    });
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">₿ BTC STRATUM ' + tt('btc-stratum') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Modelo de Acumulación RSU · MA200W + MVRV + Puell + AHR999</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<button id="btn-dashboard" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;font-weight:500;">📊 DASHBOARD</button>'
        + '<button id="btn-backtest"  style="background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;letter-spacing:0.05em;">📈 BACKTEST</button>'
        + '</div>'
        + '<div id="btc-result"></div>';
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────

async function loadDashboard(el) {
    el.innerHTML = loading('Cargando datos BTC...');
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/btc-stratum/dashboard', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderDashboard(data);
        renderChart(data);
    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderDashboard(data) {
    return headerSection(data)
        + alertsSection(data)
        + scoreSection(data)
        + componentsSection(data)
        + chartSection(data)
        + halvingSection(data)
        + macroSection(data)
        + levelsSection(data)
        + hashrateSection(data)
        + stressSection(data)
        + methodologySection();
}

function headerSection(data) {
    const chgColor = data.chg_24h >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr   = (data.chg_24h >= 0 ? '+' : '') + data.chg_24h + '%';
    const z        = data.zone;

    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'

        // Precio
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:6px;">BITCOIN · BTC/USD</div>'
        + '<div style="color:var(--color-text);font-size:32px;font-weight:500;">$' + Number(data.price).toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;margin-top:4px;">' + chgStr + ' 24h</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:4px;">ATH: $' + Number(data.ath).toLocaleString('en-US') + ' · Drawdown: <span style="color:#f23645;">' + data.drawdown + '%</span></div>'
        + sourcesBar(data.sources)
        + '</div>'

        // RSU Score
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:6px;">RSU SCORE ' + tt('rsu-btc-score') + '</div>'
        + '<div style="color:' + data.rsu_signal.color + ';font-size:36px;font-weight:500;">' + data.rsu_score + '</div>'
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin:8px 0;">'
        + '<div style="height:100%;width:' + data.rsu_score + '%;background:' + data.rsu_signal.color + ';border-radius:4px;transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="color:' + data.rsu_signal.color + ';font-size:12px;letter-spacing:0.08em;">' + data.rsu_signal.label + '</div>'
        + '</div>'

        // Zona
        + '<div style="background:var(--color-surface);border:1px solid ' + z.color + '44;border-radius:var(--radius);padding:1.25rem;">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:6px;">ZONA ACTUAL · URGENCIA</div>'
        + '<div style="color:' + z.color + ';font-size:18px;font-weight:500;margin-bottom:4px;">' + z.zone + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Asignación sugerida: <span style="color:' + z.color + ';font-size:16px;font-weight:500;">' + z.allocation + '%</span></div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:4px;">Urgencia: <span style="color:' + z.color + ';">' + z.urgency + '</span></div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:4px;">vs MA200W: <span style="color:' + (data.deviation >= 0 ? '#f23645' : 'var(--color-accent)') + ';">' + (data.deviation >= 0 ? '+' : '') + data.deviation + '%</span></div>'
        + '</div>'
        + '</div>';
}

function alertsSection(data) {
    if (!data.alerts || !data.alerts.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">⚡ ALERTAS ACTIVAS</div>'
        + data.alerts.map(a => '<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
            + '<span style="font-size:16px;">' + a.icon + '</span>'
            + '<span style="color:' + a.color + ';">' + a.msg + '</span>'
            + '</div>').join('')
        + '</div>';
}

function scoreSection(data) {
    const c = data.components;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">DESGLOSE RSU SCORE ' + tt('rsu-btc-score') + '</div>'
        + '<div style="color:' + data.rsu_signal.color + ';font-size:20px;font-weight:500;">' + data.rsu_score + '/100</div>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;">'
        + componentCard('MA 200W', c.ma200, '40%', tt('ma200w'))
        + componentCard('MVRV Z-Score', c.mvrv, '30%', tt('mvrv-z'))
        + componentCard('Puell Multiple', c.puell, '20%', tt('puell-multiple'))
        + componentCard('AHR999', c.ahr999, '10%', tt('ahr999'))
        + '</div>'
        + '</div>';
}

function componentCard(name, comp, weight, tooltip) {
    const color = comp.score < 40 ? 'var(--color-accent)' : comp.score < 70 ? '#ffb800' : '#f23645';
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;text-align:center;">'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">' + name + ' ' + tooltip + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">Peso: ' + weight + '</div>'
        + '<div style="color:' + color + ';font-size:22px;font-weight:500;">' + comp.score.toFixed(1) + '</div>'
        + '<div style="background:var(--color-surface);border-radius:2px;height:4px;margin-top:6px;">'
        + '<div style="height:100%;width:' + comp.score + '%;background:' + color + ';border-radius:2px;"></div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">Raw: ' + comp.raw + '</div>'
        + '</div>';
}

function componentsSection(data) {
    const curv = data.curvature;
    const color = curv.slope > 0.2 ? 'var(--color-accent)' : curv.slope < -0.2 ? '#f23645' : '#ffb800';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">CURVATURA MA200W</div>'
        + '<div style="display:flex;gap:2rem;flex-wrap:wrap;font-size:12px;">'
        + '<div><span style="color:var(--color-muted);">MA200W: </span><span style="color:var(--color-text);">$' + Number(curv.ma_value).toLocaleString('en-US') + '</span></div>'
        + '<div><span style="color:var(--color-muted);">Pendiente: </span><span style="color:' + color + ';">' + curv.slope + '% (30d)</span></div>'
        + '<div><span style="color:var(--color-muted);">Tendencia: </span><span style="color:' + color + ';">' + curv.trend + '</span></div>'
        + '<div><span style="color:var(--color-muted);">Aceleración: </span><span style="color:' + (curv.acceleration === 'ACELERANDO' ? 'var(--color-accent)' : '#ffb800') + ';">' + curv.acceleration + '</span></div>'
        + '</div>'
        + '</div>';
}

function chartSection(data) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">PRECIO BTC · MA200W · ZONAS (3 AÑOS)</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Semanal</div>'
        + '</div>'
        + '<div style="padding:16px;"><canvas id="btc-chart" height="200"></canvas></div>'
        + '</div>';
}

function halvingSection(data) {
    const h = data.halving;
    const phaseColor = h.phase === 'ACUMULACIÓN' ? 'var(--color-accent)'
        : h.phase === 'BULL TEMPRANO' ? '#00d9ff'
        : h.phase === 'BULL AVANZADO' ? '#ffb800'
        : h.phase === 'DISTRIBUCIÓN'  ? '#ff9800'
        : '#f23645';

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">CICLO HALVING ' + tt('halving-cycle') + '</div>'
        + '<div style="display:flex;gap:2rem;flex-wrap:wrap;align-items:center;">'
        + '<div style="flex:1;">'
        + '<div style="color:' + phaseColor + ';font-size:18px;font-weight:500;margin-bottom:4px;">' + h.phase + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Progreso del ciclo: <span style="color:var(--color-text);">' + h.progress_pct + '%</span></div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Días desde halving: <span style="color:var(--color-text);">' + h.days_since + '</span></div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Días al próximo: <span style="color:#ffb800;">' + h.days_to_next + '</span> (' + h.next_halving + ')</div>'
        + '</div>'
        + '<div style="flex:2;">'
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:8px;">'
        + '<div style="height:100%;width:' + h.progress_pct + '%;background:linear-gradient(90deg,var(--color-accent),' + phaseColor + ');border-radius:4px;"></div>'
        + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--color-muted);margin-top:4px;">'
        + '<span>' + h.last_halving + '</span><span>' + h.next_halving + '</span>'
        + '</div>'
        + '</div>'
        + '</div>'
        + '</div>';
}

function macroSection(data) {
    const m = data.macro;
    // m.dxy puede venir null si la fuente (yfinance) falló -- antes el
    // backend fabricaba 103.0/50/NEUTRAL fijo; ahora se admite la ausencia
    // y aquí se muestra explícitamente "N/D" en vez de "null" o un color
    // engañoso (null < 50 evaluaría true en JS por coerción a 0).
    const hasData = m.dxy != null;
    const statusColor = m.status === 'EXPANSIVO' ? 'var(--color-accent)' : m.status === 'NEUTRAL' ? '#ffb800' : m.status === 'RESTRICTIVO' ? '#f23645' : 'var(--color-muted)';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">CONDICIONES MACRO</div>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'
        + macroCard('DXY', hasData ? m.dxy : 'N/D', 'Índice Dólar — valor alto = adverso para BTC', hasData ? (m.dxy_score < 50 ? 'var(--color-accent)' : '#f23645') : 'var(--color-muted)')
        + macroCard('LIQUIDEZ', hasData ? m.liquidity_score + '/100' : 'N/D', 'Score de condiciones de liquidez global', hasData ? statusColor : 'var(--color-muted)')
        + macroCard('ENTORNO', hasData ? m.status : 'Sin datos', 'Condición macroeconómica actual', hasData ? statusColor : 'var(--color-muted)')
        + '</div>'
        + '</div>';
}

function macroCard(label, value, desc, color) {
    return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;">'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;">' + label + '</div>'
        + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + value + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">' + desc + '</div>'
        + '</div>';
}

function levelsSection(data) {
    const l = data.levels;
    const price = data.price;
    const rows = [
        { label: 'OPORTUNIDAD MÁXIMA (-50% MA)', value: l.minus_50, color: '#006b1b' },
        { label: 'COMPRA AGRESIVA (-25% MA)',    value: l.minus_25, color: '#009627' },
        { label: 'MA 200 SEMANAS',               value: l.ma200,    color: 'var(--color-accent)' },
        { label: 'BUENA COMPRA (+25% MA)',        value: l.plus_25,  color: '#ffb800' },
        { label: 'ZONA DCA (+50% MA)',            value: l.plus_50,  color: '#ff9800' },
    ];
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">NIVELES CLAVE · MA200W</div>'
        + rows.map(r => {
            const dist = r.value ? ((price - r.value) / r.value * 100).toFixed(1) : null;
            const isCurrent = r.value && Math.abs(price - r.value) < r.value * 0.02;
            return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);background:' + (isCurrent ? r.color + '11' : 'transparent') + ';">'
                + '<div style="color:' + r.color + ';font-size:11px;">' + r.label + '</div>'
                + '<div style="text-align:right;">'
                + '<div style="color:var(--color-text);font-size:13px;font-weight:500;">$' + Number(r.value).toLocaleString('en-US') + '</div>'
                + (dist ? '<div style="color:' + (parseFloat(dist) >= 0 ? '#f23645' : 'var(--color-accent)') + ';font-size:10px;">' + (parseFloat(dist) >= 0 ? '+' : '') + dist + '% actual</div>' : '')
                + '</div>'
                + '</div>';
        }).join('')
        + '</div>';
}

function stressSection(data) {
    const s = data.stress;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">STRESS TEST · ESCENARIOS ADVERSOS ' + tt('stress-test') + '</div>'
        + '<div style="padding:8px 14px;background:rgba(242,54,69,0.05);border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">⚠ Las probabilidades son estimaciones subjetivas, no predicciones. Usar solo como referencia para gestión de riesgo.</div>'
        + s.map(sc => {
            const sevColor = sc.severity === 'extreme' ? '#f23645' : sc.severity === 'high' ? '#ff9800' : '#ffb800';
            return '<div style="padding:12px 14px;border-bottom:1px solid var(--color-border);">'
                + '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
                + '<div style="color:' + sevColor + ';font-size:12px;font-weight:500;">' + sc.name + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;">' + sc.probability + '</div>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:4px;">' + sc.description + '</div>'
                + '<div style="display:flex;gap:1.5rem;font-size:11px;">'
                + '<span style="color:var(--color-muted);">Precio objetivo: <span style="color:' + sevColor + ';">$' + Number(sc.target).toLocaleString('en-US') + '</span></span>'
                + '<span style="color:var(--color-muted);">Caída: <span style="color:' + sevColor + ';">-' + sc.drop_pct + '%</span></span>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">💡 ' + sc.hedge + '</div>'
                + '</div>';
        }).join('')
        + '</div>';
}

function methodologySection() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">METODOLOGÍA RSU v2.1</div>'
        + '<div style="color:var(--color-muted);font-size:11px;line-height:1.8;">'
        + '⚠️ <strong style="color:var(--color-text);">IMPORTANTE</strong>: Los indicadores MVRV, Puell y AHR999 son aproximaciones basadas en precio/MA200W. Los valores reales requieren datos on-chain de Glassnode. Usar como orientación, no como señal definitiva.<br><br>'
        + '<strong style="color:var(--color-text);">MA 200 Semanas (40%)</strong> — Soporte histórico más importante de BTC. Precio bajo = oportunidad histórica.<br>'
        + '<strong style="color:var(--color-text);">MVRV Z-Score (30%)</strong> — Proxy de valor de mercado vs valor realizado. &lt;0 = infravalorado.<br>'
        + '<strong style="color:var(--color-text);">Puell Multiple (20%)</strong> — Proxy de ingresos mineros vs media anual. &lt;0.5 = stress minero.<br>'
        + '<strong style="color:var(--color-text);">AHR999 (10%)</strong> — Índice de acumulación basado en relación precio/MA200. &lt;0.45 = compra fuerte.<br><br>'
        + '<strong style="color:#f23645;">Este módulo no es asesoramiento financiero. Bitcoin es un activo de alto riesgo. Solo invertir lo que puedas permitirte perder.</strong>'
        + '</div>'
        + '</div>';
}

// ── BACKTEST ──────────────────────────────────────────────────────────────────

async function loadBacktest(el) {
    el.innerHTML = loading('Ejecutando backtest histórico...');
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/btc-stratum/backtest', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        el.innerHTML = renderBacktest(data);
        renderBacktestChart(data);
    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

function renderBacktest(data) {
    const results = data.results;
    const bh      = results[0] ? results[0].bh_return : 0;

    const summary = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">BACKTEST HISTÓRICO · RSU STRATUM ' + tt('btc-backtest') + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:1rem;">Capital inicial: $10,000 · Estrategia: comprar 50% capital disponible cuando RSU &lt; umbral, vender cuando RSU &gt; 80</div>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'
        + results.map(r => {
            const color  = r.total_return > bh ? 'var(--color-accent)' : r.total_return > 0 ? '#ffb800' : '#f23645';
            const alphaColor = r.alpha > 0 ? 'var(--color-accent)' : '#f23645';
            return '<div style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">' + r.label + '</div>'
                + '<div style="color:' + color + ';font-size:22px;font-weight:500;">+' + r.total_return + '%</div>'
                + '<div style="color:var(--color-muted);font-size:11px;margin-top:4px;">Capital final: <span style="color:var(--color-text);">$' + Number(r.final_value).toLocaleString('en-US') + '</span></div>'
                + '<div style="color:var(--color-muted);font-size:11px;">Alpha vs B&H: <span style="color:' + alphaColor + ';">' + (r.alpha > 0 ? '+' : '') + r.alpha + '%</span></div>'
                + '<div style="color:var(--color-muted);font-size:11px;">Operaciones: ' + r.n_buys + ' compras · ' + r.n_sells + ' ventas</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);font-size:11px;color:var(--color-muted);">BTC Buy & Hold: <span style="color:var(--color-text);">+' + bh + '%</span> · El backtest asume ejecución perfecta sin slippage ni fees</div>'
        // El periodo evaluado empieza donde la MA200W (200 semanas) ya
        // tiene histórico real -- antes de esa fecha no hay buffer previo
        // como sí tiene el RSU Algoritmo, así que se recorta la serie
        // entera en vez de usar un valor inmaduro (ver backend, sesión
        // "min_periods mal etiquetado", 22/07/2026).
        + (data.period_start ? '<div style="font-size:10px;color:var(--color-muted);margin-top:4px;">Periodo evaluado: desde ' + data.period_start + ' (' + (data.period_days / 365).toFixed(1) + ' años) — antes de esa fecha la MA200W no tenía histórico suficiente</div>' : '')
        + '</div>';

    const chartHtml = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">RSU SCORE HISTÓRICO · SEÑALES DE COMPRA/VENTA</div>'
        + '<canvas id="backtest-chart" height="200"></canvas>'
        + '</div>';

    const lastTrades = results[1] ? results[1].trades : [];
    const tradesHtml = lastTrades.length
        ? '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
            + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">ÚLTIMAS OPERACIONES · RSU &lt; 40</div>'
            + '<div style="display:grid;grid-template-columns:100px 80px 120px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
            + '<div>FECHA</div><div>TIPO</div><div>PRECIO</div><div>RSU</div>'
            + '</div>'
            + lastTrades.map(t => '<div style="display:grid;grid-template-columns:100px 80px 120px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<div style="color:var(--color-muted);">' + t.date + '</div>'
                + '<div style="color:' + (t.type === 'BUY' ? 'var(--color-accent)' : '#f23645') + ';font-weight:500;">' + t.type + '</div>'
                + '<div style="color:var(--color-text);">$' + Number(t.price).toLocaleString('en-US') + '</div>'
                + '<div style="color:var(--color-muted);">' + t.rsu + '</div>'
                + '</div>').join('')
            + '</div>'
        : '';

    const disclaimer = '<div style="background:rgba(242,54,69,0.05);border:1px solid rgba(242,54,69,0.2);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;font-size:11px;color:var(--color-muted);">'
        + '⚠️ <strong style="color:#f23645;">DISCLAIMER BACKTEST</strong>: Resultados históricos no garantizan rentabilidad futura. El backtest asume ejecución perfecta, sin costes de transacción, sin impacto en mercado y con datos de cierre diario. En la práctica los resultados diferirán significativamente. No es asesoramiento financiero.'
        + '</div>';

    return summary + chartHtml + tradesHtml + disclaimer;
}

// ── CHARTS ────────────────────────────────────────────────────────────────────

function renderChart(data) {
    loadChartJs(() => {
        const ctx = document.getElementById('btc-chart');
        if (!ctx || !data.chart_data.length) return;
        const labels  = data.chart_data.map(d => d.date);
        const prices  = data.chart_data.map(d => d.price);
        const ma200   = data.chart_data.map(d => d.ma200);
        const minus25 = data.chart_data.map(d => d.minus25);
        const minus50 = data.chart_data.map(d => d.minus50);
        const plus25  = data.chart_data.map(d => d.plus25);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'BTC/USD',     data: prices,  borderColor: '#f7931a', borderWidth: 2,   pointRadius: 0, fill: false, tension: 0.3 },
                    { label: 'MA200W',      data: ma200,   borderColor: '#00ffad', borderWidth: 2,   pointRadius: 0, fill: false, tension: 0.3 },
                    { label: '-25% MA',     data: minus25, borderColor: '#28a745', borderWidth: 1,   pointRadius: 0, fill: false, tension: 0.3, borderDash: [4,4] },
                    { label: '-50% MA',     data: minus50, borderColor: '#006b1b', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.3, borderDash: [2,4] },
                    { label: '+25% MA',     data: plus25,  borderColor: '#ffb800', borderWidth: 1,   pointRadius: 0, fill: false, tension: 0.3, borderDash: [4,4] },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#666', font: { size: 10 }, boxWidth: 12 } },
                    tooltip: { backgroundColor: '#111', borderColor: '#333', borderWidth: 1, titleColor: '#aaa', bodyColor: '#ccc',
                        callbacks: { label: item => item.dataset.label + ': $' + Number(item.parsed.y).toLocaleString('en-US') }
                    }
                },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 8, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: { ticks: { color: '#555', font: { size: 9 }, callback: v => '$' + Number(v).toLocaleString('en-US') }, grid: { color: 'rgba(255,255,255,0.04)' } }
                }
            }
        });
    });
}

function renderBacktestChart(data) {
    loadChartJs(() => {
        const ctx = document.getElementById('backtest-chart');
        if (!ctx || !data.rsu_series.length) return;
        const labels = data.rsu_series.map(d => d.date);
        const rsu    = data.rsu_series.map(d => d.value);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'RSU Score', data: rsu, borderColor: '#00d9ff', backgroundColor: '#00d9ff11', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 },
                    { label: 'Umbral 20', data: labels.map(() => 20), borderColor: '#00ffad', borderWidth: 1, pointRadius: 0, borderDash: [4,4], fill: false },
                    { label: 'Umbral 40', data: labels.map(() => 40), borderColor: '#ffb800', borderWidth: 1, pointRadius: 0, borderDash: [4,4], fill: false },
                    { label: 'Umbral 80', data: labels.map(() => 80), borderColor: '#f23645', borderWidth: 1, pointRadius: 0, borderDash: [4,4], fill: false },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: true, position: 'top', labels: { color: '#666', font: { size: 10 }, boxWidth: 12 } } },
                scales: {
                    x: { ticks: { color: '#555', font: { size: 9 }, maxTicksLimit: 8, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: { min: 0, max: 100, ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
                }
            }
        });
    });
}

function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s   = document.createElement('script');
    s.src     = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload  = cb;
    document.head.appendChild(s);
}

function sourcesBar(sources) {
    if (!sources) return '';
    return '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">'
        + Object.entries(sources).map(([k, v]) =>
            '<span style="font-size:9px;background:rgba(0,217,255,0.08);border:1px solid rgba(0,217,255,0.2);border-radius:3px;padding:1px 6px;color:var(--color-muted);">'
            + k.toUpperCase() + ': ' + v + '</span>'
        ).join('')
        + '</div>';
}
// ── HELPERS ───────────────────────────────────────────────────────────────────

function hashrateSection(data) {
    const h = data.hash_data;
    const p = data.puell_data;
    if (!h && !p) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">DATOS ON-CHAIN · MINERÍA</div>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'
        + (h ? macroCard('HASHRATE', h.hashrate_ehs + ' EH/s', 'Media 30d: ' + h.avg30_ehs + ' EH/s · ' + h.trend, h.trend === 'SUBIENDO' ? 'var(--color-accent)' : '#f23645') : '')
        + (p && p.puell ? macroCard('PUELL MULTIPLE', p.puell, 'Ingresos mineros: $' + p.daily_revenue + 'M · Media 365d: $' + p.sma365_revenue + 'M', p.puell < 0.5 ? 'var(--color-accent)' : p.puell < 1 ? '#ffb800' : '#f23645') : '')
        + (p ? macroCard('FUENTE PUELL', p.source || 'N/A', 'Datos reales de ingresos de mineros', 'var(--color-muted)') : '')
        + '</div>'
        + '</div>';
}

function loading(msg) {
    return '<div style="padding:2rem;color:var(--color-muted);font-size:12px;text-align:center;">'
        + '<div style="font-size:24px;margin-bottom:8px;">₿</div>'
        + msg
        + '</div>';
}