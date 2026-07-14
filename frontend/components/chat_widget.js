// ── CHAT DE AYUDA RSU ────────────────────────────────────────────────────────
//
// Burbuja flotante disponible en todas las páginas. Responde preguntas sobre
// la metodología del algoritmo RSU, las funcionalidades de la terminal, y el
// contenido de la Academia — con contexto real recuperado de la base de
// conocimiento (backend/services/chat_service.py), no respuestas genéricas.
//
// Un único componente, montado una sola vez en el bootstrap (core/router.js),
// igual que command_palette.js.

let bubbleEl   = null;
let panelEl    = null;
let isOpen     = false;
let cargando   = false;
let mensajes   = [];
let historialCargado = false;

function authHeader() {
    const token = sessionStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

export function initChatWidget() {
    if (bubbleEl) return; // ya montado

    bubbleEl = document.createElement('div');
    bubbleEl.id = 'rsu-chat-bubble';
    bubbleEl.innerHTML = '💬';
    bubbleEl.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; width: 52px; height: 52px;
        border-radius: 50%; background: var(--color-accent); color: #000;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; cursor: pointer; z-index: 9998;
        box-shadow: 0 2px 12px rgba(0,0,0,0.4);
        transition: transform 0.15s ease;
    `;
    bubbleEl.addEventListener('mouseenter', () => bubbleEl.style.transform = 'scale(1.08)');
    bubbleEl.addEventListener('mouseleave', () => bubbleEl.style.transform = 'scale(1)');
    bubbleEl.addEventListener('click', toggleChat);
    document.body.appendChild(bubbleEl);

    panelEl = document.createElement('div');
    panelEl.id = 'rsu-chat-panel';
    panelEl.style.cssText = `
        position: fixed; bottom: 84px; right: 20px; width: 380px; height: 540px;
        max-height: calc(100vh - 110px);
        background: var(--color-surface); border: 1px solid var(--color-border);
        border-radius: var(--radius); box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        display: none; flex-direction: column; z-index: 9999; overflow: hidden;
        font-family: var(--font-mono);
    `;
    panelEl.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--color-border);flex-shrink:0;">
            <div>
                <div style="color:var(--color-accent);font-size:13px;letter-spacing:0.05em;text-shadow:var(--glow-text);">ASISTENTE RSU</div>
                <div style="color:var(--color-muted);font-size:10px;margin-top:2px;">Metodología, funcionalidades, Academia</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
                <button id="rsu-chat-clear" title="Borrar conversación" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);width:24px;height:24px;border-radius:4px;cursor:pointer;font-size:12px;">🗑</button>
                <button id="rsu-chat-close" title="Cerrar" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);width:24px;height:24px;border-radius:4px;cursor:pointer;font-size:13px;">✕</button>
            </div>
        </div>
        <div id="rsu-chat-messages" style="flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px;"></div>
        <div style="padding:10px 12px;border-top:1px solid var(--color-border);flex-shrink:0;">
            <div style="display:flex;gap:8px;">
                <input id="rsu-chat-input" type="text" placeholder="Pregunta lo que sea sobre RSU Terminal..."
                    style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">
                <button id="rsu-chat-send" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:8px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:600;">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(panelEl);

    panelEl.querySelector('#rsu-chat-close').addEventListener('click', toggleChat);
    panelEl.querySelector('#rsu-chat-clear').addEventListener('click', limpiarConversacion);
    panelEl.querySelector('#rsu-chat-send').addEventListener('click', enviarMensaje);
    panelEl.querySelector('#rsu-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !cargando) enviarMensaje();
    });
}

function toggleChat() {
    isOpen = !isOpen;
    panelEl.style.display = isOpen ? 'flex' : 'none';
    if (isOpen && !historialCargado) {
        cargarHistorial();
    }
    if (isOpen) {
        setTimeout(() => panelEl.querySelector('#rsu-chat-input')?.focus(), 50);
    }
}

async function cargarHistorial() {
    const cont = panelEl.querySelector('#rsu-chat-messages');
    try {
        const res  = await fetch('/api/v1/chat/historial', { headers: authHeader() });
        const data = await res.json();
        historialCargado = true;
        if (data.ok && data.mensajes.length) {
            mensajes = data.mensajes;
            renderMensajes();
        } else {
            mostrarBienvenida();
        }
    } catch (e) {
        mostrarBienvenida();
    }
}

function mostrarBienvenida() {
    const cont = panelEl.querySelector('#rsu-chat-messages');
    cont.innerHTML = `<div style="color:var(--color-muted);font-size:11px;line-height:1.6;padding:8px;">
        👋 Pregúntame lo que quieras sobre la metodología del algoritmo RSU, cómo funciona cualquier sección de la terminal, o el contenido de la Academia.
    </div>`;
}

function renderMensajes() {
    const cont = panelEl.querySelector('#rsu-chat-messages');
    if (!mensajes.length) {
        mostrarBienvenida();
        return;
    }
    cont.innerHTML = mensajes.map(m => burbujaMensaje(m.rol, m.mensaje)).join('');
    cont.scrollTop = cont.scrollHeight;
}

function burbujaMensaje(rol, texto, esCargando) {
    const esUser = rol === 'user';
    const bg     = esUser ? 'var(--color-accent)' : 'var(--color-bg,#0a0a0a)';
    const color  = esUser ? '#000' : 'var(--color-text)';
    const align  = esUser ? 'flex-end' : 'flex-start';
    const borde  = esUser ? 'none' : '1px solid var(--color-border)';
    const contenido = esCargando
        ? '<span style="opacity:0.6;">Pensando...</span>'
        : escapeHtml(texto).replace(/\n/g, '<br>');
    return `<div style="align-self:${align};max-width:85%;background:${bg};color:${color};border:${borde};border-radius:10px;padding:8px 12px;font-size:12px;line-height:1.5;">${contenido}</div>`;
}

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

async function enviarMensaje() {
    if (cargando) return;
    const input = panelEl.querySelector('#rsu-chat-input');
    const texto = input.value.trim();
    if (!texto) return;

    input.value = '';
    cargando = true;
    mensajes.push({ rol: 'user', mensaje: texto });
    renderMensajes();

    const cont = panelEl.querySelector('#rsu-chat-messages');
    cont.insertAdjacentHTML('beforeend', '<div id="rsu-chat-loading">' + burbujaMensaje('assistant', '', true) + '</div>');
    cont.scrollTop = cont.scrollHeight;

    try {
        const res  = await fetch('/api/v1/chat/mensaje', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeader() },
            body: JSON.stringify({ mensaje: texto }),
        });
        const data = await res.json();
        panelEl.querySelector('#rsu-chat-loading')?.remove();
        if (data.ok) {
            mensajes.push({ rol: 'assistant', mensaje: data.respuesta });
        } else {
            mensajes.push({ rol: 'assistant', mensaje: '⚠ ' + (data.error || 'No se pudo obtener respuesta.') });
        }
    } catch (e) {
        panelEl.querySelector('#rsu-chat-loading')?.remove();
        mensajes.push({ rol: 'assistant', mensaje: '⚠ Error de conexión. Inténtalo de nuevo.' });
    }
    cargando = false;
    renderMensajes();
}

async function limpiarConversacion() {
    try {
        await fetch('/api/v1/chat/historial', { method: 'DELETE', headers: authHeader() });
    } catch (e) { /* no bloquear la limpieza visual aunque falle la llamada */ }
    mensajes = [];
    renderMensajes();
}