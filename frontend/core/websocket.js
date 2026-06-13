const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 5000;

let socket     = null;
let handlers   = {};
let reconnectT = null;

export function initWebSocket(token) {
    if (socket && socket.readyState === WebSocket.OPEN) return;

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

    socket.onclose = () => {
        console.log('[WS] Desconectado — reconectando en 5s');
        document.dispatchEvent(new CustomEvent('ws:disconnected'));
        reconnectT = setTimeout(() => {
            const t = sessionStorage.getItem('rsu_token');
            if (t) initWebSocket(t);
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