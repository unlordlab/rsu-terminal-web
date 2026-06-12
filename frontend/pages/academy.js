const MODULES = [
    {
        id: 1, title: "Bienvenida", icon: "👋",
        description: "Introducción al programa y configuración inicial de tu espacio de trabajo.",
        chapters: 3, duration: "45 min",
        videos: [
            { title: "Bienvenida al Programa",    duration: "15:30", url: "https://www.youtube.com/watch?v=6kjnyouSnHs" },
            { title: "Configuración del Entorno", duration: "18:45", url: "https://www.youtube.com/watch?v=WSvGAHejvgU" },
            { title: "Roadmap del Curso",         duration: "11:20", url: "#" },
        ]
    },
    {
        id: 2, title: "Inicio Trading Lab", icon: "🚀",
        description: "Primeros pasos en el Trading Lab. Entendiendo la plataforma y herramientas básicas.",
        chapters: 4, duration: "1h 20min",
        videos: [
            { title: "Introducción al Trading Lab", duration: "20:00", url: "#" },
            { title: "Herramientas Esenciales",     duration: "25:30", url: "#" },
            { title: "Tu Primera Operación",        duration: "22:15", url: "#" },
            { title: "Checklist Pre-Trading",       duration: "12:45", url: "#" },
        ]
    },
    {
        id: 3, title: "Introducción", icon: "📚",
        description: "Conceptos fundamentales del trading: mercados, instrumentos y terminología.",
        chapters: 5, duration: "2h 10min",
        videos: [
            { title: "¿Qué es el Trading?",       duration: "25:00", url: "#" },
            { title: "Tipos de Mercados",          duration: "30:00", url: "#" },
            { title: "Instrumentos Financieros",   duration: "28:00", url: "#" },
            { title: "Terminología Básica",        duration: "22:00", url: "#" },
            { title: "Psicología del Trader",      duration: "25:00", url: "#" },
        ]
    },
    {
        id: 4, title: "Lab Station", icon: "🧪",
        description: "Configuración avanzada de estaciones de trabajo para análisis técnico.",
        chapters: 4, duration: "1h 45min",
        videos: [
            { title: "Setup Profesional",              duration: "28:00", url: "#" },
            { title: "Pantallas y Layouts",            duration: "22:00", url: "#" },
            { title: "Atajos y Productividad",         duration: "25:00", url: "#" },
            { title: "Gestión de Múltiples Monitores", duration: "30:00", url: "#" },
        ]
    },
    {
        id: 5, title: "Lab Foundation", icon: "🏗️",
        description: "Fundamentos del análisis técnico: soportes, resistencias y tendencias.",
        chapters: 6, duration: "3h 30min",
        videos: [
            { title: "Teoría de Dow",          duration: "35:00", url: "#" },
            { title: "Soportes y Resistencias",duration: "40:00", url: "#" },
            { title: "Líneas de Tendencia",    duration: "35:00", url: "#" },
            { title: "Canales y Patrones",     duration: "45:00", url: "#" },
            { title: "Velas Japonesas I",      duration: "35:00", url: "#" },
            { title: "Velas Japonesas II",     duration: "30:00", url: "#" },
        ]
    },
    {
        id: 6, title: "Advanced Foundation", icon: "🔬",
        description: "Conceptos avanzados: indicadores, osciladores y sistemas de trading.",
        chapters: 5, duration: "4h 15min",
        videos: [
            { title: "Medias Móviles Avanzadas",  duration: "50:00", url: "#" },
            { title: "RSI y Estocástico",         duration: "45:00", url: "#" },
            { title: "MACD y Divergencias",       duration: "55:00", url: "#" },
            { title: "Volumen y Perfil",          duration: "45:00", url: "#" },
            { title: "Construcción de Sistemas",  duration: "60:00", url: "#" },
        ]
    },
    {
        id: 7, title: "Multi-TimeFrame Análisis", icon: "📊",
        description: "Análisis multi-temporal: sincronización de timeframes y confluencias.",
        chapters: 4, duration: "2h 45min",
        videos: [
            { title: "Teoría de Timeframes",  duration: "40:00", url: "#" },
            { title: "Top-Down Analysis",     duration: "45:00", url: "#" },
            { title: "Confluencias y Zonas",  duration: "40:00", url: "#" },
            { title: "Casos Prácticos MTF",   duration: "50:00", url: "#" },
        ]
    },
    {
        id: 10, title: "Manejo de la Posición", icon: "🎯",
        description: "Gestión activa de trades: stops, targets y ajustes en vivo.",
        chapters: 5, duration: "3h 20min",
        videos: [
            { title: "Stop Loss Inteligente",  duration: "40:00", url: "#" },
            { title: "Take Profit y RRR",      duration: "35:00", url: "#" },
            { title: "Breakeven y Trailing",   duration: "45:00", url: "#" },
            { title: "Escalado de Posiciones", duration: "40:00", url: "#" },
            { title: "Gestión en Vivo",        duration: "50:00", url: "#" },
        ]
    },
    {
        id: 11, title: "Gestión Monetaria", icon: "💰",
        description: "Gestión de capital: sizing, riesgo por trade y curva de equity.",
        chapters: 4, duration: "2h 30min",
        videos: [
            { title: "Regla del 1-2%",          duration: "35:00", url: "#" },
            { title: "Position Sizing",          duration: "40:00", url: "#" },
            { title: "Drawdown y Recuperación",  duration: "35:00", url: "#" },
            { title: "Optimización de Curva",    duration: "40:00", url: "#" },
        ]
    },
    {
        id: 12, title: "Creación de Watchlist", icon: "📋",
        description: "Construcción y mantenimiento de listas de seguimiento efectivas.",
        chapters: 3, duration: "1h 45min",
        videos: [
            { title: "Criterios de Selección", duration: "35:00", url: "#" },
            { title: "Scanning y Filtrado",    duration: "35:00", url: "#" },
            { title: "Mantenimiento Diario",   duration: "35:00", url: "#" },
        ]
    },
    {
        id: 13, title: "Trader Goals", icon: "🎖️",
        description: "Planificación de objetivos y desarrollo de disciplina de trading.",
        chapters: 3, duration: "1h 30min",
        videos: [
            { title: "SMART Goals",            duration: "30:00", url: "#" },
            { title: "Trading Plan Personal",  duration: "35:00", url: "#" },
            { title: "Review y Mejora Continua", duration: "25:00", url: "#" },
        ]
    },
    {
        id: 14, title: "Despedida", icon: "🎓",
        description: "Cierre del programa y próximos pasos en tu carrera de trading.",
        chapters: 2, duration: "45 min",
        videos: [
            { title: "Resumen y Checklist Final", duration: "25:00", url: "#" },
            { title: "Comunidad y Recursos",      duration: "20:00", url: "#" },
        ]
    },
];

