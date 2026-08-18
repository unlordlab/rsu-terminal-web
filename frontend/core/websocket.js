// URL dinámica basada en el host actual — funciona en localhost Y en producción
// sin ningún cambio de configuración. Usa wss:// automáticamente si la página
// se sirve sobre HTTPS (Hetzner con Nginx + certificado).
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL      = WS_PROTOCOL + '//' + window.location.host + '/ws';
const RECONNECT_DELAY = 5000;

let socket     = null;
let handlers   = {};
let reconnectT = null;

// Sin argumento: la cookie de sesión (httpOnly) viaja sola en el handshake
// del WebSocket por ser el mismo origen, así que ya no hay que pasarle el
// token -- ni tenerlo a mano, ni exponerlo en la URL. El parámetro se acepta
// todavía para las sesiones abiertas antes del cambio a cookie, que siguen
// llevando su token en el navegador.
// Páginas donde no se intenta conectar: no hay sesión que valga y el servidor
// rechazaría con un 4401 que mandaría a login estando ya en login.
const RUTAS_SIN_SESION = ['/login', '/register'];

export function initWebSocket(token) {
    if (socket && socket.readyState === WebSocket.OPEN) return;
    if (RUTAS_SIN_SESION.includes(window.location.pathname)) return;

    const url = WS_URL + (token ? '?token=' + token : '');
    socket = new WebSocket(url);

    socket.onopen = () => {
        console.log('[WS] Conectado');
        if (reconnectT) { clearTimeout(reconnectT); reconnectT = null; }
        document.dispatchEvent(new CustomEvent('ws:connected'));
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'ping') return;
            document.dispatchEvent(new CustomEvent('ws:market_update', { detail: data }));
            Object.values(handlers).forEach(fn => fn(data));
        } catch(e) {
            console.warn('[WS] Error parsing:', e);
        }
    };

    socket.onclose = (event) => {
        document.dispatchEvent(new CustomEvent('ws:disconnected'));

        // 4401 = el backend ha rechazado el token (ausente/inválido/caducado).
        // Reintentar aquí solo provocaría un bucle infinito de conexiones
        // rechazadas: mejor limpiar la sesión y mandar a login, igual que
        // hace el interceptor de fetch para las peticiones HTTP con 401.
        if (event.code === 4401) {
            console.log('[WS] Sesión inválida o caducada, redirigiendo a login');
            import('/core/api.js').then(m => m.clearToken());
            if (window.__navigate) window.__navigate('/login');
            return;
        }

        console.log('[WS] Desconectado — reconectando en 5s');
        reconnectT = setTimeout(() => {
            import('/core/api.js').then(m => { if (m.isLoggedIn()) initWebSocket(); });
        }, RECONNECT_DELAY);
    };

    socket.onerror = () => {
        socket.close();
    };
}

export function onMarketUpdate(id, fn) {
    handlers[id] = fn;
}

export function offMarketUpdate(id) {
    delete handlers[id];
}

export function wsConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
}