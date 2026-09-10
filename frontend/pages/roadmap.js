export async function render(container) {
    container.innerHTML = pageContent();
}

function pageContent() {
    return header() + revision() + sections() + footer();
}

// ── REVISIÓN: LO QUE PASÓ (Páginas Contenido #9 y #10) ──────────────────────
//
// El texto de abajo es la previsión ORIGINAL y no se toca: una previsión
// retocada después de conocer el resultado deja de valer como previsión.
// Encima va lo que pasó, con cifras y con su fecha. Hasta el 10/09/2026 la
// página seguía hablando en futuro de una primavera que ya había pasado, sin
// decir que la corrección se había producido tal como estaba escrita.
//
// LAS CIFRAS son una FOTO FECHADA, no un dato vivo: cierres diarios de Yahoo
// Finance, medidos el 10/09/2026 con datos hasta el 09/09. Máximo del año
// anterior al suelo → suelo → cierre del 09/09.
//
// CUÁNDO SE ESCRIBIÓ: el 20/12/2025, según su autor (10/09/2026). Es lo que
// da valor al acierto: tres meses y diez días antes del suelo del 30/03. Ojo:
// en ESTE repositorio el texto aparece por primera vez el 12/06/2026, en la
// migración desde la versión anterior de la terminal, así que la fecha es la
// que declara el autor. Si existe una publicación de entonces, enlazarla
// aquí la convertiría en comprobable.
const ESCRITO_EL = '20 de diciembre de 2025';
const REVISION_FECHA = '9 de septiembre de 2026';
const REVISION_INDICES = [
    // [índice, caída, desde, hasta, rebote desde el suelo, en el año]
    ['S&P 500',      '−9,1%',  '27/01', '30/03', '+20,4%', '+11,6%'],
    ['Nasdaq 100',   '−11,8%', '28/01', '30/03', '+28,2%', '+16,5%'],
    ['Russell 2000', '−11,2%', '22/01', '30/03', '+21,0%', '+17,7%'],
];

function revision() {
    const celda = 'padding:6px 10px;border-bottom:1px solid var(--color-border);font-size:12px;';
    const filas = REVISION_INDICES.map(([n, caida, desde, hasta, rebote, anio]) =>
        '<tr><td style="' + celda + 'color:var(--color-text);">' + n + '</td>'
        + '<td style="' + celda + 'color:#f23645;">' + caida + ' <span style="color:var(--color-muted);font-size:11px;">(' + desde + ' → ' + hasta + ')</span></td>'
        + '<td style="' + celda + 'color:var(--color-accent);">' + rebote + '</td>'
        + '<td style="' + celda + 'color:var(--color-muted);">' + anio + '</td></tr>').join('');
    return '<div style="border:1px solid var(--color-accent);background:rgba(0,255,173,0.04);border-radius:var(--radius);padding:1.25rem;margin:1rem 0 2rem;">'
        + '<div style="color:var(--color-accent);font-size:14px;letter-spacing:0.1em;margin-bottom:8px;">🔎 REVISIÓN · SEPTIEMBRE 2026 · LO QUE PASÓ</div>'
        + '<p style="color:var(--color-muted);font-size:13px;margin-bottom:12px;">La previsión es la original, escrita el ' + ESCRITO_EL + ', y se deja tal cual, sin retocar, para poder compararla con lo que ocurrió. Estas son las cifras, con los cierres diarios de Yahoo Finance a ' + REVISION_FECHA + ':</p>'
        + '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-family:var(--font-mono);">'
        + '<tr><th style="' + celda + 'color:var(--color-muted);text-align:left;font-weight:normal;"></th>'
        + '<th style="' + celda + 'color:var(--color-muted);text-align:left;font-weight:normal;">CORRECCIÓN</th>'
        + '<th style="' + celda + 'color:var(--color-muted);text-align:left;font-weight:normal;">REBOTE DESDE EL SUELO</th>'
        + '<th style="' + celda + 'color:var(--color-muted);text-align:left;font-weight:normal;">EN EL AÑO</th></tr>'
        + filas + '</table></div>'
        + list([
            '<b style="color:var(--color-accent)">✅ La corrección del 8% al 15%:</b> se produjo, entre el 9% y el 12% en los tres índices.',
            '<b style="color:var(--color-accent)">✅ El rebote fuerte y la recuperación en la segunda mitad:</b> entre un 20% y un 28% desde el suelo.',
            '<b style="color:#ffb800">◐ El calendario:</b> el máximo llegó a finales de enero y el suelo el 30 de marzo, justo al empezar la primavera. La caída se adelantó unas semanas, y el «inicio constructivo de enero–febrero» duró solo enero.',
        ])
        + '<p style="color:var(--color-muted);font-size:11px;margin-top:10px;">Puedes comprobarlas en el histórico de <a href="https://finance.yahoo.com/quote/%5EGSPC/history/" target="_blank" rel="noopener noreferrer" style="color:var(--color-accent);">S&amp;P 500 en Yahoo Finance</a> (y del mismo modo con ^NDX y ^RUT).</p>'
        + '</div>';
}

