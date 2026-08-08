import { setSession } from '/core/api.js';
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
                ">Crea tu cuenta · Plan gratuito por defecto</div>

                <div style="margin-bottom: 1rem;">
                    <label style="
                        display: block;
                        color: var(--color-muted);
                        font-size: 11px;
                        margin-bottom: 6px;
                        letter-spacing: 0.1em;
                    ">EMAIL</label>
                    <input
                        type="email"
                        id="email-input"
                        placeholder="tu@email.com"
                        autocomplete="username"
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
                        "
                    >
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="
                        display: block;
                        color: var(--color-muted);
                        font-size: 11px;
                        margin-bottom: 6px;
                        letter-spacing: 0.1em;
                    ">CONTRASEÑA (mín. 8 caracteres)</label>
                    <input
                        type="password"
                        id="password-input"
                        placeholder="········"
                        autocomplete="new-password"
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
                        "
                    >
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="
                        display: block;
                        color: var(--color-muted);
                        font-size: 11px;
                        margin-bottom: 6px;
                        letter-spacing: 0.1em;
                    ">REPITE LA CONTRASEÑA</label>
                    <input
                        type="password"
                        id="password2-input"
                        placeholder="········"
                        autocomplete="new-password"
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
                        "
                    >
                </div>

                <div id="register-error" style="
                    color: var(--color-danger);
                    font-size: 12px;
                    margin-bottom: 1rem;
                    min-height: 16px;
                "></div>

                <button
                    id="register-btn"
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
                    "
                >CREAR CUENTA</button>

                <div style="
                    text-align: center;
                    margin-top: 1.25rem;
                    font-size: 12px;
                    color: var(--color-muted);
                ">
                    ¿Ya tienes cuenta?
                    <a id="go-login" href="/login" style="color: var(--color-accent); text-decoration: none; margin-left: 4px;">Inicia sesión</a>
                </div>
            </div>
        </div>
    `;

    const emailInput = container.querySelector('#email-input');
    const passInput  = container.querySelector('#password-input');
    const pass2Input = container.querySelector('#password2-input');
    const btn        = container.querySelector('#register-btn');
    const error      = container.querySelector('#register-error');
    const goLogin    = container.querySelector('#go-login');

    emailInput.focus();

    async function doRegister() {
        const email     = emailInput.value.trim();
        const password  = passInput.value;
        const password2 = pass2Input.value;

        if (!email || !password || !password2) return;
        if (password !== password2) {
            error.textContent = '✗ Las contraseñas no coinciden';
            return;
        }

        btn.textContent = 'CREANDO...';
        btn.style.opacity = '0.7';
        error.textContent = '';

        try {
            const data = await api.post('/auth/register', { email, password });
            if (data?.ok) {
                setSession(data.tier, data.email);
                window.__navigate('/');
            }
        } catch (err) {
            error.textContent = '✗ ' + (err.message || 'No se ha podido crear la cuenta');
        } finally {
            btn.textContent = 'CREAR CUENTA';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doRegister);
    [emailInput, passInput, pass2Input].forEach(el => el.addEventListener('keydown', e => {
        if (e.key === 'Enter') doRegister();
    }));

    goLogin.addEventListener('click', (e) => {
        e.preventDefault();
        window.__navigate('/login');
    });
}
