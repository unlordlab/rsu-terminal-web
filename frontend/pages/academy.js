import { authHeader } from '/core/api.js';
// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — Página principal + Renderer de lecciones
// ─────────────────────────────────────────────────────────────────────────────

import { esc } from '/core/ui.js';
import { LESSON_INDEX, PALABRAS_POR_MINUTO } from '/pages/academy_manifest.js';

// ── CARGA BAJO DEMANDA DEL CONTENIDO ─────────────────────────────────────────
// academy_lessons.js (~525 KB) y academy_charts.js (~684 KB) se importaban
// antes de forma ESTÁTICA, así que entrar en Academy descargaba y parseaba
// ~1,3 MB aunque el usuario solo quisiera ver el índice de módulos. En móvil
// con datos eso son varios segundos de pantalla en blanco por una pantalla
// que solo necesita 26 títulos.
//
// Ahora el índice se pinta con academy_manifest.js (~8 KB, generado por
// scripts/gen_academy_manifest.py) y el contenido pesado se trae por partes,
// solo cuando de verdad hace falta:
//   · índice de módulos      → 0 KB extra
//   · detalle de un módulo   → quizzes (~84 KB)
//   · abrir una lección      → lecciones + gráficos (~1,2 MB, una sola vez)
//   · buscador               → lecciones (~525 KB, al escribir la 1ª búsqueda)
let _LESSONS = null;
let _CHARTS  = null;
let _QUIZZES = null;

async function cargarLecciones() {
    if (!_LESSONS) _LESSONS = (await import('/pages/academy_lessons.js')).LESSONS;
    return _LESSONS;
}
async function cargarGraficos() {
    if (!_CHARTS) _CHARTS = (await import('/pages/academy_charts.js')).CHARTS;
    return _CHARTS;
}
async function cargarQuizzes() {
    if (!_QUIZZES) _QUIZZES = (await import('/pages/academy_quizzes.js')).QUIZZES;
    return _QUIZZES;
}


// ── DATOS DE MÓDULOS ─────────────────────────────────────────────────────────

const MODULES = [
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
];