// El descargo DONDE SE LEE LA PREVISIÓN (Páginas Contenido #10): la página da
// cifras y fases concretas de mercado, y el descargo vivía en otra página sin
// ningún enlace desde aquí.
function avisoLegal() {
    return '<div style="color:var(--color-muted);font-size:11px;text-align:center;margin:0.5rem 0 1rem;">'
        + 'Escenario personal, no recomendación de inversión — '
        + '<span onclick="window.__navigate(\'/disclaimer\')" style="color:var(--color-accent);cursor:pointer;text-decoration:underline;">ver descargo completo</span>'
        + '</div>';
}

function header() {
    return '<div style="margin-bottom:2rem;text-align:center;">'
        // Ver el mismo cambio en manifest.js: la línea anterior afirmaba
        // "ENCRYPTION: AES-256" en un sitio que se sirve por HTTP sin TLS.
        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.15em;margin-bottom:8px;">[TRANSMISIÓN RECIBIDA // CANAL ABIERTO]</div>'
        + '<div style="color:var(--color-accent);font-size:24px;letter-spacing:0.12em;text-shadow:var(--glow-text);margin-bottom:6px;">🗺️ 2026 ROADMAP</div>'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.2em;">PROTOCOLO DE NAVEGACIÓN ESTRATÉGICA // CICLO 2026</div>'
        + '</div>'
        + avisoLegal()
        + '<div style="color:var(--color-muted);font-size:11px;text-align:center;margin-bottom:0.5rem;">📅 Texto original escrito el ' + ESCRITO_EL + ' · revisado en septiembre de 2026</div>'

        + box('default',
            'Cuando pienso en 2026 no veo un año lineal. No veo una tendencia limpia ni un mercado que simplemente continúe lo iniciado en 2025. Lo que visualizo es un año con <b style="color:var(--color-accent)">fases muy definidas</b>, con tensión política creciente, con volatilidad cíclica marcada y, sobre todo, con una <b style="color:var(--color-accent)">ventana táctica extremadamente importante en primavera</b>.'
            + '<p style="margin-top:10px;color:var(--color-muted);">Mi escenario base no es euforia constante ni colapso estructural. Es algo mucho más interesante: <b style="color:var(--color-accent)">un año de correcciones estratégicas dentro de una estructura macro todavía funcional</b>.</p>'
        )
        + divider();
}

