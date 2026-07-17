import { errorMessage } from '/core/ui.js';

let currentPage  = 1;
let activeRating = 'Todos';
let searchQuery  = '';

let _mdStylesInjected = false;

function ensureMarkdownStyles() {
    if (_mdStylesInjected) return;
    _mdStylesInjected = true;
    const style = document.createElement('style');
    style.textContent = `
        .tesis-markdown h1, .tesis-markdown h2, .tesis-markdown h3 {
            color: var(--color-accent); margin: 1.5rem 0 0.75rem; letter-spacing: 0.03em;
        }
        .tesis-markdown h1 { font-size: 18px; } .tesis-markdown h2 { font-size: 15px; } .tesis-markdown h3 { font-size: 13px; }
        .tesis-markdown p { margin: 0.6rem 0; }
        .tesis-markdown strong { color: var(--color-text); }
        .tesis-markdown ul, .tesis-markdown ol { padding-left: 1.4rem; margin: 0.5rem 0; }
        .tesis-markdown table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 12px; }
        .tesis-markdown th, .tesis-markdown td {
            border: 1px solid var(--color-border); padding: 6px 10px; text-align: left;
        }
        .tesis-markdown th { color: var(--color-accent); background: var(--color-surface2); }
        .tesis-markdown blockquote {
            border-left: 2px solid var(--color-accent); margin: 0.75rem 0; padding: 0.4rem 0 0.4rem 0.9rem;
            color: var(--color-muted); background: var(--color-surface2);
        }
        .tesis-markdown code { background: var(--color-surface2); padding: 1px 5px; border-radius: 3px; font-family: var(--font-mono); }
        .tesis-markdown hr { border: none; border-top: 1px solid var(--color-border); margin: 1.5rem 0; }
    `;
    document.head.appendChild(style);
}

function renderMarkdown(text) {
    ensureMarkdownStyles();
    try {
        if (window.marked) return window.marked.parse(text);
    } catch (e) {
        console.error('Error renderizando markdown:', e);
    }
    // Fallback si marked.js no cargó por lo que sea: texto plano con saltos de línea
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return '<pre style="white-space:pre-wrap;font-family:var(--font-mono);">' + escaped + '</pre>';
}
let allRatings   = ['Todos'];

export async function render(container) {
    container.innerHTML = header() + gallery();
    setupFilters(container);
    await loadGallery(container);
}

function header() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">TESIS</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Base de datos de análisis · Tesis de inversión RSU</div>'
        + '</div>';
}

function gallery() {
    return '<div style="display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;">'
        + '<input id="tesis-search" type="text" placeholder="Buscar ticker o nombre..." style="flex:1;min-width:200px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 12px;color:var(--color-text);font-family:var(--font-mono);font-size:13px;outline:none;">'
        + '<div id="rating-filters" style="display:flex;gap:6px;flex-wrap:wrap;"></div>'
        + '</div>'
        + '<div id="tesis-stats" style="color:var(--color-muted);font-size:11px;margin-bottom:1rem;"></div>'
        + '<div id="tesis-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem;"></div>'
        + '<div id="tesis-pagination" style="display:flex;justify-content:center;gap:8px;margin-top:1.5rem;"></div>';
}

function setupFilters(container) {
    const input = container.querySelector('#tesis-search');
    let timeout;
    input.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            searchQuery = input.value.trim();
            currentPage = 1;
            loadGallery(container);
        }, 400);
    });
}

