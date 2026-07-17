import { renderThemeMaker } from '/pages/admin_theme_maker.js';

const ADMIN_KEY_STORAGE = 'rsu_admin_key';

async function keyFetch(fullPath, options = {}) {
    const key = sessionStorage.getItem(ADMIN_KEY_STORAGE);
    const res = await fetch(fullPath, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'X-Admin-Key': key || '',
            ...(options.headers || {}),
        },
    });
    if (res.status === 401) {
        const err = new Error('Clave de administrador inválida');
        err.isAuthError = true;
        throw err;
    }
    if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(body.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

const adminFetch     = (path, options) => keyFetch('/api/v1/auth' + path, options);
const analyticsFetch = (path, options) => keyFetch('/api/v1/analytics' + path, options);
const communityFetch = (path, options) => keyFetch('/api/v1/community' + path, options);
const tesisFetch      = (path, options) => keyFetch('/api/v1/tesis' + path, options);
const academyReviewFetch = (path, options) => keyFetch('/api/v1/academy-review' + path, options);

const TIER_LABELS = { free: 'FREE', tier1: 'TIER 1', tiers: 'TIER S' };

// Etiquetas legibles para las secciones, mismas que en components/sidebar.js.
const SECTION_LABELS = {
    '/':             'Dashboard',
    '/manifiesto':   'Manifiesto',
    '/market':       'Market',
    '/cartera':      'Cartera',
    '/rsrw':         'RS/RW',
    '/scanner':      'Scanner',
    '/newsfeed':     'News Feed',
    '/tesis':        'Tesis',
    '/spxl':         'SPXL',
    '/btc-stratum':  'BTC Stratum',
    '/options':      'Options Flow',
    '/research':     'Research',
    '/insider':      'Insider Flow',
    '/academy':      'Academy',
    '/roadmap':      'Roadmap 2026',
    '/canslim':      'CANSLIM',
    '/algoritmo':    'RSU Algoritmo',
    '/disclaimer':   'Disclaimer',
};

let activeTab = 'usuarios';

export async function render(container) {
    container.innerHTML = `
        <div style="max-width: 1000px; margin: 0 auto; padding: 1.5rem 1rem;">
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;margin-bottom:1rem;">
                ADMIN
            </div>
            <div id="admin-tabs" style="display:flex;gap:4px;margin-bottom:1.25rem;border-bottom:1px solid var(--color-border);">
                <button data-tab="usuarios" class="admin-tab-btn">USUARIOS</button>
                <button data-tab="metricas" class="admin-tab-btn">MÉTRICAS</button>
                <button data-tab="peticiones" class="admin-tab-btn">PETICIONES</button>
                <button data-tab="tesis" class="admin-tab-btn">TESIS PENDIENTES</button>
                <button data-tab="academy" class="admin-tab-btn">ACADEMY PENDIENTE</button>
                <button data-tab="feedback" class="admin-tab-btn">FEEDBACK</button>
                <button data-tab="temas" class="admin-tab-btn">TEMAS</button>
            </div>
            <div id="admin-content"></div>
        </div>
    `;

    if (!document.getElementById('admin-tab-style')) {
        const style = document.createElement('style');
        style.id = 'admin-tab-style';
        style.textContent = `
            .admin-tab-btn {
                background: none; border: none; border-bottom: 2px solid transparent;
                color: var(--color-muted); padding: 8px 14px; font-family: var(--font-mono);
                font-size: 12px; letter-spacing: 0.08em; cursor: pointer;
            }
            .admin-tab-btn:hover { color: var(--color-text); }
            .admin-tab-btn.active { color: var(--color-accent); border-bottom-color: var(--color-accent); }
        `;
        document.head.appendChild(style);
    }

    const content = container.querySelector('#admin-content');
    const tabs = container.querySelectorAll('.admin-tab-btn');

    function setActiveTabUI() {
        tabs.forEach(b => b.classList.toggle('active', b.dataset.tab === activeTab));
    }

    async function renderActiveTab() {
        setActiveTabUI();
        if (!sessionStorage.getItem(ADMIN_KEY_STORAGE)) {
            renderKeyPrompt(content, renderActiveTab);
            return;
        }
        if (activeTab === 'usuarios') {
            await renderUsersPanel(content);
        } else if (activeTab === 'feedback') {
            await renderFeedbackPanel(content);
        } else if (activeTab === 'temas') {
            await renderThemeMaker(content);
        } else if (activeTab === 'peticiones') {
            await renderHealthPanel(content);
        } else if (activeTab === 'tesis') {
            await renderTesisPanel(content);
        } else if (activeTab === 'academy') {
            await renderAcademyReviewPanel(content);
        } else {
            await renderMetricsPanel(content);
        }
    }

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            activeTab = btn.dataset.tab;
            renderActiveTab();
        });
    });

    await renderActiveTab();
}