const PHASES = [
    { label: "📍 FASE 1 // FUNDAMENTOS",          modules: [0,1,2]   },
    { label: "🔬 FASE 2 // LABORATORIO Y TÉCNICO", modules: [3,4,5]   },
    { label: "🎯 FASE 3 // ESTRATEGIA AVANZADA",  modules: [6,7]     },
    { label: "🚀 FASE 4 // ESPECIALIZACIÓN",       modules: [8,9,10,11] },
];

let activeModule = null;

export async function render(container) {
    activeModule = null;
    container.innerHTML = pageHeader() + phasesGrid() + pageFooter();
    setupCards(container);
}

function pageHeader() {
    return '<div style="margin-bottom:2rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ACADEMY</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">PROTOCOLO DE FORMACIÓN // 14 MÓDULOS // ACCESO COMPLETO</div>'
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

        // Thumbnail
        + '<div style="height:110px;background:linear-gradient(135deg,var(--color-surface),var(--color-bg,#0a0a0a));'
        + 'display:flex;align-items:center;justify-content:center;border-bottom:1px solid var(--color-border);">'
        + '<span style="font-size:3rem;">' + m.icon + '</span>'
        + '</div>'

        // Body
        + '<div style="padding:1rem;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<div style="background:var(--color-accent);color:#000;width:22px;height:22px;border-radius:3px;'
        + 'display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500;flex-shrink:0;">'
        + m.id + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;font-weight:500;letter-spacing:0.05em;">' + m.title.toUpperCase() + '</div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:11px;line-height:1.5;margin-bottom:10px;">' + m.description + '</div>'
        + '<div style="display:flex;gap:8px;font-size:10px;color:var(--color-muted);margin-bottom:10px;">'
        + '<span>📹 ' + m.videos.length + ' vídeos</span>'
        + '<span>⏱ ' + m.duration + '</span>'
        + '</div>'

        // Progress bar
        + '<div style="background:var(--color-bg,#0a0a0a);height:3px;border-radius:2px;overflow:hidden;">'
        + '<div style="height:100%;width:0%;background:var(--color-accent);border-radius:2px;"></div>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:4px;">0% completado</div>'

        + '</div>'
        + '</div>';
}

function pageFooter() {
    return '<div style="text-align:center;margin-top:3rem;padding:1.5rem;border-top:1px solid var(--color-border);">'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.15em;">'
        + '[END OF TRANSMISSION // RSU_ACADEMY_v2.0]<br>'
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

        // Header módulo
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.5rem;">'
        + '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem;">'
        + '<span style="font-size:2.5rem;">' + m.icon + '</span>'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:20px;letter-spacing:0.1em;">' + m.title.toUpperCase() + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-top:2px;">'
        + '📹 ' + m.videos.length + ' vídeos · ⏱ ' + m.duration + ' · 📚 ' + m.chapters + ' capítulos'
        + '</div>'
        + '</div>'
        + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;line-height:1.6;">' + m.description + '</div>'
        + '</div>'

        // Lista de vídeos
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