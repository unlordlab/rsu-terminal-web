import { api } from '/core/api.js';

export async function render(container) {
    container.innerHTML = `
        <div style="margin-bottom: 2rem;">
            <div style="
                color: var(--color-accent);
                font-size: 18px;
                letter-spacing: 0.1em;
                text-shadow: var(--glow-text);
                margin-bottom: 4px;
            ">DASHBOARD</div>
            <div style="color: var(--color-muted); font-size: 12px;">
                Bienvenido a RSU Terminal v2.0
            </div>
        </div>

        <div id="health-card" style="
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            font-size: 13px;
            color: var(--color-muted);
        ">Comprobando servidor...</div>

        <div style="
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
        ">
            ${modules.map(m => `
                <div
                    class="module-card"
                    data-path="${m.path}"
                    style="
                        background: var(--color-surface);
                        border: 1px solid var(--color-border);
                        border-radius: var(--radius);
                        padding: 1.25rem;
                        cursor: pointer;
                        transition: all var(--transition);
                    "
                >
                    <div style="
                        color: var(--color-accent);
                        font-size: 20px;
                        margin-bottom: 8px;
                    ">${m.icon}</div>
                    <div style="
                        color: var(--color-text);
                        font-size: 13px;
                        margin-bottom: 4px;
                        letter-spacing: 0.05em;
                    ">${m.label}</div>
                    <div style="
                        color: var(--color-muted);
                        font-size: 11px;
                    ">${m.desc}</div>
                </div>
            `).join('')}
        </div>
    `;

    // Hover en cards
    const style = document.createElement('style');
    style.textContent = `
        .module-card:hover {
            border-color: var(--color-accent) !important;
            background: var(--color-surface2) !important;
        }
    `;
    document.head.appendChild(style);

    // Click en cards → navegar
    container.querySelectorAll('.module-card').forEach(card => {
        card.addEventListener('click', () => {
            window.__navigate(card.getAttribute('data-path'));
        });
    });

    // Health check al servidor
    try {
        const health = await fetch('/health').then(r => r.json());
        const card = container.querySelector('#health-card');
        if (card) {
            card.style.borderColor = 'var(--color-success)';
            card.innerHTML = `
                <span style="color: var(--color-success);">● SERVIDOR ONLINE</span>
                <span style="margin-left: 1rem;">${health.app}</span>
            `;
        }
    } catch {
        const card = container.querySelector('#health-card');
        if (card) {
            card.style.borderColor = 'var(--color-danger)';
            card.innerHTML = `<span style="color: var(--color-danger);">✗ SERVIDOR OFFLINE</span>`;
        }
    }
}

const modules = [
    { path: '/market',   icon: '◈', label: 'MARKET',    desc: 'Dashboard de mercado' },
    { path: '/cartera',  icon: '◎', label: 'CARTERA',   desc: 'Portfolio tracker' },
    { path: '/rsrw',     icon: '◆', label: 'RS/RW',     desc: 'Scanner de fuerza relativa' },
    { path: '/spxl',     icon: '▲', label: 'SPXL',      desc: 'Estrategia DCA apalancada' },
    { path: '/research', icon: '◉', label: 'RESEARCH',  desc: 'Análisis con IA' },
    { path: '/canslim',  icon: '◈', label: 'CANSLIM',   desc: 'Screener CAN SLIM' },
];