function renderKeyPrompt(content, onSuccess) {
    content.innerHTML = `
        <div style="
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-lg);
            padding: 2rem;
            max-width: 380px;
        ">
            <label style="
                display: block;
                color: var(--color-muted);
                font-size: 11px;
                margin-bottom: 6px;
                letter-spacing: 0.1em;
            ">ADMIN KEY</label>
            <input
                type="password"
                id="admin-key-input"
                placeholder="········"
                style="
                    width: 100%;
                    background: var(--color-bg);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius);
                    padding: 10px 12px;
                    color: var(--color-text);
                    font-family: var(--font-mono);
                    font-size: 14px;
                    outline: none;
                    box-sizing: border-box;
                    margin-bottom: 0.75rem;
                "
            >
            <div id="admin-key-error" style="color:var(--color-danger);font-size:12px;margin-bottom:0.75rem;min-height:16px;"></div>
            <button id="admin-key-btn" style="
                width: 100%;
                background: var(--color-accent);
                color: #000;
                border: none;
                border-radius: var(--radius);
                padding: 10px;
                font-family: var(--font-mono);
                font-size: 13px;
                letter-spacing: 0.1em;
                cursor: pointer;
            ">ENTRAR</button>
        </div>
    `;

    const input = content.querySelector('#admin-key-input');
    const btn   = content.querySelector('#admin-key-btn');
    const error = content.querySelector('#admin-key-error');
    input.focus();

    async function tryKey() {
        const key = input.value.trim();
        if (!key) return;
        sessionStorage.setItem(ADMIN_KEY_STORAGE, key);
        error.textContent = '';
        btn.textContent = 'VERIFICANDO...';
        try {
            await onSuccess();
        } catch (err) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
            error.textContent = '✗ ' + (err.message || 'Clave inválida');
            btn.textContent = 'ENTRAR';
        }
    }

    btn.addEventListener('click', tryKey);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') tryKey(); });
}

// ─── USUARIOS ───────────────────────────────────────────────────────────

