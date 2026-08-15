import { authHeader } from '/core/api.js';
import { tt } from '/components/tooltip.js';
import { errorMessage, esc, fmtFecha, panel } from '/core/ui.js';


// Mismo estilo de "píldora" del ticker que ya usa Cartera — antes Watchlist
// solo tenía la versión mínima de .ticker-link de base.css (sin fondo ni
// borde), por eso se veía plano al lado de Cartera.
function injectStyles() {
    if (document.getElementById('watchlist-styles')) return;
    const s = document.createElement('style');
    s.id = 'watchlist-styles';
    s.textContent = `
        .ticker-link {
            background:rgba(0,255,173,.1);color:var(--color-accent);
            border:1px solid rgba(0,255,173,.3);border-radius:3px;
            padding:2px 8px;font-size:12px;cursor:pointer;
            text-decoration:none;transition:all .15s;display:inline-block;
            justify-self:start;
        }
        .ticker-link:hover { background:rgba(0,255,173,.2);border-color:var(--color-accent); }
    `;
    document.head.appendChild(s);
}

export async function render(container) {
    injectStyles();
    container.innerHTML = pageShell();
    wireForm(container);
    loadWatchlist(container);
    loadAlerts(container);
    loadTelegramBanner(container);

    // Deep-link ?ticker= -- a diferencia de research.js/rsrw.js/insider.js/
    // canslim.js, aquí SOLO se rellena el campo, sin enviar automáticamente:
    // auto-añadir un ticker a la watchlist solo por visitar una URL sería
    // un efecto secundario no deseado (a diferencia de "buscar", que no
    // cambia ningún dato).
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        const addInput = container.querySelector('#wl-add-input');
        if (addInput) addInput.value = urlTicker.toUpperCase();
    }
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">★ WATCHLIST ' + tt('watchlist') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Tus tickers seguidos + alertas de precio</div>'
        + '</div>'

        // Añadir ticker
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="wl-add-input" type="text" placeholder="Añadir ticker (NVDA, AAPL...)" style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;text-transform:uppercase;">'
        + '<button id="wl-add-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">＋ AÑADIR</button>'
        + '</div>'

        + '<div id="wl-table"></div>'

        + '<div id="wl-telegram-banner"></div>'

        // Crear alerta
        + '<div style="margin-top:1.5rem;margin-bottom:0.75rem;color:var(--color-accent);font-size:14px;letter-spacing:0.08em;">⏰ NUEVA ALERTA ' + tt('price-alerts') + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;flex-wrap:wrap;align-items:center;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:12px 14px;">'
        + '<input id="alert-ticker" type="text" placeholder="Ticker" style="width:100px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;text-transform:uppercase;">'
        + '<select id="alert-metric" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<option value="price">Precio</option>'
        + '<option value="rvol">RVOL</option>'
        + '<option value="ema_touch">Toque de EMA</option>'
        + '</select>'
        + '<select id="alert-condition" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<option value="above">Por encima de</option>'
        + '<option value="below">Por debajo de</option>'
        + '</select>'
        + '<input id="alert-price" type="number" step="0.01" placeholder="Precio objetivo ($)" style="width:160px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<select id="alert-ema-period" style="display:none;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<option value="10">EMA 10</option>'
        + '<option value="20">EMA 20</option>'
        + '<option value="50" selected>EMA 50</option>'
        + '<option value="200">EMA 200</option>'
        + '</select>'
        + '<button id="alert-create-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">CREAR ALERTA</button>'
        + '<span id="alert-form-msg" style="font-size:11px;color:var(--color-muted);"></span>'
        + '</div>'

        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        + '<span></span>'
        + '<button id="alert-clear-triggered-btn" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:5px 12px;font-size:10px;cursor:pointer;">🗑 LIMPIAR DISPARADAS</button>'
        + '</div>'
        + '<div id="alerts-table"></div>';
}

// El cuerpo vive en core/ui.js::panel() -- este mismo envoltorio estaba
// copiado en cinco paginas. `avisos` es opcional: las llamadas de siempre no
// cambian.
function shell(title, content, subtitle, avisos) {
    return panel({ titulo: title, contenido: content, subtitulo: subtitle,
                   avisos, escapar: true });
}

