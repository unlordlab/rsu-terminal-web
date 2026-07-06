const NAV_ITEMS = [
    { path: '/',          label: 'Dashboard',    icon: 'D' },
    { path: '/manifiesto', label: 'Manifiesto',  icon: '📜' },
    { path: '/market',    label: 'Market',       icon: 'M' },
    { path: '/cartera',   label: 'Cartera',      icon: 'C' },
    { path: '/rsrw',      label: 'RS/RW',        icon: 'R' },
    { path: '/scanner',   label: 'Scanner',      icon: '⚡' },
    { path: '/newsfeed',  label: 'News Feed',    icon: 'N' },
    { path: '/tesis',     label: 'Tesis', icon: 'T' },
    { path: '/spxl',      label: 'SPXL',         icon: 'S' },
    { path: '/btc-stratum', label: 'BTC Stratum', icon: '₿' },
    { path: '/options', label: 'Options Flow', icon: 'O' },
    { path: '/research',  label: 'Research',     icon: 'I' },
    { path: '/insider',   label: 'Insider Flow',  icon: '🔍' },
    { path: '/academy', label: 'Academy', icon: 'Ac' },
    { path: '/roadmap', label: 'Roadmap 2026', icon: 'R' },
    { path: '/canslim',   label: 'CANSLIM',      icon: 'K' },
    { path: '/algoritmo', label: 'RSU Algoritmo',icon: 'A' },
    { path: '/disclaimer', label: 'Disclaimer', icon: '⚖' },
];

export function renderSidebar(container, navigate) {
    const style = document.createElement('style');
    style.textContent = '.nav-item { display:flex; align-items:center; gap:10px; padding:0.6rem 1rem; color:var(--color-muted); text-decoration:none; border-left:2px solid transparent; font-size:13px; cursor:pointer; } .nav-item:hover { color:var(--color-text); background:var(--color-surface2); } .nav-item.active { color:var(--color-accent); border-left-color:var(--color-accent); background:var(--color-surface2); }';
    document.head.appendChild(style);

    const header = document.createElement('div');
    header.style.cssText = 'padding:1.25rem 1rem 1rem; border-bottom:1px solid var(--color-border); margin-bottom:0.5rem;';
    const logoStyle = document.createElement('style');
    logoStyle.textContent = `
        @keyframes logo-pulse {
            0%, 100% { box-shadow: 0 0 8px rgba(0,255,173,0.4), 0 0 16px rgba(0,255,173,0.2); }
            50%       { box-shadow: 0 0 14px rgba(0,255,173,0.7), 0 0 28px rgba(0,255,173,0.3), 0 0 40px rgba(0,217,255,0.1); }
        }
        .rsu-logo {
            animation: logo-pulse 3s ease-in-out infinite;
            transition: transform 0.3s ease;
        }
        .rsu-logo:hover {
            transform: scale(1.08) rotate(3deg);
        }
    `;
    document.head.appendChild(logoStyle);

    header.innerHTML = '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        + '<img src="/assets/logo.png" class="rsu-logo" style="width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid var(--color-accent);" onerror="this.style.display=\'none\'">'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:15px;letter-spacing:0.12em;text-shadow:var(--glow-text);">RSU TERMINAL</div>'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">v2.0 FastAPI</div>'
        + '</div>'
        + '</div>';

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

    container.appendChild(header);
    container.appendChild(nav);
    setActive(location.pathname);
}

export function setActiveNavItem(path) {
    setActive(path);
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