async function renderUsersPanel(content) {
    let data;
    try {
        data = await adminFetch('/admin/users');
    } catch (err) {
        if (err.isAuthError) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        }
        renderKeyPrompt(content, () => renderUsersPanel(content));
        if (err.isAuthError) {
            content.querySelector('#admin-key-error').textContent = '✗ Clave de administrador inválida';
        }
        return;
    }

    const users = data.users || [];

    content.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
            <span style="color:var(--color-muted);font-size:12px;">${users.length} usuario${users.length === 1 ? '' : 's'}</span>
            <div>
                <button id="admin-refresh" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;margin-right:6px;">REFRESCAR</button>
                <button id="admin-logout" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">SALIR</button>
            </div>
        </div>
        <div id="admin-msg" style="font-size:12px;margin-bottom:0.75rem;min-height:16px;"></div>
        <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="border-bottom:1px solid var(--color-border);color:var(--color-muted);text-align:left;">
                        <th style="padding:8px;">Email</th>
                        <th style="padding:8px;">Tier</th>
                        <th style="padding:8px;">Alta</th>
                        <th style="padding:8px;">Resetear contraseña</th>
                    </tr>
                </thead>
                <tbody id="admin-table-body"></tbody>
            </table>
        </div>
    `;

    const tbody = content.querySelector('#admin-table-body');
    const msg   = content.querySelector('#admin-msg');

    function showMsg(text, isError) {
        msg.textContent = text;
        msg.style.color = isError ? 'var(--color-danger)' : 'var(--color-accent)';
        setTimeout(() => { msg.textContent = ''; }, 3500);
    }

    users.forEach(u => {
        const tr = document.createElement('tr');
        tr.style.cssText = 'border-bottom:1px solid var(--color-border);';

        const tdEmail = document.createElement('td');
        tdEmail.style.padding = '8px';
        tdEmail.textContent = u.email;

        const tdTier = document.createElement('td');
        tdTier.style.padding = '8px';
        const select = document.createElement('select');
        select.style.cssText = 'background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:4px 6px;font-family:var(--font-mono);font-size:12px;';
        Object.entries(TIER_LABELS).forEach(([value, label]) => {
            const opt = document.createElement('option');
            opt.value = value;
            opt.textContent = label;
            if (value === u.tier) opt.selected = true;
            select.appendChild(opt);
        });
        select.addEventListener('change', async () => {
            const newTier = select.value;
            try {
                await adminFetch('/admin/set-tier', { method: 'POST', body: JSON.stringify({ email: u.email, tier: newTier }) });
                showMsg(`✓ ${u.email} → ${TIER_LABELS[newTier]}`, false);
            } catch (err) {
                showMsg('✗ ' + err.message, true);
                select.value = u.tier;
            }
        });
        tdTier.appendChild(select);

        const tdDate = document.createElement('td');
        tdDate.style.padding = '8px';
        tdDate.style.color = 'var(--color-muted)';
        tdDate.style.fontSize = '11px';
        try {
            tdDate.textContent = new Date(u.created_at).toLocaleDateString();
        } catch { tdDate.textContent = u.created_at; }

        const tdReset = document.createElement('td');
        tdReset.style.padding = '8px';
        const resetBtn = document.createElement('button');
        resetBtn.textContent = 'Resetear';
        resetBtn.style.cssText = 'background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;';
        resetBtn.addEventListener('click', async () => {
            const newPassword = window.prompt(`Nueva contraseña para ${u.email} (mín. 8 caracteres):`);
            if (!newPassword) return;
            try {
                await adminFetch('/admin/reset-password', { method: 'POST', body: JSON.stringify({ email: u.email, new_password: newPassword }) });
                showMsg(`✓ Contraseña actualizada para ${u.email}`, false);
            } catch (err) {
                showMsg('✗ ' + err.message, true);
            }
        });
        tdReset.appendChild(resetBtn);

        tr.appendChild(tdEmail);
        tr.appendChild(tdTier);
        tr.appendChild(tdDate);
        tr.appendChild(tdReset);
        tbody.appendChild(tr);
    });

    content.querySelector('#admin-refresh').addEventListener('click', () => renderUsersPanel(content));
    content.querySelector('#admin-logout').addEventListener('click', () => {
        sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        renderKeyPrompt(content, () => renderUsersPanel(content));
    });
}

// ─── MÉTRICAS ───────────────────────────────────────────────────────────

let metricsDays = 30;
let healthHours = 24;

async function renderMetricsPanel(content) {
    let data;
    try {
        data = await analyticsFetch(`/summary?days=${metricsDays}`);
    } catch (err) {
        if (err.isAuthError) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        }
        renderKeyPrompt(content, () => renderMetricsPanel(content));
        if (err.isAuthError) {
            content.querySelector('#admin-key-error').textContent = '✗ Clave de administrador inválida';
        }
        return;
    }

    const maxSectionVisits = Math.max(1, ...data.sections.map(s => s.visits));
    const maxTickerViews   = Math.max(1, ...data.tickers.map(t => t.views));
    const maxTesisViews    = Math.max(1, ...data.tesis.map(t => t.views));

    function barRow(label, sub, value, max) {
        const pct = Math.round((value / max) * 100);
        return `
            <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
                    <span style="color:var(--color-text);">${label}</span>
                    <span style="color:var(--color-muted);">${value}${sub ? ` · ${sub}` : ''}</span>
                </div>
                <div style="background:var(--color-surface2);border-radius:3px;height:6px;overflow:hidden;">
                    <div style="width:${pct}%;height:100%;background:var(--color-accent);"></div>
                </div>
            </div>
        `;
    }

    const sectionsHtml = data.sections.length
        ? data.sections.map(s => barRow(SECTION_LABELS[s.section] || s.section, `${s.unique_users} usuario${s.unique_users === 1 ? '' : 's'}`, s.visits, maxSectionVisits)).join('')
        : '<p style="color:var(--color-muted);font-size:12px;">Sin datos todavía.</p>';

    const tickersHtml = data.tickers.length
        ? data.tickers.map(t => barRow(t.ticker, `${t.unique_users} usuario${t.unique_users === 1 ? '' : 's'}`, t.views, maxTickerViews)).join('')
        : '<p style="color:var(--color-muted);font-size:12px;">Sin datos todavía.</p>';

    const tesisHtml = data.tesis.length
        ? data.tesis.map(t => barRow(t.ticker, `${t.unique_users} usuario${t.unique_users === 1 ? '' : 's'}`, t.views, maxTesisViews)).join('')
        : '<p style="color:var(--color-muted);font-size:12px;">Sin datos todavía.</p>';

    content.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;gap:6px;align-items:center;">
                <span style="color:var(--color-muted);font-size:11px;">VENTANA:</span>
                <select id="metrics-days" style="background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:4px 8px;font-family:var(--font-mono);font-size:12px;">
                    <option value="7"${metricsDays === 7 ? ' selected' : ''}>7 días</option>
                    <option value="30"${metricsDays === 30 ? ' selected' : ''}>30 días</option>
                    <option value="90"${metricsDays === 90 ? ' selected' : ''}>90 días</option>
                    <option value="365"${metricsDays === 365 ? ' selected' : ''}>1 año</option>
                </select>
            </div>
            <button id="metrics-refresh" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">REFRESCAR</button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:1.5rem;">
            ${statCard('Visitas de sección', data.total_page_views)}
            ${statCard('Consultas de ticker', data.total_ticker_views)}
            ${statCard('Usuarios activos', data.unique_users)}
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.25rem;">
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:1rem;">
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">SECCIONES MÁS VISITADAS</div>
                ${sectionsHtml}
            </div>
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:1rem;">
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">TICKERS MÁS CONSULTADOS</div>
                ${tickersHtml}
            </div>
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:1rem;">
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">TESIS MÁS CONSULTADAS</div>
                ${tesisHtml}
            </div>
        </div>
    `;

    content.querySelector('#metrics-refresh').addEventListener('click', () => renderMetricsPanel(content));
    content.querySelector('#metrics-days').addEventListener('change', (e) => {
        metricsDays = parseInt(e.target.value, 10) || 30;
        renderMetricsPanel(content);
    });
}