function loading() { return '<div style="padding:1rem;color:var(--color-muted);font-size:12px;">Cargando...</div>'; }
function error(msg) { return errorMessage(msg); }

// ── WATCHLIST ────────────────────────────────────────────────────────────────

async function loadWatchlist(container) {
    const el = container.querySelector('#wl-table');
    el.innerHTML = shell('TICKERS SEGUIDOS', loading());
    try {
        const res  = await fetch('/api/v1/watchlist', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        if (!data.data.length) {
            el.innerHTML = shell('TICKERS SEGUIDOS', '<div style="padding:1.5rem;text-align:center;color:var(--color-muted);font-size:12px;">Todavía no sigues ningún ticker. Añade uno arriba ↑</div>');
            return;
        }
        const header = '<div style="display:grid;grid-template-columns:1fr 100px 90px 90px 40px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
            + '<div>TICKER</div><div style="text-align:right;">PRECIO</div><div style="text-align:right;">VAR%</div><div style="text-align:center;">ALERTA</div><div></div></div>';
        const rows = data.data.map(w => {
            // chg puede ser null teniendo precio: la fuente de respaldo da la
            // cotización pero no la variación del día. Antes `Math.abs(null)`
            // daba 0 y se pintaba un "▲ 0.00%" que parecía una sesión plana
            // real. Sin variación se muestra "—", igual que sin precio.
            const hayChg = w.ok && w.chg != null;
            const up     = (w.chg || 0) >= 0;
            const color  = hayChg ? (up ? 'var(--color-accent)' : '#f23645') : 'var(--color-muted)';
            const arrow  = up ? '▲' : '▼';
            return '<div style="display:grid;grid-template-columns:1fr 100px 90px 90px 40px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;">'
                + '<div class="ticker-link" style="color:var(--color-accent);cursor:pointer;font-weight:500;" onclick="goToResearch(\'' + esc(w.ticker) + '\')">' + esc(w.ticker) + '</div>'
                + '<div style="text-align:right;color:var(--color-text);">' + (w.ok ? '$' + w.price.toFixed(2) : '—') + '</div>'
                + '<div style="text-align:right;color:' + color + ';">' + (hayChg ? arrow + ' ' + Math.abs(w.chg).toFixed(2) + '%' : '—') + '</div>'
                + '<div style="text-align:center;"><button class="wl-alert-btn" data-ticker="' + esc(w.ticker) + '" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:3px;padding:3px 8px;font-size:10px;cursor:pointer;">＋ alerta</button></div>'
                + '<div style="text-align:center;"><button class="wl-remove-btn" data-ticker="' + esc(w.ticker) + '" style="background:transparent;border:none;color:var(--color-muted);cursor:pointer;font-size:14px;" title="Quitar de watchlist">✕</button></div>'
                + '</div>';
        }).join('');
        el.innerHTML = shell('TICKERS SEGUIDOS', header + rows);

        el.querySelectorAll('.wl-remove-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ticker = btn.getAttribute('data-ticker');
                btn.disabled = true;
                await fetch('/api/v1/watchlist/' + encodeURIComponent(ticker), { method: 'DELETE', headers: authHeader() });
                loadWatchlist(container);
            });
        });
        el.querySelectorAll('.wl-alert-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ticker = btn.getAttribute('data-ticker');
                const input  = container.querySelector('#alert-ticker');
                input.value  = ticker;
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                input.focus();
            });
        });
    } catch(e) {
        el.innerHTML = shell('TICKERS SEGUIDOS', error(e.message));
    }
}

function wireAddTicker(container) {
    const input = container.querySelector('#wl-add-input');
    const btn   = container.querySelector('#wl-add-btn');
    const submit = async () => {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.disabled = true;
        try {
            const res  = await fetch('/api/v1/watchlist', { method: 'POST', headers: authHeader(), body: JSON.stringify({ ticker }) });
            const data = await res.json();
            if (data.ok) {
                input.value = '';
                loadWatchlist(container);
            } else {
                alert(data.error || 'No se pudo añadir el ticker');
            }
        } catch(e) {
            alert('Error de red: ' + e.message);
        } finally {
            btn.disabled = false;
        }
    };
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
}

