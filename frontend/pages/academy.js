// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — Página principal + Renderer de lecciones
// ─────────────────────────────────────────────────────────────────────────────

import { LESSONS } from '/pages/academy_lessons.js';
import { CHARTS  } from '/pages/academy_charts.js';
import { QUIZZES } from '/pages/academy_quizzes.js';

// ── DATOS DE MÓDULOS ─────────────────────────────────────────────────────────

const MODULES = [
    { id:0,  title:'RSU Terminal',                icon:'🖥️', description:'Entiende qué es RSU Terminal, la metodología detrás y cómo sacar el máximo partido a cada herramienta.', duration:'40 min',
      videos:[{title:'Qué es RSU Terminal',duration:'10:00'},{title:'La Metodología RSU',duration:'10:00'},{title:'Las Herramientas',duration:'12:00'},{title:'Flujo de Trabajo Semanal',duration:'8:00'}]},
    { id:1,  title:'Configuración de Gráficos',   icon:'📊', description:'Configura correctamente tus gráficos en múltiples temporalidades. El análisis top-down empieza aquí.', duration:'59 min',
      videos:[{title:'Gráfico Mensual — La visión macro',duration:'12:00'},{title:'Gráfico Semanal — La tendencia media',duration:'11:00'},{title:'Gráfico Diario — El setup operativo',duration:'12:00'},{title:'Velas Limpias — Sin ruido visual',duration:'10:00'},{title:'Medias Móviles Exponenciales (EMA)',duration:'14:00'}]},
    { id:2,  title:'Estructura de Mercado',        icon:'🏗️', description:'Identifica la tendencia antes de operar. Máximos y mínimos crecientes o decrecientes lo dicen todo.', duration:'50 min',
      videos:[{title:'Máximos Crecientes — Señal alcista',duration:'12:00'},{title:'Mínimos Crecientes — Soporte dinámico',duration:'13:00'},{title:'Máximos Decrecientes — Señal bajista',duration:'12:00'},{title:'Mínimos Decrecientes — Presión vendedora',duration:'13:00'}]},
    { id:3,  title:'Análisis de Tendencia',        icon:'📈', description:'Nunca luches contra el mercado. Aprende a identificar y operar a favor de la tendencia dominante.', duration:'55 min',
      videos:[{title:'Tendencia Alcista — Cómo montarla',duration:'14:00'},{title:'Tendencia Bajista — Cómo evitarla',duration:'13:00'},{title:'Rango Lateral — Paciencia obligatoria',duration:'14:00'},{title:'Validación de Líneas de Tendencia',duration:'14:00'}]},
    { id:4,  title:'Soporte y Resistencia',        icon:'🧱', description:'Los niveles fuertes controlan el precio. Aprende a marcar zonas que realmente importan.', duration:'1h',
      videos:[{title:'Soporte Fresco — Primera vez testeado',duration:'15:00'},{title:'Resistencia Mayor — Donde venden los grandes',duration:'15:00'},{title:'Marcado de Zonas — Técnica profesional',duration:'15:00'},{title:'Niveles con Múltiples Toques',duration:'15:00'}]},
    { id:5,  title:'Oferta y Demanda',             icon:'⚖️', description:'Las instituciones actúan en estas zonas. Aprende a identificar dónde el dinero inteligente opera.', duration:'1h 10min',
      videos:[{title:'Zonas de Demanda',duration:'18:00'},{title:'Zonas de Oferta',duration:'17:00'},{title:'Áreas de Rechazo',duration:'17:00'},{title:'Formación de Base',duration:'18:00'}]},
    { id:6,  title:'Comportamiento de Velas',      icon:'🕯️', description:'El cierre de la vela revela la verdad. Las formaciones de velas cuentan la historia del mercado.', duration:'1h',
      videos:[{title:'Engulfing Alcista',duration:'15:00'},{title:'Engulfing Bajista',duration:'15:00'},{title:'Pin Bar',duration:'15:00'},{title:'Inside Bar',duration:'15:00'}]},
    { id:7,  title:'Rupturas de Precio',           icon:'💥', description:'Confirma si es real o una trampa. Las rupturas falsas son la fuente de pérdidas más común.', duration:'1h 5min',
      videos:[{title:'Ruptura de Rango',duration:'16:00'},{title:'Ruptura de Tendencia',duration:'16:00'},{title:'Ruptura de Soporte',duration:'17:00'},{title:'Entradas en Retest',duration:'16:00'}]},
    { id:8,  title:'Análisis de Volumen',          icon:'📦', description:'El volumen confirma el precio. Sin volumen, el movimiento no tiene convicción real.', duration:'1h',
      videos:[{title:'Volumen en Rupturas',duration:'15:00'},{title:'Bajo Volumen en Retrocesos',duration:'15:00'},{title:'Volumen Clímax',duration:'16:00'},{title:'Participación Débil',duration:'15:00'}]},
    { id:9,  title:'Patrones de Gráfico',          icon:'🔷', description:'Los patrones solo funcionan con contexto. Aprende a leerlos dentro de la tendencia dominante.', duration:'1h 10min',
      videos:[{title:'Triángulo Ascendente',duration:'17:00'},{title:'Triángulo Descendente',duration:'17:00'},{title:'Rectángulo',duration:'18:00'},{title:'Bandera y Asta',duration:'18:00'}]},
    { id:10, title:'Alineación Multi-Temporalidad',icon:'🔭', description:'La alineación crea potencia. Cuando mensual, semanal y diario coinciden, la probabilidad dispara.', duration:'1h 30min',
      videos:[{title:'Sesgo Mensual',duration:'20:00'},{title:'Estructura Semanal',duration:'20:00'},{title:'Setup Diario',duration:'20:00'},{title:'Trigger en TF Menor',duration:'20:00'},{title:'Configurar tu Watchlist',duration:'10:00'}]},
    { id:11, title:'Planificación del Trade',      icon:'📋', description:'Sin plan no hay trading. Define entrada, stop y objetivo antes de pulsar el botón.', duration:'1h',
      videos:[{title:'Definir el Setup',duration:'15:00'},{title:'Ratio Riesgo/Recompensa',duration:'15:00'},{title:'Tamaño de Posición',duration:'15:00'},{title:'El Plan de Trade',duration:'15:00'}]},
    { id:12, title:'Gestión del Riesgo',           icon:'🛡️', description:'Sobrevive primero, gana después. La gestión del riesgo es lo único que te mantiene en el juego.', duration:'1h 10min',
      videos:[{title:'Riesgo Fijo por Trade',duration:'17:00'},{title:'Sizing de Posición',duration:'18:00'},{title:'Sin Revenge Trading',duration:'17:00'},{title:'Protección de Capital',duration:'18:00'}]},
    { id:13, title:'Ejecución',                    icon:'⚡', description:'La disciplina es el edge. Espera confirmación, sigue el plan y sal sin ego.', duration:'1h',
      videos:[{title:'Esperar Confirmación',duration:'15:00'},{title:'Evitar Entradas Prematuras',duration:'15:00'},{title:'Seguir el Plan',duration:'15:00'},{title:'Salir Sin Ego',duration:'15:00'}]},
    { id:14, title:'Trampas del Mercado',          icon:'⚠️', description:'El mercado cobra matrícula. Aprende a reconocer las trampas más comunes antes de caer en ellas.', duration:'1h 5min',
      videos:[{title:'Falsas Rupturas',duration:'16:00'},{title:'Entradas Tardías',duration:'16:00'},{title:'Sobretrading',duration:'17:00'},{title:'Ignorar el Volumen',duration:'16:00'}]},
    { id:15, title:'Revisión Post-Trade',          icon:'📓', description:'Journal o repite el dolor. La revisión sistemática es lo que separa a los traders rentables.', duration:'50 min',
      videos:[{title:'Captura de Pantalla',duration:'12:00'},{title:'Registro de Errores',duration:'13:00'},{title:'Revisión del Setup',duration:'13:00'},{title:'Lecciones Aprendidas',duration:'12:00'}]},
    { id:16, title:'Las 4 Etapas (Weinstein)',     icon:'🔄', description:'Acumulación, avance, distribución y declive. El mapa de ciclo de vida que dice cuándo comprar y cuándo no.', duration:'1h',
      videos:[{title:'Etapa 1 — Acumulación',duration:'15:00'},{title:'Etapa 2 — Avance',duration:'15:00'},{title:'Etapa 3 — Distribución',duration:'15:00'},{title:'Etapa 4 — Declive',duration:'15:00'}]},
    { id:17, title:'El Mercado Descuenta Información', icon:'⏳', description:'Por qué el precio se mueve ANTES de la noticia. Buy the rumour, sell the news — y cómo no quedar atrapado en el lado equivocado.', duration:'1h',
      videos:[{title:'La Máquina de Descontar',duration:'15:00'},{title:'Buy the Rumour',duration:'15:00'},{title:'Sell the News',duration:'15:00'},{title:'Earnings y Eventos Macro',duration:'15:00'}]},
    { id:18, title:'Risk/Reward',                  icon:'⚖️', description:'No es una cifra que se calcula — es el resultado de dónde compras. Una buena zona de demanda mejora el riesgo, la recompensa y la psicología a la vez.', duration:'1h',
      videos:[{title:'La Zona de Entrada lo Decide Todo',duration:'15:00'},{title:'Anatomía de una Buena Zona de Demanda',duration:'15:00'},{title:'El Lado Psicológico del Buen R:R',duration:'15:00'},{title:'Aplicar el R:R desde la Zona, no desde la Calculadora',duration:'15:00'}]},
    { id:19, title:'Métodos de Confirmación de Entrada', icon:'🎯', description:'6 técnicas para confirmar que una entrada tiene base real: trendlines, soporte/resistencia, Fibonacci, consolidaciones, gaps y volumen.', duration:'1h 30min',
      videos:[{title:'Reversión y Ruptura de Línea de Tendencia',duration:'15:00'},{title:'Soporte y Resistencia como Confirmación',duration:'15:00'},{title:'Retroceso de Fibonacci',duration:'15:00'},{title:'Consolidaciones',duration:'15:00'},{title:'Gaps de Precio',duration:'15:00'},{title:'Volumen Clímax y Tendencia',duration:'15:00'}]},
    { id:20, title:'RSU Score Explicado',        icon:'🧮', description:'Qué mide realmente el RSU Score, cómo se calcula el Piotroski F-Score, y por qué son dos indicadores independientes que hay que leer juntos, no como un semáforo ciego.', duration:'50 min',
      videos:[{title:'Qué Mide el RSU Score',duration:'12:00'},{title:'Piotroski F-Score — Salud Financiera',duration:'13:00'},{title:'Comparativa Sectorial — Valorar en Contexto',duration:'12:00'},{title:'Cómo Leer Todo Junto',duration:'13:00'}]},
    { id:21, title:'Análisis Fundamental',       icon:'📐', description:'La base fundamental detrás de CAN SLIM: cómo leer estados financieros, rentabilidad, valoración con múltiplos y los catalizadores que mueven el precio.', duration:'55 min',
      videos:[{title:'Ingresos, Márgenes y Beneficio',duration:'14:00'},{title:'Rentabilidad y Eficiencia — ROE, ROA',duration:'13:00'},{title:'Valoración — P/E, PEG, EV/EBITDA, P/S, P/B',duration:'14:00'},{title:'Catalizadores — Earnings, Insiders, Institucionales',duration:'14:00'}]},
    { id:22, title:'El Triángulo RSU',           icon:'🔺', description:'Cuando el flujo de opciones, el posicionamiento institucional y la técnica se alinean, la probabilidad de una operación ganadora se dispara. La metodología de confluencia de tres señales.', duration:'50 min',
      videos:[{title:'Los Tres Pilares del Triángulo',duration:'12:00'},{title:'Order Flow — La Huella del Dinero Grande',duration:'13:00'},{title:'Posicionamiento — Qué Apuesta el Mercado',duration:'13:00'},{title:'El Checklist de Confluencia',duration:'12:00'}]},
    { id:23, title:'Convicción a Largo Plazo',   icon:'🏔️', description:'Por qué a veces merece la pena pagar una prima de valoración por una posición estratégica en un tema de crecimiento secular — y cómo no confundir convicción con negación cuando la tesis se rompe.', duration:'50 min',
      videos:[{title:'Pagar la Prima por Posición Estratégica',duration:'13:00'},{title:'Identificar Posiciones "Misión Crítica"',duration:'13:00'},{title:'El Marco Temporal de la Convicción',duration:'12:00'},{title:'Convicción Propia y Gestión del Riesgo',duration:'12:00'}]},
    { id:24, title:'Volatilidad, el VIX y la Oportunidad', icon:'🌪️', description:'La volatilidad no es lo mismo que perder capital de forma permanente. Qué mide el VIX de verdad, por qué los picos extremos de miedo han sido históricamente zonas interesantes — y por qué desconfiar de cualquier tabla de rendimientos "hipotéticos".', duration:'50 min',
      videos:[{title:'Volatilidad: Dispersión, no Pérdida',duration:'12:00'},{title:'El VIX — Qué Mide y Qué NO Mide',duration:'13:00'},{title:'Picos de Miedo y Reversión a la Media',duration:'13:00'},{title:'Usarlo con Criterio, no a Ciegas',duration:'12:00'}]},
];

