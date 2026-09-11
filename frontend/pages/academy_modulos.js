// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — Módulos, fases y lecciones de cada módulo
//
// Aparte de academy.js para que el Dashboard (tarjeta «sigue donde lo
// dejaste») recorra los módulos en el MISMO orden que enseña Academy, sin
// cargar la página entera ni copiar la lista.
// ─────────────────────────────────────────────────────────────────────────────

import { LESSON_INDEX } from '/pages/academy_manifest.js';

// ── DATOS DE MÓDULOS ─────────────────────────────────────────────────────────

export const MODULES = [
    { id:0,  title:'RSU Terminal',                icon:'🖥️', description:'Entiende qué es RSU Terminal, la metodología detrás y cómo sacar el máximo partido a cada herramienta.' },
    { id:1,  title:'Configuración de Gráficos',   icon:'📊', description:'Configura correctamente tus gráficos en múltiples temporalidades. El análisis top-down empieza aquí.' },
    { id:2,  title:'Estructura de Mercado',        icon:'🏗️', description:'Identifica la tendencia antes de operar. Máximos y mínimos crecientes o decrecientes lo dicen todo.' },
    { id:3,  title:'Análisis de Tendencia',        icon:'📈', description:'Nunca luches contra el mercado. Aprende a identificar y operar a favor de la tendencia dominante.' },
    { id:4,  title:'Soporte y Resistencia',        icon:'🧱', description:'Los niveles fuertes controlan el precio. Aprende a marcar zonas que realmente importan.' },
    { id:5,  title:'Oferta y Demanda',             icon:'⚖️', description:'Las instituciones actúan en estas zonas. Aprende a identificar dónde el dinero inteligente opera.' },
    { id:6,  title:'Comportamiento de Velas',      icon:'🕯️', description:'El cierre de la vela revela la verdad. Las formaciones de velas cuentan la historia del mercado.' },
    { id:7,  title:'Rupturas de Precio',           icon:'💥', description:'Confirma si es real o una trampa. Las rupturas falsas son la fuente de pérdidas más común.' },
    { id:8,  title:'Análisis de Volumen',          icon:'📦', description:'El volumen confirma el precio. Sin volumen, el movimiento no tiene convicción real.' },
    { id:9,  title:'Patrones de Gráfico',          icon:'🔷', description:'Los patrones solo funcionan con contexto. Aprende a leerlos dentro de la tendencia dominante.' },
    { id:10, title:'Alineación Multi-Temporalidad',icon:'🔭', description:'La alineación crea potencia. Cuando mensual, semanal y diario coinciden, la probabilidad dispara.' },
    { id:11, title:'Planificación del Trade',      icon:'📋', description:'Sin plan no hay trading. Define entrada, stop y objetivo antes de pulsar el botón.' },
    { id:12, title:'Gestión del Riesgo',           icon:'🛡️', description:'Sobrevive primero, gana después. La gestión del riesgo es lo único que te mantiene en el juego.' },
    { id:13, title:'Ejecución',                    icon:'⚡', description:'La disciplina es el edge. Espera confirmación, sigue el plan y sal sin ego.' },
    { id:14, title:'Trampas del Mercado',          icon:'⚠️', description:'El mercado cobra matrícula. Aprende a reconocer las trampas más comunes antes de caer en ellas.' },
    { id:15, title:'Revisión Post-Trade',          icon:'📓', description:'Journal o repite el dolor. La revisión sistemática es lo que separa a los traders rentables.' },
    { id:16, title:'Las 4 Etapas (Weinstein)',     icon:'🔄', description:'Acumulación, avance, distribución y declive. El mapa de ciclo de vida que dice cuándo comprar y cuándo no.' },
    { id:17, title:'El Mercado Descuenta Información', icon:'⏳', description:'Por qué el precio se mueve ANTES de la noticia. Buy the rumour, sell the news — y cómo no quedar atrapado en el lado equivocado.' },
    { id:18, title:'Risk/Reward',                  icon:'⚖️', description:'No es una cifra que se calcula — es el resultado de dónde compras. Una buena zona de demanda mejora el riesgo, la recompensa y la psicología a la vez.' },
    { id:19, title:'Métodos de Confirmación de Entrada', icon:'🎯', description:'6 técnicas para confirmar que una entrada tiene base real: trendlines, soporte/resistencia, Fibonacci, consolidaciones, gaps y volumen.' },
    { id:20, title:'RSU Score Explicado',        icon:'🧮', description:'Qué mide realmente el RSU Score, cómo se calcula el Piotroski F-Score, y por qué son dos indicadores independientes que hay que leer juntos, no como un semáforo ciego.' },
    { id:21, title:'Análisis Fundamental',       icon:'📐', description:'La base fundamental detrás de CAN SLIM: cómo leer estados financieros, rentabilidad, valoración con múltiplos y los catalizadores que mueven el precio.' },
    { id:22, title:'El Triángulo RSU',           icon:'🔺', description:'Cuando el flujo de opciones, el posicionamiento institucional y la técnica se alinean, la probabilidad de una operación ganadora se dispara. La metodología de confluencia de tres señales.' },
    { id:23, title:'Convicción a Largo Plazo',   icon:'🏔️', description:'Por qué a veces merece la pena pagar una prima de valoración por una posición estratégica en un tema de crecimiento secular — y cómo no confundir convicción con negación cuando la tesis se rompe.' },
    { id:24, title:'Volatilidad, el VIX y la Oportunidad', icon:'🌪️', description:'La volatilidad no es lo mismo que perder capital de forma permanente. Qué mide el VIX de verdad, por qué los picos extremos de miedo han sido históricamente zonas interesantes — y por qué desconfiar de cualquier tabla de rendimientos "hipotéticos".' },
    { id:25, title:'Construir una Posición con DCA', icon:'🧱', description:'Promediar coste con aportaciones fijas no es lo mismo que escalar una posición en una caída — y confundirlas es un error caro, sobre todo en instrumentos apalancados. Cómo construir cualquiera de las dos con criterio, no a ciegas.' },
    { id:26, title:'RSU Algoritmo — El Semáforo de Suelos', icon:'🚦', description:'Manual completo del semáforo: qué mide cada uno de sus cinco factores, por qué hay una condición obligatoria que no se puede saltar, cómo se entra por tramos y sin stop, y qué ha hecho de verdad en las 16 señales de los últimos 18 años — incluidos los plazos en los que no aporta nada.' },
    { id:27, title:'La Cartera RSU',              icon:'💼', description:'Por qué la cartera está compuesta así y cómo se lee su pantalla: el reparto en cuatro bloques (de los que esta página muestra dos), la tesis de las cinco tendencias que sostienen la parte de acciones, por qué se paga una prima de valoración y se cobra en volatilidad, los niveles CORE/HIGH/LOTTERY que fijan el tamaño antes de comprar, y qué significa cada cifra de la pantalla — incluido lo que la Cartera no hace.' },
    { id:28, title:'CANSLIM — El Buscador de Valores', icon:'🔎', description:'Manual del buscador: qué significa cada una de las siete letras y qué te dice cuando falla, cómo se lee la tabla —incluida la trampa de fijarse solo en la puntuación—, qué añade el análisis individual, y una rutina de uso con los tres errores que este tipo de herramienta invita a cometer.' },
    { id:29, title:'RS/RW — La Fuerza Relativa',   icon:'📊', description:'Manual de la fuerza relativa: por qué «ha subido» no dice nada sin el mercado al lado, qué significa de verdad el percentil —y por qué siempre hay un 20% de líderes, también en un desplome—, cómo se lee cada tabla, y las tres secciones que convierten la foto del día en una película: quién entra y sale del liderazgo, hacia dónde rota el dinero entre sectores y si el mercado tira entero o solo unos pocos.' },
    { id:30, title:'SPXL — La Estrategia de Caídas', icon:'📉', description:'La única herramienta de la terminal que trabaja cuando el mercado corrige, no cuando sube. Qué cambia el triple apalancamiento, la premisa que la sostiene —el índice sube a largo plazo— y qué pasa si esa premisa falla, cómo compra por peldaños sin intentar acertar el suelo, las tres salidas según lo honda que fuera la caída, y por qué su 98% de aciertos no significa lo que parece. Con los números reales de 17,7 años, incluido lo que pierde frente a comprar y mantener.' },
    { id:31, title:'El Indicador RSU',              icon:'📶', description:'Manual del panel de barras que aparece bajo el gráfico en Research. Qué mide en realidad —dónde está el precio dentro de su propio rango reciente, no si la acción está cara o barata—, qué dice cada uno de los seis colores y las dos franjas del fondo, y una estrategia concreta de cuatro pasos para usarlo: filtrar en Scanner, descartar lo que va en contra de la tendencia, esperar el cruce y decidir con el resto de la terminal. Incluye dónde falla, por qué en tendencias fuertes deja de aportar, y en qué se diferencia del «Flujo con volumen» que aparece a su lado.' },
    { id:32, title:'Research — La Ficha de un Valor', icon:'🔎', description:'Manual de la ficha completa de un valor: cuándo se usa (con un nombre ya en la mano, no para explorar), de qué cinco categorías está hecho el RSU Score y por qué el desglose importa más que el número, cómo leer lo que hacen directivos, fondos y analistas —y por qué comprar informa más que vender—, un recorrido de cuatro paradas para descartar pronto, y dónde falla: bancos, aseguradoras, compañías extranjeras y salidas a bolsa recientes.' },
    { id:33, title:'Volume Spread Analysis (VSA)', icon:'👣', description:'Cuánto recorre cada vela, dónde cierra y con cuánto volumen: las huellas del dinero grande. Cómo se forma un suelo y cuándo se entra.' },
    { id:34, title:'Trading de Gaps', icon:'🕳️', description:'Qué dice cada hueco entre dos velas según dónde aparece, cuándo se rellena y cómo se opera el día que sale. Con el riesgo que un gap supone para quien ya está dentro.' },
];

