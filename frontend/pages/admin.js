const ADMIN_KEY_STORAGE = 'rsu_admin_key';

async function adminFetch(path, options = {}) {
    const key = sessionStorage.getItem(ADMIN_KEY_STORAGE);
    const res = await fetch('/api/v1/auth' + path, {
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

const TIER_LABELS = { free: 'FREE', tier1: 'TIER 1', tiers: 'TIER S' };

export async function render(container) {
    container.innerHTML = `
        <div style="max-width: 900px; margin: 0 auto; padding: 1.5rem 1rem;">
            <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;margin-bottom:1.5rem;">
                ADMIN · USUARIOS
            </div>
            <div id="admin-content"></div>
        </div>
    `;
    const content = container.querySelector('#admin-content');

    if (sessionStorage.getItem(ADMIN_KEY_STORAGE)) {
        await renderPanel(content);
    } else {
        renderKeyPrompt(content);
    }
}

function renderKeyPrompt(content) {
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
            await renderPanel(content);
        } catch (err) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
            error.textContent = '✗ ' + (err.message || 'Clave inválida');
            btn.textContent = 'ENTRAR';
        }
    }

    btn.addEventListener('click', tryKey);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') tryKey(); });
}

async function renderPanel(content) {
    let data;
    try {
        data = await adminFetch('/admin/users');
    } catch (err) {
        if (err.isAuthError) {
            sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        }
        renderKeyPrompt(content);
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

    content.querySelector('#admin-refresh').addEventListener('click', () => renderPanel(content));
    content.querySelector('#admin-logout').addEventListener('click', () => {
        sessionStorage.removeItem(ADMIN_KEY_STORAGE);
        renderKeyPrompt(content);
    });
}
