// ── MODAL DE TRANSPARENCIA DE COSTES ─────────────────────────────────────────
//
// Se muestra una sola vez por usuario, justo después de aceptar el
// disclaimer (mismo patrón: aceptación guardada en el backend, no en el
// navegador -- sigue pidiéndose aunque cambie de dispositivo, deja de
// pedirse en cuanto lo confirma una vez). A diferencia del disclaimer, este
// no bloquea con checkbox obligatorio -- es informativo, no legal, así que
// un solo botón de "Entendido" basta.

export function showPricingModal(onAcknowledged, opciones = {}) {
    const esConsulta = opciones.esConsulta === true;  // reabierto desde la cabecera, no el flujo de bienvenida
    if (document.getElementById('pricing-modal-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'pricing-modal-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.innerHTML =
        '<div style="width:520px;max-width:100%;max-height:85vh;display:flex;flex-direction:column;background:var(--color-surface);border:1px solid var(--color-accent);border-radius:var(--radius);overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.6);">'
        + '<div style="padding:16px 20px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:14px;letter-spacing:0.08em;text-shadow:var(--glow-text);">POR QUÉ RSU TERMINAL NO ES GRATIS DEL TODO</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">Antes de empezar, una cosa que nos gusta dejar clara</div>'
        + '</div>'
        + '<div style="padding:18px 20px;overflow-y:auto;flex:1;">'

        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0 0 12px;">'
        + 'RSU Terminal existe para ayudarte a tomar decisiones de inversión mejor informadas. Y "mejor informadas" depende directamente de una cosa: '
        + '<b style="color:var(--color-text);">la calidad de los datos detrás de cada pantalla</b> — y los datos de calidad cuestan dinero de verdad.'
        + '</p>'

        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0 0 12px;">'
        + '<b style="color:var(--color-text);">Lo que hacemos aquí no es magia, es gestión de información.</b> RSU Terminal no inventa datos ni genera información de la nada — '
        + 'recoge datos de mercado reales (de proveedores que se pagan), les aplica fórmulas y criterios, y te los presenta de forma clara para que decidas tú. '
        + 'Cuanto mejor sea la fuente de datos, mejor es lo que podemos calcular y mostrarte — y las fuentes buenas no son gratis.'
        + '</p>'

        + '<div style="background:var(--color-surface2);border-radius:var(--radius);padding:12px 14px;margin:0 0 12px;">'
        + '<div style="color:var(--color-text);font-size:11.5px;font-weight:600;margin-bottom:8px;">Algunos números reales, para que te hagas una idea:</div>'
        + '<ul style="color:var(--color-muted);font-size:12px;line-height:1.7;margin:0;padding-left:18px;">'
        + '<li>Una tesis de inversión de Gael cuesta, de media, unos <b style="color:var(--color-text);">50€</b> en llamadas a modelos de IA — y eso sin contar las que se descartan por no cumplir los criterios de calidad antes de publicarse.</li>'
        + '<li>El servidor donde vive la terminal, el dominio, y cada una de las APIs de datos de mercado (que además hay que ir mejorando según crece la terminal) tienen coste mensual fijo.</li>'
        + '<li>Cada nueva herramienta que construimos necesita datos nuevos, y los datos nuevos casi siempre cuestan más.</li>'
        + '<li>Y luego está mi tiempo — la terminal la mantengo y la mejoro yo, prácticamente cada día.</li>'
        + '</ul>'
        + '</div>'

        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0 0 12px;">'
        + '<b style="color:var(--color-text);">El objetivo sigue siendo el acceso democrático</b> — así lo dice nuestro manifiesto, y lo creemos de verdad. Pero "democrático" no puede significar "insostenible": '
        + 'si la terminal no se puede pagar a sí misma, no hay terminal para nadie, ni gratis ni de pago. Los tiers de pago no son un capricho — son literalmente lo que permite que existan mejores datos, '
        + 'mejores herramientas, y que este proyecto pueda seguir vivo y mejorando en vez de estancarse o desaparecer.'
        + '</p>'

        + '<p style="color:var(--color-muted);font-size:12.5px;line-height:1.7;margin:0;">'
        + 'Si en algún momento quieres ir más allá del plan gratuito, los tiers <b style="color:var(--color-text);">Tier 1</b> y <b style="color:var(--color-text);">Tier S</b> desbloquean funciones que dependen de esos datos de mejor calidad — '
        + 'y cada suscripción va directa a que la terminal pueda seguir invirtiendo en ser mejor, para todos.'
        + '</p>'

        + '</div>'
        + '<div style="padding:14px 20px;border-top:1px solid var(--color-border);">'
        + '<button id="pricing-ack-btn" style="width:100%;background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px;font-family:var(--font-mono);font-size:12px;letter-spacing:0.05em;cursor:pointer;">' + (esConsulta ? 'CERRAR' : 'ENTENDIDO, GRACIAS') + '</button>'
        + '<span id="pricing-error" style="display:block;color:#f23645;font-size:11px;margin-top:8px;text-align:center;"></span>'
        + '</div>'
        + '</div>';

    document.body.appendChild(overlay);

    if (esConsulta) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
    }

    const btn     = overlay.querySelector('#pricing-ack-btn');
    const errorEl = overlay.querySelector('#pricing-error');

    btn.addEventListener('click', async () => {
        if (esConsulta) {
            overlay.remove();
            return;
        }
        btn.disabled = true;
        btn.textContent = 'Guardando...';
        errorEl.textContent = '';
        try {
            const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
            const res = await fetch('/api/v1/auth/acknowledge-pricing', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
            });
            const data = await res.json();
            if (!data.ok) throw new Error('No se pudo guardar la confirmación');
            overlay.remove();
            if (onAcknowledged) onAcknowledged();
        } catch (e) {
            errorEl.textContent = 'Error: ' + e.message + '. Inténtalo de nuevo.';
            btn.disabled = false;
            btn.textContent = 'ENTENDIDO, GRACIAS';
        }
    });
}