const PHASES = [
    { label:'🖥️ INTRO // RSU TERMINAL',              modules:[0] },
    { label:'📍 FASE 1 // ANÁLISIS TÉCNICO FUNDAMENTAL', modules:[1,2,3,4] },
    { label:'🔬 FASE 2 // LECTURA DE MERCADO AVANZADA',  modules:[5,6,7,8,17,24] },
    { label:'🎯 FASE 3 // ESTRATEGIA Y PLANIFICACIÓN',   modules:[9,10,11,18,19,23,25] },
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

function leccionesDe(moduleId) {
    return Object.keys(LESSON_INDEX)
        .filter(k => k.startsWith(moduleId + '-'))
        .map(k => ({ key: k, index: parseInt(k.split('-')[1], 10), ...LESSON_INDEX[k] }))
        .sort((a, b) => a.index - b.index);
}

function minutosDeLectura(palabras) {
    return Math.max(1, Math.round(palabras / PALABRAS_POR_MINUTO));
}

function minutosDeModulo(lecciones) {
    return minutosDeLectura(lecciones.reduce((t, l) => t + l.words, 0));
}

// ── PROGRESO DEL USUARIO ─────────────────────────────────────────────────────
// Una lección cuenta como leída cuando el usuario llega al FINAL de su
// contenido (ver observarFinDeLeccion), no cuando la abre: marcar al abrir
// habría llenado la barra de lecciones que nadie llegó a leer.

let _leidas         = new Set();
let _quizzes        = {};      // { "12": {score, total} }
let _finLeccion      = null;   // comprobación de "he llegado al final", se limpia en cleanup()
let _finLeccionMain  = null;   // nodo #main al que se enganchó (para poder desengancharlo)
let _finLeccionTimer = null;   // red de seguridad periódica (ver observarFinDeLeccion)

async function cargarProgreso() {
    try {
        const res  = await fetch('/api/v1/academy/progress', { headers: authHeader() });
        const data = await res.json();
        if (data && data.ok) {
            _leidas  = new Set(data.lessons || []);
            _quizzes = data.quizzes || {};
        }
    } catch (_) {
        // Sin progreso disponible se sigue navegando con normalidad: las
        // barras se quedan a cero, que es la verdad (no se sabe qué ha leído).
    }
}

async function marcarLeccionLeida(key) {
    if (_leidas.has(key)) return;
    _leidas.add(key);                      // optimista: la UI responde al instante
    try {
        const res = await fetch('/api/v1/academy/progress/lesson', {
            method: 'POST', headers: authHeader(), body: JSON.stringify({ lesson_key: key })
        });
        if (!res.ok) throw new Error(res.status);
    } catch (_) {
        _leidas.delete(key);               // no se guardó: no fingir que sí
    }
}

async function guardarResultadoQuiz(moduleId, score, total) {
    const previo = _quizzes[String(moduleId)];
    if (!previo || score > previo.score) _quizzes[String(moduleId)] = { score, total };
    try {
        await fetch('/api/v1/academy/progress/quiz', {
            method: 'POST', headers: authHeader(),
            body: JSON.stringify({ module_id: moduleId, score, total })
        });
    } catch (_) { /* mismo criterio: si falla, se reintenta al repetir el quiz */ }
}

// ── ESTILOS ───────────────────────────────────────────────────────────────────

function injectStyles() {
    if (document.getElementById('academy-styles')) return;
    const s = document.createElement('style');
    s.id = 'academy-styles';
    s.textContent = `
        /* Cards */
        .ac-card { cursor:pointer; transition: border-color .15s, transform .15s, box-shadow .15s; }
        .ac-card:hover { border-color: var(--color-accent) !important; transform: translateY(-2px); box-shadow: 0 4px 24px rgba(0,255,173,.08); }

        /* Lesson blocks */
        .ac-tip    { background: rgba(0,255,173,.06); border-left: 3px solid var(--color-accent); padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 12px 0; }
        .ac-warn   { background: rgba(255,152,0,.06); border-left: 3px solid #ff9800; padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 12px 0; }
        .ac-concept{ background: rgba(0,217,255,.05); border: 1px solid rgba(0,217,255,.2); padding: 16px; border-radius: 6px; margin: 14px 0; }
        .ac-steps  { padding: 0; list-style: none; margin: 12px 0; }
        .ac-steps li{ padding: 8px 0 8px 28px; position: relative; border-bottom: 1px solid var(--color-border); color: var(--color-text); font-size: 13px; line-height: 1.6; }
        .ac-steps li:last-child { border-bottom: none; }
        .ac-steps li::before { content: attr(data-n); position: absolute; left: 0; top: 8px; color: var(--color-accent); font-size: 11px; font-weight: 600; width: 20px; text-align: right; }
        .ac-table  { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 12px; }
        .ac-table th { background: rgba(255,255,255,.04); color: var(--color-accent); padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--color-border); letter-spacing: .06em; font-size: 11px; }
        .ac-table td { padding: 8px 12px; border-bottom: 1px solid var(--color-border); color: var(--color-text); line-height: 1.5; }
        .ac-table tr:last-child td { border-bottom: none; }
        .ac-table tr:hover td { background: rgba(255,255,255,.02); }
        .ac-chart  { width: 100%; margin: 16px 0; border-radius: 6px; overflow: hidden; border: 1px solid var(--color-border); }
        .ac-chart svg { width: 100%; height: auto; display: block; }
        .ac-section-heading { font-size: 15px; color: var(--color-text); margin: 28px 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border); letter-spacing: .04em; }
        .ac-intro  { font-size: 15px; line-height: 1.8; color: var(--color-secondary); margin-bottom: 28px; padding: 16px 20px; background: rgba(0,217,255,.04); border-radius: 6px; border-left: 3px solid var(--color-secondary); }
        .ac-text   { font-size: 13px; line-height: 1.8; color: var(--color-text); margin: 10px 0; }
        .ac-text strong { color: var(--color-accent); font-weight: 600; }
        .ac-text em     { color: var(--color-secondary); font-style: normal; }

        /* Nav pills */
        .ac-nav-pill { display:inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; cursor: pointer; border: 1px solid var(--color-border); color: var(--color-muted); transition: all .15s; margin: 0 4px 4px 0; }
        .ac-nav-pill:hover, .ac-nav-pill.active { border-color: var(--color-accent); color: var(--color-accent); background: rgba(0,255,173,.06); }

        /* Progress bar */
        .ac-progress { height: 3px; background: var(--color-border); border-radius: 2px; overflow: hidden; margin-top: 10px; }
        .ac-progress-bar { height: 100%; background: var(--color-accent); border-radius: 2px; transition: width .3s; }

        /* Lesson list item */
        .ac-lesson-item { display:flex; align-items:center; gap:12px; padding:12px 16px; border-bottom:1px solid var(--color-border); cursor:pointer; transition: background .12s; }
        .ac-lesson-item:hover { background: rgba(255,255,255,.02); }
        .ac-lesson-item:hover .ac-lesson-title { color: var(--color-accent); }
        .ac-lesson-num { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; flex-shrink:0; }

        /* Quiz */
        .quiz-option:not(:disabled):hover { border-color: var(--color-accent) !important; }
    `;
    document.head.appendChild(s);
}

// ── VISTA PRINCIPAL (grid de módulos) ─────────────────────────────────────────

export async function render(container) {
    injectStyles();
    container.innerHTML = header() + searchBox() + `<div id="ac-search-results"></div>`
                        + `<div id="ac-index">${phases()}${outcome()}${footer()}</div>`;
    attachCardListeners(container);
    attachSearch(container);

    // El índice se pinta ya, sin esperar a la red; cuando llega el progreso se
    // actualizan las barras en su sitio (una petición no debe retrasar la
    // primera pintura de una página que no depende de ella).
    cargarProgreso().then(() => actualizarBarras(container));
}

// El router destruye la página al navegar fuera (ver core/router.js): aquí se
// sueltan los listeners de "lección leída" para que no sigan vivos apuntando a
// un nodo que ya no está en el DOM.
export function cleanup() {
    detenerObservacion();
}

function header() {
    const totalLecciones = Object.keys(LESSON_INDEX).length;
    const totalMin       = minutosDeLectura(
        Object.values(LESSON_INDEX).reduce((t, l) => t + l.words, 0)
    );
    const horas = Math.floor(totalMin / 60), mins = totalMin % 60;
    return `<div style="margin-bottom:1.25rem;">
        <div style="color:var(--color-accent);font-size:18px;letter-spacing:.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ACADEMY</div>
        <div style="color:var(--color-secondary);font-size:13px;letter-spacing:.15em;margin-bottom:4px;">TECHNICAL ANALYSIS BLUEPRINT</div>
        <div style="color:var(--color-muted);font-size:12px;">${MODULES.length} MÓDULOS · ${totalLecciones} LECCIONES · ~${horas}h ${mins}min DE LECTURA</div>
    </div>`;
}

// ── BUSCADOR ─────────────────────────────────────────────────────────────────
// Con 26 módulos y 108 lecciones, "¿dónde se explicaba el VIX?" no tenía
// respuesta salvo abrir módulos a ojo. Busca primero por título (instantáneo,
// sale del manifiesto ya cargado) y, en cuanto llegan las lecciones, también
// dentro del texto de cada una.

function searchBox() {
    return `<div style="margin-bottom:1.5rem;">
        <input id="ac-search" type="search" placeholder="Buscar en Academy (p. ej. VIX, Weinstein, stop loss)…" autocomplete="off"
            style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-text);border-radius:var(--radius);padding:10px 14px;font-family:var(--font-mono);font-size:13px;outline:none;">
    </div>`;
}

function textoDeLeccion(lesson) {
    const partes = [lesson.title || '', lesson.intro || ''];
    (lesson.sections || []).forEach(sec => {
        partes.push(sec.heading || '');
        (sec.blocks || []).forEach(b => {
            if (b.content) partes.push(b.content);
            if (b.title)   partes.push(b.title);
            if (b.items)   partes.push(b.items.join(' '));
            if (b.headers) partes.push(b.headers.join(' '));
            if (b.rows)    partes.push(b.rows.map(r => r.join(' ')).join(' '));
        });
    });
    return partes.join(' ').replace(/<[^>]+>/g, ' ');
}

function extracto(texto, consulta) {
    const pos = texto.toLowerCase().indexOf(consulta.toLowerCase());
    if (pos < 0) return '';
    const ini = Math.max(0, pos - 60);
    const raw = (ini > 0 ? '…' : '') + texto.slice(ini, pos + consulta.length + 90).trim() + '…';
    // Se escapa el fragmento y DESPUÉS se resalta sobre el texto ya escapado,
    // así el <mark> no puede abrir la puerta a inyectar nada.
    const escapado = esc(raw.replace(/\s+/g, ' '));
    const aguja    = esc(consulta).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escapado.replace(new RegExp(aguja, 'gi'), m => `<mark style="background:rgba(0,255,173,.25);color:var(--color-text);">${m}</mark>`);
}

function buscar(consulta) {
    const q = consulta.trim().toLowerCase();
    if (q.length < 2) return [];
    const resultados = [];
    for (const [key, meta] of Object.entries(LESSON_INDEX)) {
        const modId  = parseInt(key.split('-')[0], 10);
        const modulo = MODULES.find(m => m.id === modId);
        const enTitulo = meta.title.toLowerCase().includes(q);
        let fragmento = '';
        if (_LESSONS && _LESSONS[key]) {
            const texto = textoDeLeccion(_LESSONS[key]);
            if (texto.toLowerCase().includes(q)) fragmento = extracto(texto, consulta.trim());
        }
        if (enTitulo || fragmento) {
            resultados.push({ key, title: meta.title, modulo, enTitulo, fragmento, words: meta.words });
        }
    }
    // Coincidir en el título es una señal más fuerte que aparecer de pasada
    // en el cuerpo: esos resultados van primero.
    return resultados.sort((a, b) => (b.enTitulo - a.enTitulo) || a.key.localeCompare(b.key)).slice(0, 30);
}

function renderResultados(resultados, consulta, cargandoTexto) {
    if (!resultados.length) {
        return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1.5rem;color:var(--color-muted);font-size:12px;">
            Sin resultados para "${esc(consulta)}"${cargandoTexto ? ' — todavía buscando solo por título, cargando el texto de las lecciones…' : ''}
        </div>`;
    }
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1.5rem;">
        <div style="padding:10px 16px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:11px;letter-spacing:.08em;">
            ${resultados.length} ${resultados.length === 1 ? 'RESULTADO' : 'RESULTADOS'}${cargandoTexto ? ' · buscando también dentro del texto…' : ''}
        </div>
        ${resultados.map(r => `
            <div class="ac-lesson-item" data-search-key="${r.key}">
                <div class="ac-lesson-num" style="background:${_leidas.has(r.key) ? 'var(--color-accent)' : 'rgba(255,255,255,.05)'};color:${_leidas.has(r.key) ? '#000' : 'var(--color-muted)'};">
                    ${_leidas.has(r.key) ? '✓' : '📖'}
                </div>
                <div style="flex:1;min-width:0;">
                    <div class="ac-lesson-title" style="color:var(--color-text);font-size:13px;">${esc(r.title)}</div>
                    <div style="color:var(--color-muted);font-size:10px;margin-top:2px;">MÓDULO ${r.modulo ? r.modulo.id + ' · ' + esc(r.modulo.title) : '—'}</div>
                    ${r.fragmento ? `<div style="color:var(--color-secondary);font-size:11px;line-height:1.5;margin-top:5px;">${r.fragmento}</div>` : ''}
                </div>
                <div style="color:var(--color-muted);font-size:11px;flex-shrink:0;">~${minutosDeLectura(r.words)} min</div>
            </div>`).join('')}
    </div>`;
}

function attachSearch(container) {
    const input   = container.querySelector('#ac-search');
    const salida  = container.querySelector('#ac-search-results');
    const indice  = container.querySelector('#ac-index');
    if (!input || !salida || !indice) return;

    let debounce = null;

    function pintar(consulta) {
        if (consulta.trim().length < 2) {
            salida.innerHTML = '';
            indice.style.display = '';
            return;
        }
        indice.style.display = 'none';
        salida.innerHTML = renderResultados(buscar(consulta), consulta, !_LESSONS);
        salida.querySelectorAll('[data-search-key]').forEach(item => {
            const key   = item.getAttribute('data-search-key');
            const modId = parseInt(key.split('-')[0], 10);
            item.addEventListener('click', () => abrirLeccion(container, key, MODULES.find(m => m.id === modId)));
        });
    }

    input.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            const consulta = input.value;
            pintar(consulta);
            // La primera búsqueda dispara la carga del texto completo; cuando
            // llega se repinta con los resultados de cuerpo, no solo de título.
            if (consulta.trim().length >= 2 && !_LESSONS) {
                cargarLecciones().then(() => {
                    if (input.value === consulta && document.body.contains(input)) pintar(consulta);
                }).catch(() => {});
            }
        }, 200);
    });
}

