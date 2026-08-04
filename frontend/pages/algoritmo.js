import { tt } from '/components/tooltip.js';
import { errorMessage, esc, fmtFecha } from '/core/ui.js';

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
            + '<div style="color:var(--color-muted);font-size:12px;margin-top:4px;">' + data.score + ' / ' + (data.max_score || 100) + '</div>'
            + '</div>';

        // Los cinco factores se AGRUPAN en tres bloques. El cálculo no cambia
        // ni un punto: es solo cómo se presenta.
        //
        // El porqué (medido el 31/07/2026 sobre 4.673 sesiones): los inputs de
        // RSI, VIX y EMA200W son casi la misma información — VIX vs distancia
        // a la EMA200W r=0,67, RSI vs VIX r=0,51. Mostrarlos como tres barras
        // separadas da una falsa sensación de confirmación múltiple: el
        // usuario ve tres cosas coincidir y cree que son tres señales
        // independientes, cuando es una repetida. Agrupadas bajo "¿ha caído de
        // verdad?" se lee lo que son.
        //
        // Se probó FUSIONARLAS también en el cálculo y salió peor — ver la
        // explicación larga en rsu_algoritmo_service.py. Aquí se agrupa solo
        // de cara al usuario.
        const BLOQUES = [
            { titulo: '¿Ha caído de verdad?',      claves: ['RSI', 'VIX', 'EMA200W'],
              nota: 'sobreventa, miedo y distancia a la media de largo plazo' },
            { titulo: '¿Ha habido capitulación?',  claves: ['Volume'],
              nota: 'volumen de pánico en el día del mínimo' },
            { titulo: '¿Participa todo el mercado?', claves: ['Breadth'],
              nota: 'amplitud: cuántas acciones acompañan, no solo el índice' },
        ];

        const barra = (key, m) => {
            const pct = m.max > 0 ? Math.round(m.score / m.max * 100) : 0;
            const etiqueta = key === 'Breadth' && m.metodo ? key + ' — ' + m.metodo : key;
            return '<div style="margin-bottom:8px;">'
                + '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">'
                + '<span style="color:var(--color-muted);">' + etiqueta + '</span>'
                + '<span style="color:' + m.color + ';font-weight:500;">' + m.score + ' / ' + m.max + '</span>'
                + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:3px;height:6px;">'
                + '<div style="height:100%;width:' + pct + '%;background:' + m.color + ';border-radius:3px;transition:width 0.8s;"></div>'
                + '</div>'
                + '</div>';
        };

        const factores = BLOQUES.map(b => {
            const presentes = b.claves.filter(k => data.metricas[k]);
            if (!presentes.length) return '';
            const suma = presentes.reduce((a, k) => a + (data.metricas[k].score || 0), 0);
            const tope = presentes.reduce((a, k) => a + (data.metricas[k].max || 0), 0);
            return '<div style="margin-bottom:14px;">'
                + '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;">'
                + '<span style="color:var(--color-text);font-size:12px;font-weight:500;">' + b.titulo + '</span>'
                + '<span style="color:var(--color-muted);font-size:12px;">' + suma + ' / ' + tope + '</span>'
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:6px;">' + b.nota + '</div>'
                + presentes.map(k => barra(k, data.metricas[k])).join('')
                + '</div>';
        }).join('')
        // La SMA200 va aparte y al final: no puntúa, solo decide el umbral.
        + (data.metricas['SMA200']
            ? '<div style="border-top:1px solid var(--color-border);padding-top:10px;">'
              + barra('SMA200 (umbral, no puntúa)', data.metricas['SMA200'])
              + '</div>'
            : '');

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
        const emaMetrica = (data.metricas || {})['EMA200W'] || {};
        const emaDist    = emaMetrica.distancia_pct;
        const emaMargen  = emaMetrica.margen_suelo == null ? 10 : emaMetrica.margen_suelo;
        const abiColor = data.abi_estado === 'ALTA DISPERSIÓN' ? '#ff9800' : 'var(--color-muted)';
        const abiTxt   = data.abi_valor == null ? 'ABI: sin datos (requiere scan nocturno)' : 'ABI: ' + data.abi_valor + '% (' + data.abi_estado + ')';
        const gatekeepersHtml = '<div style="margin-top:1rem;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border:1px solid var(--color-border);">'
            + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;margin-bottom:8px;">LA PUERTA ' + tt('algoritmo-gatekeepers') + ' (para VERDE hacen falta ' + data.umbral_verde + '/' + (data.max_score || 100) + ')</div>'
            + '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:12px;">'
            // Se dice la distancia real, no un "cerca" a secas: la condición es
            // asimétrica (≤ +10% sobre la media de 200 semanas, sin límite por
            // abajo) y antes la etiqueta afirmaba "cerca" estando un +24% por
            // encima, que es justo lo contrario de una zona de suelo.
            + '<div style="color:' + gkColor(data.gatekeeper_a) + ';">' + gkIcon(data.gatekeeper_a) + ' Vuelta a la media de 200 semanas'
            + (emaDist == null ? '' : ' <span style="color:var(--color-muted);">(' + (emaDist >= 0 ? '+' : '') + emaDist + '%, exige ≤ +' + emaMargen + '%)</span>')
            + '</div>'
            // El RVOL extremo ya NO valida una señal (31/07/2026): las que
            // entraban solo por él rendían +3,49% a 60d frente a +12,90% de
            // las validadas por la vuelta a la media. Se sigue mostrando
            // porque es información útil, pero en gris y marcado como
            // contexto, para no dar a entender que abre la puerta.
            + '<div style="color:var(--color-muted);">' + gkIcon(data.gatekeeper_b) + ' RVOL extremo en el mínimo <span style="font-size:10px;">(contexto, ya no valida)</span></div>'
            + '<div style="color:' + gkColor(data.ftd_confirmado) + ';">' + gkIcon(data.ftd_confirmado) + ' FTD confirmado</div>'
            + '<div style="color:var(--color-muted);">Drawdown 52w: <span style="color:' + (data.drawdown_52w_pct <= -15 ? '#f23645' : 'var(--color-text)') + ';">' + data.drawdown_52w_pct + '%</span></div>'
            + '<div style="color:' + creditColor + ';">' + creditTxt + '</div>'
            // tt() devuelve HTML (un <span> con comillas dentro), así que NO puede ir
            // dentro de un atributo: la primera comilla cerraba el title= y el resto
            // se derramaba a la página como texto ('?">ABI: 38.8%'). Va fuera, como
            // el icono ? del resto de la terminal.
            + '<div style="color:' + abiColor + ';" title="Contexto — no puntúa en el score">' + abiTxt + ' ' + tt('abi-absolute-breadth') + '</div>'
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
            // Los cinco factores suman 100 exactos desde el 31/07/2026, así
            // que el score SE LEE COMO UN PORCENTAJE directo. Se sigue usando
            // data.max_score en vez de un 100 a fuego: si algún día vuelven a
            // cambiar los pesos, la pantalla no miente sola.
            + '<span style="color:' + data.color + ';font-size:56px;font-weight:500;line-height:1;">' + data.score + '</span>'
            + '<span style="color:var(--color-muted);font-size:18px;">/' + (data.max_score || 100) + '</span>'
            // El semáforo OFICIAL (el que avisa por Telegram y entra en el
            // track record) se decide una vez al día, con los cierres. Lo que
            // se ve aquí durante la sesión es un cálculo en curso, y hay que
            // decirlo: antes cambiaba de color intradía y el usuario recibía
            // tres avisos en un día por puro ruido.
            + (data.provisional
                ? '<span style="color:var(--color-muted);font-size:11px;margin-left:auto;" title="El estado oficial se fija con el cierre de Nueva York. Este cálculo se actualiza durante la sesión y puede variar.">· en curso, se fija al cierre</span>'
                : '')
            + '</div>'
            + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:8px;margin-bottom:1rem;">'
            + '<div style="height:100%;width:' + Math.min(100, data.score / (data.max_score || 100) * 100) + '%;background:' + data.color + ';border-radius:4px;transition:width 1s;"></div>'
            + '</div>'
            + '<div style="color:' + data.color + ';font-size:18px;letter-spacing:0.15em;margin-bottom:0.75rem;font-weight:500;">' + data.senal + '</div>'
            + '<div style="color:var(--color-text);font-size:13px;line-height:1.7;padding:1rem;background:var(--color-bg,#0a0a0a);border-radius:var(--radius);border-left:3px solid ' + data.color + ';">'
            + data.recomendacion
            + '</div>'
            + advertenciasHtml
            + gatekeepersHtml
            + '</div>'
            + '</div>'

            // El puente "cuándo -> qué". Se rellena aparte (loadCandidatos)
            // para que un fallo del scan de RS/RW no retrase ni rompa el
            // semáforo, que es lo principal de esta página.
            + '<div id="algo-candidatos" style="margin-bottom:1rem;"></div>'

            // Fila 2: factores + detalles + medias
            + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">CÓMO SE FORMA EL SCORE ' + tt('algoritmo-bloques') + '</div>'
            + factores
            + '</div>'

            + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">QUÉ ESTÁ PASANDO HOY, PUNTO POR PUNTO</div>'
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
            // "máximo" y no "20 años" a secas: la EMA200 semanal necesita 15
            // años de buffer previo para converger, y SPY solo cotiza desde
            // 1993 — así que lo evaluable arranca en 2008. El periodo real se
            // imprime debajo del resultado, esto solo evita prometer de más.
            + '<option value="20">Máximo (desde 2008, incluye la Gran Crisis)</option>'
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

        loadCandidatos(container, isGreen);

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
        // Si la caché del backtest está fría, el cálculo tarda minutos y el
        // proxy corta antes, devolviendo una página HTML de error. Hacer
        // res.json() sobre eso soltaba "Unexpected token '<'", que no le dice
        // nada a nadie. Se detecta y se explica qué está pasando y qué hacer.
        const tipo = res.headers.get('content-type') || '';
        if (!res.ok || !tipo.includes('application/json')) {
            throw new Error(
                res.status === 504 || res.status === 502
                    ? 'El backtest está tardando más de lo que permite el servidor. Se está calculando en segundo plano — espera un minuto y vuelve a pulsar RECALCULAR.'
                    : 'El servidor respondió ' + res.status + ' sin datos utilizables. Si se repite, revisa los logs del backend.'
            );
        }
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

    // DOS ventajas por horizonte, no una. La de siempre compara contra un día
    // cualquiera de SPY; la nueva, contra días de pánico comparables (VIX>25).
    // La segunda es la honesta: este algoritmo no se dispara un día
    // cualquiera, y el pánico ya rebota solo. Enseñar solo la primera infla el
    // mérito del sistema — medido, más de la mitad de la ventaja se evapora.
    const pp = v => (v > 0 ? '+' : '') + v + ' pp';
    const statsRows = horizontes.map(h => {
        const s = data.stats[h.key];
        if (!s) return '';
        const cFacil = s.ventaja_pp > 0 ? 'var(--color-text)' : '#f23645';
        const tieneDura = s.ventaja_panico_pp != null;
        const cDura = !tieneDura ? 'var(--color-muted)'
                    : s.ventaja_panico_pp > 0 ? 'var(--color-accent)' : '#f23645';
        return '<div style="display:grid;grid-template-columns:70px 1fr 1fr 1fr 1fr;gap:10px;padding:10px 0;border-bottom:1px solid var(--color-border);align-items:center;font-size:12px;">'
            + '<div style="color:var(--color-text);font-weight:500;">' + h.label + '</div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Señal: </span><span style="color:' + (s.retorno_medio_senal >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (s.retorno_medio_senal >= 0 ? '+' : '') + s.retorno_medio_senal + '%</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">vs día normal: </span><span style="color:' + cFacil + ';">' + pp(s.ventaja_pp) + '</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">vs día de pánico: </span><span style="color:' + cDura + ';font-weight:600;">' + (tieneDura ? pp(s.ventaja_panico_pp) : 'sin datos') + '</span></div>'
            + '<div><span style="color:var(--color-muted);font-size:10px;">Aciertos: </span><span style="color:var(--color-text);">' + s.tasa_exito_pct + '% de ' + s.n_senales + '</span></div>'
            + '</div>';
    }).join('')
    + '<div style="color:var(--color-muted);font-size:10px;line-height:1.6;margin-top:8px;">'
    + '<b style="color:var(--color-text);">Cómo leer esto.</b> "vs día normal" compara las señales contra comprar en un día cualquiera. '
    + 'Es la cifra bonita, y engaña: el algoritmo solo se dispara cuando hay miedo, y el miedo ya rebota por sí solo. '
    + '"vs día de pánico" compara contra días parecidos (VIX &gt; 25) — eso es lo que aporta el sistema de verdad. '
    + 'Con pocas señales, un porcentaje de aciertos alto no es una promesa: mira siempre cuántas son.'
    + '</div>';

    const senalesHtml = data.senales.length === 0
        ? '<div style="color:var(--color-muted);font-size:12px;padding:1rem 0;">No se detectaron señales VERDE en el periodo analizado — el nuevo sistema con gatekeepers obligatorios es considerablemente más selectivo que la versión anterior.</div>'
        : '<div style="max-height:340px;overflow-y:auto;margin-top:0.5rem;">'
          + '<div style="display:grid;grid-template-columns:80px 50px 74px 66px 74px 62px 44px 44px 44px 44px;gap:6px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:9px;color:var(--color-muted);position:sticky;top:0;background:var(--color-surface);">'
          + '<div>FECHA</div><div>SCORE</div>'
          + '<div title="Distancia del precio a su media de 200 semanas el día de la señal. Es la condición obligatoria del sistema: para que haya señal tiene que estar por debajo de +10%. Por debajo de 0% el precio ya cotiza bajo su media de cuatro años.">VS MEDIA 200S</div>'
          + '<div title="Cuánto había caído ya el índice desde su máximo de las últimas 52 semanas cuando saltó la señal — el tamaño del susto previo.">DESDE MÁX</div>'
          + '<div title="Lo peor que llegó a estar la posición DESPUÉS de entrar, en cualquier momento de los 60 días, usando los mínimos intradía.">LLEGÓ A CAER</div>'
          + '<div title="✓FTD = en el momento de la señal ya había un día de subida fuerte con volumen (dinero institucional moviéndose). ⚠BAA = el spread de crédito estaba elevado, aunque mejorando.">CONTEXTO</div>'
          + '<div>+5d</div><div>+10d</div><div>+20d</div><div>+60d</div>'
          + '</div>'
          + data.senales.map(s => {
              const r = s.retornos;
              const fmt = v => v == null ? '<span style="color:#555;">—</span>' : '<span style="color:' + (v >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (v >= 0 ? '+' : '') + v + '%</span>';
              // "VS MEDIA 200S" es la condición obligatoria del sistema,
              // pero se etiqueta por lo que MIDE y no por el papel que juega:
              // un encabezado "PUERTA" obliga a saberse la jerga del módulo
              // para entender qué es ese número. Y como booleano no valdría
              // (sería ✓ en las 16 filas, sin señal no hay puerta abierta),
              // se muestra la distancia, que sí tiene recorrido real: de
              // −20,5% (jun-2009) a +9,3% (abr-2025).
              //
              // ✓FTD y ⚠BAA van en su propia columna CONTEXTO. Antes se
              // pegaban dentro de la celda de LLEGÓ A CAER, así que esa
              // celda mezclaba un porcentaje de caída con dos etiquetas que
              // no tienen nada que ver con él.
              const caida = (s.peor_caida || {}).d60;
              const dist  = s.dist_ema200w;
              const ftdTag = s.ftd_confirmado ? ' <span style="color:var(--color-accent);" title="FTD confirmado">✓FTD</span>' : '';
              const creditTag = s.credit_spread_nivel === 'elevado'
                  ? ' <span style="color:#ff9800;" title="BAA10Y ' + s.credit_spread_valor + '% — elevado pero mejorando en el momento de la señal (si hubiera estado empeorando, se habría filtrado igual que crítico)">⚠BAA</span>'
                  : '';
              const contexto = (ftdTag + creditTag).trim() || '<span style="color:#555;">—</span>';
              return '<div style="display:grid;grid-template-columns:80px 50px 74px 66px 74px 62px 44px 44px 44px 44px;gap:6px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:10px;align-items:center;">'
                  + '<div style="color:var(--color-text);">' + esc(fmtFecha(s.fecha)) + '</div>'
                  + '<div style="color:var(--color-muted);">' + s.score + '/' + (data.max_score || 100) + '</div>'
                  + '<div style="color:var(--color-accent);" title="El precio estaba a ' + (dist != null ? dist + '%' : '?') + ' de su media de 200 semanas — la condición obligatoria pide menos de +10%">' + (dist != null ? (dist >= 0 ? '+' : '') + dist + '%' : '—') + '</div>'
                  + '<div style="color:' + (s.drawdown_pct <= -15 ? '#f23645' : 'var(--color-muted)') + ';">' + s.drawdown_pct + '%</div>'
                  + '<div style="color:' + (caida != null && caida <= -10 ? '#f23645' : 'var(--color-muted)') + ';">' + (caida != null ? caida + '%' : '—') + '</div>'
                  + '<div>' + contexto + '</div>'
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
            // La EMA200W sale SIEMPRE sin variación desde que es condición
            // obligatoria (31/07/2026): todas las señales la tienen al máximo,
            // así que no hay dos grupos que comparar. Eso no es un fallo de
            // datos y el mensaje genérico de "sin variación" lo parecía.
            const fiableTag = d.sin_variacion
                ? (factor === 'EMA200W'
                    ? ' <span style="color:#666;font-size:9px;" title="Es la condición obligatoria para dar VERDE, así que todas las señales la cumplen al máximo. Sin dos grupos distintos no hay correlación que calcular — no es un fallo de datos.">— obligatoria, siempre al máximo</span>'
                    : ' <span style="color:#666;font-size:9px;" title="El factor tuvo el mismo valor en todas las señales de la muestra — no hay nada que comparar">— sin variación</span>')
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
        + (data.mcclellan_metodo
            ? '<div style="color:var(--color-muted);margin-top:4px;">McClellan/Breadth en este backtest: ' + data.mcclellan_metodo + ' — aproximación de amplitud sectorial (9 ETFs), no de las ~500 acciones individuales del S&P 500.</div>'
            : '')
        + '</div>'

        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.05em;margin-bottom:6px;">QUÉ APORTA LA SEÑAL ' + tt('algoritmo-baseline') + '</div>'
        + '<div style="display:grid;grid-template-columns:70px 1fr 1fr 1fr 1fr;gap:10px;padding:6px 0;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>PLAZO</div><div>RETORNO SEÑAL</div><div>VS DÍA NORMAL</div><div>VS DÍA DE PÁNICO</div><div>ACIERTOS</div>'
        + '</div>'
        + statsRows

        + '<div style="margin-top:1rem;color:var(--color-muted);font-size:11px;letter-spacing:0.05em;">HISTORIAL DE SEÑALES <span style="font-weight:normal;text-transform:none;letter-spacing:0;">(VS MEDIA 200S = la condición obligatoria: dónde estaba el precio respecto a su media de 200 semanas · DESDE MÁX = lo que ya había caído el índice antes de entrar · LLEGÓ A CAER = lo peor que se puso la posición después de entrar · pasa el ratón por cada cabecera para el detalle)</span></div>'
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

// ── El puente "cuándo → qué" ──────────────────────────────────────────────────
// El semáforo dice cuándo empezar a construir, pero no en qué. Esta caja lo
// cierra con los valores que mejor aguantaron la caída, del scan nocturno de
// RS/RW — no calcula nada nuevo.
//
// Se muestra SIEMPRE, no solo en VERDE: en ámbar aparece en gris con el aviso
// de que todavía no toca. Verlos antes es justo lo que permite tener la
// decisión tomada cuando llegue el momento, que es para lo que sirve la fase
// de watchlist.
async function loadCandidatos(container, enVerde) {
    const caja = container.querySelector('#algo-candidatos');
    if (!caja) return;
    try {
        const token = sessionStorage.getItem('rsu_token');
        const res  = await fetch('/api/v1/algoritmo/candidatos', {
            headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        if (!res.ok) return;
        const data = await res.json();
        if (!data.ok || !data.candidatos || !data.candidatos.length) return;

        const borde  = enVerde ? 'var(--color-accent)' : 'var(--color-border)';
        const titulo = enVerde
            ? 'EN QUÉ EMPEZAR A CONSTRUIR'
            : 'EN QUÉ MIRARÍAS SI SE PUSIERA VERDE';
        const bajada = enVerde
            ? 'El semáforo está en verde. Estos son los valores que mejor aguantaron la caída y ya están recuperando fuerza.'
            : 'Todavía NO es momento de entrar. Esta lista está aquí para que tengas la decisión tomada cuando llegue.';

        // Mismo patrón de ticker que Scanner, RS/RW e Insider: clase
        // ticker-link (cursor, hover y subrayado del tema) + goToResearch,
        // que navega por el router del SPA en vez de recargar la página.
        const filas = data.candidatos.map(c =>
            '<div style="display:grid;grid-template-columns:80px 1fr;gap:12px;padding:9px 0;border-bottom:1px solid var(--color-border);align-items:baseline;">'
            + '<div onclick="goToResearch(\'' + esc(c.ticker) + '\')" class="ticker-link" style="color:var(--color-accent);font-weight:500;">' + esc(c.ticker) + '</div>'
            + '<span style="color:var(--color-muted);font-size:12px;">' + esc(c.porque)
            + '<span style="opacity:0.6;"> · ' + esc(c.sector) + '</span></span>'
            + '</div>'
        ).join('');

        caja.innerHTML = '<div style="background:var(--color-surface);border:1px solid ' + borde + ';border-radius:var(--radius);padding:1.25rem;">'
            + '<div style="color:' + (enVerde ? 'var(--color-accent)' : 'var(--color-muted)') + ';font-size:12px;letter-spacing:0.08em;margin-bottom:4px;">' + titulo + ' ' + tt('algoritmo-candidatos') + '</div>'
            + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:10px;">' + bajada + '</div>'
            + filas
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:10px;">' + esc(data.criterio) + ' · ' + esc(data.fuente) + '. Pulsa cualquiera para abrir su análisis.</div>'
            + '</div>';
    } catch (e) {
        // Silencioso a propósito: es un añadido, no debe ensuciar la página
        // principal si el Gist de RS/RW no responde.
    }
}
