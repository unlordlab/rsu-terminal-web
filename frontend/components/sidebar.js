const NAV_ITEMS = [
    { path: '/',         label: 'Dashboard',  icon: '⌂' },
    { path: '/market',   label: 'Market',     icon: '◈' },
    { path: '/cartera',  label: 'Cartera',    icon: '◎' },
    { path: '/rsrw',     label: 'RS/RW',      icon: '◆' },
    { path: '/spxl',     label: 'SPXL',       icon: '▲' },
    { path: '/research', label: 'Research',   icon: '◉' },
    { path: '/canslim',  label: 'CANSLIM',    icon: '◈' },
];

export function renderSidebar(container, navigate) {
    container.innerHTML = `
        <div style="
            padding: 1.25rem 1rem 1rem;
            border-bottom: 1px solid var(--color-border);
            margin-bottom: 0.5rem;
        ">
            <div style="
                color: var(--color-accent);
                font-size: 16px;
                letter-spacing: 0.1em;
                text-shadow: var(--glow-text);
            ">RSU TERMINAL</div>
            <div style="color: var(--color-muted); font-size: 11px; margin-top: 2px;">
                v2.0 · FastAPI
            </div>
        </div>

        <nav style="padding: 0.5rem 0;">
            ${NAV_ITEMS.map(item => `
                
                    href="${item.path}"
                    class="nav-item"
                    data-path="${item.path}"
                    style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        padding: 0.6rem 1rem;
                        color: var(--color-muted);
                        text-decoration: none;
                        transition: all var(--transition);
                        border-left: 2px solid transparent;
                        font-size: 13px;
                        cursor: pointer;
                    "
                >
                    <span style="font-size: 14px; width: 16px; text-align: center;">
                        ${item.icon}
                    </span>
                    ${item.label}
                </a>
            `).join('')}
        </nav>
    `;

    // Estilos hover y activo
    const style = document.createElement('style');
    style.textContent = `
        .nav-item:hover {
            color: var(--color-text) !important;
            background: var(--color-surface2);
        }
        .nav-item.active {
            color: var(--color-accent) !important;
            border-left-color: var(--color-accent) !important;
            background: var(--color-surface2);
            text-shadow: var(--glow-text);
        }
    `;
    document.head.appendChild(style);

    // Click handler
    container.querySelectorAll('.nav-item').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const path = link.getAttribute('data-path');
            setActive(path);
            navigate(path);
        });
    });

    // Marcar activo según ruta actual
    setActive(location.pathname);

    // Actualizar activo cuando cambia la ruta
    document.addEventListener('routechange', e => setActive(e.detail.path));
}

function setActive(path) {
    document.querySelectorAll('.nav-item').forEach(link => {
        link.classList.toggle('active', link.getAttribute('data-path') === path);
    });
}
