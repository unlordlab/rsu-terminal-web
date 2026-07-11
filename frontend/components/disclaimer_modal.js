// ── MODAL DE ACEPTACIÓN DEL DISCLAIMER ───────────────────────────────────────
//
// Se muestra una sola vez por usuario (queda guardado en el backend, no en
// el navegador — así sigue pidiéndose aunque cambie de dispositivo, y deja
// de pedirse en cuanto lo acepta una vez). Bloquea el resto de la app hasta
// que el usuario marca la casilla y confirma — no se puede cerrar con Esc
// ni haciendo clic fuera, a diferencia del command palette.

export function showDisclaimerModal(onAccepted) {
    if (document.getElementById('disclaimer-modal-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'disclaimer-modal-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.innerHTML =
        '<div style="width:480px;max-width:100%;max-height:85vh;display:flex;flex-direction:column;background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.6);">'
        + '<div style="padding:16px 20px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:14px;letter-spacing:0.08em;text-shadow:var(--glow-text);">DESCARGO DE RESPONSABILIDAD</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">Antes de continuar, un momento</div>'
        + '</div>'
        + '<div style="padding:18px 20px;overflow-y:auto;flex:1;">'
        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0 0 12px;">'
        + 'Todo el contenido de RSU Terminal — análisis, señales, gráficos y comentarios — tiene una finalidad estrictamente educativa e informativa. '
        + '<b style="color:var(--color-text);">No es asesoría financiera ni una recomendación de inversión.</b>'
        + '</p>'
        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0 0 12px;">'
        + 'El trading conlleva un riesgo alto de pérdida de capital. <b style="color:var(--color-text);">Nunca operes con dinero que no puedas permitirte perder.</b> '
        + 'Eres el único responsable de tus decisiones — RSU y sus administradores no se hacen responsables de las pérdidas derivadas del uso de esta información.'
        + '</p>'
        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0;">'
        + '<span onclick="window.__navigate(\'/disclaimer\')" style="color:var(--color-secondary);cursor:pointer;">Leer el descargo completo →</span>'
        + '</p>'
        + '</div>'
        + '<div style="padding:14px 20px;border-top:1px solid var(--color-border);">'
        + '<label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;margin-bottom:14px;">'
        + '<input type="checkbox" id="disclaimer-checkbox" style="margin-top:2px;accent-color:var(--color-accent);cursor:pointer;">'
        + '<span style="color:var(--color-text);font-size:12px;line-height:1.5;">He leído y acepto los términos del descargo de responsabilidad.</span>'
        + '</label>'
        + '<button id="disclaimer-accept-btn" disabled style="width:100%;background:var(--color-border);color:var(--color-muted);border:none;border-radius:var(--radius);padding:10px;font-family:var(--font-mono);font-size:12px;letter-spacing:0.05em;cursor:not-allowed;transition:all .15s;">ACEPTAR Y CONTINUAR</button>'
        + '<span id="disclaimer-error" style="display:block;color:#f23645;font-size:11px;margin-top:8px;text-align:center;"></span>'
        + '</div>'
        + '</div>';

    document.body.appendChild(overlay);

    const checkbox = overlay.querySelector('#disclaimer-checkbox');
    const btn       = overlay.querySelector('#disclaimer-accept-btn');
    const errorEl   = overlay.querySelector('#disclaimer-error');

    checkbox.addEventListener('change', () => {
        btn.disabled = !checkbox.checked;
        btn.style.background = checkbox.checked ? 'var(--color-accent)' : 'var(--color-border)';
        btn.style.color      = checkbox.checked ? '#000' : 'var(--color-muted)';
        btn.style.cursor     = checkbox.checked ? 'pointer' : 'not-allowed';
    });

    btn.addEventListener('click', async () => {
        if (!checkbox.checked) return;
        btn.disabled = true;
        btn.textContent = 'Guardando...';
        errorEl.textContent = '';
        try {
            const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
            const res = await fetch('/api/v1/auth/accept-disclaimer', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
            });
            const data = await res.json();
            if (!data.ok) throw new Error('No se pudo guardar la aceptación');
            overlay.remove();
            if (onAccepted) onAccepted();
        } catch (e) {
            errorEl.textContent = 'Error: ' + e.message + '. Inténtalo de nuevo.';
            btn.disabled = false;
            btn.textContent = 'ACEPTAR Y CONTINUAR';
        }
    });
}