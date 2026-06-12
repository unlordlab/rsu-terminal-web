import { cycleTheme, getCurrentTheme } from '/core/theme.js';

export function renderTopbar(container, navigate) {
    container.innerHTML = `
        <div style="flex: 1; color: var(--color-muted); font-size: 12px;" id="topbar-breadcrumb">
            /dashboard
        </div>

        <div style="display: flex; align-items: center; gap: 1rem;">
            <span id="market-status" style="font-size: 12px; color: var(--color-muted);">
                ● MARKET
            </span>

            <button
                id="theme-toggle"
                title="Cambiar tema"
                style="
                    background: none;
                    border: 1px solid var(--color-border);
                    color: var(--color-muted);
                    padding: 4px 10px;
                    border-radius: var(--radius);
                    cursor: pointer;
                    font-family: var(--font-mono);
                    font-size: 11px;
                    transition: all var(--transition);
                "
            >THEME</button>

            <button
                id="logout-btn"
                style="
                    background: none;
                    border: 1px solid var(--color-border);
                    color: var(--color-muted);
                    padding: 4px 10px;
                    border-radius: var(--radius);
                    cursor: pointer;
                    font-family: var(--font-mono);
                    font-size: 11px;
                    transition: all var(--transition);
                "
            >LOGOUT</button>
        </div>
    `;

    // Theme toggle
    container.querySelector('#theme-toggle').addEventListener('click', () => {
        cycleTheme();
        updateThemeLabel();
    });

    // Logout
    container.querySelector('#logout-btn').addEventListener('click', () => {
        sessionStorage.removeItem('rsu_token');
        navigate('/login');
    });

    // Actualizar breadcrumb cuando cambia la ruta
    window.addEventListener('popstate', updateBreadcrumb);
    document.addEventListener('routechange', e => updateBreadcrumb(e.detail?.path));

    function updateThemeLabel() {
        const btn = container.querySelector('#theme-toggle');
        if (btn) btn.textContent = getCurrentTheme().toUpperCase();
    }

    function updateBreadcrumb(path) {
        const crumb = container.querySelector('#topbar-breadcrumb');
        if (crumb) crumb.textContent = typeof path === 'string' ? path : location.pathname;
    }

    updateThemeLabel();
}