function phases() {
    return PHASES.map(phase => {
        const mods = phase.modules.map(i => MODULES[i]).filter(Boolean);
        return `<div style="margin-bottom:2rem;">
            <div style="color:var(--color-secondary);font-size:12px;letter-spacing:.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1rem;">${phase.label}</div>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;">
                ${mods.map(m => card(m)).join('')}
            </div>
        </div>`;
    }).join('<div style="border-top:1px solid var(--color-border);margin:1.5rem 0;"></div>');
}

function card(m) {
    const lecciones = leccionesDe(m.id);
    const leidas    = lecciones.filter(l => _leidas.has(l.key)).length;
    const pct       = lecciones.length ? Math.round(leidas / lecciones.length * 100) : 0;
    const completo  = lecciones.length > 0 && leidas === lecciones.length;
    return `<div class="ac-card" data-id="${m.id}" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="height:80px;background:linear-gradient(135deg,var(--color-surface),var(--color-bg,#0a0a0a));display:flex;align-items:center;justify-content:center;border-bottom:1px solid var(--color-border);position:relative;">
            <span style="font-size:2.2rem;">${m.icon}</span>
            <span data-mod-badge="${m.id}" style="position:absolute;top:8px;right:8px;background:var(--color-accent);color:#000;font-size:9px;padding:2px 6px;border-radius:10px;font-family:monospace;letter-spacing:.05em;${completo ? '' : 'display:none;'}">✓ COMPLETO</span>
        </div>
        <div style="padding:1rem;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <div style="background:var(--color-accent);color:#000;width:20px;height:20px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0;">${m.id}</div>
                <div style="color:var(--color-text);font-size:12px;letter-spacing:.04em;">${m.title.toUpperCase()}</div>
            </div>
            <div style="color:var(--color-muted);font-size:11px;line-height:1.5;margin-bottom:10px;">${m.description}</div>
            <div style="display:flex;gap:8px;font-size:10px;color:var(--color-muted);">
                <span>📖 ${lecciones.length} ${lecciones.length === 1 ? 'lección' : 'lecciones'}</span>
                <span>⏱ ~${minutosDeModulo(lecciones)} min de lectura</span>
            </div>
            <div class="ac-progress"><div class="ac-progress-bar" data-mod-bar="${m.id}" style="width:${pct}%"></div></div>
            <div data-mod-txt="${m.id}" style="color:var(--color-muted);font-size:10px;margin-top:5px;">${leidas}/${lecciones.length} leídas</div>
        </div>
    </div>`;
}

