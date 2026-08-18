import { Tooltip } from '/components/tooltip.js';
import { initTheme } from '/core/theme.js';
import { renderSidebar, setActiveNavItem, NAV_ITEMS } from '/components/sidebar.js';
import { renderTopbar } from '/components/topbar.js';
import { initWebSocket } from '/core/websocket.js';
import { api, setSession, isLoggedIn, authHeader, clearToken } from '/core/api.js';
import { initCommandPalette } from '/components/command_palette.js';
import { showDisclaimerModal } from '/components/disclaimer_modal.js';
import { showPricingModal } from '/components/pricing_modal.js';
import { initChatWidget } from '/components/chat_widget.js';
import { initInstallPrompt } from '/components/install_prompt.js';

const ROUTES = {
    '/':           () => import('/pages/dashboard.js'),
    '/manifiesto': () => import('/pages/manifest.js'),
    '/market':     () => import('/pages/market.js'),
    '/cartera':    () => import('/pages/cartera.js'),
    '/rsrw':       () => import('/pages/rsrw.js'),
    '/scanner':    () => import('/pages/scanner.js'),
    '/watchlist':  () => import('/pages/watchlist.js'),
    '/account':    () => import('/pages/account.js'),
    '/community':  () => import('/pages/community.js'),
    '/spxl':       () => import('/pages/spxl.js'),
    '/btc-stratum': () => import('/pages/btc_stratum.js'),
    '/research':   () => import('/pages/research.js'),
    '/insider':    () => import('/pages/insider.js'),
    '/congress':   () => import('/pages/congress.js'),
    '/track-record': () => import('/pages/track_record.js'),
    '/newsfeed':   () => import('/pages/newsfeed.js'),
    '/canslim':    () => import('/pages/canslim.js'),
    '/options':    () => import('/pages/options.js'),
    '/academy':    () => import('/pages/academy.js'),
    '/roadmap':    () => import('/pages/roadmap.js'),
    '/tesis':      () => import('/pages/tesis.js'),
    '/equipo':     () => import('/pages/equipo.js'),
    '/algoritmo':  () => import('/pages/algoritmo.js'),
    '/login':      () => import('/pages/login.js'),
    '/register':   () => import('/pages/register.js'),
    '/admin':      () => import('/pages/admin.js'),
    '/disclaimer': () => import('/pages/disclaimer.js'),
};