export const PHASES = [
    { label:'🖥️ INTRO // RSU TERMINAL',              modules:[0] },
    { label:'📍 FASE 1 // ANÁLISIS TÉCNICO FUNDAMENTAL', modules:[1,2,3,4] },
    { label:'🔬 FASE 2 // LECTURA DE MERCADO AVANZADA',  modules:[5,6,7,8,33,17,24] },
    { label:'🎯 FASE 3 // ESTRATEGIA Y PLANIFICACIÓN',   modules:[9,10,11,18,19,34,23,25] },
    { label:'🚀 FASE 4 // EJECUCIÓN Y MENTALIDAD',       modules:[12,13,14,15] },
    { label:'🔄 FASE 5 // CICLO DE VIDA DEL PRECIO',     modules:[16] },
    { label:'🧮 FASE 6 // HERRAMIENTAS PROPIETARIAS RSU', modules:[20,21,22] },
    // Guía de la Terminal: el manual de cada módulo, en lenguaje de usuario.
    // Se separa de la FASE 6 a propósito — aquella explica los CONCEPTOS que
    // usan las herramientas (qué es el RSU Score, qué es el análisis
    // fundamental); esta explica CÓMO SE USA cada pantalla y qué ha hecho de
    // verdad. Se irá ampliando con un módulo por herramienta.
    { label:'🛠️ GUÍA DE LA TERMINAL // CÓMO FUNCIONA CADA HERRAMIENTA', modules:[26,27,28,29,30,31,32] },
];

// ── LECCIONES DE CADA MÓDULO ─────────────────────────────────────────────────
// La lista sale del manifiesto (= del contenido real), no de una lista
// declarada a mano en MODULES. Antes cada módulo declaraba un array `videos`
// con títulos y duraciones tipo '15:00' heredado de una versión anterior de
// Academy en la que las lecciones iban a ser vídeos: los vídeos nunca se
// grabaron, pero la interfaz seguía anunciando 📹 y más de 20 horas de
// duración sobre contenido que es texto. Además ese array ya había divergido
// del contenido real (en el módulo 12, dos títulos declarados no coincidían
// con los de las lecciones que se abrían).

export function leccionesDe(moduleId) {
    return Object.keys(LESSON_INDEX)
        .filter(k => k.startsWith(moduleId + '-'))
        .map(k => ({ key: k, index: parseInt(k.split('-')[1], 10), ...LESSON_INDEX[k] }))
        .sort((a, b) => a.index - b.index);
}
