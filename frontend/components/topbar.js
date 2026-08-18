import { cycleTheme, getCurrentTheme, nombreTema } from '/core/theme.js';
import { initWebSocket, onMarketUpdate } from '/core/websocket.js';
import { logout, getTier, isLoggedIn } from '/core/api.js';
import { showPricingModal } from '/components/pricing_modal.js';

const TIER_LABELS = { free: 'FREE', tier1: 'TIER 1', tiers: 'TIER S' };
const TIER_COLORS = { free: 'var(--color-muted)', tier1: 'var(--color-accent)', tiers: '#ffd700' };

export function renderTopbar(container, navigate) {
    // DESMONTAR LO DE LA LLAMADA ANTERIOR, Y LO PRIMERO DE TODO.
    //
    // renderTopbar() no corre una vez: en cada carga corre DOS (al arrancar el
    // router, y otra vez cuando /auth/me devuelve el tier al día). Cada llamada
    // enganchaba escuchas nuevas y abría un `setInterval` para el reloj, y
    // nada de eso se quitaba jamás -- se acumulaban, cada una apuntando a un
    // `container` distinto, y el reloj latía dos veces por carga.
    //
    // Va al PRINCIPIO por un error que ya se cometió aquí: puesto más abajo,
    // la segunda llamada paraba el reloj que ella misma acababa de arrancar
    // unas líneas antes, y el reloj se quedaba congelado. El orden no es un
    // detalle de estilo.
    //
    // El desmontaje vive en el módulo y no en el container a propósito: las
    // escuchas cuelgan de `document`, del velo y de la barra lateral, así que
    // sobreviven aunque el topbar se repinte entero.
    desmontarTopbar();

    container.innerHTML = `
        <button id="nav-toggle" aria-label="Abrir el menú de secciones" aria-expanded="false">☰</button>
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
    _relojT = setInterval(() => updateClock(container), 1000);

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
    container.querySelector('#logout-btn').addEventListener('click', async () => {
        // La cookie es httpOnly: borrarla es cosa del backend, por eso
        // logout() llama a /auth/logout antes de limpiar lo local.
        await logout();
        navigate('/login');
    });

    _escuchas = [
        ['ws:connected',    () => setWsIndicator(container, true)],
        ['ws:disconnected', () => setWsIndicator(container, false)],
        ['ws:market_update', (e) => pintarTicker(container, e.detail)],
    ];
    _escuchas.forEach(([tipo, fn]) => document.addEventListener(tipo, fn));
    onMarketUpdate('topbar', (data) => pintarTicker(container, data));

    updateThemeLabel(container);

    // Cajón de navegación (solo visible por debajo de 768px, ver index.html).
    // El estado vive en una clase de #app y no en JS: así el CSS decide
    // cuándo aplica y no hay dos fuentes de verdad que se contradigan al
    // girar el móvil o cambiar de tamaño.
    const app    = document.getElementById('app');
    const toggle = container.querySelector('#nav-toggle');
    const velo   = document.getElementById('nav-velo');

    const cerrarNav = () => {
        app.classList.remove('nav-abierta');
        toggle.setAttribute('aria-expanded', 'false');
    };
    toggle.addEventListener('click', () => {
        const abierta = app.classList.toggle('nav-abierta');
        toggle.setAttribute('aria-expanded', String(abierta));
    });
    // Estas tres viven en elementos que NO están dentro del topbar (el velo,
    // la barra lateral y el propio documento), así que no desaparecen al
    // repintarlo: hay que quitarlas a mano o se acumulan una por llamada.
    // `#nav-toggle` no entra aquí porque sí se recrea con el innerHTML de
    // arriba, y con él se va su escucha.
    const cerrarConEscape = e => {
        if (e.key === 'Escape' && app.classList.contains('nav-abierta')) cerrarNav();
    };
    // Tocar una sección tiene que cerrar el cajón: si no, se queda tapando
    // la página que se acaba de abrir. Delegado en el propio sidebar para
    // que siga funcionando cuando renderSidebar() lo repinte entero.
    const cerrarSiEsSeccion = e => {
        if (e.target.closest('.nav-item')) cerrarNav();
    };
    const sidebar = document.getElementById('sidebar');
    if (velo)    _escuchasExtra.push([velo, 'click', cerrarNav]);
    if (sidebar) _escuchasExtra.push([sidebar, 'click', cerrarSiEsSeccion]);
    _escuchasExtra.push([document, 'keydown', cerrarConEscape]);
    _escuchasExtra.forEach(([el, tipo, fn]) => el.addEventListener(tipo, fn));

    // Iniciar WebSocket. Sin condicionarlo a isLoggedIn() -- ver el comentario
    // largo en core/router.js: ese marcador puede faltar con la sesión viva, y
    // entonces el ticker se quedaba en «Conectando...» sin que nada lo dijera.
    initWebSocket();

    // RED DE SEGURIDAD: el ticker no puede depender SOLO de que llegue un
    // empujón del WebSocket.
    //
    // Hasta ahora, si ese primer mensaje se perdía por cualquier motivo, el
    // ticker se quedaba en «Conectando...» para siempre y sin reintentar --
    // que es justo lo que reportó el usuario. Y hay varias formas de
    // perderlo: la pestaña cargada de fondo (ver pintarTicker), un socket
    // que muere antes del primer envío, o un dato que reventase el pintado.
    //
    // Los mismos números salen por HTTP, así que a los 6 segundos sin
    // noticias se piden y se pinta con ellos. No sustituye al WebSocket: en
    // cuanto llegue el primer mensaje real, este lo sobrescribe.
    clearTimeout(_respaldoT);
    _respaldoT = setTimeout(() => respaldoPorHttp(container), 6000);
}

