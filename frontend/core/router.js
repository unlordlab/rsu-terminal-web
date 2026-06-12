import { initTheme } from '/core/theme.js';
import { renderSidebar } from '/components/sidebar.js';
import { renderTopbar } from '/components/topbar.js';

// Mapa de rutas → módulos. Añadir aquí cada nuevo módulo.
const ROUTES = {
  '/':          () => import('/pages/dashboard.js'),
  '/market':    () => import('/pages/market.js'),
  '/cartera':   () => import('/pages/cartera.js'),
  '/rsrw':      () => import('/pages/rsrw.js'),
  '/spxl':      () => import('/pages/spxl.js'),
  '/research':  () => import('/pages/research.js'),
  '/canslim':   () => import('/pages/canslim.js'),
};

async function navigate(path) {
  const view = document.getElementById('view');
  view.innerHTML = '<p style="color:var(--color-muted)">Cargando...</p>';

  const loader = ROUTES[path] || ROUTES['/'];
  const module = await loader();
  await module.render(view);

  // Actualizar URL sin recargar
  history.pushState({}, '', path);
}

// Arranque
initTheme();
renderSidebar(document.getElementById('sidebar'), navigate);
renderTopbar(document.getElementById('topbar'));

// Routing inicial
navigate(location.pathname);

// Navegación con botones atrás/adelante del browser
window.addEventListener('popstate', () => navigate(location.pathname));