const MODULE_LABELS = {
    indices: 'Índices', sectors: 'Sectores', forex: 'Forex', commodities: 'Commodities',
};

function healthColor(rate) {
    if (rate === null || rate === undefined) return 'var(--color-muted)';
    if (rate >= 95) return '#3ecf8e';
    if (rate >= 80) return '#e0b13e';
    return '#e05d5d';
}

async function renderHealthPanel(content) {
    let data;
    try {
        data = await analyticsFetch(`/yfinance-health?hours=${healthHours}`);
    } catch (err) {
        if (err.isAuthError) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        }
        renderKeyPrompt(content, () => renderHealthPanel(content));
        if (err.isAuthError) {
            content.querySelector('#admin-key-error').textContent = '✗ Clave de administrador inválida';
        }
        return;
    }

    const totalOk   = data.modules.reduce((s, m) => s + m.ok, 0);
    const totalFail = data.modules.reduce((s, m) => s + m.fail, 0);
    const totalAll  = totalOk + totalFail;
    const globalRate = totalAll ? Math.round((totalOk / totalAll) * 1000) / 10 : null;
    const worstModule = data.modules.length ? data.modules[0] : null;

    const modulesHtml = data.modules.length
        ? data.modules.map(m => `
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
                    <span style="color:var(--color-text);">${MODULE_LABELS[m.module] || m.module}</span>
                    <span style="color:${healthColor(m.success_rate)};">${m.success_rate === null ? '—' : m.success_rate + '%'} · ${m.ok}/${m.total}</span>
                </div>
                <div style="background:var(--color-surface2);border-radius:3px;height:6px;overflow:hidden;">
                    <div style="width:${m.success_rate ?? 0}%;height:100%;background:${healthColor(m.success_rate)};"></div>
                </div>
            </div>
        `).join('')
        : '<p style="color:var(--color-muted);font-size:12px;">Sin datos todavía en esta ventana.</p>';

    const failuresHtml = data.recent_failures.length
        ? data.recent_failures.map(f => {
            const d = new Date(f.timestamp * 1000);
            return `
                <div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:11px;">
                    <div style="display:flex;justify-content:space-between;color:var(--color-text);">
                        <span>${MODULE_LABELS[f.module] || f.module}</span>
                        <span style="color:var(--color-muted);">${d.toLocaleString('es-ES')}</span>
                    </div>
                    <div style="color:var(--color-muted);margin-top:2px;word-break:break-word;">${(f.detail || 'sin detalle').slice(0, 160)}</div>
                </div>
            `;
        }).join('')
        : '<p style="color:var(--color-muted);font-size:12px;">Sin fallos registrados en esta ventana. 🎉</p>';

    content.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;gap:6px;align-items:center;">
                <span style="color:var(--color-muted);font-size:11px;">VENTANA:</span>
                <select id="health-hours" style="background:var(--color-bg);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:4px 8px;font-family:var(--font-mono);font-size:12px;">
                    <option value="1"${healthHours === 1 ? ' selected' : ''}>Última hora</option>
                    <option value="6"${healthHours === 6 ? ' selected' : ''}>6 horas</option>
                    <option value="24"${healthHours === 24 ? ' selected' : ''}>24 horas</option>
                    <option value="72"${healthHours === 72 ? ' selected' : ''}>3 días</option>
                    <option value="168"${healthHours === 168 ? ' selected' : ''}>7 días</option>
                </select>
            </div>
            <button id="health-refresh" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">REFRESCAR</button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:1.5rem;">
            ${statCard('Peticiones totales', totalAll)}
            ${statCard('% éxito global', globalRate === null ? '—' : globalRate + '%')}
            ${statCard('Módulo más débil', worstModule ? (MODULE_LABELS[worstModule.module] || worstModule.module) : '—')}
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.25rem;">
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:1rem;">
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">% ÉXITO POR MÓDULO</div>
                ${modulesHtml}
            </div>
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:1rem;">
                <div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ÚLTIMOS FALLOS</div>
                <div style="max-height:400px;overflow-y:auto;">${failuresHtml}</div>
            </div>
        </div>

        <p style="color:var(--color-muted);font-size:11px;margin-top:1rem;">
            Guía: por debajo del 80% de éxito sostenido durante horas (no un pico puntual) es la señal de que
            hace falta revisar la versión de yfinance, retomar un proxy, o evaluar migrar a una API de pago.
        </p>
    `;

    content.querySelector('#health-refresh').addEventListener('click', () => renderHealthPanel(content));
    content.querySelector('#health-hours').addEventListener('change', (e) => {
        healthHours = parseInt(e.target.value, 10) || 24;
        renderHealthPanel(content);
    });
}

async function renderTesisPanel(content) {
    let data;
    try {
        data = await tesisFetch('/admin/pending');
    } catch (err) {
        if (err.isAuthError) sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        renderKeyPrompt(content, () => renderTesisPanel(content));
        if (err.isAuthError) content.querySelector('#admin-key-error').textContent = '✗ Clave de administrador inválida';
        return;
    }

    const items = data.items || [];

    if (!items.length) {
        content.innerHTML = `
            <p style="color:var(--color-muted);font-size:13px;">
                No hay tesis pendientes de revisión ahora mismo. 🎉
            </p>
        `;
        return;
    }

    content.innerHTML = `
        <p style="color:var(--color-muted);font-size:11px;margin-bottom:1rem;">
            ${items.length} tesis a la espera de revisión. Se generan automáticamente (agente Bull) o se crean a mano — ninguna se publica sin tu aprobación explícita.
        </p>
        <div id="tesis-pending-list" style="display:flex;flex-direction:column;gap:12px;"></div>
    `;

    const list = content.querySelector('#tesis-pending-list');

    items.forEach(item => {
        const card = document.createElement('div');
        card.style.cssText = `
            background:var(--color-surface);border:1px solid var(--color-border);
            border-radius:var(--radius-lg);padding:1rem;
        `;
        const fecha = new Date(item.created_at * 1000).toLocaleString('es-ES');
        const fuenteLabel = item.fuente === 'agente_bull' ? '🐂 Agente Bull' : '✍️ Manual';

        card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:14px;color:var(--color-text);font-weight:600;">${item.ticker} · ${item.rating}</div>
                    <div style="font-size:12px;color:var(--color-muted);margin-top:2px;">${item.titulo || '(sin título)'}</div>
                    <div style="font-size:11px;color:var(--color-muted);margin-top:4px;">${fuenteLabel} · ${fecha}${item.criterio ? ' · ' + item.criterio : ''}</div>
                </div>
                <div style="display:flex;gap:6px;flex-shrink:0;">
                    <button class="tesis-toggle-btn" data-id="${item.id}" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">VER</button>
                    <button class="tesis-approve-btn" data-id="${item.id}" style="background:none;border:1px solid #3ecf8e;color:#3ecf8e;padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">APROBAR</button>
                    <button class="tesis-reject-btn" data-id="${item.id}" style="background:none;border:1px solid #e05d5d;color:#e05d5d;padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">RECHAZAR</button>
                </div>
            </div>
            <div class="tesis-full-content" data-id="${item.id}" style="display:none;margin-top:12px;padding-top:12px;border-top:1px solid var(--color-border);white-space:pre-wrap;font-size:12px;line-height:1.6;color:var(--color-text);max-height:500px;overflow-y:auto;"></div>
        `;
        list.appendChild(card);

        card.querySelector('.tesis-toggle-btn').addEventListener('click', (e) => {
            const box = card.querySelector('.tesis-full-content');
            const isOpen = box.style.display !== 'none';
            box.style.display = isOpen ? 'none' : 'block';
            e.target.textContent = isOpen ? 'VER' : 'OCULTAR';
            if (!isOpen && !box.dataset.loaded) {
                box.textContent = item.contenido;
                box.dataset.loaded = '1';
            }
        });

        card.querySelector('.tesis-approve-btn').addEventListener('click', async () => {
            if (!confirm(`¿Aprobar y publicar la tesis de ${item.ticker}?`)) return;
            try {
                await tesisFetch(`/admin/${item.id}/approve`, { method: 'POST' });
                renderTesisPanel(content);
            } catch (err) {
                alert('Error al aprobar: ' + err.message);
            }
        });

        card.querySelector('.tesis-reject-btn').addEventListener('click', async () => {
            if (!confirm(`¿Descartar la tesis de ${item.ticker}? No se puede deshacer.`)) return;
            try {
                await tesisFetch(`/admin/${item.id}/reject`, { method: 'POST' });
                renderTesisPanel(content);
            } catch (err) {
                alert('Error al rechazar: ' + err.message);
            }
        });
    });
}

