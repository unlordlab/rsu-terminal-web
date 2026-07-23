import { hasTier } from '/core/api.js';

export const NAV_ITEMS = [
    { path: '/',          label: 'Dashboard',    icon: 'D' },
    { path: '/manifiesto', label: 'Manifiesto',  icon: '📜' },
    { path: '/market',    label: 'Market',       icon: 'M' },
    { path: '/cartera',   label: 'Cartera',      icon: 'C', minTier: 'tier1' },
    { path: '/rsrw',      label: 'RS/RW',        icon: 'R' },
    { path: '/scanner',   label: 'Scanner',      icon: '⚡' },
    { path: '/watchlist', label: 'Watchlist',    icon: '★' },
    { path: '/newsfeed',  label: 'News Feed',    icon: 'N' },
    { path: '/tesis',     label: 'Tesis', icon: 'T', minTier: 'tier1' },
    { path: '/equipo',    label: 'Equipo RSU',   icon: '👥' },
    { path: '/spxl',      label: 'SPXL',         icon: 'S' },
    { path: '/btc-stratum', label: 'BTC Stratum', icon: '₿' },
    { path: '/options', label: 'Options Flow', icon: 'O' },
    { path: '/research',  label: 'Research',     icon: 'I' },
    { path: '/insider',   label: 'Insider Flow',  icon: '🔍' },
    { path: '/congress',  label: 'Congress Trading', icon: '🏛️' },
    { path: '/academy', label: 'Academy', icon: 'Ac' },
    { path: '/roadmap', label: 'Roadmap 2026', icon: 'R' },
    { path: '/community', label: 'Comunidad', icon: '👥' },
    { path: '/canslim',   label: 'CANSLIM',      icon: 'K' },
    { path: '/algoritmo', label: 'RSU Algoritmo',icon: 'A' },
    { path: '/disclaimer', label: 'Disclaimer', icon: '⚖' },
];

export function renderSidebar(container, navigate) {
    container.innerHTML = '';

    if (!document.getElementById('sidebar-nav-style')) {
        const style = document.createElement('style');
        style.id = 'sidebar-nav-style';
        style.textContent = '.nav-item { display:flex; align-items:center; gap:10px; padding:0.6rem 1rem; color:var(--color-muted); text-decoration:none; border-left:2px solid transparent; font-size:13px; cursor:pointer; } .nav-item:hover { color:var(--color-text); background:var(--color-surface2); } .nav-item.active { color:var(--color-accent); border-left-color:var(--color-accent); background:var(--color-surface2); }';
        document.head.appendChild(style);
    }

    const header = document.createElement('div');
    header.style.cssText = 'padding:1.25rem 1rem 1rem; border-bottom:1px solid var(--color-border); margin-bottom:0.5rem;';
    if (!document.getElementById('sidebar-logo-style')) {
        const logoStyle = document.createElement('style');
        logoStyle.id = 'sidebar-logo-style';
        logoStyle.textContent = `
        @keyframes logo-pulse {
            0%, 100% { filter: drop-shadow(0 0 4px var(--color-accent)) drop-shadow(0 0 8px color-mix(in srgb, var(--color-accent) 50%, transparent)); }
            50%       { filter: drop-shadow(0 0 8px var(--color-accent)) drop-shadow(0 0 16px color-mix(in srgb, var(--color-accent) 60%, transparent)); }
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
    }

    header.innerHTML = '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        + '<div class="rsu-logo" style="width:52px;height:52px;flex-shrink:0;background-color:var(--color-accent);'
        + '-webkit-mask-image:url(/assets/logo-icon.png);mask-image:url(/assets/logo-icon.png);'
        + '-webkit-mask-size:contain;mask-size:contain;-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;'
        + '-webkit-mask-position:center;mask-position:center;"></div>'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:15px;letter-spacing:0.12em;text-shadow:var(--glow-text);">RSU TERMINAL</div>'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;">v2.0</div>'
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

        if (item.path === '/watchlist') {
            const badge = document.createElement('span');
            badge.id = 'watchlist-alert-badge';
            badge.style.cssText = 'margin-left:auto;background:#f23645;color:#fff;font-size:9px;font-weight:600;border-radius:8px;padding:1px 6px;display:none;';
            a.appendChild(badge);
        }

        if (item.minTier && !hasTier(item.minTier)) {
            const lock = document.createElement('span');
            lock.textContent = '🔒';
            lock.style.cssText = 'margin-left:auto;font-size:10px;opacity:0.6;';
            a.appendChild(lock);
            a.title = 'Requiere plan Tier 1 o superior';
        }

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
    startAlertBadgePolling();
}

// Campanita de alertas disparadas: consulta el contador de "no vistas" y lo
// pinta como badge junto a Watchlist en el sidebar. Poll cada 60s (misma
// cadencia que el resto de refrescos en vivo de la terminal) — no hay push
// en tiempo real todavía, ver nota en routers/ws.py (alerts_check_loop).
let _alertBadgeInterval = null;

function startAlertBadgePolling() {
    refreshAlertBadge();
    if (_alertBadgeInterval) clearInterval(_alertBadgeInterval);
    _alertBadgeInterval = setInterval(refreshAlertBadge, 60000);
}

function refreshAlertBadge() {
    const token = localStorage.getItem('rsu_token') || sessionStorage.getItem('rsu_token');
    if (!token) return;
    fetch('/api/v1/watchlist/alerts/unseen-count', { headers: { 'Authorization': 'Bearer ' + token } })
        .then(function(res) { return res.ok ? res.json() : null; })
        .then(function(data) {
            const badge = document.getElementById('watchlist-alert-badge');
            if (!badge || !data) return;
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(function() { /* silencioso: no interrumpe la navegación por un fallo de red puntual */ });
}

window.__refreshAlertBadge = refreshAlertBadge;

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