import { esc } from '/core/ui.js';

// Política de privacidad. Dos cosas que hay que respetar al tocar este fichero:
//
// 1. DESCRIBE LO QUE EL CÓDIGO HACE, no lo que suena bien. Cada apartado sale
//    de una auditoría real de las bases de datos y de las llamadas salientes
//    (18/08/2026). Si mañana se añade una tabla con datos personales, o una
//    llamada nueva a un tercero, HAY QUE ACTUALIZAR ESTO -- una política que
//    se queda vieja es peor que no tenerla, porque afirma algo falso.
//
// 2. LOS PLAZOS DE ARRIBA SON LOS DEL CÓDIGO. 90 días de analítica y 30 de
//    chat están en analytics_service.RETENCION_DIAS y chat_service.
//    RETENCION_DIAS, y hay un test que comprueba que no se separen.
//
// Los datos del titular NO están aquí: el repositorio es público y un DNI
// escrito en un fichero queda publicado para siempre en el historial de git.
// Se piden a /api/v1/legal/titular, que los lee del .env del servidor.

const ACTUALIZADA = '18 de agosto de 2026';

export async function render(container) {
    let titular = null;
    try {
        const res = await fetch('/api/v1/legal/titular');
        titular = await res.json();
    } catch (_) { /* se dice abajo, no se rompe la página */ }

    container.innerHTML = cabecera() + bloqueTitular(titular) + cuerpo();
}

function cabecera() {
    return `<div style="margin-bottom:1.5rem;">
        <div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;margin-bottom:4px;">POLÍTICA DE PRIVACIDAD</div>
        <div style="color:var(--color-muted);font-size:12px;">Última actualización: ${esc(ACTUALIZADA)}</div>
    </div>`;
}

function bloqueTitular(t) {
    // Sin responsable identificado la política no vale. Se dice en vez de
    // enseñar un hueco, para que se note y se arregle.
    if (!t || !t.ok || !t.completo) {
        return seccion('Quién responde de tus datos', `
            <div style="background:rgba(255,184,0,0.10);border:1px solid #ffb800;border-radius:var(--radius);padding:10px 14px;font-size:12px;">
                ⚠️ Los datos del responsable no están configurados en este servidor,
                así que esta política todavía <strong>no está completa</strong>.
            </div>`);
    }
    return seccion('Quién responde de tus datos', `
        <p>${esc(t.nombre)}, con NIF ${esc(t.nif)}, actuando como persona física.</p>
        <p>Para cualquier cosa relacionada con tus datos, incluido ejercer los derechos
        que se explican más abajo: <strong>${esc(t.email)}</strong>.</p>`);
}

function seccion(titulo, html) {
    return `<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:16px 20px;margin-bottom:1rem;max-width:820px;">
        <div style="color:var(--color-accent);font-size:13px;letter-spacing:.06em;margin-bottom:10px;">${esc(titulo)}</div>
        <div style="color:var(--color-text);font-size:13px;line-height:1.7;">${html}</div>
    </div>`;
}