// Repinta solo las barras/contadores cuando llega el progreso del backend,
// sin volver a construir el índice entero (evita perder el scroll).
function actualizarBarras(container) {
    MODULES.forEach(m => {
        const lecciones = leccionesDe(m.id);
        const leidas    = lecciones.filter(l => _leidas.has(l.key)).length;
        const pct       = lecciones.length ? Math.round(leidas / lecciones.length * 100) : 0;
        const bar   = container.querySelector(`[data-mod-bar="${m.id}"]`);
        const txt   = container.querySelector(`[data-mod-txt="${m.id}"]`);
        const badge = container.querySelector(`[data-mod-badge="${m.id}"]`);
        if (bar)   bar.style.width  = pct + '%';
        if (txt)   txt.textContent  = `${leidas}/${lecciones.length} leídas`;
        if (badge) badge.style.display = (lecciones.length > 0 && leidas === lecciones.length) ? '' : 'none';
    });
}

function outcome() {
    const items = [
        {icon:'✅', text:'Setup Limpio — Sin ruido, sin dudas'},
        {icon:'⏳', text:'Entrada Paciente — Esperar la confirmación'},
        {icon:'🛡️', text:'Riesgo Controlado — Capital protegido'},
        {icon:'💰', text:'Salida Rentable — Ejecutar el plan'},
    ];
    return `<div style="border-top:1px solid var(--color-border);margin-top:2rem;padding-top:2rem;">
        <div style="color:var(--color-secondary);font-size:12px;letter-spacing:.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1.5rem;">🏆 RESULTADO FINAL // TECHNICAL ANALYSIS BLUEPRINT</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;">
            ${items.map(i=>`<div style="background:rgba(0,255,173,.04);border:1px solid var(--color-accent);border-radius:var(--radius);padding:1.25rem;text-align:center;">
                <div style="font-size:1.8rem;margin-bottom:8px;">${i.icon}</div>
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:.04em;">${i.text}</div>
            </div>`).join('')}
        </div>
    </div>`;
}

