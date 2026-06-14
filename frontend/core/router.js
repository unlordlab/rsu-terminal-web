import { Tooltip } from '/components/tooltip.js';
import { initTheme } from '/core/theme.js';
import { renderSidebar } from '/components/sidebar.js';
import { renderTopbar } from '/components/topbar.js';
import { initWebSocket } from '/core/websocket.js';

const ROUTES = {
    '/':           () => import('/pages/dashboard.js'),
    '/market':     () => import('/pages/market.js'),
    '/cartera':    () => import('/pages/cartera.js'),
    '/rsrw':       () => import('/pages/rsrw.js'),
    '/spxl':       () => import('/pages/spxl.js'),
    '/btc-stratum': () => import('/pages/btc_stratum.js'),
    '/research':   () => import('/pages/research.js'),
    '/insider':    () => import('/pages/insider.js'),
    '/newsfeed':   () => import('/pages/newsfeed.js'),
    '/canslim':    () => import('/pages/canslim.js'),
    '/options':    () => import('/pages/options.js'),
    '/academy':    () => import('/pages/academy.js'),
    '/roadmap':    () => import('/pages/roadmap.js'),
    '/tesis':      () => import('/pages/tesis.js'),
    '/algoritmo':  () => import('/pages/algoritmo.js'),
    '/login':      () => import('/pages/login.js'),
    '/disclaimer': () => import('/pages/disclaimer.js'),
};

const TOKEN_KEY = 'rsu_token';

function isAuthenticated() {
    return !!sessionStorage.getItem(TOKEN_KEY);
}

export function navigate(path) {
    const cleanPath = path.split('?')[0];
    const protectedRoutes = ['/', '/market', '/cartera', '/rsrw', '/newsfeed', '/spxl', '/btc-stratum', '/roadmap', '/academy', '/tesis', '/options', '/research', '/disclaimer', '/canslim', '/algoritmo', '/insider'];
    const needsAuth = protectedRoutes.includes(cleanPath);
    if (needsAuth && !isAuthenticated()) {
        loadView('/login');
        history.pushState({}, '', '/login');
        return;
    }
    loadView(path);
    history.pushState({}, '', path);
}

async function loadView(path) {
    const cleanPath = path.split('?')[0];
    const view = document.getElementById('view');
    if (!view) return;
    view.innerHTML = '<p class="loading">Cargando</p>';
    try {
        const loader = ROUTES[cleanPath] || ROUTES['/'];
        const module = await loader();
        await module.render(view);
    } catch (err) {
        if (view) view.innerHTML = '<p style="color:var(--color-danger)">Error cargando módulo: ' + err.message + '</p>';
        console.error(err);
    }
}

initTheme();
const token = sessionStorage.getItem('rsu_token');
if (token) initWebSocket(token);
renderSidebar(document.getElementById('sidebar'), navigate);
renderTopbar(document.getElementById('topbar'), navigate);
navigate(location.pathname);
window.addEventListener('popstate', () => navigate(location.pathname));
window.__navigate = navigate;
window.__loadView = loadView;
Tooltip.init();

window.goToResearch = function(ticker) {
    if (!ticker) return;
    const path = '/research?ticker=' + ticker.toUpperCase();
    history.pushState({}, '', path);
    loadView(path);
};