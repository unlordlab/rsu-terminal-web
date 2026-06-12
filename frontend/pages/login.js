import { setToken } from '/core/api.js';
import { api } from '/core/api.js';

export async function render(container) {
    container.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 70vh;
        ">
            <div style="
                background: var(--color-surface);
                border: 1px solid var(--color-border);
                border-radius: var(--radius-lg);
                padding: 2.5rem;
                width: 100%;
                max-width: 380px;
            ">
                <div style="
                    color: var(--color-accent);
                    font-size: 20px;
                    letter-spacing: 0.15em;
                    margin-bottom: 4px;
                    text-shadow: var(--glow-text);
                ">RSU TERMINAL</div>

                <div style="
                    color: var(--color-muted);
                    font-size: 12px;
                    margin-bottom: 2rem;
                ">Acceso restringido · Comunidad de traders</div>

                <div style="margin-bottom: 1rem;">
                    <label style="
                        display: block;
                        color: var(--color-muted);
                        font-size: 11px;
                        margin-bottom: 6px;
                        letter-spacing: 0.1em;
                    ">CONTRASEÑA</label>
                    <input
                        type="password"
                        id="password-input"
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
                            transition: border-color var(--transition);
                        "
                    >
                </div>

                <div id="login-error" style="
                    color: var(--color-danger);
                    font-size: 12px;
                    margin-bottom: 1rem;
                    min-height: 16px;
                "></div>

                <button
                    id="login-btn"
                    style="
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
                        transition: opacity var(--transition);
                    "
                >ENTRAR</button>
            </div>
        </div>
    `;

    const input = container.querySelector('#password-input');
    const btn   = container.querySelector('#login-btn');
    const error = container.querySelector('#login-error');

    // Focus automático
    input.focus();

    async function doLogin() {
        const password = input.value.trim();
        if (!password) return;

        btn.textContent = 'VERIFICANDO...';
        btn.style.opacity = '0.7';
        error.textContent = '';

        try {
            const data = await api.post('/auth/login', { password });
            if (data?.access_token) {
                setToken(data.access_token);
                window.__navigate('/');
            }
        } catch (err) {
            error.textContent = '✗ Contraseña incorrecta';
            input.value = '';
            input.focus();
        } finally {
            btn.textContent = 'ENTRAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doLogin);
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') doLogin();
    });
}
