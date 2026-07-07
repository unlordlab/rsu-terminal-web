import { Tooltip } from '/components/tooltip.js';
import { initTheme } from '/core/theme.js';
import { renderSidebar, setActiveNavItem } from '/components/sidebar.js';
import { renderTopbar } from '/components/topbar.js';
import { initWebSocket } from '/core/websocket.js';
import { api, setSession, getToken } from '/core/api.js';

const ROUTES = {
    '/':           () => import('/pages/dashboard.js'),
    '/manifiesto': () => import('/pages/manifest.js'),
    '/market':     () => import('/pages/market.js'),
    '/cartera':    () => import('/pages/cartera.js'),
    '/rsrw':       () => import('/pages/rsrw.js'),
    '/scanner':    () => import('/pages/scanner.js'),
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
    '/register':   () => import('/pages/register.js'),
    '/admin':      () => import('/pages/admin.js'),
    '/disclaimer': () => import('/pages/disclaimer.js'),
};

const TOKEN_KEY = 'rsu_token';

function isAuthenticated() {
    return !!getToken();
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

    if (response.status === 401 && url.includes('/api/v1/') && !url.includes('/auth/admin') && location.pathname !== '/login') {
        localStorage.removeItem(TOKEN_KEY);
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

// ---------------------------------------------------------------------------
// Navegación con "volver" que preserva el estado de la página anterior.
//
// Cada página se renderiza dentro de su propio <div> (en vez de pisar
// siempre el mismo contenedor). Al navegar a una página nueva, la página
// actual no se destruye: se oculta y se guarda como "página anterior" junto
// con su scroll. Si el usuario pulsa "Volver" (o el atrás del navegador) y
// el destino es exactamente esa página anterior, se vuelve a mostrar tal
// cual estaba -mismos filtros, resultados y scroll- en vez de recargarla
// desde cero.
//
// Solo se mantiene UNA página anterior en memoria (no todo el historial) y,
// si el usuario navega dos veces seguidas a la misma sección (p.ej. cambia
// de ticker en /research), esa página no se cachea: se descarta y se
// renderiza de nuevo limpia. Esto evita tener en el DOM dos copias de la
// misma página con ids duplicados (muchas páginas usan document.getElementById
// con ids fijos para sus gráficos).
// ---------------------------------------------------------------------------

let currentPage = null;     // { fullPath, container }
let cachedPrevPage = null;  // { fullPath, container, scrollTop }
let navDepth = 0;

function cleanRoute(fullPath) {
    return fullPath.split('?')[0];
}

function getMainEl() {
    return document.getElementById('main');
}

function detachCurrentAsPrev() {
    if (!currentPage) return;
    const mainEl = getMainEl();
    const scrollTop = mainEl ? mainEl.scrollTop : 0;
    currentPage.container.style.display = 'none';
    // Solo guardamos una página anterior: si ya había otra en caché, se descarta.
    if (cachedPrevPage && cachedPrevPage.container.parentNode) {
        cachedPrevPage.container.parentNode.removeChild(cachedPrevPage.container);
    }
    cachedPrevPage = { fullPath: currentPage.fullPath, container: currentPage.container, scrollTop };
}

async function loadView(fullPath) {
    const view = document.getElementById('view');
    if (!view) return;

    // ¿El destino es exactamente la página que tenemos cacheada como "anterior"?
    // -> restaurarla tal cual, sin volver a pedir datos ni perder filtros/scroll.
    if (cachedPrevPage && cachedPrevPage.fullPath === fullPath) {
        if (currentPage && currentPage.container.parentNode) {
            currentPage.container.parentNode.removeChild(currentPage.container);
        }
        const restored = cachedPrevPage;
        cachedPrevPage = null;
        restored.container.style.display = '';
        currentPage = { fullPath, container: restored.container };
        const mainEl = getMainEl();
        requestAnimationFrame(() => { if (mainEl) mainEl.scrollTop = restored.scrollTop || 0; });
        return;
    }

    const sameRouteAsCurrent = currentPage && cleanRoute(currentPage.fullPath) === cleanRoute(fullPath);
    if (currentPage && !sameRouteAsCurrent) {
        // Página realmente distinta: la actual pasa a ser la "anterior" cacheada.
        detachCurrentAsPrev();
    } else if (currentPage && sameRouteAsCurrent) {
        // Misma sección (p.ej. otro ticker en /research): no cachear, descartar.
        if (currentPage.container.parentNode) currentPage.container.parentNode.removeChild(currentPage.container);
        currentPage = null;
    }

    const container = document.createElement('div');
    container.className = 'view-page';
    view.appendChild(container);
    container.innerHTML = '<p class="loading">Cargando</p>';
    currentPage = { fullPath, container };

    try {
        const cleanPath = cleanRoute(fullPath);
        const loader = ROUTES[cleanPath] || ROUTES['/'];
        const module = await loader();
        await module.render(container);
        const mainEl = getMainEl();
        if (mainEl) mainEl.scrollTop = 0;
    } catch (err) {
        container.innerHTML = '<p style="color:var(--color-danger)">Error cargando módulo: ' + err.message + '</p>';
        console.error(err);
    }
}

function updateBackButton() {
    const bar = document.getElementById('back-bar');
    if (!bar) return;
    const show = navDepth > 0 && location.pathname !== '/login';
    bar.style.display = show ? '' : 'none';
}

function goBack() {
    if (navDepth > 0) history.back();
}

export function navigate(path, options = {}) {
    const isPopState = !!options.isPopState;
    const cleanPath = path.split('?')[0];
    const protectedRoutes = ['/', '/manifiesto', '/market', '/cartera', '/rsrw', '/scanner', '/newsfeed', '/spxl', '/btc-stratum', '/roadmap', '/academy', '/tesis', '/options', '/research', '/disclaimer', '/canslim', '/algoritmo', '/insider', '/admin'];
    const needsAuth = protectedRoutes.includes(cleanPath);

    if (needsAuth && !isAuthenticated()) {
        loadView('/login');
        if (!isPopState) {
            navDepth += 1;
            history.pushState({ navDepth }, '', '/login');
        }
        setActiveNavItem('/login');
        updateBackButton();
        return;
    }

    loadView(path);
    if (!isPopState) {
        navDepth += 1;
        history.pushState({ navDepth }, '', path);
    }
    setActiveNavItem(cleanPath);
    updateBackButton();
}

initTheme();
const token = getToken();
if (token) initWebSocket(token);
renderSidebar(document.getElementById('sidebar'), navigate);
renderTopbar(document.getElementById('topbar'), navigate);

// El tier guardado en sessionStorage es el que tenía el usuario en el
// último login/registro. Si el admin lo ha subido de tier desde entonces,
// esto lo refresca sin obligar a re-loguear, y repinta sidebar/topbar.
if (token) {
    api.get('/auth/me').then(me => {
        if (me?.tier) {
            setSession(token, me.tier, me.email);
            renderSidebar(document.getElementById('sidebar'), navigate);
            renderTopbar(document.getElementById('topbar'), navigate);
            setActiveNavItem(location.pathname);
        }
    }).catch(() => {});
}

const backBtn = document.getElementById('global-back-btn');
if (backBtn) backBtn.addEventListener('click', goBack);

const initialFullPath = location.pathname + location.search;
history.replaceState({ navDepth: 0 }, '', initialFullPath);
navigate(initialFullPath, { isPopState: true });

window.addEventListener('popstate', (e) => {
    navDepth = (e.state && typeof e.state.navDepth === 'number') ? e.state.navDepth : 0;
    navigate(location.pathname + location.search, { isPopState: true });
});

window.__navigate = navigate;
window.__loadView = loadView;
Tooltip.init();

window.goToResearch = function(ticker) {
    if (!ticker) return;
    navigate('/research?ticker=' + ticker.toUpperCase());
};