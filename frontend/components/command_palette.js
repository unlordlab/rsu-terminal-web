// ── COMMAND PALETTE ──────────────────────────────────────────────────────────
//
// Ctrl+K (Cmd+K en Mac) abre un buscador rápido con TODAS las secciones de la
// terminal, filtrable escribiendo. Además, "g" + una letra navega
// directamente a las ~10 secciones más usadas sin abrir nada (mismo patrón
// que Gmail/GitHub/Linear). "?" muestra la chuleta de atajos.
//
// Un único componente, montado una sola vez en el bootstrap (core/router.js),
// no por página — igual que sidebar.js y topbar.js.

import { cycleTheme } from '/core/theme.js';

let paletteEl   = null;
let helpEl      = null;
let navigateFn  = null;
let allItems    = [];
let filteredItems = [];
let selectedIndex = 0;
let mode = 'nav'; // 'nav' (buscador) | 'help' (chuleta de atajos)

const ACTIONS = [
    { type: 'action', label: 'Cambiar tema (CRT / Dark Pro / Light / Bubblebath)', icon: '🎨', run: () => cycleTheme() },
];

// Atajos directos "g + letra" — solo las secciones más usadas. El palette
// (Ctrl+K) ya cubre el 100% de las secciones buscando por nombre; esto es
// un atajo rápido extra para no tener que abrir nada en el día a día.
const QUICK_KEYS = {
    'd': { path: '/',            label: 'Dashboard' },
    'm': { path: '/market',      label: 'Market' },
    'c': { path: '/cartera',     label: 'Cartera' },
    's': { path: '/scanner',     label: 'Scanner' },
    'w': { path: '/watchlist',   label: 'Watchlist' },
    'r': { path: '/research',    label: 'Research' },
    'i': { path: '/insider',     label: 'Insider Flow' },
    'o': { path: '/options',     label: 'Options Flow' },
    'a': { path: '/academy',     label: 'Academia' },
    'u': { path: '/community',   label: 'Comunidad' },
};

export function initCommandPalette(navItems, navigate) {
    navigateFn = navigate;
    allItems = [
        ...navItems.map(n => ({ type: 'nav', label: n.label, icon: n.icon, path: n.path })),
        ...ACTIONS,
    ];
    _buildDOM();
    _bindKeys();
}

function _buildDOM() {
    if (document.getElementById('cmdk-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'cmdk-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:none;align-items:flex-start;justify-content:center;padding-top:12vh;';
    overlay.innerHTML =
        '<div id="cmdk-box" style="width:520px;max-width:92vw;background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.5);">'
        + '<input id="cmdk-input" type="text" placeholder="Ir a una sección o acción..." autocomplete="off" spellcheck="false" '
        + 'style="width:100%;box-sizing:border-box;background:var(--color-bg,#0a0a0a);border:none;border-bottom:1px solid var(--color-border);padding:14px 16px;color:var(--color-text);font-family:var(--font-mono);font-size:14px;outline:none;">'
        + '<div id="cmdk-list" style="max-height:360px;overflow-y:auto;"></div>'
        + '<div style="padding:6px 14px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);display:flex;gap:14px;">'
        + '<span>↑↓ moverse</span><span>↵ ir</span><span>esc cerrar</span><span style="margin-left:auto;">? = atajos</span>'
        + '</div>'
        + '</div>';
    document.body.appendChild(overlay);
    paletteEl = overlay;

    overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) closePalette(); });

    const input = overlay.querySelector('#cmdk-input');
    input.addEventListener('input', () => _filter(input.value));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); _move(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); _move(-1); }
        else if (e.key === 'Enter')  { e.preventDefault(); _select(); }
        else if (e.key === 'Escape') { closePalette(); }
    });

    // Modal de ayuda — chuleta estática de atajos, separado del buscador
    const help = document.createElement('div');
    help.id = 'cmdk-help-overlay';
    help.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:none;align-items:center;justify-content:center;';
    help.innerHTML =
        '<div style="width:420px;max-width:90vw;background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.5);">'
        + '<div style="padding:12px 16px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:13px;letter-spacing:0.05em;">⌨ ATAJOS DE TECLADO</div>'
        + '<div style="padding:12px 16px;font-size:12px;color:var(--color-text);">'
        + _helpRow('Ctrl/Cmd + K', 'Buscador de secciones y acciones')
        + _helpRow('g luego d/m/c/s/w/r/i/o/a/u', 'Ir directo a Dashboard/Market/Cartera/Scanner/Watchlist/Research/Insider/Options/Academia/Comunidad')
        + _helpRow('?', 'Esta ayuda')
        + _helpRow('Esc', 'Cerrar cualquier ventana')
        + '</div>'
        + '<div style="padding:10px 16px;border-top:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">Pulsa Esc o haz clic fuera para cerrar</div>'
        + '</div>';
    document.body.appendChild(help);
    helpEl = help;
    help.addEventListener('mousedown', (e) => { if (e.target === help) closeHelp(); });
}