function isAuthenticated() {
    return isLoggedIn();
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
        // clearToken() y no un removeItem suelto: ademas del resto de token
        // antiguo hay que quitar el marcador de sesion, o isLoggedIn()
        // seguiria diciendo que hay sesion despues de que el backend la haya
        // rechazado. La cookie la borra el backend con su propia respuesta.
        clearToken();
        navigate('/login?expired=1');
        return response;
    }

    // FastAPI/Starlette devuelve 403 (no 401) cuando la cabecera Authorization
    // llega vacía o mal formada (comportamiento propio de HTTPBearer, no un
    // fallo nuestro) — esto puede pasar en cascada tras un token caducado,
    // si algún fetch se queda sin cabecera. Sin este bloque, un 403 así
    // deja al usuario viendo errores por toda la pantalla en vez de
    // mandarlo al login, que es lo que realmente necesita. Se distingue de
    // un 403 legítimo de "no tienes ese plan" mirando el mensaje exacto que
    // usa require_tier() en el backend — ese sí debe mostrar su propio aviso,
    // no forzar un logout de alguien que está bien autenticado.
    if (response.status === 403 && url.includes('/api/v1/') && !url.includes('/auth/admin') && location.pathname !== '/login') {
        let esRestriccionDePlan = false;
        try {
            const body = await response.clone().json();
            const detail = body.detail || '';
            esRestriccionDePlan = typeof detail === 'string' && detail.includes('requiere el plan');
        } catch (e) { /* respuesta no-JSON, tratar como fallo de auth */ }

        if (!esRestriccionDePlan) {
            clearToken();
            navigate('/login?expired=1');
            return response;
        }
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

// Convención opcional: un módulo de página puede exportar `cleanup()` para
// parar timers/WebSockets/gráficos antes de que su contenedor se destruya
// de verdad (removeChild). Nunca se llama solo por ocultar una página para
// cachearla (ver detachCurrentAsPrev) -- esa sigue "viva" a propósito, para
// poder restaurarla al instante con scroll/filtros intactos.
function callCleanup(page) {
    if (page && typeof page.cleanup === 'function') {
        try { page.cleanup(); } catch (e) { console.error('[router] cleanup falló:', e); }
    }
}

function detachCurrentAsPrev() {
    if (!currentPage) return;
    const mainEl = getMainEl();
    const scrollTop = mainEl ? mainEl.scrollTop : 0;
    currentPage.container.style.display = 'none';
    // Solo guardamos una página anterior: si ya había otra en caché, se descarta
    // de verdad (removeChild) -- esa sí necesita cleanup, ya no va a volver.
    if (cachedPrevPage && cachedPrevPage.container.parentNode) {
        callCleanup(cachedPrevPage);
        cachedPrevPage.container.parentNode.removeChild(cachedPrevPage.container);
    }
    cachedPrevPage = { fullPath: currentPage.fullPath, container: currentPage.container, scrollTop, cleanup: currentPage.cleanup };
}

async function loadView(fullPath) {
    const view = document.getElementById('view');
    if (!view) return;

    // ¿El destino es exactamente la página que tenemos cacheada como "anterior"?
    // -> restaurarla tal cual, sin volver a pedir datos ni perder filtros/scroll.
    if (cachedPrevPage && cachedPrevPage.fullPath === fullPath) {
        if (currentPage && currentPage.container.parentNode) {
            callCleanup(currentPage);
            currentPage.container.parentNode.removeChild(currentPage.container);
        }
        const restored = cachedPrevPage;
        cachedPrevPage = null;
        restored.container.style.display = '';
        currentPage = { fullPath, container: restored.container, cleanup: restored.cleanup };
        const mainEl = getMainEl();
        requestAnimationFrame(() => { if (mainEl) mainEl.scrollTop = restored.scrollTop || 0; });
        return;
    }

    const sameRouteAsCurrent = currentPage && cleanRoute(currentPage.fullPath) === cleanRoute(fullPath);
    if (currentPage && !sameRouteAsCurrent) {
        // Página realmente distinta: la actual pasa a ser la "anterior" cacheada.
        detachCurrentAsPrev();
    } else if (currentPage && sameRouteAsCurrent) {
        // Misma sección (p.ej. otro ticker en /research): no cachear, descartar de verdad.
        if (currentPage.container.parentNode) {
            callCleanup(currentPage);
            currentPage.container.parentNode.removeChild(currentPage.container);
        }
        currentPage = null;
    }

    const container = document.createElement('div');
    container.className = 'view-page';
    view.appendChild(container);
    container.innerHTML = '<p class="loading">Cargando</p>';
    currentPage = { fullPath, container, cleanup: null };

    try {
        const cleanPath = cleanRoute(fullPath);
        const loader = ROUTES[cleanPath] || ROUTES['/'];
        const module = await loader();
        currentPage.cleanup = typeof module.cleanup === 'function' ? module.cleanup : null;
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

// Notifica al backend qué sección se ha visitado, para el panel de
// métricas de /admin ("qué sección entra más gente"). Fire-and-forget:
// nunca debe bloquear ni romper la navegación real, así que cualquier
// fallo (red caída, etc.) se ignora en silencio. Se excluyen /login,
// /register y /admin porque no son "contenido" de la terminal, solo ruido.
const ANALYTICS_EXCLUDED = new Set(['/login', '/register', '/admin']);

function trackPageView(cleanPath) {
    if (ANALYTICS_EXCLUDED.has(cleanPath)) return;
    fetch('/api/v1/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...authHeader(),
        },
        body: JSON.stringify({ section: cleanPath }),
    }).catch(() => { /* no pasa nada si falla */ });
}

export function navigate(path, options = {}) {
    const isPopState = !!options.isPopState;
    const cleanPath = path.split('?')[0];
    const protectedRoutes = ['/', '/manifiesto', '/market', '/cartera', '/rsrw', '/scanner', '/watchlist', '/account', '/community', '/newsfeed', '/spxl', '/btc-stratum', '/roadmap', '/academy', '/tesis', '/equipo', '/options', '/research', '/disclaimer', '/canslim', '/algoritmo', '/insider', '/congress', '/track-record', '/admin'];
    const needsAuth = protectedRoutes.includes(cleanPath);

    if (needsAuth && isAuthenticated()) trackPageView(cleanPath);

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
initInstallPrompt();
const sesionActiva = isLoggedIn();
// El WebSocket NO se condiciona a isLoggedIn(): esa función lee un marcador
// de localStorage/sessionStorage, y desde que el token vive en una cookie
// httpOnly ese marcador puede faltar con la sesión perfectamente viva (p. ej.
// tras reiniciar el navegador con el marcador en sessionStorage). En ese estado
// la app funcionaba entera --las llamadas HTTP llevan la cookie sola-- pero el
// ticker del topbar se quedaba en «Conectando...» para siempre, porque nadie
// llegaba a abrir el socket. Se intenta conectar y decide el servidor: si no
// hay sesión responde 4401, que onclose ya sabe tratar mandando a login.
initWebSocket();
if (sesionActiva) initChatWidget();
renderSidebar(document.getElementById('sidebar'), navigate);
renderTopbar(document.getElementById('topbar'), navigate);
initCommandPalette(NAV_ITEMS, navigate);

// El tier guardado en sessionStorage es el que tenía el usuario en el
// último login/registro. Si el admin lo ha subido de tier desde entonces,
// esto lo refresca sin obligar a re-loguear, y repinta sidebar/topbar.
if (sesionActiva) {
    api.get('/auth/me').then(me => {
        if (me?.tier) {
            setSession(me.tier, me.email, !!localStorage.getItem('rsu_session'));
            renderSidebar(document.getElementById('sidebar'), navigate);
            renderTopbar(document.getElementById('topbar'), navigate);
            setActiveNavItem(location.pathname);
        }
        // Encadenados: si falta aceptar el disclaimer, se muestra primero, y
        // solo al aceptarlo se comprueba el mensaje de transparencia de
        // costes. Si el disclaimer ya estaba aceptado (usuarios existentes
        // antes de que este segundo mensaje existiera), se comprueba
        // directamente -- así también lo ven, no solo los registros nuevos.
        const mostrarPricingSiHaceFalta = () => {
            if (me && me.pricing_message_seen === false) {
                showPricingModal();
            }
        };
        if (me && me.disclaimer_accepted === false) {
            // disclaimer_actualizado = ya aceptó una versión anterior del
            // texto (no es un usuario nuevo) -- el modal se lo explica.
            showDisclaimerModal(mostrarPricingSiHaceFalta, me.disclaimer_actualizado === true);
        } else {
            mostrarPricingSiHaceFalta();
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

window.__quickAddWatchlist = async function(ticker, btnEl) {
    if (!ticker || !btnEl) return;
    const original = btnEl.textContent;
    btnEl.disabled = true;
    btnEl.textContent = '...';
    try {
        const { addToWatchlist } = await import('/core/ui.js');
        const data = await addToWatchlist(ticker);
        if (data.ok) {
            btnEl.textContent = '✓ En watchlist';
            btnEl.style.color = 'var(--color-accent)';
            btnEl.style.borderColor = 'var(--color-accent)';
        } else {
            btnEl.textContent = original;
            btnEl.disabled = false;
            alert(data.error || 'No se pudo añadir a la watchlist');
        }
    } catch (e) {
        btnEl.textContent = original;
        btnEl.disabled = false;
    }
};