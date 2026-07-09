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

    // ── MÓDULO 0, LECCIÓN 1 ────────────────────────────────────────────────
    '0-1': {
        moduleId: 0,
        lessonIndex: 0,
        title: 'Qué es RSU Terminal',
        duration: '10 min',
        intro: 'RSU Terminal es una plataforma de análisis bursátil construida por traders, para traders. No es un broker, no da señales automáticas y no gestiona tu dinero. Es una herramienta para ayudarte a tomar mejores decisiones con más información y más contexto.',
        sections: [
            {
                heading: 'Origen y filosofía',
                blocks: [
                    { type: 'text', content: 'RSU Terminal nació de una necesidad concreta: tener en un solo lugar todas las herramientas que un trader serio necesita para analizar el mercado, sin depender de plataformas dispersas, sin suscripciones múltiples y con una estética que respeta el trabajo de análisis. La terminal fue diseñada para una comunidad de traders activos que comparten una metodología común.' },
                    { type: 'chart', id: 'rsu_philosophy' },
                    { type: 'concept', title: 'Lo que RSU Terminal NO es', content: 'RSU Terminal no es un robot de trading, no genera señales de compra/venta automáticas, no gestiona tu dinero y no garantiza resultados. Es una herramienta de análisis. Las decisiones las tomas tú. La responsabilidad es tuya. Esta distinción es fundamental: una herramienta potente en manos de alguien sin metodología puede hacer más daño que bien.' },
                ]
            },
            {
                heading: 'La comunidad RSU',
                blocks: [
                    { type: 'text', content: 'La terminal es mantenida y financiada por una comunidad de ~100 traders que contribuyen a los costes de infraestructura y APIs. No hay anunciantes, no hay conflictos de interés. La plataforma evoluciona según las necesidades reales de sus usuarios.' },
                    { type: 'chart', id: 'rsu_community' },
                    { type: 'steps', items: [
                        'Acceso a datos de mercado en tiempo real vía WebSocket',
                        'Scanner CAN SLIM sobre el S&P 500 completo',
                        'Options Flow con detección de actividad institucional',
                        'Briefing nocturno con análisis macro automatizado',
                        'Academia con metodología completa de trading',
                    ]},
                ]
            },
            {
                heading: 'Para quién es RSU Terminal',
                blocks: [
                    { type: 'text', content: 'RSU Terminal está diseñada para traders con experiencia básica o intermedia que quieren llevar su análisis al siguiente nivel. No es para quien busca "señales fáciles" — es para quien entiende que el trading requiere metodología, disciplina y trabajo constante.' },
                    { type: 'chart', id: 'rsu_for_who' },
                    { type: 'table',
                        headers: ['Perfil', 'RSU Terminal', 'Motivo'],
                        rows: [
                            ['Trader con metodología propia', '✓ Ideal', 'Herramientas que potencian tu proceso'],
                            ['Trader aprendiendo', '✓ Válido', 'Academia + herramientas integradas'],
                            ['Buscador de señales automáticas', '✗ No encaja', 'RSU no genera señales de compra/venta'],
                            ['Inversor pasivo (buy & hold)', '~ Parcial', 'Solo módulos de research y cartera'],
                        ]
                    },
                ]
            },
            {
                heading: 'Disclaimer importante',
                blocks: [
                    { type: 'text', content: 'Nada de lo que aparece en RSU Terminal es asesoramiento financiero. Los análisis, scores, ratings y briefings son herramientas de información, no recomendaciones de inversión. Los mercados financieros implican riesgo de pérdida de capital. Opera siempre dentro de tu tolerancia al riesgo personal.' },
                    { type: 'warning', content: 'Los datos de yfinance, FMP y otras fuentes pueden tener retrasos, errores o inconsistencias. Contrasta siempre la información crítica con fuentes primarias (broker, SEC EDGAR, Bloomberg) antes de tomar decisiones de trading. RSU Terminal es una herramienta de apoyo, no la única fuente de verdad.' },
                ]
            },
        ]
    },

    // ── MÓDULO 0, LECCIÓN 2 ────────────────────────────────────────────────
    '0-2': {
        moduleId: 0,
        lessonIndex: 1,
        title: 'La Metodología RSU',
        duration: '10 min',
        intro: 'RSU no es una colección aleatoria de herramientas. Hay una metodología detrás — un marco de análisis coherente que va de lo macro a lo micro, del contexto al detalle. Entender el marco es tan importante como entender cada herramienta.',
        sections: [
            {
                heading: 'El enfoque Top-Down',
                blocks: [
                    { type: 'text', content: 'La metodología RSU parte siempre del contexto más grande hacia el más pequeño. Primero entiendes el mercado general, luego el sector, luego el activo individual. Nunca al revés. Analizar una acción sin entender primero si el mercado está en tendencia alcista o bajista es como navegar sin mirar el horizonte.' },
                    { type: 'chart', id: 'rsu_topdown' },
                    { type: 'steps', items: [
                        '<strong>Nivel 1 — Mercado:</strong> ¿Cuál es la tendencia del S&P 500? ¿El mercado permite comprar? (Market Dashboard + FED & Macro)',
                        '<strong>Nivel 2 — Sector:</strong> ¿Qué sectores lideran? ¿Hay rotación sectorial en marcha? (RS/RW Scanner + CAN SLIM heatmap)',
                        '<strong>Nivel 3 — Activo:</strong> ¿La acción individual es líder de su sector? (CAN SLIM + Research)',
                        '<strong>Nivel 4 — Setup:</strong> ¿Hay un setup técnico válido con buen R:R? (Análisis técnico)',
                        '<strong>Nivel 5 — Ejecución:</strong> Entrada, stop, tamaño, plan (Planificación del trade)',
                    ]},
                ]
            },
            {
                heading: 'Los tres pilares de la metodología',
                blocks: [
                    { type: 'text', content: 'Toda la metodología RSU descansa en tres pilares que deben estar presentes simultáneamente para considerar una operación. Si falta cualquiera de los tres, no hay trade.' },
                    { type: 'chart', id: 'rsu_three_pillars' },
                    { type: 'concept', title: 'Pilar 1: Contexto favorable', content: 'El mercado general y el sector deben estar en condiciones de permitir compras. Un setup técnico perfecto en un mercado bajista tiene mucha menor probabilidad de éxito. El contexto es el filtro más importante y el primero en evaluarse.' },
                    { type: 'concept', title: 'Pilar 2: Activo de calidad', content: 'No cualquier acción merece atención. RSU busca líderes: activos con RS Rating alto, fundamentales sólidos o en aceleración, y estructura técnica alcista. Los rezagados se quedan fuera independientemente del setup.' },
                    { type: 'concept', title: 'Pilar 3: Setup con R:R favorable', content: 'Incluso con contexto favorable y activo de calidad, si el setup no ofrece un ratio riesgo/recompensa de al menos 1:2, no se opera. La disciplina en el R:R es lo que hace sostenible la metodología a largo plazo.' },
                ]
            },
            {
                heading: 'Gestión del riesgo primero',
                blocks: [
                    { type: 'text', content: 'La gestión del riesgo no es lo último que piensas — es lo primero. Antes de buscar oportunidades, defines cuánto puedes perder. Antes de calcular ganancias potenciales, calculas la pérdida máxima. Esta inversión del orden mental es lo que separa a los traders que sobreviven de los que no.' },
                    { type: 'chart', id: 'rsu_risk_first' },
                    { type: 'table',
                        headers: ['Trader amateur', 'Trader RSU'],
                        rows: [
                            ['"¿Cuánto puedo ganar?"', '"¿Cuánto puedo perder?"'],
                            ['Entra, luego piensa el stop', 'Define el stop antes de entrar'],
                            ['Tamaño según "sensación"', 'Tamaño según riesgo fijo (1%)'],
                            ['Sale cuando tiene miedo', 'Sale cuando el plan lo dice'],
                            ['Promedia pérdidas', 'Nunca promedia pérdidas'],
                        ]
                    },
                ]
            },
            {
                heading: 'Paciencia como ventaja competitiva',
                blocks: [
                    { type: 'text', content: 'La metodología RSU produce relativamente pocas señales de alta calidad. En mercados desfavorables, la respuesta correcta es no operar. Esta inactividad deliberada es incomprendida por los traders que equiparan actividad con productividad, pero es una de las ventajas más importantes del sistema.' },
                    { type: 'chart', id: 'rsu_patience' },
                    { type: 'tip', label: 'REGLA RSU', content: 'Si no hay triple alineación (mercado favorable + activo líder + setup con R:R ≥ 1:2), no hay trade. El capital preservado en períodos de baja probabilidad es capital disponible para los momentos de alta probabilidad. Operar menos, ganar más.' },
                ]
            },
        ]
    },

    // ── MÓDULO 0, LECCIÓN 3 ────────────────────────────────────────────────
    '0-3': {
        moduleId: 0,
        lessonIndex: 2,
        title: 'Las Herramientas',
        duration: '12 min',
        intro: 'RSU Terminal tiene 10 módulos especializados. Cada uno tiene un propósito específico dentro del flujo de análisis. Entender qué hace cada herramienta y cuándo usarla es el primer paso para sacar partido real a la plataforma.',
        sections: [
            {
                heading: 'Análisis de mercado',
                blocks: [
                    { type: 'text', content: 'El primer bloque de herramientas cubre el análisis del contexto de mercado. Son las herramientas que debes revisar antes de mirar cualquier acción individual.' },
                    { type: 'chart', id: 'tools_market_analysis' },
                    { type: 'table',
                        headers: ['Herramienta', 'Qué hace', 'Cuándo usarla'],
                        rows: [
                            ['Market Dashboard', 'Fear & Greed, VIX, AD Line, breadth', 'Cada mañana antes de operar'],
                            ['FED & Macro', 'Balance Fed, curva de tipos, CPI, PCE', 'Semanalmente + días de datos macro'],
                            ['SPXL Strategy', 'Estrategia DCA en correcciones del SPX', 'Cuando el SPX corrige >15%'],
                            ['BTC Stratum', 'Modelo de acumulación Bitcoin on-chain', 'Zonas de acumulación BTC'],
                        ]
                    },
                ]
            },
            {
                heading: 'Selección de activos',
                blocks: [
                    { type: 'text', content: 'El segundo bloque identifica qué activos merecen atención. El objetivo es filtrar de 5,000+ acciones del mercado americano a una lista manejable de candidatos de alta calidad.' },
                    { type: 'chart', id: 'tools_stock_selection' },
                    { type: 'table',
                        headers: ['Herramienta', 'Qué hace', 'Cuándo usarla'],
                        rows: [
                            ['CAN SLIM', 'Scanner IBD + Trend Template sobre S&P 500', 'Dominical — identificar candidatos'],
                            ['RS/RW Scanner', 'Fortaleza/debilidad relativa vs mercado', 'Identificar líderes y rezagados'],
                            ['Options Flow', 'Flujo de opciones institucional', 'Detectar posicionamiento institucional'],
                            ['Research / Earnings', 'Análisis fundamental + LLM', 'Antes de entrar en un activo nuevo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Seguimiento y gestión',
                blocks: [
                    { type: 'text', content: 'El tercer bloque gestiona las posiciones abiertas y mantiene al trader informado sin necesidad de estar pegado a la pantalla.' },
                    { type: 'chart', id: 'tools_management' },
                    { type: 'table',
                        headers: ['Herramienta', 'Qué hace', 'Cuándo usarla'],
                        rows: [
                            ['Cartera', 'Seguimiento de posiciones con precios live', 'Siempre abierta durante sesión'],
                            ['Resumen de Mercado Diario', 'Resumen macro + noticias clasificadas por IA', 'Cada noche antes de cerrar'],
                            ['Newsfeed', 'Noticias en tiempo real por ticker', 'Ante movimientos inexplicados'],
                        ]
                    },
                    { type: 'tip', label: 'FLUJO RECOMENDADO', content: 'Mañana: Market Dashboard → CAN SLIM/RS/RW → Cartera. Durante sesión: Cartera + Newsfeed si hay movimientos. Noche: Resumen de Mercado Diario + Research para preparar el día siguiente. Domingo: CAN SLIM scan completo + FED & Macro semanal.' },
                ]
            },
            {
                heading: 'La Academia',
                blocks: [
                    { type: 'text', content: 'La Academia es el módulo donde estás ahora. Está diseñada para que el conocimiento y las herramientas se aprendan juntos — cada lección explica un concepto y las herramientas de la terminal que lo implementan.' },
                    { type: 'chart', id: 'tools_academy' },
                    { type: 'concept', title: 'Teoría + práctica integradas', content: 'El enfoque de la Academia es distinto al de la mayoría de cursos de trading. No hay teoría abstracta desconectada de la práctica. Cada concepto aprendido tiene una herramienta en la terminal donde puedes aplicarlo inmediatamente. Aprende el concepto → ve a la herramienta → aplícalo con datos reales.' },
                ]
            },
        ]
    },

    // ── MÓDULO 0, LECCIÓN 4 ────────────────────────────────────────────────
    '0-4': {
        moduleId: 0,
        lessonIndex: 3,
        title: 'Flujo de Trabajo Semanal',
        duration: '8 min',
        intro: 'Tener las mejores herramientas sin un proceso estructurado es como tener un taller de carpintería sin saber qué construir. El flujo de trabajo semanal convierte las herramientas en un sistema reproducible.',
        sections: [
            {
                heading: 'El ritual dominical',
                blocks: [
                    { type: 'text', content: 'El domingo es el día más importante de la semana para un trader. Sin el ruido del mercado abierto, con calma, defines el contexto de la semana que empieza. Todo lo que hagas el domingo determina la calidad de tus decisiones de lunes a viernes.' },
                    { type: 'chart', id: 'weekly_ritual_sunday' },
                    { type: 'steps', items: [
                        '<strong>CAN SLIM Scanner:</strong> Scan completo del S&P 500. Identificar candidatos con score ≥ 60.',
                        '<strong>RS/RW:</strong> ¿Qué sectores lideran esta semana? ¿Hay rotación?',
                        '<strong>Market Dashboard:</strong> Sesgo mensual, estructura semanal, estado del mercado.',
                        '<strong>FED & Macro:</strong> ¿Hay datos macro importantes esta semana? (CPI, Fed, PCE, NFP)',
                        '<strong>Watchlist:</strong> Lista de 5-10 activos a vigilar con niveles y triggers definidos.',
                    ]},
                ]
            },
            {
                heading: 'La rutina diaria (lunes a viernes)',
                blocks: [
                    { type: 'text', content: 'La rutina diaria es corta — 15-20 minutos antes de la apertura y 10 minutos al cierre. No necesitas estar frente a la pantalla todo el día si tienes un plan claro.' },
                    { type: 'chart', id: 'weekly_ritual_daily' },
                    { type: 'table',
                        headers: ['Momento', 'Herramienta', 'Tiempo', 'Qué buscas'],
                        rows: [
                            ['Pre-apertura (8:30-9:30)', 'Market Dashboard', '5 min', 'Contexto macro, futuros, VIX'],
                            ['Pre-apertura', 'Newsfeed', '5 min', 'Noticias relevantes para watchlist'],
                            ['Pre-apertura', 'Cartera', '5 min', 'Precios actuales, revisar stops'],
                            ['Durante sesión', 'Cartera (live)', 'Pasivo', 'Solo si hay alertas o triggers'],
                            ['Cierre (16:00-16:30)', 'Cartera + Resumen de Mercado Diario', '10 min', 'Revisión del día, prep mañana'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cuándo no hacer nada',
                blocks: [
                    { type: 'text', content: 'Una parte fundamental del flujo de trabajo es reconocer cuándo el mercado no ofrece condiciones favorables y, en consecuencia, no operar. Esta disciplina de "no hacer nada" es la más difícil de mantener pero una de las más rentables.' },
                    { type: 'chart', id: 'weekly_ritual_wait' },
                    { type: 'concept', title: 'Las semanas sin trade', content: 'Habrá semanas donde completes toda tu rutina de análisis y concluyas que no hay ningún setup de suficiente calidad. Eso no es un fracaso — es el sistema funcionando correctamente. El trader que fuerza un trade cada semana acaba perdiendo. El trader que espera la oportunidad de A+ acaba ganando.' },
                ]
            },
            {
                heading: 'Adaptación según condición de mercado',
                blocks: [
                    { type: 'text', content: 'El flujo de trabajo no es idéntico en todos los entornos de mercado. En mercado alcista confirmado buscas activamente. En mercado bajo presión reduces el tamaño. En corrección te limitas a gestionar posiciones existentes y preparar la lista para el rebote.' },
                    { type: 'chart', id: 'weekly_ritual_adapt' },
                    { type: 'table',
                        headers: ['Estado mercado', 'Postura', 'Actividad'],
                        rows: [
                            ['Confirmed Uptrend', 'Ofensiva', 'Buscar y abrir posiciones. Tamaño completo.'],
                            ['Uptrend Under Pressure', 'Defensiva', 'No abrir nuevas. Proteger existentes.'],
                            ['Rally Attempt', 'Espera activa', 'Preparar lista. Esperar Follow Through Day.'],
                            ['Market Correction', 'Preservar capital', 'Gestionar stops. Reducir exposición.'],
                        ]
                    },
                ]
            },
        ]
    },

    // ── MÓDULO 1, LECCIÓN 1 ────────────────────────────────────────────────
    '1-1': {
        moduleId: 1,
        lessonIndex: 0,
        title: 'Gráfico Mensual — La visión macro',
        duration: '8 min',
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
        duration: '8 min',
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
        duration: '9 min',
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
        duration: '7 min',
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

    // ── MÓDULO 1, LECCIÓN 5 ────────────────────────────────────────────────
    '1-5': {
        moduleId: 1,
        lessonIndex: 4,
        title: 'Medias Móviles Exponenciales (EMA)',
        duration: '14 min',
        intro: 'Ya has usado la EMA 21 como soporte dinámico en las lecciones anteriores. Esta lección va un paso atrás: qué es exactamente una EMA, en qué se diferencia de una SMA, y cómo convertirla en una herramienta operativa concreta de entrada y salida — no solo una línea en el gráfico.',
        sections: [
            {
                heading: 'Qué es una EMA y por qué no es lo mismo que una SMA',
                blocks: [
                    { type: 'text', content: 'Una media móvil simple (SMA) da el mismo peso a cada vela del periodo: el cierre de hace 21 sesiones pesa exactamente igual que el de ayer. Una media móvil exponencial (EMA) pondera de forma decreciente hacia atrás — el precio más reciente tiene más peso que el más antiguo. El resultado práctico: la EMA reacciona antes a un cambio de precio que la SMA del mismo periodo.' },
                    { type: 'chart', id: 'ema_vs_sma_reaction' },
                    { type: 'table', headers: ['Característica', 'SMA', 'EMA'], rows: [
                        ['Peso de cada vela', 'Igual para todas', 'Mayor cuanto más reciente'],
                        ['Velocidad de reacción', 'Más lenta, más suave', 'Más rápida, sigue el precio de cerca'],
                        ['Retraso (lag)', 'Mayor', 'Menor, aunque nunca cero'],
                        ['Uso típico en RSU', 'SMA 50 / SMA 200 — contexto de fondo', 'EMA 21 — soporte dinámico de corto plazo'],
                    ]},
                    { type: 'concept', title: 'Por qué esto importa para el trading', content: 'La menor inercia de la EMA la hace más útil como referencia de entrada y salida de corto plazo — reacciona antes cuando la tendencia empieza a perder fuerza. La mayor inercia de la SMA la hace más útil como filtro de contexto de fondo — no te saca de la tendencia por un solo día de ruido. Por eso en RSU Terminal se combinan las dos: EMA 21 para timing, SMA 50/200 para contexto.' },
                ]
            },
            {
                heading: 'Por qué la EMA 21 y no otro periodo',
                blocks: [
                    { type: 'text', content: 'El periodo 21 no es arbitrario: corresponde aproximadamente a un mes de sesiones bursátiles (21 días de trading). Es lo suficientemente corto para reaccionar a la estructura reciente de HH/HL, y lo suficientemente largo para no ser ruido de 2-3 días.' },
                    { type: 'warning', content: 'Ningún periodo de EMA es mágico. La EMA 21 funciona bien porque es la que más operadores institucionales vigilan — y cuando muchos participantes reaccionan al mismo nivel, ese nivel se vuelve una profecía autocumplida en cierta medida. Cambiar constantemente de periodo buscando "la EMA perfecta" es curve-fitting, no mejora real.' },
                ]
            },
            {
                heading: 'La EMA como punto de entrada — con confirmación de volumen',
                blocks: [
                    { type: 'text', content: 'El error más común es comprar en el primer toque de la EMA sin más. La EMA marca <em>dónde</em> mirar, no <em>cuándo</em> entrar. La entrada válida necesita dos cosas juntas: una reacción de precio en la EMA, y una lectura de volumen que confirme esa reacción.' },
                    { type: 'chart', id: 'ema_entry_volume' },
                    { type: 'steps', items: [
                        'El precio retrocede hacia la EMA 21 en tendencia alcista establecida (HH/HL previos)',
                        'Durante el retroceso, el volumen debería ser bajo o decreciente — señal de que no hay presión vendedora real, solo una pausa (conecta con la lección de Volumen Clímax: un retroceso con volumen bajo es sano)',
                        'Aparece una vela de reacción alcista sobre o cerca de la EMA (envolvente, pin bar, cierre fuerte)',
                        'Esa vela de reacción debe venir acompañada de volumen superior al de los días de retroceso — es la confirmación de que los compradores han vuelto',
                        'Entrada: en el cierre de la vela de confirmación, o en la ruptura de su máximo al día siguiente',
                    ]},
                    { type: 'warning', content: 'Si el retroceso a la EMA viene con volumen creciente en las velas bajistas, no es una pausa sana — puede ser el inicio de una distribución. No compres el toque de EMA solo porque "está ahí"; sin la lectura de volumen, es una moneda al aire.' },
                ]
            },
            {
                heading: 'La EMA como punto de salida',
                blocks: [
                    { type: 'text', content: 'La misma media que sirve para entrar sirve como referencia de salida — pero con un criterio distinto al de la entrada. Para salir, lo relevante no es el toque de la EMA, sino el cierre respecto a ella.' },
                    { type: 'chart', id: 'ema_exit_signal' },
                    { type: 'table', headers: ['Señal', 'Interpretación', 'Acción'], rows: [
                        ['Mecha toca o perfora la EMA, pero el cierre queda por encima', 'Test normal de soporte dinámico dentro de tendencia sana', 'Mantener posición'],
                        ['Cierre por debajo de la EMA por primera vez en semanas', 'Posible cambio de carácter de la tendencia', 'Reducir posición o poner alerta máxima'],
                        ['Cierre por debajo de la EMA + volumen elevado', 'Salida de manos fuertes, señal de mayor peso', 'Salir total o parcialmente'],
                        ['Precio recupera la EMA al día siguiente con fuerza', 'Falsa señal, continuación probable', 'Reevaluar, posible reentrada'],
                    ]},
                    { type: 'tip', label: 'TRAILING CON EMA', content: 'Una técnica simple de trailing stop es usar el cierre diario respecto a la EMA 21: mientras el precio cierre por encima, mantienes la posición; el primer cierre por debajo es tu señal de salida. No reacciones a un toque intradía ni a una mecha — solo al cierre. Este método suele capturar el 60-70% del movimiento de una tendencia sin necesidad de vigilar el gráfico constantemente.' },
                    { type: 'concept', title: 'Entrada y salida no son simétricas', content: 'Para entrar exiges reacción de precio + confirmación de volumen — dos condiciones. Para salir, basta con el cierre por debajo de la EMA — una condición, porque proteger capital debe ser más rápido y menos exigente que arriesgarlo. Pedir la misma confirmación de volumen para salir que para entrar suele significar salir demasiado tarde.' },
                ]
            },
            {
                heading: 'Golden Cross y Death Cross',
                blocks: [
                    { type: 'text', content: 'El Golden Cross y el Death Cross son los cruces de medias más conocidos del análisis técnico, y trabajan con periodos distintos a los de esta lección: no la EMA 21, sino la <strong>SMA 50</strong> y la <strong>SMA 200</strong> — las mismas que ya usas en el gráfico diario y en el Trend Template de Minervini.' },
                    { type: 'chart', id: 'golden_death_cross' },
                    { type: 'table', headers: ['Cruce', 'Qué ocurre', 'Lectura de fondo'], rows: [
                        ['Golden Cross', 'SMA 50 cruza al alza por encima de la SMA 200', 'La tendencia de medio plazo (50) confirma que ya supera a la de largo plazo (200) — sesgo estructural alcista'],
                        ['Death Cross', 'SMA 50 cruza a la baja por debajo de la SMA 200', 'La tendencia de medio plazo se ha girado por debajo de la de largo plazo — sesgo estructural bajista'],
                    ]},
                    { type: 'warning', content: 'El Golden Cross y el Death Cross son señales <em>tardías</em> por definición: como usan dos medias de 50 y 200 sesiones, el cruce ocurre semanas después de que el precio ya haya cambiado de dirección. No son señales de timing de entrada — son confirmación de que el régimen de fondo ha cambiado, útiles para decidir si operar a favor de largos o de cortos, no para marcar el punto exacto de entrada.' },
                    { type: 'steps', items: [
                        'Usa el Golden/Death Cross como filtro de régimen, igual que la MA10 mensual de la Lección 1: te dice en qué dirección operar, no cuándo',
                        'Para el timing de entrada real, sigue apoyándote en la EMA 21 y la confirmación de volumen de la sección anterior',
                        'Un Golden Cross reciente + retroceso a EMA 21 con volumen bajo es una combinación de alta probabilidad: régimen de fondo alcista confirmado + entrada de precisión',
                        'Desconfía de un Golden Cross que aparece justo cuando el precio ya está muy extendido sobre ambas medias — puede llegar al final del movimiento en vez de al principio',
                    ]},
                    { type: 'tip', label: 'CONTEXTO HISTÓRICO', content: 'El Golden Cross del S&P 500 es una de las señales macro más seguidas por la prensa financiera y por eso tiene un componente de profecía autocumplida: cuando aparece, muchos gestores institucionales que siguen reglas mecánicas empiezan a comprar, lo cual añade demanda real al margen de la señal técnica en sí.' },
                ]
            },
        ]
    },

    // ── MÓDULO 2, LECCIÓN 1 ────────────────────────────────────────────────
    '2-1': {
        moduleId: 2,
        lessonIndex: 0,
        title: 'Máximos Crecientes — Señal alcista',
        duration: '8 min',
        intro: 'El mercado no sube en línea recta. Sube en impulsos y corrige en retrocesos. Cuando cada impulso llega más alto que el anterior, los compradores están en control. Eso es todo lo que necesitas saber para definir una tendencia alcista.',
        sections: [
            {
                heading: '¿Qué es un máximo creciente?',
                blocks: [
                    { type: 'text', content: 'Un <strong>máximo creciente (Higher High, HH)</strong> se produce cuando el precio sube, retrocede, y en el siguiente impulso supera el máximo anterior. Cada nuevo HH confirma que los compradores tienen más fuerza que los vendedores.' },
                    { type: 'chart', id: 'hh_definition' },
                    { type: 'concept', title: 'HH: definición precisa', content: 'Un máximo creciente válido requiere que el precio haya hecho un retroceso claro antes del nuevo impulso. Un precio que sube sin parar no genera HH — genera una vela o barra larga. El HH aparece después de una corrección visible, cuando el nuevo impulso supera el pico anterior.' },
                ]
            },
            {
                heading: 'Por qué los HH confirman tendencia',
                blocks: [
                    { type: 'text', content: 'Detrás de cada HH hay una historia simple: los vendedores intentaron frenar el precio en el máximo anterior, y <strong>fracasaron</strong>. Los compradores absorbieron toda la oferta disponible y empujaron el precio aún más arriba. Eso revela quién manda.' },
                    { type: 'chart', id: 'hh_psychology' },
                    { type: 'steps', items: [
                        'El precio sube y forma un máximo (punto A)',
                        'Los vendedores entran y el precio retrocede — corrección normal',
                        'Los compradores regresan con más fuerza y superan el punto A',
                        'Ese nuevo máximo (punto B > A) es el primer HH confirmado',
                        'Cuando B es superado por C, la tendencia alcista está establecida',
                    ]},
                    { type: 'warning', content: 'Un solo máximo más alto no confirma tendencia. Necesitas al menos dos HH consecutivos, cada uno precedido de un retroceso, para hablar de tendencia alcista establecida. Con uno solo es demasiado pronto.' },
                ]
            },
            {
                heading: 'Identificar HH en el gráfico',
                blocks: [
                    { type: 'text', content: 'La identificación de máximos crecientes es visual y subjetiva en timeframes cortos, pero se vuelve clara y objetiva en semanal y mensual. Cuanto mayor es el timeframe, más fiable es la señal.' },
                    { type: 'chart', id: 'hh_identification' },
                    { type: 'table',
                        headers: ['Timeframe', 'Fiabilidad HH', 'Uso recomendado'],
                        rows: [
                            ['Mensual', '⭐⭐⭐⭐⭐', 'Sesgo macro — dirección del año'],
                            ['Semanal', '⭐⭐⭐⭐', 'Tendencia principal — dirección del mes'],
                            ['Diario',  '⭐⭐⭐',   'Setup operativo — dirección de la semana'],
                            ['Horario', '⭐⭐',     'Ejecución — solo con contexto mayor alineado'],
                            ['< 1h',    '⭐',       'Ruido — usar solo para timing de entrada'],
                        ]
                    },
                    { type: 'tip', label: 'PRÁCTICA', content: 'Abre un gráfico semanal de cualquier índice o acción. Marca con una línea horizontal cada pico relevante. Luego verifica si cada pico supera al anterior. Si lo hace, estás en tendencia alcista. Si no, no lo estás. Así de simple.' },
                ]
            },
            {
                heading: 'HH como señal de continuación',
                blocks: [
                    { type: 'text', content: 'Cuando el precio rompe un máximo previo con fuerza y volumen, no es solo una confirmación de tendencia — es también una <strong>señal de continuación</strong>. Los stops de los vendedores que apostaban por resistencia saltan, añadiendo combustible al movimiento.' },
                    { type: 'chart', id: 'hh_breakout' },
                    { type: 'concept', title: 'Stop Hunt alcista', content: 'Muchos traders ponen stops justo por encima de máximos previos esperando que el precio no los supere. Cuando el precio rompe esos máximos, esos stops se ejecutan como órdenes de compra, acelerando el movimiento alcista. Por eso las rupturas de máximos con volumen suelen ser explosivas.' },
                    { type: 'tip', label: 'ENTRADA', content: 'La entrada más conservadora en una tendencia alcista es esperar la ruptura de un HH y comprar en el retest del nivel roto. El antiguo máximo se convierte en nuevo soporte. Menor riesgo, mayor confirmación.' },
                ]
            },
        ]
    },

    // ── MÓDULO 2, LECCIÓN 2 ────────────────────────────────────────────────
    '2-2': {
        moduleId: 2,
        lessonIndex: 1,
        title: 'Mínimos Crecientes — Soporte dinámico',
        duration: '8 min',
        intro: 'Si los máximos crecientes te dicen que los compradores atacan con más fuerza, los mínimos crecientes te dicen que los vendedores pierden terreno en cada corrección. Juntos forman la firma inequívoca de una tendencia alcista sana.',
        sections: [
            {
                heading: '¿Qué es un mínimo creciente?',
                blocks: [
                    { type: 'text', content: 'Un <strong>mínimo creciente (Higher Low, HL)</strong> ocurre cuando el precio corrige pero no llega tan abajo como la corrección anterior. Cada retroceso encuentra compradores más arriba que la vez anterior. Los vendedores se rinden antes.' },
                    { type: 'chart', id: 'hl_definition' },
                    { type: 'concept', title: 'HL: la firma del comprador institucional', content: 'Cuando un fondo o institución quiere acumular posición, no puede comprar todo de golpe sin mover el precio en su contra. Compra en correcciones. El resultado visible en el gráfico son mínimos que no llegan tan abajo como los anteriores: Higher Lows. Es la huella del dinero inteligente acumulando.' },
                ]
            },
            {
                heading: 'HH + HL: la combinación perfecta',
                blocks: [
                    { type: 'text', content: 'Una tendencia alcista real necesita <strong>ambas condiciones simultáneamente</strong>: máximos crecientes Y mínimos crecientes. Si solo tienes HH sin HL, los retrocesos son demasiado profundos y la tendencia es débil. Si tienes HL sin HH, el precio se acumula pero no avanza.' },
                    { type: 'chart', id: 'hh_hl_combined' },
                    { type: 'table',
                        headers: ['Patrón', 'Interpretación', 'Acción'],
                        rows: [
                            ['HH + HL', 'Tendencia alcista sana', 'Buscar longs en retrocesos'],
                            ['HH sin HL', 'Tendencia frágil, retrocesos profundos', 'Precaución, stops amplios'],
                            ['HL sin HH', 'Acumulación, sin confirmación', 'Esperar ruptura de máximo'],
                            ['Sin HH ni HL', 'Lateral o bajista', 'No operar longs'],
                        ]
                    },
                    { type: 'tip', label: 'REGLA DE ORO', content: 'En una tendencia alcista establecida, cada HL es una oportunidad de entrada. El precio retrocede, forma un mínimo más alto que el anterior, y reanuda el alza. Ese momento — cuando el HL está formado y el precio empieza a girar — es la entrada de menor riesgo en toda la tendencia.' },
                ]
            },
            {
                heading: 'El HL como nivel de stop',
                blocks: [
                    { type: 'text', content: 'Los mínimos crecientes no solo señalan entradas — también definen dónde poner el stop loss. Si compras en tendencia alcista y el precio rompe el último HL relevante, la estructura ha cambiado. <strong>El stop va por debajo del último HL.</strong>' },
                    { type: 'chart', id: 'hl_stop_loss' },
                    { type: 'steps', items: [
                        'Identifica el último HL formado en tu timeframe de entrada',
                        'Entra en la dirección alcista cuando el precio gira desde ese nivel',
                        'Coloca el stop loss por debajo del HL (con un pequeño margen para evitar spikes)',
                        'Si el precio forma un nuevo HL más alto, sube el stop al nuevo nivel',
                        'Cierra la posición si el precio cierra por debajo del último HL en el timeframe de entrada',
                    ]},
                    { type: 'warning', content: 'No pongas el stop justo en el HL. El precio frecuentemente hace un spike por debajo antes de recuperar, especialmente en semanal. Añade un margen del 0.5-1% por debajo del HL para evitar ser sacado por ruido.' },
                ]
            },
            {
                heading: 'Cuando el HL falla: cambio de tendencia',
                blocks: [
                    { type: 'text', content: 'El fallo del HL es la primera señal de alerta en una tendencia alcista. Cuando el precio corrige y <strong>no consigue mantenerse por encima del mínimo anterior</strong>, algo ha cambiado. No es señal inmediata de venta, pero sí de precaución.' },
                    { type: 'chart', id: 'hl_failure' },
                    { type: 'concept', title: 'Secuencia de cambio de tendencia', content: 'El cambio de tendencia alcista a bajista generalmente sigue este orden: primero falla el HL (precio no aguanta más arriba), luego el precio rompe el último HL hacia abajo, y finalmente no consigue superar el último HH. Solo en ese momento se puede confirmar cambio de tendencia. Los cambios bruscos sin estos pasos son menos fiables.' },
                ]
            },
        ]
    },

    // ── MÓDULO 2, LECCIÓN 3 ────────────────────────────────────────────────
    '2-3': {
        moduleId: 2,
        lessonIndex: 2,
        title: 'Máximos Decrecientes — Señal bajista',
        duration: '8 min',
        intro: 'Un mercado bajista no empieza con una caída vertical. Empieza cuando los compradores dejan de poder recuperar los máximos anteriores. Cada rebote que llega menos lejos que el anterior es una venta de los que mandan.',
        sections: [
            {
                heading: '¿Qué es un máximo decreciente?',
                blocks: [
                    { type: 'text', content: 'Un <strong>máximo decreciente (Lower High, LH)</strong> se produce cuando el precio rebota tras una caída, pero no consigue recuperar el máximo anterior. Los compradores intentan recuperar el control y <strong>fracasan</strong>. Los vendedores siguen mandando.' },
                    { type: 'chart', id: 'lh_definition' },
                    { type: 'concept', title: 'LH: la resistencia que baja', content: 'En una tendencia bajista, la resistencia no es un nivel fijo — es un nivel que baja con cada rebote. Los vendedores entran antes, más agresivamente, con cada nuevo intento de recuperación. Eso es lo que genera la serie de LH: la presión vendedora aumenta con cada rebote fallido.' },
                ]
            },
            {
                heading: 'Psicología detrás del LH',
                blocks: [
                    { type: 'text', content: 'Entender por qué se forman los LH es más valioso que simplemente identificarlos. Detrás de cada LH hay tres grupos de participantes actuando:' },
                    { type: 'chart', id: 'lh_psychology' },
                    { type: 'steps', items: [
                        '<strong>Atrapados en longs:</strong> compraron cerca del máximo anterior y esperan el rebote para salir sin pérdida. Cuando el rebote llega, venden aliviados — eso frena el alza',
                        '<strong>Vendedores en corto:</strong> añaden posición en cada rebote porque saben que la tendencia es bajista. Su venta agresiva en el rebote genera el LH',
                        '<strong>Compradores tardíos:</strong> intentan comprar en el rebote pensando que es una oportunidad. Su fuerza se agota antes de llegar al máximo anterior',
                    ]},
                    { type: 'warning', content: 'No intentes comprar cada LH pensando que "el precio ya ha caído suficiente". En una tendencia bajista clara con LH consecutivos, cada rebote es una trampa para compradores. La fuerza siempre está del lado de los vendedores hasta que la estructura cambie.' },
                ]
            },
            {
                heading: 'Usar LH para timing de entrada corta',
                blocks: [
                    { type: 'text', content: 'El LH es la firma del mercado bajista, pero también es la zona de entrada óptima para posiciones cortas. El precio rebota, forma el LH, y empieza a girar a la baja — ese es el momento de menor riesgo para vender.' },
                    { type: 'chart', id: 'lh_short_entry' },
                    { type: 'table',
                        headers: ['Tipo de entrada', 'Riesgo', 'Confirmación necesaria'],
                        rows: [
                            ['Vender en la zona del LH anticipando el giro', 'Alto', 'Ninguna — entrada agresiva'],
                            ['Vender cuando el precio gira en el LH (vela de señal)', 'Medio', 'Vela bajista en LH'],
                            ['Vender en ruptura del último mínimo tras el LH', 'Bajo', 'Cierre bajo mínimo previo'],
                            ['Vender en retest del nivel roto tras la ruptura', 'Muy bajo', 'Precio testa y gira'],
                        ]
                    },
                    { type: 'tip', label: 'ENTRADA ÓPTIMA', content: 'La entrada de menor riesgo en tendencia bajista no es vender en el LH — es esperar que el precio rompa el último mínimo relevante, luego reteste ese nivel desde abajo (ahora convertido en resistencia), y vender cuando confirme el rechazo. Más tarde pero con mucha más probabilidad.' },
                ]
            },
            {
                heading: 'Cuándo el LH indica final de tendencia bajista',
                blocks: [
                    { type: 'text', content: 'La serie de LH termina cuando el precio, en un rebote, <strong>consigue superar el último LH</strong>. No es señal de compra inmediata, pero sí la primera señal de que los vendedores están perdiendo el control.' },
                    { type: 'chart', id: 'lh_reversal' },
                    { type: 'concept', title: 'Primera señal de cambio bajista→alcista', content: 'El cambio de tendencia bajista a alcista empieza cuando un rebote supera el último LH. Esto indica que los compradores han ganado suficiente fuerza para romper la resistencia decreciente. No cierres posiciones cortas en el primer intento — espera que el precio también supere un máximo relevante anterior y forme un HL antes de dar por terminada la tendencia bajista.' },
                ]
            },
        ]
    },

    // ── MÓDULO 2, LECCIÓN 4 ────────────────────────────────────────────────
    '2-4': {
        moduleId: 2,
        lessonIndex: 3,
        title: 'Mínimos Decrecientes — Presión vendedora',
        duration: '8 min',
        intro: 'Si los máximos decrecientes muestran que los compradores pierden fuerza en los rebotes, los mínimos decrecientes confirman que los vendedores atacan con más fuerza en cada caída. LH + LL es la firma completa de la tendencia bajista.',
        sections: [
            {
                heading: '¿Qué es un mínimo decreciente?',
                blocks: [
                    { type: 'text', content: 'Un <strong>mínimo decreciente (Lower Low, LL)</strong> ocurre cuando el precio cae a un nivel más bajo que el mínimo anterior. Cada nueva caída rompe el suelo anterior. Los vendedores tienen cada vez más control y presionan el precio a cotas más bajas.' },
                    { type: 'chart', id: 'll_definition' },
                    { type: 'concept', title: 'LL: el suelo que cede', content: 'En una tendencia alcista, el suelo (los mínimos de corrección) sube con el mercado. En una tendencia bajista ocurre lo opuesto: el suelo cede en cada caída. Cada LL significa que los compradores que intentaron defender el mínimo anterior han sido superados por la presión vendedora.' },
                ]
            },
            {
                heading: 'LH + LL: la estructura bajista completa',
                blocks: [
                    { type: 'text', content: 'La tendencia bajista se define por la presencia simultánea de <strong>LH y LL</strong>. Esto significa que tanto los rebotes como las caídas van en la misma dirección: abajo. Es la estructura opuesta y simétrica de la tendencia alcista (HH + HL).' },
                    { type: 'chart', id: 'lh_ll_combined' },
                    { type: 'table',
                        headers: ['Patrón', 'Interpretación', 'Acción'],
                        rows: [
                            ['LH + LL', 'Tendencia bajista establecida', 'Evitar longs, buscar cortos en LH'],
                            ['LL sin LH', 'Caída en pánico, posible sobreventa', 'Esperar rebote y ver si forma LH'],
                            ['LH sin LL', 'Resistencia bajista sin caída nueva', 'Observar — puede ser consolidación'],
                            ['HL + HH que rompe LH', 'Primera señal de recuperación', 'Vigilar cambio de tendencia'],
                        ]
                    },
                    { type: 'warning', content: 'La trampa más cara en tendencia bajista es comprar cada LL pensando que "ya no puede caer más". El precio siempre puede caer más. Sin señal de cambio de estructura (ruptura de LH), cada nuevo LL es una continuación, no un suelo.' },
                ]
            },
            {
                heading: 'El LL como zona de stop en cortos',
                blocks: [
                    { type: 'text', content: 'Al igual que el HL define el stop en posiciones largas, el <strong>último LL define el objetivo de precio y el trailing stop en posiciones cortas</strong>. Cuando el precio cae y forma un nuevo LL, bajas el stop para proteger ganancias.' },
                    { type: 'chart', id: 'll_trailing_stop' },
                    { type: 'steps', items: [
                        'Entras corto cerca del LH con stop por encima del último LH',
                        'El precio cae y forma un nuevo LL — la tendencia confirma',
                        'Baja el stop loss al nivel del LH anterior (ahora más bajo)',
                        'En cada nuevo LL + LH, repite el proceso bajando el stop',
                        'Cierra cuando el precio supere el último LH sin formar nuevo LL',
                    ]},
                    { type: 'tip', label: 'GESTIÓN EN BAJISTA', content: 'En tendencias bajistas los movimientos suelen ser más rápidos y violentos que en alcistas. Los stops deben ser más amplios para tolerar los rebotes bruscos (LH). Una buena referencia: stop un 1-2% por encima del último LH identificado en el timeframe de operativa.' },
                ]
            },
            {
                heading: 'Leer la estructura completa de una vez',
                blocks: [
                    { type: 'text', content: 'Con los cuatro conceptos del módulo 2 dominados (HH, HL, LH, LL), puedes leer cualquier gráfico en segundos. La pregunta que debes hacerte siempre que abres un gráfico es la misma: <strong>¿qué secuencia de máximos y mínimos veo?</strong>' },
                    { type: 'chart', id: 'full_structure_read' },
                    { type: 'table',
                        headers: ['Lo que ves', 'Conclusión inmediata'],
                        rows: [
                            ['HH + HL consecutivos', '✅ Tendencia alcista — buscar longs en HL'],
                            ['LH + LL consecutivos', '🔴 Tendencia bajista — evitar longs'],
                            ['HH + LL mezclados', '⚠️ Lateral o transición — esperar claridad'],
                            ['Un HH que no llega al anterior LH', '🔍 Primer signo de debilidad alcista'],
                            ['Un HL que supera el último LH', '🔍 Primer signo de recuperación bajista'],
                        ]
                    },
                    { type: 'concept', title: 'El análisis de estructura es suficiente', content: 'Muchos traders pasan años buscando el indicador perfecto cuando la respuesta estaba en el precio desde el principio. La secuencia HH-HL-LH-LL te dice todo lo que necesitas saber sobre quién controla el mercado en cada momento. Dominar esto es suficiente para tener un edge real.' },
                    { type: 'tip', label: 'EJERCICIO', content: 'Durante una semana, cada vez que abras un gráfico, escribe en papel: "Veo HH/HL/LH/LL — por tanto la tendencia es X — por tanto busco Y". Hazlo antes de mirar indicadores. Después de 50 gráficos, la lectura de estructura será automática.' },
                ]
            },
        ]
    },
    // ── MÓDULO 3, LECCIÓN 1 ────────────────────────────────────────────────
    '3-1': {
        moduleId: 3,
        lessonIndex: 0,
        title: 'Tendencia Alcista — Cómo montarla',
        duration: '9 min',
        intro: 'Montar una tendencia alcista no significa comprar en cualquier momento porque "el mercado sube". Significa identificar el punto exacto de menor riesgo dentro del movimiento y entrar con el viento a favor.',
        sections: [
            {
                heading: 'Las tres fases de una tendencia alcista',
                blocks: [
                    { type: 'text', content: 'Toda tendencia alcista pasa por tres fases bien definidas. Entender en qué fase está el mercado determina completamente cómo debes actuar: si es momento de comprar agresivamente, de gestionar posición existente, o de estar preparado para salir.' },
                    { type: 'chart', id: 'uptrend_phases' },
                    { type: 'steps', items: [
                        '<strong>Fase de Acumulación:</strong> el precio se mueve lateral tras una caída. El volumen es bajo. Los institucionales compran silenciosamente. Difícil de operar en tiempo real.',
                        '<strong>Fase de Tendencia:</strong> el precio rompe al alza con volumen. Se establecen HH y HL claramente. Es la fase donde se gana dinero. La más fácil de operar.',
                        '<strong>Fase de Distribución:</strong> el precio alcanza máximos pero los impulsos son más débiles. El volumen en alzas decrece. Los institucionales venden. Momento de reducir o cerrar.',
                    ]},
                    { type: 'tip', label: 'CLAVE', content: 'La mayoría del dinero se gana en la Fase 2. No intentes adivinar el inicio de la Fase 1 — espera la confirmación de la ruptura y opera la Fase 2 con convicción.' },
                ]
            },
            {
                heading: 'Dónde entrar en tendencia alcista',
                blocks: [
                    { type: 'text', content: 'La tendencia alcista no sube en línea recta. Sube en impulsos y corrige en retrocesos. Los retrocesos son tu oportunidad. La pregunta correcta no es "¿está subiendo?" sino <strong>"¿dónde termina el retroceso y reanuda el alza?"</strong>' },
                    { type: 'chart', id: 'uptrend_entries' },
                    { type: 'table',
                        headers: ['Zona de entrada', 'Riesgo', 'Probabilidad', 'Cuándo usarla'],
                        rows: [
                            ['Retroceso a EMA 21', 'Bajo', 'Alta', 'Tendencia fuerte, primera corrección'],
                            ['Retroceso a SMA 50', 'Medio', 'Media-alta', 'Tendencia establecida, corrección mayor'],
                            ['Retroceso a soporte previo', 'Medio', 'Alta si hay reacción', 'Nivel con historial de rebotes'],
                            ['Ruptura de consolidación', 'Bajo-medio', 'Alta con volumen', 'Tras base lateral en tendencia'],
                        ]
                    },
                    { type: 'warning', content: 'No persigas el precio cuando está lejos de sus medias. Una acción que ha subido un 30% sin corrección tiene riesgo de retroceso inminente. Espera la corrección y entra en la zona de valor, no en el pico.' },
                ]
            },
            {
                heading: 'Gestión de posición en tendencia',
                blocks: [
                    { type: 'text', content: 'Entrar bien es solo la mitad. La otra mitad es <strong>aguantar</strong>. La tendencia alcista está diseñada para sacar a los traders débiles con correcciones normales que asustan pero no invalidan la estructura.' },
                    { type: 'chart', id: 'uptrend_management' },
                    { type: 'concept', title: 'El arte de aguantar', content: 'Las tendencias más rentables son las que duran meses o años. Para aguantar una tendencia larga sin ser sacado por ruido: define tu stop en semanal (no en diario), sube el stop solo cuando se forme un nuevo HL confirmado, y divide la posición — cierra parcialmente en resistencias para reducir estrés psicológico sin salir del todo.' },
                    { type: 'tip', label: 'TRAILING STOP', content: 'En tendencia alcista fuerte, un trailing stop efectivo es colocarlo por debajo del mínimo de cada semana completada. Si cierras el viernes y el precio ha hecho un HL más alto, subes el stop. Simple y elimina la emoción de la gestión.' },
                ]
            },
            {
                heading: 'Señales de agotamiento de tendencia',
                blocks: [
                    { type: 'text', content: 'Ninguna tendencia es eterna. Las señales de agotamiento no significan venta inmediata, pero sí reducción de exposición y mayor vigilancia.' },
                    { type: 'chart', id: 'uptrend_exhaustion' },
                    { type: 'steps', items: [
                        'Impulsos cada vez más cortos en precio y duración',
                        'Correcciones cada vez más profundas (HL que casi toca el HL anterior)',
                        'Volumen decreciente en los impulsos alcistas',
                        'Divergencia bajista en RSI semanal (precio HH, RSI LH)',
                        'Primer cierre semanal por debajo de EMA 21 tras meses de tendencia',
                    ]},
                    { type: 'warning', content: 'Una sola señal de agotamiento no es suficiente para salir. Necesitas al menos dos o tres coincidiendo. Los mercados pueden seguir subiendo con señales de agotamiento durante semanas. Reduce riesgo pero no salgas todo de golpe.' },
                ]
            },
        ]
    },

    // ── MÓDULO 3, LECCIÓN 2 ────────────────────────────────────────────────
    '3-2': {
        moduleId: 3,
        lessonIndex: 1,
        title: 'Tendencia Bajista — Cómo evitarla',
        duration: '8 min',
        intro: 'La regla más rentable del trading no es encontrar el mejor long. Es no estar en el mercado cuando el mercado baja. Preservar capital en tendencias bajistas es lo que separa a los traders que sobreviven de los que no.',
        sections: [
            {
                heading: 'Por qué las tendencias bajistas son distintas',
                blocks: [
                    { type: 'text', content: 'Las tendencias bajistas tienen tres características que las hacen más peligrosas que las alcistas: son <strong>más rápidas</strong> (el miedo mueve más que la codicia), los <strong>rebotes son violentos</strong> (los short-sellers cubren posiciones), y la mayoría de participantes tienen <strong>sesgo largo</strong> (quieren creer que el precio va a recuperar).' },
                    { type: 'chart', id: 'downtrend_characteristics' },
                    { type: 'concept', title: 'El sesgo largo: el enemigo invisible', content: 'La mayoría de traders aprenden a comprar antes que a vender en corto. Cuando el mercado baja, su instinto es buscar "el suelo". Este sesgo hace que muchos compren en cada rebote de una tendencia bajista, perdiendo dinero repetidamente. El antídoto es simple: si la estructura es LH+LL, no hay longs hasta que cambie la estructura.' },
                ]
            },
            {
                heading: 'Identificar tendencia bajista temprano',
                blocks: [
                    { type: 'text', content: 'No esperes a que el mercado haya caído un 30% para reconocer la tendencia bajista. Las señales tempranas están en el precio antes de que la caída sea obvia.' },
                    { type: 'chart', id: 'downtrend_early_signs' },
                    { type: 'steps', items: [
                        'Primer cierre semanal por debajo de SMA 50 tras tendencia alcista',
                        'Rebote que no consigue superar el máximo anterior (primer LH)',
                        'Precio que vuelve a caer y rompe el último mínimo relevante (primer LL)',
                        'EMA 21 que cruza por debajo de SMA 50 (señal técnica clásica)',
                        'Volumen alto en las caídas y bajo en los rebotes',
                    ]},
                    { type: 'tip', label: 'SEÑAL TEMPRANA', content: 'La señal más temprana y fiable es el primer LH confirmado tras una tendencia alcista. No esperes el LL. Cuando el precio no puede recuperar el máximo anterior y empieza a girar, ya tienes la primera prueba de cambio de control. Reduce exposición ahí.' },
                ]
            },
            {
                heading: 'Tres respuestas válidas ante tendencia bajista',
                blocks: [
                    { type: 'text', content: 'Cuando identificas tendencia bajista establecida (LH+LL confirmados), tienes tres opciones válidas. Lo que <em>no</em> es opción válida es ignorarla y mantener longs con la esperanza de recuperación.' },
                    { type: 'chart', id: 'downtrend_responses' },
                    { type: 'table',
                        headers: ['Respuesta', 'Cuándo usarla', 'Resultado esperado'],
                        rows: [
                            ['Salir completamente en cash', 'Bajista claro en todos los TF', 'Preservas capital, pierdes posibles rebotes'],
                            ['Reducir a posición mínima (20-30%)', 'Señales mixtas, incertidumbre', 'Reduces daño, mantienes exposición reducida'],
                            ['Abrir posiciones cortas', 'Estructura bajista clara + catalizador', 'Ganas dinero mientras el mercado cae'],
                        ]
                    },
                    { type: 'warning', content: 'Nunca añadas a una posición perdedora en tendencia bajista. "Promediar a la baja" en un activo en tendencia bajista es la forma más rápida de destruir una cuenta. Cada nuevo LL significa que quien vendió antes tenía razón.' },
                ]
            },
            {
                heading: 'Los rebotes en tendencia bajista',
                blocks: [
                    { type: 'text', content: 'Los rebotes en tendencia bajista son frecuentes, bruscos y engañosos. Pueden durar días o semanas y recuperar el 30-50% de la caída anterior. <strong>No son señales de recuperación</strong> hasta que la estructura cambie.' },
                    { type: 'chart', id: 'downtrend_bounces' },
                    { type: 'concept', title: 'El rebote trampa', content: 'El rebote más peligroso en tendencia bajista es el que ocurre tras una caída muy vertical. El precio sube con fuerza, el sentimiento mejora, los medios empiezan a hablar de recuperación. Pero en un mercado bajista estructural, ese rebote termina formando un LH. Los que compraron en el rebote quedan atrapados de nuevo. El patrón se repite hasta que la estructura cambia de verdad.' },
                    { type: 'tip', label: 'REGLA', content: 'En tendencia bajista, un rebote no es señal de compra hasta que supera el último LH relevante con cierre semanal. Si el rebote falla antes de llegar al LH, es el mercado dándote otra oportunidad de salir o vender en corto.' },
                ]
            },
        ]
    },

    // ── MÓDULO 3, LECCIÓN 3 ────────────────────────────────────────────────
    '3-3': {
        moduleId: 3,
        lessonIndex: 2,
        title: 'Rango Lateral — Paciencia obligatoria',
        duration: '8 min',
        intro: 'El mercado no siempre sube ni baja. La mayor parte del tiempo se mueve en rangos laterales. Operar en lateral sin reconocerlo es la causa de pérdidas que no tienen sentido: el setup parecía perfecto pero el precio no fue a ningún lado.',
        sections: [
            {
                heading: '¿Qué es un rango lateral y por qué se forma?',
                blocks: [
                    { type: 'text', content: 'Un rango lateral (también llamado consolidación, acumulación o distribución) es un período donde el precio se mueve entre dos niveles horizontales sin tendencia clara. Se forman cuando <strong>compradores y vendedores tienen fuerzas equivalentes</strong> y ninguno consigue dominar.' },
                    { type: 'chart', id: 'range_definition' },
                    { type: 'concept', title: 'Tipos de rangos por su función', content: 'No todos los rangos son iguales. Un rango tras una tendencia alcista larga suele ser distribución (los institucionales venden mientras el precio se mantiene). Un rango tras una caída prolongada suele ser acumulación (los institucionales compran). El contexto previo al rango cambia completamente su interpretación.' },
                ]
            },
            {
                heading: 'Cómo identificar un rango válido',
                blocks: [
                    { type: 'text', content: 'Para que un rango sea operable necesita al menos <strong>dos toques claros tanto en el soporte como en la resistencia</strong>. Con un solo toque en cada extremo no hay rango confirmado — hay dos puntos que no garantizan nada.' },
                    { type: 'chart', id: 'range_identification' },
                    { type: 'steps', items: [
                        'El precio toca un nivel y rebota (primer toque de soporte o resistencia)',
                        'El precio va al extremo opuesto y rebota (primer toque del otro extremo)',
                        'El precio vuelve al primer nivel y rebota de nuevo (segundo toque — rango confirmado)',
                        'Cuantos más toques tenga cada nivel, más fiable es el rango',
                        'El rango es válido hasta que el precio lo rompe con cierre fuera del mismo',
                    ]},
                    { type: 'tip', label: 'MEDIDA', content: 'La anchura del rango es importante. Rangos muy estrechos (menos del 5% entre soporte y resistencia) no ofrecen suficiente recorrido para operar con ratio positivo. Busca rangos de al menos 8-10% de amplitud para que la operación tenga sentido.' },
                ]
            },
            {
                heading: 'Estrategias dentro del rango',
                blocks: [
                    { type: 'text', content: 'Dentro de un rango hay dos estrategias principales. Ambas son válidas — depende de tu perfil y del contexto macro.' },
                    { type: 'chart', id: 'range_strategies' },
                    { type: 'table',
                        headers: ['Estrategia', 'Entrada', 'Stop', 'Objetivo', 'Perfil'],
                        rows: [
                            ['Comprar en soporte', 'Toque de soporte + vela de señal', 'Bajo el soporte -1%', 'Resistencia del rango', 'Conservador'],
                            ['Vender en resistencia', 'Toque de resistencia + vela de señal', 'Sobre la resistencia +1%', 'Soporte del rango', 'Conservador'],
                            ['Esperar la ruptura', 'Cierre fuera del rango con volumen', 'Dentro del rango (25%)', 'Proyección = amplitud del rango', 'Agresivo'],
                        ]
                    },
                    { type: 'warning', content: 'Las rupturas falsas de rango son extremadamente comunes. El precio cierra fuera del rango, atrae compradores (o vendedores), y vuelve dentro. Nunca entres en una ruptura sin volumen de confirmación y espera siempre el cierre del período (diario o semanal) fuera del rango antes de entrar.' },
                ]
            },
            {
                heading: 'Cuándo esperar y no operar',
                blocks: [
                    { type: 'text', content: 'La habilidad más infravalorada del trading es saber <strong>cuándo no hacer nada</strong>. En rango lateral sin señal clara, el cash es una posición válida y rentable: no pierde, no genera estrés y te mantiene fresco para la oportunidad real.' },
                    { type: 'chart', id: 'range_patience' },
                    { type: 'concept', title: 'El costo del sobretrading en lateral', content: 'En lateral, cada entrada incorrecta no solo pierde el capital arriesgado — también consume energía mental y comisiones. Un trader que hace 10 operaciones en lateral con 50% de win rate y ratio 1:1 termina en cero antes de comisiones. El mismo trader esperando la ruptura con una sola operación bien ejecutada puede ganar lo que el rango completo proyecta.' },
                    { type: 'tip', label: 'CRITERIO', content: 'Define antes de operar: ¿está el precio en tendencia o en rango? Si estás en rango y no estás cerca del soporte ni de la resistencia — estás en el medio —, no hay operación válida. El medio del rango es tierra de nadie.' },
                ]
            },
        ]
    },

    // ── MÓDULO 3, LECCIÓN 4 ────────────────────────────────────────────────
    '3-4': {
        moduleId: 3,
        lessonIndex: 3,
        title: 'Validación de Líneas de Tendencia',
        duration: '8 min',
        intro: 'Una línea de tendencia mal trazada da señales falsas. Una bien trazada es una de las herramientas más simples y poderosas del análisis técnico. La diferencia está en saber qué conectar y cuándo el precio te confirma que la has dibujado bien.',
        sections: [
            {
                heading: 'Qué es una línea de tendencia válida',
                blocks: [
                    { type: 'text', content: 'Una línea de tendencia alcista conecta dos o más <strong>mínimos relevantes</strong> del precio en ascenso. Una línea de tendencia bajista conecta dos o más <strong>máximos relevantes</strong> en descenso. La línea no puede ser horizontal — eso es soporte o resistencia, no tendencia.' },
                    { type: 'chart', id: 'trendline_valid' },
                    { type: 'concept', title: 'La regla de los tres puntos', content: 'Una línea de tendencia definida por dos puntos es tentativa. Cuando el precio la toca por tercera vez y rebota, la línea está validada. Con tres o más toques, la línea tiene poder predictivo real. Con solo dos puntos, cualquier línea puede ser dibujada y no dice nada.' },
                ]
            },
            {
                heading: 'Cómo trazar líneas correctamente',
                blocks: [
                    { type: 'text', content: 'El error más común es conectar los <em>cuerpos</em> de las velas ignorando las mechas. Las mechas representan movimiento real de precio. La línea debe tocar los <strong>mínimos de mecha</strong> en alcista y los <strong>máximos de mecha</strong> en bajista.' },
                    { type: 'chart', id: 'trendline_drawing' },
                    { type: 'steps', items: [
                        'Identifica los mínimos relevantes (HL) en tendencia alcista o máximos (LH) en bajista',
                        'Conecta el primer y segundo punto con una línea recta',
                        'Extiende la línea hacia el futuro',
                        'Observa si el tercer toque la valida (precio toca y rebota)',
                        'Con tres toques, la línea es operable: entra en el próximo toque con stop bajo la línea',
                    ]},
                    { type: 'warning', content: 'No fuerces la línea para que toque más puntos ajustando el ángulo. Si tienes que "estirar" la línea para que toque el tercer punto, esa línea no existe. Las mejores líneas de tendencia son las que se dibujan solas — los toques son obvios sin manipulación.' },
                ]
            },
            {
                heading: 'Canales de precio',
                blocks: [
                    { type: 'text', content: 'Cuando el precio se mueve entre dos líneas paralelas — una conectando los mínimos y otra los máximos — se forma un <strong>canal de precio</strong>. El canal define con precisión el rango de la tendencia y ofrece zonas de entrada y salida muy claras.' },
                    { type: 'chart', id: 'price_channel' },
                    { type: 'table',
                        headers: ['Tipo de canal', 'Característica', 'Operativa'],
                        rows: [
                            ['Canal alcista', 'Máximos y mínimos crecientes paralelos', 'Compra en línea inferior, vende parcial en superior'],
                            ['Canal bajista', 'Máximos y mínimos decrecientes paralelos', 'Vende en línea superior, cubre en inferior'],
                            ['Canal horizontal', 'Máximos y mínimos al mismo nivel', 'Igual que rango lateral — soporte y resistencia'],
                        ]
                    },
                    { type: 'tip', label: 'CANAL COMO OBJETIVO', content: 'Cuando el precio rompe la línea de tendencia inferior de un canal alcista, el objetivo mínimo de caída es la anchura del canal proyectada hacia abajo. Si el canal mide 15 puntos de anchura y el precio rompe el suelo del canal en 100, el objetivo es 85.' },
                ]
            },
            {
                heading: 'Ruptura de línea de tendencia: ¿cuándo creerla?',
                blocks: [
                    { type: 'text', content: 'Las líneas de tendencia se rompen con frecuencia de forma falsa. El precio las cruza brevemente y vuelve. La clave es distinguir una ruptura real de un spike temporal.' },
                    { type: 'chart', id: 'trendline_break' },
                    { type: 'steps', items: [
                        '<strong>Cierre fuera de la línea:</strong> el precio no solo cruza — cierra el período por fuera',
                        '<strong>Volumen:</strong> la ruptura viene acompañada de volumen superior a la media',
                        '<strong>Retest fallido:</strong> el precio vuelve a la línea, la toca desde el otro lado y rebota',
                        '<strong>Cambio de estructura:</strong> además de romper la línea, el precio forma el primer LH (en alcista) o HH (en bajista)',
                    ]},
                    { type: 'concept', title: 'La línea rota se convierte en nivel opuesto', content: 'Cuando una línea de tendencia alcista se rompe a la baja, pasa a actuar como resistencia en el rebote posterior. Este fenómeno de polaridad también funciona en líneas de tendencia, no solo en soportes y resistencias horizontales. Cuando el precio retestea la línea rota desde abajo y la rechaza, es la señal de entrada más fiable para posiciones cortas tras una ruptura bajista.' },
                ]
            },
        ]
    },
    // ── MÓDULO 4, LECCIÓN 1 ────────────────────────────────────────────────
    '4-1': {
        moduleId: 4,
        lessonIndex: 0,
        title: 'Soporte Fresco — Primera vez testeado',
        duration: '9 min',
        intro: 'Un soporte fresco es el nivel más poderoso que existe. Nadie ha sido quemado ahí todavía. Los compradores que lo crearon siguen en posición y defenderán ese precio con fuerza cuando el mercado regrese.',
        sections: [
            {
                heading: '¿Qué hace que un soporte sea "fresco"?',
                blocks: [
                    { type: 'text', content: 'Un soporte fresco se forma cuando el precio rebota desde un nivel por <strong>primera vez</strong>. No ha sido testeado antes. Esto significa que todos los compradores que entraron en esa zona siguen en posición con ganancias — y cuando el precio regrese, tienen un incentivo fuerte para defender ese nivel y mantener sus ganancias.' },
                    { type: 'chart', id: 'fresh_support_formation' },
                    { type: 'concept', title: 'La memoria del mercado', content: 'El mercado tiene memoria. Los participantes recuerdan dónde el precio rebotó con fuerza. Cuando el precio regresa a esa zona, los mismos actores que compraron antes vuelven a comprar — algunos añadiendo a posiciones ganadoras, otros que no pudieron entrar la primera vez y ahora tienen su oportunidad. Esta memoria colectiva es lo que hace que los niveles funcionen.' },
                ]
            },
            {
                heading: 'Cómo se forma un soporte fresco',
                blocks: [
                    { type: 'text', content: 'La formación de soporte requiere una secuencia específica que te indica cuándo un nivel tiene verdadero respaldo institucional detrás.' },
                    { type: 'chart', id: 'fresh_support_formation_2' },
                    { type: 'steps', items: [
                        'El precio cae hasta un nivel donde aparecen compradores agresivos',
                        'Se forma una vela de reversión clara: pin bar, engulfing alcista, o cierre fuerte en máximos',
                        'El precio sube desde ese nivel con fuerza — cuanto más fuerte el rebote, mejor el soporte',
                        'El nivel queda marcado como el primer toque de soporte',
                        'Cuando el precio regresa a esa zona, el soporte está "activo" — es operable',
                    ]},
                    { type: 'tip', label: 'CALIDAD', content: 'La calidad de un soporte fresco se mide por la fuerza del rebote original. Un precio que cae al soporte y sube un 15% desde ahí es mucho más poderoso que uno que sube un 3%. El rebote inicial te dice cuántos compradores entraron y con cuánta convicción.' },
                ]
            },
            {
                heading: 'Entrada en soporte fresco',
                blocks: [
                    { type: 'text', content: 'La entrada en soporte fresco es una de las operaciones de mayor probabilidad disponibles. El riesgo es bajo (stop bajo el soporte) y el potencial es alto (precio libre de resistencias entre el soporte y el máximo anterior).' },
                    { type: 'chart', id: 'fresh_support_entry' },
                    { type: 'table',
                        headers: ['Tipo de entrada', 'Cuándo', 'Stop', 'Objetivo mínimo'],
                        rows: [
                            ['Anticipada', 'Precio toca la zona del soporte', 'Bajo el soporte -1%', 'Máximo anterior'],
                            ['Confirmada', 'Vela de señal alcista en el soporte', 'Bajo la vela de señal', 'Máximo anterior'],
                            ['Conservadora', 'Cierre por encima del primer HL tras el toque', 'Bajo el HL', 'Máximo anterior'],
                        ]
                    },
                    { type: 'warning', content: 'Un soporte fresco solo es fresco una vez. Después del primer retest, pasa a ser soporte testeado — sigue siendo válido pero con menos fuerza. Si el nivel es testeado muchas veces sin romperse, paradójicamente se debilita: cada toque consume a los compradores disponibles en esa zona.' },
                ]
            },
            {
                heading: 'Diferencia entre soporte fresco y zona consolidada',
                blocks: [
                    { type: 'text', content: 'No todos los soportes son iguales. Un soporte fresco tiene la máxima potencia. Una zona de consolidación previa también actúa como soporte pero por razones distintas: el precio ha pasado mucho tiempo ahí y muchos participantes tienen posiciones referenciadas a esos niveles.' },
                    { type: 'chart', id: 'fresh_vs_consolidated' },
                    { type: 'concept', title: 'Por qué la consolidación actúa como soporte', content: 'Cuando el precio consolida durante semanas en un rango, se crean millones de órdenes referenciadas a esos niveles: stops de vendedores, órdenes de compra pendientes, posiciones abiertas. Cuando el precio vuelve a esa zona, toda esa liquidez se activa simultáneamente. El efecto es similar al soporte fresco pero por un mecanismo diferente.' },
                ]
            },
        ]
    },

    // ── MÓDULO 4, LECCIÓN 2 ────────────────────────────────────────────────
    '4-2': {
        moduleId: 4,
        lessonIndex: 1,
        title: 'Resistencia Mayor — Donde venden los grandes',
        duration: '9 min',
        intro: 'Las resistencias mayores no son líneas dibujadas en un gráfico. Son zonas donde el dinero institucional tiene posiciones abiertas y necesita vender para cerrarlas. Entender esto cambia cómo interactúas con esos niveles.',
        sections: [
            {
                heading: 'Por qué existe la resistencia',
                blocks: [
                    { type: 'text', content: 'Una resistencia se forma porque en ese nivel hubo <strong>vendedores con más fuerza que los compradores</strong>. El precio subió hasta ahí, los vendedores entraron masivamente, y el precio tuvo que retroceder. Todos los que compraron por encima de ese nivel en el pasado están en pérdidas y esperan que el precio vuelva para salir sin pérdida — eso crea presión vendedora adicional cuando el precio sube de nuevo.' },
                    { type: 'chart', id: 'resistance_why' },
                    { type: 'concept', title: 'El "overhead supply"', content: 'Overhead supply (oferta por encima) es el término institucional para describir la presión vendedora acumulada por encima del precio actual. Cada máximo anterior tiene overhead supply: los traders que compraron ahí y están en pérdidas. Cuanto más tiempo el precio ha estado por debajo de un nivel, más overhead supply se acumula y más difícil es para el precio superarlo.' },
                ]
            },
            {
                heading: 'Tipos de resistencia por importancia',
                blocks: [
                    { type: 'text', content: 'No todas las resistencias son iguales. La importancia de una resistencia depende de <strong>cuántos participantes tienen posiciones referenciadas a ese nivel</strong> y en cuántos timeframes es visible.' },
                    { type: 'chart', id: 'resistance_types' },
                    { type: 'table',
                        headers: ['Tipo', 'Formación', 'Fuerza', 'Timeframe'],
                        rows: [
                            ['Máximo histórico (ATH)', 'Nunca superado antes', '⭐⭐⭐⭐⭐', 'Todos'],
                            ['Máximo de varios años', 'Superado hace 2+ años', '⭐⭐⭐⭐', 'Mensual/Semanal'],
                            ['Resistencia de tendencia bajista', 'LH reciente en bajista', '⭐⭐⭐', 'Semanal/Diario'],
                            ['Resistencia de rango actual', 'Techo del rango lateral', '⭐⭐', 'Diario'],
                            ['Resistencia intradiaria', 'Máximo de sesión', '⭐', 'Horario/Menor'],
                        ]
                    },
                    { type: 'tip', label: 'PRIORIDAD', content: 'Cuando una resistencia es visible en múltiples timeframes simultáneamente — por ejemplo, es el techo del rango diario Y un máximo relevante semanal Y coincide con un nivel de fibonacci —, su fuerza se multiplica. Estos son los niveles donde los institucionales colocan sus órdenes más grandes.' },
                ]
            },
            {
                heading: 'Operar cerca de resistencia mayor',
                blocks: [
                    { type: 'text', content: 'Acercarse a una resistencia mayor cambia las reglas del juego. Si tienes una posición larga que se aproxima a una resistencia importante, debes decidir: <strong>tomar ganancias, reducir, o aguantar y esperar la ruptura.</strong>' },
                    { type: 'chart', id: 'resistance_trading' },
                    { type: 'steps', items: [
                        'Marca la resistencia antes de entrar — no la descubras cuando ya estás en posición',
                        'Reduce el 50% de la posición cuando el precio llega a 2-3% de la resistencia',
                        'Mantén el 50% restante con stop ajustado, esperando ver si rompe o rechaza',
                        'Si el precio rechaza la resistencia con volumen, cierra el resto',
                        'Si el precio consolida bajo la resistencia con volumen decreciente, puede preparar ruptura',
                    ]},
                    { type: 'warning', content: 'Nunca añadas a una posición larga cuando el precio está pegado a una resistencia mayor sin haberla roto todavía. El riesgo/recompensa es desfavorable: poco potencial alcista (ya estás en la resistencia) y riesgo de rechazo significativo.' },
                ]
            },
            {
                heading: 'La ruptura de resistencia mayor',
                blocks: [
                    { type: 'text', content: 'Cuando una resistencia mayor se rompe con convicción, cambia el comportamiento de miles de participantes simultáneamente. Los vendedores que apostaban por esa resistencia cubren posiciones (comprando), los compradores que esperaban la ruptura entran, y los stops de los cortos saltan. El resultado es un movimiento explosivo.' },
                    { type: 'chart', id: 'resistance_breakout' },
                    { type: 'concept', title: 'Polaridad: la resistencia se convierte en soporte', content: 'Una vez rota con fuerza y volumen, la resistencia deja de ser resistencia y pasa a ser soporte. Este cambio de función — polaridad — es uno de los principios más fiables del análisis técnico. El nivel que antes frenó el precio al alza, ahora lo sostiene cuando el precio regresa a testear.' },
                ]
            },
        ]
    },

    // ── MÓDULO 4, LECCIÓN 3 ────────────────────────────────────────────────
    '4-3': {
        moduleId: 4,
        lessonIndex: 2,
        title: 'Marcado de Zonas — Técnica profesional',
        duration: '8 min',
        intro: 'Dibujar niveles es fácil. Dibujar los niveles correctos es un arte. La mayoría de traders acaban con gráficos llenos de líneas que no dicen nada. Un profesional tiene cuatro o cinco niveles clave y sabe exactamente qué esperar en cada uno.',
        sections: [
            {
                heading: 'Zona vs nivel: diferencia fundamental',
                blocks: [
                    { type: 'text', content: 'El precio no respeta líneas exactas — respeta <strong>zonas</strong>. Una zona tiene un rango de precio, no un número exacto. Dibujar una línea fina como soporte es un error: el precio puede entrar en la zona por encima o por debajo de la línea y seguir siendo válida.' },
                    { type: 'chart', id: 'zone_vs_level' },
                    { type: 'concept', title: 'Cómo definir el ancho de una zona', content: 'El ancho de una zona depende del timeframe: en mensual, una zona puede tener 3-5% de amplitud. En semanal, 1-2%. En diario, 0.5-1%. La zona la define el rango de precio donde el mercado tomó la decisión de cambiar de dirección: desde donde empezó el rechazo hasta donde terminó la vela de señal.' },
                ]
            },
            {
                heading: 'Los cuatro tipos de zona que importan',
                blocks: [
                    { type: 'text', content: 'No todo en un gráfico merece ser marcado. Hay cuatro tipos de zona que realmente tienen peso predictivo y merecen tu atención:' },
                    { type: 'chart', id: 'zone_types' },
                    { type: 'steps', items: [
                        '<strong>Zona de oferta (resistencia):</strong> donde el precio cayó rápido desde un nivel. Los vendedores que crearon esa caída volverán a vender cuando el precio regrese.',
                        '<strong>Zona de demanda (soporte):</strong> donde el precio subió rápido desde un nivel. Los compradores que crearon ese impulso volverán a comprar en el retest.',
                        '<strong>Zona de consolidación previa:</strong> rango donde el precio pasó mucho tiempo. Tiene muchas órdenes acumuladas — actúa como S/R cuando el precio regresa.',
                        '<strong>Nivel psicológico redondo:</strong> 100, 150, 200, 500... Los humanos anclan precios en números redondos. Los institucionales colocan órdenes en masa en estos niveles.',
                    ]},
                ]
            },
            {
                heading: 'Proceso de marcado profesional',
                blocks: [
                    { type: 'text', content: 'El proceso de marcado correcto es <strong>de mayor a menor timeframe</strong>. Primero marcas los niveles del mensual, luego los del semanal, luego los del diario. Los niveles del mensual tienen más peso que los del semanal, y los del semanal más que los del diario.' },
                    { type: 'chart', id: 'zone_marking_process' },
                    { type: 'table',
                        headers: ['Paso', 'Timeframe', 'Qué marcar', 'Color sugerido'],
                        rows: [
                            ['1', 'Mensual', 'Máximos/mínimos históricos, grandes rangos', 'Rojo/Verde brillante'],
                            ['2', 'Semanal', 'HH/HL/LH/LL relevantes, zonas de rechazo fuertes', 'Naranja/Azul'],
                            ['3', 'Diario', 'Zonas de oferta/demanda recientes, consolidaciones', 'Amarillo/Teal'],
                            ['4', 'Eliminar', 'Todo nivel redundante o demasiado cercano a otro', '—'],
                        ]
                    },
                    { type: 'tip', label: 'LIMPIEZA', content: 'Si tu gráfico tiene más de 6-7 zonas marcadas, tienes demasiadas. Cada zona adicional reduce la claridad y aumenta la parálisis. Quédate solo con las zonas que, si el precio llega ahí, sabes exactamente qué harás. Si no sabes qué harías, esa zona no está justificada.' },
                ]
            },
            {
                heading: 'Actualizar niveles regularmente',
                blocks: [
                    { type: 'text', content: 'Los niveles no son estáticos. Cada semana el mercado crea nuevos niveles relevantes y los anteriores pierden vigencia. El análisis técnico requiere <strong>actualización continua</strong>, no un análisis puntual guardado en plantilla.' },
                    { type: 'chart', id: 'zone_update' },
                    { type: 'steps', items: [
                        'Cada domingo, revisa los niveles marcados de la semana anterior',
                        'Elimina los niveles que el precio ya ha roto y dejado atrás claramente',
                        'Añade los nuevos niveles creados durante la semana (nuevos HH, nuevas zonas de rechazo)',
                        'Verifica que las zonas clave del mensual y semanal siguen siendo relevantes',
                        'Anota en qué zona está el precio actualmente y qué esperas si llega al siguiente nivel',
                    ]},
                    { type: 'warning', content: 'Un error común es mantener niveles del pasado indefinidamente porque "algún día el precio puede volver ahí". Si el precio ha estado más de un año lejos de un nivel y no hay contexto técnico relevante, ese nivel ya no tiene peso. Límpialo.' },
                ]
            },
        ]
    },

    // ── MÓDULO 4, LECCIÓN 4 ────────────────────────────────────────────────
    '4-4': {
        moduleId: 4,
        lessonIndex: 3,
        title: 'Niveles con Múltiples Toques',
        duration: '9 min',
        intro: 'Cada vez que el precio toca un nivel y lo respeta, ese nivel gana credibilidad. Pero hay un punto de inflexión: demasiados toques sin ruptura empiezan a debilitar el nivel. Entender esta dinámica te separa del trader que mecanicamente compra en soporte.',
        sections: [
            {
                heading: 'Por qué los toques múltiples refuerzan un nivel',
                blocks: [
                    { type: 'text', content: 'Cada vez que el precio llega a un nivel y lo respeta, más participantes toman nota de ese nivel. Se crea un <strong>efecto de atención creciente</strong>: en el primer toque solo los que participaron en la formación original reaccionan; en el segundo, se añaden los que vieron el primer rebote; en el tercero, ya hay traders de todo tipo esperando el nivel.' },
                    { type: 'chart', id: 'multiple_touches_strength' },
                    { type: 'concept', title: 'Self-fulfilling prophecy', content: 'Los niveles técnicos tienen un componente de profecía autocumplida: cuantos más traders los marcan y esperan reacciones en ellos, más probable es que el precio reaccione en esos niveles. Esto no hace el análisis técnico "falso" — lo hace más poderoso. Los niveles con más seguidores son los que más tienden a funcionar.' },
                ]
            },
            {
                heading: 'La paradoja del nivel muy testeado',
                blocks: [
                    { type: 'text', content: 'Aquí viene el concepto contra-intuitivo: <strong>un nivel testeado 5 veces no es cinco veces más fuerte que uno testeado una vez — puede ser más débil.</strong> Cada toque consume compradores disponibles en esa zona. Después de muchos toques, los compradores originales ya han agotado su capacidad de compra.' },
                    { type: 'chart', id: 'multiple_touches_paradox' },
                    { type: 'steps', items: [
                        '<strong>1-2 toques:</strong> soporte fresco o semi-fresco. Alta fuerza. Los compradores originales siguen activos.',
                        '<strong>3-4 toques:</strong> soporte establecido. Fuerza media-alta. El nivel es conocido, hay atención creciente.',
                        '<strong>5-6 toques:</strong> soporte maduro. Fuerza media. Los compradores originales van agotándose.',
                        '<strong>7+ toques:</strong> soporte debilitado. Mayor probabilidad de ruptura en el siguiente test.',
                    ]},
                    { type: 'tip', label: 'SEÑAL', content: 'Cuando el precio llega al soporte por cuarta o quinta vez pero el rebote es más débil que los anteriores (el precio no sube tanto ni tan rápido), es una señal de agotamiento del soporte. Ese soporte está a punto de romperse. Reduce exposición o ajusta el stop muy cerca.' },
                ]
            },
            {
                heading: 'Volumen en los toques: el indicador definitivo',
                blocks: [
                    { type: 'text', content: 'El volumen en cada toque del nivel te dice si los compradores (en soporte) o vendedores (en resistencia) siguen activos o se están agotando. Es el dato más importante para evaluar la salud de un nivel con múltiples toques.' },
                    { type: 'chart', id: 'multiple_touches_volume' },
                    { type: 'table',
                        headers: ['Volumen en el toque', 'Interpretación', 'Acción'],
                        rows: [
                            ['Alto y creciente en cada toque', 'Compradores activos y comprometidos', 'El soporte aguantará — comprar con confianza'],
                            ['Alto en primer toque, decreciente', 'Compradores agotándose gradualmente', 'Reducir tamaño en cada entrada sucesiva'],
                            ['Bajo en múltiples toques', 'Nivel ignorado por institucionales', 'Soporte frágil — solo stops muy ajustados'],
                            ['Pico de volumen con mala reacción', 'Compradores absorbidos por vendedores', 'Ruptura inminente — no entrar en largo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Ruptura de nivel multi-testeado',
                blocks: [
                    { type: 'text', content: 'La ruptura de un nivel que ha resistido múltiples toques suele ser especialmente potente. Se han acumulado muchos stops por debajo del soporte (de todos los que compraron en los toques anteriores) y cuando el precio los rompe, se ejecutan todos simultáneamente, acelerando la caída.' },
                    { type: 'chart', id: 'multiple_touches_break' },
                    { type: 'concept', title: 'Stop hunt antes de la ruptura real', content: 'Un patrón muy común antes de la ruptura definitiva de un nivel multi-testeado: el precio hace un spike fugaz por debajo del soporte (ejecutando los stops de los más ajustados), vuelve a subir brevemente, y luego rompe definitivamente. Este movimiento — llamado stop hunt o barrido de liquidez — es diseñado para eliminar a los compradores débiles antes de la caída real.' },
                    { type: 'warning', content: 'No pongas tu stop en el nivel exacto del soporte cuando hay múltiples toques previos. Todos saben dónde está ese nivel y los stops se amontonan ahí. Un spike de 0.3-0.5% por debajo puede ejecutar tu stop antes de que el precio se recupere. Añade siempre un colchón de seguridad.' },
                ]
            },
        ]
    },
    // ── MÓDULO 5, LECCIÓN 1 ────────────────────────────────────────────────
    '5-1': {
        moduleId: 5,
        lessonIndex: 0,
        title: 'Zonas de Demanda',
        duration: '9 min',
        intro: 'Las zonas de demanda son donde el dinero institucional compra. No son soportes cualquiera — son niveles donde hubo una orden tan grande que el precio salió disparado desde ahí. Cuando el precio regresa, esa orden puede seguir activa.',
        sections: [
            {
                heading: 'Oferta y demanda: la base de todo',
                blocks: [
                    { type: 'text', content: 'El precio de cualquier activo se mueve por una razón y solo una: el desequilibrio entre <strong>oferta y demanda</strong>. Cuando hay más compradores que vendedores al precio actual, el precio sube para encontrar nuevos vendedores. Cuando hay más vendedores, baja para encontrar compradores. El análisis de oferta y demanda busca identificar dónde están los grandes desequilibrios.' },
                    { type: 'chart', id: 'supply_demand_basics' },
                    { type: 'concept', title: 'Por qué los institucionales dejan huellas', content: 'Un fondo institucional no puede comprar 10 millones de acciones en un instante sin mover el precio en su contra. Divide la orden en partes y las ejecuta a lo largo del tiempo en una zona de precio específica. El resultado visible en el gráfico: el precio cae lentamente hasta una zona, luego sube agresivamente. Esa zona es donde estaba la orden institucional.' },
                ]
            },
            {
                heading: 'Cómo identificar una zona de demanda',
                blocks: [
                    { type: 'text', content: 'Una zona de demanda válida tiene una firma específica: <strong>el precio llega a la zona de forma controlada y sale de ella de forma explosiva</strong>. La salida explosiva es la prueba de que había una orden grande esperando.' },
                    { type: 'chart', id: 'demand_zone_identification' },
                    { type: 'steps', items: [
                        'Busca un movimiento alcista fuerte y rápido (impulso)',
                        'Traza hacia atrás desde la base del impulso',
                        'La zona de demanda es el último rango lateral antes del impulso (la "base")',
                        'El techo de la zona = el máximo de la última vela bajista antes del impulso',
                        'El suelo de la zona = el mínimo de esa misma vela bajista (o el mínimo de la base)',
                    ]},
                    { type: 'tip', label: 'CALIDAD', content: 'Las mejores zonas de demanda son las que han sido visitadas solo una vez (zonas frescas) y de las que el precio salió con una sola vela grande alcista — no con varias velas mediocres. Un impulso de una sola vela que representa el 3-5% de movimiento indica una orden institucional enorme.' },
                ]
            },
            {
                heading: 'Tipos de zonas de demanda',
                blocks: [
                    { type: 'text', content: 'No todas las zonas de demanda se forman igual. Cada patrón de formación tiene un nombre y una ligera diferencia en cómo debes operarla:' },
                    { type: 'chart', id: 'demand_zone_types' },
                    { type: 'table',
                        headers: ['Patrón', 'Formación', 'Fuerza'],
                        rows: [
                            ['Rally-Base-Rally (RBR)', 'Subida → pausa lateral → nueva subida', '⭐⭐⭐ Alta'],
                            ['Drop-Base-Rally (DBR)', 'Caída → pausa lateral → subida fuerte', '⭐⭐⭐⭐⭐ Muy alta'],
                            ['Rally-Base directo', 'Subida sin pausa visible, solo velas de compresión', '⭐⭐ Media'],
                        ]
                    },
                    { type: 'tip', label: 'DBR', content: 'El patrón Drop-Base-Rally es el más poderoso. El precio cae (creando pánico), se estabiliza brevemente (los institucionales acumulan silenciosamente mientras el retail vende con miedo), y luego sube con fuerza explosiva. La base tras la caída es la zona de demanda más limpia que existe.' },
                ]
            },
            {
                heading: 'Entrar en zona de demanda',
                blocks: [
                    { type: 'text', content: 'La entrada en zona de demanda requiere que el precio regrese a la zona sin haberla visitado antes. El retest de una zona de demanda fresca tiene una de las mayores probabilidades de éxito en el análisis técnico.' },
                    { type: 'chart', id: 'demand_zone_entry' },
                    { type: 'steps', items: [
                        'Identifica la zona de demanda (techo y suelo de la base pre-impulso)',
                        'Espera que el precio regrese a la zona en un retroceso natural',
                        'Entra cuando el precio toca el techo de la zona (entrada agresiva) o cuando muestra reacción (conservadora)',
                        'Stop loss por debajo del suelo de la zona — si la zona se rompe, la demanda ya no está ahí',
                        'Objetivo: el impulso original y más allá si la tendencia es alcista',
                    ]},
                    { type: 'warning', content: 'Una zona de demanda que ha sido visitada múltiples veces pierde su efectividad. Si el precio ha estado dentro de la zona más de una o dos veces, la orden institucional original probablemente ya se ha llenado. No la operes como si fuera fresca.' },
                ]
            },
        ]
    },

    // ── MÓDULO 5, LECCIÓN 2 ────────────────────────────────────────────────
    '5-2': {
        moduleId: 5,
        lessonIndex: 1,
        title: 'Zonas de Oferta',
        duration: '9 min',
        intro: 'Las zonas de oferta son el espejo exacto de las zonas de demanda. Son donde el dinero institucional vende — no de golpe, sino acumulando posiciones cortas silenciosamente mientras el precio se estabiliza, hasta que la presión es tan grande que el precio colapsa.',
        sections: [
            {
                heading: 'La firma de la zona de oferta',
                blocks: [
                    { type: 'text', content: 'Una zona de oferta se identifica por la firma opuesta a la demanda: <strong>el precio sube hacia la zona de forma ordenada y cae desde ella de forma explosiva</strong>. La caída explosiva es la prueba de que había órdenes de venta masivas acumuladas en esa zona.' },
                    { type: 'chart', id: 'supply_zone_identification' },
                    { type: 'concept', title: 'Por qué el precio cae desde la oferta', content: 'Cuando un institucional quiere vender una posición enorme, necesita que haya suficientes compradores al otro lado. Espera que el precio suba hasta una zona donde hay liquidez compradora (stops de cortos, órdenes de compra pendientes) y vende ahí masivamente. El precio no puede absorber tanta oferta y colapsa. Eso es una zona de oferta.' },
                ]
            },
            {
                heading: 'Identificar zonas de oferta válidas',
                blocks: [
                    { type: 'text', content: 'La técnica es idéntica a la de demanda pero al revés. Buscas la base que precede a una caída explosiva:' },
                    { type: 'chart', id: 'supply_zone_types' },
                    { type: 'steps', items: [
                        'Busca una caída fuerte y rápida (impulso bajista)',
                        'Traza hacia atrás desde el inicio de la caída',
                        'La zona de oferta es el último rango lateral antes de la caída (la "base")',
                        'El suelo de la zona = el mínimo de la última vela alcista antes de la caída',
                        'El techo de la zona = el máximo de esa misma vela (o el máximo de la base)',
                    ]},
                    { type: 'table',
                        headers: ['Patrón', 'Formación', 'Fuerza'],
                        rows: [
                            ['Drop-Base-Drop (DBD)', 'Caída → pausa lateral → nueva caída', '⭐⭐⭐ Alta'],
                            ['Rally-Base-Drop (RBD)', 'Subida → pausa lateral → caída fuerte', '⭐⭐⭐⭐⭐ Muy alta'],
                            ['Drop-Base directo', 'Caída sin pausa visible', '⭐⭐ Media'],
                        ]
                    },
                ]
            },
            {
                heading: 'Operar el retest de zona de oferta',
                blocks: [
                    { type: 'text', content: 'Cuando el precio regresa a una zona de oferta desde abajo, entra en el territorio donde los institucionales tienen órdenes de venta pendientes. El precio entra, los vendedores se activan, y el precio vuelve a caer. Esta es la operación más limpia en un mercado bajista.' },
                    { type: 'chart', id: 'supply_zone_entry' },
                    { type: 'tip', label: 'ENTRADA', content: 'La entrada conservadora en zona de oferta es esperar que el precio entre en la zona, muestre una vela bajista de señal (cierre bajo la apertura, preferiblemente con mecha superior larga), y vender en el cierre de esa vela. Stop por encima del techo de la zona. Objetivo: el inicio del impulso bajista original.' },
                    { type: 'warning', content: 'No vendas en corto antes de que el precio llegue a la zona. Muchos traders anticipan el rechazo y entran demasiado pronto. El precio puede seguir subiendo durante días antes de llegar a la zona. Paciencia: espera el nivel, no anticipes el movimiento.' },
                ]
            },
            {
                heading: 'Zonas de oferta en tendencia alcista',
                blocks: [
                    { type: 'text', content: 'Las zonas de oferta no solo son para cortos. En tendencia alcista, cada zona de oferta que el precio rompe se convierte en una zona de demanda potencial en el siguiente retroceso. <strong>La oferta rota se convierte en demanda.</strong>' },
                    { type: 'chart', id: 'supply_becomes_demand' },
                    { type: 'concept', title: 'El ciclo oferta-demanda en tendencia', content: 'En una tendencia alcista sana el precio asciende rompiendo zonas de oferta una a una. Cada zona rota deja de ser resistencia y pasa a ser soporte en el siguiente retroceso. El trader que entiende esto opera: compra en los retrocesos a zonas de oferta rotas, con stop bajo la zona y objetivo en la siguiente zona de oferta por encima.' },
                ]
            },
        ]
    },

    // ── MÓDULO 5, LECCIÓN 3 ────────────────────────────────────────────────
    '5-3': {
        moduleId: 5,
        lessonIndex: 2,
        title: 'Áreas de Rechazo',
        duration: '8 min',
        intro: 'Un área de rechazo es la señal más inmediata que el precio da de que un nivel importa. No necesitas semanas de historia — un rechazo fuerte en tiempo real te dice que hay órdenes activas en ese nivel ahora mismo.',
        sections: [
            {
                heading: '¿Qué es un área de rechazo?',
                blocks: [
                    { type: 'text', content: 'Un área de rechazo se forma cuando el precio llega a un nivel y <strong>vuelve agresivamente en la dirección contraria</strong>. La velocidad y fuerza del rechazo indica la magnitud de las órdenes que estaban esperando en ese nivel. Un rechazo débil puede ser ignorado; un rechazo fuerte con volumen es una señal operativa inmediata.' },
                    { type: 'chart', id: 'rejection_area_definition' },
                    { type: 'concept', title: 'Rechazo vs rebote normal', content: 'La diferencia entre un rechazo y un simple rebote está en la velocidad y la vela resultante. Un rechazo produce velas con mechas largas — el precio intentó ir en una dirección, fue rechazado con fuerza, y cerró lejos de donde intentó llegar. Un rebote normal tiene cuerpos pequeños y movimiento gradual. Cuanto más larga la mecha del rechazo y más cercano el cierre al extremo opuesto, más potente la señal.' },
                ]
            },
            {
                heading: 'Tipos de rechazo y su potencia',
                blocks: [
                    { type: 'text', content: 'No todos los rechazos son iguales. Su potencia depende de tres factores: la longitud de la mecha, el tamaño del cuerpo y el contexto en que aparecen.' },
                    { type: 'chart', id: 'rejection_types' },
                    { type: 'table',
                        headers: ['Tipo', 'Características', 'Potencia', 'Contexto ideal'],
                        rows: [
                            ['Pin bar extremo', 'Mecha >3x cuerpo, cierre en extremo opuesto', '⭐⭐⭐⭐⭐', 'En zona de S/R o demanda/oferta'],
                            ['Engulfing', 'Vela que envuelve la anterior completamente', '⭐⭐⭐⭐', 'Tras movimiento extendido'],
                            ['Doji en extremo', 'Apertura ≈ cierre en nivel clave', '⭐⭐⭐', 'En resistencia/soporte claro'],
                            ['Mecha larga sin pin', 'Shadow >1.5x cuerpo, cierre medio', '⭐⭐', 'Confirmación adicional necesaria'],
                        ]
                    },
                    { type: 'tip', label: 'CONTEXTO', content: 'Un pin bar perfecto en medio de una tendencia sin nivel claro vale poco. El mismo pin bar en una zona de demanda fresca, en soporte semanal, con tendencia alcista mensual, vale muchísimo. La potencia del rechazo se multiplica por el número de factores confluentes.' },
                ]
            },
            {
                heading: 'Leer rechazos en tiempo real',
                blocks: [
                    { type: 'text', content: 'La habilidad de leer rechazos en tiempo real te permite actuar antes de que la vela cierre. A medida que se forma la mecha, estás viendo el rechazo ocurrir en directo — el precio intentando ir en una dirección y siendo empujado de vuelta.' },
                    { type: 'chart', id: 'rejection_realtime' },
                    { type: 'steps', items: [
                        'El precio llega a una zona de interés (S/R, demanda/oferta, nivel psicológico)',
                        'La mecha empieza a formarse — el precio se adentra en la zona y empieza a volver',
                        'Observa si el cuerpo de la vela se está formando lejos del extremo de la mecha',
                        'Si el cuerpo confirma el rechazo (cierre fuerte en la dirección opuesta a la mecha), es operativo',
                        'Entra en el cierre de la vela de rechazo con stop justo más allá del extremo de la mecha',
                    ]},
                    { type: 'warning', content: 'No entres antes de que la vela cierre. Lo que parece un pin bar con 2 horas restantes puede convertirse en una vela envolvente bajista al cierre. El mercado tiene tiempo de cambiar. Espera el cierre del período para confirmar la forma final de la vela.' },
                ]
            },
            {
                heading: 'Rechazos en múltiples timeframes',
                blocks: [
                    { type: 'text', content: 'Cuando el mismo nivel produce rechazos visibles en múltiples timeframes simultáneamente, la señal es especialmente potente. Un pin bar en diario que coincide con una mecha larga en semanal en el mismo nivel es una de las mejores señales disponibles.' },
                    { type: 'chart', id: 'rejection_multi_tf' },
                    { type: 'concept', title: 'Cascada de rechazos', content: 'Una cascada de rechazos ocurre cuando el precio es rechazado de un nivel en mensual, luego en semanal, y finalmente en diario, todo en el mismo período de tiempo. Cada rechazo en un timeframe menor confirma la presión vendedora del timeframe mayor. Este alineamiento produce movimientos muy direccionales y sostenidos.' },
                ]
            },
        ]
    },

    // ── MÓDULO 5, LECCIÓN 4 ────────────────────────────────────────────────
    '5-4': {
        moduleId: 5,
        lessonIndex: 3,
        title: 'Formación de Base',
        duration: '9 min',
        intro: 'Una base no es solo una consolidación aburrida. Es el período donde se acumula la energía para el próximo movimiento. Aprender a leer bases te da ventaja sobre el 90% de los traders que solo reaccionan cuando el movimiento ya ha comenzado.',
        sections: [
            {
                heading: '¿Qué es una base y por qué se forma?',
                blocks: [
                    { type: 'text', content: 'Una base es un período de movimiento lateral comprimido que se forma mientras los institucionales acumulan (base alcista) o distribuyen (base bajista) posiciones. Desde afuera parece que el precio "no hace nada". Por dentro, se está produciendo una transferencia masiva de acciones entre manos débiles y manos fuertes.' },
                    { type: 'chart', id: 'base_formation_what' },
                    { type: 'concept', title: 'Manos débiles vs manos fuertes', content: 'Durante una base, los inversores impacientes (manos débiles) venden aburridos de que el precio no se mueve. Los institucionales (manos fuertes) absorben silenciosamente esas ventas, acumulando la posición que necesitan. Cuando ya tienen suficiente posición, el precio rompe al alza con fuerza. Los que vendieron durante la base ahora tienen que comprar más caro para recuperar su posición.' },
                ]
            },
            {
                heading: 'Características de una base de calidad',
                blocks: [
                    { type: 'text', content: 'No toda consolidación es una base de calidad. Hay señales específicas que diferencian una base que va a producir un movimiento potente de una consolidación que simplemente precede más lateralidad.' },
                    { type: 'chart', id: 'base_quality' },
                    { type: 'steps', items: [
                        '<strong>Contracción del rango:</strong> las velas se vuelven progresivamente más pequeñas — el mercado se comprime',
                        '<strong>Volumen decreciente:</strong> durante la base, el volumen cae. Esto indica que ya no hay vendedores agresivos — la oferta se está agotando',
                        '<strong>Límite inferior respetado:</strong> los intentos de caer por debajo del soporte de la base son rechazados rápidamente',
                        '<strong>Posición en tendencia:</strong> una base en tendencia alcista tras un retroceso a la media es mucho más fiable que una base aislada',
                        '<strong>Duración razonable:</strong> bases de 3-8 semanas tienen mejor resolución que bases de 2 días o 2 años',
                    ]},
                ]
            },
            {
                heading: 'Tipos de base por patrón',
                blocks: [
                    { type: 'text', content: 'Los institucionales siempre tienden a acumular de forma similar, lo que genera patrones reconocibles. No necesitas memorizar todos — con conocer dos o tres bien tienes más que suficiente.' },
                    { type: 'chart', id: 'base_types' },
                    { type: 'table',
                        headers: ['Patrón', 'Forma', 'Ruptura típica', 'Objetivo'],
                        rows: [
                            ['Flat base', 'Lateral estricto, rango <15%', 'Por encima del techo', 'Amplitud de la base proyectada'],
                            ['Cup & Handle', 'Forma de taza con mango', 'Ruptura del asa', '1-2x la profundidad de la taza'],
                            ['VCP (Volatility Contraction)', 'Contracciones progresivas menores', 'Ruptura con volumen', 'Movimiento extendido'],
                            ['Triangle (simétrico)', 'Convergencia de HH y LL', 'Ruptura de cualquier lado', 'Amplitud de la base'],
                        ]
                    },
                    { type: 'tip', label: 'VCP', content: 'El Volatility Contraction Pattern (VCP) es uno de los patrones más fiables para swing trading. El precio hace correcciones progresivamente más pequeñas: -20%, -12%, -7%, -4%... El último apretón antes de la ruptura es el punto de entrada de menor riesgo con mayor potencial.' },
                ]
            },
            {
                heading: 'La ruptura de la base: cuándo entrar',
                blocks: [
                    { type: 'text', content: 'La base no tiene valor por sí sola. Su valor está en la ruptura. La entrada correcta en ruptura de base es una de las operaciones más asimétrica disponibles: el riesgo es pequeño (el precio acaba de salir de la base, el stop está cerca) y el potencial es el movimiento completo que la base ha estado preparando.' },
                    { type: 'chart', id: 'base_breakout' },
                    { type: 'steps', items: [
                        'Define el nivel de ruptura: el techo exacto de la base (o del asa en Cup & Handle)',
                        'Prepara la orden antes de que el precio llegue al nivel — no improvises',
                        'La entrada ideal es en el cierre del día de ruptura si viene con volumen superior al promedio',
                        'Stop: por debajo del punto de máxima compresión de la base (el último HL antes de la ruptura)',
                        'Si el precio vuelve dentro de la base sin volumen vendedor importante, no es señal de salida necesariamente — puede ser retest',
                    ]},
                    { type: 'warning', content: 'Las rupturas sin volumen tienen una tasa de fallo alta. Si el precio supera el techo de la base pero el volumen es inferior al promedio de los últimos 20 días, espera confirmación al día siguiente antes de entrar. Las mejores rupturas tienen volumen 50-200% superior al promedio.' },
                ]
            },
        ]
    },
    // ── MÓDULO 6, LECCIÓN 1 ────────────────────────────────────────────────
    '6-1': {
        moduleId: 6,
        lessonIndex: 0,
        title: 'Engulfing Alcista',
        duration: '8 min',
        intro: 'El engulfing alcista es una de las señales de reversión más claras que existe. En una sola vela, los compradores no solo recuperan todo lo que los vendedores ganaron el día anterior — lo superan. Eso es una declaración de intenciones.',
        sections: [
            {
                heading: 'Anatomía del engulfing alcista',
                blocks: [
                    { type: 'text', content: 'Un engulfing alcista se forma con dos velas: una vela bajista seguida de una vela alcista cuyo cuerpo <strong>envuelve completamente</strong> el cuerpo de la vela bajista anterior. La apertura de la segunda vela está por debajo del cierre de la primera, y el cierre está por encima de la apertura de la primera.' },
                    { type: 'chart', id: 'bullish_engulfing_anatomy' },
                    { type: 'concept', title: 'Qué revela el engulfing', content: 'El precio abrió bajo (confirmando la presión bajista del día anterior), pero los compradores entraron tan agresivamente que no solo recuperaron todo el terreno perdido — empujaron el precio por encima de donde abrió el día anterior. Los vendedores quedaron atrapados. Es una transferencia de control visible en una sola sesión.' },
                ]
            },
            {
                heading: 'Contexto: cuándo el engulfing importa',
                blocks: [
                    { type: 'text', content: 'Un engulfing alcista en medio de una tendencia alcista fuerte no dice nada especial — el precio ya estaba subiendo. El engulfing cobra potencia cuando aparece en <strong>contextos específicos</strong> que le dan significado.' },
                    { type: 'chart', id: 'bullish_engulfing_context' },
                    { type: 'steps', items: [
                        '<strong>Tras una corrección en tendencia alcista:</strong> el precio ha retrocedido a una media o zona de demanda y el engulfing confirma el fin de la corrección',
                        '<strong>En soporte relevante:</strong> el nivel ya era importante, el engulfing confirma que los compradores lo están defendiendo',
                        '<strong>Tras varios días bajistas consecutivos:</strong> agotamiento vendedor seguido de compra agresiva',
                        '<strong>Con volumen superior a la media:</strong> la vela de engulfing viene con participación institucional',
                    ]},
                    { type: 'warning', content: 'Un engulfing alcista en resistencia mayor no es señal de compra — es una trampa. El precio puede engullar la vela anterior y aun así ser rechazado por la resistencia superior. Siempre verifica el contexto antes de actuar en cualquier patrón de velas.' },
                ]
            },
            {
                heading: 'Cómo operar el engulfing alcista',
                blocks: [
                    { type: 'text', content: 'La entrada en un engulfing alcista tiene dos momentos posibles: en el cierre de la vela de engulfing (agresivo) o en la apertura del día siguiente si el precio mantiene las ganancias (conservador).' },
                    { type: 'chart', id: 'bullish_engulfing_trade' },
                    { type: 'table',
                        headers: ['Entrada', 'Cuándo', 'Ventaja', 'Riesgo'],
                        rows: [
                            ['Cierre vela engulfing', 'Al cierre del período', 'Mejor precio de entrada', 'Sin confirmación del día siguiente'],
                            ['Apertura siguiente período', 'Si abre alcista o neutral', 'Confirmación adicional', 'Precio menos favorable'],
                            ['Ruptura del máximo', 'Cuando supera el max de la vela engulfing', 'Máxima confirmación', 'Puede ser tarde, ratio peor'],
                        ]
                    },
                    { type: 'tip', label: 'STOP', content: 'El stop del engulfing alcista va por debajo del mínimo de la vela de engulfing — no de la vela bajista anterior. El mínimo de la vela alcista de engulfing es el nivel que, si se rompe, invalida la señal.' },
                ]
            },
            {
                heading: 'Engulfing con volumen: la diferencia clave',
                blocks: [
                    { type: 'text', content: 'Un engulfing alcista con volumen superior al promedio de los últimos 20 días es una señal de primer orden. El volumen confirma que no es una fluctuación aleatoria — hay dinero institucional detrás de ese movimiento.' },
                    { type: 'chart', id: 'bullish_engulfing_volume' },
                    { type: 'concept', title: 'Engulfing sin volumen = señal débil', content: 'Un engulfing alcista que se forma con volumen inferior al promedio es una señal de baja calidad. Puede ser simplemente falta de vendedores más que presencia activa de compradores. En mercados de bajo volumen (verano, navidades, pre-feriados), los patrones de velas tienen menos fiabilidad.' },
                ]
            },
        ]
    },

    // ── MÓDULO 6, LECCIÓN 2 ────────────────────────────────────────────────
    '6-2': {
        moduleId: 6,
        lessonIndex: 1,
        title: 'Engulfing Bajista',
        duration: '8 min',
        intro: 'El engulfing bajista es la versión simétrica — y psicológicamente más poderosa. Los mercados caen más rápido de lo que suben, y un engulfing bajista en el lugar correcto puede ser el inicio de una caída sostenida.',
        sections: [
            {
                heading: 'Anatomía del engulfing bajista',
                blocks: [
                    { type: 'text', content: 'El engulfing bajista es dos velas: una alcista seguida de una bajista cuyo cuerpo <strong>envuelve completamente</strong> el cuerpo de la vela alcista. La segunda vela abre por encima del cierre de la primera y cierra por debajo de la apertura de la primera. Los vendedores borraron todo lo ganado por los compradores el día anterior.' },
                    { type: 'chart', id: 'bearish_engulfing_anatomy' },
                    { type: 'concept', title: 'El engulfing bajista es más potente que el alcista', content: 'Estadísticamente, los engulfings bajistas tienden a producir movimientos más fuertes y rápidos que los alcistas. Esto se debe a la asimetría del miedo: cuando los compradores ven que sus ganancias se borran en una sola sesión, el pánico de salida acelera la caída. Los vendedores en corto también añaden presión.' },
                ]
            },
            {
                heading: 'Cuándo el engulfing bajista es más potente',
                blocks: [
                    { type: 'text', content: 'Al igual que el alcista, el engulfing bajista necesita contexto para ser operativo. Los mejores aparecen en situaciones específicas que amplifican su significado:' },
                    { type: 'chart', id: 'bearish_engulfing_context' },
                    { type: 'steps', items: [
                        '<strong>En resistencia mayor:</strong> el precio llega a un nivel clave, hace una vela alcista débil, y es engullido bajistamente — los vendedores estaban esperando ese nivel',
                        '<strong>Tras una tendencia alcista extendida sin corrección:</strong> el mercado estaba sobrecomprado y el engulfing activa la toma de beneficios masiva',
                        '<strong>En zona de oferta fresca:</strong> el precio regresa a donde hubo una venta masiva y es rechazado con un engulfing bajista',
                        '<strong>Con volumen explosivo:</strong> indica que la venta es institucional, no retail',
                    ]},
                ]
            },
            {
                heading: 'Operativa: entrar en el engulfing bajista',
                blocks: [
                    { type: 'text', content: 'La operativa en engulfing bajista es especular en corto o, si no operas cortos, es la señal para <strong>salir de posiciones largas</strong>. En ambos casos, la acción correcta es inmediata.' },
                    { type: 'chart', id: 'bearish_engulfing_trade' },
                    { type: 'table',
                        headers: ['Situación', 'Acción', 'Stop', 'Objetivo'],
                        rows: [
                            ['Tienes posición larga', 'Cerrar al cierre del engulfing', '—', '—'],
                            ['Operas cortos (en resistencia)', 'Vender corto al cierre', 'Sobre el máximo del engulfing', 'Siguiente soporte relevante'],
                            ['No operas cortos (en tendencia)', 'No entrar largo hasta nueva señal', '—', 'Esperar estructura nueva'],
                        ]
                    },
                    { type: 'tip', label: 'LARGO PLAZO', content: 'Si operas en timeframes largos (semanal), un engulfing bajista semanal en resistencia es razón suficiente para salir de todas las posiciones largas en ese activo. No esperes confirmación adicional — el cierre semanal ya es la confirmación.' },
                ]
            },
            {
                heading: 'Engulfing bajista vs simple vela bajista grande',
                blocks: [
                    { type: 'text', content: 'No toda vela bajista grande es un engulfing. La condición de envolver el cuerpo de la vela anterior es lo que le da el significado especial. Una vela bajista grande que no envuelve la anterior es simplemente momentum — no tiene la misma connotación psicológica.' },
                    { type: 'chart', id: 'bearish_engulfing_vs_simple' },
                    { type: 'concept', title: 'La psicología del engulfing vs la vela grande', content: 'En el engulfing bajista, los compradores del día anterior están todos en pérdidas. Eso crea una presión de salida específica: a medida que el precio cae, sus stops se activan uno tras otro, acelerando el movimiento. En una vela bajista grande sin envolver la anterior, no hay esa masa de compradores atrapados — el movimiento puede ser más efímero.' },
                ]
            },
        ]
    },

    // ── MÓDULO 6, LECCIÓN 3 ────────────────────────────────────────────────
    '6-3': {
        moduleId: 6,
        lessonIndex: 2,
        title: 'Pin Bar',
        duration: '8 min',
        intro: 'El pin bar es la vela que más claramente muestra el rechazo de un nivel. La mecha larga es la firma del fracaso: el precio intentó ir en esa dirección, fue rechazado con fuerza, y cerró en el extremo opuesto. Eso no es accidental.',
        sections: [
            {
                heading: 'Anatomía del pin bar',
                blocks: [
                    { type: 'text', content: 'Un pin bar tiene tres elementos clave: una <strong>mecha larga</strong> (al menos el doble del cuerpo), un <strong>cuerpo pequeño</strong> en un extremo, y una <strong>mecha corta o inexistente</strong> en el otro extremo. La mecha larga señala la dirección que fue rechazada; el cuerpo pequeño muestra que el precio cerró lejos de donde intentó llegar.' },
                    { type: 'chart', id: 'pin_bar_anatomy' },
                    { type: 'concept', title: 'La mecha como huella del rechazo', content: 'La mecha de un pin bar es literalmente la trayectoria del fracaso. El precio subió (o bajó) hasta un nivel, los participantes en la dirección opuesta entraron masivamente, y el precio fue empujado de vuelta. Cuanto más larga la mecha y más pequeño el cuerpo, más decisivo fue el rechazo. Un pin bar con mecha que representa el 80% de la vela total es una señal de reversión muy potente.' },
                ]
            },
            {
                heading: 'Pin bar alcista vs pin bar bajista',
                blocks: [
                    { type: 'text', content: 'El pin bar alcista tiene la mecha larga hacia abajo (rechazo de niveles bajos, compradores tomando control) y el pin bar bajista tiene la mecha larga hacia arriba (rechazo de niveles altos, vendedores tomando control).' },
                    { type: 'chart', id: 'pin_bar_types' },
                    { type: 'table',
                        headers: ['Tipo', 'Mecha larga', 'Cuerpo', 'Señal', 'Contexto ideal'],
                        rows: [
                            ['Pin alcista', 'Abajo (shadow inferior)', 'Arriba, pequeño', 'Compra — rechazo de bajos', 'En soporte, zona demanda, HL'],
                            ['Pin bajista', 'Arriba (shadow superior)', 'Abajo, pequeño', 'Venta — rechazo de altos', 'En resistencia, zona oferta, LH'],
                            ['Pin doble mecha', 'Ambos lados largas', 'Medio, muy pequeño (doji)', 'Indecisión — esperar', 'No operativo por sí solo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Entrada y gestión del pin bar',
                blocks: [
                    { type: 'text', content: 'El pin bar ofrece dos zonas de entrada: en el cierre de la vela (agresivo, antes de confirmación) o en el retroceso al 50% del cuerpo el día siguiente (conservador, mejor ratio pero no siempre disponible).' },
                    { type: 'chart', id: 'pin_bar_entry' },
                    { type: 'steps', items: [
                        '<strong>Entrada agresiva:</strong> al cierre de la vela pin bar, con stop más allá del extremo de la mecha',
                        '<strong>Entrada al 50%:</strong> esperas que el precio retroceda al 50% del cuerpo del pin bar y entras ahí, stop igual',
                        '<strong>Entrada en ruptura:</strong> esperas que el precio supere el extremo del cuerpo opuesto a la mecha y entras, stop en extremo de mecha',
                        'El objetivo mínimo es la apertura de la vela que precedió al pin bar',
                    ]},
                    { type: 'tip', label: 'LA ENTRADA AL 50%', content: 'La entrada al 50% del cuerpo del pin bar es la más elegante: reduces el riesgo a la mitad (stop más cercano) y mantienes el mismo objetivo, mejorando el ratio riesgo/recompensa. El precio retrocede al 50% del pin bar con frecuencia suficiente para que valga la pena esperar, especialmente en semanal.' },
                ]
            },
            {
                heading: 'Pin bar en confluencia con otros factores',
                blocks: [
                    { type: 'text', content: 'El pin bar solo tiene verdadero valor cuando coincide con otros factores técnicos. Un pin bar aislado en el medio de un rango sin nivel relevante no es una señal operativa.' },
                    { type: 'chart', id: 'pin_bar_confluence' },
                    { type: 'concept', title: 'La regla de las tres confluencias', content: 'Para que un pin bar sea operativo de alta probabilidad, necesita al menos tres de estos factores: (1) nivel de soporte/resistencia claro, (2) zona de demanda/oferta activa, (3) tendencia a favor en timeframe mayor, (4) media móvil relevante en la zona, (5) volumen superior al promedio, (6) número Fibonacci relevante. Con tres confluencias, el pin bar es una señal de primer orden.' },
                ]
            },
        ]
    },

    // ── MÓDULO 6, LECCIÓN 4 ────────────────────────────────────────────────
    '6-4': {
        moduleId: 6,
        lessonIndex: 3,
        title: 'Inside Bar',
        duration: '8 min',
        intro: 'El inside bar es la vela que más traders subestiman. No es dramático como un engulfing o un pin bar. Es silencioso. Y esa es exactamente su virtud: el mercado ha dejado de moverse, las fuerzas se equilibran, y lo que viene después de ese silencio suele ser decisivo.',
        sections: [
            {
                heading: '¿Qué es un inside bar?',
                blocks: [
                    { type: 'text', content: 'Un inside bar es una vela cuyo rango completo (de máximo a mínimo) está <strong>dentro del rango de la vela anterior</strong>. El máximo es más bajo que el máximo anterior y el mínimo es más alto que el mínimo anterior. El mercado literalmente no fue a ningún sitio nuevo en ese período.' },
                    { type: 'chart', id: 'inside_bar_definition' },
                    { type: 'concept', title: 'El inside bar como pausa de decisión', content: 'Cuando aparece un inside bar, el mercado está procesando información. Los participantes están indecisos — ni compradores ni vendedores tienen suficiente convicción para empujar el precio más allá del rango de la vela anterior. Esta compresión de energía suele resolverse con un movimiento direccional claro cuando uno de los dos grupos toma el control.' },
                ]
            },
            {
                heading: 'Inside bar en tendencia: señal de continuación',
                blocks: [
                    { type: 'text', content: 'En una tendencia alcista o bajista establecida, el inside bar suele ser una señal de <strong>continuación</strong>, no de reversión. El mercado hace una pausa, consolida las ganancias, y luego continúa en la misma dirección.' },
                    { type: 'chart', id: 'inside_bar_continuation' },
                    { type: 'steps', items: [
                        'El precio está en tendencia alcista clara (HH+HL)',
                        'Aparece un inside bar tras una vela alcista fuerte (la "madre")',
                        'El inside bar es la pausa — el mercado digiere el impulso anterior',
                        'Entrada: cuando el precio supera el máximo del inside bar (ruptura alcista)',
                        'Stop: por debajo del mínimo del inside bar o de la vela madre',
                    ]},
                    { type: 'tip', label: 'MÚLTIPLES INSIDE BARS', content: 'Cuando aparecen dos o tres inside bars consecutivos, la compresión es aún mayor. Cada vela que queda dentro de la anterior acumula más presión. La ruptura de ese patrón multi-inside suele ser especialmente fuerte y sostenida.' },
                ]
            },
            {
                heading: 'Inside bar en nivel clave: señal de reversión',
                blocks: [
                    { type: 'text', content: 'Cuando el inside bar aparece justo en una zona de soporte/resistencia o en una zona de oferta/demanda, su significado cambia: puede ser la pausa que precede a una reversión importante.' },
                    { type: 'chart', id: 'inside_bar_reversal' },
                    { type: 'table',
                        headers: ['Contexto del inside bar', 'Señal', 'Entrada'],
                        rows: [
                            ['Tras impulso alcista, en resistencia', 'Posible techo — reversión bajista', 'Ruptura bajista del inside bar'],
                            ['Tras caída, en soporte/demanda', 'Posible suelo — reversión alcista', 'Ruptura alcista del inside bar'],
                            ['En medio de tendencia sin nivel', 'Continuación probable', 'Ruptura en dirección de tendencia'],
                            ['Tras varios días de lateralidad', 'Sin señal — esperar otro patrón', 'No operar'],
                        ]
                    },
                    { type: 'warning', content: 'El inside bar en un mercado lateralizado sin tendencia clara no tiene significado operativo. El inside bar cobra vida cuando hay contexto: una tendencia previa clara, un nivel relevante, o una vela madre especialmente significativa. Sin contexto, es ruido.' },
                ]
            },
            {
                heading: 'False break del inside bar',
                blocks: [
                    { type: 'text', content: 'Una de las configuraciones más potentes con el inside bar es el <strong>false break</strong> o ruptura falsa: el precio rompe el inside bar en una dirección, atrae a los traders que siguen la ruptura, y luego vuelve con fuerza en la dirección opuesta.' },
                    { type: 'chart', id: 'inside_bar_false_break' },
                    { type: 'concept', title: 'Cazar stops con el false break', content: 'El false break del inside bar es una de las operaciones favoritas del dinero institucional. Rompen el mínimo del inside bar (activando los stops de los compradores y atrayendo a vendedores en corto), y luego compran masivamente esa liquidez, empujando el precio al alza con fuerza. Los que vendieron en la ruptura quedan atrapados en corto. La señal de entrada: el precio vuelve a entrar dentro del rango del inside bar tras la ruptura falsa.' },
                ]
            },
        ]
    },
    // ── MÓDULO 7, LECCIÓN 1 ────────────────────────────────────────────────
    '7-1': {
        moduleId: 7,
        lessonIndex: 0,
        title: 'Ruptura de Rango',
        duration: '9 min',
        intro: 'La ruptura de un rango es uno de los momentos más importantes en el mercado. Después de semanas de equilibrio entre compradores y vendedores, uno de los dos grupos gana. El resultado suele ser un movimiento direccional potente. El problema es que la mayoría de las rupturas son falsas.',
        sections: [
            {
                heading: 'Por qué los rangos producen rupturas potentes',
                blocks: [
                    { type: 'text', content: 'Durante un rango lateral, se acumula energía en forma de órdenes pendientes: stops de compradores por debajo del soporte, stops de vendedores por encima de la resistencia, órdenes de entrada en ambos lados. Cuando el precio rompe uno de los extremos, esas órdenes se ejecutan en cascada, creando un movimiento rápido y direccional.' },
                    { type: 'chart', id: 'range_breakout_energy' },
                    { type: 'concept', title: 'El principio de medición', content: 'La ruptura de un rango proyecta un objetivo de precio igual a la amplitud del rango. Si el rango tiene 20 puntos de altura y el precio rompe al alza, el objetivo mínimo es 20 puntos por encima del techo del rango. Este principio de medición funciona con fiabilidad suficiente para usarlo como referencia de objetivo.' },
                ]
            },
            {
                heading: 'Rupturas reales vs falsas',
                blocks: [
                    { type: 'text', content: 'La estadística es brutal: <strong>más del 70% de las rupturas aparentes de un rango son falsas</strong>. El precio cruza el nivel, atrae seguidores de la ruptura, y vuelve dentro del rango. La confirmación es lo que separa una entrada rentable de una trampa.' },
                    { type: 'chart', id: 'range_breakout_real_vs_false' },
                    { type: 'table',
                        headers: ['Señal', 'Ruptura real', 'Ruptura falsa'],
                        rows: [
                            ['Volumen', 'Muy superior al promedio (150-300%)', 'Igual o inferior al promedio'],
                            ['Vela', 'Cierre fuerte en el extremo', 'Cierre débil, mecha larga'],
                            ['Continuación', 'Día siguiente confirma la dirección', 'Vuelve dentro del rango'],
                            ['Velocidad', 'Movimiento rápido y decisivo', 'Lento, indeciso'],
                            ['Retest', 'Regresa al nivel y rebota', 'Regresa y vuelve a entrar'],
                        ]
                    },
                    { type: 'tip', label: 'FILTRO PRINCIPAL', content: 'El filtro más eficaz para evitar rupturas falsas es el volumen. Si el precio rompe el techo de un rango con volumen inferior al promedio de los últimos 20 días, espera. Si al día siguiente el volumen no aumenta, la ruptura probablemente es falsa. No entres sin volumen.' },
                ]
            },
            {
                heading: 'La entrada en ruptura de rango',
                blocks: [
                    { type: 'text', content: 'Hay tres formas de entrar en una ruptura de rango, cada una con su propio perfil de riesgo-recompensa:' },
                    { type: 'chart', id: 'range_breakout_entry' },
                    { type: 'steps', items: [
                        '<strong>Entrada agresiva:</strong> compras en el cierre del primer día de ruptura con volumen. Mayor riesgo si es falsa, pero mejor precio.',
                        '<strong>Entrada en retest:</strong> esperas que el precio vuelva a testear el nivel roto como soporte. Más seguro, peor precio. No siempre ocurre.',
                        '<strong>Entrada en confirmación:</strong> esperas el segundo cierre por encima del nivel. Mínimo riesgo de falsa ruptura, pero el precio ya se ha movido considerablemente.',
                    ]},
                    { type: 'warning', content: 'Si el precio rompe el rango y vuelve a entrar dentro del rango con una vela completa (cierre dentro del rango), la ruptura ha fallado. Sal inmediatamente. No esperes "a ver si se recupera". Una ruptura que vuelve dentro del rango suele conducir a un movimiento en la dirección contraria.' },
                ]
            },
            {
                heading: 'El objetivo tras la ruptura',
                blocks: [
                    { type: 'text', content: 'Una vez dentro de la ruptura, el objetivo de precio mínimo es la amplitud del rango proyectada en la dirección de la ruptura. A partir de ahí, los siguientes niveles técnicos relevantes (resistencias previas, zonas de oferta, máximos históricos) definen los objetivos adicionales.' },
                    { type: 'chart', id: 'range_breakout_target' },
                    { type: 'concept', title: 'Gestión tras la ruptura', content: 'Tras entrar en una ruptura de rango: cierra el 50% en el objetivo medido (amplitud del rango proyectada), sube el stop al punto de entrada para el 50% restante, y deja correr la posición hacia los siguientes niveles técnicos. Si el precio vuelve al punto de entrada sin haber alcanzado el objetivo medido, es señal de debilidad — sale todo.' },
                ]
            },
        ]
    },

    // ── MÓDULO 7, LECCIÓN 2 ────────────────────────────────────────────────
    '7-2': {
        moduleId: 7,
        lessonIndex: 1,
        title: 'Ruptura de Tendencia',
        duration: '9 min',
        intro: 'La ruptura de una línea de tendencia no es el fin de la tendencia — es la primera advertencia. La diferencia entre un trader que pierde dinero y uno que lo preserva está en saber cuándo esa advertencia se convierte en señal de acción.',
        sections: [
            {
                heading: 'Cuándo una ruptura de tendencia es significativa',
                blocks: [
                    { type: 'text', content: 'No toda ruptura de línea de tendencia merece atención. La significancia depende de <strong>cuántos toques válidos tenía la línea</strong>, el timeframe en que aparece, y si va acompañada de volumen y cambio de estructura.' },
                    { type: 'chart', id: 'trendline_break_significance' },
                    { type: 'steps', items: [
                        'Línea con 2 toques válidos: ruptura poco significativa, puede ser ajuste',
                        'Línea con 3-4 toques válidos: ruptura relevante, señal de precaución',
                        'Línea con 5+ toques válidos: ruptura muy significativa, posible cambio de tendencia',
                        'Ruptura con volumen superior al promedio: multiplica la significancia',
                        'Ruptura seguida de incapacidad de recuperar: confirma el cambio',
                    ]},
                ]
            },
            {
                heading: 'Ruptura de tendencia alcista: qué esperar',
                blocks: [
                    { type: 'text', content: 'Cuando una línea de tendencia alcista con varios toques válidos se rompe, el precio suele seguir esta secuencia predecible que te da múltiples oportunidades de actuar:' },
                    { type: 'chart', id: 'uptrend_line_break' },
                    { type: 'steps', items: [
                        'El precio rompe la línea de tendencia con fuerza (vela grande, volumen)',
                        'El precio rebota brevemente hacia la línea rota (retest)',
                        'La línea rota actúa como resistencia y el precio es rechazado (confirmación)',
                        'El precio forma el primer LH relevante — estructura cambiando',
                        'El precio rompe el último HL de la tendencia alcista — cambio confirmado',
                    ]},
                    { type: 'tip', label: 'ACCIÓN', content: 'No esperes a ver todos los pasos para actuar. Con los pasos 1 y 2 completados (ruptura y retest), ya tienes suficiente para reducir exposición significativamente. No es necesario esperar la confirmación total si el riesgo de mantener es elevado.' },
                ]
            },
            {
                heading: 'Ruptura de tendencia bajista: señal de recuperación',
                blocks: [
                    { type: 'text', content: 'La ruptura de una línea de tendencia bajista es la primera señal de que la presión vendedora está cediendo. Al igual que con la alcista, necesita confirmación para ser operativa.' },
                    { type: 'chart', id: 'downtrend_line_break' },
                    { type: 'concept', title: 'Primera señal no es confirmación', content: 'La ruptura de la línea de tendencia bajista solo confirma que los vendedores han perdido el control momentáneamente. Para que sea una señal de compra válida, necesitas ver además: el precio superar el último LH de la tendencia, y el primer retroceso quedarse por encima del nivel de ruptura. Sin esas confirmaciones, puede ser solo un rebote técnico más.' },
                ]
            },
            {
                heading: 'Rupturas aceleradas: el patrón final',
                blocks: [
                    { type: 'text', content: 'Al final de una tendencia alcista fuerte, el precio a veces rompe la línea de tendencia por arriba — se acelera en lugar de desacelerarse. Esta ruptura de la línea superior del canal es frecuentemente la señal de la fase final de la tendencia, no de su continuación.' },
                    { type: 'chart', id: 'accelerated_breakout' },
                    { type: 'concept', title: 'El agotamiento por parabolismo', content: 'Cuando el precio empieza a subir en parabólico — cada semana más rápido que la anterior, rompiendo la línea de tendencia por arriba — el mercado está en su fase de distribución final. Los institucionales están vendiendo a los compradores más entusiastas. El colapso que sigue suele ser tan rápido como la subida parabolica. No es el momento de comprar — es el momento de vender.' },
                ]
            },
        ]
    },

    // ── MÓDULO 7, LECCIÓN 3 ────────────────────────────────────────────────
    '7-3': {
        moduleId: 7,
        lessonIndex: 2,
        title: 'Ruptura de Soporte',
        duration: '9 min',
        intro: 'La ruptura de un soporte importante es uno de los momentos más peligrosos del mercado para los compradores y más lucrativos para los vendedores. Entender por qué un soporte se rompe y qué viene después marca la diferencia entre perder capital y preservarlo.',
        sections: [
            {
                heading: 'Por qué se rompen los soportes',
                blocks: [
                    { type: 'text', content: 'Un soporte se rompe cuando la <strong>presión vendedora supera permanentemente la demanda disponible</strong> en esa zona. No es un evento aleatorio — suele estar precedido por señales de debilidad que avisan con antelación.' },
                    { type: 'chart', id: 'support_break_why' },
                    { type: 'steps', items: [
                        'Los rebotes desde el soporte se vuelven progresivamente más débiles (menor altura, menor volumen)',
                        'El precio pasa cada vez más tiempo cerca del soporte sin poder alejarse',
                        'Aparecen velas bajistas de tamaño creciente en los acercamientos al soporte',
                        'El volumen aumenta en los tramos bajistas y disminuye en los rebotes',
                        'El soporte cede con una vela de gran tamaño y volumen muy superior al promedio',
                    ]},
                    { type: 'warning', content: 'Si ves estas señales de debilidad acumulándose en un soporte que tienes referenciado, no esperes a que se rompa para actuar. Reduce exposición mientras el precio todavía está cerca del soporte, no después de que haya caído un 10% por debajo.' },
                ]
            },
            {
                heading: 'Tipos de ruptura de soporte',
                blocks: [
                    { type: 'text', content: 'No todas las rupturas de soporte son iguales en velocidad y consecuencias. El tipo de ruptura define cómo debes reaccionar:' },
                    { type: 'chart', id: 'support_break_types' },
                    { type: 'table',
                        headers: ['Tipo', 'Característica', 'Velocidad de reacción'],
                        rows: [
                            ['Ruptura limpia', 'Vela grande, cierre bajo el soporte, volumen', 'Inmediata — salir al cierre'],
                            ['Ruptura con spike', 'Penetración breve, cierre cerca del soporte', 'Esperar cierre — puede ser stop hunt'],
                            ['Ruptura lenta', 'El precio va filtrando el soporte gradualmente', 'Reducir en cada cierre bajo el nivel'],
                            ['Ruptura en gap', 'El precio abre directamente bajo el soporte', 'Ya roto — evalúa el retest antes de actuar'],
                        ]
                    },
                ]
            },
            {
                heading: 'El soporte roto como nueva resistencia',
                blocks: [
                    { type: 'text', content: 'Cuando un soporte se rompe con convicción, se convierte en resistencia. El precio regresa a testear ese nivel desde abajo — y los que compraron ahí antes y están atrapados en pérdidas aprovechan el retest para salir, creando presión vendedora que convierte el antiguo soporte en resistencia.' },
                    { type: 'chart', id: 'support_becomes_resistance' },
                    { type: 'concept', title: 'El retest: oportunidad de dos lados', content: 'El retest del soporte roto ofrece oportunidades en ambos lados: para los que todavía tienen posiciones largas, es la última oportunidad de salir a mejor precio antes de la siguiente caída. Para los que buscan cortos, es la entrada de menor riesgo — el precio ha subido hasta la zona de resistencia con bajo volumen, el stop es pequeño (por encima de la resistencia) y el potencial es alto.' },
                ]
            },
            {
                heading: 'Qué hacer cuando se rompe tu soporte',
                blocks: [
                    { type: 'text', content: 'La ruptura del soporte en una posición que tienes abierta es un momento que pone a prueba la disciplina. La respuesta emocional es "esperar a que se recupere". La respuesta correcta es otra.' },
                    { type: 'chart', id: 'support_break_action' },
                    { type: 'steps', items: [
                        '<strong>Si tenías stop por debajo del soporte:</strong> ya saliste automáticamente. Bien hecho. Analiza si el retest ofrece reentrada o si el contexto ha cambiado.',
                        '<strong>Si no tenías stop definido:</strong> sal en el cierre de la vela que rompe el soporte. No esperes el retest para salir — el retest puede no llegar.',
                        '<strong>Si el precio ya está 5-10% bajo el soporte:</strong> evalúa si el retest es probable antes de entrar de nuevo. Si hay mucho daño, el precio puede seguir cayendo sin retorno.',
                        '<strong>En ningún caso:</strong> añadas a la posición perdedora esperando recuperación.',
                    ]},
                    { type: 'tip', label: 'REGLA', content: 'Tu stop loss define el punto en que reconoces que estabas equivocado. Si no tienes stop, defines ese punto de otra forma — pero debes tenerlo definido antes de entrar. La ruptura de un soporte importante en el que basaste tu entrada es razón suficiente para salir sin necesidad de más señales.' },
                ]
            },
        ]
    },

    // ── MÓDULO 7, LECCIÓN 4 ────────────────────────────────────────────────
    '7-4': {
        moduleId: 7,
        lessonIndex: 3,
        title: 'Entradas en Retest',
        duration: '9 min',
        intro: 'El retest es la segunda oportunidad que el mercado te da. La primera ruptura ocurrió y te la perdiste, o no estabas seguro. El retest es el mercado regresando a confirmar que el nivel ha cambiado de función. Es la entrada de menor riesgo disponible tras una ruptura.',
        sections: [
            {
                heading: 'Por qué ocurre el retest',
                blocks: [
                    { type: 'text', content: 'Después de una ruptura, hay dos fuerzas que tiran del precio de vuelta al nivel roto: los traders que compraron la ruptura y toman ganancias parciales (presión bajista), y los traders que se perdieron la ruptura y esperan el retest para entrar (presión compradora al nivel). Esta segunda fuerza es la que hace que el retest sea tan fiable: hay demanda real esperando en el nivel.' },
                    { type: 'chart', id: 'retest_why' },
                    { type: 'concept', title: 'No todos los retests son iguales', content: 'Un retest profundo (el precio vuelve completamente al nivel y lo toca) tiene más valor confirmatorio que un retest superficial (el precio se acerca pero no toca el nivel). El retest ideal toca el nivel exacto, muestra una vela de rechazo, y vuelve en la dirección de la ruptura. Un retest que penetra significativamente el nivel o que tarda demasiado en producirse pierde potencia.' },
                ]
            },
            {
                heading: 'Retest tras ruptura alcista',
                blocks: [
                    { type: 'text', content: 'Tras una ruptura al alza (del techo de un rango, de una resistencia, de una línea de tendencia bajista), el precio regresa a testear el nivel roto como soporte. La calidad del retest determina la calidad de la entrada.' },
                    { type: 'chart', id: 'retest_bullish' },
                    { type: 'steps', items: [
                        'El precio rompe la resistencia con fuerza y volumen',
                        'El precio sube durante 1-5 días adicionales (impulso post-ruptura)',
                        'El precio comienza un retroceso hacia el nivel roto',
                        'El retroceso ocurre con volumen decreciente (corrección sana)',
                        'El precio toca el nivel, muestra rechazo (vela alcista, pin bar, engulfing), y retoma el alza',
                        'Entrada en la vela de rechazo, stop bajo el nivel retestado',
                    ]},
                    { type: 'tip', label: 'TIMING', content: 'La entrada en retest tiene una ventana de tiempo. Si el precio tarda más de 2-3 semanas en volver al nivel, el nivel pierde relevancia — otros factores técnicos han entrado en juego. El retest ideal ocurre dentro de la primera semana tras la ruptura.' },
                ]
            },
            {
                heading: 'Retest tras ruptura bajista',
                blocks: [
                    { type: 'text', content: 'Tras una ruptura a la baja (del soporte de un rango, de una línea de tendencia alcista, de un soporte histórico), el precio regresa a testear el nivel roto desde abajo — ahora como resistencia. Esta es la entrada de mayor calidad para posiciones cortas.' },
                    { type: 'chart', id: 'retest_bearish' },
                    { type: 'table',
                        headers: ['Característica del retest bajista', 'Señal positiva', 'Señal negativa'],
                        rows: [
                            ['Volumen en el retroceso (subida al nivel)', 'Bajo — corrección sana', 'Alto — compradores activos'],
                            ['Vela en el nivel', 'Bajista, rechazo claro', 'Alcista, penetra el nivel'],
                            ['Velocidad del retorno', 'Rápido tras el rechazo', 'Lento, precio se mantiene en el nivel'],
                            ['Estructura', 'Precio no supera el máximo anterior', 'Precio supera el máximo anterior'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cuando el retest falla',
                blocks: [
                    { type: 'text', content: 'Un retest fallido — donde el precio vuelve al nivel y lo rompe en la dirección contraria a la ruptura original — es una señal importante. Indica que la ruptura era falsa y que la dirección real es opuesta a la que parecía.' },
                    { type: 'chart', id: 'retest_failed' },
                    { type: 'concept', title: 'El retest fallido como señal operativa', content: 'El retest fallido es especialmente poderoso en los dos casos extremos. Si el precio rompe un soporte, lo retestea, y luego sube con fuerza por encima del nivel de ruptura, el mercado está diciendo que la ruptura bajista era falsa — señal alcista. Si el precio rompe una resistencia, la retestea, y luego cae con fuerza bajo el nivel, la ruptura alcista era falsa — señal bajista. En ambos casos, los que entraron en la ruptura original quedan atrapados y añaden presión en la dirección correcta.' },
                    { type: 'warning', content: 'Si entras en un retest y el precio rompe el nivel en lugar de respetarlo, sal inmediatamente. Un retest que falla no es "el mercado tomándose su tiempo" — es el mercado diciéndote que la estructura que identificaste no era válida. La pérdida pequeña de un retest fallido es preferible a mantener esperando una recuperación que puede no llegar.' },
                ]
            },
        ]
    },
    // ── MÓDULO 8, LECCIÓN 1 ────────────────────────────────────────────────
    '8-1': {
        moduleId: 8,
        lessonIndex: 0,
        title: 'Volumen en Rupturas',
        duration: '8 min',
        intro: 'El volumen es el único indicador que no se puede falsificar. El precio puede moverse por inercia, por baja liquidez, o por un solo actor. El volumen te dice si hay convicción real detrás del movimiento o si es ruido.',
        sections: [
            {
                heading: 'Por qué el volumen confirma el precio',
                blocks: [
                    { type: 'text', content: 'El precio y el volumen son las dos únicas variables primarias del mercado. Todo lo demás —medias, RSI, MACD— son derivados matemáticos del precio. El volumen, en cambio, mide la <strong>participación real</strong>: cuántos contratos o acciones cambiaron de manos. Sin participación, no hay convicción.' },
                    { type: 'chart', id: 'volume_confirms_price' },
                    { type: 'concept', title: 'Divergencia precio-volumen', content: 'Cuando el precio sube pero el volumen baja, el movimiento es sospechoso. Están subiendo los que ya estaban dentro, no entrando nuevos compradores. Sin flujo nuevo de dinero, la subida se agota. La regla: precio y volumen deben moverse en la misma dirección para que el movimiento sea sostenible.' },
                ]
            },
            {
                heading: 'Volumen en rupturas: el filtro definitivo',
                blocks: [
                    { type: 'text', content: 'La regla más importante del volumen: <strong>una ruptura sin volumen es una trampa hasta que se demuestre lo contrario</strong>. Para que una ruptura sea válida necesita al menos 1.5x el volumen promedio de los últimos 20 días. Las mejores rupturas tienen 2-3x o más.' },
                    { type: 'chart', id: 'breakout_volume_valid' },
                    { type: 'table',
                        headers: ['Volumen en ruptura', 'Interpretación', 'Probabilidad de continuación'],
                        rows: [
                            ['< 0.8x promedio', 'Ruptura falsa probable', '20-30%'],
                            ['0.8x - 1.5x promedio', 'Ruptura dudosa — esperar confirmación', '40-50%'],
                            ['1.5x - 2x promedio', 'Ruptura válida', '60-70%'],
                            ['2x - 3x promedio', 'Ruptura fuerte — alta convicción', '70-80%'],
                            ['> 3x promedio', 'Ruptura institucional — máxima convicción', '80%+'],
                        ]
                    },
                    { type: 'tip', label: 'CÁLCULO', content: 'Calcula el volumen promedio de los últimos 20 días y márcalo como referencia antes de la ruptura. Cuando el precio toca el nivel de ruptura, compara el volumen actual con esa referencia. Si no llega a 1.5x, espera al día siguiente antes de entrar.' },
                ]
            },
            {
                heading: 'Volumen decreciente en el pullback: señal alcista',
                blocks: [
                    { type: 'text', content: 'Tras una ruptura alcista con volumen, el precio suele retroceder al nivel roto (pullback). Si ese retroceso ocurre con <strong>volumen significativamente inferior</strong> al de la ruptura, es una señal muy alcista: los vendedores son pocos y débiles.' },
                    { type: 'chart', id: 'pullback_low_volume' },
                    { type: 'steps', items: [
                        'Precio rompe resistencia con volumen 2x+ superior al promedio',
                        'Precio sube 3-5 días adicionales con volumen moderado',
                        'Precio retrocede al nivel roto — volumen cae al 40-60% del promedio',
                        'Bajo volumen en el retroceso = sin presión vendedora real',
                        'El nivel roto actúa como soporte — entrada con stop bajo ese nivel',
                    ]},
                    { type: 'warning', content: 'Si el pullback al nivel roto viene con volumen alto, la ruptura está siendo cuestionada. Los vendedores están activos. En ese caso el nivel puede no aguantar — reduce el tamaño de la posición o espera confirmación adicional antes de entrar.' },
                ]
            },
            {
                heading: 'Leer el volumen en gráfico de velas',
                blocks: [
                    { type: 'text', content: 'El volumen se lee siempre en relación al contexto reciente, no en valor absoluto. Una vela con 10 millones de acciones puede ser alta o baja dependiendo de si el promedio es 5M o 50M. Siempre compara con la media de 20-50 días.' },
                    { type: 'chart', id: 'volume_candle_reading' },
                    { type: 'concept', title: 'Vela + volumen = historia completa', content: 'La combinación de la forma de la vela con el volumen te da la historia completa de la sesión. Vela alcista grande + volumen alto = compradores agresivos. Vela alcista pequeña + volumen alto = compradores y vendedores equilibrados, indecisión. Vela bajista + volumen muy alto = posible capitulación o distribución. Cada combinación tiene una interpretación diferente.' },
                ]
            },
        ]
    },

    // ── MÓDULO 8, LECCIÓN 2 ────────────────────────────────────────────────
    '8-2': {
        moduleId: 8,
        lessonIndex: 1,
        title: 'Bajo Volumen en Retrocesos',
        duration: '8 min',
        intro: 'Si el volumen alto en rupturas es la señal de entrada, el volumen bajo en retrocesos es la confirmación de que la tendencia sigue intacta. Aprender a leer los retrocesos con volumen te evitará salir de posiciones ganadoras antes de tiempo.',
        sections: [
            {
                heading: 'El retroceso saludable',
                blocks: [
                    { type: 'text', content: 'Un retroceso saludable dentro de una tendencia alcista tiene tres características: es <strong>temporal</strong> (dura pocos días o semanas), es <strong>moderado</strong> en precio (no rompe la estructura HH+HL), y ocurre con <strong>volumen decreciente</strong>. Cuando el volumen baja durante la corrección, significa que pocos quieren vender — los vendedores se están agotando.' },
                    { type: 'chart', id: 'healthy_pullback_volume' },
                    { type: 'concept', title: 'La corrección como recarga', content: 'En una tendencia alcista fuerte, los retrocesos de bajo volumen son períodos de recarga. Los compradores que no pudieron entrar en el impulso anterior esperan la corrección para entrar a mejor precio. Cuando el volumen baja durante la corrección, es señal de que el precio está llegando a la zona donde esos compradores están esperando.' },
                ]
            },
            {
                heading: 'Cómo medir el volumen en retrocesos',
                blocks: [
                    { type: 'text', content: 'No basta con observar que el volumen "parece bajo". Necesitas una referencia concreta para determinar si es realmente bajo o simplemente menor que el pico del impulso.' },
                    { type: 'chart', id: 'pullback_volume_measure' },
                    { type: 'steps', items: [
                        'Calcula el volumen promedio de los últimos 20 días (incluyendo el impulso)',
                        'Observa el volumen durante cada día del retroceso',
                        'Un retroceso es de "bajo volumen" si el volumen diario está por debajo del 70% del promedio',
                        'Si algún día del retroceso supera el 100% del promedio, la corrección tiene presión vendedora real',
                        'Compara también el volumen del retroceso con el del impulso anterior — debería ser significativamente menor',
                    ]},
                    { type: 'tip', label: 'SEÑAL', content: 'El día de giro desde el retroceso — cuando el precio para de caer y empieza a recuperar — suele venir con un pequeño aumento de volumen. No es el volumen alto del impulso, pero es claramente mayor que los días del retroceso. Esa es la señal de entrada más precisa en tendencia.' },
                ]
            },
            {
                heading: 'Retroceso profundo con volumen bajo: no siempre es malo',
                blocks: [
                    { type: 'text', content: 'Un retroceso puede ser profundo en precio (50-60% del impulso anterior) y aun así ser saludable si el volumen es muy bajo. Lo que importa es la presión vendedora, no la profundidad. Mercados de baja liquidez pueden tener retrocesos profundos con muy poco volumen.' },
                    { type: 'chart', id: 'deep_pullback_low_volume' },
                    { type: 'table',
                        headers: ['Retroceso', 'Volumen', 'Interpretación'],
                        rows: [
                            ['Superficial (< 30%)', 'Bajo', '✅ Tendencia muy fuerte — comprar'],
                            ['Moderado (30-50%)', 'Bajo', '✅ Corrección normal — comprar en soporte'],
                            ['Profundo (50-70%)', 'Bajo', '⚠️ Aceptable — verificar estructura'],
                            ['Moderado (30-50%)', 'Alto', '🔴 Presión vendedora — esperar'],
                            ['Profundo (> 70%)', 'Alto', '🔴 Posible cambio de tendencia'],
                        ]
                    },
                ]
            },
            {
                heading: 'Trampa: confundir bajo volumen con falta de interés',
                blocks: [
                    { type: 'text', content: 'El bajo volumen durante un retroceso es positivo. El bajo volumen durante una <strong>ruptura o un impulso</strong> es negativo. Son situaciones opuestas que requieren interpretaciones opuestas. El contexto es todo.' },
                    { type: 'chart', id: 'volume_context_trap' },
                    { type: 'concept', title: 'La regla de contexto del volumen', content: 'Bajo volumen es alcista cuando ocurre en correcciones (pocos vendedores). Bajo volumen es bajista cuando ocurre en impulsos (pocos compradores). Alto volumen es alcista en impulsos (muchos compradores). Alto volumen es bajista en correcciones (muchos vendedores). El mismo dato numérico tiene significados opuestos según el contexto.' },
                ]
            },
        ]
    },

    // ── MÓDULO 8, LECCIÓN 3 ────────────────────────────────────────────────
    '8-3': {
        moduleId: 8,
        lessonIndex: 2,
        title: 'Volumen Clímax',
        duration: '16 min',
        intro: 'El volumen clímax es el momento en que el mercado se rinde. Una vela enorme con volumen extraordinario que marca el punto de máximo miedo o máxima codicia. Reconocerlo es una de las habilidades más valiosas del trader técnico.',
        sections: [
            {
                heading: '¿Qué es el volumen clímax?',
                blocks: [
                    { type: 'text', content: 'El volumen clímax ocurre cuando el volumen de una sesión supera entre <strong>3 y 10 veces</strong> el promedio habitual, generalmente acompañado de una vela de gran tamaño. Es el momento en que participantes que normalmente no operan entran en pánico (climax bajista) o en euforia (climax alcista). Paradójicamente, suele marcar el final del movimiento, no su continuación.' },
                    { type: 'chart', id: 'climax_volume_definition' },
                    { type: 'concept', title: 'Por qué el clímax marca el final', content: 'En un clímax bajista, todo el mundo que quería vender ya vendió en ese momento de pánico. No quedan vendedores. Los únicos que pueden comprar a esos precios son los que tienen convicción alcista de largo plazo. El resultado: el precio ya no tiene presión bajista y revierte. Lo mismo en sentido contrario con el clímax alcista.' },
                ]
            },
            {
                heading: 'Clímax bajista: señal de suelo',
                blocks: [
                    { type: 'text', content: 'El clímax bajista es la capitulación. Se forma tras una caída prolongada, con una vela bajista enorme y volumen extraordinario. El precio puede seguir cayendo brevemente tras el clímax, pero la presión vendedora se agota rápidamente.' },
                    { type: 'chart', id: 'selling_climax' },
                    { type: 'steps', items: [
                        'El precio lleva semanas o meses cayendo — hay miedo generalizado',
                        'Aparece una vela bajista de gran tamaño (3-5% o más en un día)',
                        'El volumen es 3x+ superior al promedio de los últimos 20 días',
                        'El precio puede hacer un nuevo mínimo al día siguiente (retest del clímax)',
                        'Si el retest tiene volumen bajo, la capitulación está confirmada — suelo potencial',
                        'Entrada: cuando el precio supera el máximo de la vela de clímax',
                    ]},
                    { type: 'warning', content: 'El clímax bajista no significa "comprar inmediatamente". El precio puede seguir cayendo varios días antes de recuperar. Espera la confirmación: el precio debe superar el máximo de la vela de clímax con volumen creciente. Sin esa confirmación, puede haber más caída.' },
                ]
            },
            {
                heading: 'Clímax alcista: señal de techo',
                blocks: [
                    { type: 'text', content: 'El clímax alcista ocurre tras una subida prolongada. Una vela alcista enorme con volumen extraordinario que parece muy alcista pero es en realidad una señal de agotamiento. Es el último gran impulso antes del techo.' },
                    { type: 'chart', id: 'buying_climax' },
                    { type: 'table',
                        headers: ['Característica', 'Clímax alcista', 'Clímax bajista'],
                        rows: [
                            ['Contexto previo', 'Tendencia alcista larga', 'Tendencia bajista larga'],
                            ['Vela', 'Gran vela alcista', 'Gran vela bajista'],
                            ['Volumen', '3x+ del promedio', '3x+ del promedio'],
                            ['Señal', 'Techo potencial — reducir', 'Suelo potencial — vigilar'],
                            ['Confirmación', 'Cierre débil días siguientes', 'Volumen bajo en retest'],
                            ['Error común', 'Comprar pensando que sigue', 'Vender en el pánico'],
                        ]
                    },
                ]
            },
            {
                heading: 'Clímax de volumen en niveles clave',
                blocks: [
                    { type: 'text', content: 'El clímax de volumen es especialmente significativo cuando ocurre exactamente en un nivel técnico relevante: soporte histórico, resistencia mayor, zona de demanda o máximo de 52 semanas. La coincidencia de clímax + nivel clave multiplica la fiabilidad de la señal.' },
                    { type: 'chart', id: 'climax_at_level' },
                    { type: 'tip', label: 'PACIENCIA', content: 'Tras un clímax de volumen, el mercado suele entrar en un período de consolidación de días o semanas antes de que la reversión sea clara. No hay que entrar en el mismo día del clímax. La entrada óptima es en el retest posterior con bajo volumen, no en el clímax en sí.' },
                ]
            },
            {
                heading: 'Clímax real vs. volumen alto rutinario',
                blocks: [
                    { type: 'text', content: 'No todo pico de volumen es capitulación o euforia genuina. Días de vencimiento de opciones (opex), rebalanceos de índices, inclusión/exclusión de un índice, o una noticia puntual sin relación con la tesis de fondo pueden disparar el volumen 3x+ sin que exista un cambio real de sentimiento entre compradores y vendedores.' },
                    { type: 'table', headers: ['Señal', 'Clímax genuino', 'Volumen alto rutinario'], rows: [
                        ['Contexto previo', 'Tendencia extendida (varias semanas/meses)', 'Puede aparecer en cualquier punto, sin tendencia extendida'],
                        ['Tamaño de la vela', 'Rango de vela amplio, muy por encima del ATR habitual', 'Rango de vela normal o solo ligeramente mayor'],
                        ['Momento del mes', 'Cualquier día', 'Coincide con tercer viernes (opex), rebalanceo trimestral de índice, o fecha de earnings de un competidor/proveedor'],
                        ['Noticia asociada', 'Ausente o genérica — el movimiento es principalmente técnico/emocional', 'Evento identificable y puntual (M&A, cambio de índice, block trade institucional)'],
                    ]},
                    { type: 'warning', content: 'Antes de tratar un pico de volumen como clímax de capitulación o euforia, comprueba la fecha en el calendario (opex, rebalanceos) y busca si hay una noticia concreta detrás. Un volumen alto explicado por un evento mecánico puntual no tiene la misma fiabilidad como señal de reversión que un clímax emocional genuino.' },
                ]
            },
            {
                heading: 'Clímax apilados: cuando el primero no es el final',
                blocks: [
                    { type: 'text', content: 'En caídas severas o burbujas muy extendidas, puede aparecer más de un clímax en secuencia — un primer clímax que parece marcar suelo/techo, seguido de un rebote débil, y después un segundo (o tercer) clímax aún mayor. Comprar o vender agresivamente en el primer clímax de una secuencia de varios es uno de los errores más costosos de esta técnica.' },
                    { type: 'chart', id: 'climax_stacking' },
                    { type: 'steps', items: [
                        'Tras un clímax, espera el retest — no asumas que es el único ni el definitivo',
                        'Si el retest rompe el mínimo/máximo del clímax anterior con volumen similar o mayor, estás ante un clímax apilado, no ante una confirmación',
                        'Cada clímax adicional en la secuencia reduce la fiabilidad de "esta vez sí es el suelo/techo" hasta que el volumen empieza a decrecer en los sucesivos retests',
                        'La señal de mayor fiabilidad no es el primer clímax, sino el clímax en el que el retest posterior se hace con volumen claramente decreciente',
                    ]},
                    { type: 'tip', label: 'REGLA RSU', content: 'En movimientos extremos (crashes, burbujas de manía), reduce tamaño de posición en el primer clímax y resérvate munición para una posible segunda entrada si aparece un clímax apilado — no dispares toda la posición en la primera señal.' },
                ]
            },
            {
                heading: 'Medir el volumen relativo con precisión',
                blocks: [
                    { type: 'text', content: 'Decir "volumen 3x+" sin más contexto es impreciso si no se especifica frente a qué se compara. La forma correcta es calcular el volumen relativo (RVOL): volumen de la sesión dividido entre el volumen medio de un periodo de referencia, normalmente 20 o 50 sesiones.' },
                    { type: 'table', headers: ['RVOL', 'Interpretación'], rows: [
                        ['< 1.0x', 'Participación por debajo de lo normal — sin relevancia como clímax'],
                        ['1.5x – 2.5x', 'Volumen elevado pero dentro de rango habitual de días de tendencia'],
                        ['3x – 5x', 'Zona de clímax — merece atención si coincide con vela amplia y contexto de tendencia extendida'],
                        ['> 5x', 'Clímax extremo — poco frecuente, normalmente asociado a capitulación o pánico de mercado amplio'],
                    ]},
                    { type: 'warning', content: 'Usa siempre el promedio de volumen de los últimos 20-50 días como referencia, no un promedio anual ni el volumen de un solo día anterior. Comparar contra una sola sesión (por ejemplo "el doble que ayer") produce falsos positivos si el día de referencia ya era atípico.' },
                ]
            },
            {
                heading: 'Gestión de riesgo específica para trades de clímax',
                blocks: [
                    { type: 'text', content: 'Operar clímax de volumen implica entrar cerca de la máxima volatilidad reciente del valor. El stop y el tamaño de posición deben reflejar ese riesgo elevado, no el mismo criterio que usarías en una entrada de tendencia establecida.' },
                    { type: 'steps', items: [
                        'Stop en clímax bajista: por debajo del mínimo de la vela de clímax (o de su retest, si es más ajustado y sigue siendo técnicamente válido)',
                        'Stop en clímax alcista (para posiciones cortas o para cerrar largos): por encima del máximo de la vela de clímax',
                        'Reduce el tamaño de posición inicial frente a una entrada de tendencia estándar — la volatilidad implícita tras un clímax es mayor y el rango de la vela de invalidación suele ser más amplio',
                        'Considera escalar la entrada: una parte en la confirmación de ruptura del clímax, el resto en el retest de bajo volumen, en vez de una única entrada de tamaño completo',
                    ]},
                    { type: 'concept', title: 'Por qué el tamaño de posición importa más aquí que en otros setups', content: 'Un clímax de volumen, por definición, ocurre en el punto de mayor emoción del mercado sobre ese valor. Si la lectura es incorrecta y el clímax resulta ser apilado (ver sección anterior), el movimiento en contra puede ser rápido y amplio. Reducir el tamaño inicial es la forma de participar en la asimetría de la señal sin exponerse al peor escenario.' },
                ]
            },
        ]
    },

    // ── MÓDULO 8, LECCIÓN 4 ────────────────────────────────────────────────
    '8-4': {
        moduleId: 8,
        lessonIndex: 3,
        title: 'Participación Débil',
        duration: '8 min',
        intro: 'Un mercado que sube sin participación es un mercado frágil. La participación débil es la señal más temprana de que una tendencia está perdiendo fuerza — mucho antes de que el precio lo muestre claramente.',
        sections: [
            {
                heading: '¿Qué es la participación débil?',
                blocks: [
                    { type: 'text', content: 'La participación débil ocurre cuando el precio avanza pero el volumen es sistemáticamente inferior al promedio. No hablamos de un día puntual de bajo volumen — hablamos de una <strong>tendencia sostenida</strong> donde los impulsos alcistas tienen cada vez menos volumen. El dinero inteligente ya no está comprando.' },
                    { type: 'chart', id: 'weak_participation' },
                    { type: 'concept', title: 'El mercado que sube solo', content: 'Cuando una acción o índice sube con volumen decreciente, lo que está ocurriendo es que los vendedores se retiran (no hay oferta) más que los compradores están activos. Es una subida por ausencia de vendedores, no por presencia de compradores. Ese tipo de subida es mucho más frágil y susceptible a colapsar ante cualquier noticia negativa.' },
                ]
            },
            {
                heading: 'Señales de participación débil',
                blocks: [
                    { type: 'text', content: 'La participación débil no siempre es obvia en el precio. Hay que leerla específicamente en el volumen, comparando la evolución de los últimos meses con la tendencia histórica del activo.' },
                    { type: 'chart', id: 'weak_participation_signals' },
                    { type: 'steps', items: [
                        'Volumen en días alcistas sistemáticamente por debajo del promedio (< 70%)',
                        'Volumen en días bajistas igual o superior al de los días alcistas',
                        'Cada nuevo máximo de precio viene con menos volumen que el anterior',
                        'La media de volumen de 20 días está en descenso constante',
                        'Los gaps alcistas se cierran rápidamente al día siguiente',
                    ]},
                    { type: 'warning', content: 'La participación débil por sí sola no es señal de venta inmediata. El precio puede seguir subiendo semanas con participación débil. Es una señal de precaución: reduce el tamaño de nuevas posiciones, ajusta stops y prepárate para salir ante la primera señal de estructura.' },
                ]
            },
            {
                heading: 'Divergencia volumen-precio: la señal más potente',
                blocks: [
                    { type: 'text', content: 'La divergencia volumen-precio ocurre cuando el precio marca nuevos máximos pero el volumen marca nuevos mínimos. Es la forma más clara de participación débil y ha precedido la mayoría de los grandes techos de mercado históricos.' },
                    { type: 'chart', id: 'volume_price_divergence' },
                    { type: 'table',
                        headers: ['Patrón', 'Precio', 'Volumen', 'Señal'],
                        rows: [
                            ['Confirmación alcista', 'Nuevo máximo', 'Nuevo máximo', '✅ Tendencia sana'],
                            ['Divergencia bajista', 'Nuevo máximo', 'Mínimo decreciente', '⚠️ Precaución — techo potencial'],
                            ['Confirmación bajista', 'Nuevo mínimo', 'Nuevo máximo', '🔴 Presión vendedora fuerte'],
                            ['Divergencia alcista', 'Nuevo mínimo', 'Mínimo decreciente', '🟡 Vendedores agotándose'],
                        ]
                    },
                    { type: 'tip', label: 'TIMEFRAME', content: 'La divergencia volumen-precio es más fiable en semanal y mensual que en diario. En diario puede haber muchas divergencias falsas por ruido. Cuando la divergencia aparece en semanal, especialmente coincidiendo con una resistencia técnica relevante, la probabilidad de reversión es muy alta.' },
                ]
            },
            {
                heading: 'Recuperar la participación: señal de continuación',
                blocks: [
                    { type: 'text', content: 'Cuando una tendencia alcista lleva tiempo con participación débil y de repente aparece un día o semana con volumen muy superior al promedio en dirección alcista, es una señal de que el dinero institucional ha vuelto. Esta recuperación de participación suele preceder una aceleración de la tendencia.' },
                    { type: 'chart', id: 'participation_recovery' },
                    { type: 'concept', title: 'El volumen de acumulación silenciosa', content: 'Los institucionales acumulan posición durante períodos de bajo volumen general. Compran en pequeñas cantidades durante días o semanas sin revelar su posición. Cuando terminan de acumular y empiezan a impulsar, el volumen se dispara de golpe. Ese día de volumen explosivo tras una base de bajo volumen es una de las señales de entrada más potentes disponibles.' },
                ]
            },
        ]
    },
    // ── MÓDULO 9, LECCIÓN 1 ────────────────────────────────────────────────
    '9-1': {
        moduleId: 9,
        lessonIndex: 0,
        title: 'Triángulo Ascendente',
        duration: '8 min',
        intro: 'El triángulo ascendente es uno de los patrones de continuación más fiables del análisis técnico. La presión compradora sistemática que lo define no deja duda sobre quién está ganando el duelo entre compradores y vendedores.',
        sections: [
            {
                heading: 'Anatomía del triángulo ascendente',
                blocks: [
                    { type: 'text', content: 'El triángulo ascendente tiene dos elementos: una <strong>resistencia horizontal</strong> (línea superior plana) y una <strong>serie de mínimos crecientes</strong> (línea inferior ascendente). Los compradores empujan el precio cada vez más alto en cada corrección, mientras los vendedores defienden el mismo nivel de resistencia repetidamente. La tensión entre ambas fuerzas comprime el precio hasta que algo cede.' },
                    { type: 'chart', id: 'ascending_triangle_anatomy' },
                    { type: 'concept', title: 'Por qué es un patrón alcista', content: 'En el triángulo ascendente, los compradores son progresivamente más agresivos (mínimos más altos) mientras los vendedores mantienen la misma posición (resistencia plana). Cada rechazo en la resistencia consume menos energía compradora. Eventualmente, los compradores agotan a los vendedores y el precio rompe al alza.' },
                ]
            },
            {
                heading: 'Requisitos para un triángulo válido',
                blocks: [
                    { type: 'text', content: 'No cualquier consolidación con una resistencia plana es un triángulo ascendente válido. Hay criterios mínimos que debe cumplir para ser operable:' },
                    { type: 'chart', id: 'ascending_triangle_valid' },
                    { type: 'steps', items: [
                        'Al menos <strong>dos toques</strong> en la resistencia horizontal (mínimo para definirla)',
                        'Al menos <strong>dos mínimos crecientes</strong> que permitan trazar la línea inferior',
                        'Duración mínima de <strong>3-4 semanas</strong> — los patrones más cortos son menos fiables',
                        'El precio debe comprimir progresivamente — las oscilaciones se reducen hacia el vértice',
                        'Volumen decreciente durante la formación y explosivo en la ruptura',
                    ]},
                    { type: 'warning', content: 'Un triángulo ascendente dentro de una tendencia bajista no es alcista. El contexto de la tendencia mayor determina la dirección esperada de la ruptura. Un triángulo ascendente en tendencia bajista puede romper a la baja — el patrón favorece al alza pero no lo garantiza.' },
                ]
            },
            {
                heading: 'La ruptura y el objetivo de precio',
                blocks: [
                    { type: 'text', content: 'La ruptura válida del triángulo ascendente debe ocurrir por encima de la resistencia horizontal con volumen superior al promedio. El objetivo de precio se calcula proyectando la <strong>altura máxima del triángulo</strong> desde el punto de ruptura.' },
                    { type: 'chart', id: 'ascending_triangle_breakout' },
                    { type: 'table',
                        headers: ['Elemento', 'Cálculo', 'Ejemplo'],
                        rows: [
                            ['Altura del triángulo', 'Resistencia − primer mínimo del patrón', '150 − 130 = 20 puntos'],
                            ['Punto de ruptura', 'Nivel de la resistencia horizontal', '150'],
                            ['Objetivo mínimo', 'Ruptura + Altura', '150 + 20 = 170'],
                            ['Stop loss', 'Bajo el último mínimo del triángulo', '< 143 (último HL)'],
                        ]
                    },
                    { type: 'tip', label: 'ENTRADA', content: 'La entrada más conservadora es esperar el cierre por encima de la resistencia con volumen y luego comprar en la apertura del día siguiente. Si el precio vuelve a testear la resistencia rota (ahora soporte) con bajo volumen, esa es la entrada de menor riesgo con stop más pequeño.' },
                ]
            },
            {
                heading: 'Triángulo ascendente en tendencia alcista vs rango',
                blocks: [
                    { type: 'text', content: 'El mismo patrón tiene diferente significado según dónde aparece. En tendencia alcista es un patrón de continuación de alta probabilidad. En rango o después de una caída, es potencialmente un patrón de acumulación pero necesita más confirmación.' },
                    { type: 'chart', id: 'ascending_triangle_context' },
                    { type: 'concept', title: 'El triángulo de continuación vs el de reversión', content: 'Cuando el triángulo ascendente aparece después de un impulso alcista (el precio ha subido y consolida), la probabilidad de ruptura al alza es del 70-80%. Cuando aparece después de una tendencia bajista, como posible reversión, la probabilidad baja al 50-60%. Siempre opera a favor del contexto mayor.' },
                ]
            },
        ]
    },

    // ── MÓDULO 9, LECCIÓN 2 ────────────────────────────────────────────────
    '9-2': {
        moduleId: 9,
        lessonIndex: 1,
        title: 'Triángulo Descendente',
        duration: '8 min',
        intro: 'El triángulo descendente es el espejo exacto del ascendente. Los vendedores son cada vez más agresivos mientras los compradores defienden el mismo soporte. La presión bajista se acumula hasta que el soporte cede y el precio colapsa.',
        sections: [
            {
                heading: 'Anatomía del triángulo descendente',
                blocks: [
                    { type: 'text', content: 'El triángulo descendente tiene una <strong>línea de soporte horizontal</strong> (inferior plana) y una <strong>serie de máximos decrecientes</strong> (línea superior descendente). Los vendedores entran cada vez antes — no esperan al máximo anterior para vender. Los compradores mientras tanto defienden el mismo soporte una y otra vez.' },
                    { type: 'chart', id: 'descending_triangle_anatomy' },
                    { type: 'concept', title: 'La lógica bajista del patrón', content: 'Cada rebote en el soporte del triángulo descendente es más débil que el anterior. Los compradores están defendiendo, pero cada vez con menos fuerza. Los vendedores, en cambio, actúan con creciente agresividad. Esta asimetría resuelve casi siempre con la ruptura del soporte.' },
                ]
            },
            {
                heading: 'La ruptura bajista: señal y objetivo',
                blocks: [
                    { type: 'text', content: 'La ruptura del soporte horizontal del triángulo descendente suele ser rápida y violenta. Los stops de todos los que compraron en los rebotes del soporte se activan simultáneamente, acelerando la caída.' },
                    { type: 'chart', id: 'descending_triangle_breakdown' },
                    { type: 'steps', items: [
                        'El precio rompe el soporte con una vela bajista de gran tamaño',
                        'El volumen es significativamente superior al promedio',
                        'Los stops de compradores se activan en cascada — el movimiento se acelera',
                        'Objetivo: soporte − altura del triángulo',
                        'Stop en corto: por encima del último máximo del triángulo (último LH)',
                    ]},
                    { type: 'tip', label: 'FALSA RUPTURA', content: 'Los triángulos descendentes también producen falsas rupturas bajistas — el precio cae bajo el soporte, activa stops, y vuelve a entrar al triángulo. Si el precio cierra de vuelta dentro del triángulo tras la ruptura, sal inmediatamente del corto. La posibilidad de ruptura alcista aumenta significativamente después de una falsa ruptura bajista.' },
                ]
            },
            {
                heading: 'Triángulo descendente en tendencia bajista',
                blocks: [
                    { type: 'text', content: 'En tendencia bajista, el triángulo descendente es un patrón de continuación de alta probabilidad. El precio ha caído, consolida formando el triángulo, y luego continúa a la baja. La fiabilidad es mayor cuando aparece después de un impulso bajista claro.' },
                    { type: 'chart', id: 'descending_triangle_trend' },
                    { type: 'table',
                        headers: ['Contexto', 'Dirección esperada', 'Probabilidad'],
                        rows: [
                            ['En tendencia bajista', 'Ruptura bajista (continuación)', '70-75%'],
                            ['En rango lateral', 'Ruptura bajista (sesgo)', '55-60%'],
                            ['En tendencia alcista', 'Ruptura alcista posible (reversión rara)', '40-50%'],
                            ['Tras impulso bajista fuerte', 'Ruptura bajista (alta conv.)', '75-80%'],
                        ]
                    },
                ]
            },
            {
                heading: 'Gestión del trade en triángulo descendente',
                blocks: [
                    { type: 'text', content: 'Si operas el triángulo descendente como corto, la gestión es diferente a una posición larga: los movimientos bajistas son más rápidos y la cobertura de cortos puede crear rebotes violentos en cualquier momento.' },
                    { type: 'chart', id: 'descending_triangle_management' },
                    { type: 'concept', title: 'Cobertura de cortos y rebotes trampa', content: 'Cuando el precio cae significativamente, los traders en corto empiezan a cerrar posiciones (comprar para cubrir). Esto crea rebotes bruscos e inesperados que pueden ser confusos. En un triángulo descendente, el primer rebote significativo tras la ruptura suele ser el retest del soporte roto (ahora resistencia) — es la oportunidad de añadir al corto o entrar si te perdiste la ruptura.' },
                ]
            },
        ]
    },

    // ── MÓDULO 9, LECCIÓN 3 ────────────────────────────────────────────────
    '9-3': {
        moduleId: 9,
        lessonIndex: 2,
        title: 'Rectángulo',
        duration: '8 min',
        intro: 'El rectángulo es el patrón más limpio y más fácil de operar. Dos niveles horizontales paralelos que contienen el precio. Sin inclinación, sin ambigüedad. Lo que importa es lo que ocurre en los extremos y cuándo y cómo el precio escapa.',
        sections: [
            {
                heading: 'Formación del rectángulo',
                blocks: [
                    { type: 'text', content: 'Un rectángulo se forma cuando el precio oscila repetidamente entre dos niveles horizontales bien definidos: soporte y resistencia. Cada toque del soporte atrae compradores, cada toque de la resistencia atrae vendedores. Las fuerzas están equilibradas — nadie puede dominar.' },
                    { type: 'chart', id: 'rectangle_formation' },
                    { type: 'concept', title: 'Rectángulo de acumulación vs distribución', content: 'Un rectángulo tras una tendencia alcista prolongada suele ser distribución: los institucionales venden mientras el precio se mantiene. Un rectángulo tras una tendencia bajista prolongada suele ser acumulación: los institucionales compran mientras el precio consolida. El contexto previo determina la interpretación.' },
                ]
            },
            {
                heading: 'Operar dentro del rectángulo',
                blocks: [
                    { type: 'text', content: 'El rectángulo ofrece dos estrategias distintas: operar los rebotes dentro del rango o esperar la ruptura. Ambas son válidas pero tienen perfiles de riesgo muy diferentes.' },
                    { type: 'chart', id: 'rectangle_trading' },
                    { type: 'table',
                        headers: ['Estrategia', 'Entrada', 'Stop', 'Objetivo', 'Cuándo usarla'],
                        rows: [
                            ['Rebote en soporte', 'Toque del soporte + vela alcista', 'Bajo el soporte −1%', 'Resistencia del rango', 'Rectángulo amplio (>10%), varios toques'],
                            ['Rebote en resistencia', 'Toque de resistencia + vela bajista', 'Sobre la resistencia +1%', 'Soporte del rango', 'Rectángulo amplio, operas cortos'],
                            ['Ruptura alcista', 'Cierre sobre resistencia con vol.', 'Dentro del rango (−1 de res.)', 'Soporte + amplitud del rango', 'Siempre — mayor probabilidad'],
                            ['Ruptura bajista', 'Cierre bajo soporte con vol.', 'Dentro del rango (+1 de sup.)', 'Resistencia − amplitud del rango', 'Siempre — mayor probabilidad'],
                        ]
                    },
                    { type: 'warning', content: 'No operes rebotes en un rectángulo estrecho (menos del 5% de amplitud). El ratio riesgo/recompensa es desfavorable — el stop tiene que estar fuera del rango para ser válido, lo que lo hace demasiado grande respecto al objetivo.' },
                ]
            },
            {
                heading: 'La ruptura del rectángulo: señal y objetivo',
                blocks: [
                    { type: 'text', content: 'La ruptura del rectángulo proyecta un objetivo igual a la <strong>amplitud del rango</strong> desde el punto de ruptura. Si el rango tiene 20 puntos de altura y el precio rompe al alza en 150, el objetivo mínimo es 170.' },
                    { type: 'chart', id: 'rectangle_breakout' },
                    { type: 'steps', items: [
                        'Mide la amplitud del rectángulo (resistencia − soporte)',
                        'Espera el cierre fuera del rango con volumen superior al promedio',
                        'Proyecta la amplitud desde el punto de ruptura',
                        'Coloca stop dentro del rango (por debajo de la resistencia rota si es ruptura alcista)',
                        'Si el precio vuelve a entrar en el rango, sal — la ruptura ha fallado',
                    ]},
                ]
            },
            {
                heading: 'Rectángulos de largo plazo: los más potentes',
                blocks: [
                    { type: 'text', content: 'Los rectángulos que se forman durante meses o incluso años en gráficos semanales y mensuales generan las rupturas más potentes. Cuanto más tiempo el precio ha estado confinado, más energía acumulada hay para el movimiento posterior a la ruptura.' },
                    { type: 'chart', id: 'rectangle_longterm' },
                    { type: 'tip', label: 'MÁXIMOS HISTÓRICOS', content: 'Uno de los patrones más potentes del mercado es cuando un activo rompe un rectángulo de largo plazo que incluyó su máximo histórico anterior. La ruptura de un ATH tras años de consolidación suele generar un movimiento de magnitud similar a todo el rango previo. Los mejores ejemplos históricos de acciones multiplicando 5-10x empiezan con este patrón.' },
                ]
            },
        ]
    },

    // ── MÓDULO 9, LECCIÓN 4 ────────────────────────────────────────────────
    '9-4': {
        moduleId: 9,
        lessonIndex: 3,
        title: 'Bandera y Asta',
        duration: '9 min',
        intro: 'La bandera es el patrón de continuación más limpio y más rápido de resolver. Un movimiento fuerte seguido de una pequeña corrección ordenada. Cuando el precio retoma el movimiento original, suele hacerlo con la misma fuerza que el impulso inicial.',
        sections: [
            {
                heading: 'Anatomía de la bandera',
                blocks: [
                    { type: 'text', content: 'El patrón bandera tiene dos partes: el <strong>asta</strong> (impulso inicial fuerte y rápido) y la <strong>bandera</strong> (consolidación en canal inclinado ligeramente en contra del asta). La bandera es una corrección ordenada y de bajo volumen que "carga" el siguiente impulso.' },
                    { type: 'chart', id: 'flag_anatomy' },
                    { type: 'concept', title: 'Por qué funciona la bandera', content: 'El asta representa un desequilibrio fuerte entre compradores y vendedores. La bandera es el período donde el mercado "descansa" — los compradores que entraron en el asta realizan ganancias parciales y los que se perdieron el movimiento esperan la consolidación para entrar. Cuando este equilibrio se rompe de nuevo en la dirección original, el movimiento se reanuda.' },
                ]
            },
            {
                heading: 'Características de una bandera de calidad',
                blocks: [
                    { type: 'text', content: 'No toda consolidación después de un impulso es una bandera válida. Hay características específicas que definen una bandera de alta calidad:' },
                    { type: 'chart', id: 'flag_quality' },
                    { type: 'steps', items: [
                        '<strong>El asta:</strong> movimiento fuerte, rápido (1-4 semanas), en una dirección clara con poco retroceso',
                        '<strong>Ángulo de la bandera:</strong> la consolidación se inclina ligeramente en contra del asta (bandera alcista inclina hacia abajo, bajista hacia arriba)',
                        '<strong>Duración:</strong> entre 1 y 4 semanas. Banderas más largas se convierten en canales o triángulos',
                        '<strong>Volumen:</strong> decreciente durante la bandera, explosivo en la ruptura',
                        '<strong>Corrección:</strong> no más del 38-50% del asta. Si retrocede más, pierde la calidad de bandera',
                    ]},
                    { type: 'warning', content: 'Una bandera que retrocede más del 61.8% del asta (nivel de Fibonacci) deja de ser una bandera sana. Puede seguir funcionando como patrón de continuación, pero la probabilidad de éxito baja significativamente. Con correcciones tan profundas, el movimiento original ya no tiene la misma fuerza.' },
                ]
            },
            {
                heading: 'Entrada y objetivo en la bandera',
                blocks: [
                    { type: 'text', content: 'La ruptura de la bandera es el momento de entrada. El objetivo se calcula proyectando la longitud del asta desde el punto de ruptura de la bandera.' },
                    { type: 'chart', id: 'flag_entry_target' },
                    { type: 'table',
                        headers: ['Elemento', 'Descripción'],
                        rows: [
                            ['Asta', 'Desde el inicio del impulso hasta el inicio de la bandera'],
                            ['Punto de ruptura', 'Cuando el precio supera la línea superior de la bandera (alcista)'],
                            ['Objetivo', 'Punto de ruptura + longitud del asta'],
                            ['Stop', 'Bajo la línea inferior de la bandera o bajo el 50% del asta'],
                            ['Volumen', 'Ruptura debe venir con volumen 1.5x+ del promedio'],
                        ]
                    },
                    { type: 'tip', label: 'TIMING', content: 'La bandera suele resolverse en 1-3 semanas. Si después de 4 semanas el precio no ha roto la bandera en ninguna dirección, el patrón está perdiendo validez. Cuanto más rápido se resuelva la bandera, mayor suele ser el movimiento posterior.' },
                ]
            },
            {
                heading: 'Bandera bajista: el mismo patrón al revés',
                blocks: [
                    { type: 'text', content: 'La bandera bajista tiene un asta bajista (caída rápida) seguida de una consolidación que se inclina ligeramente hacia arriba. El volumen decrece en la bandera y explota cuando el precio rompe a la baja. El objetivo es el mismo: longitud del asta proyectada desde la ruptura.' },
                    { type: 'chart', id: 'bear_flag' },
                    { type: 'concept', title: 'La bandera bajista como trampa de compradores', content: 'La consolidación ligeramente alcista de la bandera bajista atrae compradores que piensan que la caída ha terminado. Cuando el precio rompe a la baja, esos compradores quedan atrapados y sus stops se activan, acelerando el movimiento bajista. Esta mecánica hace que las banderas bajistas produzcan movimientos especialmente rápidos y violentos.' },
                ]
            },
        ]
    },
    // ── MÓDULO 10, LECCIÓN 1 ───────────────────────────────────────────────
    '10-1': {
        moduleId: 10,
        lessonIndex: 0,
        title: 'Sesgo Mensual',
        duration: '9 min',
        intro: 'El sesgo mensual es la pregunta más importante que un trader debe responder antes de abrir cualquier posición: ¿qué dirección favorece el mercado a gran escala este mes? Todo lo demás — setups diarios, patrones de velas, niveles intradiarios — es secundario si el sesgo mensual apunta en tu contra.',
        sections: [
            {
                heading: 'Qué es el sesgo mensual y por qué importa',
                blocks: [
                    { type: 'text', content: 'El sesgo mensual es la dirección dominante del mercado en el timeframe mensual: alcista, bajista o neutral. Determina qué tipo de operaciones tienen más probabilidad de éxito en todos los timeframes menores. Operar en contra del sesgo mensual es nadar contra la corriente — puedes hacerlo, pero el esfuerzo es mucho mayor y el resultado mucho menos predecible.' },
                    { type: 'chart', id: 'monthly_bias_definition' },
                    { type: 'concept', title: 'El sesgo como filtro, no como señal', content: 'El sesgo mensual no te dice cuándo entrar ni cuándo salir. Te dice qué tipo de operaciones filtrar. Con sesgo alcista, descartas los cortos y solo buscas longs. Con sesgo bajista, descartas los longs y solo buscas cortos o permaneces en cash. Con sesgo neutral, reduces el tamaño de todas las posiciones y exiges más confirmación.' },
                ]
            },
            {
                heading: 'Cómo determinar el sesgo mensual',
                blocks: [
                    { type: 'text', content: 'El sesgo mensual se determina leyendo la estructura de precio en el gráfico mensual. No necesitas indicadores — solo la lectura de máximos y mínimos relativos y la posición del precio respecto a sus medias.' },
                    { type: 'chart', id: 'monthly_bias_how' },
                    { type: 'steps', items: [
                        '<strong>Estructura:</strong> ¿los últimos 3-6 meses muestran HH+HL (alcista), LH+LL (bajista) o sin dirección clara (neutral)?',
                        '<strong>Medias:</strong> ¿el precio está por encima o por debajo de la MA10 mensual?',
                        '<strong>Zona:</strong> ¿el precio está en zona de demanda (comprar), oferta (vender) o en tierra de nadie (esperar)?',
                        '<strong>Vela del mes:</strong> ¿la vela mensual actual es alcista o bajista? ¿Con qué volumen?',
                        '<strong>Contexto macro:</strong> ¿hay factores externos relevantes (FED, earnings season, estacionalidad)?',
                    ]},
                    { type: 'tip', label: 'RITUAL SEMANAL', content: 'Cada domingo antes de la semana de trading, dedica 10 minutos a revisar el sesgo mensual. Escríbelo explícitamente: "Sesgo mensual SPX: ALCISTA — precio sobre MA10, estructura HH+HL, sin resistencia mayor próxima". Tener el sesgo escrito evita que el ruido diario te haga olvidar el cuadro grande.' },
                ]
            },
            {
                heading: 'Cambio de sesgo mensual: cuándo reconocerlo',
                blocks: [
                    { type: 'text', content: 'El sesgo mensual no cambia de un día para otro. Los cambios verdaderos tardan varios meses en confirmarse — y esa lentitud es una ventaja, no una desventaja. Te da tiempo de reaccionar sin ser víctima del ruido.' },
                    { type: 'chart', id: 'monthly_bias_change' },
                    { type: 'table',
                        headers: ['Señal', 'Peso', 'Acción'],
                        rows: [
                            ['Cierre mensual bajo MA10', 'Alto', 'Reducir posiciones largas al 50%'],
                            ['Primer LH en mensual', 'Muy alto', 'Reducir al 25%, vigilar estructura'],
                            ['Primer LL en mensual', 'Definitivo', 'Cambio de sesgo a bajista confirmado'],
                            ['Cierre mensual sobre MA10 en bajista', 'Alto', 'Cubrir cortos parcialmente'],
                            ['Primer HH en mensual desde bajista', 'Definitivo', 'Cambio de sesgo a alcista'],
                        ]
                    },
                ]
            },
            {
                heading: 'Sesgo mensual por sectores y activos',
                blocks: [
                    { type: 'text', content: 'El sesgo mensual no tiene que ser el mismo para todos los activos. El SPX puede tener sesgo alcista mientras el sector energético tiene sesgo bajista. <strong>Opera en los activos cuyo sesgo mensual individual coincide con el sesgo del mercado general.</strong>' },
                    { type: 'chart', id: 'monthly_bias_sectors' },
                    { type: 'concept', title: 'Alineación doble: mercado + sector + activo', content: 'La probabilidad máxima se alcanza cuando el sesgo mensual del mercado general (SPX), del sector y del activo individual apuntan todos en la misma dirección. Esta triple alineación es rara, pero cuando ocurre, es el momento de mayor convicción y mayor tamaño de posición.' },
                ]
            },
        ]
    },

    // ── MÓDULO 10, LECCIÓN 2 ───────────────────────────────────────────────
    '10-2': {
        moduleId: 10,
        lessonIndex: 1,
        title: 'Estructura Semanal',
        duration: '9 min',
        intro: 'Si el mensual es el mapa y el diario es la entrada, el semanal es el territorio real donde operas. La estructura semanal te dice si el mercado está en condiciones de darte un trade en la próxima semana o si debes esperar.',
        sections: [
            {
                heading: 'La estructura semanal como semáforo',
                blocks: [
                    { type: 'text', content: 'El gráfico semanal funciona como semáforo para tus decisiones de la semana. <strong>Verde</strong>: estructura alcista, HH+HL, precio sobre medias → busca longs. <strong>Rojo</strong>: estructura bajista, LH+LL, precio bajo medias → no entres longs. <strong>Amarillo</strong>: estructura indecisa, precio cerca de nivel clave → espera.' },
                    { type: 'chart', id: 'weekly_structure_semaphore' },
                    { type: 'concept', title: 'Leer la última vela semanal', content: 'La vela semanal que acaba de cerrarse el viernes es la información más reciente que tienes. Su tamaño, dirección, mechas y volumen te dicen cómo cerró la semana el dinero institucional. Una vela semanal alcista grande con cierre en máximos es más informativa que 5 días de análisis diario.' },
                ]
            },
            {
                heading: 'Estructura semanal vs sesgo mensual: qué hacer cuando divergen',
                blocks: [
                    { type: 'text', content: 'A veces el sesgo mensual es alcista pero la estructura semanal es bajista — el mercado está en corrección dentro de una tendencia alcista. Este es el escenario más común y también el más confuso para traders sin metodología clara.' },
                    { type: 'chart', id: 'weekly_vs_monthly' },
                    { type: 'table',
                        headers: ['Sesgo mensual', 'Estructura semanal', 'Decisión'],
                        rows: [
                            ['Alcista', 'Alcista', '✅ Buscar longs con alta convicción'],
                            ['Alcista', 'Correctivo (lateral/bajista)', '⏸ Esperar — el semanal puede volver a alcista'],
                            ['Alcista', 'Bajista fuerte (LH+LL)', '⚠️ Posible cambio de sesgo — reducir'],
                            ['Bajista', 'Bajista', '🔴 Solo cortos o cash'],
                            ['Bajista', 'Rebote alcista', '⏸ No comprar — es un rebote en bajista'],
                            ['Neutral', 'Cualquiera', '🔹 Reducir tamaño, exigir más confirmación'],
                        ]
                    },
                    { type: 'tip', label: 'REGLA', content: 'En mensual alcista + semanal correctivo: no abras nuevas posiciones largas, pero tampoco cierres las existentes que están en ganancia. La corrección semanal en tendencia mensual alcista es normal. Espera que el semanal recupere estructura alcista antes de añadir.' },
                ]
            },
            {
                heading: 'Identificar el punto de giro semanal',
                blocks: [
                    { type: 'text', content: 'El punto de giro semanal es el nivel donde el mercado en corrección tiene mayor probabilidad de recuperar la tendencia mensual. Identificarlo correctamente te da la entrada de mejor calidad de toda la semana.' },
                    { type: 'chart', id: 'weekly_pivot_point' },
                    { type: 'steps', items: [
                        'El mercado ha tenido sesgo mensual alcista con HH+HL durante meses',
                        'En la última semana o dos, el precio ha retrocedido',
                        'Identifica la zona de soporte: EMA 21 semanal, último HL, zona de demanda relevante',
                        'Espera que el precio llegue a esa zona con volumen bajo (retroceso sin convicción)',
                        'Cuando aparece una vela de señal alcista (pin bar, engulfing) en la zona: esa es tu entrada',
                    ]},
                ]
            },
            {
                heading: 'Zonas de interés semanal para la próxima semana',
                blocks: [
                    { type: 'text', content: 'El domingo o lunes por la mañana, antes de que empiece la semana de trading, debes identificar las zonas de interés del gráfico semanal: dónde el precio puede rebotar, dónde puede ser rechazado, qué niveles vigilar.' },
                    { type: 'chart', id: 'weekly_zones_planning' },
                    { type: 'concept', title: 'El plan de la semana', content: 'Un plan de semana efectivo tiene tres elementos: (1) el sesgo semanal (alcista/bajista/neutral), (2) las dos o tres zonas de precio más relevantes donde actuarás, y (3) qué tipo de señal necesitas ver en esas zonas para entrar. Si el precio no llega a tus zonas y no da señal, no hay trade esa semana. La paciencia es parte del plan.' },
                ]
            },
        ]
    },

    // ── MÓDULO 10, LECCIÓN 3 ───────────────────────────────────────────────
    '10-3': {
        moduleId: 10,
        lessonIndex: 2,
        title: 'Setup Diario',
        duration: '9 min',
        intro: 'Con el sesgo mensual definido y la estructura semanal analizada, el gráfico diario es donde buscas el setup concreto. No cualquier movimiento diario — solo el que está perfectamente alineado con los dos timeframes superiores.',
        sections: [
            {
                heading: 'El setup diario dentro del contexto mayor',
                blocks: [
                    { type: 'text', content: 'Un setup diario sin contexto es ruido. El mismo patrón — un engulfing alcista, un pin bar en soporte — tiene probabilidades completamente diferentes dependiendo de si el mensual y el semanal están alineados o no. Con alineación, la probabilidad sube. Sin alineación, es simplemente ruido estadístico.' },
                    { type: 'chart', id: 'daily_setup_context' },
                    { type: 'concept', title: 'La cadena de confirmación', content: 'Antes de entrar en cualquier posición diaria, verifica la cadena completa: (1) ¿El sesgo mensual está a favor? (2) ¿La estructura semanal está alineada? (3) ¿El nivel diario donde aparece el setup es relevante? (4) ¿El patrón de vela es claro? Si falla cualquiera de los cuatro puntos, el setup no es válido.' },
                ]
            },
            {
                heading: 'Los tres tipos de setup diario válido',
                blocks: [
                    { type: 'text', content: 'En alineación multi-temporalidad, hay tres setups diarios que tienen la mayor probabilidad de éxito. Son los únicos que merece la pena operar cuando se busca alta convicción.' },
                    { type: 'chart', id: 'daily_setup_types' },
                    { type: 'steps', items: [
                        '<strong>Setup de retroceso:</strong> el precio ha subido (en tendencia alcista), retrocede al EMA 21 diario o a una zona de demanda, y muestra vela de señal alcista. El más común y fiable.',
                        '<strong>Setup de ruptura:</strong> el precio consolida en base y rompe al alza con volumen. Se entra en el cierre del día de ruptura o en el retest. Menos frecuente pero con mayor potencial.',
                        '<strong>Setup de inversión:</strong> en fin de corrección, el precio llega a soporte semanal/mensual y el diario muestra señal clara de giro. El más potente pero también el que más confirmación requiere.',
                    ]},
                    { type: 'warning', content: 'No entres en un setup diario si el precio está en medio del rango semanal — sin cerca de soporte ni de resistencia relevante. Los mejores setups diarios ocurren en los extremos del rango semanal, no en el centro. En el centro del rango, el precio puede ir en cualquier dirección.' },
                ]
            },
            {
                heading: 'Gestión del setup diario: cuándo escalar',
                blocks: [
                    { type: 'text', content: 'Cuando mensual, semanal y diario están perfectamente alineados y el setup diario es de alta calidad, es el momento de usar un tamaño de posición mayor. La alineación multi-temporalidad justifica una apuesta más grande.' },
                    { type: 'chart', id: 'daily_setup_scaling' },
                    { type: 'table',
                        headers: ['Alineación', 'Tamaño de posición', 'Stop', 'Gestión'],
                        rows: [
                            ['M↑ + S↑ + D setup', '100% (máximo)', 'Bajo el setup', 'Aguantar con trailing stop semanal'],
                            ['M↑ + S neutral + D setup', '50-60%', 'Bajo el setup', 'Salida parcial en primera resistencia'],
                            ['M↑ + S↓ + D rebote', '25-30%', 'Muy ajustado', 'Salida rápida — operación contraria'],
                            ['M neutral + S + D', '30-40%', 'Bajo el setup', 'Objetivo conservador'],
                        ]
                    },
                ]
            },
            {
                heading: 'Timing de entrada intradiario',
                blocks: [
                    { type: 'text', content: 'Una vez identificado el setup diario, el timing exacto de entrada puede mejorarse usando el gráfico de 4 horas o incluso el de 1 hora. Esto no cambia la tesis — solo optimiza el precio de entrada y reduce el stop.' },
                    { type: 'chart', id: 'daily_intraday_timing' },
                    { type: 'concept', title: 'El timeframe de ejecución', content: 'Si en diario ves que el precio ha llegado a tu zona de interés, bajas a 4h para ver la acción del precio con más detalle. Buscas el primer giro alcista en 4h que confirme que el nivel diario está aguantando. Entras en esa señal de 4h con el stop bajo el mínimo de 4h. El resultado: mismo trade, stop mucho más pequeño, mejor ratio.' },
                ]
            },
        ]
    },

    // ── MÓDULO 10, LECCIÓN 4 ───────────────────────────────────────────────
    '10-4': {
        moduleId: 10,
        lessonIndex: 3,
        title: 'Trigger en TF Menor',
        duration: '9 min',
        intro: 'El trigger es el último elemento de la cadena. Tienes el contexto (mensual), la estructura (semanal), el setup (diario) — ahora necesitas la señal exacta que activa la entrada. El trigger en timeframe menor es lo que convierte el análisis en acción.',
        sections: [
            {
                heading: '¿Qué es un trigger y para qué sirve?',
                blocks: [
                    { type: 'text', content: 'Un trigger (gatillo) es una señal específica y objetiva que activa tu entrada. No es intuición ni una sensación de que el precio "parece" que va a subir. Es un evento concreto: una vela de un tipo específico en un nivel específico con un volumen mínimo.' },
                    { type: 'chart', id: 'trigger_definition' },
                    { type: 'concept', title: 'Sin trigger no hay entrada', content: 'La disciplina del trigger elimina la peor causa de pérdidas en trading: entrar demasiado pronto. Si el precio llega a tu zona de interés pero no da el trigger, no entras. Aunque el precio finalmente suba sin ti — no entras sin trigger. La próxima vez el setup que no tuvo trigger puede ser el que falla. El trigger protege tu capital en los casos en que el nivel no aguanta.' },
                ]
            },
            {
                heading: 'Triggers válidos por timeframe',
                blocks: [
                    { type: 'text', content: 'El tipo de trigger apropiado depende del timeframe en que estás operando. Los triggers de timeframes mayores son más lentos pero más fiables. Los de timeframes menores son más rápidos pero con más ruido.' },
                    { type: 'chart', id: 'trigger_by_timeframe' },
                    { type: 'table',
                        headers: ['TF de setup', 'TF del trigger', 'Señal de trigger'],
                        rows: [
                            ['Mensual', 'Semanal', 'Engulfing semanal, pin bar semanal en zona'],
                            ['Semanal', 'Diario', 'Engulfing diario, pin bar diario, inside bar ruptura'],
                            ['Diario', '4H', 'HH en 4H desde zona, vela alcista en 4H'],
                            ['4H', '1H', 'Primer HH en 1H, vela de señal en 1H'],
                            ['1H', '15min', 'Ruptura de micro-resistencia en 15min'],
                        ]
                    },
                ]
            },
            {
                heading: 'El proceso completo: de sesgo a trigger',
                blocks: [
                    { type: 'text', content: 'El proceso de trading con alineación multi-temporalidad sigue siempre el mismo flujo, de mayor a menor timeframe. Este proceso elimina la improvisación y convierte el trading en un sistema reproducible.' },
                    { type: 'chart', id: 'mtf_full_process' },
                    { type: 'steps', items: [
                        '<strong>Domingo:</strong> revisar sesgo mensual y estructura semanal. Definir zonas de interés para la semana.',
                        '<strong>Lunes-viernes (pre-market):</strong> revisar si el precio ha llegado a alguna zona de interés semanal.',
                        '<strong>Si hay zona activa:</strong> bajar a diario y buscar setup. ¿Hay patrón de vela o nivel técnico claro?',
                        '<strong>Si hay setup:</strong> bajar a 4H o 1H y esperar el trigger específico que definiste.',
                        '<strong>Trigger activado:</strong> entrar con tamaño según alineación, stop bajo el trigger, plan de gestión definido.',
                        '<strong>Sin trigger:</strong> no hay entrada. Cerrar el gráfico y esperar al día siguiente.',
                    ]},
                ]
            },
            {
                heading: 'Errores comunes con el trigger',
                blocks: [
                    { type: 'text', content: 'El trigger es el punto donde más errores se cometen, precisamente porque es el último paso antes de la acción. El miedo a perderse el movimiento (FOMO) actúa con más fuerza aquí que en cualquier otro punto del análisis.' },
                    { type: 'chart', id: 'trigger_mistakes' },
                    { type: 'steps', items: [
                        '<strong>Anticipar el trigger:</strong> entrar antes de que se forme la vela de señal completa. La vela puede cambiar completamente antes del cierre.',
                        '<strong>Cambiar el trigger sobre la marcha:</strong> si el trigger definido no llega, inventar otro más fácil de cumplir para entrar de todas formas.',
                        '<strong>Ignorar el volumen:</strong> aceptar un trigger sin el volumen mínimo requerido, especialmente en rupturas.',
                        '<strong>FOMO post-trigger:</strong> el precio ya subió un 3% sin tu entrada y entras igualmente. Ese trade ya no tiene el mismo ratio.',
                        '<strong>Trigger en zona equivocada:</strong> el precio dio la señal pero no en el nivel de interés — sino en el medio del rango donde no hay estructura clara.',
                    ]},
                    { type: 'tip', label: 'DISCIPLINA', content: 'Lleva un registro de los setups que no operaste porque no dieron trigger. Cada mes, revisa cuántos de esos setups sin trigger habrían fallado. Verás que el trigger te salvó de pérdidas con más frecuencia de lo que te hizo perder oportunidades. Esa estadística personal es el mejor antídoto contra el FOMO.' },
                ]
            },
        ]
    },

    // ── MÓDULO 10, LECCIÓN 5 ───────────────────────────────────────────────
    '10-5': {
        moduleId: 10,
        lessonIndex: 4,
        title: 'Configurar tu Watchlist',
        duration: '10 min',
        intro: 'La watchlist es el resultado tangible de todo el proceso de este módulo: el sesgo mensual, la estructura semanal y el setup diario no sirven de nada si no se traducen en una lista concreta de activos con niveles y triggers definidos. Sin watchlist, cada mañana empiezas de cero. Con ella, empiezas donde lo dejaste el domingo.',
        sections: [
            {
                heading: 'Cuándo se construye y cuándo se revisa',
                blocks: [
                    { type: 'text', content: 'La watchlist se construye una vez por semana, el domingo, como parte de la rutina descrita en la lección anterior — no se improvisa un lunes por la mañana con el mercado ya abierto. Fuera de ese momento, solo se hacen ajustes menores: eliminar un ticker que ya no cumple los criterios, o añadir uno excepcional que apareció entre semana con una señal muy clara.' },
                    { type: 'table', headers: ['Momento', 'Qué se hace', 'Alcance del cambio'], rows: [
                        ['Domingo (construcción)', 'Revisión completa: sesgo mensual, sectores líderes, scanner CAN SLIM', 'La lista se rehace desde cero'],
                        ['Pre-market diario', 'Comprobar si algún ticker de la lista llegó a su zona de interés', 'Sin cambios en la composición de la lista'],
                        ['Entre semana (excepcional)', 'Un ticker rompe estructura de forma clara fuera de la revisión dominical', 'Añadir solo si cumple el mismo checklist que un domingo'],
                    ]},
                    { type: 'warning', content: 'Añadir tickers a la watchlist "sobre la marcha" porque han subido mucho ese día es la puerta de entrada más común al sobretrading y al FOMO. Si un ticker no pasó el filtro del domingo, necesita una razón igual de sólida — no solo que "se está moviendo" — para entrar entre semana.' },
                ]
            },
            {
                heading: 'Qué debe tener un candidato antes de entrar en la lista',
                blocks: [
                    { type: 'text', content: 'No cualquier activo que "se ve bien" merece un hueco en la watchlist. Cada candidato debe pasar un checklist mínimo antes de ganarse el seguimiento activo durante la semana.' },
                    { type: 'steps', items: [
                        '<strong>Alineación de contexto:</strong> sesgo mensual y estructura semanal coherentes con la dirección que buscas — nunca en contra',
                        '<strong>Liderazgo relativo:</strong> el activo o su sector muestra fortaleza relativa frente al mercado general (RS Rating alto, sector en rotación positiva)',
                        '<strong>Zona de interés definida:</strong> un nivel de precio concreto donde ocurriría el setup — no "está cerca de algo interesante" en general',
                        '<strong>Trigger anticipado:</strong> ya sabes de antemano qué señal específica en qué timeframe activaría la entrada si el precio llega a la zona',
                        '<strong>R:R potencial mínimo:</strong> con el nivel de entrada y el objetivo técnico más cercano, el ratio proyectado ya alcanza al menos 1:2 antes incluso de que el precio llegue ahí',
                    ]},
                    { type: 'concept', title: 'La watchlist no es una lista de deseos', content: 'Una watchlist mal construida es simplemente una lista de activos que "le gustan" al trader, sin criterio objetivo. Una watchlist bien construida es una lista de hipótesis de trading ya definidas: si pasa X en el nivel Y, entro con el plan Z. La diferencia es la que separa preparación de improvisación.' },
                ]
            },
            {
                heading: 'Tamaño de la lista y priorización',
                blocks: [
                    { type: 'text', content: 'El tamaño recomendado es de 5 a 10 activos activos por semana. Menos de 5 puede dejarte sin oportunidades si el mercado no coopera con esos pocos nombres; más de 10-12 satura la capacidad real de vigilar cada zona con la atención que merece.' },
                    { type: 'table', headers: ['Nº de candidatos disponibles', 'Cómo priorizar'], rows: [
                        ['Más candidatos que hueco en la lista', 'Prioriza por calidad de zona (fresca, alto volumen) y R:R potencial, no por cuánto ha subido el activo'],
                        ['Varios candidatos del mismo sector', 'Quédate con el de mejor estructura técnica individual — no dupliques exposición al mismo riesgo sectorial'],
                        ['Menos de 5 candidatos válidos', 'Es una señal legítima, no un problema — algunas semanas el mercado ofrece pocas oportunidades de calidad'],
                    ]},
                    { type: 'warning', content: 'Forzar la lista hasta 10 activos cuando el scanner solo arrojó 3 candidatos de calidad real es el mismo error de fondo que forzar un trade: bajar el estándar por la necesidad de sentir actividad. Una watchlist corta y de alta calidad vale más que una larga y mediocre.' },
                ]
            },
            {
                heading: 'Cuándo eliminar un ticker de la lista',
                blocks: [
                    { type: 'text', content: 'Mantener un ticker en la watchlist indefinidamente "por si acaso" acumula ruido y diluye la atención sobre los candidatos que sí siguen siendo válidos. La poda semanal es tan importante como la incorporación de nuevos nombres.' },
                    { type: 'steps', items: [
                        'El precio se alejó significativamente de la zona de interés sin activar el trigger — la oportunidad de esa semana ha pasado',
                        'El sesgo mensual o la estructura semanal cambiaron y ya no son coherentes con la tesis original',
                        'El sector perdió liderazgo relativo frente al mercado desde la última revisión',
                        'El trigger se activó y ya operaste el setup — sale de watchlist activa (ganador o perdedor, entra al journal, no se sigue vigilando igual)',
                    ]},
                    { type: 'tip', label: 'REGLA DE LA WATCHLIST', content: 'Solo operas activos que estaban en tu lista del domingo. Esta regla, ya mencionada en el módulo de Sobretrading, es la razón última por la que construir bien la watchlist importa: convierte la disciplina de entrada en algo automático, porque la decisión difícil ya se tomó con calma el fin de semana, no bajo presión con el mercado abierto.' },
                ]
            },
        ]
    },

    // ── MÓDULO 11, LECCIÓN 1 ───────────────────────────────────────────────
    '11-1': {
        moduleId: 11,
        lessonIndex: 0,
        title: 'Definir el Setup',
        duration: '9 min',
        intro: 'Un trade sin setup definido no es un trade — es una apuesta. La diferencia entre un trader profesional y uno amateur no está en la frecuencia de sus operaciones sino en la claridad con la que puede describir exactamente por qué entra en cada una.',
        sections: [
            {
                heading: '¿Qué es un setup?',
                blocks: [
                    { type: 'text', content: 'Un setup es una configuración específica y repetible de condiciones de mercado que históricamente ha producido un determinado resultado con una probabilidad conocida. No es una corazonada, no es "el precio parece que va a subir", no es seguir a alguien en Twitter. Es un conjunto de condiciones <strong>objetivas y verificables</strong> que debes poder describir sin ambigüedad.' },
                    { type: 'chart', id: 'setup_definition' },
                    { type: 'concept', title: 'El setup como hipótesis', content: 'Trata cada trade como un experimento científico. El setup es tu hipótesis: "Cuando ocurren las condiciones X, Y, Z, el precio tiende a moverse en dirección A con probabilidad P". La entrada es el experimento. El resultado confirma o refuta la hipótesis. Sin hipótesis clara, no puedes aprender de los resultados.' },
                ]
            },
            {
                heading: 'Los 5 elementos de un setup válido',
                blocks: [
                    { type: 'text', content: 'Un setup completo debe tener exactamente cinco elementos definidos antes de abrir la posición. Si falta alguno, el setup no está completo y no debes operar.' },
                    { type: 'chart', id: 'setup_five_elements' },
                    { type: 'steps', items: [
                        '<strong>Contexto:</strong> ¿Cuál es el sesgo mensual? ¿La estructura semanal? ¿El setup está a favor de la tendencia mayor?',
                        '<strong>Nivel:</strong> ¿En qué precio exacto ocurre el setup? ¿Es un soporte, resistencia rota, zona de demanda, EMA?',
                        '<strong>Trigger:</strong> ¿Qué señal específica activa la entrada? ¿Vela de señal, ruptura de rango, giro en 4H?',
                        '<strong>Stop:</strong> ¿Dónde invalida el mercado mi hipótesis? El stop define el riesgo máximo del trade.',
                        '<strong>Objetivo:</strong> ¿Cuál es el target mínimo? ¿Qué ratio R:R ofrece el setup?',
                    ]},
                    { type: 'warning', content: 'El orden importa. Defines el stop ANTES que el objetivo. El stop lo fija el mercado (dónde está equivocado tu análisis). El objetivo lo fija la estructura técnica (próxima resistencia, proyección del patrón). Nunca al revés.' },
                ]
            },
            {
                heading: 'Tipos de setup por contexto',
                blocks: [
                    { type: 'text', content: 'No todos los setups son iguales. La probabilidad de éxito varía enormemente dependiendo del contexto en el que aparecen. El mismo patrón de vela tiene probabilidades muy diferentes según dónde ocurre.' },
                    { type: 'chart', id: 'setup_types_context' },
                    { type: 'table',
                        headers: ['Tipo de setup', 'Contexto óptimo', 'Probabilidad típica'],
                        rows: [
                            ['Retroceso a EMA21', 'Tendencia alcista fuerte, mercado alcista', '65-70%'],
                            ['Ruptura de base', 'Mercado alcista confirmado, RS > 80', '60-65%'],
                            ['Rebote en soporte', 'Sesgo mensual alcista, nivel mayor', '55-65%'],
                            ['Reversión desde suelo', 'VIX elevado, clímax bajista previo', '50-60%'],
                            ['Ruptura de triángulo', 'Tendencia previa clara, volumen en ruptura', '60-70%'],
                        ]
                    },
                ]
            },
            {
                heading: 'Documentar el setup antes de entrar',
                blocks: [
                    { type: 'text', content: 'El acto de escribir el setup antes de ejecutar el trade tiene un efecto psicológico poderoso: te obliga a ser específico. "Compro NVDA porque parece fuerte" no es un setup. "Compro NVDA si cierra sobre $875 con volumen 1.5x, stop bajo $845, objetivo $930" sí lo es.' },
                    { type: 'chart', id: 'setup_documentation' },
                    { type: 'tip', label: 'PLANTILLA', content: 'Usa siempre la misma plantilla antes de cada trade: Ticker | Fecha | Setup | Contexto M/S/D | Nivel de entrada | Trigger | Stop | Objetivo | R:R | Tamaño | Razonamiento. Tarda 2 minutos y elimina el 80% de los trades impulsivos.' },
                ]
            },
        ]
    },

    // ── MÓDULO 11, LECCIÓN 2 ───────────────────────────────────────────────
    '11-2': {
        moduleId: 11,
        lessonIndex: 1,
        title: 'Ratio Riesgo/Recompensa',
        duration: '9 min',
        intro: 'El ratio R:R es el número más importante de cualquier trade. No la dirección del mercado, no el análisis técnico, no el sentimiento. Si no entiendes el R:R antes de entrar, estás operando a ciegas.',
        sections: [
            {
                heading: 'Qué es el R:R y cómo se calcula',
                blocks: [
                    { type: 'text', content: 'El ratio Riesgo/Recompensa compara cuánto puedes ganar si tienes razón vs cuánto pierdes si te equivocas. Un R:R de 1:3 significa que por cada euro que arriesgas puedes ganar tres. Es el fundamento matemático de por qué el trading puede ser rentable incluso con una tasa de aciertos inferior al 50%.' },
                    { type: 'chart', id: 'rr_calculation' },
                    { type: 'concept', title: 'La matemática del R:R', content: 'Con R:R 1:2 y 50% de aciertos: por cada 10 trades, ganas 5×2R = 10R y pierdes 5×1R = 5R. Beneficio neto: +5R. Con R:R 1:1 y 50% de aciertos: empatas. Con R:R 1:3 y solo 40% de aciertos: ganas 4×3R = 12R, pierdes 6×1R = 6R. Beneficio neto: +6R. El R:R alto te permite ser rentable incluso siendo mediocre en el timing.' },
                ]
            },
            {
                heading: 'R:R mínimo aceptable',
                blocks: [
                    { type: 'text', content: 'La regla más básica del trading profesional: nunca entres en un trade con R:R inferior a 1:2. Idealmente 1:3 o superior. Con R:R 1:1 necesitas acertar el 55%+ para ser rentable (comisiones incluidas). Con R:R 1:2 solo necesitas acertar el 35%.' },
                    { type: 'chart', id: 'rr_minimum' },
                    { type: 'table',
                        headers: ['R:R', 'Aciertos necesarios para breakeven', 'Aciertos para +20% anual'],
                        rows: [
                            ['1:1', '55%', '65%+'],
                            ['1:2', '35%', '45%'],
                            ['1:3', '27%', '35%'],
                            ['1:4', '22%', '28%'],
                            ['1:5', '18%', '23%'],
                        ]
                    },
                    { type: 'tip', label: 'REGLA PRÁCTICA', content: 'Si el objetivo natural del setup (próxima resistencia, proyección del patrón) está a menos de 2R de distancia, no hay trade. No intentes ajustar el stop para "mejorar" el R:R artificialmente — eso solo aumenta la probabilidad de que salte antes de tiempo.' },
                ]
            },
            {
                heading: 'Cómo el R:R determina el tamaño de posición',
                blocks: [
                    { type: 'text', content: 'El R:R y el tamaño de posición son dos caras de la misma moneda. Defines el riesgo máximo que puedes asumir (ej: 1% de la cartera), divides por la distancia al stop en precio, y obtienes el número de acciones.' },
                    { type: 'chart', id: 'rr_position_size' },
                    { type: 'steps', items: [
                        'Capital total: $50,000',
                        'Riesgo máximo por trade: 1% = $500',
                        'Precio de entrada: $100. Stop: $95. Distancia al stop: $5',
                        'Número de acciones: $500 / $5 = 100 acciones',
                        'Capital invertido: 100 × $100 = $10,000 (20% del capital)',
                        'Objetivo a $115: ganancia potencial = 100 × $15 = $1,500 = R:R 1:3',
                    ]},
                ]
            },
            {
                heading: 'Ajustar el R:R según la alineación',
                blocks: [
                    { type: 'text', content: 'El R:R mínimo no es fijo — varía según la calidad del setup y la alineación multi-temporalidad. Con triple alineación (mensual + semanal + diario), puedes aceptar un R:R ligeramente menor porque la probabilidad de éxito es más alta.' },
                    { type: 'chart', id: 'rr_alignment' },
                    { type: 'concept', title: 'Expected Value (EV)', content: 'El verdadero objetivo es maximizar el Expected Value: EV = (Probabilidad de ganar × Ganancia) − (Probabilidad de perder × Pérdida). Con setup de alta calidad (70% de aciertos) y R:R 1:2: EV = 0.70×2 − 0.30×1 = 1.40 − 0.30 = +1.10R por trade. Con setup mediocre (45%) y R:R 1:3: EV = 0.45×3 − 0.55×1 = 1.35 − 0.55 = +0.80R. El setup de calidad tiene mayor EV aunque el R:R sea menor.' },
                ]
            },
        ]
    },

    // ── MÓDULO 11, LECCIÓN 3 ───────────────────────────────────────────────
    '11-3': {
        moduleId: 11,
        lessonIndex: 2,
        title: 'Tamaño de Posición',
        duration: '9 min',
        intro: 'El sizing es donde la mayoría de traders, incluso los que tienen buen análisis, destruyen su cuenta. Demasiado grande en el momento equivocado puede acabar con meses de trabajo en un solo trade.',
        sections: [
            {
                heading: 'El principio del riesgo fijo',
                blocks: [
                    { type: 'text', content: 'La regla más importante del sizing: nunca arriesgues más de un porcentaje fijo de tu capital en un solo trade. La mayoría de traders profesionales usan entre 0.5% y 2% por trade. El porcentaje exacto depende de tu historial de aciertos y tu psicología, pero debe ser fijo y no negociable.' },
                    { type: 'chart', id: 'fixed_risk_principle' },
                    { type: 'concept', title: 'Por qué el riesgo fijo protege tu cuenta', content: 'Con riesgo del 2% por trade, necesitas 34 stops consecutivos para perder el 50% de la cuenta (0.98^34 = 0.50). Casi imposible estadísticamente. Con riesgo del 10% por trade, solo necesitas 7 stops consecutivos. Las rachas perdedoras de 5-7 trades son normales incluso para traders exitosos. El riesgo fijo bajo es lo que te mantiene en el juego.' },
                ]
            },
            {
                heading: 'Escalado de posición según alineación',
                blocks: [
                    { type: 'text', content: 'No todos los setups son iguales — no todos merecen el mismo tamaño. El escalado de posición usa la misma base de riesgo fijo pero ajusta el porcentaje según la calidad del setup.' },
                    { type: 'chart', id: 'position_scaling' },
                    { type: 'table',
                        headers: ['Calidad del setup', 'Riesgo base', 'Alineación MTF', 'Riesgo máximo'],
                        rows: [
                            ['A+ (triple alineación)', '1%', 'M↑ S↑ D setup', '2%'],
                            ['A (doble alineación)', '1%', 'M↑ S↑ D', '1.5%'],
                            ['B (alineación parcial)', '1%', 'M↑ S neutral', '1%'],
                            ['C (sin alineación)', '1%', 'M neutral', '0.5%'],
                            ['Especulativo', '1%', 'Contra tendencia', '0.25%'],
                        ]
                    },
                ]
            },
            {
                heading: 'Averaging: cuándo y cuándo no',
                blocks: [
                    { type: 'text', content: 'Promediar una posición perdedora (comprar más mientras el trade va en tu contra) es uno de los errores más peligrosos del trading. Promediar una posición ganadora (añadir cuando el trade ya va a tu favor) es una técnica avanzada y válida.' },
                    { type: 'chart', id: 'averaging_right_wrong' },
                    { type: 'steps', items: [
                        '<strong>NUNCA:</strong> Comprar más cuando el precio baja contra ti para "mejorar el precio medio". Esto convierte pérdidas controladas en desastres.',
                        '<strong>NUNCA:</strong> Doblar posición en un trade que ya ha saltado el stop mentalmente.',
                        '<strong>SÍ:</strong> Añadir a una posición ganadora cuando el precio rompe un nuevo nivel de resistencia con volumen.',
                        '<strong>SÍ:</strong> Escalar entrada en 2-3 tramos cuando el setup lo justifica (entry 1 en nivel, entry 2 en confirmación).',
                    ]},
                    { type: 'warning', content: 'La media hacia abajo (promediando pérdidas) ha destruido más cuentas que cualquier otro error. El argumento "el precio va a volver" es válido el 60% de las veces — pero el 40% restante convierte una pérdida del 5% en una del 30%. Nunca promedia pérdidas.' },
                ]
            },
            {
                heading: 'El impacto del sizing en la psicología',
                blocks: [
                    { type: 'text', content: 'El tamaño de posición tiene un efecto directo sobre tu capacidad de tomar decisiones racionales. Una posición demasiado grande activa el sistema límbico (miedo/codicia) y desactiva el córtex prefrontal (razonamiento). Operar "demasiado grande" arruina tu juicio incluso si el análisis era correcto.' },
                    { type: 'chart', id: 'sizing_psychology' },
                    { type: 'tip', label: 'TEST DEL SUEÑO', content: 'Si una posición abierta te impide dormir, es demasiado grande. El tamaño correcto de posición es aquel con el que puedes seguir tu plan con frialdad aunque el mercado se mueva en tu contra durante 2-3 días. Si sientes ansiedad, reduce el tamaño — no el stop.' },
                ]
            },
        ]
    },

    // ── MÓDULO 11, LECCIÓN 4 ───────────────────────────────────────────────
    '11-4': {
        moduleId: 11,
        lessonIndex: 3,
        title: 'El Plan de Trade',
        duration: '9 min',
        intro: 'El plan de trade es el documento que escribe el trader racional antes de abrir la posición, para que el trader emocional (el mismo después de entrar) no pueda improvisar cuando el mercado se complique.',
        sections: [
            {
                heading: 'Por qué necesitas un plan escrito',
                blocks: [
                    { type: 'text', content: 'Cuando una posición está abierta, tu cerebro entra en modo de supervivencia. El dolor de las pérdidas potenciales activa respuestas emocionales que distorsionan el juicio. El único antídoto es haber tomado las decisiones importantes (cuándo salir, en qué condiciones aguantar) antes de que el dinero esté en riesgo.' },
                    { type: 'chart', id: 'trade_plan_why' },
                    { type: 'concept', title: 'El trader pre-trade vs el trader en trade', content: 'Antes de entrar eres el CEO: analítico, estratégico, sin emociones. Después de entrar eres el accionista: nervioso, sesgado, buscando confirmar lo que ya crees. El plan escrito es el puente entre ambos estados. "Si el precio hace X, yo hago Y" — tomado cuando estabas en calma, ejecutado cuando estás bajo presión.' },
                ]
            },
            {
                heading: 'Estructura del plan de trade',
                blocks: [
                    { type: 'text', content: 'Un plan de trade completo tiene cuatro secciones: la tesis, la entrada, la gestión y la salida. Cada sección debe ser objetiva — sin adjetivos como "probablemente", "creo que", "parece que".' },
                    { type: 'chart', id: 'trade_plan_structure' },
                    { type: 'steps', items: [
                        '<strong>TESIS:</strong> Por qué existe el setup. Contexto M/S/D. Nivel técnico relevante. Catalizador si existe.',
                        '<strong>ENTRADA:</strong> Precio exacto de entrada. Trigger específico. Tamaño de posición. Fecha límite de validez.',
                        '<strong>GESTIÓN:</strong> Stop inicial. Dónde mover el stop a breakeven. Condiciones para añadir. Condiciones para reducir.',
                        '<strong>SALIDA:</strong> Objetivo 1 (parcial). Objetivo 2 (runner). Condiciones de salida anticipada (si el precio hace X, salgo).',
                    ]},
                ]
            },
            {
                heading: 'Escenarios alternativos',
                blocks: [
                    { type: 'text', content: 'El mercado rara vez sigue el camino que esperas. Un buen plan de trade incluye escenarios alternativos: qué haces si el precio va directamente al objetivo sin pullback, qué haces si hay una caída repentina y el stop salta justo antes de recuperar, qué haces si aparece una noticia macro.' },
                    { type: 'chart', id: 'trade_plan_scenarios' },
                    { type: 'table',
                        headers: ['Escenario', 'Condición', 'Acción'],
                        rows: [
                            ['Ideal', 'Precio sube directo al objetivo 1', 'Vender 50%, mover stop a breakeven'],
                            ['Pullback post-entrada', 'Precio retrocede pero no toca stop', 'Mantener. El plan sigue válido.'],
                            ['Stop saltado', 'Precio toca el stop definido', 'Salir. Sin excepciones.'],
                            ['Gap alcista', 'Precio abre muy por encima del objetivo 1', 'Vender todo en apertura'],
                            ['Noticia negativa', 'Noticia macro adversa en posición abierta', 'Reducir 50% inmediatamente'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cuándo el plan deja de ser válido',
                blocks: [
                    { type: 'text', content: 'Un plan de trade tiene fecha de caducidad. Si el precio no se mueve en la dirección esperada dentro de un tiempo razonable, el setup pierde validez aunque el stop no haya saltado. El tiempo es una forma de riesgo — capital inmovilizado en un trade estancado es capital que no puede aprovecharse de otras oportunidades.' },
                    { type: 'chart', id: 'trade_plan_expiry' },
                    { type: 'tip', label: 'TIME STOP', content: 'Además del stop de precio, define siempre un time stop: "Si en X días el precio no ha avanzado hacia el objetivo, salgo aunque el stop no haya saltado". Para setups diarios, 5-10 días es razonable. Para setups semanales, 3-4 semanas. Un trade que no funciona rápidamente normalmente no funciona.' },
                ]
            },
        ]
    },
    // ── MÓDULO 12, LECCIÓN 1 ───────────────────────────────────────────────
    '12-1': {
        moduleId: 12,
        lessonIndex: 0,
        title: 'Riesgo Fijo por Trade',
        duration: '9 min',
        intro: 'El riesgo fijo por trade es el principio más importante de toda la gestión del riesgo. Es la regla que te mantiene en el juego cuando todo va mal, y la que te permite sobrevivir para aprovecharte de cuando todo va bien.',
        sections: [
            {
                heading: 'Por qué el riesgo fijo es no negociable',
                blocks: [
                    { type: 'text', content: 'La mayoría de traders pierde no porque su análisis sea malo, sino porque no controlan cuánto arriesgan en cada operación. Un trade que "parece muy seguro" con el 20% de la cuenta puede destruir meses de trabajo. El riesgo fijo elimina este problema: independientemente de cuánto te guste el setup, el riesgo máximo siempre es el mismo porcentaje.' },
                    { type: 'chart', id: 'fixed_risk_nonnegotiable' },
                    { type: 'concept', title: 'La asimetría de las pérdidas', content: 'Una pérdida del 50% requiere una ganancia del 100% para recuperarse. Una pérdida del 20% requiere un 25%. Una pérdida del 10% requiere un 11.1%. Las pérdidas grandes son matemáticamente devastadoras. El riesgo fijo bajo previene que una racha perdedora normal se convierta en un agujero del que no puedes salir.' },
                ]
            },
            {
                heading: 'Cómo definir tu porcentaje de riesgo',
                blocks: [
                    { type: 'text', content: 'El porcentaje de riesgo correcto depende de tu historial de aciertos y tu psicología. Si estás empezando o en una racha perdedora, usa 0.5%. Con experiencia y resultados positivos consistentes, puedes llegar al 2%. Nunca más del 2% por trade.' },
                    { type: 'chart', id: 'risk_percentage_how' },
                    { type: 'table',
                        headers: ['Perfil', 'Riesgo recomendado', 'Razonamiento'],
                        rows: [
                            ['Empezando (<1 año)', '0.25-0.5%', 'Aprender sin destruir la cuenta'],
                            ['Intermedio (1-3 años)', '0.5-1%', 'Equilibrio entre aprendizaje y rentabilidad'],
                            ['Avanzado (>3 años, resultados)', '1-1.5%', 'Historial positivo justifica más riesgo'],
                            ['Profesional (edge demostrado)', 'Hasta 2%', 'Solo con estadísticas propias sólidas'],
                            ['En racha perdedora (>5 stops)', '0.25%', 'Reducir hasta recuperar confianza'],
                        ]
                    },
                    { type: 'tip', label: 'REDUCCIÓN AUTOMÁTICA', content: 'Cuando tu cuenta baja un 10% desde el máximo reciente, reduce automáticamente el riesgo por trade a la mitad. Cuando baje un 20%, para de operar completamente durante una semana y revisa tu proceso. Esta regla automática evita el revenge trading en los peores momentos.' },
                ]
            },
            {
                heading: 'Riesgo vs exposición: la diferencia crítica',
                blocks: [
                    { type: 'text', content: 'Riesgo y exposición no son lo mismo. La exposición es el capital invertido. El riesgo es cuánto puedes perder si el stop salta. Puedes tener el 30% de la cuenta en una posición (alta exposición) con solo el 1% de riesgo (si el stop está muy cerca del precio de entrada).' },
                    { type: 'chart', id: 'risk_vs_exposure' },
                    { type: 'steps', items: [
                        'Capital: $50,000. Riesgo máximo: 1% = $500',
                        'Precio de entrada: $200. Stop: $198. Distancia: $2 (1%)',
                        'Acciones = $500 / $2 = 250 acciones',
                        'Exposición = 250 × $200 = $50,000 (100% del capital)',
                        'Riesgo real = $500 (solo el 1%) — exposición alta pero riesgo controlado',
                    ]},
                    { type: 'warning', content: 'Una posición con stop muy ajustado puede tener alta exposición con bajo riesgo. Pero si ese stop es demasiado ajustado (salta por el ruido normal del mercado), el bajo riesgo teórico se convierte en pérdidas repetidas. El stop debe estar en un nivel técnicamente válido, no calculado para que el riesgo sea mínimo.' },
                ]
            },
            {
                heading: 'Acumulación de riesgo en múltiples posiciones',
                blocks: [
                    { type: 'text', content: 'El riesgo del 1% por trade se refiere a una posición individual. Con múltiples posiciones abiertas simultáneamente, el riesgo total se acumula. Si tienes 5 posiciones con 1% de riesgo cada una y el mercado cae simultáneamente (lo que ocurre en correcciones), puedes perder el 5% en un día.' },
                    { type: 'chart', id: 'risk_accumulation' },
                    { type: 'concept', title: 'Riesgo total de cartera', content: 'Define un riesgo máximo total de cartera: el porcentaje máximo que puedes perder en un solo día si todos los stops saltan simultáneamente. Un límite razonable es el 3-5% del capital total. Si tienes 5 posiciones abiertas al 1% cada una, estás en el límite. No abras una sexta hasta que cierres alguna.' },
                ]
            },
        ]
    },

    // ── MÓDULO 12, LECCIÓN 2 ───────────────────────────────────────────────
    '12-2': {
        moduleId: 12,
        lessonIndex: 1,
        title: 'Stop Loss Dinámico',
        duration: '9 min',
        intro: 'El stop loss no es solo el nivel donde sales si te equivocas. Es la herramienta de gestión más activa del trade: lo mueves para proteger ganancias, lo ajustas cuando la estructura cambia, y determina cuándo el mercado ha invalidado tu hipótesis.',
        sections: [
            {
                heading: 'Tipos de stop loss',
                blocks: [
                    { type: 'text', content: 'Hay tres tipos de stop: el stop inicial (donde está equivocado tu análisis), el stop de breakeven (cuando mueves el stop al precio de entrada una vez el trade va a tu favor) y el trailing stop (que sigue al precio para proteger ganancias acumuladas).' },
                    { type: 'chart', id: 'stop_types' },
                    { type: 'table',
                        headers: ['Tipo de stop', 'Cuándo usarlo', 'Objetivo'],
                        rows: [
                            ['Stop inicial', 'Al abrir la posición', 'Definir el riesgo máximo'],
                            ['Stop breakeven', 'Cuando el precio alcanza 1R de ganancia', 'Eliminar el riesgo del trade'],
                            ['Trailing stop', 'Una vez en ganancia significativa', 'Proteger ganancias y dejar correr'],
                            ['Time stop', 'Si el trade no avanza en X días', 'Liberar capital estancado'],
                            ['Volatility stop', 'Basado en ATR', 'Adaptar el stop a la volatilidad del activo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Dónde colocar el stop inicial',
                blocks: [
                    { type: 'text', content: 'El stop inicial debe colocarse donde el mercado invalida tu hipótesis — no donde el riesgo es conveniente para tu sizing. Un stop inválido técnicamente (colocado arbitrariamente) casi siempre salta antes de que el trade tenga tiempo de desarrollarse.' },
                    { type: 'chart', id: 'stop_placement' },
                    { type: 'steps', items: [
                        '<strong>Setup de retroceso a soporte:</strong> stop bajo el mínimo de la vela de señal (o bajo el soporte)',
                        '<strong>Setup de ruptura:</strong> stop dentro del rango roto, por debajo de la resistencia que ahora es soporte',
                        '<strong>Setup de triángulo/patrón:</strong> stop bajo el último mínimo del patrón',
                        '<strong>Regla de margen:</strong> añade un 0.5-1% adicional bajo el nivel técnico para evitar stops prematuros por falsas rupturas',
                    ]},
                ]
            },
            {
                heading: 'El trailing stop: cuándo y cómo',
                blocks: [
                    { type: 'text', content: 'El trailing stop sigue al precio en su movimiento favorable, bloqueando ganancias mientras deja al trade continuar. La clave está en no ajustarlo demasiado rápido (sales prematuramente) ni demasiado lento (devuelves demasiada ganancia).' },
                    { type: 'chart', id: 'trailing_stop_how' },
                    { type: 'steps', items: [
                        'El precio ha subido y estás en +2R de ganancia',
                        'Mueve el stop al nivel del último HL significativo en el timeframe de entrada',
                        'Cuando el precio hace un nuevo HH, mueve el stop al nuevo HL',
                        'No muevas el stop hacia abajo nunca — solo hacia arriba',
                        'Cuando el trailing stop salta, el trade ha terminado — con ganancia',
                    ]},
                    { type: 'tip', label: 'EMA TRAILING', content: 'Una técnica efectiva de trailing stop es usar la EMA21 diaria. Mientras el precio cierra por encima de la EMA21, mantienes la posición. Cuando cierra por debajo, cierras. En tendencias fuertes, este método captura el 60-70% del movimiento total sin estar pendiente del precio constantemente.' },
                ]
            },
            {
                heading: 'El error del stop mental',
                blocks: [
                    { type: 'text', content: 'Un stop "mental" (donde decides en tu cabeza que saldrás pero no lo has colocado en el broker) es uno de los errores más peligrosos del trading. En el momento crítico, el cerebro emocional siempre encuentra una razón para no ejecutarlo.' },
                    { type: 'chart', id: 'mental_stop_danger' },
                    { type: 'concept', title: 'Por qué el stop mental falla', content: '"El precio está justo en el stop, pero parece que va a rebotar". "Solo voy a esperar un poco más". "Ya que está tan cerca del stop, aguanto". Estas son las frases que preceden a las pérdidas más grandes. El stop físico en el broker se ejecuta automáticamente. El stop mental te da la oportunidad de ignorarlo — y casi siempre la aprovechas.' },
                ]
            },
        ]
    },

    // ── MÓDULO 12, LECCIÓN 3 ───────────────────────────────────────────────
    '12-3': {
        moduleId: 12,
        lessonIndex: 2,
        title: 'Revenge Trading y Racha Perdedora',
        duration: '9 min',
        intro: 'El revenge trading es el intento de recuperar pérdidas recientes tomando más riesgo del habitual. Es la respuesta emocional más destructiva en trading y la causa principal de que pequeñas pérdidas se conviertan en desastres.',
        sections: [
            {
                heading: '¿Qué es el revenge trading?',
                blocks: [
                    { type: 'text', content: 'El revenge trading ocurre cuando, después de una o varias pérdidas, aumentas el tamaño de posición, reduces el stop, entras en setups de menor calidad o operas activos que no tenías en tu watchlist — todo con el objetivo de "recuperar" lo perdido lo antes posible. El mercado no te debe nada. No te lo puede "devolver".' },
                    { type: 'chart', id: 'revenge_trading_what' },
                    { type: 'concept', title: 'La espiral del revenge trading', content: 'Pérdida de $500 → rage trade con el doble de tamaño → pérdida de $1,200 → trade aún mayor para "recuperar todo" → pérdida de $2,500. En una hora se puede destruir el trabajo de meses. La espiral es real porque cada pérdida aumenta la presión emocional y deteriora el juicio, lo que lleva a peores decisiones, lo que lleva a más pérdidas.' },
                ]
            },
            {
                heading: 'Cómo detectar que estás en revenge trading',
                blocks: [
                    { type: 'text', content: 'El revenge trading es difícil de detectar desde dentro porque el cerebro lo racionaliza como "una oportunidad excelente que acabo de ver". Hay señales de alerta objetivas que debes reconocer.' },
                    { type: 'chart', id: 'revenge_trading_signs' },
                    { type: 'steps', items: [
                        'Has perdido en los últimos 2-3 trades y sientes urgencia de entrar',
                        'El tamaño que estás considerando es mayor al habitual',
                        'El setup no está en tu watchlist original',
                        'Estás mirando activos que no analizaste el domingo',
                        'Sientes que "el mercado me debe esta"',
                        'Estás justificando por qué "esta vez es diferente"',
                    ]},
                    { type: 'warning', content: 'Si identificas cualquiera de estas señales, la acción correcta es cerrar el ordenador y no volver a operar ese día. No importa qué setup "tan bueno" creas ver. Tu juicio está comprometido. Cualquier trade que hagas en ese estado es estadísticamente peor que tus trades normales.' },
                ]
            },
            {
                heading: 'Protocolo de racha perdedora',
                blocks: [
                    { type: 'text', content: 'Una racha perdedora no significa que tu metodología esté rota. Incluso con 60% de aciertos, puedes tener 5-7 stops consecutivos por simple probabilidad estadística. La clave es tener un protocolo definido para estas situaciones.' },
                    { type: 'chart', id: 'losing_streak_protocol' },
                    { type: 'table',
                        headers: ['Stops consecutivos', 'Acción', 'Objetivo'],
                        rows: [
                            ['3 stops', 'Revisar los 3 trades. ¿Seguiste el plan?', 'Identificar si es mala suerte o error'],
                            ['4 stops', 'Reducir tamaño al 50%', 'Proteger capital mientras revisas'],
                            ['5 stops', 'Solo paper trading por 1 semana', 'Recuperar confianza sin riesgo real'],
                            ['6+ stops', 'Parar completamente. Revisión profunda', 'El mercado puede haber cambiado'],
                        ]
                    },
                ]
            },
            {
                heading: 'La mentalidad correcta ante las pérdidas',
                blocks: [
                    { type: 'text', content: 'Los stops son el coste del negocio, no fracasos. Un cirujano no fracasa cuando una operación resulta más complicada de lo esperado — usa su protocolo. Un piloto no fracasa cuando hay turbulencias — sigue el procedimiento. En trading, el stop ejecutado correctamente es el sistema funcionando, no fallando.' },
                    { type: 'chart', id: 'loss_mindset' },
                    { type: 'tip', label: 'REENCUADRE', content: 'Después de cada stop, hazte una sola pregunta: "¿Seguí mi plan?". Si la respuesta es sí — bien hecho. El resultado no estaba en tu control, el proceso sí. Si la respuesta es no — ahí está el problema a corregir. Juzga tu trading por la calidad del proceso, no por el resultado de cada trade individual.' },
                ]
            },
        ]
    },

    // ── MÓDULO 12, LECCIÓN 4 ───────────────────────────────────────────────
    '12-4': {
        moduleId: 12,
        lessonIndex: 3,
        title: 'Protección de Capital',
        duration: '9 min',
        intro: 'Proteger el capital no es una postura conservadora — es el requisito previo para ganar. Sin capital, no puedes operar. Sin capital, no hay recuperación posible. La protección del capital es lo que convierte el trading en un juego de largo plazo.',
        sections: [
            {
                heading: 'Las reglas de protección de capital RSU',
                blocks: [
                    { type: 'text', content: 'Hay cuatro reglas de protección de capital que son absolutas. No tienen excepciones, no se negocian y no se rompen independientemente de la "oportunidad" que creas ver.' },
                    { type: 'chart', id: 'capital_protection_rules' },
                    { type: 'steps', items: [
                        '<strong>Regla 1:</strong> Nunca arriesgar más del 2% del capital en un solo trade',
                        '<strong>Regla 2:</strong> Nunca tener más del 5% de riesgo total en posiciones simultáneas',
                        '<strong>Regla 3:</strong> Si la cuenta baja un 10% desde el máximo, reducir el tamaño al 50%',
                        '<strong>Regla 4:</strong> Si la cuenta baja un 20% desde el máximo, parar de operar completamente',
                    ]},
                ]
            },
            {
                heading: 'El drawdown: cuándo preocuparse y cuándo no',
                blocks: [
                    { type: 'text', content: 'El drawdown es la caída desde el máximo de equity hasta el mínimo actual. Es inevitable — todos los traders tienen drawdowns, incluyendo los mejores del mundo. La cuestión no es si tendrás drawdowns sino cuán grandes son y cuánto tardas en recuperarte.' },
                    { type: 'chart', id: 'drawdown_management' },
                    { type: 'table',
                        headers: ['Drawdown', 'Valoración', 'Acción'],
                        rows: [
                            ['< 5%', 'Normal', 'Seguir el plan sin cambios'],
                            ['5-10%', 'Atención', 'Revisar los últimos trades. ¿Hay error de proceso?'],
                            ['10-15%', 'Preocupante', 'Reducir tamaño al 50%. Revisar en profundidad'],
                            ['15-20%', 'Crítico', 'Reducir al 25% o parar. Algo no funciona'],
                            ['> 20%', 'Parar', 'Alto completo. Revisión total del sistema'],
                        ]
                    },
                ]
            },
            {
                heading: 'Correlación entre posiciones',
                blocks: [
                    { type: 'text', content: 'Tener 5 posiciones en tecnología no es diversificación — es concentración con la ilusión de diversificación. Si el sector tech cae un 5% en un día, las cinco posiciones caen simultáneamente y tu riesgo real es 5 veces el de una posición individual.' },
                    { type: 'chart', id: 'position_correlation' },
                    { type: 'concept', title: 'Diversificación real', content: 'La diversificación real en trading no es tener muchos activos — es tener activos con baja correlación. Tech + Defense + Energy + Healthcare tienen correlaciones mucho más bajas entre sí que cinco acciones de tech. Distribuye el riesgo entre sectores no correlacionados para que una caída sectorial no destruya toda la cartera.' },
                ]
            },
            {
                heading: 'El capital como recurso renovable',
                blocks: [
                    { type: 'text', content: 'Si pierdes el 50% de tu cuenta, necesitas un 100% de rentabilidad para recuperarte. Si pierdes el 25%, necesitas un 33%. Cada euro de capital destruido requiere proporcionalmente más esfuerzo para recuperarse. Proteger el capital no es timidez — es matemática.' },
                    { type: 'chart', id: 'capital_recovery_math' },
                    { type: 'tip', label: 'PERSPECTIVA', content: 'Los mejores traders del mundo tienen años de drawdown. Paul Tudor Jones, Stanley Druckenmiller, Steve Cohen — todos han tenido períodos difíciles. La diferencia entre ellos y los que abandonaron no es que no tuvieran pérdidas — es que sus reglas de gestión del riesgo les impidieron que las pérdidas fueran fatales. La supervivencia es el prerrequisito del éxito.' },
                ]
            },
        ]
    },
    // ── MÓDULO 13, LECCIÓN 1 ───────────────────────────────────────────────
    '13-1': {
        moduleId: 13,
        lessonIndex: 0,
        title: 'Esperar Confirmación',
        duration: '9 min',
        intro: 'El impulso de entrar antes de tiempo es uno de los más fuertes en trading. Ver un setup formándose genera la sensación de "si no entro ahora me lo voy a perder". Esa sensación es precisamente la que hay que aprender a ignorar.',
        sections: [
            {
                heading: 'Qué es esperar confirmación',
                blocks: [
                    { type: 'text', content: 'Confirmación significa que el mercado ha mostrado evidencia objetiva de que tu hipótesis es correcta, antes de comprometer capital. Un setup "potencial" no es lo mismo que un setup "confirmado". La diferencia entre ambos es exactamente el trigger que definiste en tu plan.' },
                    { type: 'chart', id: 'confirmation_definition' },
                    { type: 'concept', title: 'El coste de la impaciencia', content: 'Entrar antes de la confirmación significa operar sobre una hipótesis no probada. Si el setup era válido, llegarás un poco tarde pero seguro. Si el setup era una trampa, te ahorras la pérdida. La pequeña porción de movimiento que "pierdes" esperando confirmación es el precio de evitar las trampas — un precio que vale la pena pagar siempre.' },
                ]
            },
            {
                heading: 'Tipos de confirmación según el setup',
                blocks: [
                    { type: 'text', content: 'La confirmación específica depende del tipo de setup. Pero todas comparten una característica: son observables objetivamente, no interpretables.' },
                    { type: 'chart', id: 'confirmation_types' },
                    { type: 'table',
                        headers: ['Setup', 'Confirmación requerida'],
                        rows: [
                            ['Ruptura de resistencia', 'Cierre por encima del nivel, no solo mecha'],
                            ['Retroceso a soporte', 'Vela de rechazo (martillo, engulfing) en el nivel'],
                            ['Patrón de continuación', 'Ruptura con volumen > 1.5x promedio'],
                            ['Reversión de tendencia', 'Cambio de estructura confirmado (nuevo HH tras LL)'],
                            ['Retest tras ruptura', 'Rechazo en el retest, no ruptura del nivel'],
                        ]
                    },
                ]
            },
            {
                heading: 'La diferencia entre paciencia y miedo',
                blocks: [
                    { type: 'text', content: 'Esperar confirmación no es lo mismo que tener miedo de operar. La paciencia disciplinada espera la señal definida en el plan. El miedo evita entrar incluso cuando la señal ya apareció. Distinguir entre ambos es clave para no caer en parálisis por análisis.' },
                    { type: 'chart', id: 'patience_vs_fear' },
                    { type: 'warning', content: 'Si la confirmación ya apareció según tu plan y sigues dudando, eso no es paciencia — es miedo, y necesita resolverse de forma distinta. Revisa tu plan: si la confirmación está ahí, el trabajo de análisis ya está hecho. El siguiente paso es ejecutar, no seguir esperando "una señal más fuerte".' },
                ]
            },
            {
                heading: 'Cómo entrenar la paciencia',
                blocks: [
                    { type: 'text', content: 'La paciencia no es un rasgo de personalidad fijo — es una habilidad que se entrena con repetición y registro consciente de resultados. Cada vez que esperas confirmación y evitas una trampa, refuerzas el comportamiento correcto.' },
                    { type: 'chart', id: 'patience_training' },
                    { type: 'tip', label: 'EJERCICIO', content: 'Durante un mes, anota cada vez que sientas el impulso de entrar antes de la confirmación. Anota qué pasó después (¿habría sido un trade ganador o perdedor?). Tras 20-30 registros, tendrás datos objetivos sobre si tu impaciencia te habría ayudado o perjudicado — casi siempre la segunda.' },
                ]
            },
        ]
    },

    // ── MÓDULO 13, LECCIÓN 2 ───────────────────────────────────────────────
    '13-2': {
        moduleId: 13,
        lessonIndex: 1,
        title: 'Evitar Entradas Prematuras',
        duration: '9 min',
        intro: 'Las entradas prematuras son la causa número uno de pérdidas evitables. No son errores de análisis — son errores de timing y disciplina. El setup era correcto, pero la ejecución llegó demasiado pronto.',
        sections: [
            {
                heading: 'Anatomía de una entrada prematura',
                blocks: [
                    { type: 'text', content: 'Una entrada prematura ocurre cuando entras en el setup antes de que se complete el trigger definido. El precio "parece" que va a confirmar, pero no lo ha hecho todavía. Esta diferencia de unos minutos u horas puede ser la diferencia entre un trade ganador y uno perdedor.' },
                    { type: 'chart', id: 'premature_entry_anatomy' },
                    { type: 'concept', title: 'El falso ahorro de la entrada anticipada', content: 'Entrar antes "para conseguir mejor precio" suena lógico, pero ignora que el trigger existe precisamente para filtrar las situaciones donde el setup no se confirma. El "mejor precio" de la entrada anticipada solo importa si el trade funciona — y la tasa de éxito de entradas sin confirmación es estructuralmente menor.' },
                ]
            },
            {
                heading: 'Las trampas más comunes de entrada anticipada',
                blocks: [
                    { type: 'text', content: 'Hay patrones repetitivos de cómo el cerebro justifica entrar antes de tiempo. Reconocerlos te permite interrumpir el proceso antes de ejecutar.' },
                    { type: 'chart', id: 'premature_entry_traps' },
                    { type: 'steps', items: [
                        '<strong>"Va a romper seguro":</strong> el precio se acerca a la resistencia y asumes que romperá sin esperar el cierre',
                        '<strong>FOMO de movimiento rápido:</strong> el precio sube rápido y entras por miedo a perderte el movimiento',
                        '<strong>Anclaje en el análisis previo:</strong> llevas días analizando el setup y entras en cuanto se acerca, sin esperar el trigger exacto',
                        '<strong>Entrada en pre-market/after-hours:</strong> operar fuera de horario con liquidez reducida, sin esperar la confirmación de la sesión regular',
                    ]},
                ]
            },
            {
                heading: 'El coste estadístico de la impaciencia',
                blocks: [
                    { type: 'text', content: 'Las entradas sin confirmación tienen una tasa de éxito estructuralmente menor que las entradas con trigger completo, porque incluyen todos los casos donde el setup finalmente NO se confirma — que son exactamente los casos que el trigger está diseñado para filtrar.' },
                    { type: 'chart', id: 'premature_entry_stats' },
                    { type: 'table',
                        headers: ['Tipo de entrada', 'Tasa de éxito aproximada', 'Razón'],
                        rows: [
                            ['Con confirmación completa', '55-65%', 'El trigger filtra falsas señales'],
                            ['Anticipada (sin cierre confirmado)', '35-45%', 'Incluye rupturas que fallan'],
                            ['Por FOMO (movimiento ya iniciado)', '30-40%', 'Entras tarde en el movimiento real'],
                        ]
                    },
                ]
            },
            {
                heading: 'Protocolo anti-impaciencia',
                blocks: [
                    { type: 'text', content: 'La solución práctica a la impaciencia no es "tener más disciplina" en abstracto — es crear fricción física entre el impulso y la ejecución. Cuanto más difícil sea ejecutar impulsivamente, menos veces lo harás.' },
                    { type: 'chart', id: 'anti_impatience_protocol' },
                    { type: 'tip', label: 'TÉCNICA DE LA REGLA DE 10 MINUTOS', content: 'Cuando sientas el impulso de entrar antes del trigger, espera 10 minutos sin tocar nada. En la mayoría de los casos, el impulso emocional se reduce significativamente en ese tiempo y puedes evaluar la situación con más objetividad. Si después de 10 minutos el trigger se ha completado, entra. Si no, sigue esperando.' },
                ]
            },
        ]
    },

    // ── MÓDULO 13, LECCIÓN 3 ───────────────────────────────────────────────
    '13-3': {
        moduleId: 13,
        lessonIndex: 2,
        title: 'Seguir el Plan',
        duration: '9 min',
        intro: 'Tener un plan no sirve de nada si lo abandonas en cuanto el mercado se mueve de forma inesperada. Seguir el plan, especialmente cuando es incómodo hacerlo, es la habilidad que distingue al trader consistente del que tiene buenas rachas seguidas de pérdidas grandes.',
        sections: [
            {
                heading: 'Por qué abandonamos el plan',
                blocks: [
                    { type: 'text', content: 'El plan se diseña en calma, antes de que el dinero esté en riesgo. Se abandona bajo presión, cuando el precio se mueve en tu contra o cuando una ganancia parcial activa la codicia por más. El plan está diseñado precisamente para esos momentos — abandonarlo cuando más se necesita es la paradoja central de la disciplina en trading.' },
                    { type: 'chart', id: 'why_abandon_plan' },
                    { type: 'concept', title: 'El plan como contrato con tu yo futuro', content: 'Piensa en el plan de trade como un contrato firmado por tu yo racional (antes de entrar) con tu yo emocional (durante el trade). Romper el contrato en el momento de presión es exactamente lo que el contrato estaba diseñado para prevenir. Cada vez que lo cumples a pesar de la incomodidad, refuerzas tu capacidad de cumplirlo la próxima vez.' },
                ]
            },
            {
                heading: 'Las dos formas de abandonar el plan',
                blocks: [
                    { type: 'text', content: 'Hay dos direcciones opuestas en las que se abandona un plan: salir demasiado pronto por miedo, o aguantar demasiado tiempo por esperanza. Ambas son igualmente dañinas pero requieren correcciones distintas.' },
                    { type: 'chart', id: 'two_ways_abandon' },
                    { type: 'table',
                        headers: ['Tipo de abandono', 'Causa emocional', 'Consecuencia'],
                        rows: [
                            ['Salir antes del stop', 'Miedo a la pérdida total', 'Conviertes pérdidas pequeñas en patrón de salidas tempranas que recortan ganadores también'],
                            ['Aguantar tras el stop', 'Esperanza de recuperación', 'Conviertes pérdidas controladas en pérdidas grandes'],
                            ['Salir antes del objetivo', 'Miedo a perder la ganancia', 'Cortas ganadores prematuramente, reduces el R:R real'],
                            ['Aguantar tras el objetivo sin plan', 'Codicia por más ganancia', 'Conviertes ganadores en pérdidas cuando el precio revierte'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cuándo SÍ está bien desviarse del plan',
                blocks: [
                    { type: 'text', content: 'Seguir el plan no significa rigidez absoluta sin capacidad de adaptación. Hay situaciones legítimas donde modificar el plan es la decisión correcta — pero deben ser excepcionales y basadas en información nueva, no en emociones del momento.' },
                    { type: 'chart', id: 'when_deviate_legit' },
                    { type: 'steps', items: [
                        '<strong>Noticia material inesperada:</strong> earnings, M&A, cambio regulatorio que invalida la tesis original',
                        '<strong>Cambio de régimen de mercado:</strong> VIX se dispara repentinamente durante el trade',
                        '<strong>Error objetivo en el plan original:</strong> descubres que calculaste mal un nivel técnico',
                    ]},
                    { type: 'warning', content: 'Lo que NO es una razón legítima para desviarse: "el precio se acerca al stop y tengo una corazonada de que va a rebotar", "he visto un tweet bajista", "estoy nervioso por la posición". Estas son reacciones emocionales disfrazadas de razonamiento — no información nueva real.' },
                ]
            },
            {
                heading: 'Construir el hábito de seguir el plan',
                blocks: [
                    { type: 'text', content: 'Seguir el plan es un músculo que se fortalece con repetición. Cada vez que lo sigues incluso cuando es incómodo, refuerzas la conexión entre intención y ejecución. Cada vez que lo abandonas, debilitas esa conexión y haces más probable que lo abandones la próxima vez.' },
                    { type: 'chart', id: 'plan_following_habit' },
                    { type: 'tip', label: 'MÉTRICA DE ADHERENCIA', content: 'Registra en tu journal, además del resultado del trade, si seguiste el plan al 100%. Calcula tu "tasa de adherencia al plan" mensualmente. El objetivo no es ganar todos los trades — es seguir el plan en el 95%+ de las ocasiones. La rentabilidad sigue naturalmente a la disciplina consistente.' },
                ]
            },
        ]
    },

    // ── MÓDULO 13, LECCIÓN 4 ───────────────────────────────────────────────
    '13-4': {
        moduleId: 13,
        lessonIndex: 3,
        title: 'Salir Sin Ego',
        duration: '9 min',
        intro: 'El ego es el enemigo silencioso de la salida correcta. Aceptar que estabas equivocado, cerrar una posición ganadora antes de que se convierta en perdedora, o admitir que el mercado cambió — todo esto requiere dejar el ego fuera de la ecuación.',
        sections: [
            {
                heading: 'Cómo el ego sabotea las salidas',
                blocks: [
                    { type: 'text', content: 'El ego convierte cada trade en una declaración sobre tu identidad como trader, en lugar de una simple transacción probabilística. "Tener razón" se vuelve más importante que "ganar dinero" — y estas dos cosas no siempre coinciden.' },
                    { type: 'chart', id: 'ego_sabotage' },
                    { type: 'concept', title: 'Tener razón vs ganar dinero', content: 'Puedes tener razón sobre la dirección del mercado y aun así perder dinero por mala ejecución. Puedes estar equivocado sobre la tesis y aun así ganar dinero por una buena gestión del riesgo. El objetivo del trading no es tener razón — es ser rentable de forma consistente. El ego confunde ambas cosas constantemente.' },
                ]
            },
            {
                heading: 'Salir de pérdidas sin ego',
                blocks: [
                    { type: 'text', content: 'Cerrar una posición perdedora según el plan no es un fracaso personal — es la ejecución correcta de un sistema probabilístico. El ego interpreta el stop como "estaba equivocado, soy mal trader". La mentalidad correcta lo interpreta como "el setup no funcionó esta vez, sigo el siguiente".' },
                    { type: 'chart', id: 'exit_loss_no_ego' },
                    { type: 'steps', items: [
                        'El stop salta según el plan → ejecutas sin dudarlo',
                        'No revisas el gráfico durante 30 minutos después (evita el impulso de re-entrar por venganza)',
                        'Anota el trade en el journal con el resultado objetivo',
                        'Pasas al siguiente setup sin cargar emocionalmente la pérdida anterior',
                    ]},
                ]
            },
            {
                heading: 'Salir de ganancias sin ego',
                blocks: [
                    { type: 'text', content: 'Paradójicamente, el ego también sabotea las salidas ganadoras. "Si he ganado tanto, puedo ganar más" lleva a no respetar el plan de salida y convertir ganancias en pérdidas cuando el mercado revierte. La codicia es la otra cara del ego.' },
                    { type: 'chart', id: 'exit_profit_no_ego' },
                    { type: 'warning', content: 'El error más común en salidas ganadoras es mover el objetivo "porque el momentum es muy fuerte" sin una base técnica real para hacerlo. Si tu plan decía vender en el objetivo 1 y el precio lo alcanza, vendes — independientemente de cuán fuerte parezca el momentum. Puedes definir un objetivo 2 para un runner, pero eso debe estar en el plan original, no improvisado en el momento.' },
                ]
            },
            {
                heading: 'Reconocer cuando el mercado cambió',
                blocks: [
                    { type: 'text', content: 'A veces el mercado cambia las reglas a mitad del trade — un cambio macro inesperado, una rotación sectorial repentina, un evento sistémico. El ego se resiste a reconocer estos cambios porque significa admitir que el análisis original ya no aplica.' },
                    { type: 'chart', id: 'recognize_market_change' },
                    { type: 'tip', label: 'PREGUNTA DE REALIDAD', content: 'Si tuvieras que abrir este trade hoy, desde cero, con la información que tienes ahora — ¿lo abrirías? Si la respuesta es no, no tienes ninguna razón para mantenerlo solo porque ya lo abriste antes. El capital invertido en el pasado (sunk cost) no debe influir en la decisión presente.' },
                ]
            },
        ]
    },
    // ── MÓDULO 14, LECCIÓN 1 ───────────────────────────────────────────────
    '14-1': {
        moduleId: 14,
        lessonIndex: 0,
        title: 'Falsas Rupturas',
        duration: '9 min',
        intro: 'Las falsas rupturas son la trampa más cara del trading técnico. El precio rompe un nivel, todo el mundo entra convencido de la continuación, y el mercado revierte bruscamente — atrapando a los que entraron tarde y beneficiando a quien esperó confirmación real.',
        sections: [
            {
                heading: 'Por qué existen las falsas rupturas',
                blocks: [
                    { type: 'text', content: 'Las falsas rupturas no son aleatorias — son frecuentemente el resultado de actividad institucional deliberada. Los grandes operadores necesitan liquidez para entrar o salir de posiciones grandes. Empujar el precio a través de un nivel obvio (donde hay stops acumulados) genera esa liquidez al activar las órdenes de los traders retail.' },
                    { type: 'chart', id: 'fake_breakout_why' },
                    { type: 'concept', title: 'Caza de stops (Stop Hunt)', content: 'Cuando un nivel de soporte o resistencia es muy obvio (visible para cualquiera con un gráfico), también es donde más stops loss están agrupados. Las instituciones con suficiente capital pueden empujar el precio brevemente a través de ese nivel para activar esos stops, conseguir la liquidez que necesitan, y luego dejar que el precio vuelva a su rango natural.' },
                ]
            },
            {
                heading: 'Anatomía de una falsa ruptura',
                blocks: [
                    { type: 'text', content: 'Las falsas rupturas siguen un patrón reconocible: ruptura del nivel, volumen débil o moderado (no explosivo), y reversión rápida de vuelta dentro del rango en pocas velas.' },
                    { type: 'chart', id: 'fake_breakout_anatomy' },
                    { type: 'table',
                        headers: ['Señal', 'Ruptura real', 'Falsa ruptura'],
                        rows: [
                            ['Volumen en la ruptura', 'Alto, >1.5x promedio', 'Bajo o normal'],
                            ['Cierre de la vela', 'Cierra claramente fuera del rango', 'Cierra cerca del nivel o dentro'],
                            ['Velocidad de reversión', 'No revierte en 1-2 días', 'Revierte en 1-3 velas'],
                            ['Contexto de tendencia', 'A favor de la tendencia mayor', 'Contra la tendencia mayor'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cómo protegerte de las falsas rupturas',
                blocks: [
                    { type: 'text', content: 'La defensa contra las falsas rupturas no es predecirlas con certeza — es esperar confirmación suficiente antes de comprometer capital, y aceptar que algunas rupturas reales se "pierden" como precio de evitar las trampas.' },
                    { type: 'chart', id: 'fake_breakout_protection' },
                    { type: 'steps', items: [
                        'Espera el cierre de la vela, no solo que el precio toque el nivel',
                        'Confirma con volumen superior a 1.5x el promedio',
                        'Si es posible, espera el retest del nivel roto antes de entrar (más conservador, menos beneficio pero más seguro)',
                        'Evita operar rupturas contra la tendencia mayor — son las que más fallan',
                    ]},
                ]
            },
            {
                heading: 'Cuando ya estás atrapado en una falsa ruptura',
                blocks: [
                    { type: 'text', content: 'Si entraste en una ruptura que resultó falsa, la respuesta correcta es salir según tu stop, sin intentar "esperar a que vuelva". El reconocimiento rápido del error limita el daño.' },
                    { type: 'chart', id: 'fake_breakout_trapped' },
                    { type: 'warning', content: 'El peor error tras una falsa ruptura es promediar la posición ("ya que estoy aquí, compro más abajo") o mover el stop esperando que el precio recupere. La falsa ruptura ya invalidó tu hipótesis original — el stop debe ejecutarse, no negociarse.' },
                ]
            },
        ]
    },

    // ── MÓDULO 14, LECCIÓN 2 ───────────────────────────────────────────────
    '14-2': {
        moduleId: 14,
        lessonIndex: 1,
        title: 'Entradas Tardías',
        duration: '9 min',
        intro: 'Entrar tarde en un movimiento ya extendido es una de las formas más comunes y silenciosas de perder dinero. El movimiento parece obvio en retrospectiva, pero entrar después de que la mayor parte del recorrido ya ocurrió cambia completamente el perfil de riesgo del trade.',
        sections: [
            {
                heading: 'Por qué entramos tarde',
                blocks: [
                    { type: 'text', content: 'El sesgo de disponibilidad hace que prestemos más atención a lo que ya está sucediendo de forma visible (un movimiento en curso, ya en todas las noticias) que a setups menos obvios en formación. Para cuando un movimiento es "obvio" para el trader promedio, la parte de mejor R:R ya ha pasado.' },
                    { type: 'chart', id: 'late_entry_why' },
                    { type: 'concept', title: 'El movimiento visible vs el setup temprano', content: 'Cuando un movimiento aparece en titulares financieros o se vuelve tendencia en redes sociales, normalmente ya ha recorrido la mayor parte de su camino. Los traders que detectaron el setup temprano (con análisis propio, antes de la atención mediática) capturaron el movimiento con mejor R:R. Los que entran "cuando todo el mundo habla de ello" entran tarde y con peor relación riesgo/recompensa.' },
                ]
            },
            {
                heading: 'Cómo identificar que ya es tarde',
                blocks: [
                    { type: 'text', content: 'Hay señales objetivas de que un movimiento ya está extendido y el R:R de entrar ahora es desfavorable, independientemente de cuán fuerte parezca el momentum.' },
                    { type: 'chart', id: 'late_entry_signs' },
                    { type: 'table',
                        headers: ['Señal', 'Implicación'],
                        rows: [
                            ['Precio extendido >20% sobre MA20', 'Probable sobrecompra de corto plazo'],
                            ['RSI diario >75 sostenido', 'Momentum agotándose, riesgo de pullback'],
                            ['Aparece en titulares financieros masivos', 'La fase pública del movimiento, no la temprana'],
                            ['Distancia al stop técnico > 2x distancia al objetivo', 'R:R desfavorable para nueva entrada'],
                        ]
                    },
                ]
            },
            {
                heading: 'Qué hacer cuando ya es tarde',
                blocks: [
                    { type: 'text', content: 'Reconocer que llegaste tarde a un movimiento no significa que no puedas participar — significa que debes esperar una entrada de mejor calidad en lugar de perseguir el precio actual.' },
                    { type: 'chart', id: 'late_entry_alternatives' },
                    { type: 'steps', items: [
                        '<strong>Esperar el primer pullback:</strong> el precio normalmente retrocede a una EMA o nivel de soporte antes de continuar',
                        '<strong>Reducir el tamaño:</strong> si decides entrar de todas formas, usa menos capital del habitual dado el peor R:R',
                        '<strong>Dejarlo pasar:</strong> la opción más disciplinada — hay siempre otro setup. No todos los movimientos son para ti.',
                    ]},
                ]
            },
            {
                heading: 'FOMO: el motor psicológico de las entradas tardías',
                blocks: [
                    { type: 'text', content: 'El FOMO (Fear Of Missing Out) es el motor emocional detrás de la mayoría de entradas tardías. La sensación de "todo el mundo está ganando dinero menos yo" nubla el análisis objetivo del R:R disponible.' },
                    { type: 'chart', id: 'fomo_mechanism' },
                    { type: 'tip', label: 'REGLA DE LA OPORTUNIDAD PERDIDA', content: 'Acepta de antemano que vas a "perderte" la mayoría de los movimientos grandes del mercado. Es matemáticamente imposible capturarlos todos. La pregunta correcta no es "¿cómo entro en este movimiento que ya pasó?" sino "¿cuál es el siguiente setup de calidad en mi watchlist?". El mercado siempre ofrece nuevas oportunidades — perseguir las que ya pasaron es la trampa.' },
                ]
            },
        ]
    },

    // ── MÓDULO 14, LECCIÓN 3 ───────────────────────────────────────────────
    '14-3': {
        moduleId: 14,
        lessonIndex: 2,
        title: 'Sobretrading',
        duration: '9 min',
        intro: 'El sobretrading es operar más de lo que la calidad de las oportunidades disponibles justifica. No es un problema de cantidad de trades en sí — es un problema de calidad decreciente cuando se fuerza la actividad.',
        sections: [
            {
                heading: 'Qué es el sobretrading',
                blocks: [
                    { type: 'text', content: 'El sobretrading ocurre cuando operas por la necesidad de "hacer algo" en lugar de por la presencia de un setup genuino de calidad. La frecuencia de tus trades debería estar determinada por la frecuencia con que aparecen setups válidos — no por tu deseo de estar activo en el mercado.' },
                    { type: 'chart', id: 'overtrading_definition' },
                    { type: 'concept', title: 'Actividad vs productividad', content: 'En muchos trabajos, más horas trabajadas correlaciona con más producido. En trading, esta lógica falla completamente. Más trades no significa más ganancias — frecuentemente significa lo contrario, porque los trades adicionales suelen ser de menor calidad que los primeros que identificaste con tu análisis disciplinado.' },
                ]
            },
            {
                heading: 'Las causas del sobretrading',
                blocks: [
                    { type: 'text', content: 'El sobretrading tiene raíces emocionales específicas que se pueden identificar y abordar individualmente.' },
                    { type: 'chart', id: 'overtrading_causes' },
                    { type: 'table',
                        headers: ['Causa', 'Patrón típico'],
                        rows: [
                            ['Aburrimiento', 'Operar por entretenimiento en mercados laterales sin setups'],
                            ['Revenge trading', 'Aumentar frecuencia tras pérdidas para "recuperar rápido"'],
                            ['Adicción a la dopamina', 'Buscar la sensación de abrir posiciones constantemente'],
                            ['Sobreconfianza tras racha ganadora', 'Sentir que "todo funciona" y bajar el estándar de calidad'],
                            ['Miedo a perderse oportunidades', 'Entrar en cada setup remotamente posible por FOMO acumulado'],
                        ]
                    },
                ]
            },
            {
                heading: 'El coste real del sobretrading',
                blocks: [
                    { type: 'text', content: 'Más allá de las pérdidas directas de trades de menor calidad, el sobretrading tiene costes ocultos: comisiones acumuladas, fatiga de decisión, y el deterioro de la capacidad de evaluar objetivamente cada nuevo setup tras docenas de decisiones en poco tiempo.' },
                    { type: 'chart', id: 'overtrading_real_cost' },
                    { type: 'warning', content: 'Las comisiones y el spread bid-ask en 50 trades mensuales pueden representar una erosión significativa de la cuenta incluso si la tasa de aciertos es decente. En cambio, 5-10 trades mensuales de alta calidad con buen R:R reducen drásticamente este coste estructural.' },
                ]
            },
            {
                heading: 'Límites prácticos contra el sobretrading',
                blocks: [
                    { type: 'text', content: 'Establecer límites objetivos y mecánicos es más efectivo que intentar "tener más disciplina" en abstracto. Los límites quitan la decisión del momento de presión.' },
                    { type: 'chart', id: 'overtrading_limits' },
                    { type: 'steps', items: [
                        '<strong>Límite diario:</strong> máximo 2-3 trades nuevos por día, independientemente de cuántos setups "veas"',
                        '<strong>Límite semanal:</strong> revisar el número total de trades cada domingo — si supera tu media histórica, pregúntate por qué',
                        '<strong>Regla de la watchlist:</strong> solo operas activos que estaban en tu lista del domingo, nunca improvisados',
                        '<strong>Cooldown tras pérdida:</strong> pausa de al menos 1 hora tras cualquier stop antes de considerar el siguiente trade',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 14, LECCIÓN 4 ───────────────────────────────────────────────
    '14-4': {
        moduleId: 14,
        lessonIndex: 3,
        title: 'Ignorar el Volumen',
        duration: '9 min',
        intro: 'El volumen es la dimensión del mercado que más se ignora y la que más información proporciona sobre la convicción real detrás de un movimiento de precio. Operar sin mirar el volumen es como conducir mirando solo el velocímetro sin mirar la carretera.',
        sections: [
            {
                heading: 'Por qué se ignora el volumen',
                blocks: [
                    { type: 'text', content: 'El precio es visualmente más llamativo — sube, baja, forma patrones evidentes. El volumen aparece como barras grises en la parte inferior del gráfico, fácil de ignorar. Pero el volumen es la "verdad" detrás del movimiento de precio: confirma si hay convicción real o simplemente ruido sin sustancia.' },
                    { type: 'chart', id: 'why_ignore_volume' },
                    { type: 'concept', title: 'El precio sin volumen es ruido', content: 'Un movimiento de precio del 5% con volumen normal es estadísticamente diferente de un movimiento del 5% con volumen 3 veces el promedio. El primero puede ser ruido de mercado sin importancia duradera. El segundo representa una decisión institucional significativa que probablemente tiene continuidad.' },
                ]
            },
            {
                heading: 'Las señales de volumen más importantes que se ignoran',
                blocks: [
                    { type: 'text', content: 'Hay patrones específicos de volumen que, cuando se ignoran, llevan a trades de menor calidad de forma sistemática.' },
                    { type: 'chart', id: 'volume_signals_ignored' },
                    { type: 'table',
                        headers: ['Patrón de volumen', 'Lo que indica', 'Error común al ignorarlo'],
                        rows: [
                            ['Ruptura con volumen bajo', 'Probable falsa ruptura', 'Entrar igual confiando solo en el precio'],
                            ['Pullback con volumen alto', 'Posible distribución, no pullback sano', 'Comprar el pullback sin verificar'],
                            ['Volumen clímax en mínimos', 'Posible capitulación, suelo cercano', 'No reconocer la oportunidad de reversión'],
                            ['Divergencia precio-volumen', 'Movimiento perdiendo fuerza', 'Mantener posición sin precaución adicional'],
                        ]
                    },
                ]
            },
            {
                heading: 'Incorporar el volumen al proceso de decisión',
                blocks: [
                    { type: 'text', content: 'El volumen no debe ser una verificación opcional al final del análisis — debe estar integrado en cada paso del proceso de decisión, desde la identificación del setup hasta la confirmación de entrada.' },
                    { type: 'chart', id: 'volume_integration_process' },
                    { type: 'steps', items: [
                        '<strong>Al identificar el setup:</strong> ¿el contexto muestra acumulación o distribución reciente?',
                        '<strong>Al esperar confirmación:</strong> ¿el trigger viene acompañado de volumen elevado?',
                        '<strong>Durante el trade:</strong> ¿el volumen en los pullbacks es bajo (sano) o alto (preocupante)?',
                        '<strong>Al considerar la salida:</strong> ¿hay señales de volumen clímax o divergencia que sugieran agotamiento?',
                    ]},
                ]
            },
            {
                heading: 'El volumen como filtro final antes de cualquier entrada',
                blocks: [
                    { type: 'text', content: 'Como regla práctica final, ningún trade debería ejecutarse sin haber verificado explícitamente el volumen del trigger. Esta verificación toma segundos pero elimina una proporción significativa de las entradas de baja calidad.' },
                    { type: 'chart', id: 'volume_final_filter' },
                    { type: 'tip', label: 'CHECKLIST DE VOLUMEN', content: 'Antes de cada entrada, responde: ¿el volumen del día de la señal es superior al promedio de 20 días? Si la respuesta es no, el trade pasa de "alta convicción" a "especulativo" — ajusta el tamaño de posición o espera mejor confirmación. Esta única pregunta filtra muchas trampas.' },
                ]
            },
        ]
    },
    // ── MÓDULO 15, LECCIÓN 1 ───────────────────────────────────────────────
    '15-1': {
        moduleId: 15,
        lessonIndex: 0,
        title: 'Captura de Pantalla',
        duration: '8 min',
        intro: 'El primer paso de cualquier revisión seria es tener evidencia visual del trade tal y como se veía en el momento de la decisión. La memoria es notoriamente poco fiable para reconstruir con precisión lo que realmente viste y pensaste.',
        sections: [
            {
                heading: 'Por qué la memoria no es suficiente',
                blocks: [
                    { type: 'text', content: 'Días o semanas después de un trade, tu memoria reconstituye los hechos de forma que confirma la narrativa que ya tienes sobre ti mismo como trader. Si crees que eres disciplinado, recordarás el trade como más metódico de lo que fue. Si te sientes mal por una pérdida, recordarás el setup como peor de lo que parecía en el momento. La captura de pantalla elimina esta distorsión.' },
                    { type: 'chart', id: 'memory_unreliable' },
                    { type: 'concept', title: 'Sesgo retrospectivo (hindsight bias)', content: 'Una vez conoces el resultado de un trade, tu cerebro reescribe automáticamente cómo "deberías haber sabido" lo que iba a pasar. Esto hace casi imposible evaluar objetivamente la calidad de la decisión original sin evidencia visual congelada en el momento exacto de la entrada.' },
                ]
            },
            {
                heading: 'Qué capturar en cada trade',
                blocks: [
                    { type: 'text', content: 'No basta con una captura del gráfico al entrar. Una revisión completa necesita capturas en momentos específicos que documenten la evolución de tu razonamiento y del mercado.' },
                    { type: 'chart', id: 'what_to_capture' },
                    { type: 'steps', items: [
                        '<strong>Pre-entrada:</strong> el gráfico exacto que viste cuando decidiste entrar, con niveles marcados',
                        '<strong>Al entrar:</strong> la vela de confirmación/trigger específica que activó la entrada',
                        '<strong>Contexto multi-temporal:</strong> capturas de mensual, semanal y diario en el momento de la decisión',
                        '<strong>Al salir:</strong> el gráfico en el momento del cierre (stop o objetivo)',
                    ]},
                ]
            },
            {
                heading: 'Cómo organizar las capturas',
                blocks: [
                    { type: 'text', content: 'Sin un sistema de organización, las capturas se acumulan sin valor. Un sistema simple de carpetas por mes y ticker permite encontrar y revisar trades rápidamente meses después.' },
                    { type: 'chart', id: 'organize_screenshots' },
                    { type: 'table',
                        headers: ['Estructura', 'Ejemplo'],
                        rows: [
                            ['Carpeta por mes', '2026-06/'],
                            ['Subcarpeta por ticker', '2026-06/NVDA_trade1/'],
                            ['Nombrado de archivo', 'pre-entrada.png, entrada.png, salida.png'],
                            ['Documento resumen', 'journal.md con enlaces a cada carpeta'],
                        ]
                    },
                ]
            },
            {
                heading: 'La disciplina de capturar siempre',
                blocks: [
                    { type: 'text', content: 'El hábito de capturar pantalla debe ser tan automático como definir el stop. Si solo capturas los trades que "salieron interesantes", tu archivo estará sesgado hacia ciertos resultados y perderá valor como herramienta de aprendizaje objetivo.' },
                    { type: 'chart', id: 'always_capture_discipline' },
                    { type: 'tip', label: 'AUTOMATIZACIÓN', content: 'Configura un atajo de teclado para capturar pantalla instantáneamente. Hazlo parte literal de tu checklist de entrada: definir stop, definir objetivo, capturar pantalla, ejecutar. Si no está en el checklist, se te olvidará en los momentos de mayor presión — que son precisamente los trades más importantes de revisar.' },
                ]
            },
        ]
    },

    // ── MÓDULO 15, LECCIÓN 2 ───────────────────────────────────────────────
    '15-2': {
        moduleId: 15,
        lessonIndex: 1,
        title: 'Registro de Errores',
        duration: '8 min',
        intro: 'No todos los trades perdedores son errores, y no todos los errores producen trades perdedores. Distinguir entre el resultado de un trade y la calidad del proceso que lo generó es la base de un registro de errores útil.',
        sections: [
            {
                heading: 'La diferencia entre pérdida y error',
                blocks: [
                    { type: 'text', content: 'Una pérdida ocurre cuando el setup, ejecutado correctamente según el plan, simplemente no funciona — esto es estadísticamente normal y esperado. Un error ocurre cuando te desvías del proceso correcto, independientemente de si el resultado fue ganador o perdedor.' },
                    { type: 'chart', id: 'loss_vs_error' },
                    { type: 'table',
                        headers: ['Situación', 'Clasificación'],
                        rows: [
                            ['Plan seguido, stop ejecutado, pérdida', 'Pérdida normal (no error)'],
                            ['Plan seguido, objetivo alcanzado, ganancia', 'Trade correcto (no error)'],
                            ['Entrada sin confirmación, resultó ganador', 'ERROR (aunque el resultado fue bueno)'],
                            ['Movió el stop por miedo, evitó pérdida', 'ERROR (aunque el resultado fue bueno)'],
                            ['Siguió el plan al 100%, resultó perdedor', 'No es error — coste normal del negocio'],
                        ]
                    },
                ]
            },
            {
                heading: 'Categorías de errores a registrar',
                blocks: [
                    { type: 'text', content: 'Un registro de errores útil clasifica cada desviación del proceso en categorías reconocibles, lo que permite identificar patrones a lo largo del tiempo en lugar de tratar cada error como un evento aislado.' },
                    { type: 'chart', id: 'error_categories' },
                    { type: 'steps', items: [
                        '<strong>Errores de entrada:</strong> sin confirmación, tamaño incorrecto, setup fuera de watchlist',
                        '<strong>Errores de gestión:</strong> mover el stop, no mover a breakeven cuando correspondía',
                        '<strong>Errores de salida:</strong> salir antes del plan, no salir cuando el plan lo indicaba',
                        '<strong>Errores de contexto:</strong> ignorar el estado del mercado general o sectorial',
                        '<strong>Errores emocionales:</strong> revenge trading, FOMO, sobretrading',
                    ]},
                ]
            },
            {
                heading: 'Cómo registrar cada error de forma útil',
                blocks: [
                    { type: 'text', content: 'Un registro de error efectivo no es solo "qué pasó" sino "por qué pasó" y "qué harás diferente la próxima vez". Sin esta tercera parte, el registro es solo documentación sin valor de mejora.' },
                    { type: 'chart', id: 'error_log_format' },
                    { type: 'concept', title: 'Plantilla de registro de error', content: 'Fecha | Ticker | Categoría de error | Qué pasó exactamente | Por qué crees que pasó (estado emocional, contexto) | Qué harás diferente la próxima vez en una situación similar. Esta última columna es la más importante — convierte el error en aprendizaje concreto y accionable.' },
                ]
            },
            {
                heading: 'Revisar el registro periódicamente',
                blocks: [
                    { type: 'text', content: 'Un registro de errores que nunca se revisa es tan inútil como no tener registro. La revisión mensual permite identificar patrones que no son visibles trade por trade — por ejemplo, que el 70% de tus errores ocurren los viernes por la tarde, o que siempre son del tipo "entrada sin confirmación".' },
                    { type: 'chart', id: 'error_log_review' },
                    { type: 'tip', label: 'REVISIÓN MENSUAL', content: 'El primer domingo de cada mes, revisa todos los errores registrados del mes anterior y agrúpalos por categoría. Identifica la categoría más frecuente — esa es tu prioridad de mejora para el mes siguiente. Concentrarte en corregir un patrón a la vez es más efectivo que intentar arreglar todo simultáneamente.' },
                ]
            },
        ]
    },

    // ── MÓDULO 15, LECCIÓN 3 ───────────────────────────────────────────────
    '15-3': {
        moduleId: 15,
        lessonIndex: 2,
        title: 'Revisión del Setup',
        duration: '8 min',
        intro: 'Más allá de los errores de ejecución, una revisión completa evalúa la calidad del análisis original — si el setup tenía las características de un buen trade independientemente del resultado final.',
        sections: [
            {
                heading: 'Separar la calidad del análisis del resultado',
                blocks: [
                    { type: 'text', content: 'Un setup de alta calidad puede perder. Un setup de baja calidad puede ganar. Evaluar el setup en sí mismo, separado del resultado, es la única forma de mejorar realmente la capacidad de identificar oportunidades, en lugar de simplemente repetir lo que "funcionó la última vez" por azar.' },
                    { type: 'chart', id: 'setup_quality_separate' },
                    { type: 'concept', title: 'La matriz de evaluación de setups', content: 'Cruza calidad del análisis (alta/baja) con resultado del trade (ganador/perdedor). Los cuatro cuadrantes resultantes —buen análisis y ganó, buen análisis y perdió, mal análisis y ganó, mal análisis y perdió— requieren reacciones completamente distintas. El cuadrante más peligroso es "mal análisis y ganó" porque refuerza erróneamente comportamientos que deberían corregirse.' },
                ]
            },
            {
                heading: 'Preguntas para revisar el setup',
                blocks: [
                    { type: 'text', content: 'Una revisión sistemática del setup responde a un conjunto fijo de preguntas, independientemente del resultado del trade. Estas preguntas evalúan la calidad del proceso de análisis original.' },
                    { type: 'chart', id: 'setup_review_questions' },
                    { type: 'steps', items: [
                        '¿El contexto de mercado y sector estaba alineado al entrar?',
                        '¿El R:R era de al menos 1:2 con base técnica real (no forzado)?',
                        '¿El stop estaba en un nivel técnicamente válido?',
                        '¿Había confirmación de volumen en el trigger?',
                        '¿El setup estaba en la watchlist preparada con antelación?',
                    ]},
                ]
            },
            {
                heading: 'Identificar tus setups de mayor edge',
                blocks: [
                    { type: 'text', content: 'Con suficientes revisiones acumuladas, empiezan a emerger patrones sobre qué tipos de setup funcionan mejor para tu estilo particular. Esta información es más valiosa que cualquier "mejor estrategia" genérica — es tu edge personal específico.' },
                    { type: 'chart', id: 'identify_best_setups' },
                    { type: 'table',
                        headers: ['Tipo de setup', 'Trades registrados', 'Tasa de éxito', 'R:R promedio'],
                        rows: [
                            ['Retroceso a EMA21', '24', '67%', '1:2.3'],
                            ['Ruptura de base', '18', '56%', '1:2.8'],
                            ['Reversión desde suelo', '12', '50%', '1:3.1'],
                            ['Ruptura de triángulo', '15', '60%', '1:2.1'],
                        ]
                    },
                ]
            },
            {
                heading: 'Especializarse en lugar de diversificar setups',
                blocks: [
                    { type: 'text', content: 'Una vez identificados tus setups de mejor desempeño histórico, la estrategia óptima es concentrar más esfuerzo en encontrarlos y reducir el tiempo dedicado a setups de menor edge personal — incluso si técnicamente son válidos según la teoría general.' },
                    { type: 'chart', id: 'specialize_setups' },
                    { type: 'tip', label: 'EL EDGE ES PERSONAL', content: 'Dos traders pueden tener resultados muy diferentes con la misma estrategia general porque su capacidad de ejecutarla bien varía. No persigas la "mejor estrategia del mercado" — identifica en qué setups específicos tú personalmente tienes mejor desempeño histórico documentado, y especialízate ahí.' },
                ]
            },
        ]
    },

    // ── MÓDULO 15, LECCIÓN 4 ───────────────────────────────────────────────
    '15-4': {
        moduleId: 15,
        lessonIndex: 3,
        title: 'Lecciones Aprendidas',
        duration: '8 min',
        intro: 'La revisión post-trade culmina en un documento vivo de lecciones aprendidas — la síntesis de todo lo que el journal, el registro de errores y la revisión de setups han revelado sobre tu trading a lo largo del tiempo.',
        sections: [
            {
                heading: 'De datos individuales a sabiduría acumulada',
                blocks: [
                    { type: 'text', content: 'Cada trade individual aporta poca información. Pero cien trades revisados sistemáticamente revelan patrones robustos sobre tus fortalezas, debilidades y el tipo de trading que mejor se adapta a tu personalidad y disponibilidad de tiempo.' },
                    { type: 'chart', id: 'data_to_wisdom' },
                    { type: 'concept', title: 'El compuesto del aprendizaje', content: 'Así como el interés compuesto hace crecer el capital de forma exponencial con el tiempo, el aprendizaje compuesto de revisiones sistemáticas mejora tu toma de decisiones de forma acelerada. Los traders que llevan 5 años revisando consistentemente toman mejores decisiones que los que llevan 5 años operando sin revisión, incluso con el mismo número de trades ejecutados.' },
                ]
            },
            {
                heading: 'Estructura de un documento de lecciones aprendidas',
                blocks: [
                    { type: 'text', content: 'El documento de lecciones aprendidas no es un diario cronológico — es una síntesis organizada por temas que se actualiza y refina con cada revisión periódica.' },
                    { type: 'chart', id: 'lessons_document_structure' },
                    { type: 'table',
                        headers: ['Sección', 'Contenido'],
                        rows: [
                            ['Mis mejores setups', 'Los 3-5 tipos de setup con mejor edge personal documentado'],
                            ['Mis errores recurrentes', 'Los patrones de error que se repiten con más frecuencia'],
                            ['Mis condiciones óptimas', 'Estado de mercado, hora del día, contexto donde rindo mejor'],
                            ['Reglas personales', 'Reglas específicas derivadas de mi propia experiencia, no genéricas'],
                        ]
                    },
                ]
            },
            {
                heading: 'Actualizar las reglas personales con evidencia',
                blocks: [
                    { type: 'text', content: 'Las reglas personales más valiosas no vienen de libros de trading genéricos — vienen de tu propia evidencia acumulada. "Nunca opero los viernes por la tarde" o "mis mejores trades ocurren cuando espero el retest" son reglas con peso real porque están respaldadas por tus propios datos.' },
                    { type: 'chart', id: 'personal_rules_evidence' },
                    { type: 'steps', items: [
                        'Identifica un patrón en tus datos de journal (ej: peor desempeño en trades de viernes)',
                        'Verifica que el patrón se mantiene con suficiente muestra (mínimo 10-15 trades)',
                        'Formula una regla personal específica basada en esa evidencia',
                        'Añade la regla a tu checklist de pre-trade',
                        'Revisa la regla cada 3 meses para confirmar que sigue siendo válida',
                    ]},
                ]
            },
            {
                heading: 'El ciclo completo de mejora continua',
                blocks: [
                    { type: 'text', content: 'La revisión post-trade no es el final del proceso de trading — es el inicio del siguiente ciclo. Cada lección aprendida se incorpora al plan de trade, que genera nuevos trades, que generan nuevas revisiones. Este ciclo, repetido consistentemente, es el verdadero motor de la mejora a largo plazo.' },
                    { type: 'chart', id: 'continuous_improvement_cycle' },
                    { type: 'tip', label: 'EL TRADER QUE REVISA GANA', content: 'La diferencia más consistente entre traders rentables a largo plazo y traders que abandonan no es la inteligencia, el capital inicial o incluso la suerte temprana — es la disciplina de revisar sistemáticamente y ajustar el proceso basándose en evidencia propia. Este módulo cierra el círculo completo de la metodología RSU: análisis, ejecución, gestión del riesgo y revisión.' },
                ]
            },
        ]
    },
    // ── MÓDULO 16, LECCIÓN 1 ───────────────────────────────────────────────
    '16-1': {
        moduleId: 16,
        lessonIndex: 0,
        title: 'Etapa 1 — Acumulación',
        duration: '15 min',
        intro: 'Stan Weinstein, en su libro de 1988 sobre cómo operar en mercados alcistas y bajistas, propuso un modelo de cuatro etapas para clasificar en qué momento de su ciclo de vida se encuentra una acción. La Etapa 1 es el punto de partida — y paradójicamente, donde casi nadie quiere comprar.',
        sections: [
            {
                heading: 'El marco de las 4 etapas',
                blocks: [
                    { type: 'text', content: 'El modelo de Weinstein usa el gráfico semanal y una media móvil de 30 semanas (equivalente aproximado a la MA150 diaria) para clasificar el precio en una de cuatro etapas recurrentes: Acumulación, Avance, Distribución y Declive. Estas etapas se repiten en bucle — tras la Etapa 4 viene de nuevo la Etapa 1, y el ciclo continúa indefinidamente mientras la acción siga cotizando.' },
                    { type: 'chart', id: 'four_stages_overview' },
                    { type: 'concept', title: 'Por qué usar el gráfico semanal', content: 'El diario tiene demasiado ruido para identificar etapas de varios meses de duración. El semanal filtra ese ruido y muestra con claridad si el precio está realmente en rango lateral, en tendencia, o en transición. La MA de 30 semanas actúa como el árbitro: cuando aplana, confirma rango; cuando gira con claridad, confirma tendencia.' },
                ]
            },
            {
                heading: 'Anatomía de la Etapa 1',
                blocks: [
                    { type: 'text', content: 'La Etapa 1 es el rango de cotización horizontal que sigue a un descenso desde la Etapa 4 anterior. El precio se mueve de forma errática, a veces por encima de la media de 30 semanas y a veces por debajo, sin ninguna dirección clara durante semanas o meses.' },
                    { type: 'chart', id: 'stage1_anatomy' },
                    { type: 'table',
                        headers: ['Característica', 'Comportamiento en Etapa 1'],
                        rows: [
                            ['Estructura de precio', 'Rango lateral, sin HH/HL ni LH/LL consistentes'],
                            ['Media de 30 semanas', 'Se aplana, sigue al precio horizontalmente'],
                            ['Relación precio vs media', 'El precio cruza la media en ambas direcciones repetidamente'],
                            ['Volumen', 'Puede aumentar — inversores capitulando tras esperar sin resultado'],
                            ['Duración típica', 'Semanas a varios meses, variable según el activo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Qué está pasando realmente bajo la superficie',
                blocks: [
                    { type: 'text', content: 'La Etapa 1 representa una transición de propiedad. Los vendedores que compraron cerca de máximos en el ciclo anterior y aguantaron toda la caída de la Etapa 4 finalmente capitulan y venden cerca de mínimos, exhaustos. Mientras tanto, compradores con horizonte más largo empiezan a acumular posiciones de forma discreta, sin prisa, aprovechando el rango para construir su posición a buen precio.' },
                    { type: 'chart', id: 'stage1_accumulation_process' },
                    { type: 'concept', title: 'La trampa de operar la Etapa 1', content: 'Es tentador intentar comprar en el "suelo" del rango y vender en el "techo" repetidamente. El problema es que no hay forma de saber, mientras el rango está en curso, si ese es realmente el último rango antes de la ruptura o si seguirá lateral durante meses más. Operar el rango es una estrategia distinta (reversión a la media) y no debe confundirse con la estrategia de tendencia que el modelo de Weinstein busca explotar.' },
                ]
            },
            {
                heading: 'Cómo identificar que sigues en Etapa 1',
                blocks: [
                    { type: 'text', content: 'No existe un indicador único que confirme la Etapa 1 — es una clasificación visual basada en la ausencia de tendencia clara. Sin embargo, hay señales que refuerzan la lectura.' },
                    { type: 'chart', id: 'stage1_identification_signals' },
                    { type: 'steps', items: [
                        'La media de 30 semanas lleva varias semanas sin pendiente clara (ni subiendo ni bajando de forma sostenida)',
                        'El precio ha tocado tanto la parte superior como la inferior del rango al menos dos veces',
                        'No hay una secuencia clara de máximos y mínimos crecientes (eso indicaría ya Etapa 2)',
                        'El activo viene de una caída prolongada (Etapa 4) antes de entrar en este rango',
                    ]},
                    { type: 'tip', label: 'NO ES SEÑAL DE COMPRA TODAVÍA', content: 'La Etapa 1 por sí sola no es una señal de entrada según la metodología de Weinstein — es la fase de espera y observación. La señal de compra llega con la ruptura confirmada hacia la Etapa 2, que se cubre en la siguiente lección.' },
                ]
            },
        ]
    },

    // ── MÓDULO 16, LECCIÓN 2 ───────────────────────────────────────────────
    '16-2': {
        moduleId: 16,
        lessonIndex: 1,
        title: 'Etapa 2 — Avance',
        duration: '15 min',
        intro: 'La Etapa 2 es, según Weinstein, el único momento del ciclo donde se debería comprar. Es la fase de tendencia alcista sostenida donde el precio abandona el rango de la Etapa 1 con fuerza y la media de 30 semanas empieza a confirmar la nueva dirección.',
        sections: [
            {
                heading: 'La ruptura que inicia la Etapa 2',
                blocks: [
                    { type: 'text', content: 'La transición de Etapa 1 a Etapa 2 ocurre cuando el precio rompe por encima de la parte superior del rango de cotización con un volumen notablemente superior al habitual durante el rango. Ese volumen es la huella de la demanda institucional entrando con fuerza — sin él, la ruptura tiene menos credibilidad.' },
                    { type: 'chart', id: 'stage2_breakout' },
                    { type: 'concept', title: 'El throwback inicial', content: 'En la parte temprana de la Etapa 2, es habitual que el precio retroceda al menos una vez hacia la parte superior del antiguo rango de la Etapa 1 (lo que ahora actúa como soporte). Este throwback no invalida la ruptura — es una segunda oportunidad de entrada para quien no compró en la ruptura inicial, siempre que el soporte se mantenga.' },
                ]
            },
            {
                heading: 'Las características que confirman la Etapa 2',
                blocks: [
                    { type: 'text', content: 'No basta con una ruptura aislada. La Etapa 2 verdadera muestra un conjunto de características que la distinguen de una falsa ruptura que termina revirtiendo de vuelta al rango.' },
                    { type: 'chart', id: 'stage2_confirmation_signs' },
                    { type: 'table',
                        headers: ['Señal', 'Cómo se manifiesta en Etapa 2'],
                        rows: [
                            ['Estructura de precio', 'Máximos y mínimos crecientes consistentes (HH y HL)'],
                            ['Media de 30 semanas', 'Gira claramente hacia arriba, queda por debajo del precio'],
                            ['Relación con la media', 'El precio se mantiene sobre la media de forma sostenida'],
                            ['Mínimo "feo" inicial', 'Suele aparecer un patrón de doble suelo poco perfecto justo al iniciar la tendencia'],
                            ['Volumen en avances', 'Tiende a expandirse en los impulsos alcistas'],
                        ]
                    },
                ]
            },
            {
                heading: 'La regla de los mínimos crecientes',
                blocks: [
                    { type: 'text', content: 'La condición más estricta para confirmar que sigues en Etapa 2 — y no en una simple corrección dentro de un rango — es la presencia de mínimos crecientes (Higher Lows). Si el precio hace un nuevo máximo pero luego cae por debajo del mínimo anterior, la estructura de Etapa 2 está en duda.' },
                    { type: 'chart', id: 'stage2_higher_lows_rule' },
                    { type: 'warning', content: 'Si no ves mínimos crecientes con claridad, no es Etapa 2 — independientemente de cuán alcista parezca el movimiento reciente. Esta es la prueba de fuego que Weinstein remarca: sin estructura de HH/HL, no hay verdadera tendencia, solo volatilidad direccional temporal.' },
                ]
            },
            {
                heading: 'Cuándo abandonar la posición dentro de la Etapa 2',
                blocks: [
                    { type: 'text', content: 'Mientras el precio se mantenga por encima de la media de 30 semanas y siga formando mínimos crecientes, la Etapa 2 sigue vigente y la posición se mantiene. La señal de salida (o al menos de alerta) llega cuando el precio cierra de forma sostenida por debajo de esa media.' },
                    { type: 'chart', id: 'stage2_exit_signal' },
                    { type: 'tip', label: 'LA REGLA SIMPLE DE WEINSTEIN', content: 'Si el precio permanece por encima de la media de 30 semanas, mantén la posición. Si cae claramente por debajo, considera tomar beneficios o al menos poner la posición en alerta máxima — probablemente la acción está entrando en Etapa 3.' },
                ]
            },
        ]
    },

    // ── MÓDULO 16, LECCIÓN 3 ───────────────────────────────────────────────
    '16-3': {
        moduleId: 16,
        lessonIndex: 2,
        title: 'Etapa 3 — Distribución',
        duration: '15 min',
        intro: 'La Etapa 3 marca el techo del ciclo. El impulso de la Etapa 2 se agota, el precio vuelve a moverse de forma lateral, y la media de 30 semanas —que venía subiendo con fuerza— empieza a aplanarse hasta que finalmente el precio la atraviesa.',
        sections: [
            {
                heading: 'Cómo se forma la Etapa 3',
                blocks: [
                    { type: 'text', content: 'Tras un avance sostenido en Etapa 2, el precio comienza a perder la capacidad de hacer nuevos máximos con la misma facilidad. Empieza a moverse de nuevo de forma horizontal, formando picos y valles pronunciados mientras intenta —sin éxito sostenido— encontrar una nueva dirección clara.' },
                    { type: 'chart', id: 'stage3_formation' },
                    { type: 'concept', title: 'La media de 30 semanas como árbitro del techo', content: 'Durante la Etapa 2, la media subía con fuerza por debajo del precio. En la Etapa 3, esa media sigue subiendo pero pierde pendiente, aplanándose progresivamente. Finalmente el precio, en su movimiento lateral, la atraviesa — primero brevemente, luego con más convicción. Ese cruce es la señal visual de que el "árbitro" está confirmando el fin del avance.' },
                ]
            },
            {
                heading: 'Qué hacer en la Etapa 3 según el perfil del trader',
                blocks: [
                    { type: 'text', content: 'Weinstein distingue explícitamente entre la respuesta de un trader de corto-medio plazo y la de un inversor con horizonte más largo durante esta fase, porque las prioridades son diferentes.' },
                    { type: 'chart', id: 'stage3_trader_vs_investor' },
                    { type: 'table',
                        headers: ['Perfil', 'Acción recomendada en Etapa 3'],
                        rows: [
                            ['Trader (corto-medio plazo)', 'Tomar beneficios — el motivo principal para mantener la posición (la tendencia) ya no está presente'],
                            ['Inversor (largo plazo)', 'Puede vender la mitad de la posición y mantener el resto a la espera'],
                            ['Si el precio reanuda una nueva Etapa 2', 'Mantener o recomprar la parte vendida — el ciclo de avance continúa'],
                            ['Si hay ruptura bajista del rango', 'Vender el resto sin excepción — la Etapa 4 ha comenzado'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué el volumen no es tan informativo aquí',
                blocks: [
                    { type: 'text', content: 'A diferencia de la Etapa 1 y la Etapa 2, donde el volumen aporta pistas relativamente claras, en la Etapa 3 el volumen puede comportarse de forma ambigua. Puede aumentar mientras el precio se debate lateralmente intentando elegir una nueva dirección, sin que ese aumento por sí solo indique si el resultado final será una continuación alcista o una ruptura bajista.' },
                    { type: 'chart', id: 'stage3_volume_ambiguity' },
                    { type: 'warning', content: 'No intentes usar el volumen como única señal de timing en la Etapa 3. La señal más fiable sigue siendo estructural: ¿el precio rompe el rango hacia arriba (nueva Etapa 2) o hacia abajo (inicio de Etapa 4)? Espera esa confirmación antes de actuar de forma decisiva.' },
                ]
            },
            {
                heading: 'Distinguir la Etapa 3 de un simple pullback en Etapa 2',
                blocks: [
                    { type: 'text', content: 'Un error común es confundir un pullback saludable dentro de una Etapa 2 en curso con el inicio de una Etapa 3. La diferencia clave está en la duración y en si se siguen formando mínimos crecientes.' },
                    { type: 'chart', id: 'stage3_vs_pullback' },
                    { type: 'steps', items: [
                        'Un pullback de Etapa 2 suele ser breve (días a pocas semanas) y respeta la media de 30 semanas como soporte',
                        'La Etapa 3 se extiende durante varias semanas o meses, con el precio cruzando la media repetidamente en ambas direcciones',
                        'En el pullback de Etapa 2, sigue habiendo un mínimo más alto que el anterior — en Etapa 3, esa progresión se rompe',
                        'Si tienes dudas, la prudencia favorece tratar la situación como posible Etapa 3 hasta que el precio confirme lo contrario',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 16, LECCIÓN 4 ───────────────────────────────────────────────
    '16-4': {
        moduleId: 16,
        lessonIndex: 3,
        title: 'Etapa 4 — Declive',
        duration: '15 min',
        intro: 'La Etapa 4 es la fase que todo el modelo de Weinstein está diseñado para ayudarte a evitar. Es el descenso sostenido que sigue a la Etapa 3, y operar — o simplemente mantener una posición — durante esta fase es, según los propios datos de backtesting de la metodología, la decisión menos rentable de las cuatro etapas.',
        sections: [
            {
                heading: 'Cómo se desarrolla la Etapa 4',
                blocks: [
                    { type: 'text', content: 'La Etapa 4 comienza con una ruptura bajista del rango formado durante la Etapa 3. El precio rompe por debajo del soporte de ese rango y, tras un posible retroceso hacia el nivel roto (similar al throwback de la Etapa 2 pero en sentido contrario), continúa descendiendo de forma sostenida.' },
                    { type: 'chart', id: 'stage4_breakdown' },
                    { type: 'concept', title: 'El volumen pierde valor predictivo aquí', content: 'A diferencia de las rupturas alcistas de la Etapa 2, donde el volumen alto es una señal de calidad importante, en las rupturas bajistas de la Etapa 4 el volumen puede ser alto o bajo indistintamente y el precio sigue cayendo en ambos casos. El pánico vendedor no siempre se manifiesta en volumen extremo desde el primer momento — a veces la caída es ordenada y constante, sin clímax de volumen visible.' },
                ]
            },
            {
                heading: 'La posición de la media de 30 semanas',
                blocks: [
                    { type: 'text', content: 'Durante toda la Etapa 4, la media de 30 semanas permanece por encima del precio actuando como resistencia dinámica, justo lo opuesto a su papel de soporte durante la Etapa 2. Cualquier rebote dentro de la Etapa 4 tiende a perder fuerza al acercarse a esa media.' },
                    { type: 'chart', id: 'stage4_ma_resistance' },
                    { type: 'table',
                        headers: ['Etapa', 'Posición de la MA30 respecto al precio', 'Función'],
                        rows: [
                            ['Etapa 2', 'Por debajo, subiendo', 'Soporte dinámico'],
                            ['Etapa 4', 'Por encima, bajando o plana', 'Resistencia dinámica'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué evitar comprar en Etapa 4 (aunque "parezca barato")',
                blocks: [
                    { type: 'text', content: 'La tentación de comprar durante la Etapa 4 surge de la comparación psicológica con precios anteriores más altos — "ha caído tanto que debe ser una ganga". Los datos de backtesting de esta metodología muestran sistemáticamente que comprar en Etapa 4 produce los peores resultados de las cuatro etapas, tanto en rentabilidad media como en porcentaje de operaciones ganadoras.' },
                    { type: 'chart', id: 'stage4_buying_trap' },
                    { type: 'warning', content: 'Un precio que ha caído mucho puede seguir cayendo mucho más — no hay ningún suelo garantizado solo por la magnitud de la caída previa. La pregunta correcta no es "¿cuánto ha caído?" sino "¿ha hecho la transición estructural de Etapa 4 a Etapa 1 (rango) y luego a Etapa 2 (ruptura confirmada)?". Sin esa transición, seguir cayendo sigue siendo la hipótesis de base.' },
                ]
            },
            {
                heading: 'El cierre del ciclo: de la Etapa 4 de vuelta a la Etapa 1',
                blocks: [
                    { type: 'text', content: 'Eventualmente, el descenso de la Etapa 4 pierde fuerza vendedora y el precio empieza de nuevo a moverse de forma lateral — el ciclo se cierra y comienza una nueva Etapa 1. Este es el motivo por el que el modelo de Weinstein se describe como cíclico: cada etapa contiene en sí misma la semilla de la siguiente.' },
                    { type: 'chart', id: 'stage4_to_stage1_cycle' },
                    { type: 'tip', label: 'LA DISCIPLINA DEL MODELO COMPLETO', content: 'El valor real de las 4 etapas no está en ninguna etapa aislada, sino en usarlas juntas como mapa de decisión: comprar preferentemente hacia el final de la Etapa 1 o al inicio confirmado de la Etapa 2, mantener mientras la Etapa 2 siga validada por mínimos crecientes, vender o reducir en la Etapa 3, y evitar por completo nuevas compras durante la Etapa 4. Es un marco simple, pero la disciplina de aplicarlo consistentemente es lo que genera el resultado.' },
                ]
            },
        ]
    },
    // ── MÓDULO 17, LECCIÓN 1 ───────────────────────────────────────────────
    '17-1': {
        moduleId: 17,
        lessonIndex: 0,
        title: 'La Máquina de Descontar',
        duration: '15 min',
        intro: 'El mercado no reacciona a lo que ya pasó — reacciona a lo que espera que pase. Esta diferencia, sutil pero fundamental, es la razón por la que el precio de una acción a menudo se mueve en la dirección "equivocada" justo cuando llega la noticia que todo el mundo estaba esperando.',
        sections: [
            {
                heading: 'El precio como expectativa colectiva',
                blocks: [
                    { type: 'text', content: 'El mercado de valores es, ante todo, un mecanismo de descuento de expectativas futuras. El precio de una acción en cualquier momento no refleja la situación actual de la empresa, sino el consenso colectivo de millones de participantes sobre cómo será su situación en el futuro. Cuando ese futuro esperado se confirma exactamente como se anticipaba, el precio ya se movió antes — no queda sorpresa que mover el precio de nuevo.' },
                    { type: 'chart', id: 'discounting_machine_concept' },
                    { type: 'concept', title: 'Descontar no es predecir con certeza', content: 'Descontar significa incorporar al precio actual la probabilidad ponderada de los distintos resultados futuros posibles, no solo el resultado más probable. Si el mercado asigna un 70% de probabilidad a que una empresa supere expectativas de beneficios, el precio ya sube parcialmente reflejando ese 70% — incluso antes de que el resultado real se publique.' },
                ]
            },
            {
                heading: 'El horizonte de descuento varía según el evento',
                blocks: [
                    { type: 'text', content: 'No todos los eventos se descuentan con la misma anticipación. Algunos eventos programados (como un informe de resultados con fecha conocida) se descuentan progresivamente durante semanas. Otros eventos inesperados (como una adquisición sorpresa) no pueden descontarse — el precio reacciona de golpe cuando ocurren, porque no había forma de anticiparlos.' },
                    { type: 'chart', id: 'discounting_horizon_types' },
                    { type: 'table',
                        headers: ['Tipo de evento', 'Horizonte de descuento', 'Ejemplo'],
                        rows: [
                            ['Programado y predecible', 'Semanas a meses antes', 'Earnings, decisión de tipos de la Fed'],
                            ['Programado pero incierto en resultado', 'Días antes, con incertidumbre alta', 'Resultado de un ensayo clínico con fecha conocida'],
                            ['No programado / sorpresa', 'No se descuenta — reacción inmediata', 'Fusión inesperada, dimisión de un CEO'],
                            ['Tendencial y gradual', 'Continuo, se ajusta constantemente', 'Cambio de hábitos de consumo, adopción tecnológica'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué "todo el mundo lo sabe" ya está en el precio',
                blocks: [
                    { type: 'text', content: 'Una de las trampas mentales más comunes es pensar que una pieza de información que tú conoces te da ventaja. Si esa información es de dominio público —disponible en cualquier medio financiero, accesible a cualquier analista institucional— el mercado ya la ha incorporado al precio antes de que tú actúes sobre ella.' },
                    { type: 'chart', id: 'already_priced_in' },
                    { type: 'warning', content: '"Esta empresa va a tener un trimestre excelente" no es información explotable si esa expectativa ya es el consenso del mercado. La pregunta que realmente importa no es "¿va a ir bien la empresa?" sino "¿va a ir MEJOR de lo que el mercado ya espera?". Esa segunda pregunta es mucho más difícil de responder con ventaja.' },
                ]
            },
            {
                heading: 'Implicaciones prácticas para el trading',
                blocks: [
                    { type: 'text', content: 'Entender el mercado como máquina de descuento cambia fundamentalmente cómo interpretas el movimiento de precio alrededor de eventos conocidos. El movimiento previo al evento es tan informativo —o más— que el movimiento posterior.' },
                    { type: 'chart', id: 'discounting_practical_implications' },
                    { type: 'steps', items: [
                        'Antes de cualquier evento conocido, pregúntate: ¿qué expectativa ya refleja el precio actual?',
                        'Observa el movimiento de las semanas previas al evento — ese movimiento ES la anticipación del mercado',
                        'El resultado real del evento debe compararse contra la expectativa descontada, no contra el resultado en términos absolutos',
                        'Una "buena noticia" puede generar caída de precio si fue menos buena de lo ya descontado',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 17, LECCIÓN 2 ───────────────────────────────────────────────
    '17-2': {
        moduleId: 17,
        lessonIndex: 1,
        title: 'Buy the Rumour',
        duration: '15 min',
        intro: '"Comprar el rumor" describe el patrón donde el precio sube de forma sostenida en las semanas previas a un evento esperado positivo, impulsado por la anticipación colectiva — mucho antes de que ese evento se confirme oficialmente.',
        sections: [
            {
                heading: 'Anatomía del patrón "buy the rumour"',
                blocks: [
                    { type: 'text', content: 'El patrón se desarrolla en una secuencia reconocible: surge una expectativa positiva sobre un evento futuro (un lanzamiento de producto, una aprobación regulatoria, un informe de resultados esperado como fuerte), los participantes informados comienzan a posicionarse con anticipación, y el precio sube de forma gradual a medida que más participantes se suman a esa expectativa.' },
                    { type: 'chart', id: 'buy_rumour_anatomy' },
                    { type: 'concept', title: 'La anticipación se autorrefuerza', content: 'A medida que el precio sube por la anticipación, ese mismo movimiento alcista atrae más atención y más compradores que extrapolan la subida como confirmación de que "algo bueno va a pasar". Este mecanismo de refuerzo puede llevar el precio a niveles que exceden lo que el evento real, por bueno que sea, puede justificar — preparando el terreno para la fase de "sell the news".' },
                ]
            },
            {
                heading: 'Quién compra el rumor primero',
                blocks: [
                    { type: 'text', content: 'No todos los participantes acceden a la misma información al mismo tiempo. Analistas institucionales, fondos especializados y participantes con investigación propia tienden a posicionarse antes de que la expectativa se vuelva de conocimiento generalizado entre el público inversor.' },
                    { type: 'chart', id: 'who_buys_rumour_first' },
                    { type: 'table',
                        headers: ['Fase de la anticipación', 'Quién participa', 'Características del movimiento'],
                        rows: [
                            ['Temprana', 'Analistas especializados, fondos sectoriales', 'Subida lenta, poco volumen, poco notada'],
                            ['Media', 'Medios financieros, traders técnicos', 'Subida más visible, volumen creciente'],
                            ['Tardía', 'Público general, redes sociales', 'Subida acelerada, FOMO, volumen alto'],
                            ['Pico', 'Casi todos posicionados ya', 'Precio extendido, vulnerable a "sell the news"'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cómo identificar que estás en fase de rumor',
                blocks: [
                    { type: 'text', content: 'Reconocer que un movimiento de precio corresponde a la fase de "comprar el rumor" —en lugar de a una tendencia fundamental independiente— ayuda a calibrar expectativas sobre lo que puede ocurrir cuando el evento finalmente se confirme.' },
                    { type: 'chart', id: 'identify_rumour_phase' },
                    { type: 'steps', items: [
                        'Existe un evento conocido y con fecha aproximada en el horizonte cercano (días o semanas)',
                        'El precio sube de forma más marcada que el resto del sector sin un catalizador fundamental ya confirmado',
                        'La narrativa en medios y redes se centra explícitamente en la expectativa del evento próximo',
                        'El volumen y la volatilidad implícita en opciones tienden a aumentar a medida que se acerca la fecha',
                    ]},
                ]
            },
            {
                heading: 'El riesgo de comprar tarde en la fase de rumor',
                blocks: [
                    { type: 'text', content: 'Comprar en la fase tardía de "buy the rumour" —cuando el movimiento ya es ampliamente conocido y comentado— invierte la relación riesgo-recompensa. El precio puede tener ya poco recorrido adicional antes del evento, mientras el riesgo de una reversión brusca tras la confirmación (sea cual sea el resultado) aumenta.' },
                    { type: 'chart', id: 'late_rumour_risk' },
                    { type: 'tip', label: 'LA VENTANA DE OPORTUNIDAD SE CIERRA', content: 'La mejor relación riesgo-recompensa en este patrón está en las fases temprana y media de la anticipación, no en la tardía. Si descubres el "rumor" cuando ya está en todas las portadas financieras, es probable que la mayor parte del movimiento ya haya ocurrido — y el riesgo de quedar atrapado en la reversión post-evento es alto.' },
                ]
            },
        ]
    },

    // ── MÓDULO 17, LECCIÓN 3 ───────────────────────────────────────────────
    '17-3': {
        moduleId: 17,
        lessonIndex: 2,
        title: 'Sell the News',
        duration: '15 min',
        intro: '"Vender la noticia" es el reverso del rumor: el momento en que, paradójicamente, el precio cae justo cuando se confirma la buena noticia que el mercado venía anticipando durante semanas.',
        sections: [
            {
                heading: 'Por qué la confirmación puede generar caída',
                blocks: [
                    { type: 'text', content: 'Cuando el precio ha subido durante semanas anticipando un evento positivo, ese evento ya está mayormente "comprado" — descontado en el precio actual. Si el resultado real coincide exactamente con la expectativa (ni mejor ni peor), no queda sorpresa positiva adicional que justifique más subida. El catalizador que sostenía la compra desaparece, y los participantes que compraron el rumor empiezan a tomar beneficios — generando presión vendedora justo en el momento de "buenas noticias".' },
                    { type: 'chart', id: 'sell_news_mechanism' },
                    { type: 'concept', title: 'La sorpresa relativa, no el resultado absoluto', content: 'Lo que mueve el precio tras un evento no es si el resultado fue bueno o malo en términos absolutos, sino si fue mejor o peor que lo que el mercado ya tenía descontado. Un resultado objetivamente excelente puede generar caída si el mercado esperaba algo aún mejor. Un resultado mediocre puede generar subida si el mercado temía algo mucho peor.' },
                ]
            },
            {
                heading: 'Los tres escenarios posibles al confirmarse el evento',
                blocks: [
                    { type: 'text', content: 'Cuando finalmente llega el evento que el mercado venía anticipando, hay tres desenlaces posibles según cómo el resultado real se compare con la expectativa descontada.' },
                    { type: 'chart', id: 'three_outcome_scenarios' },
                    { type: 'table',
                        headers: ['Escenario', 'Resultado vs expectativa', 'Reacción típica del precio'],
                        rows: [
                            ['Supera lo descontado', 'Mejor de lo que el mercado esperaba', 'Subida adicional — sorpresa positiva real'],
                            ['Cumple lo descontado', 'Exactamente lo esperado', 'Caída o lateral — "sell the news" clásico'],
                            ['No alcanza lo descontado', 'Peor de lo esperado', 'Caída marcada — doble decepción'],
                        ]
                    },
                ]
            },
            {
                heading: 'Distinguir "sell the news" de un cambio de tesis real',
                blocks: [
                    { type: 'text', content: 'No toda caída tras una noticia positiva es simplemente "sell the news" — a veces la caída refleja que el mercado ha encontrado, dentro del propio anuncio, una razón fundamental nueva y real para revisar su tesis a la baja (por ejemplo, guidance débil dentro de un informe de resultados que superó expectativas en la cifra principal).' },
                    { type: 'chart', id: 'sell_news_vs_real_change' },
                    { type: 'warning', content: 'Antes de asumir que una caída post-evento es simplemente la mecánica de "vender la noticia", revisa si hay contenido sustantivo en el anuncio que justifique una revisión real de la tesis a medio plazo (cambio de guidance, comentarios de gestión, cambios estructurales). Si lo hay, no es solo la mecánica de descuento — es información nueva genuina.' },
                ]
            },
            {
                heading: 'Cómo operar alrededor de eventos conocidos',
                blocks: [
                    { type: 'text', content: 'Entender el patrón "buy the rumour, sell the news" no significa necesariamente evitar operar alrededor de eventos — significa calibrar el riesgo y el timing de forma distinta a si el evento no existiera.' },
                    { type: 'chart', id: 'trading_around_known_events' },
                    { type: 'steps', items: [
                        '<strong>Si ya tienes posición desde la fase temprana del rumor:</strong> considera reducir parcialmente antes del evento, asegurando parte de la ganancia ya generada por la anticipación',
                        '<strong>Si consideras entrar justo antes del evento:</strong> evalúa si el R:R sigue siendo favorable una vez el rumor ya está mayormente descontado',
                        '<strong>Si el evento es muy incierto en su resultado:</strong> la volatilidad implícita en opciones suele estar elevada — el coste de protegerse aumenta',
                        '<strong>Tras el evento:</strong> espera a ver si el mercado interpreta el resultado como sorpresa real antes de reaccionar al movimiento inicial, que puede ser ruido de cierre de posiciones',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 17, LECCIÓN 4 ───────────────────────────────────────────────
    '17-4': {
        moduleId: 17,
        lessonIndex: 3,
        title: 'Earnings y Eventos Macro',
        duration: '15 min',
        intro: 'Los informes de resultados trimestrales y las decisiones de política monetaria son los dos tipos de evento programado donde el mecanismo de descuento del mercado se observa con mayor claridad y frecuencia — y donde la disciplina de entender este concepto importa más.',
        sections: [
            {
                heading: 'Earnings: el guidance importa más que el resultado',
                blocks: [
                    { type: 'text', content: 'En los informes de resultados trimestrales, el mercado típicamente ya tiene una estimación de consenso para las cifras principales (beneficio por acción, ingresos). La reacción del precio depende menos del cumplimiento de esa estimación que de las indicaciones que la empresa da sobre el futuro —el guidance— porque el guidance es la parte de la información que aún no estaba completamente descontada.' },
                    { type: 'chart', id: 'earnings_guidance_importance' },
                    { type: 'concept', title: 'Por qué el guidance mueve más el precio', content: 'El resultado del trimestre que ya pasó es información histórica que el mercado ha podido anticipar con razonable precisión usando datos macro, comentarios de la dirección en el trimestre anterior, e indicadores adelantados del sector. El guidance sobre los próximos trimestres es la pieza de información genuinamente nueva — y por tanto la que puede mover el precio de forma más significativa al revisar las expectativas futuras.' },
                ]
            },
            {
                heading: 'La reacción en las horas posteriores al informe',
                blocks: [
                    { type: 'text', content: 'La primera reacción del precio tras la publicación de resultados —especialmente en sesión extendida, antes de que el mercado regular abra— puede ser volátil y no siempre representa la interpretación final que el mercado adoptará una vez analizada toda la información del informe.' },
                    { type: 'chart', id: 'post_earnings_reaction_timeline' },
                    { type: 'table',
                        headers: ['Momento', 'Característica de la reacción'],
                        rows: [
                            ['Primeros minutos (after-hours)', 'Reacción a la cifra principal, alta volatilidad, baja liquidez'],
                            ['Durante la conference call', 'Ajustes según comentarios de gestión sobre guidance y márgenes'],
                            ['Apertura del día siguiente', 'Reacción más informada, mayor liquidez, dirección más consolidada'],
                            ['Días posteriores', 'Revisiones de analistas, puede confirmar o revertir la reacción inicial'],
                        ]
                    },
                ]
            },
            {
                heading: 'Eventos macro: la Fed como caso de estudio',
                blocks: [
                    { type: 'text', content: 'Las decisiones de tipos de interés de la Reserva Federal son quizás el ejemplo más estudiado de mecanismo de descuento en los mercados financieros. El mercado de futuros sobre tipos de interés permite observar, con bastante precisión, qué decisión está descontando el mercado antes de que ocurra.' },
                    { type: 'chart', id: 'fed_decision_discounting' },
                    { type: 'steps', items: [
                        'Antes de cada reunión del FOMC, el mercado de futuros de tipos ya refleja una probabilidad implícita para cada posible decisión',
                        'Si la decisión final coincide con la probabilidad mayoritaria ya descontada, el movimiento de mercado tras el anuncio suele ser moderado',
                        'El verdadero movimiento de mercado en estos eventos a menudo viene del tono de la conferencia posterior (hawkish o dovish), no de la decisión de tipos en sí',
                        'Una decisión "como se esperaba" puede generar fuerte movimiento si el lenguaje usado sorprende respecto a las expectativas sobre el futuro',
                    ]},
                ]
            },
            {
                heading: 'Aplicación práctica: el checklist antes de eventos conocidos',
                blocks: [
                    { type: 'text', content: 'Tanto para earnings como para eventos macro, aplicar conscientemente el concepto de mercado como máquina de descuento se traduce en un conjunto de preguntas concretas que ayudan a evitar las trampas más comunes alrededor de estos eventos.' },
                    { type: 'chart', id: 'pre_event_checklist' },
                    { type: 'tip', label: 'CHECKLIST PRE-EVENTO', content: '¿Qué expectativa de consenso ya refleja el precio actual? ¿Cómo se ha movido el precio en las semanas previas — sugiere optimismo o pesimismo ya incorporado? ¿La volatilidad implícita en opciones está elevada (señal de incertidumbre alta) o normal? Si el resultado coincide exactamente con el consenso, ¿qué movimiento de precio sería razonable esperar? Responder estas preguntas antes del evento, no después, es lo que distingue la disciplina de la reacción impulsiva.' },
                ]
            },
        ]
    },
    // ── MÓDULO 18, LECCIÓN 1 ───────────────────────────────────────────────
    '18-1': {
        moduleId: 18,
        lessonIndex: 0,
        title: 'La Zona de Entrada lo Decide Todo',
        duration: '15 min',
        intro: 'El ratio riesgo/recompensa no es una cifra que se calcula después de elegir un punto de entrada cualquiera — es una consecuencia directa de DÓNDE compras. Comprar en una zona de demanda real y comprar en "tierra de nadie" no son dos variantes del mismo trade: son trades fundamentalmente distintos en su perfil de riesgo, su potencial y su gestión psicológica.',
        sections: [
            {
                heading: 'Tierra de nadie vs zona de demanda',
                blocks: [
                    { type: 'text', content: '"Tierra de nadie" es comprar en mitad de un rango, sin ningún nivel técnico cercano que justifique por qué el precio debería rebotar ahí en lugar de seguir cayendo. Una zona de demanda real es un nivel donde el precio ya mostró antes una reacción compradora clara — un sitio donde, históricamente, la oferta se agotó y la demanda tomó el control de forma visible.' },
                    { type: 'chart', id: 'no_mans_land_vs_demand_zone' },
                    { type: 'concept', title: 'Por qué importa el lugar, no solo el precio', content: 'Dos compras al mismo precio numérico pueden ser trades completamente distintos según el contexto. Comprar a $100 en mitad de un rango sin razón técnica es una apuesta. Comprar a $100 porque ahí está el límite inferior de una zona de demanda con dos toques previos es una decisión informada con una hipótesis clara de por qué el precio podría reaccionar justo ahí.' },
                ]
            },
            {
                heading: 'El stop se ajusta solo cuando compras en buen soporte',
                blocks: [
                    { type: 'text', content: 'Cuando compras justo en el límite de una zona de demanda sólida, el nivel de invalidación de tu idea está naturalmente muy cerca: justo por debajo de esa zona. Si compras en tierra de nadie, no hay ningún nivel natural donde colocar el stop — tienes que inventarlo, casi siempre demasiado lejos por simple prudencia, porque no hay ninguna razón técnica que te diga "aquí se acaba la idea".' },
                    { type: 'chart', id: 'stop_distance_by_entry_quality' },
                    { type: 'table',
                        headers: ['Tipo de entrada', 'Dónde va el stop', 'Distancia típica del stop'],
                        rows: [
                            ['Límite de zona de demanda sólida', 'Justo bajo la zona, nivel técnico claro', 'Ajustada — pocas veces necesitas más del 1-2%'],
                            ['Mitad de zona de demanda amplia', 'Bajo el mínimo de la zona', 'Moderada — depende de la anchura de la zona'],
                            ['Tierra de nadie, sin nivel cercano', 'Inventado por prudencia, sin base técnica', 'Amplia — a menudo el doble o el triple de lo necesario'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué un stop ajustado dispara el R:R',
                blocks: [
                    { type: 'text', content: 'El ratio riesgo/recompensa tiene el riesgo en el denominador. Si compras en buen soporte y tu stop está a un 1.5% de distancia en lugar de a un 4%, el mismo objetivo técnico —la siguiente resistencia relevante— genera un R:R muchísimo más favorable solo por la calidad del punto de entrada, sin cambiar nada del objetivo de salida.' },
                    { type: 'chart', id: 'rr_disparity_same_target' },
                    { type: 'steps', items: [
                        'Mismo objetivo en ambos casos: resistencia a $120',
                        'Entrada en zona de demanda a $100, stop técnico a $98.50 (riesgo 1.5%) → R:R 1:13.3',
                        'Entrada en tierra de nadie a $100, stop forzado a $96 (riesgo 4%) → R:R 1:5',
                        'El objetivo es idéntico — la diferencia completa de R:R viene solo de dónde compraste',
                    ]},
                ]
            },
            {
                heading: 'El potencial de recompensa también mejora',
                blocks: [
                    { type: 'text', content: 'No solo se reduce el riesgo: comprar en una zona de demanda real suele significar comprar más cerca del punto donde empieza el movimiento, lo que deja más recorrido completo hasta la siguiente resistencia. Comprar en tierra de nadie, en mitad de un rango, normalmente significa que ya te has perdido parte del movimiento hacia ese mismo objetivo — capturas menos puntos del mismo viaje.' },
                    { type: 'chart', id: 'more_room_to_target' },
                    { type: 'tip', label: 'EL LUGAR GENERA AMBOS LADOS DE LA ECUACIÓN', content: 'Una buena zona de demanda no solo reduce el riesgo (stop más cerca) — también amplía la recompensa potencial (más distancia hasta el objetivo desde un precio de entrada más bajo dentro del mismo movimiento). El R:R favorable no es una casualidad estadística: es la consecuencia directa de haber elegido bien el lugar donde entras.' },
                ]
            },
        ]
    },

    // ── MÓDULO 18, LECCIÓN 2 ───────────────────────────────────────────────
    '18-2': {
        moduleId: 18,
        lessonIndex: 1,
        title: 'Anatomía de una Buena Zona de Demanda',
        duration: '15 min',
        intro: 'No todas las zonas donde el precio rebotó alguna vez son iguales. Antes de poder usar la calidad de la zona para mejorar tu R:R, necesitas saber distinguir una zona de demanda genuinamente fuerte de una zona débil que parece soporte pero no tiene la convicción real detrás.',
        sections: [
            {
                heading: 'Qué hace fuerte a una zona de demanda',
                blocks: [
                    { type: 'text', content: 'Una zona de demanda fuerte se reconoce por cómo se formó, no solo por su ubicación en el gráfico. La reacción que originó la zona debe mostrar evidencia clara de que la demanda entró con decisión: una vela o serie de velas que revierten con fuerza, idealmente con volumen superior al habitual, dejando un rechazo visualmente nítido del precio inferior.' },
                    { type: 'chart', id: 'strong_demand_zone_anatomy' },
                    { type: 'table',
                        headers: ['Característica', 'Zona fuerte', 'Zona débil'],
                        rows: [
                            ['Velocidad del rechazo', 'Reversión rápida y marcada', 'Reversión lenta, indecisa'],
                            ['Volumen en el rechazo', 'Notablemente superior al promedio', 'Normal o bajo'],
                            ['Número de toques previos', 'Pocos toques (1-2), zona "fresca"', 'Muchos toques — se va debilitando'],
                            ['Contexto de tendencia', 'A favor de la tendencia mayor', 'Contra la tendencia mayor'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué las zonas "frescas" son mejores',
                blocks: [
                    { type: 'text', content: 'Cada vez que el precio toca una zona de demanda y rebota, parte de las órdenes de compra acumuladas en esa zona se ejecutan y se consumen. Una zona que ha sido tocada y respetada muchas veces tiene cada vez menos órdenes pendientes — está, literalmente, agotándose. Una zona fresca, tocada por primera o segunda vez, conserva todo su potencial de demanda intacto.' },
                    { type: 'chart', id: 'fresh_vs_tested_zones' },
                    { type: 'concept', title: 'El agotamiento progresivo de una zona', content: 'Piensa en una zona de demanda como un depósito de órdenes de compra acumuladas mientras el precio estuvo ahí por última vez. La primera vez que el precio regresa, ese depósito está lleno y el rebote suele ser fuerte. La tercera o cuarta vez que regresa, buena parte del depósito ya se gastó en rebotes anteriores, y la zona tiene mucha más probabilidad de romperse en lugar de sostener.' },
                ]
            },
            {
                heading: 'El error de comprar en cualquier "soporte" sin verificar la calidad',
                blocks: [
                    { type: 'text', content: 'No todo lo que parece soporte en un gráfico es una zona de demanda con convicción real. Una simple pausa del precio durante una caída, sin un rechazo claro y sin volumen, puede parecer técnicamente un "soporte" en el sentido de que el precio se detuvo ahí — pero no tiene la calidad necesaria para sostener un trade con buen R:R.' },
                    { type: 'chart', id: 'fake_support_vs_real_demand' },
                    { type: 'warning', content: 'Si la única razón para llamar "soporte" a un nivel es que el precio se detuvo ahí brevemente durante una caída, sin ningún rechazo decisivo ni volumen de confirmación, probablemente no es una zona de demanda real — es solo una pausa dentro de una tendencia bajista que puede romperse en el siguiente intento.' },
                ]
            },
            {
                heading: 'Marcar la zona correctamente: límites, no líneas',
                blocks: [
                    { type: 'text', content: 'Una zona de demanda nunca es una línea exacta de un solo precio — es un rango entre el mínimo de la mecha de rechazo y el cierre del cuerpo de la vela que generó el rebote. Marcar la zona como un rango, no como una línea, evita la trampa de pensar que el precio "rompió el soporte" cuando en realidad solo tocó la parte superior de una zona todavía válida.' },
                    { type: 'chart', id: 'zone_as_range_not_line' },
                    { type: 'steps', items: [
                        'Identifica la vela (o velas) de rechazo más clara dentro de la zona',
                        'El límite inferior de la zona es el mínimo de la mecha de esa vela',
                        'El límite superior de la zona es el cierre del cuerpo de esa misma vela',
                        'El stop va justo por debajo del límite inferior de la zona, no en mitad de ella',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 18, LECCIÓN 3 ───────────────────────────────────────────────
    '18-3': {
        moduleId: 18,
        lessonIndex: 2,
        title: 'El Lado Psicológico del Buen R:R',
        duration: '15 min',
        intro: 'El beneficio de comprar en una zona de demanda sólida con buen R:R no es solo matemático — es psicológico. Operar desde una posición de convicción técnica clara cambia por completo cómo se vive el trade mientras está abierto, y esa diferencia tiene consecuencias prácticas sobre las decisiones que tomas en tiempo real.',
        sections: [
            {
                heading: 'Por qué "tierra de nadie" genera más ansiedad',
                blocks: [
                    { type: 'text', content: 'Cuando compras sin un nivel técnico claro que respalde la decisión, cada movimiento en contra del precio genera dudas: ¿debería haber esperado más? ¿esto es normal o es la señal de que me he equivocado? Sin una zona de referencia clara, no tienes ninguna forma objetiva de responder esa pregunta — todo se convierte en interpretación emocional del momento.' },
                    { type: 'chart', id: 'anxiety_no_mans_land' },
                    { type: 'concept', title: 'La zona de demanda como ancla psicológica', content: 'Cuando compras en el límite de una zona de demanda sólida, tienes una respuesta objetiva preparada de antemano para cualquier movimiento en contra: "mientras el precio no rompa por debajo de la zona, la idea sigue siendo válida". Esa frase, repetible y verificable en el gráfico, sustituye la duda emocional por una regla clara que puedes consultar en cualquier momento del trade.' },
                ]
            },
            {
                heading: 'Comparando la experiencia de ambos trades',
                blocks: [
                    { type: 'text', content: 'El mismo movimiento adverso del precio —por ejemplo, una caída del 2% tras la entrada— se vive de forma completamente distinta según si compraste en una zona de demanda con margen, o en tierra de nadie con un stop ya cerca.' },
                    { type: 'chart', id: 'comparing_trade_experience' },
                    { type: 'table',
                        headers: ['Situación', 'Compra en zona de demanda', 'Compra en tierra de nadie'],
                        rows: [
                            ['Caída del 2% tras entrar', 'Normal, dentro de la zona — no genera duda', 'Roza el stop — genera ansiedad y tentación de moverlo'],
                            ['Decisión durante el trade', 'Objetiva: ¿rompió la zona o no?', 'Subjetiva: ¿aguanto o salgo?'],
                            ['Probabilidad de mover el stop por miedo', 'Baja — hay margen y un nivel claro', 'Alta — el stop está demasiado cerca y sin respaldo técnico'],
                        ]
                    },
                ]
            },
            {
                heading: 'Menos pérdidas potenciales por el simple hecho de la ubicación',
                blocks: [
                    { type: 'text', content: 'Una parte importante de las pérdidas evitables no viene de que el análisis fuera incorrecto, sino de comprar en un punto donde el ruido normal del mercado —los movimientos pequeños sin significado direccional— alcanza el stop antes de que la idea tenga oportunidad de desarrollarse. Comprar en una zona de demanda amplia da espacio para que ese ruido ocurra sin invalidar la operación.' },
                    { type: 'chart', id: 'fewer_losses_from_placement' },
                    { type: 'warning', content: 'Muchas pérdidas que se atribuyen a "mala suerte" o a que "el mercado me sacó por poco" en realidad son consecuencia de haber comprado en un punto sin margen técnico real, donde cualquier fluctuación normal del precio —no necesariamente una señal de que la idea estaba equivocada— resulta suficiente para ejecutar el stop.' },
                ]
            },
            {
                heading: 'La convicción no es arrogancia — es trabajo previo',
                blocks: [
                    { type: 'text', content: 'La confianza que sientes operando desde una buena zona de demanda no viene de la personalidad ni de la actitud — viene del trabajo de identificar correctamente esa zona antes de entrar. Esa es la diferencia entre confianza informada y exceso de confianza: la primera se basa en evidencia técnica verificable en el gráfico, la segunda no.' },
                    { type: 'chart', id: 'conviction_from_preparation' },
                    { type: 'tip', label: 'LA PREPARACIÓN PRECEDE A LA CALMA', content: 'Si notas que un trade te genera ansiedad significativa mientras está en curso, antes de trabajar la "psicología del trading" en abstracto, revisa primero si el origen del problema es simplemente que compraste en un punto sin verdadero respaldo técnico. Muchas veces el problema psicológico tiene una causa estructural muy simple: la calidad del punto de entrada.' },
                ]
            },
        ]
    },

    // ── MÓDULO 18, LECCIÓN 4 ───────────────────────────────────────────────
    '18-4': {
        moduleId: 18,
        lessonIndex: 3,
        title: 'Aplicar el R:R desde la Zona, no desde la Calculadora',
        duration: '15 min',
        intro: 'Entender que la calidad de la zona de entrada determina el R:R cambia el orden completo del proceso de decisión. En lugar de calcular un R:R abstracto y buscar después dónde encaja, el proceso correcto empieza siempre por identificar la mejor zona disponible — el R:R es el resultado de esa elección, no un objetivo independiente.',
        sections: [
            {
                heading: 'El orden correcto del proceso',
                blocks: [
                    { type: 'text', content: 'El proceso que realmente funciona no es "quiero un R:R de 1:3, ¿dónde lo consigo?" sino "esta es la mejor zona de demanda disponible en este activo ahora mismo, ¿qué R:R me ofrece comprar justo en su límite?". El primer enfoque invita a forzar niveles artificiales. El segundo deja que el mercado, a través de su propia estructura, te diga qué R:R es razonable esperar.' },
                    { type: 'chart', id: 'correct_process_order' },
                    { type: 'steps', items: [
                        'Identifica las zonas de demanda relevantes en el activo, evaluando su calidad (frescura, volumen, contexto de tendencia)',
                        'Espera a que el precio llegue al límite de la mejor zona disponible',
                        'Coloca el stop justo por debajo de esa zona — ahí está tu riesgo real, no donde tú decidas arbitrariamente',
                        'Identifica el objetivo técnico (próxima resistencia relevante) — ahí está tu recompensa potencial',
                        'El R:R resultante de esos dos niveles es la información que valida o descarta el trade',
                    ]},
                ]
            },
            {
                heading: 'Cuándo una zona de demanda NO justifica el trade, aunque exista',
                blocks: [
                    { type: 'text', content: 'No toda zona de demanda identificada correctamente lleva automáticamente a un trade válido. Si el objetivo técnico más cercano está demasiado próximo a la zona de entrada, incluso un stop perfectamente ajustado puede no generar suficiente R:R para justificar el riesgo —y forzar el trade igualmente sería repetir el error de operar sin disciplina, solo con mejor análisis previo.' },
                    { type: 'chart', id: 'demand_zone_insufficient_rr' },
                    { type: 'concept', title: 'Buena zona no es sinónimo de buen trade', content: 'Una excelente zona de demanda con una resistencia inmediatamente encima, sin espacio real hasta el siguiente nivel relevante, sigue siendo una zona de demanda de calidad — pero no necesariamente un trade que merezca ejecutarse ahora mismo. La calidad de la zona reduce el riesgo; el espacio hasta el objetivo determina si la recompensa potencial justifica tomarlo.' },
                ]
            },
            {
                heading: 'Comparar varias oportunidades usando este criterio',
                blocks: [
                    { type: 'text', content: 'Cuando varios activos en tu watchlist muestran zonas de demanda simultáneamente, comparar la calidad de cada zona y el espacio disponible hasta el siguiente objetivo te permite priorizar el capital hacia la oportunidad con mejor R:R real, en lugar de operar todas por igual.' },
                    { type: 'chart', id: 'comparing_multiple_opportunities' },
                    { type: 'table',
                        headers: ['Activo', 'Calidad de zona', 'Espacio hasta objetivo', 'R:R resultante'],
                        rows: [
                            ['Activo A', 'Fresca, alto volumen', 'Amplio (resistencia lejana)', 'Muy favorable'],
                            ['Activo B', 'Testeada 3 veces', 'Amplio', 'Moderado — zona ya debilitada'],
                            ['Activo C', 'Fresca, alto volumen', 'Estrecho (resistencia cercana)', 'Insuficiente a pesar de buena zona'],
                        ]
                    },
                ]
            },
            {
                heading: 'El resumen que conecta todo el módulo',
                blocks: [
                    { type: 'text', content: 'El ratio riesgo/recompensa favorable no es un objetivo que se persigue de forma independiente — es el resultado natural de comprar en el lugar correcto. Una zona de demanda de calidad ofrece simultáneamente un stop más ajustado y técnicamente justificado, más recorrido hasta el objetivo, y una experiencia psicológica del trade mucho más manejable mientras está en curso.' },
                    { type: 'chart', id: 'module_summary_connection' },
                    { type: 'tip', label: 'LA PREGUNTA QUE LO RESUME TODO', content: 'Antes de cualquier entrada, en lugar de preguntarte "¿qué R:R tiene este trade?", pregúntate primero "¿estoy comprando en una zona de demanda real y de calidad, o estoy comprando en tierra de nadie?". Si la respuesta es zona de calidad, el buen R:R suele aparecer solo, como consecuencia. Si es tierra de nadie, ningún cálculo posterior de R:R compensará la falta de una base técnica real en el punto de entrada.' },
                ]
            },
        ]
    },
    // ── MÓDULO 19, LECCIÓN 1 ───────────────────────────────────────────────
    '19-1': {
        moduleId: 19,
        lessonIndex: 0,
        title: 'Reversión y Ruptura de Línea de Tendencia',
        duration: '15 min',
        intro: 'La línea de tendencia es probablemente la herramienta de confirmación más usada en price action, y sus dos eventos clave —la ruptura y la reversión posterior— forman una secuencia reconocible que muchos traders usan como señal de entrada o de salida.',
        sections: [
            {
                heading: 'Dos eventos, una secuencia',
                blocks: [
                    { type: 'text', content: 'Sobre una tendencia alcista, se traza una línea conectando los mínimos crecientes que han venido sosteniendo el precio. Mientras esa línea se respeta, la tendencia sigue vigente. La "ruptura de línea de tendencia" ocurre cuando el precio finalmente cierra por debajo de esa línea, señalando que el soporte dinámico que sostenía la subida ha fallado. Tras esa ruptura, si el precio empieza a formar una nueva secuencia de máximos decrecientes, se puede trazar una nueva línea en sentido contrario — eso es la "reversión de línea de tendencia", la confirmación de que el cambio de sesgo tiene continuidad real.' },
                    { type: 'chart', id: 'trendline_break_reversal_sequence' },
                    { type: 'concept', title: 'La ruptura es el aviso, la reversión es la confirmación', content: 'Una ruptura de línea de tendencia por sí sola puede ser ruido — un movimiento que perfora la línea brevemente y luego la recupera. La reversión, en cambio, requiere que se forme una estructura nueva y reconocible en la dirección contraria. Por eso muchos traders esperan a ver ambos eventos en secuencia antes de tratarlo como una señal de entrada fiable.' },
                ]
            },
            {
                heading: 'Cómo se ve en ambos sentidos',
                blocks: [
                    { type: 'text', content: 'El mismo patrón funciona en espejo para una tendencia bajista: la línea de tendencia bajista conecta los máximos decrecientes, y su ruptura al alza —seguida de una nueva línea ascendente conectando mínimos crecientes— es la señal equivalente de cambio de sesgo hacia el lado comprador.' },
                    { type: 'chart', id: 'trendline_both_directions' },
                    { type: 'table',
                        headers: ['Contexto previo', 'Ruptura', 'Reversión que confirma'],
                        rows: [
                            ['Tendencia alcista', 'Cierre por debajo de la línea de soporte dinámico', 'Nueva línea bajista con máximos decrecientes'],
                            ['Tendencia bajista', 'Cierre por encima de la línea de resistencia dinámica', 'Nueva línea alcista con mínimos crecientes'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué no toda ruptura merece confianza inmediata',
                blocks: [
                    { type: 'text', content: 'Una línea de tendencia puede ser perforada brevemente por una mecha sin que eso represente un cambio real de estructura — especialmente si el cierre de la vela vuelve a quedar dentro de la línea. La diferencia entre una ruptura genuina y ruido pasajero suele estar en si el cierre, no solo la mecha, queda claramente al otro lado de la línea.' },
                    { type: 'chart', id: 'wick_vs_close_break' },
                    { type: 'warning', content: 'Reaccionar a cada toque de la línea de tendencia como si fuera una ruptura confirmada lleva a entradas prematuras en lo que termina siendo solo una mecha de rechazo dentro de la tendencia original, no un cambio de sesgo real.' },
                ]
            },
        ]
    },

    // ── MÓDULO 19, LECCIÓN 2 ───────────────────────────────────────────────
    '19-2': {
        moduleId: 19,
        lessonIndex: 1,
        title: 'Soporte y Resistencia como Confirmación',
        duration: '15 min',
        intro: 'Cuando el precio respeta repetidamente los mismos niveles horizontales, esos niveles se convierten en una de las señales de confirmación más directas: comprar cerca del soporte y vender cerca de la resistencia, dentro de un rango bien definido.',
        sections: [
            {
                heading: 'Los niveles horizontales como marco de referencia',
                blocks: [
                    { type: 'text', content: 'Un nivel de resistencia es un techo donde el precio ha encontrado presión vendedora en múltiples ocasiones, evitando que siga subiendo. Un nivel de soporte es un suelo donde el precio ha encontrado presión compradora en múltiples ocasiones, evitando que siga cayendo. Cuantas más veces el precio toca esos niveles y reacciona en la dirección esperada, más fiable se considera el nivel como referencia.' },
                    { type: 'chart', id: 'support_resistance_multiple_touches' },
                    { type: 'concept', title: 'La memoria del mercado', content: 'Los niveles de soporte y resistencia funcionan porque reflejan zonas de precio donde un número significativo de participantes ya tomó decisiones en el pasado — órdenes pendientes, posiciones que se defienden, niveles psicológicos redondos. Esa "memoria" colectiva del mercado es lo que hace que el precio reaccione de forma similar cada vez que vuelve a esos niveles.' },
                ]
            },
            {
                heading: 'Confirmar la entrada en el toque del nivel',
                blocks: [
                    { type: 'text', content: 'La forma más directa de usar soporte y resistencia como confirmación de entrada es esperar a que el precio llegue al nivel y muestre una reacción clara —una vela de rechazo, una pausa con baja presión vendedora cerca del soporte, o el patrón inverso cerca de la resistencia— antes de tomar la posición, en lugar de anticiparse antes de que el precio llegue al nivel.' },
                    { type: 'chart', id: 'confirmation_at_level_touch' },
                    { type: 'steps', items: [
                        'Identifica el nivel con al menos 2-3 toques previos donde el precio reaccionó de forma similar',
                        'Espera a que el precio llegue de nuevo al nivel, sin anticipar la entrada antes de tiempo',
                        'Busca una señal de rechazo en el propio nivel (vela de reversión, pausa del momentum)',
                        'La entrada se confirma con esa reacción, no solo con la proximidad al nivel',
                    ]},
                ]
            },
            {
                heading: 'Qué pasa cuando el nivel finalmente cede',
                blocks: [
                    { type: 'text', content: 'Ningún nivel de soporte o resistencia es permanente. Cuando finalmente se rompe de forma confirmada, ese mismo nivel tiende a invertir su función: una resistencia rota suele actuar después como soporte, y un soporte roto suele actuar después como resistencia. Reconocer este cambio de rol es tan útil como reconocer el nivel mientras estaba vigente.' },
                    { type: 'chart', id: 'level_role_reversal' },
                    { type: 'tip', label: 'EL NIVEL ROTO NO DESAPARECE', content: 'Cuando una resistencia se rompe y el precio retesta esa misma zona desde arriba, ese retest —si el nivel ahora actúa como soporte— suele ofrecer una entrada con mejor relación riesgo/recompensa que perseguir la ruptura inicial.' },
                ]
            },
        ]
    },

    // ── MÓDULO 19, LECCIÓN 3 ───────────────────────────────────────────────
    '19-3': {
        moduleId: 19,
        lessonIndex: 2,
        title: 'Retroceso de Fibonacci',
        duration: '15 min',
        intro: 'Los niveles de retroceso de Fibonacci son una herramienta usada para identificar hasta dónde es razonable esperar que el precio corrija dentro de una tendencia, antes de que esa tendencia continúe en su dirección original.',
        sections: [
            {
                heading: 'Qué mide un retroceso de Fibonacci',
                blocks: [
                    { type: 'text', content: 'Tras un movimiento direccional claro —un impulso desde un mínimo hasta un máximo, por ejemplo— el precio rara vez continúa en línea recta indefinidamente. Suele retroceder una porción de ese movimiento antes de reanudar la tendencia. La herramienta de Fibonacci traza niveles horizontales en proporciones específicas de ese impulso —comúnmente 38%, 50% y 62%— como zonas donde ese retroceso podría detenerse.' },
                    { type: 'chart', id: 'fibonacci_retracement_levels' },
                    { type: 'concept', title: 'Por qué esas proporciones concretas', content: 'Los niveles de Fibonacci provienen de una secuencia matemática que aparece de forma recurrente en patrones naturales. En mercados financieros no existe una razón fundamental que obligue al precio a respetar exactamente esas proporciones — su utilidad viene de que un número suficiente de participantes los observa y actúa en consecuencia, lo que termina generando reacciones de precio reales en esos niveles.' },
                ]
            },
            {
                heading: 'Cómo se traza correctamente',
                blocks: [
                    { type: 'text', content: 'Para una tendencia alcista, la herramienta se traza desde el mínimo significativo hasta el máximo significativo del impulso que se quiere medir. Los niveles resultantes (38%, 50%, 62%) marcan, de arriba hacia abajo, las zonas donde la corrección podría encontrar soporte antes de que la tendencia alcista continúe. Para una tendencia bajista, el proceso es el espejo: se traza desde el máximo hasta el mínimo del impulso bajista.' },
                    { type: 'chart', id: 'fibonacci_correct_drawing' },
                    { type: 'table',
                        headers: ['Nivel', 'Interpretación típica'],
                        rows: [
                            ['38%', 'Retroceso superficial — tendencia muy fuerte, poca corrección'],
                            ['50%', 'Retroceso intermedio — punto de equilibrio entre impulso y corrección'],
                            ['62%', 'Retroceso profundo — última zona razonable antes de cuestionar la tendencia'],
                        ]
                    },
                ]
            },
            {
                heading: 'Usarlo como confirmación, no como predicción aislada',
                blocks: [
                    { type: 'text', content: 'Un nivel de Fibonacci por sí solo es una zona de probabilidad, no una garantía de reacción. Su valor como herramienta de confirmación aumenta considerablemente cuando coincide con otro elemento de contexto ya conocido — un nivel de soporte o resistencia previo, una zona de demanda u oferta, o una vela de rechazo clara justo en ese nivel.' },
                    { type: 'chart', id: 'fibonacci_confluence' },
                    { type: 'warning', content: 'Operar la simple llegada del precio a un nivel de Fibonacci, sin ninguna otra confirmación de contexto, trata una zona de probabilidad como si fuera una señal definitiva — el mismo error que tratar cualquier nivel técnico aislado como suficiente por sí solo.' },
                ]
            },
        ]
    },

    // ── MÓDULO 19, LECCIÓN 4 ───────────────────────────────────────────────
    '19-4': {
        moduleId: 19,
        lessonIndex: 3,
        title: 'Consolidaciones',
        duration: '15 min',
        intro: 'Dentro de una tendencia ya establecida, el precio no sube o baja de forma continua — hace pausas. Esas pausas, cuando tienen una estructura reconocible, se llaman consolidaciones, y su resolución suele confirmar la continuidad de la tendencia previa.',
        sections: [
            {
                heading: 'Qué es una consolidación dentro de una tendencia',
                blocks: [
                    { type: 'text', content: 'Una consolidación es un periodo donde el precio se mueve dentro de un rango ajustado, sin avanzar de forma significativa en ninguna dirección, tras haber completado un tramo claro de la tendencia. A diferencia de un rango amplio que puede preceder a una reversión, una consolidación dentro de tendencia suele ser más breve y más estrecha — una pausa para que el mercado digiera el movimiento reciente antes de continuar.' },
                    { type: 'chart', id: 'consolidation_within_trend' },
                    { type: 'concept', title: 'La pausa que recarga el movimiento', content: 'Las consolidaciones suelen interpretarse como el mercado "tomando aliento" — los participantes que ya están en la tendencia mantienen sus posiciones mientras nuevos participantes deciden si sumarse, sin que ninguno de los dos bandos empuje el precio con fuerza en ninguna dirección durante esa pausa.' },
                ]
            },
            {
                heading: 'Cómo identificar una consolidación de calidad',
                blocks: [
                    { type: 'text', content: 'No todas las pausas dentro de una tendencia son iguales. Una consolidación de calidad muestra un rango progresivamente más estrecho, con velas de cuerpo pequeño y volumen decreciente mientras dura la pausa — señales de que la presión direccional simplemente está en compás de espera, no de que el mercado esté indeciso sobre la dirección general.' },
                    { type: 'chart', id: 'quality_consolidation_signs' },
                    { type: 'table',
                        headers: ['Característica', 'Consolidación de calidad', 'Pausa débil o indecisión'],
                        rows: [
                            ['Rango de precio', 'Progresivamente más estrecho', 'Errático, sin contracción clara'],
                            ['Volumen durante la pausa', 'Decreciente', 'Irregular o en aumento'],
                            ['Duración', 'Relativamente breve frente al impulso previo', 'Se extiende sin resolución clara'],
                        ]
                    },
                ]
            },
            {
                heading: 'La resolución como señal de entrada',
                blocks: [
                    { type: 'text', content: 'La señal de entrada llega cuando el precio sale de la consolidación en la dirección de la tendencia que la precedió, idealmente acompañado de un repunte de volumen que confirme que la pausa ha terminado y la presión direccional original ha retomado el control.' },
                    { type: 'chart', id: 'consolidation_resolution_entry' },
                    { type: 'steps', items: [
                        'Confirma que la consolidación ocurre dentro de una tendencia ya establecida, no en un techo o suelo sin contexto previo',
                        'Observa la contracción progresiva del rango y el volumen decreciente como señales de calidad',
                        'Espera la salida de la consolidación en la dirección de la tendencia original',
                        'Busca un repunte de volumen en la resolución como confirmación adicional',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 19, LECCIÓN 5 ───────────────────────────────────────────────
    '19-5': {
        moduleId: 19,
        lessonIndex: 4,
        title: 'Gaps de Precio',
        duration: '15 min',
        intro: 'Un gap es un salto de precio entre el cierre de una sesión y la apertura de la siguiente, sin que se negocie en el rango intermedio. Según el momento del movimiento en que aparece, un gap cuenta una historia distinta sobre lo que probablemente viene después.',
        sections: [
            {
                heading: 'Tres tipos de gap, tres mensajes distintos',
                blocks: [
                    { type: 'text', content: 'Un gap de ruptura (breakaway gap) aparece al inicio de un movimiento nuevo, normalmente rompiendo una zona de consolidación o un nivel relevante, señalando el comienzo de una tendencia con fuerza. Un gap de continuación (runaway gap) aparece en mitad de una tendencia ya en marcha, confirmando que el movimiento sigue teniendo fuerza direccional genuina. Un gap de agotamiento (exhaustion gap) aparece tras un movimiento ya extendido, y suele señalar que la tendencia está llegando a su fase final antes de una posible reversión.' },
                    { type: 'chart', id: 'three_gap_types' },
                    { type: 'concept', title: 'La posición en el movimiento es la clave', content: 'El mismo evento técnico —un salto de precio sin negociación intermedia— significa cosas opuestas según en qué momento del movimiento aparece. Un gap idéntico en tamaño puede ser el inicio prometedor de una tendencia o la señal de que esa misma tendencia se está quedando sin combustible, dependiendo únicamente de dónde ocurre dentro de la secuencia completa del movimiento.' },
                ]
            },
            {
                heading: 'Cómo diferenciarlos en la práctica',
                blocks: [
                    { type: 'text', content: 'La diferenciación se basa en el contexto que rodea al gap, no en el gap aislado. Un gap de ruptura aparece tras una fase de consolidación o lateralidad previa. Un gap de continuación aparece cuando la tendencia ya lleva un tramo recorrido y sigue mostrando estructura saludable. Un gap de agotamiento aparece tras una extensión ya considerable del movimiento, a menudo acompañado de señales adicionales de sobrecompra o sobreventa.' },
                    { type: 'chart', id: 'gap_context_identification' },
                    { type: 'table',
                        headers: ['Tipo de gap', 'Dónde aparece', 'Lo que sugiere'],
                        rows: [
                            ['Ruptura (BG)', 'Al salir de una consolidación', 'Inicio de tendencia con fuerza'],
                            ['Continuación (RG)', 'En mitad de una tendencia ya activa', 'La tendencia mantiene su fuerza'],
                            ['Agotamiento (EG)', 'Tras un movimiento ya extendido', 'Posible fase final antes de reversión'],
                        ]
                    },
                ]
            },
            {
                heading: 'El comportamiento posterior al gap como confirmación',
                blocks: [
                    { type: 'text', content: 'Más allá de clasificar el tipo de gap, observar si se rellena rápidamente o si el precio se aleja de él sin volver añade una capa adicional de confirmación. Un gap de ruptura o de continuación que no se rellena en las sesiones siguientes refuerza la idea de que el movimiento tiene convicción real. Un gap de agotamiento que se rellena rápidamente refuerza la idea de que el movimiento se está quedando sin fuerza.' },
                    { type: 'chart', id: 'gap_fill_behavior' },
                    { type: 'tip', label: 'EL CONTEXTO MANDA SOBRE LA ETIQUETA', content: 'Clasificar correctamente un gap importa menos que entender por qué se produjo. Un gap solo aporta valor como señal de confirmación cuando se interpreta junto con la fase del movimiento en la que aparece, no como un evento aislado y autoexplicativo.' },
                ]
            },
        ]
    },

    // ── MÓDULO 19, LECCIÓN 6 ───────────────────────────────────────────────
    '19-6': {
        moduleId: 19,
        lessonIndex: 5,
        title: 'Volumen Clímax y Tendencia',
        duration: '15 min',
        intro: 'El volumen acompaña al precio contando una parte de la historia que el precio solo no puede contar: cuánta convicción real hay detrás de un movimiento. Distinguir entre volumen de tendencia y volumen clímax es clave para confirmar si un movimiento tiene fuerza genuina o está llegando a su límite.',
        sections: [
            {
                heading: 'Volumen de tendencia: la confirmación saludable',
                blocks: [
                    { type: 'text', content: 'El volumen de tendencia (volume trend) es el patrón donde el volumen aumenta de forma gradual y sostenida en la dirección del movimiento principal — más participación a medida que el precio avanza, sin picos desproporcionados en una sola sesión. Este patrón confirma que el movimiento tiene respaldo genuino y creciente, no solo impulso pasajero.' },
                    { type: 'chart', id: 'volume_trend_pattern' },
                    { type: 'concept', title: 'Participación creciente, no explosiva', content: 'Un volumen de tendencia saludable no necesita ser espectacular en ninguna sesión individual — lo relevante es la tendencia del propio volumen, que debería ir aumentando de forma consistente en la dirección del precio a medida que más participantes se suman al movimiento.' },
                ]
            },
            {
                heading: 'Volumen clímax: el extremo que suele agotar el movimiento',
                blocks: [
                    { type: 'text', content: 'Un volumen clímax (volume climax) es un pico de volumen extremo y repentino, muy por encima de lo habitual, que típicamente aparece tras un movimiento ya extendido. Representa el punto donde la participación alcanza su máximo —a menudo el momento en que los últimos participantes rezagados finalmente se suman al movimiento— y suele coincidir con el agotamiento de esa tendencia, no con su continuación.' },
                    { type: 'chart', id: 'volume_climax_pattern' },
                    { type: 'table',
                        headers: ['Patrón de volumen', 'Qué señala', 'Momento típico'],
                        rows: [
                            ['Volume Trend (VT)', 'Movimiento con respaldo creciente y saludable', 'Durante el desarrollo de la tendencia'],
                            ['Volume Climax (VC)', 'Posible agotamiento, últimos compradores/vendedores entrando', 'Tras una extensión ya considerable'],
                        ]
                    },
                ]
            },
            {
                heading: 'Cómo se alternan ambos patrones en un movimiento completo',
                blocks: [
                    { type: 'text', content: 'En un movimiento de mercado típico, es común observar una alternancia: volumen de tendencia que confirma cada nuevo tramo del movimiento, interrumpido ocasionalmente por picos de volumen clímax que señalan pausas o correcciones, antes de que el volumen de tendencia se reanude si el movimiento de fondo continúa.' },
                    { type: 'chart', id: 'vt_vc_alternation' },
                    { type: 'steps', items: [
                        'Durante el desarrollo normal de la tendencia, espera ver volumen de tendencia creciendo de forma gradual',
                        'Un pico de volumen clímax tras una extensión ya notable es una señal de alerta, no de confirmación de continuidad',
                        'Tras un volumen clímax, observa si el precio consolida o retrocede — eso valida la lectura de agotamiento',
                        'Si el volumen de tendencia se reanuda tras la pausa, el movimiento de fondo probablemente continúa',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 20, LECCIÓN 1 ───────────────────────────────────────────────
    '20-1': {
        moduleId: 20,
        lessonIndex: 0,
        title: 'Qué Mide el RSU Score',
        duration: '12 min',
        intro: 'El RSU Score es un número de 0 a 100 que resume cinco factores fundamentales y de sentimiento de mercado en una sola cifra. No es una recomendación de compra automática — es un punto de partida rápido para decidir si un ticker merece que profundices.',
        sections: [
            {
                heading: 'Los cinco factores, 20 puntos cada uno',
                blocks: [
                    { type: 'text', content: 'El RSU Score reparte 100 puntos en cinco bloques iguales de 20 puntos. Cada bloque se puntúa de forma independiente y solo suma si hay dato disponible — si falta un dato (por ejemplo, no hay consenso de analistas para un ticker poco cubierto), ese bloque simplemente no aporta puntos ni resta.' },
                    { type: 'chart', id: 'rsu_score_breakdown' },
                    { type: 'table', headers: ['Factor', 'Máx', 'Umbral 20 pts', 'Umbral 15 pts', 'Umbral 10 pts'], rows: [
                        ['Crecimiento de Ingresos', '20', '> 25%', '> 15%', '> 5%'],
                        ['ROE', '20', '> 25%', '> 15%', '> 8%'],
                        ['Margen Neto', '20', '> 20%', '> 10%', '> 2%'],
                        ['Consenso de Analistas', '20', '≥ 75% alcistas', '≥ 60% alcistas', '≥ 40% alcistas'],
                        ['Potencial P. Objetivo', '20', '> 25% upside', '> 15% upside', '> 5% upside'],
                    ]},
                    { type: 'tip', label: 'IMPORTANTE', content: 'Es un sistema de escalones, no una fórmula continua. Un ROE del 24,9% puntúa igual que uno del 15,1% (15 puntos) — quedarse justo debajo de un umbral tiene más impacto en el score que una mejora de varios puntos dentro del mismo escalón.' },
                ]
            },
            {
                heading: 'Las cinco etiquetas',
                blocks: [
                    { type: 'text', content: 'El score final se traduce en una etiqueta y un color que ves de un vistazo en la cabecera de Research.' },
                    { type: 'chart', id: 'rsu_score_labels' },
                    { type: 'table', headers: ['Score', 'Etiqueta', 'Color'], rows: [
                        ['≥ 80', 'COMPRA FUERTE', 'Verde acento'],
                        ['65–79', 'COMPRA', 'Verde acento'],
                        ['50–64', 'NEUTRAL', 'Ámbar'],
                        ['35–49', 'PRECAUCIÓN', 'Rojo'],
                        ['< 35', 'EVITAR', 'Rojo'],
                    ]},
                    { type: 'warning', content: 'El color (verde/ámbar/rojo) cambia en el umbral de 70 y 50 puntos, mientras que la etiqueta de texto cambia en 80/65/50/35. Entre 65 y 69 verás la etiqueta "COMPRA" en color ámbar, no verde — no es un error, son dos escalas independientes dentro del mismo componente.' },
                ]
            },
            {
                heading: 'Qué NO mide el RSU Score',
                blocks: [
                    { type: 'concept', title: 'Un score fundamental + sentimiento, no técnico', content: 'Los cinco factores del RSU Score son puramente fundamentales (crecimiento, rentabilidad) y de sentimiento de mercado (analistas, precio objetivo). No incluye ningún elemento de estructura de precio, volumen, fase de Weinstein ni momentum — para eso está la sección de Niveles Técnicos aparte, en la misma página de Research.' },
                    { type: 'text', content: 'Un ticker puede tener un RSU Score de 85 (fundamentales excelentes, analistas muy alcistas) y estar técnicamente en Fase 4 de Weinstein — es decir, en clara tendencia bajista. El score te dice "la empresa es de calidad y el consenso es optimista", no "es buen momento de comprar ahora mismo".' },
                    { type: 'tip', label: 'REGLA RSU', content: 'Usa el RSU Score para filtrar candidatos (elegir QUÉ mirar), y la estructura técnica — EMAs, fase de Weinstein, soporte/resistencia — para decidir CUÁNDO entrar. Nunca al revés.' },
                ]
            },
        ]
    },

    // ── MÓDULO 20, LECCIÓN 2 ───────────────────────────────────────────────
    '20-2': {
        moduleId: 20,
        lessonIndex: 1,
        title: 'Piotroski F-Score — Salud Financiera',
        duration: '13 min',
        intro: 'El Piotroski F-Score es un indicador independiente del RSU Score. Mide la salud financiera de una empresa comparando el último ejercicio contable con el anterior, a través de 9 criterios binarios. Cuantos más criterios cumple, más sólida es la base contable del negocio.',
        sections: [
            {
                heading: 'Los 9 criterios',
                blocks: [
                    { type: 'text', content: 'Cada criterio suma 1 punto si se cumple, 0 si no se cumple. El score va de 0 a 9. Se agrupan en tres bloques: rentabilidad, apalancamiento/liquidez, y eficiencia operativa.' },
                    { type: 'chart', id: 'piotroski_criteria' },
                    { type: 'table', headers: ['Bloque', 'Criterio', 'Pasa si...'], rows: [
                        ['Rentabilidad', 'ROA positivo', 'Beneficio neto / Activos totales > 0'],
                        ['Rentabilidad', 'CFO positivo', 'Flujo de caja operativo > 0'],
                        ['Rentabilidad', 'ROA en mejora', 'ROA de este año > ROA del año anterior'],
                        ['Rentabilidad', 'Calidad del beneficio', 'CFO > Beneficio neto (el beneficio se traduce en caja real)'],
                        ['Apalancamiento', 'Deuda LP estable o baja', 'Deuda LP / Activos no ha subido vs. año anterior'],
                        ['Apalancamiento', 'Liquidez mejora', 'Current Ratio (activo circulante / pasivo circulante) sube'],
                        ['Apalancamiento', 'Sin dilución', 'El número de acciones en circulación no ha aumentado'],
                        ['Eficiencia', 'Margen bruto mejora', 'Margen bruto de este año > año anterior'],
                        ['Eficiencia', 'Rotación de activos mejora', 'Ingresos / Activos totales sube vs. año anterior'],
                    ]},
                ]
            },
            {
                heading: 'Las cuatro etiquetas y el caso "sin dato"',
                blocks: [
                    { type: 'chart', id: 'piotroski_scale' },
                    { type: 'table', headers: ['Score', 'Etiqueta'], rows: [
                        ['≥ 8', 'EXCELENTE'],
                        ['6–7', 'SÓLIDO'],
                        ['4–5', 'NEUTRAL'],
                        ['< 4', 'DÉBIL'],
                    ]},
                    { type: 'warning', content: 'Cuando yfinance no reporta una línea contable concreta para un ticker (pasa sobre todo con financieras, REITs o empresas extranjeras), ese criterio se muestra con un guion gris "–" en vez de una X roja. Es una diferencia deliberada: el guion significa "no lo sabemos", la X significa "lo sabemos y no pasa el criterio". No confundas un dato ausente con una mala noticia — pero recuerda que igualmente NO suma el punto.' },
                ]
            },
            {
                heading: 'RSU Score y Piotroski son independientes',
                blocks: [
                    { type: 'text', content: 'Es el error de lectura más común: pensar que el Piotroski F-Score forma parte del cálculo del RSU Score. No es así en la versión actual de la terminal — son dos tarjetas separadas en la página de Research, cada una con su propia escala (0-100 vs 0-9) y su propia lógica. Se complementan, pero no se combinan en un único número.' },
                    { type: 'concept', title: 'Por qué mirar los dos', content: 'El RSU Score te dice si el mercado y los fundamentales recientes son favorables ahora mismo. El Piotroski te dice si esos fundamentales están construidos sobre una base contable sólida — caja real, sin dilución, sin apalancamiento creciente. Una empresa con RSU Score alto pero Piotroski bajo (4 o menos) puede estar creciendo a base de deuda o de beneficio contable que no se traduce en caja: vale la pena investigar antes de confiar solo en el primer número.' },
                    { type: 'tip', label: 'LECTURA CONJUNTA', content: 'RSU Score alto + Piotroski alto = fundamentales fuertes y confirmados por la contabilidad. RSU Score alto + Piotroski bajo = revisa antes de comprar, puede haber ruido de corto plazo (recompra de acciones, evento puntual) tapando un deterioro de fondo.' },
                ]
            },
        ]
    },

    // ── MÓDULO 20, LECCIÓN 3 ───────────────────────────────────────────────
    '20-3': {
        moduleId: 20,
        lessonIndex: 2,
        title: 'Comparativa Sectorial — Valorar en Contexto',
        duration: '12 min',
        intro: 'Un P/E de 30 no significa lo mismo en un valor tecnológico de alto crecimiento que en una utility regulada. La sección de métricas de Research compara cada múltiplo con la mediana del sector para que sepas si lo que ves es caro, barato o normal dentro de su categoría.',
        sections: [
            {
                heading: 'Qué métricas se comparan',
                blocks: [
                    { type: 'text', content: 'La comparativa sectorial calcula la mediana del sector para cada métrica y marca si el ticker está en mejor o peor posición ("favorable"). Se aplica a valoración, rentabilidad y crecimiento — no a todas las métricas de la tarjeta, algunas como el Current Ratio o el Free Cash Flow se muestran sin comparación sectorial.' },
                    { type: 'chart', id: 'sector_comparison_example' },
                    { type: 'table', headers: ['Bloque', 'Métricas con comparativa sectorial'], rows: [
                        ['Valoración', 'P/E Trailing, P/E Forward, P/S, EV/EBITDA, PEG, P/B'],
                        ['Rentabilidad', 'ROE, ROA, Margen Neto, Margen Operativo, Margen Bruto, D/E Ratio'],
                        ['Crecimiento', 'Revenue Growth, Earnings Growth'],
                    ]},
                ]
            },
            {
                heading: 'Cómo leer "favorable"',
                blocks: [
                    { type: 'text', content: 'Para métricas de valoración (P/E, EV/EBITDA, P/S, P/B, PEG), "favorable" significa que el múltiplo del ticker está por debajo de la mediana del sector — es decir, cotiza más barato en relación a sus comparables. Para métricas de rentabilidad y crecimiento, "favorable" significa lo contrario: por encima de la mediana es mejor.' },
                    { type: 'warning', content: 'Barato relativo al sector no es lo mismo que barato en términos absolutos. Un sector entero puede estar sobrevalorado tras un rally — en ese caso, "favorable" solo te dice que destaca dentro de un grupo caro, no que sea una ganga objetiva.' },
                    { type: 'concept', title: 'Por qué el PEG es especialmente sensible al sector', content: 'El PEG (P/E dividido entre el crecimiento de beneficios) es la métrica más directamente ligada a la filosofía CAN SLIM: paga un múltiplo alto solo si el crecimiento lo justifica. Comparar el PEG contra la mediana sectorial evita el error clásico de descartar una empresa por P/E alto cuando en realidad crece mucho más rápido que sus comparables.' },
                ]
            },
            {
                heading: 'Los límites de la comparativa',
                blocks: [
                    { type: 'text', content: 'La comparativa depende de una clasificación sectorial correcta (dato de yfinance) y de que existan suficientes comparables con datos completos. En sectores poco poblados o con clasificaciones ambiguas (conglomerados, empresas de nicho), la mediana puede estar calculada sobre pocos tickers y ser menos representativa.' },
                    { type: 'steps', items: [
                        'Mira primero el múltiplo absoluto — ¿tiene sentido para el tipo de negocio?',
                        'Después mira la comparativa sectorial — ¿está caro o barato relativo a sus pares?',
                        'Cruza con el crecimiento — un múltiplo alto con crecimiento acelerado no es lo mismo que un múltiplo alto sin crecimiento',
                        'Si el sector tiene pocos comparables, dale menos peso a la comparativa y más al análisis absoluto',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 20, LECCIÓN 4 ───────────────────────────────────────────────
    '20-4': {
        moduleId: 20,
        lessonIndex: 3,
        title: 'Cómo Leer Todo Junto',
        duration: '13 min',
        intro: 'El poder de la página de Research no está en un solo número, sino en cruzar varias fuentes independientes: RSU Score, Piotroski, comparativa sectorial, insiders e institucionales. Esta lección propone un flujo de lectura ordenado.',
        sections: [
            {
                heading: 'El flujo de lectura recomendado',
                blocks: [
                    { type: 'chart', id: 'research_workflow' },
                    { type: 'steps', items: [
                        '<strong>RSU Score:</strong> ¿Es COMPRA/COMPRA FUERTE? Si es PRECAUCIÓN/EVITAR, entiende primero qué factor concreto lo está lastrando (mira el desglose de los 5 bloques).',
                        '<strong>Piotroski F-Score:</strong> ¿Confirma la solidez contable? Presta especial atención a la calidad del beneficio (CFO vs. Beneficio Neto) y a la dilución.',
                        '<strong>Comparativa sectorial:</strong> ¿El precio actual es razonable frente a sus comparables, o ya recoge todo lo bueno?',
                        '<strong>Insiders:</strong> ¿Hay compras discrecionales recientes (código P) o solo movimiento rutinario (A/M/F/G/C)?',
                        '<strong>Institucional:</strong> ¿El % en manos institucionales es alto y estable, o hay señales de rotación reciente?',
                        '<strong>Estructura técnica:</strong> solo al final, decide el timing de entrada con EMAs, fase de Weinstein y soporte/resistencia — nunca antes que los pasos anteriores.',
                    ]},
                ]
            },
            {
                heading: 'Combinaciones que merecen atención extra',
                blocks: [
                    { type: 'table', headers: ['RSU Score', 'Piotroski', 'Lectura'], rows: [
                        ['Alto (≥65)', 'Alto (≥6)', 'Fundamentales fuertes y confirmados — el escenario más limpio'],
                        ['Alto (≥65)', 'Bajo (<4)', 'Revisa calidad del beneficio y dilución antes de confiar en el score'],
                        ['Bajo (<50)', 'Alto (≥6)', 'Empresa sólida pero quizás cara o con sentimiento de analistas débil — posible candidata de valor, no de momentum'],
                        ['Bajo (<50)', 'Bajo (<4)', 'Sin argumento fundamental — exige una tesis técnica o de catalizador muy fuerte para justificar el trade'],
                    ]},
                    { type: 'warning', content: 'Ningún cruce de scores sustituye la gestión de riesgo. Incluso el escenario "más limpio" (score alto + Piotroski alto) necesita una entrada técnica válida y un stop definido — la calidad fundamental reduce el riesgo de tesis, no el riesgo de timing.' },
                ]
            },
            {
                heading: 'Errores comunes al usar estos indicadores',
                blocks: [
                    { type: 'text', content: 'El error más frecuente es tratar el RSU Score como una señal binaria de compra/venta, ignorando el desglose. El segundo más frecuente es olvidar que Piotroski compara solo dos ejercicios — una empresa que tuvo un año excepcionalmente malo hace dos ejercicios puede mostrar "mejoras" en varios criterios simplemente por el efecto base, sin que el negocio esté realmente mejorando de forma estructural.' },
                    { type: 'tip', label: 'BUENA PRÁCTICA', content: 'Revisa el histórico de varios trimestres antes de operar solo con el snapshot actual del score. Un score puntual es una fotografía; la tendencia de varios trimestres es la película, y la película es lo que realmente importa.' },
                ]
            },
        ]
    },

    // ── MÓDULO 21, LECCIÓN 1 ───────────────────────────────────────────────
    '21-1': {
        moduleId: 21,
        lessonIndex: 0,
        title: 'Ingresos, Márgenes y Beneficio',
        duration: '14 min',
        intro: 'Antes de mirar cualquier múltiplo de valoración, hay que entender si el negocio genera más ingresos, y si esos ingresos se traducen en beneficio real. Esta lección cubre la lectura del estado de resultados trimestral tal y como aparece en Research.',
        sections: [
            {
                heading: 'Las cuatro líneas clave del estado de resultados',
                blocks: [
                    { type: 'text', content: 'El gráfico trimestral de Research muestra cuatro magnitudes en cascada: Ingresos (Revenue), Beneficio Bruto (Gross Profit), Beneficio Operativo (Operating Income) y Beneficio Neto (Net Income). Cada una resta un bloque de costes distinto a la anterior, y la distancia entre ellas te dice dónde se está comiendo el margen.' },
                    { type: 'chart', id: 'income_statement_quarters' },
                    { type: 'table', headers: ['Línea', 'Qué resta respecto a la anterior', 'Qué revela'], rows: [
                        ['Ingresos', '—', 'Demanda del producto/servicio, crecimiento top-line'],
                        ['Beneficio Bruto', 'Coste de los bienes vendidos (COGS)', 'Poder de fijación de precios, eficiencia productiva'],
                        ['Beneficio Operativo', 'Gastos operativos (I+D, marketing, admin)', 'Disciplina de gasto, escalabilidad del modelo'],
                        ['Beneficio Neto', 'Intereses, impuestos, partidas extraordinarias', 'Resultado final atribuible al accionista'],
                    ]},
                ]
            },
            {
                heading: 'La escalera de márgenes',
                blocks: [
                    { type: 'chart', id: 'margin_ladder' },
                    { type: 'concept', title: 'Por qué comparar márgenes trimestre a trimestre', content: 'El crecimiento de ingresos por sí solo puede ser engañoso: una empresa puede crecer en ventas mientras pierde margen (vendiendo con descuentos agresivos, por ejemplo). Comparar el margen bruto y el margen operativo entre trimestres del mismo negocio revela si ese crecimiento es sano o se está comprando a costa de rentabilidad.' },
                    { type: 'tip', label: 'PATRÓN CAN SLIM', content: 'La metodología CAN SLIM busca aceleración: no solo que los ingresos crezcan, sino que la tasa de crecimiento del trimestre actual sea mayor que la de trimestres anteriores. Compara al menos 3-4 trimestres del gráfico, no solo el último dato.' },
                ]
            },
            {
                heading: 'Señales de alerta en el estado de resultados',
                blocks: [
                    { type: 'steps', items: [
                        'Ingresos crecen pero el Beneficio Bruto se queda plano o cae → problema de márgenes, presión de costes o precios',
                        'Beneficio Operativo cae mientras el Beneficio Bruto sube → gasto operativo descontrolado, falta de disciplina',
                        'Beneficio Neto muy distinto del Operativo de forma recurrente → revisa partidas extraordinarias, puede estar maquillando el resultado real del negocio',
                        'Un solo trimestre malo tras varios buenos no invalida la tesis — un patrón de 2-3 trimestres consecutivos sí merece revisión',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 21, LECCIÓN 2 ───────────────────────────────────────────────
    '21-2': {
        moduleId: 21,
        lessonIndex: 1,
        title: 'Rentabilidad y Eficiencia — ROE, ROA',
        duration: '13 min',
        intro: 'Los ratios de rentabilidad miden cuánto beneficio genera una empresa por cada unidad de capital o de activos empleados. Son la base cuantitativa detrás del bloque de "Rentabilidad" tanto del RSU Score como de la tarjeta de métricas de Research.',
        sections: [
            {
                heading: 'ROE, ROA y márgenes: qué mide cada uno',
                blocks: [
                    { type: 'table', headers: ['Métrica', 'Fórmula', 'Qué responde'], rows: [
                        ['ROE', 'Beneficio Neto / Patrimonio Neto', '¿Cuánto gana la empresa con el dinero de los accionistas?'],
                        ['ROA', 'Beneficio Neto / Activos Totales', '¿Cuánto gana la empresa con TODOS sus activos, con deuda incluida?'],
                        ['Margen Neto', 'Beneficio Neto / Ingresos', '¿Qué porcentaje de cada venta se convierte en beneficio final?'],
                        ['Margen Operativo', 'Beneficio Operativo / Ingresos', 'Rentabilidad del negocio "core", antes de intereses e impuestos'],
                        ['Margen Bruto', 'Beneficio Bruto / Ingresos', 'Poder de fijación de precios frente al coste directo del producto'],
                    ]},
                    { type: 'warning', content: 'Un ROE muy alto puede ser señal de excelencia operativa — o simplemente de mucho apalancamiento (poca deuda propia, mucha deuda financiera). Un ROE de 40% con un D/E Ratio muy elevado no es comparable a un ROE de 40% con balance conservador. Mira siempre el ROE junto al D/E Ratio.' },
                ]
            },
            {
                heading: 'D/E Ratio y Current Ratio: la salud del balance',
                blocks: [
                    { type: 'text', content: 'El D/E Ratio (deuda sobre patrimonio) y el Current Ratio (activo circulante sobre pasivo circulante) no entran en el cálculo del RSU Score, pero son la base de dos de los nueve criterios del Piotroski F-Score (apalancamiento estable y liquidez en mejora) — conecta lo aprendido en el módulo anterior con estas métricas.' },
                    { type: 'steps', items: [
                        'D/E Ratio alto y creciente + ROE alto: la rentabilidad puede depender del apalancamiento, no de la eficiencia del negocio',
                        'Current Ratio por debajo de 1: la empresa podría tener dificultades para cubrir sus obligaciones a corto plazo con sus activos líquidos',
                        'Current Ratio muy por encima de 2-3 de forma sostenida: puede indicar capital ocioso mal empleado, no siempre es positivo',
                    ]},
                ]
            },
            {
                heading: 'Free Cash Flow: el filtro de calidad final',
                blocks: [
                    { type: 'text', content: 'El Free Cash Flow (caja libre) es la caja que genera el negocio después de cubrir sus necesidades de inversión (capex). Es el mismo principio que el criterio de "calidad del beneficio" del Piotroski (CFO > Beneficio Neto): un beneficio contable positivo no vale lo mismo si no se traduce en caja disponible real para la empresa.' },
                    { type: 'concept', title: 'Por qué el FCF importa para el trader, no solo para el inversor', content: 'Una empresa con FCF positivo y creciente tiene más margen para recomprar acciones, pagar dividendo, reducir deuda o financiar crecimiento sin diluir a los accionistas actuales — todo eso son catalizadores potenciales de precio a medio plazo que un trader técnico puede anticipar si sabe leer este dato.' },
                ]
            },
        ]
    },

    // ── MÓDULO 21, LECCIÓN 3 ───────────────────────────────────────────────
    '21-3': {
        moduleId: 21,
        lessonIndex: 2,
        title: 'Valoración — P/E, PEG, EV/EBITDA, P/S, P/B',
        duration: '14 min',
        intro: 'Cada múltiplo de valoración responde una pregunta distinta y es más o menos útil según el tipo de negocio. Usar el múltiplo equivocado para el tipo de empresa equivocado es una de las fuentes más comunes de error en análisis fundamental.',
        sections: [
            {
                heading: 'Los cinco múltiplos de la tarjeta de Valoración',
                blocks: [
                    { type: 'chart', id: 'valuation_multiples_context' },
                    { type: 'table', headers: ['Múltiplo', 'Fórmula', 'Mejor para...'], rows: [
                        ['P/E Trailing', 'Precio / BPA (últimos 12 meses)', 'Empresas maduras y rentables con beneficios estables'],
                        ['P/E Forward', 'Precio / BPA estimado (próximos 12 meses)', 'Incorporar expectativas de crecimiento futuro'],
                        ['PEG', 'P/E / Tasa de crecimiento de beneficios', 'Comparar crecimiento vs. precio pagado — clave en CAN SLIM'],
                        ['EV/EBITDA', 'Valor de Empresa / EBITDA', 'Comparar empresas con distinta estructura de deuda'],
                        ['P/S', 'Precio / Ventas por acción', 'Empresas de alto crecimiento aún sin beneficio positivo'],
                        ['P/B', 'Precio / Valor Contable por acción', 'Bancos, aseguradoras y negocios intensivos en activos'],
                    ]},
                ]
            },
            {
                heading: 'Por qué el PEG es el más relevante para la filosofía CAN SLIM',
                blocks: [
                    { type: 'text', content: 'Un PEG de 1 significa, de forma simplificada, que estás pagando un P/E igual a la tasa de crecimiento de beneficios esperada. Un PEG por debajo de 1 sugiere que el mercado no está pagando toda la prima que el crecimiento futuro justificaría; por encima de 1-1.5, el precio ya descuenta buena parte de las expectativas.' },
                    { type: 'warning', content: 'El PEG depende de una estimación de crecimiento futuro, que es una proyección, no un hecho. Un PEG bajo basado en estimaciones de crecimiento poco realistas puede parecer una ganga y no serlo. Cruza siempre el PEG con el histórico real de Revenue Growth y Earnings Growth del gráfico trimestral.' },
                ]
            },
            {
                heading: 'P/S y P/B: cuándo usarlos en vez del P/E',
                blocks: [
                    { type: 'steps', items: [
                        'Si la empresa tiene Beneficio Neto negativo o muy volátil, el P/E no es útil — usa P/S para valorar el negocio en función de sus ventas',
                        'En sectores intensivos en activos físicos (banca, industria pesada, inmobiliario), el P/B es más relevante porque el valor contable refleja mejor el negocio subyacente',
                        'El EV/EBITDA es preferible al P/E cuando comparas empresas con niveles de deuda muy distintos, porque el Valor de Empresa incluye la deuda neta y el EBITDA elimina el efecto de la estructura de capital',
                    ]},
                    { type: 'tip', label: 'REGLA PRÁCTICA', content: 'Nunca valores usando un único múltiplo aislado. Usa la comparativa sectorial (Módulo 20, Lección 3) para saber si ese múltiplo concreto es caro o barato dentro de su categoría, y cruza al menos dos múltiplos distintos antes de sacar una conclusión.' },
                ]
            },
        ]
    },

    // ── MÓDULO 21, LECCIÓN 4 ───────────────────────────────────────────────
    '21-4': {
        moduleId: 21,
        lessonIndex: 3,
        title: 'Catalizadores — Earnings, Insiders, Institucionales',
        duration: '14 min',
        intro: 'Los fundamentales dicen si una empresa es de calidad. Los catalizadores dicen cuándo el mercado puede reconocer esa calidad. Esta lección cubre las señales de Research que anticipan movimiento: earnings, insiders, institucionales y corto interés.',
        sections: [
            {
                heading: 'Earnings: el catalizador más predecible',
                blocks: [
                    { type: 'chart', id: 'earnings_catalysts_timeline' },
                    { type: 'text', content: 'Research muestra la fecha del próximo earnings y el histórico trimestral de BPA (EPS). Un patrón de sorpresas positivas consecutivas (BPA real por encima del estimado) suele preceder revisiones al alza de las estimaciones de analistas — que a su vez pueden mover el precio incluso sin que el ticker esté "barato" en términos de múltiplos.' },
                    { type: 'warning', content: 'La volatilidad implícita sube antes de earnings y el resultado es binario: puede sorprender bien o mal. Si operas alrededor de earnings, reduce el tamaño de posición o ajusta el stop — no trates ese día como una sesión normal.' },
                ]
            },
            {
                heading: 'Insiders: quién compra con su propio dinero',
                blocks: [
                    { type: 'text', content: 'La sección de Insiders de Research clasifica cada transacción por su código de Formulario 4 de la SEC. Solo los códigos P (compra discrecional en mercado abierto) y S (venta discrecional) son señales de convicción real — el resto (A, M, F, G, C) son movimientos rutinarios de compensación que no reflejan una decisión activa del insider sobre el precio actual.' },
                    { type: 'table', headers: ['Código', 'Naturaleza', 'Señal'], rows: [
                        ['P', 'Compra discrecional en mercado abierto', 'Señal de confianza — el insider paga con su dinero'],
                        ['S', 'Venta discrecional en mercado abierto', 'Posible cautela — aunque también puede ser diversificación personal'],
                        ['A / M / F / G / C', 'Concesión, ejercicio de opciones, impuestos, donación, conversión', 'Rutinaria — ignora estas para señales de trading'],
                    ]},
                    { type: 'tip', label: 'CONTEXTO IMPORTA', content: 'Una sola compra P de un directivo menor pesa menos que varias compras P de distintos insiders (especialmente el CEO o CFO) en un periodo corto. Busca clusters de compras, no eventos aislados.' },
                ]
            },
            {
                heading: 'Institucionales y corto interés',
                blocks: [
                    { type: 'text', content: 'El % en manos institucionales y el desglose de holders muestran quién posee el float, pero recuerda la limitación estructural: todos los 13F reportan al mismo cierre de trimestre, por lo que la comparación de precio de referencia se hace contra ese cierre trimestral, no contra el precio individual al que compró cada institución.' },
                    { type: 'text', content: 'El corto interés, cuando es elevado en relación al volumen medio, añade combustible potencial a un movimiento alcista fuerte (cobertura forzada de cortos). No es una señal por sí sola, pero combinada con una ruptura técnica válida y buen volumen, amplifica el escenario.' },
                    { type: 'steps', items: [
                        'Earnings próximos + patrón de sorpresas positivas → catalizador de calendario conocido',
                        'Cluster de compras insider código P → catalizador de convicción interna',
                        '% institucional alto y estable + corto interés elevado → catalizador de posicionamiento técnico',
                        'Ningún catalizador presente → los fundamentales pueden ser correctos pero el timing es incierto, sé más paciente con el tamaño de entrada',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 22, LECCIÓN 1 ───────────────────────────────────────────────
    '22-1': {
        moduleId: 22,
        lessonIndex: 0,
        title: 'Los Tres Pilares del Triángulo',
        duration: '12 min',
        intro: 'Un setup técnico perfecto, por sí solo, no es una razón suficiente para entrar. Tampoco lo es un flujo de opciones agresivo, ni un posicionamiento institucional favorable. El Triángulo RSU es el marco que exige que las tres señales — flujo de opciones, posicionamiento y técnica — apunten en la misma dirección antes de tratar una operación como de alta convicción.',
        sections: [
            {
                heading: 'Tres señales, tres orígenes distintos',
                blocks: [
                    { type: 'text', content: 'Cada pilar del Triángulo viene de una fuente de información completamente independiente de las otras dos. El <strong>flujo de opciones</strong> (Options Flow) muestra dónde está entrando dinero grande ahora mismo. El <strong>posicionamiento</strong> (Research: institucionales, insiders, corto interés) muestra quién ya tiene la posición construida. La <strong>técnica</strong> muestra si el precio está realmente en condiciones de moverse. Ninguna de las tres deriva de las otras — por eso, cuando coinciden, la coincidencia en sí misma es información.' },
                    { type: 'chart', id: 'triangle_three_pillars' },
                    { type: 'concept', title: 'Por qué la independencia importa', content: 'Si tres fuentes de datos que no se calculan entre sí llegan a la misma conclusión de forma independiente, la probabilidad de que sea ruido baja considerablemente. Es el mismo principio que usar tres testigos distintos en lugar de uno solo.' },
                ]
            },
            {
                heading: 'La escala de confianza: 1, 2 o 3 señales',
                blocks: [
                    { type: 'text', content: 'El Triángulo no es binario. No hace falta esperar a que las tres señales estén siempre presentes para hacer algo — pero el número de señales alineadas debe determinar directamente el tamaño de la posición.' },
                    { type: 'chart', id: 'triangle_confidence_scale' },
                    { type: 'table',
                        headers: ['Señales alineadas', 'Interpretación', 'Acción'],
                        rows: [
                            ['1 de 3', 'Puede ser ruido o casualidad', 'No operar — o, como mucho, vigilar en watchlist'],
                            ['2 de 3', 'Sesgo razonable, falta confirmación', 'Tamaño reducido, stop ajustado'],
                            ['3 de 3', 'Confluencia real — el Triángulo se ha formado', 'Tamaño completo dentro de tu plan de riesgo'],
                        ]
                    },
                ]
            },
            {
                heading: 'Por qué cada pilar, en solitario, puede fallar',
                blocks: [
                    { type: 'concept', title: 'El flujo de opciones puede equivocarse', content: 'Una operación institucional grande no es infalible — puede ser una cobertura, no una apuesta direccional, o simplemente una gestora equivocándose. El tamaño de la operación no garantiza que tenga razón.' },
                    { type: 'concept', title: 'El posicionamiento cambia rápido', content: 'Un insider que compró hace un mes o una institución que reportó hace un trimestre no dicen nada sobre lo que piensan hoy. El posicionamiento es una fotografía, no un vídeo en directo.' },
                    { type: 'concept', title: 'La técnica sin apoyo de flujo o posicionamiento es solo probabilidad', content: 'Un breakout puede ser real o puede ser una trampa de liquidez. Sin nada más que lo respalde, estás apostando a que el patrón se cumpla — sin saber si hay dinero grande detrás empujando en la misma dirección.' },
                ]
            },
            {
                heading: 'El Triángulo no es una garantía',
                blocks: [
                    { type: 'text', content: 'Ninguna combinación de señales es inmune a un evento de mercado inesperado: una decisión de la Fed, un titular geopolítico, una rebaja de guidance. El Triángulo RSU mejora la probabilidad, no la garantiza.' },
                    { type: 'warning', content: 'Un Triángulo RSU perfecto, con las tres señales alineadas, puede fallar igual si sobreviene una noticia que cambia el contexto de golpe. Por eso el tamaño de posición y el stop loss siguen siendo obligatorios incluso en el setup de mayor convicción.' },
                    { type: 'tip', label: 'REGLA DEL TRIÁNGULO', content: 'Cuenta cuántos de los tres pilares están realmente presentes antes de entrar — no los que crees que "probablemente" están. Si solo tienes uno, es una apuesta. Con dos, es una posición pequeña. Con tres, es donde el Triángulo RSU realmente actúa.' },
                ]
            },
        ]
    },

    // ── MÓDULO 22, LECCIÓN 2 ───────────────────────────────────────────────
    '22-2': {
        moduleId: 22,
        lessonIndex: 1,
        title: 'Order Flow — La Huella del Dinero Grande',
        duration: '13 min',
        intro: 'No podemos ver quién está detrás de una operación de opciones de gran tamaño — si es un insider, una gestora institucional o simplemente una cuenta con mucho capital. Pero sí podemos ver qué apuesta se está haciendo, con cuánto dinero, y si se repite. Esta lección explica cómo leer esa huella en Options Flow.',
        sections: [
            {
                heading: 'Qué es el order flow y qué NO es',
                blocks: [
                    { type: 'text', content: 'El order flow institucional es el rastro que dejan las operaciones de gran tamaño en el mercado de opciones: bloques (block trades) y barridos (sweeps) que superan claramente el volumen habitual de ese contrato. No es una señal de compra automática — es información sobre dónde se está posicionando dinero grande, que tú interpretas dentro del resto del Triángulo.' },
                    { type: 'concept', title: 'No sabemos quién es, sabemos qué apuesta', content: 'Puede ser un insider con información, una gestora con research propio, o simplemente un trader con mucho capital y suerte. Da igual: si la operación es lo bastante grande y se repite en el tiempo, merece tu atención como una de las tres señales del Triángulo.' },
                ]
            },
            {
                heading: 'Cómo leerlo en RSU Options Flow',
                blocks: [
                    { type: 'chart', id: 'order_flow_signal_reading' },
                    { type: 'table',
                        headers: ['Campo', 'Qué mide', 'Por qué importa'],
                        rows: [
                            ['Prima total', 'Dinero real puesto en juego en la operación', 'Una prima de $500K pesa más que una de $8K'],
                            ['Vol/OI', 'Volumen del día frente al interés abierto previo', 'Un ratio alto indica posición nueva, no roll de una existente'],
                            ['Bloque / Sweep', 'Cómo se ejecutó la orden', 'El sweep (barrido de varios exchanges a la vez) sugiere urgencia por entrar'],
                            ['Score / Señal', 'Puntuación agregada que calcula RSU Terminal', 'Resume automáticamente el conjunto de factores anteriores'],
                        ]
                    },
                ]
            },
            {
                heading: 'Tamaño y consistencia: los dos filtros de calidad',
                blocks: [
                    { type: 'text', content: 'Dos operaciones grandes distintas no valen lo mismo. Una prima de $2M en un ticker de mega-capitalización con opciones muy líquidas es normal; la misma prima en un ticker pequeño y poco operado es una señal mucho más fuerte, porque representa un porcentaje mayor del volumen habitual de ese nombre.' },
                    { type: 'chart', id: 'order_flow_consistency_days' },
                    { type: 'tip', label: 'LA MEJOR SEÑAL', content: 'Order flow alcista que se repite durante varios días seguidos, en el mismo ticker y en la misma dirección, es mucho más fiable que una operación aislada por grande que sea. La repetición descarta la casualidad.' },
                ]
            },
            {
                heading: 'Las trampas del order flow',
                blocks: [
                    { type: 'text', content: 'No toda operación grande es direccional. Una parte del order flow institucional es cobertura (hedging) de una posición ya existente en acciones, no una apuesta nueva. Y una sola operación, sin repetición ni respaldo técnico, puede ser simplemente ruido.' },
                    { type: 'warning', content: 'No entres solo porque veas una operación grande en Options Flow. Es un pilar del Triángulo, no el Triángulo completo. Sin técnica que lo respalde y sin señal de posicionamiento adicional, sigue siendo una apuesta de un solo factor.' },
                ]
            },
        ]
    },

    // ── MÓDULO 22, LECCIÓN 3 ───────────────────────────────────────────────
    '22-3': {
        moduleId: 22,
        lessonIndex: 2,
        title: 'Posicionamiento — Qué Apuesta el Mercado',
        duration: '13 min',
        intro: 'Si el order flow es la señal de "quién está entrando ahora", el posicionamiento es la señal de "quién ya está dentro". RSU construye esta lectura combinando tres fuentes de Research que ya conoces del Módulo 21: institucionales, insiders y corto interés — leídas aquí en conjunto, como un solo pilar del Triángulo.',
        sections: [
            {
                heading: 'Tres ventanas al posicionamiento',
                blocks: [
                    { type: 'chart', id: 'positioning_three_signals' },
                    { type: 'concept', title: 'Titularidad institucional', content: 'El % del float en manos institucionales y su evolución trimestral (13F) indican si las gestoras están construyendo o reduciendo posición. Recuerda la limitación: todos los 13F comparten el mismo cierre de trimestre, así que es una fotografía trimestral, no en tiempo real.' },
                    { type: 'concept', title: 'Transacciones de insiders', content: 'Los códigos P (compra) y S (venta) del Formulario 4, especialmente en clusters de varios insiders comprando en un periodo corto, son la señal de convicción más directa: alguien con información interna arriesga su propio dinero.' },
                    { type: 'concept', title: 'Corto interés y squeeze gauge', content: 'Un corto interés elevado no es, por sí solo, ni alcista ni bajista — pero combinado con una ruptura técnica real, añade combustible potencial vía cobertura forzada de posiciones cortas.' },
                ]
            },
            {
                heading: 'Leer el conjunto, no una sola pieza',
                blocks: [
                    { type: 'text', content: 'El pilar de posicionamiento no se confirma con una sola de las tres fuentes — se confirma cuando varias apuntan en la misma dirección. Un cluster de compras insider, junto con un % institucional estable o en aumento, y un corto interés que añade presión potencial de cobertura, forman una lectura de posicionamiento mucho más sólida que cualquiera de los tres factores por separado.' },
                    { type: 'table',
                        headers: ['Combinación', 'Lectura'],
                        rows: [
                            ['Insiders comprando + institucional al alza', 'Posicionamiento alcista fuerte'],
                            ['Insiders comprando + institucional plano', 'Posicionamiento alcista moderado'],
                            ['Sin actividad insider + institucional a la baja', 'Posicionamiento débil — no cuenta como pilar confirmado'],
                            ['Corto interés alto + resto neutro', 'Solo combustible potencial, no es señal de posicionamiento en sí misma'],
                        ]
                    },
                ]
            },
            {
                heading: 'El posicionamiento es dinámico',
                blocks: [
                    { type: 'text', content: 'Una lectura de posicionamiento bullish puede deteriorarse con rapidez: una rebaja de guidance, el rechazo de un nivel técnico clave, o simplemente una corrección del mercado general pueden cambiar el apetito institucional en cuestión de días.' },
                    { type: 'chart', id: 'positioning_dynamic_warning' },
                    { type: 'warning', content: 'No confíes en una lectura de posicionamiento de hace semanas. Antes de entrar, vuelve a comprobar los tres componentes — insiders, institucionales y corto interés — para confirmar que la fotografía sigue siendo la misma que cuando la detectaste.' },
                ]
            },
            {
                heading: 'Checklist rápido de posicionamiento',
                blocks: [
                    { type: 'steps', items: [
                        '¿Hay cluster de compras insider código P en las últimas semanas?',
                        '¿El % institucional se mantiene estable o sube en el último trimestre reportado?',
                        '¿El corto interés es elevado en relación al volumen medio (combustible potencial)?',
                        '¿Volviste a comprobar estos tres puntos justo antes de entrar, no hace días?',
                    ]},
                ]
            },
        ]
    },

    // ── MÓDULO 22, LECCIÓN 4 ───────────────────────────────────────────────
    '22-4': {
        moduleId: 22,
        lessonIndex: 3,
        title: 'El Checklist de Confluencia',
        duration: '12 min',
        intro: 'Ya conoces los tres pilares por separado. Esta lección los une en un proceso repetible: en qué orden buscarlos, cómo confirmar que realmente están alineados, y cómo conectar el Triángulo RSU con el resto de tu proceso de trading — planificación, R:R y confirmación de entrada.',
        sections: [
            {
                heading: 'El orden de búsqueda recomendado',
                blocks: [
                    { type: 'text', content: 'De los tres pilares, el order flow notable es el más escaso — no aparece todos los días en todos los tickers. Por eso es el punto de partida más eficiente: en lugar de revisar la técnica de cientos de tickers uno a uno, empiezas por donde ya hay dinero grande moviéndose.' },
                    { type: 'chart', id: 'triangle_workflow_order' },
                    { type: 'steps', items: [
                        '<strong>1. Escanea Options Flow</strong> en busca de operaciones grandes y consistentes → crea una lista corta de candidatos',
                        '<strong>2. Revisa la técnica</strong> de cada candidato — no hace falta que ya haya roto, basta con que se esté formando un setup claro',
                        '<strong>3. Comprueba el posicionamiento</strong> en Research — insiders, institucionales, corto interés',
                        '<strong>4. Espera la confirmación técnica</strong> — el cierre de vela que valida la ruptura, no la mecha',
                        '<strong>5. Entra con tu plan</strong> — R:R definido, stop calculado, tamaño según cuántos pilares están realmente alineados',
                    ]},
                ]
            },
            {
                heading: 'Ejemplo ilustrativo',
                blocks: [
                    { type: 'text', content: 'Imagina un ticker que llevas semanas vigilando por una resistencia horizontal clara, testeada varias veces sin romperse. Un día detectas en Options Flow una compra de calls fuera de dinero por varios cientos de miles de dólares, ejecutada como sweep — señal de urgencia. Revisas Research: hay una compra insider código P reciente y el % institucional ha subido en el último trimestre. Tienes order flow y posicionamiento alineados; solo falta la técnica.' },
                    { type: 'text', content: 'Unos días después, el precio cierra por encima de la resistencia con volumen por encima de la media. Ahí se completa el Triángulo: las tres señales, de fuentes independientes, apuntan en la misma dirección. Ese es el momento de ejecutar el plan — no antes, con la técnica aún sin confirmar.' },
                ]
            },
            {
                heading: 'Conecta con el resto de tu proceso',
                blocks: [
                    { type: 'text', content: 'El Triángulo RSU no sustituye el resto de la metodología — la precede. Una vez confirmado, sigues necesitando todo lo que ya viste en módulos anteriores: un ratio riesgo/recompensa mínimo de 1:2 (Módulo 18), un método de confirmación de entrada válido (Módulo 19), y un plan de trade con entrada, stop y tamaño definidos antes de pulsar el botón (Módulo 11).' },
                    { type: 'concept', title: 'El Triángulo filtra el "qué"; tu proceso decide el "cómo"', content: 'El Triángulo te dice si un ticker merece tu atención de alta convicción. El resto de tu proceso — gestión del riesgo, R:R, plan de trade — sigue decidiendo cómo ejecutas esa idea. Uno no sustituye al otro.' },
                ]
            },
            {
                heading: 'Regla final',
                blocks: [
                    { type: 'tip', label: 'RESUMEN DEL TRIÁNGULO RSU', content: 'Sin las tres señales alineadas — order flow, posicionamiento y técnica confirmada — no hay Triángulo RSU. Con dos, tamaño reducido. Con una sola, ni se considera. Y ni siquiera con las tres presentes dejes de aplicar tu gestión del riesgo: el Triángulo mejora la probabilidad, nunca la garantiza.' },
                ]
            },
        ]
    },
};