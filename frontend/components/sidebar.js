import { cycleTheme, getCurrentTheme } from '/core/theme.js';

const NAV_ITEMS = [
    { path: '/',         label: 'Dashboard',  icon: '⌂' },
    { path: '/market',   label: 'Market',     icon: '◈' },
    { path: '/cartera',  label: 'Cartera',    icon: '◎' },
    { path: '/rsrw',     label: 'RS/RW',      icon: '◆' },
    { path: '/spxl',     label: 'SPXL',       icon: '▲' },
    { path: '/research', label: 'Research',   icon: '◉' },
    { path: '/canslim',  label: 'CANSLIM',    icon: '◈' },
];

export function renderSidebar(container, navigate) {
    const style = document.createElement('style');
    style.textContent = `
        .nav-item { display:flex; align-items:center; gap:10px; padding:0.6rem 1rem; color:var(--color-muted); text-decoration:none; transition:all var(--transition); border-left:2px solid transparent; font-size:13px; cursor:pointer; }
        .nav-item:hover { color:var(--color-text); background:var(--color-surface2); }
        .nav-item.active { color:var(--color-accent); border-left-color:var(--color-accent); background:var(--color-surface2); text-shadow:var(--glow-text); }
    `;
    document.head.appendChild(style);

    const header = document.createElement('div');
    header.style.cssText = 'padding:1.25rem 1rem 1rem; border-bottom:1px solid var(--color-border); margin-bottom:0.5rem;';
    header.innerHTML = '<div style="color:var(--color-accent);font-size:16px;letter-spacing:0.1em;text-shadow:var(--glow-text);">RSU TERMINAL</div><div style="color:var(--color-muted);font-size:11px;margin-top:2px;">v2.0 · FastAPI</div>';
    container.appendChild(header);

    const nav = document.createElement('nav');
    nav.style.padding = '0.5rem 0';

    NAV_ITEMS.forEach(item => {
        const a = document.createElement('a');
        a.href = item.path;
        a.className = 'nav-item';
        a.setAttribute('data-path', item.path);

        const icon = document.createElement('span');
        icon.style.cssText = 'font-size:14px;width:16px;text-align:center;';
        icon.textContent = item.icon;

        const label = document.createElement('span');
        label.textContent = item.label;

        a.appendChild(icon);
        a.appendChild(label);

        a.addEventListener('click', e => {
            e.preventDefault();
