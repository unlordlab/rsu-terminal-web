const NAV_ITEMS = [
    { path: '/',          label: 'Dashboard',    icon: 'D' },
    { path: '/market',    label: 'Market',       icon: 'M' },
    { path: '/cartera',   label: 'Cartera',      icon: 'C' },
    { path: '/rsrw',      label: 'RS/RW',        icon: 'R' },
    { path: '/spxl',      label: 'SPXL',         icon: 'S' },
    { path: '/research',  label: 'Research',     icon: 'I' },
    { path: '/canslim',   label: 'CANSLIM',      icon: 'K' },
    { path: '/algoritmo', label: 'RSU Algoritmo',icon: 'A' },
];

export function renderSidebar(container, navigate) {
    const style = document.createElement('style');
    style.textContent = '.nav-item { display:flex; align-items:center; gap:10px; padding:0.6rem 1rem; color:var(--color-muted); text-decoration:none; border-left:2px solid transparent; font-size:13px; cursor:pointer; } .nav-item:hover { color:var(--color-text); background:var(--color-surface2); } .nav-item.active { color:var(--color-accent); border-left-color:var(--color-accent); background:var(--color-surface2); }';
    document.head.appendChild(style);

    const header = document.createElement('div');
    header.style.cssText = 'padding:1.25rem 1rem 1rem; border-bottom:1px solid var(--color-border); margin-bottom:0.5rem;';
    header.innerHTML = '<div style="color:var(--color-accent);font-size:16px;letter-spacing:0.1em;">RSU TERMINAL</div><div style="color:var(--color-muted);font-size:11px;margin-top:2px;">v2.0 FastAPI</div>';
    container.appendChild(header);

    const nav = document.createElement('nav');
    nav.style.padding = '0.5rem 0';

    NAV_ITEMS.forEach(function(item) {
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

        a.addEventListener('click', function(e) {
            e.preventDefault();
            setActive(item.path);
            navigate(item.path);
        });

        nav.appendChild(a);
    });

    container.appendChild(nav);
    setActive(location.pathname);
}

function setActive(path) {
    document.querySelectorAll('.nav-item').forEach(function(link) {
        if (link.getAttribute('data-path') === path) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}
