const MODULES = [
    {
        id: 1, title: "Configuración de Gráficos", icon: "📊",
        description: "Configura correctamente tus gráficos en múltiples temporalidades. El análisis top-down empieza aquí.",
        chapters: 4, duration: "45 min",
        videos: [
            { title: "Gráfico Mensual — La visión macro",     duration: "12:00", url: "#" },
            { title: "Gráfico Semanal — La tendencia media",  duration: "11:00", url: "#" },
            { title: "Gráfico Diario — El setup operativo",   duration: "12:00", url: "#" },
            { title: "Velas Limpias — Sin ruido visual",      duration: "10:00", url: "#" },
        ]
    },
    {
        id: 2, title: "Estructura de Mercado", icon: "🏗️",
        description: "Identifica la tendencia antes de operar. Máximos y mínimos crecientes o decrecientes lo dicen todo.",
        chapters: 4, duration: "50 min",
        videos: [
            { title: "Máximos Crecientes — Señal alcista",    duration: "12:00", url: "#" },
            { title: "Mínimos Crecientes — Soporte dinámico", duration: "13:00", url: "#" },
            { title: "Máximos Decrecientes — Señal bajista",  duration: "12:00", url: "#" },
            { title: "Mínimos Decrecientes — Presión vendedora", duration: "13:00", url: "#" },
        ]
    },
    {
        id: 3, title: "Análisis de Tendencia", icon: "📈",
        description: "Nunca luches contra el mercado. Aprende a identificar y operar a favor de la tendencia dominante.",
        chapters: 4, duration: "55 min",
        videos: [
            { title: "Tendencia Alcista — Cómo montarla",     duration: "14:00", url: "#" },
            { title: "Tendencia Bajista — Cómo evitarla",     duration: "13:00", url: "#" },
            { title: "Rango Lateral — Paciencia obligatoria", duration: "14:00", url: "#" },
            { title: "Validación de Líneas de Tendencia",     duration: "14:00", url: "#" },
        ]
    },
    {
        id: 4, title: "Soporte y Resistencia", icon: "🧱",
        description: "Los niveles fuertes controlan el precio. Aprende a marcar zonas que realmente importan.",
        chapters: 4, duration: "1h",
        videos: [
            { title: "Soporte Fresco — Primera vez testeado",  duration: "15:00", url: "#" },
            { title: "Resistencia Mayor — Donde venden los grandes", duration: "15:00", url: "#" },
            { title: "Marcado de Zonas — Técnica profesional", duration: "15:00", url: "#" },
            { title: "Niveles con Múltiples Toques",           duration: "15:00", url: "#" },
        ]
    },
    {
        id: 5, title: "Oferta y Demanda", icon: "⚖️",
        description: "Las instituciones actúan en estas zonas. Aprende a identificar dónde el dinero inteligente opera.",
        chapters: 4, duration: "1h 10min",
        videos: [
            { title: "Zonas de Demanda — Dónde compran los grandes", duration: "18:00", url: "#" },
            { title: "Zonas de Oferta — Dónde venden los grandes",   duration: "17:00", url: "#" },
            { title: "Áreas de Rechazo — Señales de reacción",       duration: "17:00", url: "#" },
            { title: "Formación de Base — Acumulación institucional", duration: "18:00", url: "#" },
        ]
    },
    {
        id: 6, title: "Comportamiento de Velas", icon: "🕯️",
        description: "El cierre de la vela revela la verdad. Las formaciones de velas cuentan la historia del mercado.",
        chapters: 4, duration: "1h",
        videos: [
            { title: "Engulfing Alcista — Reversión potente",  duration: "15:00", url: "#" },
            { title: "Engulfing Bajista — Trampa para bulls",  duration: "15:00", url: "#" },
            { title: "Pin Bar — Rechazo de nivel clave",       duration: "15:00", url: "#" },
            { title: "Inside Bar — Compresión antes del movimiento", duration: "15:00", url: "#" },
        ]
    },
    {
        id: 7, title: "Rupturas de Precio", icon: "💥",
        description: "Confirma si es real o una trampa. Las rupturas falsas son la fuente de pérdidas más común.",
        chapters: 4, duration: "1h 5min",
        videos: [
            { title: "Ruptura de Rango — Cuándo creerla",       duration: "16:00", url: "#" },
            { title: "Ruptura de Tendencia — Cambio de régimen", duration: "16:00", url: "#" },
            { title: "Ruptura de Soporte — Señal bajista",       duration: "17:00", url: "#" },
            { title: "Entradas en Retest — La entrada profesional", duration: "16:00", url: "#" },
        ]
    },
    {
        id: 8, title: "Análisis de Volumen", icon: "📦",
        description: "El volumen confirma el precio. Sin volumen, el movimiento no tiene convicción real.",
        chapters: 4, duration: "1h",
        videos: [
            { title: "Volumen en Rupturas — Confirmación clave",   duration: "15:00", url: "#" },
            { title: "Bajo Volumen en Retrocesos — Señal alcista", duration: "15:00", url: "#" },
            { title: "Volumen Clímax — Agotamiento del movimiento", duration: "15:00", url: "#" },
            { title: "Participación Débil — Trampa a evitar",      duration: "15:00", url: "#" },
        ]
    },
    {
        id: 9, title: "Patrones de Gráfico", icon: "🔷",
        description: "Los patrones solo funcionan con contexto. Aprende a leerlos dentro de la tendencia dominante.",
        chapters: 4, duration: "1h 10min",
        videos: [
            { title: "Triángulo Ascendente — Continuación alcista",  duration: "17:00", url: "#" },
            { title: "Triángulo Descendente — Continuación bajista", duration: "17:00", url: "#" },
            { title: "Rectángulo — Rango operativo",                 duration: "18:00", url: "#" },
            { title: "Bandera y Asta — Impulso y continuación",      duration: "18:00", url: "#" },
        ]
    },
    {
        id: 10, title: "Alineación Multi-Temporalidad", icon: "🔭",
        description: "La alineación crea potencia. Cuando mensual, semanal y diario coinciden, la probabilidad dispara.",
        chapters: 4, duration: "1h 20min",
        videos: [
            { title: "Sesgo Mensual — La dirección macro",         duration: "20:00", url: "#" },
            { title: "Estructura Semanal — La tendencia real",     duration: "20:00", url: "#" },
            { title: "Setup Diario — El punto de entrada",         duration: "20:00", url: "#" },
            { title: "Trigger en TF Menor — La ejecución precisa", duration: "20:00", url: "#" },
        ]
    },
    {
        id: 11, title: "Planificación del Trade", icon: "📋",
        description: "Sin plan no hay trading. Define entrada, stop y objetivo antes de pulsar el botón.",
        chapters: 4, duration: "1h",
        videos: [
            { title: "Zona de Entrada — Dónde y por qué",       duration: "15:00", url: "#" },
            { title: "Stop Loss — No negociable",                duration: "15:00", url: "#" },
            { title: "Niveles Objetivo — Take Profit inteligente", duration: "15:00", url: "#" },
            { title: "Ratio Riesgo/Recompensa — El número que importa", duration: "15:00", url: "#" },
        ]
    },
    {
        id: 12, title: "Gestión del Riesgo", icon: "🛡️",
        description: "Sobrevive primero, gana después. La gestión del riesgo es lo único que te mantiene en el juego.",
        chapters: 4, duration: "1h 10min",
        videos: [
            { title: "Riesgo Fijo por Trade — La regla del 1-2%",  duration: "17:00", url: "#" },
            { title: "Sizing de Posición — Cálculo exacto",         duration: "18:00", url: "#" },
            { title: "Sin Revenge Trading — El mayor asesino",      duration: "17:00", url: "#" },
            { title: "Protección de Capital — Prioridad absoluta",  duration: "18:00", url: "#" },
        ]
    },
    {
        id: 13, title: "Ejecución", icon: "⚡",
        description: "La disciplina es el edge. Espera confirmación, sigue el plan y sal sin ego.",
        chapters: 4, duration: "1h",
        videos: [
            { title: "Esperar Confirmación — No adelantarse",      duration: "15:00", url: "#" },
            { title: "Evitar Entradas Prematuras — La trampa más cara", duration: "15:00", url: "#" },
            { title: "Seguir el Plan — Sin improvisar",            duration: "15:00", url: "#" },
            { title: "Salir Sin Ego — Cerrar cuando toca",         duration: "15:00", url: "#" },
        ]
    },
    {
        id: 14, title: "Trampas del Mercado", icon: "⚠️",
        description: "El mercado cobra matrícula. Aprende a reconocer las trampas más comunes antes de caer en ellas.",
        chapters: 4, duration: "1h 5min",
        videos: [
            { title: "Falsas Rupturas — Stop Hunt profesional",    duration: "16:00", url: "#" },
            { title: "Entradas Tardías — El FOMO que destroza",    duration: "16:00", url: "#" },
            { title: "Sobretrading — Menos es más",                duration: "17:00", url: "#" },
            { title: "Ignorar el Volumen — Error fatal",           duration: "16:00", url: "#" },
        ]
    },
    {
        id: 15, title: "Revisión Post-Trade", icon: "📓",
        description: "Journal o repite el dolor. La revisión sistemática es lo que separa a los traders rentables.",
        chapters: 4, duration: "50 min",
        videos: [
            { title: "Captura de Pantalla — Documenta todo",       duration: "12:00", url: "#" },
            { title: "Registro de Errores — Honestidad brutal",    duration: "13:00", url: "#" },
            { title: "Revisión del Setup — ¿Cumplí las reglas?",  duration: "13:00", url: "#" },
            { title: "Lecciones Aprendidas — El verdadero beneficio", duration: "12:00", url: "#" },
        ]
    },
];

