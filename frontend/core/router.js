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

// Interceptor global de fetch: cubre dos casos transversales a toda la app,
// sin tener que modificar cada página individualmente:
//
// 1) 401 → token inválido/expirado: limpia sesión y redirige a /login.
// 2) 429 → rate limit excedido: reescribe la respuesta para que toda página
//    que haga `data.ok` / `data.error` reciba un objeto uniforme con
//    `rate_limited: true` y el tiempo de espera real, en vez de un "Sin datos"
//    genérico que no explica qué pasó. Esto cubre las páginas (cartera.js,
//    market.js, canslim.js) que usan su propio helper authHeader() local en
//    vez de core/api.js.
const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await _originalFetch.apply(this, args);
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';

    if (response.status === 401 && url.includes('/api/v1/') && location.pathname !== '/login') {
        sessionStorage.removeItem(TOKEN_KEY);
        navigate('/login');
        return response;
    }

    if (response.status === 429 && url.includes('/api/v1/')) {
        let retryIn = 60, message = 'Demasiadas peticiones. Espera unos segundos e inténtalo de nuevo.';
        try {
            const body = await response.clone().json();
            const detail = body.detail || body;
            if (detail.retry_in) retryIn = detail.retry_in;
            if (detail.message)  message  = detail.message;
        } catch (e) { /* respuesta no-JSON, usar valores por defecto */ }

        const uniformBody = JSON.stringify({
            ok: false,
            rate_limited: true,
            retry_in: retryIn,
            error: message,
        });
        return new Response(uniformBody, {
            status: 429,
            statusText: response.statusText,
            headers: response.headers,
        });
    }

    return response;
};

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