const PHASES = [
    { label:'🖥️ INTRO // RSU TERMINAL',              modules:[0] },
    { label:'📍 FASE 1 // ANÁLISIS TÉCNICO FUNDAMENTAL', modules:[1,2,3,4] },
    { label:'🔬 FASE 2 // LECTURA DE MERCADO AVANZADA',  modules:[5,6,7,8,17,24] },
    { label:'🎯 FASE 3 // ESTRATEGIA Y PLANIFICACIÓN',   modules:[9,10,11,18,19,23] },
    { label:'🚀 FASE 4 // EJECUCIÓN Y MENTALIDAD',       modules:[12,13,14,15] },
    { label:'🔄 FASE 5 // CICLO DE VIDA DEL PRECIO',     modules:[16] },
    { label:'🧮 FASE 6 // HERRAMIENTAS PROPIETARIAS RSU', modules:[20,21,22] },
];

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
    container.innerHTML = header() + phases() + outcome() + footer();
    attachCardListeners(container);
}

function header() {
    return `<div style="margin-bottom:2rem;">
        <div style="color:var(--color-accent);font-size:18px;letter-spacing:.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ACADEMY</div>
        <div style="color:var(--color-secondary);font-size:13px;letter-spacing:.15em;margin-bottom:4px;">TECHNICAL ANALYSIS BLUEPRINT</div>
        <div style="color:var(--color-muted);font-size:12px;">${MODULES.length} MÓDULOS // ACCESO COMPLETO // DE CERO A TRADER TÉCNICO</div>
    </div>`;
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
    const hasContent = Object.keys(LESSONS).some(k => k.startsWith(m.id + '-'));
    return `<div class="ac-card" data-id="${m.id}" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
        <div style="height:80px;background:linear-gradient(135deg,var(--color-surface),var(--color-bg,#0a0a0a));display:flex;align-items:center;justify-content:center;border-bottom:1px solid var(--color-border);position:relative;">
            <span style="font-size:2.2rem;">${m.icon}</span>
            ${hasContent ? `<span style="position:absolute;top:8px;right:8px;background:var(--color-accent);color:#000;font-size:9px;padding:2px 6px;border-radius:10px;font-family:monospace;letter-spacing:.05em;">LEER</span>` : ''}
        </div>
        <div style="padding:1rem;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <div style="background:var(--color-accent);color:#000;width:20px;height:20px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0;">${m.id}</div>
                <div style="color:var(--color-text);font-size:12px;letter-spacing:.04em;">${m.title.toUpperCase()}</div>
            </div>
            <div style="color:var(--color-muted);font-size:11px;line-height:1.5;margin-bottom:10px;">${m.description}</div>
            <div style="display:flex;gap:8px;font-size:10px;color:var(--color-muted);">
                <span>📹 ${m.videos.length} lecciones</span>
                <span>⏱ ${m.duration}</span>
            </div>
            <div class="ac-progress"><div class="ac-progress-bar" style="width:0%"></div></div>
        </div>
    </div>`;
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
        <div style="color:var(--color-muted);font-size:10px;letter-spacing:.15em;">[END OF TRANSMISSION // TECHNICAL_ANALYSIS_BLUEPRINT_v1.0]<br>[STATUS: ALL MODULES UNLOCKED // ACCESS: FULL]</div>
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

function renderModuleDetail(container, m) {
    injectStyles();
    const lessons = m.videos.map((v, i) => ({...v, key: `${m.id}-${i+1}`}));

    container.innerHTML = `
        <button id="btn-volver" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;margin-bottom:1.5rem;">← VOLVER</button>

        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.5rem;">
            <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;">
                <span style="font-size:2.5rem;">${m.icon}</span>
                <div>
                    <div style="color:var(--color-accent);font-size:18px;letter-spacing:.08em;">${m.title.toUpperCase()}</div>
                    <div style="color:var(--color-muted);font-size:12px;margin-top:2px;">📹 ${m.videos.length} lecciones · ⏱ ${m.duration}</div>
                </div>
            </div>
            <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${m.description}</div>
        </div>

        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">
            <div style="padding:10px 16px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:11px;letter-spacing:.08em;">CONTENIDO DEL MÓDULO</div>
            ${lessons.map((v, i) => {
                const hasLesson = !!LESSONS[v.key];
                return `<div class="ac-lesson-item" data-key="${v.key}" data-has="${hasLesson}">
                    <div class="ac-lesson-num" style="background:${hasLesson ? 'var(--color-accent)' : 'rgba(255,255,255,.05)'};color:${hasLesson ? '#000' : 'var(--color-muted)'};">
                        ${hasLesson ? '▶' : i+1}
                    </div>
                    <div style="flex:1;">
                        <div class="ac-lesson-title" style="color:${hasLesson ? 'var(--color-text)' : 'var(--color-muted)'};font-size:13px;">${v.title}</div>
                        ${hasLesson ? `<div style="color:var(--color-accent);font-size:10px;margin-top:2px;letter-spacing:.04em;">LECCIÓN DISPONIBLE</div>` : ''}
                    </div>
                    <div style="color:var(--color-muted);font-size:11px;">${v.duration}</div>
                </div>`;
            }).join('')}
        </div>

        ${quizBlock(m)}
    `;

    container.querySelector('#btn-volver').addEventListener('click', () => render(container));

    container.querySelectorAll('.ac-lesson-item').forEach(item => {
        if (item.getAttribute('data-has') !== 'true') return;
        item.addEventListener('click', () => {
            const key = item.getAttribute('data-key');
            const lesson = LESSONS[key];
            if (lesson) renderLesson(container, lesson, m);
        });
    });

    const quizBtn = container.querySelector('#btn-start-quiz');
    if (quizBtn) {
        quizBtn.addEventListener('click', () => {
            const quiz = QUIZZES[m.id];
            if (quiz) renderQuiz(container, quiz, m);
        });
    }
}

// ── BLOQUE DE ACCESO AL QUIZ (en la vista de módulo) ───────────────────────────

function quizBlock(m) {
    const quiz = QUIZZES[m.id];
    if (!quiz) return '';
    return `<div style="background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);padding:1.25rem;margin-top:1.5rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
        <div>
            <div style="color:var(--color-accent);font-size:12px;letter-spacing:.08em;margin-bottom:4px;">🎯 QUIZ DEL MÓDULO</div>
            <div style="color:var(--color-muted);font-size:11px;">${quiz.questions.length} preguntas · repite las que falles hasta acertarlas, sin límite de intentos</div>
        </div>
        <button id="btn-start-quiz" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;letter-spacing:.05em;flex-shrink:0;">EMPEZAR QUIZ →</button>
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
}

// ── VISTA DE LECCIÓN (contenido didáctico) ────────────────────────────────────

function renderLesson(container, lesson, module) {
    injectStyles();

    // Navegación entre lecciones del módulo
    const moduleKey = lesson.moduleId;
    const allLessons = module.videos.map((v,i) => ({key:`${moduleKey}-${i+1}`, title:v.title}));
    const currentIdx = lesson.lessonIndex;

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
                <span style="color:var(--color-muted);font-size:12px;">⏱ ${lesson.duration}</span>
                <span style="color:var(--color-accent);font-size:10px;background:rgba(0,255,173,.08);padding:2px 8px;border-radius:10px;border:1px solid rgba(0,255,173,.2);">MÓDULO ${module.id} // ${module.title.toUpperCase()}</span>
            </div>
        </div>

        <!-- Intro -->
        <div class="ac-intro">${lesson.intro}</div>

        <!-- Sections -->
        <div id="lesson-body">
            ${lesson.sections.map(sec => renderSection(sec)).join('')}
        </div>

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
        pill.addEventListener('click', () => {
            const key = pill.getAttribute('data-key');
            const l = LESSONS[key];
            if (l) renderLesson(container, l, module);
        });
    });

    container.querySelectorAll('.ac-lesson-nav').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-key');
            const l = LESSONS[key];
            if (l) renderLesson(container, l, module);
            else container.scrollTo && container.scrollTo(0,0);
        });
    });

    // Scroll top
    const main = document.getElementById('main');
    if (main) main.scrollTop = 0;
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
            const chartFn = CHARTS[block.id];
            if (!chartFn) return `<div style="color:var(--color-muted);font-size:11px;padding:8px;border:1px dashed var(--color-border);border-radius:4px;margin:12px 0;">Gráfico: ${block.id}</div>`;
            return `<div class="ac-chart">${chartFn()}</div>`;

        case 'divider':
            return `<hr style="border:none;border-top:1px solid var(--color-border);margin:20px 0;">`;

        default:
            return '';
    }
}