function footer() {
    return `<div style="text-align:center;margin-top:3rem;padding:1.5rem;border-top:1px solid var(--color-border);">
        <div style="color:var(--color-muted);font-size:10px;letter-spacing:.15em;">[END OF TRANSMISSION // TECHNICAL_ANALYSIS_BLUEPRINT_v1.0]<br>[${MODULES.length} MÓDULOS // ${Object.keys(LESSON_INDEX).length} LECCIONES // RSU ACADEMY]</div>
    </div>`;
}

function attachCardListeners(container) {
    container.querySelectorAll('.ac-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = parseInt(card.getAttribute('data-id'));
            const m  = MODULES.find(x => x.id === id);
            if (m) renderModuleDetail(container, m);
        });
    });
}

// ── VISTA DE MÓDULO (lista de lecciones) ──────────────────────────────────────

async function renderModuleDetail(container, m) {
    injectStyles();
    const lessons = leccionesDe(m.id);
    await cargarQuizzes();   // ~84 KB, solo al entrar en un módulo

    container.innerHTML = `
        <button id="btn-volver" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;margin-bottom:1.5rem;">← VOLVER</button>

        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.5rem;">
            <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;">
                <span style="font-size:2.5rem;">${m.icon}</span>
                <div>
                    <div style="color:var(--color-accent);font-size:18px;letter-spacing:.08em;">${m.title.toUpperCase()}</div>
                    <div style="color:var(--color-muted);font-size:12px;margin-top:2px;">📖 ${lessons.length} ${lessons.length === 1 ? 'lección' : 'lecciones'} · ⏱ ~${minutosDeModulo(lessons)} min de lectura</div>
                </div>
            </div>
            <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${m.description}</div>
        </div>

        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
            <div style="padding:10px 16px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:11px;letter-spacing:.08em;">CONTENIDO DEL MÓDULO</div>
            ${lessons.map((l, i) => {
                const leida = _leidas.has(l.key);
                return `<div class="ac-lesson-item" data-key="${l.key}">
                    <div class="ac-lesson-num" style="background:${leida ? 'var(--color-accent)' : 'rgba(255,255,255,.05)'};color:${leida ? '#000' : 'var(--color-muted)'};">
                        ${leida ? '✓' : i + 1}
                    </div>
                    <div style="flex:1;">
                        <div class="ac-lesson-title" style="color:var(--color-text);font-size:13px;">${esc(l.title)}</div>
                        ${leida ? `<div style="color:var(--color-accent);font-size:10px;margin-top:2px;letter-spacing:.04em;">LEÍDA</div>` : ''}
                    </div>
                    <div style="color:var(--color-muted);font-size:11px;">~${minutosDeLectura(l.words)} min</div>
                </div>`;
            }).join('')}
        </div>

        ${quizBlock(m)}
    `;

    container.querySelector('#btn-volver').addEventListener('click', () => render(container));

    container.querySelectorAll('.ac-lesson-item').forEach(item => {
        item.addEventListener('click', () => abrirLeccion(container, item.getAttribute('data-key'), m));
    });

    const quizBtn = container.querySelector('#btn-start-quiz');
    if (quizBtn) {
        quizBtn.addEventListener('click', () => {
            const quiz = _QUIZZES[m.id];
            if (quiz) renderQuiz(container, quiz, m);
        });
    }
}

// Punto único de apertura de una lección: se encarga de traer el contenido
// pesado (lecciones + gráficos) antes de renderizar, con un aviso visible
// mientras llega -- la primera vez son ~1,2 MB y en móvil se nota.
async function abrirLeccion(container, key, m) {
    const previo = container.innerHTML;
    if (!_LESSONS || !_CHARTS) {
        container.innerHTML = `<div style="color:var(--color-muted);font-size:12px;padding:2rem;text-align:center;">Cargando contenido de la lección…</div>`;
    }
    try {
        await Promise.all([cargarLecciones(), cargarGraficos()]);
    } catch (_) {
        container.innerHTML = previo;
        return;
    }
    const lesson = _LESSONS[key];
    if (lesson) renderLesson(container, lesson, m, key);
    else container.innerHTML = previo;
}

// ── BLOQUE DE ACCESO AL QUIZ (en la vista de módulo) ───────────────────────────

function quizBlock(m) {
    const quiz = _QUIZZES && _QUIZZES[m.id];
    if (!quiz) return '';
    const previo = _quizzes[String(m.id)];
    const marca  = previo
        ? `<div style="color:var(--color-accent);font-size:11px;margin-top:4px;">✓ Mejor resultado: ${previo.score}/${previo.total} a la primera</div>`
        : '';
    return `<div style="background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);padding:1.25rem;margin-top:1.5rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
        <div>
            <div style="color:var(--color-accent);font-size:12px;letter-spacing:.08em;margin-bottom:4px;">🎯 QUIZ DEL MÓDULO</div>
            <div style="color:var(--color-muted);font-size:11px;">${quiz.questions.length} preguntas · repite las que falles hasta acertarlas, sin límite de intentos</div>
            ${marca}
        </div>
        <button id="btn-start-quiz" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;letter-spacing:.05em;flex-shrink:0;">${previo ? 'REPETIR QUIZ →' : 'EMPEZAR QUIZ →'}</button>
    </div>`;
}