function _helpRow(keys, desc) {
    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid var(--color-border);">'
        + '<span style="color:var(--color-muted);font-size:11px;">' + desc + '</span>'
        + '<span style="color:var(--color-accent);font-size:11px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:4px;padding:2px 8px;white-space:nowrap;">' + keys + '</span>'
        + '</div>';
}

function _filter(query) {
    const q = query.trim().toLowerCase();
    filteredItems = !q ? allItems : allItems.filter(i => i.label.toLowerCase().includes(q));
    selectedIndex = 0;
    _renderList();
}

function _renderList() {
    const list = paletteEl.querySelector('#cmdk-list');
    if (!filteredItems.length) {
        list.innerHTML = '<div style="padding:16px;color:var(--color-muted);font-size:12px;text-align:center;">Sin resultados</div>';
        return;
    }
    list.innerHTML = filteredItems.map((item, i) => {
        const active = i === selectedIndex;
        return '<div class="cmdk-item" data-idx="' + i + '" style="display:flex;align-items:center;gap:10px;padding:10px 16px;cursor:pointer;font-size:13px;'
            + 'background:' + (active ? 'var(--color-accent)18' : 'transparent') + ';'
            + 'border-left:2px solid ' + (active ? 'var(--color-accent)' : 'transparent') + ';">'
            + '<span style="width:20px;text-align:center;color:var(--color-accent);">' + item.icon + '</span>'
            + '<span style="color:var(--color-text);">' + item.label + '</span>'
            + (item.type === 'action' ? '<span style="margin-left:auto;color:var(--color-muted);font-size:9px;">ACCIÓN</span>' : '')
            + '</div>';
    }).join('');
    list.querySelectorAll('.cmdk-item').forEach(el => {
        el.addEventListener('mouseenter', () => { selectedIndex = parseInt(el.dataset.idx, 10); _renderList(); });
        el.addEventListener('click', () => { selectedIndex = parseInt(el.dataset.idx, 10); _select(); });
    });
}

function _move(delta) {
    if (!filteredItems.length) return;
    selectedIndex = (selectedIndex + delta + filteredItems.length) % filteredItems.length;
    _renderList();
    const activeEl = paletteEl.querySelector('.cmdk-item[data-idx="' + selectedIndex + '"]');
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

function _select() {
    const item = filteredItems[selectedIndex];
    if (!item) return;
    closePalette();
    if (item.type === 'nav') navigateFn(item.path);
    else if (item.type === 'action') item.run();
}

export function openPalette() {
    if (!paletteEl) return;
    closeHelp();
    paletteEl.style.display = 'flex';
    const input = paletteEl.querySelector('#cmdk-input');
    input.value = '';
    _filter('');
    setTimeout(() => input.focus(), 10);
}

export function closePalette() {
    if (paletteEl) paletteEl.style.display = 'none';
}

export function openHelp() {
    if (!helpEl) return;
    closePalette();
    helpEl.style.display = 'flex';
}

export function closeHelp() {
    if (helpEl) helpEl.style.display = 'none';
}

function _isTypingContext(target) {
    const tag = (target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || target.isContentEditable;
}

let gPressedAt = 0;

function _bindKeys() {
    document.addEventListener('keydown', (e) => {
        const paletteOpen = paletteEl && paletteEl.style.display === 'flex';
        const helpOpen     = helpEl && helpEl.style.display === 'flex';

        // Ctrl+K / Cmd+K — funciona siempre, incluso escribiendo en un campo
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            paletteOpen ? closePalette() : openPalette();
            return;
        }

        if (helpOpen) {
            if (e.key === 'Escape') closeHelp();
            return;
        }
        if (paletteOpen) return; // el resto lo gestiona el propio input del palette

        if (_isTypingContext(e.target)) return; // no interferir al escribir en la propia página
        if (e.ctrlKey || e.metaKey || e.altKey) return;

        if (e.key === '?') { e.preventDefault(); openHelp(); return; }

        if (e.key.toLowerCase() === 'g') { gPressedAt = Date.now(); return; }

        if (gPressedAt && Date.now() - gPressedAt < 900) {
            const target = QUICK_KEYS[e.key.toLowerCase()];
            gPressedAt = 0;
            if (target) { e.preventDefault(); navigateFn(target.path); }
        }
    });
}