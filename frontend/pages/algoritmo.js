export async function render(container) {
    container.innerHTML = '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RSU ALGORITMO</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Detector de fondos · Multi-factor V2.1 · SPY</div>'
        + '</div>'
        + '<div id="algo-full"></div>';

    // Reutiliza el mismo widget del dashboard
    const script = document.createElement('script');
    script.type = 'module';
    script.textContent = `
        import { render as dashRender } from '/pages/dashboard.js';
    `;

    const token = sessionStorage.getItem('rsu_token');
    const el    = container.querySelector('#algo-full');
    el.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando...</div>';

    try {
        const res  = await fetch('/api/v1/algoritmo/', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);

        el.innerHTML = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Redirigiendo al dashboard...</div>';
        window.__navigate('/');
    } catch(e) {
        el.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
    }
}