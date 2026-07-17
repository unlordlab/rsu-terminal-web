const TEAM = [
    {
        img: '/assets/team/unlord.jpg',
        nombre: 'unlord',
        rol: 'CEO & Fundador',
        icon: '👑',
        bio: 'Fundador, arquitecto y, a partir de las 3 de la madrugada, también soporte técnico de emergencia. Responsable de que la terminal exista, de que casi siempre esté en pie, y de discutir con la IA durante horas sobre por qué un proxy residencial no era la solución.',
        estado: 'ACTIVO',
        estadoColor: '#3ecf8e',
    },
    {
        img: '/assets/team/gael.jpg',
        nombre: 'Gael',
        rol: '"El Bull" — Agente de Tesis Alcistas',
        icon: '🐂',
        bio: 'Escanea el mercado buscando activos que cumplen criterios CANSLIM y han sufrido una corrección. Optimista compulsivo — ve potencial de rerating en casi todo lo que analiza. Necesita que unlord revise y apruebe cada informe antes de publicarlo, por el bien de todos.',
        estado: 'EN SERVICIO',
        estadoColor: '#3ecf8e',
    },
    {
        img: '/assets/team/elia.jpg',
        nombre: 'Elia',
        rol: 'Revisión y ampliación de Academy',
        icon: '🎓',
        bio: 'Encargada de revisar y ampliar el contenido educativo de Academy — lecciones, quizzes y gráficos. Su misión: que nadie entre confundido y salga todavía más confundido. Se toma muy en serio que las explicaciones sean claras, aunque el mercado no lo sea.',
        estado: 'EN SERVICIO',
        estadoColor: '#3ecf8e',
    },
    {
        img: '/assets/team/laia.jpg',
        nombre: 'Laia',
        rol: 'Comité de Ética — cree en serio en el Manifiesto',
        icon: '⚖️',
        bio: 'Activista, utópica, con un punto de mala leche y principios insobornables. No genera nada — cuestiona lo que ya existe, incluido el criterio de unlord. Audita el lenguaje de hype en las tesis de Gael y si las aprobaciones se sesgan hacia la comodidad. No le debe lealtad a nadie del equipo.',
        estado: 'EN SERVICIO',
        estadoColor: '#3ecf8e',
    },
];

export async function render(container) {
    container.innerHTML = pageContent();
}

function pageContent() {
    return header() + teamGrid() + footer();
}

function header() {
    return `
        <div style="margin-bottom:2rem;text-align:center;">
            <div style="color:var(--color-muted);font-size:11px;letter-spacing:0.15em;margin-bottom:8px;">[PERSONNEL FILE // CLEARANCE: PUBLIC]</div>
            <div style="color:var(--color-accent);font-size:24px;letter-spacing:0.12em;text-shadow:var(--glow-text);margin-bottom:6px;">👥 EQUIPO RSU</div>
            <div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.2em;">HUMANOS Y AGENTES QUE HACEN FUNCIONAR ESTO</div>
        </div>
        <p style="color:var(--color-muted);text-align:center;max-width:640px;margin:0 auto 2.5rem;font-size:13px;line-height:1.6;">
            Detrás de cada módulo hay alguien (o algo) responsable. Algunos son humanos con demasiado café encima,
            otros son agentes de IA con instrucciones muy concretas y ninguna autoridad para publicar nada sin permiso.
        </p>
    `;
}

function teamGrid() {
    return `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem;max-width:1000px;margin:0 auto;">
            ${TEAM.map(memberCard).join('')}
        </div>
    `;
}

function memberCard(m) {
    return `
        <div style="
            background:var(--color-surface);
            border:1px solid var(--color-border);
            border-radius:var(--radius-lg);
            overflow:hidden;
            transition:border-color 0.2s;
        ">
            <div style="position:relative;aspect-ratio:1/1;overflow:hidden;background:var(--color-surface2);">
                <img src="${m.img}" alt="${m.nombre}" style="width:100%;height:100%;object-fit:cover;display:block;" />
                <div style="
                    position:absolute;top:8px;right:8px;
                    background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);
                    border:1px solid ${m.estadoColor}55;
                    color:${m.estadoColor};
                    font-size:10px;letter-spacing:0.08em;
                    padding:3px 8px;border-radius:3px;
                    font-family:var(--font-mono);
                ">${m.estado}</div>
            </div>
            <div style="padding:1rem;">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
                    <span style="font-size:16px;">${m.icon}</span>
                    <span style="color:var(--color-accent);font-size:16px;letter-spacing:0.05em;font-weight:600;">${m.nombre}</span>
                </div>
                <div style="color:var(--color-secondary);font-size:11px;letter-spacing:0.08em;margin-bottom:10px;">${m.rol}</div>
                <p style="color:var(--color-muted);font-size:12px;line-height:1.6;margin:0;">${m.bio}</p>
            </div>
        </div>
    `;
}

function footer() {
    return `
        <p style="color:var(--color-muted);text-align:center;font-size:11px;margin-top:2.5rem;letter-spacing:0.05em;">
            [MÁS FICHAS EN CAMINO // EL EQUIPO CRECE SEGÚN SE CONSTRUYEN NUEVOS AGENTES]
        </p>
    `;
}