import { cycleTheme, getCurrentTheme } from '/core/theme.js';
import { initWebSocket, onMarketUpdate } from '/core/websocket.js';
import { clearToken, getTier } from '/core/api.js';
import { showPricingModal } from '/components/pricing_modal.js';

const TIER_LABELS = { free: 'FREE', tier1: 'TIER 1', tiers: 'TIER S' };
const TIER_COLORS = { free: 'var(--color-muted)', tier1: 'var(--color-accent)', tiers: '#ffd700' };

export function renderTopbar(container, navigate) {
    container.innerHTML = `
        <div style="flex:1;overflow:hidden;position:relative;min-width:0;height:48px;">
            <div id="ticker-track" style="
                display:inline-flex;
                gap:2rem;
                position:absolute;
                top:0;left:0;
                white-space:nowrap;
                animation:ticker-scroll 60s linear infinite;
                align-items:center;
                height:48px;
            ">
                <span style="color:var(--color-muted);font-size:11px;">Conectando...</span>
            </div>
        </div>

        <div style="display:flex;align-items:center;gap:0.75rem;flex-shrink:0;margin-left:1rem;">
            <span id="tier-badge" style="
                font-size:10px;letter-spacing:0.08em;flex-shrink:0;
                padding:2px 8px;border-radius:var(--radius);
                border:1px solid var(--color-border);
            "></span>
            <span id="pricing-info-btn" title="Por qué RSU Terminal no es gratis del todo" style="
                cursor:pointer;color:var(--color-muted);font-size:12px;
                flex-shrink:0;line-height:1;user-select:none;
            ">ⓘ</span>
            <span id="ws-indicator" style="
                width:6px;height:6px;border-radius:50%;
                background:#555;transition:background 0.3s;
                flex-shrink:0;
            "></span>
            <span id="market-status" style="font-size:11px;color:var(--color-muted);flex-shrink:0;">● MKT</span>
            <span id="topbar-time" style="font-size:11px;color:var(--color-muted);flex-shrink:0;font-family:var(--font-mono);"></span>
            <span id="account-btn" title="Mi Cuenta" style="
                cursor:pointer;color:var(--color-muted);font-size:14px;
                flex-shrink:0;line-height:1;user-select:none;
            ">⚙</span>
            <button id="theme-toggle" style="
                background:none;border:1px solid var(--color-border);
                color:var(--color-muted);padding:3px 10px;
                border-radius:var(--radius);cursor:pointer;
                font-family:var(--font-mono);font-size:11px;
            ">THEME</button>
            <button id="logout-btn" style="
                background:none;border:1px solid var(--color-border);
                color:var(--color-muted);padding:3px 10px;
                border-radius:var(--radius);cursor:pointer;
                font-family:var(--font-mono);font-size:11px;
            ">LOGOUT</button>
        </div>
    `;

    // Inyectar CSS de animación
    if (!document.getElementById('ticker-css')) {
        const style = document.createElement('style');
        style.id = 'ticker-css';
        style.textContent = `
            @keyframes ticker-scroll {
                0%   { transform: translateX(100vw); }
                100% { transform: translateX(-100%); }
            }
            #ticker-track:hover {
                animation-play-state: paused;
            }
        `;
        document.head.appendChild(style);
    }

    // Reloj en tiempo real hora Madrid
    updateClock(container);
    setInterval(() => updateClock(container), 1000);

    // Theme
    container.querySelector('#theme-toggle').addEventListener('click', () => {
        cycleTheme();
        updateThemeLabel(container);
    });

    // Tier badge
    const tier = getTier();
    const badge = container.querySelector('#tier-badge');
    badge.textContent = TIER_LABELS[tier] || 'FREE';
    badge.style.color = TIER_COLORS[tier] || 'var(--color-muted)';

    // Info de transparencia de costes -- reabre el mismo mensaje que se ve
    // al registrarse, siempre disponible por si alguien quiere volver a
    // leerlo. Ver conversación 20/07/2026.
    const pricingBtn = container.querySelector('#pricing-info-btn');
    pricingBtn.addEventListener('mouseenter', () => { pricingBtn.style.color = 'var(--color-accent)'; });
    pricingBtn.addEventListener('mouseleave', () => { pricingBtn.style.color = 'var(--color-muted)'; });
    pricingBtn.addEventListener('click', () => {
        showPricingModal(null, { esConsulta: true });
    });

    // Mi Cuenta (vinculación de Telegram, etc.)
    const accountBtn = container.querySelector('#account-btn');
    accountBtn.addEventListener('mouseenter', () => { accountBtn.style.color = 'var(--color-accent)'; });
    accountBtn.addEventListener('mouseleave', () => { accountBtn.style.color = 'var(--color-muted)'; });
    accountBtn.addEventListener('click', () => { navigate('/account'); });

    // Logout
    container.querySelector('#logout-btn').addEventListener('click', () => {
        clearToken();
        navigate('/login');
    });

    // WS events
    document.addEventListener('ws:connected',    () => setWsIndicator(container, true));
    document.addEventListener('ws:disconnected', () => setWsIndicator(container, false));

    // Market updates
    onMarketUpdate('topbar', (data) => {
        requestAnimationFrame(() => updateTicker(container, data));
    });

    // Escuchar también el evento directo del documento
    document.addEventListener('ws:market_update', (e) => {
        requestAnimationFrame(() => updateTicker(container, e.detail));
    });

    updateThemeLabel(container);

    // Iniciar WebSocket
    const token = sessionStorage.getItem('rsu_token');
    if (token) initWebSocket(token);
}