const PHASES = [
    { label: "📍 FASE 1 // ANÁLISIS TÉCNICO FUNDAMENTAL", modules: [0, 1, 2, 3, 4] },
    { label: "🔬 FASE 2 // LECTURA DE MERCADO AVANZADA",  modules: [5, 6, 7, 8] },
    { label: "🎯 FASE 3 // ESTRATEGIA Y PLANIFICACIÓN",   modules: [9, 10, 11] },
    { label: "🚀 FASE 4 // EJECUCIÓN Y MENTALIDAD",       modules: [12, 13, 14] },
];

const OUTCOME = {
    icon:  "🏆",
    title: "RESULTADO FINAL",
    items: [
        { icon: "✅", text: "Setup Limpio — Sin ruido, sin dudas" },
        { icon: "⏳", text: "Entrada Paciente — Esperar la confirmación" },
        { icon: "🛡️", text: "Riesgo Controlado — Capital protegido" },
        { icon: "💰", text: "Salida Rentable — Ejecutar el plan" },
    ]
};

let activeModule = null;

export async function render(container) {
    activeModule = null;
    container.innerHTML = pageHeader() + phasesGrid() + outcomeSection() + pageFooter();
    setupCards(container);
}

function pageHeader() {
    return '<div style="margin-bottom:2rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ACADEMY</div>'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.15em;margin-bottom:4px;">TECHNICAL ANALYSIS BLUEPRINT</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">15 MÓDULOS // ACCESO COMPLETO // DE CERO A TRADER TÉCNICO</div>'
        + '</div>';
}

