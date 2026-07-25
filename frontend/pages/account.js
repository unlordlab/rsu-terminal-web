import { errorMessage, esc, safeUrl } from '/core/ui.js';

function authHeader() {
    const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

let _pollTimer = null;

export async function render(container) {
    container.innerHTML = pageShell();
    await loadStatus(container);
}

export function cleanup() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">⚙ MI CUENTA</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Vinculación de notificaciones</div>'
        + '</div>'
        + '<div id="account-telegram-section" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;max-width:520px;">'
        + '<div style="color:var(--color-text);font-size:13px;">Cargando…</div>'
        + '</div>';
}

async function loadStatus(container) {
    const section = container.querySelector('#account-telegram-section');
    try {
        const res = await fetch('/api/v1/auth/me', { headers: authHeader() });
        const data = await res.json();
        if (!res.ok) { section.innerHTML = errorMessage(data.detail || 'No se pudo cargar el estado de la cuenta'); return; }
        renderTelegramSection(container, data.telegram_linked);
    } catch (e) {
        section.innerHTML = errorMessage('Error de red: ' + e.message);
    }
}

function renderTelegramSection(container, linked) {
    const section = container.querySelector('#account-telegram-section');
    section.innerHTML =
        '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;margin-bottom:10px;">🔔 ALERTAS DE WATCHLIST POR TELEGRAM</div>'
        + (linked
            ? '<div style="color:var(--color-accent);font-size:13px;margin-bottom:12px;">✅ Vinculado — tus alertas de Watchlist te llegarán aquí en cuanto se disparen.</div>'
              + '<button id="tg-unlink-btn" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:6px 16px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:12px;">DESVINCULAR</button>'
            : '<div style="color:var(--color-muted);font-size:13px;margin-bottom:12px;">Sin vincular — tus alertas de Watchlist solo se ven en la campanita de la web.</div>'
              + '<button id="tg-link-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">VINCULAR TELEGRAM</button>');

    const linkBtn = section.querySelector('#tg-link-btn');
    if (linkBtn) linkBtn.addEventListener('click', () => startLinking(container));

    const unlinkBtn = section.querySelector('#tg-unlink-btn');
    if (unlinkBtn) unlinkBtn.addEventListener('click', () => doUnlink(container));
}

async function startLinking(container) {
    const section = container.querySelector('#account-telegram-section');
    section.innerHTML = '<div style="color:var(--color-muted);font-size:13px;">Generando enlace…</div>';
    try {
        const res = await fetch('/api/v1/auth/telegram-link', { method: 'POST', headers: authHeader() });
        const data = await res.json();
        if (res.status === 503) {
            section.innerHTML = '<div style="color:var(--color-muted);font-size:13px;">Las notificaciones por Telegram no están disponibles todavía en este servidor.</div>';
            return;
        }
        if (!res.ok || !data.ok) {
            section.innerHTML = errorMessage(data.detail || data.error || 'No se pudo generar el enlace');
            return;
        }
        renderLinkPending(container, data.deep_link);
    } catch (e) {
        section.innerHTML = errorMessage('Error de red: ' + e.message);
    }
}

function renderLinkPending(container, deepLink) {
    const section = container.querySelector('#account-telegram-section');
    section.innerHTML =
        '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.06em;margin-bottom:10px;">🔔 ALERTAS DE WATCHLIST POR TELEGRAM</div>'
        + '<div style="color:var(--color-text);font-size:13px;margin-bottom:12px;">1. Abre el enlace y pulsa "Iniciar" en Telegram.<br>2. Vuelve aquí y pulsa "Ya lo vinculé".</div>'
        + '<a href="' + esc(safeUrl(deepLink)) + '" target="_blank" rel="noopener" style="display:inline-block;background:var(--color-accent);color:#000;border-radius:var(--radius);padding:8px 20px;font-family:var(--font-mono);font-size:12px;font-weight:500;text-decoration:none;margin-bottom:12px;">ABRIR EN TELEGRAM</a>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-bottom:12px;">El enlace caduca a los 15 minutos.</div>'
        + '<button id="tg-check-btn" style="background:none;border:1px solid var(--color-border);color:var(--color-text);padding:6px 16px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:12px;">YA LO VINCULÉ, COMPROBAR</button>';

    section.querySelector('#tg-check-btn').addEventListener('click', () => loadStatus(container));
}

async function doUnlink(container) {
    const section = container.querySelector('#account-telegram-section');
    try {
        const res = await fetch('/api/v1/auth/telegram-unlink', { method: 'POST', headers: authHeader() });
        const data = await res.json();
        if (!res.ok || !data.ok) { section.innerHTML = errorMessage(data.detail || 'No se pudo desvincular'); return; }
        renderTelegramSection(container, false);
    } catch (e) {
        section.innerHTML = errorMessage('Error de red: ' + e.message);
    }
}
