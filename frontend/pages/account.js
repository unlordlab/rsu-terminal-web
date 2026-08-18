import { authHeader } from '/core/api.js';
import { errorMessage, esc, safeUrl } from '/core/ui.js';


let _pollTimer = null;

export async function render(container) {
    container.innerHTML = pageShell();
    await loadStatus(container);
    wireDatos(container);
}

export function cleanup() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

function pageShell() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">⚙ MI CUENTA</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Notificaciones y datos personales</div>'
        + '</div>'
        + '<div id="account-telegram-section" style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;max-width:520px;">'
        + '<div style="color:var(--color-text);font-size:13px;">Cargando…</div>'
        + '</div>'
        + seccionDatos();
}

// Los dos derechos que hasta el 18/08/2026 no tenían ni código ni botón:
// llevarse los datos y borrar la cuenta. Van juntos y en la misma página
// porque quien busca uno suele buscar el otro.
function seccionDatos() {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;max-width:520px;margin-top:1rem;">'
        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:.08em;margin-bottom:10px;">TUS DATOS</div>'
        + '<div style="color:var(--color-text);font-size:13px;margin-bottom:10px;">Puedes descargar todo lo que guardamos de ti, o borrar la cuenta entera.</div>'
        + '<button id="btn-descargar-datos" style="padding:7px 14px;background:transparent;color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);font-family:var(--font-mono);font-size:12px;cursor:pointer;">DESCARGAR MIS DATOS</button>'
        + '<div id="datos-resultado" style="font-size:12px;margin-top:10px;"></div>'
        + '<div style="border-top:1px solid var(--color-border);margin-top:16px;padding-top:14px;">'
        // El aviso va ANTES del botón, no después: leerlo cuando ya has
        // pulsado no sirve de nada.
        + '<div style="color:#f23645;font-size:12px;margin-bottom:8px;">Borrar la cuenta es <strong>irreversible</strong>. Se borran tu cuenta, tu watchlist, tus alertas, tu progreso de la academia, tus mensajes al chat y tu actividad. No hay papelera.</div>'
        + '<button id="btn-borrar-cuenta" style="padding:7px 14px;background:transparent;color:#f23645;border:1px solid #f23645;border-radius:var(--radius);font-family:var(--font-mono);font-size:12px;cursor:pointer;">BORRAR MI CUENTA</button>'
        + '<div id="borrar-zona" style="margin-top:10px;"></div>'
        + '</div></div>';
}

function wireDatos(container) {
    const salida = container.querySelector('#datos-resultado');

    container.querySelector('#btn-descargar-datos').addEventListener('click', async () => {
        salida.innerHTML = '<span style="color:var(--color-muted);">Reuniendo tus datos…</span>';
        try {
            const res = await fetch('/api/v1/auth/mis-datos', { headers: authHeader() });
            const data = await res.json();
            if (!res.ok) { salida.innerHTML = errorMessage(data.detail || 'No se pudo preparar la descarga'); return; }
            // Descarga local: el JSON ya está en el navegador, no hace falta
            // que el servidor guarde un fichero en ningún sitio.
            const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)],
                                                    { type: 'application/json' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mis-datos-rsu-terminal.json';
            a.click();
            URL.revokeObjectURL(url);
            const n = Object.values(data.datos || {}).reduce((t, f) => t + f.length, 0);
            salida.innerHTML = '<span style="color:var(--color-accent);">Descargado: ' + esc(n) + ' registros en ' + esc(Object.keys(data.datos || {}).length) + ' apartados.</span>';
        } catch (e) {
            salida.innerHTML = errorMessage('Error de red: ' + e.message);
        }
    });

    container.querySelector('#btn-borrar-cuenta').addEventListener('click', () => {
        const zona = container.querySelector('#borrar-zona');
        // Se pide la contraseña ANTES de borrar, no un "¿estás seguro?": una
        // sesión abierta en un ordenador ajeno no debe bastar para esto.
        zona.innerHTML = '<div style="font-size:12px;color:var(--color-muted);margin-bottom:6px;">Escribe tu contraseña para confirmar:</div>'
            + '<input id="borrar-pwd" type="password" placeholder="········" style="padding:6px 10px;background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);font-family:var(--font-mono);font-size:12px;">'
            + ' <button id="borrar-confirmar" style="padding:6px 12px;background:#f23645;color:#fff;border:none;border-radius:var(--radius);font-family:var(--font-mono);font-size:12px;cursor:pointer;">CONFIRMAR BORRADO</button>'
            + '<div id="borrar-msg" style="font-size:12px;margin-top:8px;"></div>';

        zona.querySelector('#borrar-confirmar').addEventListener('click', async () => {
            const msg = zona.querySelector('#borrar-msg');
            const pwd = zona.querySelector('#borrar-pwd').value;
            if (!pwd) { msg.innerHTML = '<span style="color:#ffb800;">Escribe tu contraseña.</span>'; return; }
            msg.innerHTML = '<span style="color:var(--color-muted);">Borrando…</span>';
            try {
                const res = await fetch('/api/v1/auth/borrar-cuenta', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...authHeader() },
                    body: JSON.stringify({ password: pwd }),
                });
                const data = await res.json();
                if (!res.ok) { msg.innerHTML = errorMessage(data.detail || 'No se pudo borrar'); return; }
                // Se dice CUÁNTO se borró, no un "listo" a secas: es la
                // diferencia entre creer que se borró y verlo.
                msg.innerHTML = '<span style="color:var(--color-accent);">Cuenta borrada: '
                    + esc(data.total) + ' registros eliminados. Cerrando sesión…</span>';
                setTimeout(() => { window.location.href = '/login'; }, 2500);
            } catch (e) {
                msg.innerHTML = errorMessage('Error de red: ' + e.message);
            }
        });
    });
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