function sections() {
    return [
        section('01 // EL CONTEXTO: AÑO DE MIDTERMS',
            '<p style="color:var(--color-muted);">2026 es un año de elecciones intermedias en EE.UU., y eso importa mucho más de lo que el inversor promedio cree.</p>'
            + '<p style="color:var(--color-muted);margin-bottom:10px;">Históricamente, los años de midterms tienden a tener:</p>'
            + list(['Volatilidad superior a la media','Correcciones significativas en la primera mitad del año','Recuperaciones importantes hacia la segunda mitad','Un cierre de año generalmente constructivo'])
            + quote('"El mercado no es solo descuento de flujos futuros. Es también un termómetro psicológico. Y ningún gobierno quiere llegar a noviembre con mercados deprimidos."')
        ),

        section('02 // ESCENARIO BASE: ESTRUCTURA TEMPORAL',
            '<p style="color:var(--color-muted);">Si tuviera que dibujar la película del año, sería algo así:</p>'
            + phaseBox('Fase 1: Inicio constructivo (enero–febrero)',
                ['Comienzo de año con inercia positiva','Liquidez todavía presente','Sentimiento moderadamente optimista'],
                'Nada extremo, pero tampoco debilidad clara. Debajo de la superficie empieza a acumularse desgaste: valoraciones exigentes, posicionamiento cargado y narrativas muy consensuadas.'
            )
        ),

        section('03 // LA CAÍDA DE PRIMAVERA: NÚCLEO TÁCTICO DEL AÑO',
            // Marca de la revisión, para quien llegue directamente aquí. El
            // texto original de la sección sigue igual debajo.
            '<div style="color:var(--color-accent);font-size:12px;margin-bottom:10px;">🔎 Revisión septiembre 2026: se cumplió — corrección del 9% al 12% con el suelo el 30/03, y rebote del 20% al 28% desde ahí. Detalle arriba.</div>'
            + quote('No como posibilidad remota. Como elemento central del año.', '#f23645')
            + '<p style="color:var(--color-muted);margin:10px 0;">Porque ahí confluyen:</p>'
            + list(['Ajustes de expectativas macro','Repricing de política monetaria','Ruido político creciente','Fatiga tras el impulso inicial','Liquidez más irregular'])
            + box('warning',
                '<p style="color:var(--color-text);">No hablo de crisis financiera. Estoy pensando en:</p>'
                + list(['Correcciones del <b style="color:var(--color-accent)">8% al 15%</b> en índices principales','Más daño en sectores especulativos','Limpieza fuerte en activos sobreextendidos','Volatilidad disparándose temporalmente','Titulares alarmistas'])
                + '<p style="color:var(--color-accent);margin-top:10px;font-size:14px;">Lo suficiente para generar miedo real. Pero no lo suficiente para romper la estructura macro.</p>'
            )
        ),

        section('04 // ¿POR QUÉ CREO QUE SERÍA COMPRABLE?',
            '<p style="color:var(--color-muted);">En año electoral, el incentivo para sostener el sentimiento económico es altísimo. Si los mercados corrigen, aumenta la probabilidad de:</p>'
            + list(['Tono más acomodaticio desde autoridades','Señales de apoyo fiscal','Narrativa de estabilidad','Expectativas de política monetaria menos restrictiva'])
            + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem;">'
            + stratCard('❌ NO ES', '"Si cae, salgo corriendo"', '#f23645')
            + stratCard('✅ ES', '"Si cae según el patrón esperado, empiezo a escalar riesgo"', 'var(--color-accent)')
            + '</div>'
        ),

        section('05 // CÓMO ME PREPARO PARA ESA VENTANA',
            phaseBox('Liquidez estratégica', [],
                'No quiero llegar a marzo completamente invertido si veo extensión excesiva en febrero. Mantener munición seca es parte del plan.'
            )
            + '<p style="color:var(--color-muted);margin:1rem 0 0.5rem;">Lista definida antes de la corrección:</p>'
            + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:0.75rem;margin-bottom:1rem;">'
            + ['⚡ INFRAESTRUCTURA ENERGÉTICA','🔌 REDES ELÉCTRICAS','💻 SEMICONDUCTORES','⛏️ METALES INDUSTRIALES','📈 ACTIVOS BETA ELEVADA']
                .map(t => '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;color:var(--color-accent);font-size:12px;letter-spacing:0.05em;">' + t + '</div>').join('')
            + '</div>'
            + quote('La primavera es mi momento de acumulación estratégica.', 'var(--color-accent)', 'rgba(0,255,173,0.05)')
        ),

        section('06 // SEGUNDO SEMESTRE: RECUPERACIÓN Y TRAMO FUERTE',
            '<p style="color:var(--color-muted);">A medida que se acercan las elecciones:</p>'
            + list(['Disminuye la incertidumbre','Aumenta el apoyo narrativo','Se estabilizan expectativas','El mercado anticipa menor riesgo político'])
            + box('default',
                '<p style="color:var(--color-accent);font-size:13px;margin-bottom:8px;">MI ESCENARIO BASE CONTEMPLA:</p>'
                + list(['Rebote fuerte tras la caída primaveral','Posible recuperación en V si la corrección fue intensa','Rotación hacia sectores con fundamentos sólidos','Mejor comportamiento relativo de activos de riesgo'])
            )
        ),

        section('07 // POLÍTICA FISCAL: "RUN IT HOT"',
            '<p style="color:var(--color-muted);">No espero austeridad agresiva. Mi lectura es que veremos voluntad de mantener la economía caliente:</p>'
            + list(['Gasto público elevado','Proyectos de infraestructura','Incentivos industriales','Apoyo indirecto a mercados'])
            + quote('Eso limita el riesgo de recesión profunda en mi escenario base.')
        ),

        section('08 // POLÍTICA MONETARIA',
            '<p style="color:var(--color-muted);">No espero un endurecimiento extremo. Si la inflación se mantiene moderándose, el margen para mantener tasas estables existe.</p>'
            + phaseBox('', [], 'No necesito recortes agresivos. <b style="color:var(--color-accent)">Necesito que el miedo a subidas adicionales desaparezca.</b>')
        ),

        section('09 // EL DÓLAR Y LA INFLACIÓN',
            '<p style="color:var(--color-muted);">Probablemente comportamiento mixto del dólar:</p>'
            + list(['Fortaleza temporal en momentos de estrés','Debilidad relativa cuando mejora el apetito por riesgo'])
            + '<p style="color:var(--color-muted);margin-top:10px;">En cuanto a inflación, espero un canal moderado — sin volver al pánico inflacionario.</p>'
        ),

        section('10 // COMMODITIES Y ACTIVOS REALES',
            '<p style="color:var(--color-muted);margin-bottom:1rem;">2026 puede favorecer activos reales en determinados momentos:</p>'
            + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:0.75rem;margin-bottom:1rem;">'
            + [['🥇 ORO','Cobertura ante incertidumbre'],['🔩 METALES INDUSTRIALES','Ligados a infraestructura'],['⛽ ENERGÍA TRADICIONAL','Sensible a tensiones geopolíticas'],['🔗 CADENAS DE SUMINISTRO','Activos estratégicos']]
                .map(([t,d]) => '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.75rem;">'
                    + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.05em;margin-bottom:4px;">' + t + '</div>'
                    + '<div style="color:var(--color-muted);font-size:11px;">' + d + '</div>'
                    + '</div>').join('')
            + '</div>'
        ),

        section('11 // TECNOLOGÍA E INTELIGENCIA ARTIFICIAL',
            '<p style="color:var(--color-muted);">No etiqueto automáticamente el sector como burbuja. Sí veo sobreextensiones en ciertos nombres. Pero también veo transformación estructural real.</p>'
            + box('danger',
                '<p style="color:#ff9800;font-size:13px;margin-bottom:6px;">⚠️ EL RIESGO ESTÁ EN PAGAR CUALQUIER PRECIO</p>'
                + '<p style="color:var(--color-accent);">La oportunidad está en seleccionar modelos de negocio con adopción tangible.</p>'
            )
        ),

        section('12 // RIESGOS QUE PODRÍAN INVALIDAR MI ESCENARIO',
            box('danger', list(['Repunte inflacionario inesperado','Política monetaria volviéndose agresiva otra vez','Evento geopolítico estructural','Recesión profunda no anticipada']))
            + quote('Si la caída de primavera viniera acompañada de deterioro macro estructural, entonces no sería corrección táctica, sería cambio de régimen.', '#f23645')
            + '<p style="color:var(--color-muted);">Pero ese no es mi escenario base.</p>'
        ),

        conclusion(),
    ].join('');
}