function phasesGrid() {
    return PHASES.map(phase => {
        const phaseModules = phase.modules.map(i => MODULES[i]).filter(Boolean);
        return '<div style="margin-bottom:2rem;">'
            + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1rem;">'
            + phase.label + '</div>'
            + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;">'
            + phaseModules.map(m => moduleCard(m)).join('')
            + '</div>'
            + '</div>';
    }).join('<div style="border-top:1px solid var(--color-border);margin:1.5rem 0;"></div>');
}

function moduleCard(m) {
    return '<div class="academy-card" data-id="' + m.id + '" style="'
        + 'background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);'
        + 'overflow:hidden;cursor:pointer;transition:all var(--transition);">'

        + '<div style="height:90px;background:linear-gradient(135deg,var(--color-surface),var(--color-bg,#0a0a0a));'
        + 'display:flex;align-items:center;justify-content:center;border-bottom:1px solid var(--color-border);">'
        + '<span style="font-size:2.5rem;">' + m.icon + '</span>'
        + '</div>'

        + '<div style="padding:1rem;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<div style="background:var(--color-accent);color:#000;width:22px;height:22px;border-radius:3px;'
        + 'display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500;flex-shrink:0;">'
        + m.id + '</div>'
        + '<div style="color:var(--color-text);font-size:12px;font-weight:500;letter-spacing:0.04em;">' + m.title.toUpperCase() + '</div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;line-height:1.5;margin-bottom:10px;">' + m.description + '</div>'
        + '<div style="display:flex;gap:8px;font-size:10px;color:var(--color-muted);margin-bottom:10px;">'
        + '<span>📹 ' + m.videos.length + ' vídeos</span>'
        + '<span>⏱ ' + m.duration + '</span>'
        + '</div>'
        + '<div style="background:var(--color-bg,#0a0a0a);height:3px;border-radius:2px;overflow:hidden;">'
        + '<div style="height:100%;width:0%;background:var(--color-accent);border-radius:2px;"></div>'
        + '</div>'
        + '</div>'
        + '</div>';
}

