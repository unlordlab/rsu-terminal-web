export async function render(container) {
    container.innerHTML = placeholder('CANSLIM', 'Screener · En construcción');
}
function placeholder(title, desc) {
    return `
        <div style="margin-bottom: 2rem;">
            <div style="
                color: var(--color-accent);
                font-size: 18px;
                letter-spacing: 0.1em;
                text-shadow: var(--glow-text);
                margin-bottom: 4px;
            ">${title}</div>
            <div style="color: var(--color-muted); font-size: 12px;">${desc}</div>
        </div>
        <div style="
            border: 1px dashed var(--color-border);
            border-radius: var(--radius);
            padding: 3rem;
            text-align: center;
            color: var(--color-muted);
            font-size: 13px;
        ">
            Módulo pendiente de migración desde Streamlit
        </div>
    `;
}