// ── ALERTAS ──────────────────────────────────────────────────────────────────

const IMPACT_LABEL = { active: 'ACTIVA', triggered: 'DISPARADA', cancelled: 'CANCELADA' };
const IMPACT_COLOR = { active: '#3b82f6', triggered: '#00ffad', cancelled: 'var(--color-muted)' };

async function loadAlerts(container) {
    const el = container.querySelector('#alerts-table');
    el.innerHTML = shell('MIS ALERTAS', loading());
    try {
        const res  = await fetch('/api/v1/watchlist/alerts', { headers: authHeader() });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');
        if (!data.data.length) {
            el.innerHTML = shell('MIS ALERTAS', '<div style="padding:1.5rem;text-align:center;color:var(--color-muted);font-size:12px;">Todavía no has creado ninguna alerta.</div>');
        } else {
            const header = '<div style="display:grid;grid-template-columns:90px 130px 110px 100px 1fr 40px;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
                + '<div>TICKER</div><div>CONDICIÓN</div><div style="text-align:right;">OBJETIVO</div><div>ESTADO</div><div>DETALLE</div><div></div></div>';
            const rows = data.data.map(a => {
                const isRvol = a.metric === 'rvol';
                const isEma  = a.metric === 'ema_touch';
                const condLabel = isEma
                    ? ('Toque de EMA' + esc(a.ema_period))
                    : (a.condition === 'above' ? 'Por encima de ' : 'Por debajo de ') + (isRvol ? 'RVOL' : 'precio');
                const targetFmt = isEma ? 'Cruce' : (isRvol ? Number(a.target_price).toFixed(2) + 'x' : '$' + Number(a.target_price).toFixed(2));
                const stColor   = IMPACT_COLOR[a.status] || 'var(--color-muted)';
                const bg        = a.status === 'triggered' && !a.seen ? 'rgba(0,255,173,0.05)' : 'transparent';
                const fmtTriggerPrice = (v) => isRvol ? v.toFixed(2) + 'x' : '$' + v.toFixed(2);
                const detail    = a.status === 'triggered'
                    ? ('Disparada a ' + (a.triggered_price != null ? fmtTriggerPrice(a.triggered_price) : '?') + ' el ' + esc(fmtFecha(a.triggered_at)))
                    : ('Creada el ' + esc(fmtFecha(a.created_at)));
                return '<div style="display:grid;grid-template-columns:90px 130px 110px 100px 1fr 40px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:12px;align-items:center;background:' + bg + ';">'
                    + '<div class="ticker-link" style="color:var(--color-accent);cursor:pointer;font-weight:500;" onclick="goToResearch(\'' + esc(a.ticker) + '\')">' + esc(a.ticker) + '</div>'
                    + '<div style="color:var(--color-muted);">' + condLabel + '</div>'
                    + '<div style="text-align:right;color:var(--color-text);">' + targetFmt + '</div>'
                    + '<div style="color:' + stColor + ';font-size:10px;font-weight:600;">' + esc(IMPACT_LABEL[a.status] || a.status) + '</div>'
                    + '<div style="color:var(--color-muted);font-size:10px;">' + detail + '</div>'
                    + '<div style="text-align:center;"><button class="alert-remove-btn" data-id="' + esc(a.id) + '" style="background:transparent;border:none;color:var(--color-muted);cursor:pointer;font-size:14px;" title="Eliminar alerta">✕</button></div>'
                    + '</div>';
            }).join('');
            el.innerHTML = shell('MIS ALERTAS', header + rows);

            el.querySelectorAll('.alert-remove-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    btn.disabled = true;
                    await fetch('/api/v1/watchlist/alerts/' + id, { method: 'DELETE', headers: authHeader() });
                    loadAlerts(container);
                });
            });
        }
        // Al visitar esta página se dan por vistas las alertas disparadas (apaga la campanita)
        fetch('/api/v1/watchlist/alerts/mark-seen', { method: 'POST', headers: authHeader() })
            .then(() => { if (window.__refreshAlertBadge) window.__refreshAlertBadge(); })
            .catch(() => {});
    } catch(e) {
        el.innerHTML = shell('MIS ALERTAS', error(e.message));
    }
}