async function renderAcademyReviewPanel(content) {
    let data;
    try {
        data = await academyReviewFetch('/pending');
    } catch (err) {
        if (err.isAuthError) sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        renderKeyPrompt(content, () => renderAcademyReviewPanel(content));
        if (err.isAuthError) content.querySelector('#admin-key-error').textContent = '✗ Clave de administrador inválida';
        return;
    }

    const items = data.items || [];

    if (!items.length) {
        content.innerHTML = `
            <p style="color:var(--color-muted);font-size:13px;">
                No hay propuestas de Academy pendientes de revisión ahora mismo. 🎉
            </p>
        `;
        return;
    }

    content.innerHTML = `
        <p style="color:var(--color-muted);font-size:11px;margin-bottom:1rem;">
            ${items.length} propuestas de Elia a la espera de revisión. Al aprobar, copia el bloque con el botón COPIAR
            y pégalo tú mismo en <code style="background:var(--color-surface2);padding:1px 5px;border-radius:3px;">academy_lessons.js</code> — Elia no edita el código directamente.
        </p>
        <div id="academy-pending-list" style="display:flex;flex-direction:column;gap:12px;"></div>
    `;

    const list = content.querySelector('#academy-pending-list');

    items.forEach(item => {
        const card = document.createElement('div');
        card.style.cssText = `
            background:var(--color-surface);border:1px solid var(--color-border);
            border-radius:var(--radius-lg);padding:1rem;
        `;
        const fecha = new Date(item.created_at * 1000).toLocaleString('es-ES');
        const tipoLabel = item.tipo === 'nueva_leccion' ? '🆕 Lección nueva' : '✏️ Ampliación de lección existente';

        card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:14px;color:var(--color-text);font-weight:600;">${item.titulo}</div>
                    <div style="font-size:11px;color:var(--color-muted);margin-top:4px;">${tipoLabel}${item.leccion_ref ? ' · leccion ' + item.leccion_ref : ''} · ${fecha}</div>
                    ${item.resumen ? `<div style="font-size:12px;color:var(--color-muted);margin-top:6px;">${item.resumen}</div>` : ''}
                </div>
                <div style="display:flex;gap:6px;flex-shrink:0;">
                    <button class="academy-toggle-btn" style="background:none;border:1px solid var(--color-border);color:var(--color-muted);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">VER</button>
                    <button class="academy-copy-btn" style="background:none;border:1px solid var(--color-secondary);color:var(--color-secondary);padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">COPIAR</button>
                    <button class="academy-approve-btn" style="background:none;border:1px solid #3ecf8e;color:#3ecf8e;padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">APROBAR</button>
                    <button class="academy-reject-btn" style="background:none;border:1px solid #e05d5d;color:#e05d5d;padding:4px 10px;border-radius:var(--radius);cursor:pointer;font-family:var(--font-mono);font-size:11px;">RECHAZAR</button>
                </div>
            </div>
            <pre class="academy-full-content" style="display:none;margin-top:12px;padding:10px;background:var(--color-surface2);border-radius:var(--radius);white-space:pre-wrap;font-size:11px;line-height:1.5;color:var(--color-text);max-height:500px;overflow-y:auto;font-family:var(--font-mono);">${item.bloque_js}</pre>
        `;
        list.appendChild(card);

        card.querySelector('.academy-toggle-btn').addEventListener('click', (e) => {
            const box = card.querySelector('.academy-full-content');
            const isOpen = box.style.display !== 'none';
            box.style.display = isOpen ? 'none' : 'block';
            e.target.textContent = isOpen ? 'VER' : 'OCULTAR';
        });

        card.querySelector('.academy-copy-btn').addEventListener('click', async (e) => {
            try {
                await navigator.clipboard.writeText(item.bloque_js);
                const original = e.target.textContent;
                e.target.textContent = '¡COPIADO!';
                setTimeout(() => { e.target.textContent = original; }, 1500);
            } catch (err) {
                alert('No se pudo copiar automáticamente — selecciona el texto a mano con VER.');
            }
        });

        card.querySelector('.academy-approve-btn').addEventListener('click', async () => {
            if (!confirm(`¿Marcar como aprobada? Recuerda: esto NO lo publica solo, tienes que copiarlo tú a academy_lessons.js.`)) return;
            try {
                await academyReviewFetch(`/${item.id}/approve`, { method: 'POST' });
                renderAcademyReviewPanel(content);
            } catch (err) {
                alert('Error al aprobar: ' + err.message);
            }
        });

        card.querySelector('.academy-reject-btn').addEventListener('click', async () => {
            if (!confirm(`¿Descartar esta propuesta? No se puede deshacer.`)) return;
            try {
                await academyReviewFetch(`/${item.id}/reject`, { method: 'POST' });
                renderAcademyReviewPanel(content);
            } catch (err) {
                alert('Error al rechazar: ' + err.message);
            }
        });
    });
}

function statCard(label, value) {
    return `
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:0.9rem 1rem;">
            <div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;margin-bottom:4px;">${label.toUpperCase()}</div>
            <div style="color:var(--color-text);font-size:22px;">${value}</div>
        </div>
    `;
}

const FB_TYPE_LABEL = { bug: '🐞 Bug', sugerencia: '💡 Sugerencia', otro: '✉️ Otro' };

async function renderFeedbackPanel(content) {
    content.innerHTML = '<div style="color:var(--color-muted);font-size:12px;">Cargando...</div>';
    try {
        const data = await communityFetch('/feedback');
        if (!data.data.length) {
            content.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Sin mensajes todavía.</div>';
            return;
        }
        const rows = data.data.map(f => {
            const bg = f.leido ? 'transparent' : 'rgba(0,255,173,0.04)';
            const when = (f.created_at || '').replace('T', ' ').substring(0, 16);
            return `
                <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0.9rem 1rem;margin-bottom:0.6rem;${bg !== 'transparent' ? 'border-left:2px solid var(--color-accent);' : ''}background:${bg};">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:6px;">
                        <span style="font-size:11px;color:var(--color-accent);">${FB_TYPE_LABEL[f.tipo] || f.tipo}</span>
                        <span style="font-size:10px;color:var(--color-muted);">${when} ${f.user_email ? '· ' + f.user_email : ''}</span>
                    </div>
                    <div style="color:var(--color-text);font-size:13px;line-height:1.5;white-space:pre-wrap;">${f.mensaje.replace(/</g, '&lt;')}</div>
                    ${f.contacto ? `<div style="margin-top:6px;font-size:11px;color:var(--color-muted);">Responder a: <a href="mailto:${f.contacto}" style="color:var(--color-secondary);">${f.contacto}</a></div>` : ''}
                    ${!f.leido ? `<button class="fb-mark-read" data-id="${f.id}" style="margin-top:8px;background:transparent;border:1px solid var(--color-border);color:var(--color-muted);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer;">Marcar como leído</button>` : ''}
                </div>
            `;
        }).join('');
        content.innerHTML = `<div style="margin-bottom:0.75rem;color:var(--color-muted);font-size:11px;">${data.data.length} mensajes · ${data.data.filter(f => !f.leido).length} sin leer</div>` + rows;

        content.querySelectorAll('.fb-mark-read').forEach(btn => {
            btn.addEventListener('click', async () => {
                await communityFetch(`/feedback/${btn.dataset.id}/read`, { method: 'POST' });
                renderFeedbackPanel(content);
            });
        });
    } catch (e) {
        if (e.isAuthError) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
            renderKeyPrompt(content, () => renderFeedbackPanel(content));
            return;
        }
        content.innerHTML = `<div style="color:#f23645;font-size:12px;">${e.message}</div>`;
    }
}