// ── VISTA DE QUIZ ──────────────────────────────────────────────────────────────

function renderQuiz(container, quiz, module) {
    injectStyles();

    // Estado del quiz: por cada pregunta, si ya se acertó, y cuántos intentos ha llevado
    const state = quiz.questions.map(() => ({ solved: false, selected: null, attempts: 0 }));
    let current = 0;

    function draw() {
        const total = quiz.questions.length;
        const solvedCount = state.filter(s => s.solved).length;

        if (current >= total) {
            renderQuizComplete(container, quiz, module, state);
            return;
        }

        const q = quiz.questions[current];
        const s = state[current];

        container.innerHTML = `
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap;">
                <button id="btn-exit-quiz" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← SALIR DEL QUIZ</button>
                <div style="color:var(--color-muted);font-size:11px;">${quiz.title.toUpperCase()}</div>
            </div>

            <div style="margin-bottom:1.25rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="color:var(--color-muted);font-size:11px;letter-spacing:.08em;">PREGUNTA ${current+1} DE ${total}</span>
                    <span style="color:var(--color-accent);font-size:11px;">${solvedCount}/${total} acertadas</span>
                </div>
                <div class="ac-progress"><div class="ac-progress-bar" style="width:${(solvedCount/total*100).toFixed(0)}%"></div></div>
            </div>

            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;">
                <div style="color:var(--color-text);font-size:15px;line-height:1.6;margin-bottom:1.25rem;">${q.q}</div>
                <div id="quiz-options">
                    ${q.options.map((opt, i) => optionRow(opt, i, s)).join('')}
                </div>
                <div id="quiz-feedback"></div>
            </div>
        `;

        container.querySelector('#btn-exit-quiz').addEventListener('click', () => renderModuleDetail(container, module));

        if (!s.solved) {
            container.querySelectorAll('.quiz-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    const idx = parseInt(btn.getAttribute('data-idx'));
                    handleAnswer(idx);
                });
            });
        } else {
            renderFeedback();
            renderNextButton();
        }

        const main = document.getElementById('main');
        if (main) main.scrollTop = 0;
        window.scrollTo(0, 0);
    }

    function optionRow(opt, i, s) {
        const isSelected = s.selected === i;
        const isCorrect = i === quiz.questions[current].correct;
        let bg = 'var(--color-bg,#0a0a0a)', border = 'var(--color-border)', color = 'var(--color-text)';

        if (s.solved) {
            if (isCorrect) { bg = 'rgba(0,255,173,.08)'; border = 'var(--color-accent)'; color = 'var(--color-accent)'; }
            else if (isSelected) { bg = 'rgba(242,54,69,.08)'; border = '#f23645'; color = '#f23645'; }
        } else if (isSelected) {
            bg = 'rgba(242,54,69,.08)'; border = '#f23645'; color = '#f23645';
        }

        return `<button class="quiz-option" data-idx="${i}" ${s.solved ? 'disabled' : ''} style="display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:${bg};border:1px solid ${border};color:${color};border-radius:var(--radius);padding:12px 14px;margin-bottom:8px;font-family:var(--font-mono);font-size:13px;cursor:${s.solved?'default':'pointer'};transition:all .15s;">
            <span style="width:20px;height:20px;border-radius:50%;border:1px solid ${border};display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;">${s.solved && isCorrect ? '✓' : s.solved && isSelected ? '✗' : String.fromCharCode(65+i)}</span>
            <span>${opt}</span>
        </button>`;
    }

    function handleAnswer(idx) {
        const s = state[current];
        const q = quiz.questions[current];
        s.selected = idx;
        s.attempts++;
        if (idx === q.correct) s.solved = true;
        draw();
    }

    function renderFeedback() {
        const s = state[current];
        const q = quiz.questions[current];
        const fb = container.querySelector('#quiz-feedback');
        if (!fb) return;
        const wasFirstTry = s.attempts === 1;
        fb.innerHTML = `<div style="margin-top:12px;padding:12px 14px;background:rgba(0,255,173,.06);border-left:3px solid var(--color-accent);border-radius:0 6px 6px 0;">
            <div style="color:var(--color-accent);font-size:11px;letter-spacing:.06em;margin-bottom:5px;">✓ ${wasFirstTry ? 'CORRECTO' : 'CORRECTO — ' + s.attempts + ' INTENTOS'}</div>
            <div style="color:var(--color-text);font-size:12.5px;line-height:1.6;">${q.explanation}</div>
        </div>`;
    }

    function renderNextButton() {
        const fb = container.querySelector('#quiz-feedback');
        if (!fb) return;
        const isLast = current === quiz.questions.length - 1;
        const btn = document.createElement('button');
        btn.textContent = isLast ? 'VER RESULTADOS →' : 'SIGUIENTE PREGUNTA →';
        btn.style.cssText = 'margin-top:14px;background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;letter-spacing:.05em;width:100%;';
        btn.addEventListener('click', () => { current++; draw(); });
        fb.appendChild(btn);
    }

    draw();
}