async function loadTelegramBanner(container) {
    const el = container.querySelector('#wl-telegram-banner');
    if (!el) return;
    try {
        const res  = await fetch('/api/v1/auth/me', { headers: authHeader() });
        const data = await res.json();
        if (!res.ok || data.telegram_linked) { el.innerHTML = ''; return; }
        el.innerHTML = '<div style="margin-top:0.75rem;padding:8px 14px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);font-size:11px;color:var(--color-muted);">'
            + '🔔 Tus alertas solo se ven aquí en la web. Vincula Telegram desde <span onclick="window.__navigate(\'/account\')" style="color:var(--color-accent);cursor:pointer;">Mi Cuenta</span> para recibirlas también fuera de la app.</div>';
    } catch (e) {
        el.innerHTML = '';
    }
}

function wireCreateAlert(container) {
    const btn       = container.querySelector('#alert-create-btn');
    const msg       = container.querySelector('#alert-form-msg');
    const metric    = container.querySelector('#alert-metric');
    const price     = container.querySelector('#alert-price');
    const condition = container.querySelector('#alert-condition');
    const emaPeriod = container.querySelector('#alert-ema-period');

    metric.addEventListener('change', () => {
        const isEma = metric.value === 'ema_touch';
        price.style.display     = isEma ? 'none' : '';
        condition.style.display = isEma ? 'none' : '';
        emaPeriod.style.display = isEma ? '' : 'none';
        price.placeholder = metric.value === 'rvol' ? 'RVOL objetivo (ej. 2.5)' : 'Precio objetivo ($)';
    });

    btn.addEventListener('click', async () => {
        const ticker      = container.querySelector('#alert-ticker').value.trim().toUpperCase();
        const metricValue = metric.value;
        const isEma       = metricValue === 'ema_touch';

        if (!ticker) {
            msg.style.color = '#f23645';
            msg.textContent = 'Escribe un ticker';
            return;
        }
        if (!isEma) {
            const target = parseFloat(price.value);
            if (!target || target <= 0) {
                msg.style.color = '#f23645';
                msg.textContent = metricValue === 'rvol' ? 'Rellena ticker y RVOL objetivo (p.ej. 2.5)' : 'Rellena ticker y precio objetivo';
                return;
            }
        }

        btn.disabled = true;
        msg.style.color = 'var(--color-muted)';
        msg.textContent = 'Creando...';
        try {
            const payload = isEma
                ? { ticker, metric: metricValue, ema_period: parseInt(emaPeriod.value, 10) }
                : { ticker, condition: condition.value, target_price: parseFloat(price.value), metric: metricValue };
            const res  = await fetch('/api/v1/watchlist/alerts', {
                method: 'POST', headers: authHeader(),
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (data.ok) {
                msg.style.color = '#00ffad';
                msg.textContent = 'Alerta creada ✓';
                container.querySelector('#alert-ticker').value = '';
                price.value = '';
                loadAlerts(container);
            } else {
                msg.style.color = '#f23645';
                msg.textContent = data.error || 'No se pudo crear la alerta';
            }
        } catch(e) {
            msg.style.color = '#f23645';
            msg.textContent = 'Error de red: ' + e.message;
        } finally {
            btn.disabled = false;
        }
    });
}

function wireClearTriggered(container) {
    const btn = container.querySelector('#alert-clear-triggered-btn');
    btn.addEventListener('click', async () => {
        if (!confirm('¿Eliminar todas las alertas ya disparadas? Esta acción no se puede deshacer.')) return;
        btn.disabled = true;
        try {
            await fetch('/api/v1/watchlist/alerts/triggered', { method: 'DELETE', headers: authHeader() });
            loadAlerts(container);
        } finally {
            btn.disabled = false;
        }
    });
}

function wireForm(container) {
    wireAddTicker(container);
    wireCreateAlert(container);
    wireClearTriggered(container);
}