function conclusion() {
    return '<div style="border-top:1px solid var(--color-border);margin-top:2rem;padding-top:2rem;">'
        + '<div style="color:var(--color-secondary);font-size:14px;letter-spacing:0.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1.5rem;">🔚 CONCLUSIÓN: 2026 COMO AÑO DE PREPARACIÓN Y EJECUCIÓN</div>'
        + box('default',
            list(['Inicio razonablemente estable','Corrección relevante en primavera','Ventana estratégica de acumulación','Recuperación progresiva hacia segunda mitad','Cierre de año constructivo si el patrón electoral se mantiene'])
        )
        + '<p style="color:var(--color-muted);margin:1rem 0;">No espero un año cómodo. <b style="color:var(--color-accent)">Espero un año exigente.</b></p>'
        + '<p style="color:var(--color-muted);">Pero precisamente por eso, potencialmente muy rentable para quien entienda el timing de la volatilidad.</p>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:0.75rem;margin:1.5rem 0;">'
        + ['NO TEMO LA CAÍDA DE PRIMAVERA','LA ESPERO','LA PLANIFICO','LA QUIERO']
            .map(t => '<div style="background:rgba(0,255,173,0.05);border:1px solid var(--color-accent);border-radius:var(--radius);padding:1rem;text-align:center;color:var(--color-accent);font-size:13px;letter-spacing:0.08em;font-weight:500;">' + t + '</div>').join('')
        + '</div>'
        + '<div style="text-align:center;padding:2rem;background:rgba(0,255,173,0.03);border:1px solid var(--color-accent);border-radius:var(--radius);margin-top:1rem;">'
        + '<p style="color:var(--color-muted);margin-bottom:8px;">Porque en mi escenario base, no es el inicio del problema.</p>'
        + '<p style="color:var(--color-accent);font-size:20px;letter-spacing:0.1em;">Es la oportunidad del año.</p>'
        + '</div>'
        + '</div>';
}

