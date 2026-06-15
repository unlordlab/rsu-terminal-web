// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — Contenido de lecciones
// Estructura modular: cada lección es un objeto independiente con secciones.
// Para añadir/modificar: edita el array LESSONS o añade nuevas entradas.
// ─────────────────────────────────────────────────────────────────────────────

// TIPOS DE BLOQUE disponibles en cada sección:
//  { type: 'text',    content: 'HTML string' }
//  { type: 'tip',     content: 'texto',  label: 'opcional' }
//  { type: 'warning', content: 'texto' }
//  { type: 'concept', title: 'título', content: 'texto' }
//  { type: 'chart',   id: 'nombre_svg' }   → SVG generado en academy_charts.js
//  { type: 'steps',   items: ['paso1','paso2',...] }
//  { type: 'table',   headers: [...], rows: [[...],[...]] }
//  { type: 'divider' }

export const LESSONS = {

    // ── MÓDULO 1, LECCIÓN 1 ────────────────────────────────────────────────
    '1-1': {
        moduleId: 1,
        lessonIndex: 0,
        title: 'Gráfico Mensual — La visión macro',
        duration: '12:00',
        intro: 'El gráfico mensual es el mapa. Todo lo que hagas en temporalidades menores debe estar alineado con lo que este gráfico te dice. Ignorarlo es operar a ciegas.',
        sections: [
            {
                heading: '¿Por qué empezar en mensual?',
                blocks: [
                    { type: 'text', content: 'Cada vela mensual representa <strong>30 días de decisiones</strong> de millones de participantes: fondos de pensiones, hedge funds, bancos centrales e inversores retail. El ruido diario desaparece. Lo que queda es la <em>estructura real del mercado</em>.' },
                    { type: 'chart', id: 'monthly_why' },
                    { type: 'concept', title: 'El Principio Top-Down', content: 'Análisis Top-Down significa ir de lo general a lo particular: primero el mercado global, luego el sector, luego el activo. El gráfico mensual es siempre el primer paso. Si la tendencia mensual es bajista, no busques longs en diario.' },
                ]
            },
            {
                heading: 'Qué buscar en el mensual',
                blocks: [
                    { type: 'text', content: 'En el gráfico mensual no analizas entradas. <strong>Defines el contexto</strong>. Las tres preguntas que debes responder son:' },
                    { type: 'steps', items: [
                        '¿Está el precio en tendencia alcista, bajista o lateral?',
                        '¿Hay niveles históricos de soporte o resistencia relevantes cerca?',
                        '¿El precio está lejos o cerca de máximos/mínimos históricos?',
                    ]},
                    { type: 'chart', id: 'monthly_structure' },
                    { type: 'tip', label: 'CLAVE', content: 'Si el precio lleva 3 o más meses consecutivos por encima de la media de 10 meses, estás en tendencia alcista mensual. Eso es suficiente para buscar largos en temporalidades menores.' },
                ]
            },
            {
                heading: 'La Media de 10 Meses (MA10)',
                blocks: [
                    { type: 'text', content: 'La media móvil de 10 meses es una de las herramientas más sencillas y poderosas del análisis técnico mensual. Equivale aproximadamente a la media de 200 días, pero <strong>filtra mejor el ruido</strong> porque trabaja con cierres mensuales.' },
                    { type: 'chart', id: 'ma10_monthly' },
                    { type: 'table',
                        headers: ['Situación', 'Señal', 'Acción'],
                        rows: [
                            ['Precio cruza MA10 al alza', '🟢 Alcista', 'Buscar longs en TF menores'],
                            ['Precio cruza MA10 a la baja', '🔴 Bajista', 'Reducir exposición, buscar shorts'],
                            ['Precio consolida sobre MA10', '🟡 Neutral', 'Esperar confirmación'],
                            ['MA10 plana o en lateral', '⚪ Sin tendencia', 'Operar rangos o esperar'],
                        ]
                    },
                    { type: 'warning', content: 'No uses el cruce de la MA10 mensual como señal de entrada directa. Es un filtro de contexto, no un trigger. Las entradas se buscan en diario o semanal.' },
                ]
            },
            {
                heading: 'Niveles históricos que importan',
                blocks: [
                    { type: 'text', content: 'En mensual los niveles que más respeta el precio son los que han sido testeados <strong>múltiples veces a lo largo de años</strong>. Estos niveles actúan como imanes cuando el precio se acerca.' },
                    { type: 'chart', id: 'monthly_levels' },
                    { type: 'concept', title: 'Polaridad de niveles', content: 'Una resistencia histórica, cuando es superada con fuerza y volumen, se convierte en soporte. Y viceversa. Este fenómeno se llama polaridad y es especialmente fiable en el gráfico mensual porque los niveles llevan años siendo respetados.' },
                    { type: 'tip', label: 'PRÁCTICA', content: 'Abre un gráfico mensual de cualquier índice. Marca los 3 niveles más evidentes (donde el precio rebotó o se detuvo claramente). Esos son tus referencias macro para todo el año.' },
                ]
            },
        ]
    },

    // ── MÓDULO 1, LECCIÓN 2 ────────────────────────────────────────────────
    '1-2': {
        moduleId: 1,
        lessonIndex: 1,
        title: 'Gráfico Semanal — La tendencia media',
        duration: '11:00',
        intro: 'Si el mensual te dice a dónde va el mercado, el semanal te dice cómo está llegando. La tendencia semanal es donde los traders de posición y los swing traders toman sus decisiones.',
        sections: [
            {
                heading: 'El semanal como filtro de tendencia',
                blocks: [
                    { type: 'text', content: 'Cada vela semanal agrupa <strong>5 sesiones de trading</strong>. El ruido del día a día se limpia y lo que queda es la verdadera dirección del dinero inteligente durante esa semana.' },
                    { type: 'chart', id: 'weekly_trend' },
                    { type: 'concept', title: 'Alineación Mensual-Semanal', content: 'La regla de oro: solo operas en la dirección en que el semanal coincide con el mensual. Si el mensual es alcista y el semanal también lo es, la probabilidad de éxito de tus largos se multiplica.' },
                ]
            },
            {
                heading: 'Máximos y mínimos en semanal',
                blocks: [
                    { type: 'text', content: 'La tendencia se define por la secuencia de máximos y mínimos. No necesitas indicadores. Solo necesitas leer el precio:' },
                    { type: 'chart', id: 'highs_lows_weekly' },
                    { type: 'steps', items: [
                        '<strong>Tendencia alcista:</strong> cada máximo es más alto que el anterior (HH) y cada mínimo también (HL)',
                        '<strong>Tendencia bajista:</strong> cada máximo es más bajo (LH) y cada mínimo también (LL)',
                        '<strong>Lateral:</strong> los máximos y mínimos se mantienen en el mismo rango sin progresión clara',
                        '<strong>Cambio de tendencia:</strong> cuando se rompe el último mínimo relevante en alcista (o el máximo en bajista)',
                    ]},
                    { type: 'warning', content: 'Un solo mínimo roto no confirma cambio de tendencia. Necesitas ver que el precio no recupera la zona rota y que el siguiente impulso forma un máximo más bajo. Espera confirmación.' },
                ]
            },
            {
                heading: 'Las medias clave en semanal',
                blocks: [
                    { type: 'text', content: 'En semanal las dos medias más relevantes son la <strong>EMA 21</strong> y la <strong>SMA 50</strong>. La EMA 21 actúa como soporte dinámico en tendencias fuertes. La SMA 50 es el nivel que separa el mercado sano del débil.' },
                    { type: 'chart', id: 'weekly_emas' },
                    { type: 'table',
                        headers: ['Media', 'Equivalencia diaria', 'Uso principal'],
                        rows: [
                            ['EMA 21 semanal', '~EMA 100 diario', 'Soporte dinámico en tendencia'],
                            ['SMA 50 semanal', '~SMA 250 diario', 'Nivel separador bull/bear'],
                            ['SMA 10 semanal', '~SMA 50 diario', 'Momentum a corto plazo'],
                        ]
                    },
                    { type: 'tip', label: 'ENTRY ZONE', content: 'Los retrocesos que tocan la EMA 21 semanal en tendencia alcista son de las mejores oportunidades de entrada. El precio regresa a la media, recupera fuerza y continúa. Busca una vela de confirmación antes de entrar.' },
                ]
            },
            {
                heading: 'Leer el momentum semanal',
                blocks: [
                    { type: 'text', content: 'El momentum semanal te dice si la tendencia está <strong>acelerando o agotándose</strong>. Las señales de agotamiento en semanal son especialmente fiables porque representan semanas enteras de esfuerzo sin resultado.' },
                    { type: 'chart', id: 'weekly_momentum' },
                    { type: 'concept', title: 'Divergencia de momentum', content: 'Cuando el precio hace máximos más altos pero el RSI semanal hace máximos más bajos, hay divergencia bajista. Es una señal de agotamiento que precede muchos techos importantes. No es señal de venta inmediata, sino de reducir riesgo y vigilar.' },
                ]
            },
        ]
    },

    // ── MÓDULO 1, LECCIÓN 3 ────────────────────────────────────────────────
    '1-3': {
        moduleId: 1,
        lessonIndex: 2,
        title: 'Gráfico Diario — El setup operativo',
        duration: '12:00',
        intro: 'El gráfico diario es donde tomas tus decisiones de entrada y salida. Aquí se define el setup: el patrón concreto que justifica abrir una posición.',
        sections: [
            {
                heading: 'El diario dentro del contexto mayor',
                blocks: [
                    { type: 'text', content: 'Antes de abrir un gráfico diario, ya debes saber: <strong>la tendencia mensual es alcista</strong> y <strong>la tendencia semanal también</strong>. Solo entonces el diario tiene sentido como timeframe de entrada.' },
                    { type: 'chart', id: 'daily_context' },
                    { type: 'tip', label: 'REGLA', content: 'El diario solo te da señales de compra cuando el mensual y el semanal son alcistas. Si hay conflicto entre timeframes, no operas. La duda es una señal de que el setup no está claro.' },
                ]
            },
            {
                heading: 'Anatomía de un setup en diario',
                blocks: [
                    { type: 'text', content: 'Un setup válido en diario tiene siempre tres elementos: <strong>estructura</strong> (tendencia clara), <strong>nivel</strong> (soporte o zona de interés) y <strong>catalizador</strong> (vela o patrón que activa la entrada).' },
                    { type: 'chart', id: 'daily_setup' },
                    { type: 'steps', items: [
                        '<strong>Estructura:</strong> precio por encima de EMA 21 y SMA 50, haciendo HH y HL',
                        '<strong>Nivel:</strong> retroceso a EMA 21, zona de soporte previa o base de consolidación',
                        '<strong>Catalizador:</strong> vela envolvente alcista, pin bar sobre soporte, o cierre fuerte por encima de resistencia con volumen',
                    ]},
                    { type: 'concept', title: 'La zona de entrada óptima', content: 'No entras en el primer toque de soporte. Esperas al catalizador: una vela que demuestre que los compradores están reaccionando. Esto reduce los setups pero aumenta drásticamente la tasa de éxito.' },
                ]
            },
            {
                heading: 'Las medias en diario',
                blocks: [
                    { type: 'text', content: 'Las medias más utilizadas en diario son la <strong>EMA 21</strong>, la <strong>SMA 50</strong> y la <strong>SMA 200</strong>. Cada una cumple un rol diferente:' },
                    { type: 'chart', id: 'daily_mas' },
                    { type: 'table',
                        headers: ['Media', 'Rol', 'Señal clave'],
                        rows: [
                            ['EMA 21', 'Soporte dinámico a corto', 'Retroceso a EMA 21 = posible entrada'],
                            ['SMA 50', 'Soporte medio plazo', 'Precio sobre SMA50 = tendencia sana'],
                            ['SMA 200', 'Separador bull/bear', 'Precio bajo SMA200 = evitar longs'],
                        ]
                    },
                    { type: 'warning', content: 'Nunca pongas un stop justo en la media. El precio frecuentemente hace un spike por debajo antes de recuperar. Pon el stop por debajo de la vela de catalizador, no de la media.' },
                ]
            },
            {
                heading: 'Gestión del trade desde el diario',
                blocks: [
                    { type: 'text', content: 'Una vez dentro, el gráfico diario también te dice cuándo salir. Las señales de salida más fiables son: <strong>cierre por debajo de EMA 21</strong>, <strong>vela de reversión en resistencia</strong> o <strong>pérdida de la estructura de HH-HL</strong>.' },
                    { type: 'chart', id: 'daily_exit' },
                    { type: 'tip', label: 'TRAILING STOP', content: 'En tendencias fuertes, sube el stop loss al mínimo de cada semana completa. Así capturas el grueso del movimiento sin microgestionar. Cierra parcialmente en la primera resistencia relevante y deja correr el resto.' },
                ]
            },
        ]
    },

    // ── MÓDULO 1, LECCIÓN 4 ────────────────────────────────────────────────
    '1-4': {
        moduleId: 1,
        lessonIndex: 3,
        title: 'Velas Limpias — Sin ruido visual',
        duration: '10:00',
        intro: 'La configuración visual de tu gráfico afecta directamente a tus decisiones. Demasiados indicadores generan parálisis. Un gráfico limpio genera claridad.',
        sections: [
            {
                heading: 'El problema del gráfico sobrecargado',
                blocks: [
                    { type: 'text', content: 'El error más común del trader novato es <strong>añadir indicadores hasta que el gráfico está lleno</strong>. Cada indicador añadido retrasa la lectura del precio y añade contradicciones. Cuando el MACD dice compra y el RSI dice sobrecompra, ¿qué haces?' },
                    { type: 'chart', id: 'chart_messy_vs_clean' },
                    { type: 'warning', content: 'Los indicadores son derivados del precio. Todos calculan variaciones del mismo dato: el precio. Añadir 5 indicadores no añade 5 fuentes de información. Es la misma información repetida con más retraso.' },
                ]
            },
            {
                heading: 'El setup de gráfico profesional',
                blocks: [
                    { type: 'text', content: 'La configuración que usan la mayoría de traders profesionales es sorprendentemente simple. Velas japonesas, dos o tres medias y nada más. Todo lo demás es opcional y contextual.' },
                    { type: 'chart', id: 'clean_chart_setup' },
                    { type: 'steps', items: [
                        '<strong>Tipo de gráfico:</strong> velas japonesas (candlestick). Nunca líneas ni barras OHLC para análisis de acción del precio',
                        '<strong>Fondo:</strong> oscuro o neutro. Reduce la fatiga visual en sesiones largas',
                        '<strong>Medias:</strong> EMA 21 (naranja), SMA 50 (azul), SMA 200 (rojo). Nada más',
                        '<strong>Volumen:</strong> en la parte inferior, discreto. Solo para confirmar, no para analizar constantemente',
                        '<strong>Sin indicadores adicionales</strong> en el panel principal. Si usas RSI, ponlo en panel separado',
                    ]},
                ]
            },
            {
                heading: 'Leer velas japonesas correctamente',
                blocks: [
                    { type: 'text', content: 'Una vela japonesa comunica cuatro datos: apertura, máximo, mínimo y cierre. La relación entre ellos revela el balance de poder entre compradores y vendedores en ese período.' },
                    { type: 'chart', id: 'candle_anatomy' },
                    { type: 'table',
                        headers: ['Tipo de vela', 'Qué dice', 'Contexto relevante'],
                        rows: [
                            ['Vela alcista grande, poco shadow', 'Compradores dominaron toda la sesión', 'Muy alcista si aparece en soporte'],
                            ['Vela bajista grande, poco shadow', 'Vendedores dominaron toda la sesión', 'Muy bajista si aparece en resistencia'],
                            ['Doji (apertura ≈ cierre)', 'Indecisión, equilibrio de fuerzas', 'Importante tras tendencia fuerte'],
                            ['Pin bar (shadow largo)', 'Rechazo de un nivel, reversión potencial', 'Más fiable en niveles clave'],
                            ['Inside bar (dentro de la anterior)', 'Compresión, espera movimiento', 'Ruptura define la dirección'],
                        ]
                    },
                    { type: 'concept', title: 'El cierre es lo que importa', content: 'De los cuatro datos de una vela, el cierre es el más importante. Los shadows (mechas) muestran intentos fallidos. El cuerpo muestra dónde terminó el poder. Un cierre en máximos de la vela es mucho más alcista que una vela con mecha larga superior aunque el precio haya subido.' },
                ]
            },
            {
                heading: 'Colores y configuración visual',
                blocks: [
                    { type: 'text', content: 'Los colores de las velas importan menos de lo que parece. Hay traders rentables con velas verde/rojo y otros con azul/blanco. Lo que sí importa es la <strong>consistencia y la legibilidad</strong>.' },
                    { type: 'chart', id: 'candle_colors' },
                    { type: 'tip', label: 'CONFIGURACIÓN', content: 'Usa velas con cuerpo sólido y sombras finas. Activa la opción "hollow candles" si tu plataforma la tiene: las velas alcistas tienen cuerpo hueco (solo borde) y las bajistas sólido. Permite leer el momentum de un vistazo sin depender del color.' },
                    { type: 'tip', label: 'TIMEFRAMES', content: 'Configura tres ventanas simultáneas: mensual + semanal + diario. Muchas plataformas permiten layouts de múltiples paneles. Ese es tu setup de trabajo estándar. Nunca analices en un solo timeframe.' },
                ]
            },
        ]
    },
};
