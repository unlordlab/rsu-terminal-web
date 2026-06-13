import { cycleTheme, getCurrentTheme } from '/core/theme.js';
import { initWebSocket, onMarketUpdate, offMarketUpdate } from '/core/websocket.js';

export function renderTopbar(container, navigate) {
    container.innerHTML = `
        <div id="prices-ticker" style="
            flex:1;
            display:flex;
            gap:1.5rem;
            overflow:hidden;
            align-items:center;
            font-size:11px;
        ">
            <span style="color:var(--color-muted);">Conectando...</span>
        </div>

        <div style="display:flex;align-items:center;gap:0.75rem;flex-shrink:0;">
            <span id="ws-indicator" title="WebSocket" style="
                width:6px;height:6px;border-radius:50%;
                background:#555;
                transition:background 0.3s;
            "></span>

            <span id="market-status" style="font-size:11px;color:var(--color-muted);">
                ● MKT
            </span>

            <button id="theme-toggle" title="Cambiar tema" style="
                background:none;border:1px solid var(--color-border);
                color:var(--color-muted);padding:3px 10px;
                border-radius:var(--radius);cursor:pointer;
                font-family:var(--font-mono);font-size:11px;
                transition:all var(--transition);
            ">THEME</button>

            <button id="logout-btn" style="
                background:none;border:1px solid var(--color-border);
                color:var(--color-muted);padding:3px 10px;
                border-radius:var(--radius);cursor:pointer;
                font-family:var(--font-mono);font-size:11px;
                transition:all var(--transition);
            ">LOGOUT</button>
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

    // WS indicator
    document.addEventListener('ws:connected',    () => setWsIndicator(true));
    document.addEventListener('ws:disconnected', () => setWsIndicator(false));

    // Market updates → actualizar barra
    onMarketUpdate('topbar', (data) => {
        updatePricesTicker(container, data);
    });

    function updateThemeLabel() {
        const btn = container.querySelector('#theme-toggle');
        if (btn) btn.textContent = getCurrentTheme().toUpperCase();
    }

    function setWsIndicator(connected) {
        const dot = container.querySelector('#ws-indicator');
        if (dot) {
            dot.style.background = connected ? 'var(--color-accent)' : '#555';
            dot.title = connected ? 'WebSocket conectado' : 'WebSocket desconectado';
        }
    }

    updateThemeLabel();

    // Iniciar WebSocket
    const token = sessionStorage.getItem('rsu_token');
    if (token) initWebSocket(token);
}

function updatePricesTicker(container, data) {
    const ticker = container.querySelector('#prices-ticker');
    if (!ticker) return;

    const items = [];

    // Índices
    (data.indices || []).forEach(idx => {
        const up    = idx.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        items.push(
            '<div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + idx.ticker + '</span>'
            + '<span style="color:var(--color-text);font-size:11px;">' + idx.price.toLocaleString('en-US') + '</span>'
            + '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(idx.chg).toFixed(2) + '%</span>'
            + '</div>'
        );
    });

    // Separador
    if (items.length > 0 && (data.prices || []).length > 0) {
        items.push('<div style="width:1px;height:28px;background:var(--color-border);flex-shrink:0;"></div>');
    }

    // Precios extra
    (data.prices || []).forEach(p => {
        const up    = p.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        items.push(
            '<div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + p.name + '</span>'
            + '<span style="color:var(--color-text);font-size:11px;">' + p.price.toLocaleString('en-US') + '</span>'
            + '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(p.chg).toFixed(2) + '%</span>'
            + '</div>'
        );
    });

    // RSU Score
    if (data.algo) {
        items.push('<div style="width:1px;height:28px;background:var(--color-border);flex-shrink:0;"></div>');
        items.push(
            '<div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">RSU ALGO</span>'
            + '<span style="color:' + data.algo.color + ';font-size:11px;font-weight:500;">' + data.algo.score + '/100</span>'
            + '<span style="color:' + data.algo.color + ';font-size:9px;">' + data.algo.estado + '</span>'
            + '</div>'
        );
    }

    // Timestamp
    if (data.timestamp) {
        items.push(
            '<div style="color:var(--color-muted);font-size:9px;flex-shrink:0;margin-left:auto;">⟳ ' + data.timestamp + '</div>'
        );
    }

    ticker.innerHTML = items.join('');

    // Actualizar estado mercado
    const mkt = container.querySelector('#market-status');
    if (mkt && data.indices && data.indices.length > 0) {
        mkt.style.color = 'var(--color-accent)';
        mkt.textContent = '● MKT LIVE';
    }
}