function cuerpo() {
    return seccion('Qué guardamos, y por qué', `
        <p>Todo lo que guardamos está en un servidor propio. No hay ninguna empresa de
        analítica de terceros: ni Google Analytics, ni píxeles de redes sociales, ni
        cookies de publicidad. Esto es lo que hay, apartado por apartado:</p>
        <ul style="margin:10px 0 0 18px;">
            <li><strong>Tu cuenta</strong>: tu correo, tu contraseña cifrada (nunca en claro,
                ni siquiera nosotros podemos leerla), tu plan y las fechas de alta y de
                aceptación del aviso legal. Sin esto no hay forma de que entres.</li>
            <li><strong>Lo que has configurado</strong>: tu watchlist, tus alertas y tu progreso
                en la Academia. Son la razón de tener cuenta.</li>
            <li><strong>Telegram</strong>, solo si lo vinculas: el identificador de tu chat, para
                poder mandarte tus alertas. Al desvincularlo se borra.</li>
            <li><strong>Tus mensajes al chat</strong> de la terminal, para dar continuidad a la
                conversación.</li>
            <li><strong>Tu feedback</strong>, si nos escribes: el mensaje y el contacto que dejes.</li>
            <li><strong>Uso de la terminal</strong>: qué secciones se abren y qué valores se
                consultan. <strong>Esto no lleva tu correo</strong>: se guarda con una huella
                irreversible que sirve para contar personas distintas pero no para saber
                quién eres. Nos dice qué partes se usan, no quién usa qué.</li>
            <li><strong>Registros del servidor</strong>: como cualquier servidor web, anota la
                dirección IP de cada petición. Se usan para diagnosticar problemas.</li>
        </ul>
        <p style="margin-top:12px;">Los datos de mercado —precios, escaneos, cadenas de
        opciones— no son tuyos ni te identifican: son información pública y no forman parte
        de esto.</p>`)

    + seccion('Cuánto tiempo', `
        <ul style="margin:0 0 0 18px;">
            <li><strong>Tu cuenta y lo que has configurado</strong>: mientras la tengas. Si la
                borras, desaparece en el momento.</li>
            <li><strong>Uso de la terminal</strong>: 90 días.</li>
            <li><strong>Mensajes del chat</strong>: 30 días.</li>
            <li><strong>Feedback</strong>: 1 año, por si hay que darle seguimiento.</li>
            <li><strong>Registros del servidor</strong>: se rotan, con un tope aproximado de 30 días.</li>
        </ul>
        <p style="margin-top:10px;">Estos plazos no son una intención: hay un proceso que
        borra automáticamente lo que los supera.</p>`)

    + seccion('Quién más ve algo', `
        <p>Muy poco sale de aquí, y conviene que sepas exactamente qué:</p>
        <ul style="margin:10px 0 0 18px;">
            <li><strong>Groq</strong> (Estados Unidos), solo si usas el chat: recibe el texto de
                tu pregunta para poder responderla. <strong>No recibe tu correo</strong> ni sabe
                quién la hace.</li>
            <li><strong>Telegram</strong>, solo si lo has vinculado: recibe tus alertas y el
                identificador de tu chat, que es lo que permite entregártelas.</li>
        </ul>
        <p style="margin-top:12px;">La terminal consulta muchas fuentes de datos de mercado
        —Yahoo Finance, Finnhub, la Reserva Federal, la SEC, CoinGecko y otras—, pero esas
        consultas son sobre valores, nunca sobre personas: preguntan por el precio de un
        ticker, no por quién lo está mirando.</p>
        <p>No vendemos ni cedemos datos a nadie más. No hacemos perfiles publicitarios.</p>`)

    + seccion('Cookies', `
        <p>Dos, y las dos son técnicas: una guarda tu sesión para que no tengas que
        volver a entrar en cada página, y otra la sesión del panel de administración.
        Ninguna sirve para seguirte, ni dentro ni fuera de la terminal, y por eso no hay
        banner de cookies: no hay nada que consentir.</p>`)

    + seccion('Qué puedes hacer con tus datos', `
        <p>Desde <strong>Mi Cuenta</strong>, sin pedírnoslo y sin esperar:</p>
        <ul style="margin:10px 0 0 18px;">
            <li><strong>Descargarlos todos</strong>, en un fichero que se puede leer y llevar a
                otro sitio.</li>
            <li><strong>Borrar tu cuenta</strong> y todo lo asociado. Es inmediato e
                irreversible, y te decimos cuántos registros se han eliminado.</li>
            <li><strong>Desvincular Telegram</strong>.</li>
        </ul>
        <p style="margin-top:12px;">Además puedes pedirnos que corrijamos algo, que
        limitemos el uso de tus datos o que nos opongamos a tratarlos, escribiendo al
        correo de arriba. Y si crees que no lo hacemos bien, puedes reclamar ante la
        Agencia Española de Protección de Datos (<span style="color:var(--color-muted);">aepd.es</span>).</p>`)

    + seccion('Seguridad, dicho con honestidad', `
        <p>Las contraseñas se guardan cifradas con bcrypt y la sesión viaja en una cookie
        que el JavaScript de la página no puede leer. Las copias de seguridad de las bases
        de datos se hacen a diario.</p>
        <p><strong>Lo que todavía no está</strong>: la terminal se sirve por HTTP y no por
        HTTPS mientras no haya un dominio con certificado. Eso significa que, en una red que
        no controles, el tráfico entre tu navegador y el servidor podría ser interceptado.
        Está pendiente de resolver y preferimos decirlo aquí antes que dejarlo implícito.</p>`)

    + seccion('Cambios', `
        <p>Si esto cambia, cambia la fecha de arriba. Si el cambio es importante, se avisa
        dentro de la terminal: enterarse por casualidad no es enterarse.</p>`);
}