function updateClock(container) {
    const el = container.querySelector('#topbar-time');
    if (!el) return;
    const now = new Date();
    const madrid = now.toLocaleTimeString('es-ES', {
        timeZone: 'Europe/Madrid',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    el.textContent = '⟳ ' + madrid;
}

function updateThemeLabel(container) {
    const btn = container.querySelector('#theme-toggle');
    if (btn) btn.textContent = getCurrentTheme().toUpperCase();
}

function setWsIndicator(container, connected) {
    const dot = container.querySelector('#ws-indicator');
    const mkt = container.querySelector('#market-status');
    if (dot) dot.style.background = connected ? 'var(--color-accent)' : '#555';
    if (mkt) {
        mkt.style.color  = connected ? 'var(--color-accent)' : 'var(--color-muted)';
        mkt.textContent  = connected ? 'MKT LIVE' : '● MKT';
    }
}

function updateTicker(container, data) {
    const track = container.querySelector('#ticker-track');
    if (!track) return;

    const items = [];

    // Índices
    (data.indices || []).forEach(idx => {
        const up    = idx.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        items.push(
            '<span style="display:inline-flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:60px;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + idx.ticker + '</span>'
            + '<span style="color:var(--color-text);font-size:12px;">' + idx.price.toLocaleString('en-US') + '</span>'
            + '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(idx.chg).toFixed(2) + '%</span>'
            + '</span>'
        );
    });

    // Separador
    items.push('<span style="color:var(--color-border);font-size:16px;flex-shrink:0;">│</span>');

    // Precios extra
    (data.prices || []).forEach(p => {
        const up    = p.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        items.push(
            '<span style="display:inline-flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:60px;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + p.name + '</span>'
            + '<span style="color:var(--color-text);font-size:12px;">' + p.price.toLocaleString('en-US') + '</span>'
            + '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(p.chg).toFixed(2) + '%</span>'
            + '</span>'
        );
    });

    // Separador
    if (data.algo) {
        items.push('<span style="color:var(--color-border);font-size:16px;flex-shrink:0;">│</span>');
        items.push(
            '<span style="display:inline-flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:80px;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">RSU ALGO</span>'
            + '<span style="color:' + data.algo.color + ';font-size:12px;font-weight:500;">' + data.algo.score + '/100</span>'
            + '<span style="color:' + data.algo.color + ';font-size:9px;">' + data.algo.estado + '</span>'
            + '</span>'
        );
    }

    // Duplicar contenido para loop infinito suave
    const content = items.join('');
    track.innerHTML = content + 
        '<span style="display:inline-block;min-width:4rem;"></span>' + 
        content;

    // Recalcular duración de la animación según el ancho del contenido
    const trackWidth = track.scrollWidth / 2;
    const speed      = 10; // px por segundo
    const duration   = Math.max(30, trackWidth / speed);
    track.style.animationDuration = duration + 's';
}