// ── Estado del módulo, para poder desmontar lo de la llamada anterior ──
let _escuchas = [];
let _escuchasExtra = [];
let _relojT   = null;
let _respaldoT = null;
let _tickerPintado = false;

function desmontarTopbar() {
    _escuchas.forEach(([tipo, fn]) => document.removeEventListener(tipo, fn));
    _escuchas = [];
    _escuchasExtra.forEach(([el, tipo, fn]) => el.removeEventListener(tipo, fn));
    _escuchasExtra = [];
    if (_relojT)    { clearInterval(_relojT); _relojT = null; }
    if (_respaldoT) { clearTimeout(_respaldoT); _respaldoT = null; }
}

function pintarTicker(container, data) {
    _tickerPintado = true;
    clearTimeout(_respaldoT);
    // requestAnimationFrame NO dispara mientras la pestaña está oculta, así
    // que una página cargada de fondo dejaría el pintado en cola. Se usa solo
    // cuando la pestaña se ve; si no, se pinta directamente.
    if (document.hidden) updateTicker(container, data);
    else requestAnimationFrame(() => updateTicker(container, data));
}

async function respaldoPorHttp(container) {
    if (_tickerPintado) return;
    try {
        const r = await fetch('/api/v1/market/indices', { credentials: 'include' });
        if (!r.ok) return;
        const d = await r.json();
        const indices = (d.data || [])
            .filter(i => i.ok && i.price != null)
            .map(i => ({ ticker: i.ticker, price: i.price, chg: i.pct }));
        // Sin ningún dato utilizable no se pinta: dejar «Conectando...» dice
        // más que un ticker vacío, porque el vacío parece un mercado parado.
        if (indices.length) updateTicker(container, { indices });
    } catch (_) {
        // Silencioso a propósito: es una red de seguridad, no la vía normal.
    }
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
    if (btn) btn.textContent = nombreTema(getCurrentTheme());
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

    // Un dato que falta se salta; NO tumba el ticker entero.
    //
    // `idx.price.toLocaleString()` revienta con un precio nulo, y desde el
    // 18/08/2026 los nulos son posibles POR DISEÑO: el backend convierte los
    // no-finitos en null en vez de escribir un NaN que rompía el JSON. Al
    // arreglar aquello se abrió esto -- una excepción dentro del pintado deja
    // el ticker en «Conectando...» exactamente igual que antes, con el mismo
    // silencio. Mejor enseñar los que sí tienen precio que ninguno.
    const utilizable = (v) => v != null && Number.isFinite(Number(v));

    // Índices
    (data.indices || []).filter(idx => utilizable(idx.price)).forEach(idx => {
        const up    = idx.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        // Sin variación medida no se escribe «0.00%», que se leería como un
        // día plano: se deja en blanco, que es lo que de verdad se sabe.
        const varia = utilizable(idx.chg)
            ? '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(idx.chg).toFixed(2) + '%</span>'
            : '<span style="color:var(--color-muted);font-size:9px;">—</span>';
        items.push(
            '<span style="display:inline-flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:60px;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + idx.ticker + '</span>'
            + '<span style="color:var(--color-text);font-size:12px;">' + idx.price.toLocaleString('en-US') + '</span>'
            + varia
            + '</span>'
        );
    });

    // Separador
    items.push('<span style="color:var(--color-border);font-size:16px;flex-shrink:0;">│</span>');

    // Precios extra
    (data.prices || []).filter(p => utilizable(p.price)).forEach(p => {
        const up    = p.chg >= 0;
        const color = up ? 'var(--color-accent)' : '#f23645';
        const arrow = up ? '▲' : '▼';
        items.push(
            '<span style="display:inline-flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:60px;">'
            + '<span style="color:var(--color-muted);font-size:9px;letter-spacing:0.05em;">' + p.name + '</span>'
            + '<span style="color:var(--color-text);font-size:12px;">' + p.price.toLocaleString('en-US') + '</span>'
            + (utilizable(p.chg)
                ? '<span style="color:' + color + ';font-size:9px;">' + arrow + ' ' + Math.abs(p.chg).toFixed(2) + '%</span>'
                : '<span style="color:var(--color-muted);font-size:9px;">—</span>')
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

    // Si no ha sobrevivido ni un dato, no se deja el ticker en blanco: un
    // ticker vacío se lee como «el mercado no se mueve», que es una
    // afirmación, y aquí lo cierto es que no hay dato.
    const hayDatos = items.some(x => x.indexOf('min-width') !== -1);
    if (!hayDatos) {
        track.innerHTML = '<span style="color:var(--color-muted);font-size:11px;">Sin datos de mercado ahora mismo</span>';
        return;
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