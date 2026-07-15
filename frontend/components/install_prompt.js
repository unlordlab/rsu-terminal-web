// ── AVISO DE INSTALACIÓN PWA ─────────────────────────────────────────────────
//
// Android/Chrome/Edge: automático de verdad — captura beforeinstallprompt y
// muestra un botón propio que dispara el diálogo nativo de instalación.
// iOS Safari: Apple NO permite disparar la instalación por JavaScript bajo
// ningún concepto — lo único posible es detectar iOS y mostrar instrucciones
// manuales (compartir → Añadir a pantalla de inicio). No es una limitación
// de este código, es así en cualquier web del mundo.
//
// Se oculta solo si: ya está instalada (modo standalone), el usuario la
// cerró hace menos de 14 días, o la pantalla es de tamaño escritorio (esto
// es una función pensada para móvil).

const DISMISS_KEY = 'rsu_install_dismissed_at';
const DISMISS_DAYS = 14;

let deferredPrompt = null;
let bannerEl = null;

function yaInstalada() {
    return window.matchMedia('(display-mode: standalone)').matches
        || window.navigator.standalone === true; // iOS Safari en modo standalone
}

function esIOS() {
    return /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
}

function fueDescartadoRecientemente() {
    const raw = localStorage.getItem(DISMISS_KEY);
    if (!raw) return false;
    const dias = (Date.now() - Number(raw)) / (1000 * 60 * 60 * 24);
    return dias < DISMISS_DAYS;
}

export function initInstallPrompt() {
    if (yaInstalada() || fueDescartadoRecientemente()) return;
    if (window.innerWidth >= 768) return; // pensado para móvil, no molestar en escritorio

    if (esIOS()) {
        // iOS no dispara ningún evento — se muestra directamente el aviso manual
        mostrarBanner({
            texto: 'Instala RSU Terminal: toca <strong>Compartir</strong> ⬆️ y luego <strong>"Añadir a pantalla de inicio"</strong>',
            conBoton: false,
        });
        return;
    }

    // Android/Chrome/Edge: esperar al evento antes de mostrar nada — si el
    // navegador no lo dispara (ya instalada, no cumple criterios, etc.),
    // simplemente no aparece el aviso, sin necesidad de comprobarlo a mano.
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        mostrarBanner({
            texto: 'Instala RSU Terminal en tu móvil para acceso rápido',
            conBoton: true,
        });
    });

    window.addEventListener('appinstalled', () => {
        deferredPrompt = null;
        if (bannerEl) bannerEl.remove();
    });
}

function mostrarBanner({ texto, conBoton }) {
    if (bannerEl) return; // ya mostrado
    bannerEl = document.createElement('div');
    bannerEl.id = 'rsu-install-banner';
    bannerEl.style.cssText = `
        position: relative; z-index: 9997;
        background: var(--color-surface); border-bottom: 1px solid var(--color-accent);
        padding: 10px 14px; display: flex; align-items: center; gap: 10px;
        font-family: var(--font-mono); font-size: 12px; color: var(--color-text);
    `;
    bannerEl.innerHTML = `
        <span style="flex:1;line-height:1.4;">${texto}</span>
        ${conBoton ? '<button id="rsu-install-btn" style="background:var(--color-accent);color:var(--color-bg,#0a0a0a);border:none;border-radius:4px;padding:6px 12px;font-family:var(--font-mono);font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;">Instalar</button>' : ''}
        <button id="rsu-install-close" style="background:none;border:none;color:var(--color-muted);font-size:16px;cursor:pointer;padding:0 4px;">✕</button>
    `;
    document.body.prepend(bannerEl);

    if (conBoton) {
        bannerEl.querySelector('#rsu-install-btn').addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            await deferredPrompt.userChoice; // no bloquea la UI si el usuario cancela, solo espera su elección
            deferredPrompt = null;
            bannerEl.remove();
        });
    }
    bannerEl.querySelector('#rsu-install-close').addEventListener('click', () => {
        localStorage.setItem(DISMISS_KEY, String(Date.now()));
        bannerEl.remove();
        bannerEl = null;
    });
}