function footer() {
    return '<div style="text-align:center;margin-top:3rem;padding:1.5rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.15em;">'
        + '[END OF TRANSMISSION // ROADMAP_2026_v1.0]<br>'
        + '[STATUS: ACTIVE] · [REVISADO: SEPTIEMBRE 2026]'
        + '</div>'
        + avisoLegal()
        + '</div>';
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function section(title, content) {
    return '<div style="margin-bottom:2rem;">'
        + '<div style="color:var(--color-secondary);font-size:14px;letter-spacing:0.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1rem;">' + title + '</div>'
        + content
        + '</div>'
        + divider();
}

function divider() {
    return '<div style="height:1px;background:linear-gradient(90deg,transparent,var(--color-accent),transparent);margin:1.5rem 0;"></div>';
}

function box(type, content) {
    const styles = {
        default: 'border:1px solid rgba(0,255,173,0.2);background:linear-gradient(135deg,var(--color-surface),var(--color-bg,#0a0a0a));',
        warning: 'border:1px solid rgba(255,184,0,0.3);background:rgba(255,184,0,0.03);',
        danger:  'border:1px solid rgba(242,54,69,0.3);background:rgba(242,54,69,0.03);',
    };
    return '<div style="' + (styles[type] || styles.default) + 'border-radius:var(--radius);padding:1.25rem;margin:1rem 0;">'
        + content
        + '</div>';
}

function phaseBox(title, items, text) {
    return '<div style="border-left:3px solid var(--color-accent);padding:1rem 1.25rem;margin:1rem 0;background:var(--color-surface);border-radius:0 var(--radius) var(--radius) 0;">'
        + (title ? '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.05em;margin-bottom:8px;">' + title + '</div>' : '')
        + (items.length ? list(items) : '')
        + (text ? '<p style="color:var(--color-muted);margin-top:8px;font-size:13px;">' + text + '</p>' : '')
        + '</div>';
}

function quote(text, color, bg) {
    color = color || 'var(--color-accent)';
    bg    = bg    || 'rgba(0,255,173,0.05)';
    return '<div style="background:' + bg + ';border:1px solid ' + color + '44;border-radius:var(--radius);padding:1rem 1.25rem;margin:1rem 0;text-align:center;color:' + color + ';font-size:13px;line-height:1.6;">'
        + text
        + '</div>';
}

function list(items) {
    return '<ul style="list-style:none;padding:0;margin:0.5rem 0;">'
        + items.map(i => '<li style="color:var(--color-muted);font-size:13px;padding:4px 0;"><span style="color:var(--color-accent);margin-right:8px;">▸</span>' + i + '</li>').join('')
        + '</ul>';
}

function stratCard(title, text, color) {
    return '<div style="background:var(--color-surface);border:1px solid ' + color + '33;border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:' + color + ';font-size:12px;letter-spacing:0.05em;margin-bottom:6px;">' + title + '</div>'
        + '<p style="color:' + color + ';font-size:13px;">' + text + '</p>'
        + '</div>';
}