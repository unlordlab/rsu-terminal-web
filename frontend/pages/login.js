import { setSession } from '/core/api.js';
import { api } from '/core/api.js';

export async function render(container) {
    const expirada = new URLSearchParams(location.search).get('expired') === '1';
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

                ${expirada ? `
                <div style="
                    background: rgba(255,152,0,0.1);
                    border: 1px solid rgba(255,152,0,0.4);
                    border-radius: var(--radius);
                    padding: 10px 12px;
                    margin-bottom: 1.2rem;
                    color: #ff9800;
                    font-size: 12px;
                ">⏱ Tu sesión ha caducado. Inicia sesión de nuevo para continuar.</div>
                ` : ''}

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
                            transition: border-color var(--transition);
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
                    ">CONTRASEÑA</label>
                    <input
                        type="password"
                        id="password-input"
                        placeholder="········"
                        autocomplete="current-password"
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
                            box-sizing: border-box;
                        "
                    >
                </div>

                <div id="login-error" style="
                    color: var(--color-danger);
                    font-size: 12px;
                    margin-bottom: 1rem;
                    min-height: 16px;
                "></div>

                <label style="
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    color: var(--color-muted);
                    font-size: 12px;
                    margin-bottom: 1rem;
                    cursor: pointer;
                ">
                    <input type="checkbox" id="remember-input">
                    Mantener sesión en este dispositivo
                </label>

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

                <div style="
                    text-align: center;
                    margin-top: 1.25rem;
                    font-size: 12px;
                    color: var(--color-muted);
                ">
                    ¿No tienes cuenta?
                    <a id="go-register" href="/register" style="color: var(--color-accent); text-decoration: none; margin-left: 4px;">Regístrate</a>
                </div>

                <div style="
                    text-align: center;
                    margin-top: 0.5rem;
                    font-size: 11px;
                    color: var(--color-muted);
                ">
                    ¿Contraseña olvidada? Escribe a Marc para resetearla.
                    <br><a id="go-privacidad" href="/privacidad" style="color:var(--color-muted);text-decoration:underline;">Política de privacidad</a>
                </div>
            </div>
        </div>
    `;

    const emailInput    = container.querySelector('#email-input');
    const passInput     = container.querySelector('#password-input');
    const rememberInput = container.querySelector('#remember-input');
    const btn           = container.querySelector('#login-btn');
    const error         = container.querySelector('#login-error');
    const goRegister    = container.querySelector('#go-register');

    emailInput.focus();

    async function doLogin() {
        const email    = emailInput.value.trim();
        const password = passInput.value;
        if (!email || !password) return;

        btn.textContent = 'VERIFICANDO...';
        btn.style.opacity = '0.7';
        error.textContent = '';

        try {
            const data = await api.post('/auth/login', { email, password, remember: rememberInput.checked });
            // El token ya no viene en la respuesta: llega como cookie
            // httpOnly que el navegador ha guardado antes de llegar aquí.
            if (data?.ok) {
                setSession(data.tier, data.email, rememberInput.checked);
                window.__navigate('/');
            }
        } catch (err) {
            error.textContent = '✗ ' + (err.message || 'Email o contraseña incorrectos');
            passInput.value = '';
            passInput.focus();
        } finally {
            btn.textContent = 'ENTRAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doLogin);
    [emailInput, passInput].forEach(el => el.addEventListener('keydown', e => {
        if (e.key === 'Enter') doLogin();
    }));

    goRegister.addEventListener('click', (e) => {
        e.preventDefault();
        window.__navigate('/register');
    });

    // La política tiene que ser alcanzable SIN cuenta: es lo que alguien lee
    // antes de decidir si se registra.
    const goPriv = container.querySelector('#go-privacidad');
    if (goPriv) goPriv.addEventListener('click', (e) => {
        e.preventDefault();
        window.__navigate('/privacidad');
    });
}