function renderQuizComplete(container, quiz, module, state) {
    injectStyles();
    const totalAttempts = state.reduce((sum, s) => sum + s.attempts, 0);
    const perfectRun = state.every(s => s.attempts === 1);

    // Se guarda el número de preguntas acertadas A LA PRIMERA: todas acaban
    // resolviéndose (el quiz no deja avanzar sin acertar), así que "4/4
    // acertadas" no distinguiría a nadie. Los intentos sí.
    guardarResultadoQuiz(module.id, state.filter(s => s.attempts === 1).length, quiz.questions.length);

    container.innerHTML = `
        <div style="text-align:center;padding:3rem 1.5rem;background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);">
            <div style="font-size:3rem;margin-bottom:1rem;">${perfectRun ? '🏆' : '✅'}</div>
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:.08em;margin-bottom:8px;">QUIZ COMPLETADO</div>
            <div style="color:var(--color-text);font-size:13px;margin-bottom:4px;">${quiz.title}</div>
            <div style="color:var(--color-muted);font-size:12px;margin-bottom:1.5rem;">
                ${quiz.questions.length}/${quiz.questions.length} preguntas acertadas
                ${perfectRun ? '· todas a la primera' : '· ' + totalAttempts + ' intentos totales'}
            </div>
            <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
                <button id="btn-quiz-back" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← VOLVER AL MÓDULO</button>
                <button id="btn-quiz-retry" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;">REPETIR QUIZ</button>
            </div>
        </div>
    `;

    container.querySelector('#btn-quiz-back').addEventListener('click', () => renderModuleDetail(container, module));
    container.querySelector('#btn-quiz-retry').addEventListener('click', () => renderQuiz(container, quiz, module));

    const main = document.getElementById('main');
    if (main) main.scrollTop = 0;
    window.scrollTo(0, 0);   // #main tiene overflow:auto pero no es quien scrollea (ver observarFinDeLeccion)
}

// ── VISTA DE LECCIÓN (contenido didáctico) ────────────────────────────────────

