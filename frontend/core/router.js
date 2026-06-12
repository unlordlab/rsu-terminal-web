import { initTheme } from '/core/theme.js';
import { renderSidebar } from '/components/sidebar.js';
import { renderTopbar } from '/components/topbar.js';

const ROUTES = {
    '/':         () => import('/pages/dashboard.js'),
    '/market':   () => import('/pages/market.js'),
    '/cartera':  () => import('/pages/cartera.js'),
    '/rsrw':     () => import('/pages/rsrw.js'),
    '/spxl':     () => import('/pages/spxl.js'),
    '/research': () => import('/pages/research.js'),
    '/canslim':  () => import('/pages/canslim.js'),
    '/login':    () => import('/pages/login.js'),
};

const TOKEN_KEY = 'rsu_token';

function isAuthenticated() {
    return !!sessionStorage.getItem(TOKEN_KEY);
}

export function navigate(path) {
    const protectedRoutes = ['/', '/market', '/cartera', '/rsrw', '/spxl', '/research', '/canslim'];
    const needsAuth = protectedRoutes.includes(path);

    if (needsAuth && !isAuthenticated()) {
        loadView('/login');
        history.pushState({}, '', '/login');
        return;
    }

    loadView(path);
    history.pushState({}, '', path);
}

async function loadView(path) {
    const view = document.getElementById('view');
    view.innerHTML = '<p class="loading">Cargando</p>';

    try {
        const loader = ROUTES[path] || ROUTES['/'];
        const module = await loader();
        await module.render(view);
    } catch (err) {
        view.innerHTML = `<p style="color:var(--color-danger)">Error cargando módulo: ${err.message}</p>`;
        console.error(err);
    }
}

// Arranque
initTheme();
renderSidebar(document.getElementById('sidebar'), navigate);
renderTopbar(document.getElementById('topbar'), navigate);

// Ruta inicial
navigate(location.pathname);

// Botones atrás/adelante del browser
window.addEventListener('popstate', () => navigate(location.pathname));

// Exponer navigate globalmente para usarlo desde cualquier módulo
window.__navigate = navigate;
