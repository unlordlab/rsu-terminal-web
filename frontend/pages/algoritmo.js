import { tt } from '/components/tooltip.js';
import { errorMessage } from '/core/ui.js';

export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ALGORITMO ' + tt('rsu-algoritmo') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Detector de fondos · Multi-factor V2.1 · SPY</div>'
        + '</div>'
        + '<div id="algo-content"><div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div></div>';

    const el    = container.querySelector('#algo-content');
    const token = sessionStorage.getItem('rsu_token');

    try {
        const res  = await fetch('/api/v1/algoritmo/', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        const chartId = 'algo-full-chart-' + Date.now();
        const isGreen = data.estado.startsWith('VERDE');
        const isAmbar = data.estado.startsWith('AMBAR');
        const isRed   = data.estado === 'ROJO';

        function luz(cls, on) {
            const cfg = {
                red: ['#ff6b6b,#f23645', '#f23645', '#f2364566'],
                yel: ['#ffb74d,#ff9800', '#ff9800', '#ff980066'],
                grn: ['#69f0ae,#00ffad', '#00ffad', '#00ffad66'],
            }[cls];
            return '<div style="width:80px;height:80px;border-radius:50%;margin:8px auto;transition:all 0.4s;'
                + 'border:4px solid ' + (on ? cfg[1] : 'var(--color-border)') + ';'
                + 'background:' + (on ? 'radial-gradient(circle at 30% 30%,' + cfg[0] + ')' : 'var(--color-bg,#0a0a0a)') + ';'
                + (on ? 'box-shadow:0 0 30px ' + cfg[2] + ';transform:scale(1.1);' : '')
                + '"></div>';
        }

        const semaforo = '<div style="text-align:center;padding:1.5rem 1rem;">'
            + luz('red', isRed)
            + luz('yel', isAmbar)
            + luz('grn', isGreen)
            + '<div style="color:' + data.color + ';font-size:16px;letter-spacing:0.12em;margin-top:12px;font-weight:500;">' + data.estado + '</div>'
            + '<div style="color:var(--color-muted);font-size:12px;margin-top:4px;">' + data.score + ' / 100</div>'
            + '</div>';

        const factores = Object.entries(data.metricas)
            .filter(([k]) => k !== 'FTD') // FTD ya no aporta score, se muestra aparte como confirmación
            .map(([key, m]) => {
                const pct = m.max > 0 ? Math.round(m.score / m.max * 100) : 0;
                // SMA200 ya no suma al score total (solo decide el umbral de VERDE, 60/70) —
                // se muestra igual como contexto, pero con la etiqueta clara para no dar a
                // entender que puntúa como el resto.
                const etiqueta = key === 'SMA200' ? key + ' (umbral, no puntúa)' : key;
                return '<div style="margin-bottom:10px;">'
                    + '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">'
                    + '<span style="color:var(--color-muted);">' + etiqueta + '</span>'
                    + '<span style="color:' + m.color + ';font-weight:500;">' + m.score + ' / ' + m.max + '</span>'
                    + '</div>'
                    + '<div style="background:var(--color-bg,#0a0a0a);border-radius:3px;height:6px;">'
                    + '<div style="height:100%;width:' + pct + '%;background:' + m.color + ';border-radius:3px;transition:width 0.8s;"></div>'
                    + '</div>'
                    + '</div>';
            }).join('');

        const detallesHtml = data.detalles.map(d => {
            const c = d.startsWith('✓') ? 'var(--color-accent)' : d.startsWith('~') ? '#ffb800' : d.startsWith('✗') ? '#f23645' : 'var(--color-muted)';
            return '<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;color:' + c + ';">' + d + '</div>';
        }).join('');

        const advertenciasHtml = data.advertencias.length > 0
            ? '<div style="margin-top:1rem;padding:1rem;background:rgba(255,184,0,0.05);border:1px solid rgba(255,184,0,0.2);border-radius:var(--radius);">'
              + '<div style="color:#ffb800;font-size:11px;letter-spacing:0.08em;margin-bottom:8px;">ADVERTENCIAS</div>'
              + data.advertencias.map(a => '<div style="color:#ffb800;font-size:12px;padding:3px 0;">' + a + '</div>').join('')
              + '</div>'
            : '';

        const gkColor = (ok) => ok ? 'var(--color-accent)' : 'var(--color-muted)';
        const gkIcon  = (ok) => ok ? '✓' : '○';
        const creditColor = data.credit_spread_nivel === 'critico' ? '#f23645' : data.credit_spread_nivel === 'elevado' ? '#ff9800' : 'var(--color-muted)';
        const creditTxt   = data.credit_spread_valor == null
            ? 'BAA10Y: sin datos'
            : 'BAA10Y: ' + data.credit_spread_valor + '% (' + (data.credit_spread_nivel === 'critico' ? 'CRÍTICO' : data.credit_spread_nivel === 'elevado' ? ('elevado, ' + (data.credit_spread_empeorando ? 'empeorando' : 'mejorando')) : 'normal') + ')';
        const gatekeepersHtml = '<div style="margin-top:1rem;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border:1px solid var(--color-border);">'
            + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;margin-bottom:8px;">GATEKEEPERS ' + tt('algoritmo-gatekeepers') + ' (umbral VERDE: ' + data.umbral_verde + '/100)</div>'
            + '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:12px;">'
            + '<div style="color:' + gkColor(data.gatekeeper_a) + ';">' + gkIcon(data.gatekeeper_a) + ' Cerca de EMA200 semanal</div>'
            + '<div style="color:' + gkColor(data.gatekeeper_b) + ';">' + gkIcon(data.gatekeeper_b) + ' RVOL extremo en el mínimo</div>'
            + '<div style="color:' + gkColor(data.ftd_confirmado) + ';">' + gkIcon(data.ftd_confirmado) + ' FTD confirmado</div>'
            + '<div style="color:var(--color-muted);">Drawdown 52w: <span style="color:' + (data.drawdown_52w_pct <= -15 ? '#f23645' : 'var(--color-text)') + ';">' + data.drawdown_52w_pct + '%</span></div>'
            + '<div style="color:' + creditColor + ';">' + creditTxt + '</div>'
            + '</div>'
            + '</div>';

        const mediasHtml = Object.entries(data.medias).map(([k, v]) =>
            '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;">'
            + '<span style="color:var(--color-muted);">' + k.toUpperCase() + '</span>'
            + '<span style="color:var(--color-text);">$' + v.toLocaleString('en-US') + '</span>'
            + '</div>'
        ).join('');

        el.innerHTML =
            // Fila 1: semáforo + score + recomendación
            '<div style="display:grid;grid-template-columns:200px 1fr;gap:1rem;margin-bottom:1rem;">'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);">'
            + semaforo
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;">'
            + '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:0.75rem;">'
            + '<span style="color:' + data.color + ';font-size:56px;font-weight:500;line-height:1;">' + data.score + '</span>'
            + '<span style="color:var(--color-muted);font-size:18px;">/100</span>'
            + '</div>'
            + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:8px;margin-bottom:1rem;">'
            + '<div style="height:100%;width:' + data.score + '%;background:' + data.color + ';border-radius:4px;transition:width 1s;"></div>'
            + '</div>'
            + '<div style="color:' + data.color + ';font-size:18px;letter-spacing:0.15em;margin-bottom:0.75rem;font-weight:500;">' + data.senal + '</div>'
            + '<div style="color:var(--color-text);font-size:13px;line-height:1.7;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border-left:3px solid ' + data.color + ';">'
            + data.recomendacion
            + '</div>'
            + advertenciasHtml
            + gatekeepersHtml
            + '</div>'
            + '</div>'

            // Fila 2: factores + detalles + medias
            + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">FACTORES · SCORES</div>'
            + factores
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">ANÁLISIS DE CONDICIONES</div>'
            + detallesHtml
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">MEDIAS MÓVILES · SPY</div>'
            + mediasHtml
            + '</div>'

            + '</div>'

            // Fila 3: chart completo
            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">SPY · HISTÓRICO 60 DÍAS</div>'
            + '<div style="position:relative;height:200px;">'
            + '<canvas id="' + chartId + '"></canvas>'
            + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:8px;text-align:right;">Actualizado: ' + data.timestamp + ' · Ventana de condiciones: 10 días</div>'
            + '</div>'

            // Fila 4: backtest
            + '<div id="backtest-section" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-top:1rem;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">BACKTEST · ¿TIENE VENTAJA REAL? ' + tt('algoritmo-backtest') + '</div>'
            + '<div style="display:flex;gap:8px;align-items:center;">'
            + '<select id="backtest-years" style="background:var(--color-bg,#0a0a0a);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:5px 8px;font-family:var(--font-mono);font-size:11px;">'
            + '<option value="10">10 años</option>'
            + '<option value="15">15 años</option>'
            + '<option value="20">20 años (incluye 2008)</option>'
            + '</select>'
            + '<button id="run-backtest-btn" style="background:var(--color-bg,#0a0a0a);color:var(--color-accent);border:1px solid var(--color-accent);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;letter-spacing:0.05em;">EJECUTAR BACKTEST</button>'
            + '</div>'
            + '</div>'
            + '<div id="backtest-content" style="color:var(--color-muted);font-size:12px;">Pulsa el botón para recalcular el algoritmo sobre 10 años de histórico de SPY y comparar contra el rendimiento base del índice. Puede tardar 10-20 segundos.</div>'
            + '</div>'

            // Fila 5: señales reales en vivo (distinto del backtest — se va llenando con el tiempo)
            + '<div id="historial-real-section" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-top:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.5rem;">SEÑALES REALES (EN VIVO) ' + tt('algoritmo-historial-real') + '</div>'
            + '<div id="historial-real-content" style="color:var(--color-muted);font-size:12px;">Cargando...</div>'
            + '</div>';

        renderChart(chartId, data.chart, data.color);

        container.querySelector('#run-backtest-btn').addEventListener('click', () => runBacktest(container));
        loadHistorialReal(container);

    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

async function loadHistorialReal(container) {
    const el    = container.querySelector('#historial-real-content');
    const token = sessionStorage.getItem('rsu_token');
    try {
        const res  = await fetch('/api/v1/algoritmo/historial-real', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        if (!data.cambios_semaforo.length) {
            el.innerHTML = '<div style="padding:0.5rem 0;">Todavía no hay señales registradas — esto se va llenando solo a partir de ahora. '
                + 'A diferencia del backtest (que reanaliza el mismo histórico fijo), estas señales usan datos que no existían cuando se diseñó el algoritmo, así que con el tiempo son la validación más fiable de si de verdad funciona.</div>';
            return;
        }

        const nota = '<div style="font-size:10px;color:var(--color-muted);margin-bottom:0.75rem;">A diferencia del backtest, esto no reanaliza histórico — son señales reales desde que se activó el seguimiento. El retorno se rellena solo cuando pasa el tiempo suficiente (5/10/20/60 días).</div>';

        const cambiosHtml = '<div style="margin-bottom:1rem;">'
            + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:6px;">ÚLTIMOS CAMBIOS DE SEMÁFORO</div>'
            + data.cambios_semaforo.slice(0, 10).map(c => {
                const fecha = new Date(c.fecha).toLocaleString('es-ES', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
                const color = c.estado_nuevo === 'VERDE' ? 'var(--color-accent)' : c.estado_nuevo === 'ROJO' ? '#f23645' : '#ff9800';
                return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                    + '<span style="color:var(--color-muted);">' + fecha + '</span>'
                    + '<span>' + (c.estado_anterior || '(inicio)') + ' → <span style="color:' + color + ';font-weight:500;">' + c.estado_nuevo + '</span></span>'
                    + '</div>';
            }).join('')
            + '</div>';

        let senalesHtml = '';
        if (data.senales.length) {
            const fmtRet = (v) => v == null ? '<span style="color:var(--color-muted);">pendiente</span>' : '<span style="color:' + (v >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (v >= 0 ? '+' : '') + v + '%</span>';
            senalesHtml = '<div>'
                + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-bottom:6px;">SEÑALES ACCIONABLES (VERDE / VERDE-VOL) TRACKEADAS</div>'
                + '<div style="display:grid;grid-template-columns:120px 90px 60px 70px 70px 70px 70px;gap:8px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
                + '<div>FECHA</div><div>ESTADO</div><div>SCORE</div><div>+5D</div><div>+10D</div><div>+20D</div><div>+60D</div>'
                + '</div>'
                + data.senales.map(s => {
                    const fecha = new Date(s.fecha).toLocaleDateString('es-ES', { day:'2-digit', month:'2-digit', year:'numeric' });
                    return '<div style="display:grid;grid-template-columns:120px 90px 60px 70px 70px 70px 70px;gap:8px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                        + '<div>' + fecha + '</div>'
                        + '<div style="color:' + (s.estado === 'VERDE' ? 'var(--color-accent)' : '#ff9800') + ';">' + s.estado + '</div>'
                        + '<div>' + s.score + '</div>'
                        + '<div>' + fmtRet(s.resultado_5d) + '</div>'
                        + '<div>' + fmtRet(s.resultado_10d) + '</div>'
                        + '<div>' + fmtRet(s.resultado_20d) + '</div>'
                        + '<div>' + fmtRet(s.resultado_60d) + '</div>'
                        + '</div>';
                }).join('')
                + '</div>';
        }

        el.innerHTML = nota + cambiosHtml + senalesHtml;
    } catch(e) {
        el.innerHTML = errorMessage(e.message);
    }
}

async function runBacktest(container) {
    const btn     = container.querySelector('#run-backtest-btn');
    const content = container.querySelector('#backtest-content');
    const years   = container.querySelector('#backtest-years')?.value || '10';
    btn.disabled  = true;
    btn.textContent = 'CALCULANDO...';
    content.innerHTML = '<div style="color:var(--color-muted);">Recalculando el algoritmo día a día sobre ' + years + ' años de histórico — esto puede tardar 10-30 segundos...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        const res   = await fetch('/api/v1/algoritmo/backtest?years=' + years, {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data  = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        content.innerHTML = renderBacktestResults(data);

    } catch(e) {
        content.innerHTML = errorMessage(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'RECALCULAR';
    }
}

function renderBacktestResults(data) {
    const horizontes = [
        { key: 'd5',  label: '5 días' },
        { key: 'd10', label: '10 días' },
        { key: 'd20', label: '20 días' },
        { key: 'd60', label: '60 días' },
    ];

    const statsRows = horizontes.map(h => {
        const s = data.stats[h.key];
        if (!s) return '';
        const ventajaColor = s.ventaja_pp > 0 ? 'var(--color-accent)' : '#f23645';
        const ventajaStr   = (s.ventaja_pp > 0 ? '+' : '') + s.ventaja_pp + ' pp';
        return '<div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 1fr;gap:10px;padding:10px 0;border-bottom:1px solid var(--color-border);align-items:center;font-size:12px;">'
            + '<div style="color:var(--color-text);font-weight:500;">' + h.label + '</div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Señal: </span><span style="color:' + (s.retorno_medio_senal >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (s.retorno_medio_senal >= 0 ? '+' : '') + s.retorno_medio_senal + '%</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Baseline SPY: </span><span style="color:var(--color-text);">' + (s.retorno_baseline >= 0 ? '+' : '') + s.retorno_baseline + '%</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Ventaja: </span><span style="color:' + ventajaColor + ';font-weight:600;">' + ventajaStr + '</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Éxito: </span><span style="color:var(--color-text);">' + s.tasa_exito_pct + '% (' + s.n_senales + ')</span></div>'
            + '</div>';
    }).join('');

    const senalesHtml = data.senales.length === 0
        ? '<div style="color:var(--color-muted);font-size:12px;padding:1rem 0;">No se detectaron señales VERDE en el periodo analizado — el nuevo sistema con gatekeepers obligatorios es considerablemente más selectivo que la versión anterior.</div>'
        : '<div style="max-height:340px;overflow-y:auto;margin-top:0.5rem;">'
          + '<div style="display:grid;grid-template-columns:85px 55px 80px 70px 50px 50px 50px 50px;gap:6px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);position:sticky;top:0;background:var(--color-surface);">'
          + '<div>FECHA</div><div>SCORE</div><div>GATEKEEPER</div><div>DRAWDOWN</div><div>+5d</div><div>+10d</div><div>+20d</div><div>+60d</div>'
          + '</div>'
          + data.senales.map(s => {
              const r = s.retornos;
              const fmt = v => v == null ? '<span style="color:#555;">—</span>' : '<span style="color:' + (v >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (v >= 0 ? '+' : '') + v + '%</span>';
              const gk = s.gatekeeper_a ? 'EMA200W' : (s.gatekeeper_b ? 'RVOL' : '—');
              const ftdTag = s.ftd_confirmado ? ' <span style="color:var(--color-accent);" title="FTD confirmado">✓FTD</span>' : '';
              const creditTag = s.credit_spread_nivel === 'elevado'
                  ? ' <span style="color:#ff9800;" title="BAA10Y ' + s.credit_spread_valor + '% — elevado pero mejorando en el momento de la señal (si hubiera estado empeorando, se habría filtrado igual que crítico)">⚠BAA</span>'
                  : '';
              return '<div style="display:grid;grid-template-columns:85px 55px 80px 70px 50px 50px 50px 50px;gap:6px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:10px;align-items:center;">'
                  + '<div style="color:var(--color-text);">' + s.fecha + '</div>'
                  + '<div style="color:var(--color-muted);">' + s.score + '/100</div>'
                  + '<div style="color:var(--color-secondary,#00d9ff);">' + gk + ftdTag + creditTag + '</div>'
                  + '<div style="color:' + (s.drawdown_pct <= -15 ? '#f23645' : 'var(--color-muted)') + ';">' + s.drawdown_pct + '%</div>'
                  + '<div>' + fmt(r.d5) + '</div><div>' + fmt(r.d10) + '</div><div>' + fmt(r.d20) + '</div><div>' + fmt(r.d60) + '</div>'
                  + '</div>';
          }).join('')
          + '</div>';

    const FACTOR_LABELS = {
        RSI: 'RSI (diario+semanal)', VIX: 'VIX + curva VIX/VIX3M', Breadth: 'McClellan',
        Volume: 'RVOL en mínimo', EMA200W: 'EMA200 semanal', SMA200: 'Régimen SMA200',
    };

    let importanciaHtml;
    if (!data.importancia) {
        importanciaHtml = '<div style="margin-top:1rem;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border:1px solid var(--color-border);">'
            + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;margin-bottom:6px;">IMPORTANCIA DE VARIABLES ' + tt('algoritmo-importancia') + '</div>'
            + '<div style="color:var(--color-muted);font-size:11px;">Muestra insuficiente (mínimo 8 señales con retorno calculado) para un análisis con sentido estadístico mínimo. Detectadas: ' + data.n_senales + '.</div>'
            + '</div>';
    } else {
        const filas = Object.entries(data.importancia).map(([factor, d]) => {
            const corr = d.correlacion_d20;
            const corrColor = corr == null ? 'var(--color-muted)' : (corr > 0.3 ? 'var(--color-accent)' : corr < -0.3 ? '#f23645' : '#ffb800');
            const corrWidth = corr == null ? 0 : Math.min(100, Math.abs(corr) * 100);
            const fiableTag = d.sin_variacion
                ? ' <span style="color:#666;font-size:9px;" title="El factor tuvo el mismo valor en todas las señales de la muestra — no hay nada que comparar">— sin variación</span>'
                : d.fiable
                    ? ''
                    : ' <span style="color:#ffb800;font-size:9px;" title="Grupo alto o bajo con menos de 2 señales — comparación no fiable">⚠ muestra pequeña</span>';
            return '<div style="margin-bottom:10px;">'
                + '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">'
                + '<span style="color:var(--color-text);">' + (FACTOR_LABELS[factor] || factor) + fiableTag + '</span>'
                + '<span style="color:' + corrColor + ';font-weight:500;">corr: ' + (corr == null ? 'N/D' : corr) + '</span>'
                + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:3px;height:5px;margin-bottom:4px;">'
                + '<div style="height:100%;width:' + corrWidth + '%;background:' + corrColor + ';border-radius:3px;"></div>'
                + '</div>'
                + '<div style="font-size:10px;color:var(--color-muted);">'
                + 'Score alto (n=' + d.n_alto + '): <span style="color:' + (d.retorno_medio_score_alto >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (d.retorno_medio_score_alto == null ? '—' : (d.retorno_medio_score_alto >= 0 ? '+' : '') + d.retorno_medio_score_alto + '%') + '</span>'
                + ' · Score bajo (n=' + d.n_bajo + '): <span style="color:' + (d.retorno_medio_score_bajo >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (d.retorno_medio_score_bajo == null ? '—' : (d.retorno_medio_score_bajo >= 0 ? '+' : '') + d.retorno_medio_score_bajo + '%') + '</span>'
                + '</div>'
                + '</div>';
        }).join('');

        importanciaHtml = '<div style="margin-top:1rem;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border:1px solid var(--color-border);">'
            + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;margin-bottom:10px;">IMPORTANCIA DE VARIABLES ' + tt('algoritmo-importancia') + ' (retorno a ' + data.horizonte_importancia + 'd)</div>'
            + filas
            + '</div>';
    }

    return '<div style="margin-bottom:1rem;font-size:11px;color:var(--color-muted);">'
        + 'Periodo: ' + data.periodo_inicio + ' → ' + data.periodo_fin + ' (' + data.total_dias + ' días) · '
        + '<span style="color:var(--color-accent);">' + data.n_senales + ' señales VERDE puras</span>'
        + ' <span style="color:var(--color-muted);" title="Señales agrupadas por episodio de mercado (≤15 días de trading entre sí cuentan como el mismo episodio) — medida más honesta de cuántos eventos distintos ha visto el sistema">(≈' + data.n_episodios + ' episodios de mercado independientes)</span>'
        + (data.credit_spread_disponible === false
            ? '<div style="color:#ff9800;margin-top:4px;">⚠ FRED no respondió durante este cálculo — el filtro de estrés de crédito (BAA10Y) NO se aplicó en esta corrida. Pulsa RECALCULAR de nuevo.</div>'
            : (data.credit_spread_cobertura_completa === false
                ? '<div style="color:#ff9800;margin-top:4px;">⚠ El histórico de BAA10Y descargado solo llega hasta ' + data.credit_spread_desde + ' — no cubre todo el periodo del backtest, así que el filtro de crédito no actuó en las fechas anteriores a esa.</div>'
                : ''))
        + '</div>'

        + '<div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 1fr;gap:10px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>HORIZONTE</div><div>RETORNO SEÑAL</div><div>BASELINE SPY</div><div>VENTAJA</div><div>TASA ÉXITO</div>'
        + '</div>'
        + statsRows

        + '<div style="margin-top:1rem;color:var(--color-muted);font-size:11px;letter-spacing:0.05em;">HISTORIAL DE SEÑALES <span style="font-weight:normal;text-transform:none;letter-spacing:0;">(GATEKEEPER = qué condición estructural validó la señal · ✓FTD = confirmación de volumen ya llegada)</span></div>'
        + senalesHtml

        + importanciaHtml;
}

function renderChart(chartId, chart, color) {
    const closes = chart.closes;
    const sorted = [...closes].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.1)];
    const q3 = sorted[Math.floor(sorted.length * 0.9)];
    const filtered = {
        dates:  chart.dates.filter((_, i) => closes[i] >= q1 * 0.8 && closes[i] <= q3 * 1.2),
        closes: closes.filter(v => v >= q1 * 0.8 && v <= q3 * 1.2),
    };

    if (window.Chart) {
        drawChart(chartId, filtered, color);
        return;
    }
    const script  = document.createElement('script');
    script.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    script.onload = () => drawChart(chartId, filtered, color);
    document.head.appendChild(script);
}

function drawChart(chartId, chart, color) {
    const ctx = document.getElementById(chartId);
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: chart.dates,
            datasets: [{
                data:            chart.closes,
                borderColor:     color,
                backgroundColor: color + '18',
                borderWidth:     2,
                pointRadius:     0,
                fill:            true,
                tension:         0.3,
            }]
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#555', font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                y: {
                    ticks: { color: '#555', font: { size: 10 } },
                    grid:  { color: 'rgba(255,255,255,0.04)' },
                    min:   Math.min(...chart.closes) * 0.995,
                    max:   Math.max(...chart.closes) * 1.005,
                }
            }
        }
    });
}