async function loadGallery(container) {
    const grid = container.querySelector('#tesis-grid');
    if (grid) grid.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div>';

    try {
        const token = sessionStorage.getItem('rsu_token');
        let url = '/api/v1/tesis/?page=' + currentPage + '&per_page=9';
        if (searchQuery) url += '&search=' + encodeURIComponent(searchQuery);
        if (activeRating && activeRating !== 'Todos') url += '&rating=' + encodeURIComponent(activeRating);

        const res  = await fetch(url, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        // Actualizar filtros de rating
        if (data.ratings && data.ratings.length > 0) {
            allRatings = data.ratings;
            renderRatingFilters(container);
        }

        // Stats
        const stats = container.querySelector('#tesis-stats');
        if (stats) {
            stats.innerHTML = '▸ ' + data.total + ' análisis encontrados · Página ' + data.page + ' de ' + data.total_pages;
        }

        // Grid
        if (!data.items.length) {
            grid.innerHTML = '<div style="padding:2rem;color:var(--color-muted);font-size:12px;grid-column:1/-1;text-align:center;">Sin resultados — ajusta los filtros.</div>';
        } else {
            grid.innerHTML = data.items.map(item => tesisCard(item)).join('');
            grid.querySelectorAll('.tesis-card-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const ticker = btn.getAttribute('data-ticker');
                    const fecha  = btn.getAttribute('data-fecha');
                    loadDetail(container, ticker, fecha);
                });
            });
        }

        // Paginación
        renderPagination(container, data);

    } catch(e) {
        if (grid) grid.innerHTML = errorMessage(e.message, {extraStyle: 'grid-column:1/-1;'});
    }
}

function renderRatingFilters(container) {
    const div = container.querySelector('#rating-filters');
    if (!div) return;
    div.innerHTML = allRatings.map(r => {
        const active = r === activeRating;
        const color  = r === 'BUY' ? '#00ffad' : r === 'SELL' ? '#f23645' : r === 'HOLD' ? '#ff9800' : 'var(--color-muted)';
        return '<button class="rating-filter-btn" data-rating="' + r + '" style="'
            + 'background:' + (active ? color : 'var(--color-surface)') + ';'
            + 'color:' + (active ? '#000' : color) + ';'
            + 'border:1px solid ' + color + ';border-radius:var(--radius);'
            + 'padding:4px 12px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">'
            + r + '</button>';
    }).join('');

    div.querySelectorAll('.rating-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeRating = btn.getAttribute('data-rating');
            currentPage  = 1;
            loadGallery(container);
        });
    });
}