function outcomeSection() {
    return '<div style="border-top:1px solid var(--color-border);margin-top:2rem;padding-top:2rem;">'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1.5rem;">'
        + '🏆 RESULTADO FINAL // TECHNICAL ANALYSIS BLUEPRINT</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;">'
        + OUTCOME.items.map(item =>
            '<div style="background:rgba(0,255,173,0.05);border:1px solid var(--color-accent);border-radius:var(--radius);padding:1.25rem;text-align:center;">'
            + '<div style="font-size:2rem;margin-bottom:8px;">' + item.icon + '</div>'
            + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.05em;">' + item.text + '</div>'
            + '</div>'
        ).join('')
        + '</div>'
        + '</div>';
}

function pageFooter() {
    return '<div style="text-align:center;margin-top:3rem;padding:1.5rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.15em;">'
        + '[END OF TRANSMISSION // TECHNICAL_ANALYSIS_BLUEPRINT_v1.0]<br>'
        + '[STATUS: ALL MODULES UNLOCKED // ACCESS: FULL]'
        + '</div>'
        + '</div>';
}

function setupCards(container) {
    const style = document.createElement('style');
    style.textContent = '.academy-card:hover { border-color: var(--color-accent) !important; transform: translateY(-2px); box-shadow: 0 0 20px rgba(0,255,173,0.1); }';
    document.head.appendChild(style);

    container.querySelectorAll('.academy-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = parseInt(card.getAttribute('data-id'));
            const m  = MODULES.find(x => x.id === id);
            if (m) renderModuleDetail(container, m);
        });
    });
}

function renderModuleDetail(container, m) {
    container.innerHTML = '<button id="btn-volver-academy" style="'
        + 'background:transparent;border:1px solid var(--color-border);color:var(--color-muted);'
        + 'border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;'
        + 'cursor:pointer;margin-bottom:1.5rem;">← VOLVER</button>'

        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.5rem;">'
        + '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem;">'
        + '<span style="font-size:2.5rem;">' + m.icon + '</span>'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:20px;letter-spacing:0.1em;">' + m.title.toUpperCase() + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-top:2px;">'
        + '📹 ' + m.videos.length + ' vídeos · ⏱ ' + m.duration
        + '</div>'
        + '</div>'
        + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;line-height:1.7;">' + m.description + '</div>'
        + '</div>'

        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">CONTENIDO DEL MÓDULO</div>'
        + m.videos.map((v, i) => {
            const hasUrl = v.url && v.url !== '#';
            return '<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--color-border);">'
                + '<div style="width:28px;height:28px;background:' + (hasUrl ? 'var(--color-accent)' : 'var(--color-surface2,#1a1a1a)') + ';'
                + 'color:' + (hasUrl ? '#000' : 'var(--color-muted)') + ';border-radius:50%;'
                + 'display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;">'
                + (hasUrl ? '▶' : (i+1)) + '</div>'
                + '<div style="flex:1;">'
                + (hasUrl
                    ? '<a href="' + v.url + '" target="_blank" style="color:var(--color-text);font-size:13px;text-decoration:none;">' + v.title + '</a>'
                    : '<span style="color:var(--color-muted);font-size:13px;">' + v.title + '</span>')
                + '</div>'
                + '<div style="color:var(--color-muted);font-size:11px;flex-shrink:0;">' + v.duration + '</div>'
                + '</div>';
        }).join('')
        + '</div>';

    container.querySelector('#btn-volver-academy')?.addEventListener('click', () => {
        render(container);
    });
}