function renderLesson(container, lesson, module, lessonKey) {
    injectStyles();

    // Navegación entre lecciones del módulo
    const moduleKey  = lesson.moduleId;
    const allLessons = leccionesDe(moduleKey);
    const currentIdx = allLessons.findIndex(l => l.key === lessonKey);
    const minutos    = LESSON_INDEX[lessonKey] ? minutosDeLectura(LESSON_INDEX[lessonKey].words) : null;

    const navPills = allLessons.map((l,i) =>
        `<span class="ac-nav-pill ${i===currentIdx?'active':''}" data-key="${l.key}" data-title="${l.title}">${i+1}. ${l.title.split('—')[0].trim()}</span>`
    ).join('');

    const prevLesson = currentIdx > 0 ? allLessons[currentIdx-1] : null;
    const nextLesson = currentIdx < allLessons.length-1 ? allLessons[currentIdx+1] : null;

    container.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap;">
            <button id="btn-volver-mod" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← ${module.title.toUpperCase()}</button>
            <div style="color:var(--color-muted);font-size:11px;">MÓDULO ${moduleKey}</div>
        </div>

        <!-- Nav pills -->
        <div style="margin-bottom:1.5rem;padding:12px 14px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:.1em;margin-bottom:8px;">LECCIONES DEL MÓDULO</div>
            ${navPills}
        </div>

        <!-- Lesson header -->
        <div style="margin-bottom:1.5rem;">
            <div style="color:var(--color-muted);font-size:11px;letter-spacing:.1em;margin-bottom:6px;">LECCIÓN ${currentIdx+1} DE ${allLessons.length}</div>
            <h1 style="font-size:20px;color:var(--color-text);letter-spacing:.05em;margin:0 0 6px;font-family:var(--font-mono);">${lesson.title}</h1>
            <div style="display:flex;gap:12px;align-items:center;">
                <span style="color:var(--color-muted);font-size:12px;">⏱ ~${minutos || 1} min de lectura</span>
                <span style="color:var(--color-accent);font-size:10px;background:rgba(0,255,173,.08);padding:2px 8px;border-radius:10px;border:1px solid rgba(0,255,173,.2);">MÓDULO ${module.id} // ${module.title.toUpperCase()}</span>
            </div>
        </div>

        <!-- Intro -->
        <div class="ac-intro">${lesson.intro}</div>

        <!-- Sections -->
        <div id="lesson-body">
            ${lesson.sections.map(sec => renderSection(sec)).join('')}
        </div>

        <!-- Centinela de "lección leída": cuando este nodo entra en pantalla,
             el usuario ha llegado al final del contenido. Ver observarFinDeLeccion. -->
        <div id="ac-lesson-end" style="height:1px;"></div>

        <!-- Bottom nav -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:2.5rem;padding-top:1.5rem;border-top:1px solid var(--color-border);">
            <div>
                ${prevLesson ? `<button class="ac-lesson-nav" data-key="${prevLesson.key}" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;">← ${prevLesson.title.split('—')[0].trim()}</button>` : ''}
            </div>
            <div style="color:var(--color-muted);font-size:11px;">${currentIdx+1} / ${allLessons.length}</div>
            <div>
                ${nextLesson ? `<button class="ac-lesson-nav" data-key="${nextLesson.key}" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 16px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:600;">${nextLesson.title.split('—')[0].trim()} →</button>` : `<span style="color:var(--color-accent);font-size:12px;">✓ Módulo completado</span>`}
            </div>
        </div>
    `;

    // Events
    container.querySelector('#btn-volver-mod').addEventListener('click', () => renderModuleDetail(container, module));

    container.querySelectorAll('.ac-nav-pill[data-key]').forEach(pill => {
        pill.addEventListener('click', () => abrirLeccion(container, pill.getAttribute('data-key'), module));
    });

    container.querySelectorAll('.ac-lesson-nav').forEach(btn => {
        btn.addEventListener('click', () => abrirLeccion(container, btn.getAttribute('data-key'), module));
    });

    // Scroll top
    const main = document.getElementById('main');
    if (main) main.scrollTop = 0;
    window.scrollTo(0, 0);   // #main tiene overflow:auto pero no es quien scrollea (ver observarFinDeLeccion)

    observarFinDeLeccion(container, lessonKey);
}

// Marca la lección como leída cuando el usuario llega al final del contenido.
// Criterio deliberado: marcar al ABRIR habría inflado la barra de progreso con
// lecciones que nadie llegó a leer -- el mismo tipo de dato plausible pero
// falso que ya se eliminó del resto de la terminal.
//
// Se comprueba la posición del centinela a mano en vez de con
// IntersectionObserver: #main tiene overflow:auto pero NO es el elemento que
// scrollea (su scrollHeight es igual a su clientHeight — quien scrollea es el
// documento), así que un observer con root:#main no delimita nada y su
// resultado no es fiable. Los listeners van sobre window y sobre #main para
// cubrir las dos posibilidades según el ancho de pantalla.
function observarFinDeLeccion(container, lessonKey) {
    detenerObservacion();
    if (!lessonKey || _leidas.has(lessonKey)) return;

    const centinela = container.querySelector('#ac-lesson-end');
    if (!centinela) return;
    const main = document.getElementById('main');

    _finLeccion = () => {
        if (!document.body.contains(centinela)) { detenerObservacion(); return; }
        const alto = window.innerHeight || document.documentElement.clientHeight;
        // Con un margen de 80px: llegar "al final" no exige clavar el píxel.
        if (centinela.getBoundingClientRect().top - 80 <= alto) {
            detenerObservacion();
            marcarLeccionLeida(lessonKey);
        }
    };

    window.addEventListener('scroll', _finLeccion, { passive: true });
    window.addEventListener('resize', _finLeccion, { passive: true });
    if (main) main.addEventListener('scroll', _finLeccion, { passive: true });
    _finLeccionMain = main;

    // Red de seguridad que NO depende de que lleguen eventos de scroll: se
    // comprueba la posición una vez por segundo mientras la lección esté
    // abierta. Cuesta nada y evita el peor fallo posible aquí -- que el
    // progreso deje de registrarse en silencio si algún navegador (o un
    // contenedor con scroll propio) no entrega los eventos esperados.
    // Cubre además la lección corta que cabe entera en pantalla sin scroll.
    _finLeccionTimer = setInterval(() => { if (_finLeccion) _finLeccion(); }, 1000);
}

function detenerObservacion() {
    if (_finLeccionTimer) { clearInterval(_finLeccionTimer); _finLeccionTimer = null; }
    if (!_finLeccion) return;
    window.removeEventListener('scroll', _finLeccion);
    window.removeEventListener('resize', _finLeccion);
    if (_finLeccionMain) _finLeccionMain.removeEventListener('scroll', _finLeccion);
    _finLeccion = null;
    _finLeccionMain = null;
}

// ── RENDERIZAR SECCIÓN ────────────────────────────────────────────────────────

function renderSection(sec) {
    const blocks = sec.blocks.map(b => renderBlock(b)).join('');
    return `<div style="margin-bottom:2rem;">
        <h2 class="ac-section-heading">${sec.heading}</h2>
        ${blocks}
    </div>`;
}

function renderBlock(block) {
    switch (block.type) {

        case 'text':
            return `<p class="ac-text">${block.content}</p>`;

        case 'tip':
            return `<div class="ac-tip">
                <div style="color:var(--color-accent);font-size:10px;letter-spacing:.1em;margin-bottom:5px;">${block.label || 'CONSEJO'}</div>
                <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${block.content}</div>
            </div>`;

        case 'warning':
            return `<div class="ac-warn">
                <div style="color:#ff9800;font-size:10px;letter-spacing:.1em;margin-bottom:5px;">⚠ ATENCIÓN</div>
                <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${block.content}</div>
            </div>`;

        case 'concept':
            return `<div class="ac-concept">
                <div style="color:var(--color-secondary);font-size:11px;letter-spacing:.1em;margin-bottom:8px;">💡 CONCEPTO — ${block.title.toUpperCase()}</div>
                <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${block.content}</div>
            </div>`;

        case 'steps':
            return `<ol class="ac-steps">
                ${block.items.map((item, i) => `<li data-n="${i+1}.">${item}</li>`).join('')}
            </ol>`;

        case 'table':
            return `<div style="overflow-x:auto;margin:14px 0;">
                <table class="ac-table">
                    <thead><tr>${block.headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead>
                    <tbody>${block.rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
                </table>
            </div>`;

        case 'chart':
            const chartFn = _CHARTS && _CHARTS[block.id];
            if (!chartFn) return `<div style="color:var(--color-muted);font-size:11px;padding:8px;border:1px dashed var(--color-border);border-radius:4px;margin:12px 0;">Gráfico: ${block.id}</div>`;
            return `<div class="ac-chart">${chartFn()}</div>`;

        case 'divider':
            return `<hr style="border:none;border-top:1px solid var(--color-border);margin:20px 0;">`;

        default:
            return '';
    }
}