function renderPagination(container, data) {
    const div = container.querySelector('#tesis-pagination');
    if (!div || data.total_pages <= 1) { if (div) div.innerHTML = ''; return; }

    let html = '';
    if (data.page > 1) {
        html += '<button class="page-btn" data-page="' + (data.page - 1) + '" style="' + pageBtnStyle() + '">← ANTERIOR</button>';
    }
    html += '<span style="color:var(--color-muted);font-size:12px;padding:6px 12px;">PÁGINA ' + data.page + ' / ' + data.total_pages + '</span>';
    if (data.page < data.total_pages) {
        html += '<button class="page-btn" data-page="' + (data.page + 1) + '" style="' + pageBtnStyle() + '">SIGUIENTE →</button>';
    }
    div.innerHTML = html;

    div.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage = parseInt(btn.getAttribute('data-page'));
            loadGallery(container);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

function autoHeaderHtml(ticker, color, rating, sector) {
    color = color || 'var(--color-accent)';
    const sectorUp = (sector || '').toUpperCase();
    return '<div style="height:140px;position:relative;overflow:hidden;background:linear-gradient(135deg,#151a23,#0a0c10);display:flex;align-items:center;justify-content:center;">'
        + '<div style="position:absolute;inset:0;background-image:repeating-linear-gradient(115deg, transparent, transparent 18px, ' + color + '14 18px, ' + color + '14 19px);"></div>'
        + '<div style="position:absolute;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle, ' + color + '33 0%, transparent 70%);"></div>'
        + '<span style="position:relative;color:' + color + ';font-size:2.3rem;font-weight:600;letter-spacing:4px;text-shadow:0 0 24px ' + color + '99;">' + ticker + '</span>'
        + (rating ? '<span style="position:absolute;top:8px;right:10px;font-size:9px;color:' + color + ';border:1px solid ' + color + '55;border-radius:3px;padding:1px 6px;background:#00000055;letter-spacing:0.05em;">' + rating + '</span>' : '')
        + (sectorUp ? '<span style="position:absolute;bottom:8px;left:10px;font-size:9px;color:var(--color-muted);letter-spacing:0.05em;">' + sectorUp + '</span>' : '')
        + '</div>';
}

// Usado desde el atributo onerror de <img> cuando una URL de imagen manual
// (columna "imagenencabezado" del Sheet) se rompe — antes llamaba a una
// función tickerFallback() que no existía en ningún sitio del código, así
// que una imagen rota se quedaba así, sin fallback real.
window.__tesisImgError = function(img) {
    img.outerHTML = autoHeaderHtml(img.dataset.ticker || '', img.dataset.color || '', img.dataset.rating || '', img.dataset.sector || '');
};

function tesisCard(item) {
    const color   = item.rating_color || 'var(--color-muted)';
    // Si hay una imagen puesta a mano en el Sheet, se respeta (por compatibilidad
    // con las tesis que ya la tienen). Si no hay ninguna, se genera sola una
    // cabecera de marca a partir de ticker/rating/sector — cero pasos manuales.
    const imgHtml = item.imagen && item.imagen.startsWith('http')
        ? '<img src="' + item.imagen + '" style="width:100%;height:140px;object-fit:cover;" '
          + 'data-ticker="' + item.ticker + '" data-color="' + color + '" data-rating="' + item.rating + '" data-sector="' + (item.sector || '') + '" '
          + 'onerror="window.__tesisImgError(this)">'
        : autoHeaderHtml(item.ticker, color, item.rating, item.sector);

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;">'
        + imgHtml
        + '<div style="padding:1rem;flex:1;display:flex;flex-direction:column;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        + '<span style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '55;border-radius:3px;padding:2px 8px;font-size:11px;font-weight:500;">' + item.rating + '</span>'
        + (item.es_nuevo ? '<span style="background:#00ffad22;color:#00ffad;border:1px solid #00ffad55;border-radius:3px;padding:2px 6px;font-size:10px;">NEW</span>' : '')
        + '</div>'
        + '<div style="color:var(--color-accent);font-size:16px;letter-spacing:0.08em;margin-bottom:2px;">' + item.ticker + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-bottom:8px;">' + (item.nombre || '') + '</div>'
        + '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:auto;">'
        + (item.sector ? '<span style="color:var(--color-secondary);font-size:10px;padding:2px 6px;background:rgba(0,217,255,0.08);border-radius:3px;">' + item.sector + '</span>' : '')
        + (item.autor  ? '<span style="color:var(--color-muted);font-size:10px;">👤 ' + item.autor + '</span>' : '')
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-top:8px;margin-bottom:1rem;">📅 ' + item.fecha + '</div>'
        + '<button class="tesis-card-btn" data-ticker="' + item.ticker + '" data-fecha="' + item.fecha + '" style="'
        + 'width:100%;background:transparent;border:1px solid var(--color-accent);color:var(--color-accent);'
        + 'border-radius:var(--radius);padding:8px;font-family:var(--font-mono);font-size:12px;cursor:pointer;'
        + 'letter-spacing:0.05em;transition:all var(--transition);"'
        + ' onmouseover="this.style.background=\'var(--color-accent)\';this.style.color=\'#000\'"'
        + ' onmouseout="this.style.background=\'transparent\';this.style.color=\'var(--color-accent)\'">'
        + 'LEER TESIS →'
        + '</button>'
        + '</div>'
        + '</div>';
}

async function loadDetail(container, ticker, fecha) {
    const token = sessionStorage.getItem('rsu_token');
    let url = '/api/v1/tesis/' + ticker;
    if (fecha) url += '?fecha=' + encodeURIComponent(fecha);

    container.querySelector('#tesis-grid')?.closest('div')?.previousElementSibling;

    const mainEl = container;
    mainEl.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando análisis...</div>';

    try {
        const res  = await fetch(url, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Sin datos');

        mainEl.innerHTML = renderDetail(data);

        mainEl.querySelector('#btn-volver')?.addEventListener('click', () => {
            render(container);
        });

    } catch(e) {
        mainEl.innerHTML = errorMessage(e.message);
    }
}

function renderDetail(data) {
    const color  = data.rating_color || 'var(--color-muted)';
    const upside = data.upside !== null && data.upside !== undefined;
    const upsideColor = upside && data.upside >= 0 ? 'var(--color-accent)' : '#f23645';

    const riesgoColor = (data.riesgo || '').includes('BAJO') ? 'var(--color-accent)'
        : (data.riesgo || '').includes('MEDIO') ? '#ff9800' : '#f23645';

    const metricas = [
        data.precio_objetivo ? ['🎯 PRECIO OBJETIVO', '$' + data.precio_objetivo, 'var(--color-accent)'] : null,
        data.precio_actual   ? ['💵 PRECIO ACTUAL',   '$' + data.precio_actual,   'var(--color-text)']   : null,
        upside               ? ['📈 UPSIDE', (data.upside >= 0 ? '+' : '') + data.upside + '%', upsideColor] : null,
        data.riesgo          ? ['⚠ RIESGO', data.riesgo, riesgoColor] : null,
    ].filter(Boolean);

    return '<div style="margin-bottom:1.5rem;">'
        + '<button id="btn-volver" style="background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:12px;cursor:pointer;margin-bottom:1rem;">← VOLVER</button>'
        + '<div style="font-family:var(--font-mono);color:var(--color-muted);font-size:11px;letter-spacing:0.1em;margin-bottom:4px;">[LOADING ANALYSIS // TICKER: ' + data.ticker + ']</div>'
        + '<div style="color:var(--color-accent);font-size:22px;letter-spacing:0.08em;margin-bottom:4px;">' + data.nombre + ' <span style="color:var(--color-muted);font-size:14px;">// ' + data.ticker + '</span></div>'
        + '</div>'

        // Métricas header
        + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">'
        + metricCard('RATING',   data.rating, color)
        + metricCard('FECHA',    data.fecha,  'var(--color-text)')
        + metricCard('SECTOR',   data.sector, 'var(--color-secondary)')
        + metricCard('ANALISTA', data.autor,  '#ff9800')
        + '</div>'

        // Resumen
        + (data.resumen ? '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
            + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">📝 RESUMEN EJECUTIVO</div>'
            + '<div style="color:var(--color-text);font-size:13px;line-height:1.7;">' + data.resumen + '</div>'
            + '</div>' : '')

        // Métricas clave
        + (metricas.length > 0
            ? '<div style="display:grid;grid-template-columns:repeat(' + metricas.length + ',1fr);gap:1rem;margin-bottom:1rem;">'
              + metricas.map(([label, val, c]) => metricCard(label, val, c)).join('')
              + '</div>'
            : '')

        // Documento
        + '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">📄 DOCUMENTO COMPLETO</div>'
        + (data.url_doc
            ? '<iframe src="' + data.url_doc + '" style="width:100%;height:820px;border:none;border-radius:var(--radius);" allowfullscreen></iframe>'
            : data.contenido
                ? '<div class="tesis-markdown" style="color:var(--color-text);font-size:13px;line-height:1.7;max-width:100%;overflow-x:auto;">' + renderMarkdown(data.contenido) + '</div>'
                : '<div style="color:var(--color-muted);font-size:12px;padding:1rem;text-align:center;">⚠ Sin documento disponible.</div>')
        + '</div>'

        // Footer
        + '<div style="text-align:center;padding:1rem;color:var(--color-muted);font-size:10px;letter-spacing:0.1em;">'
        + '[END OF ANALYSIS // ' + data.ticker + '_v1.0] [FECHA: ' + data.fecha + '] [STATUS: ACTIVE]'
        + '</div>';
}

function metricCard(label, value, color) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;text-align:center;">'
        + '<div style="color:' + color + ';font-size:18px;font-weight:500;margin-bottom:4px;">' + (value || 'N/A') + '</div>'
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.1em;">' + label + '</div>'
        + '</div>';
}

function pageBtnStyle() {
    return 'background:var(--color-surface);border:1px solid var(--color-border);color:var(--color-muted);border-radius:var(--radius);padding:6px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;';
}