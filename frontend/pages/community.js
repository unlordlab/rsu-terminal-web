const DISCORD_URL = 'https://discord.gg/ztSpwB9qe';
const CONTACT_EMAIL = 'unl4b@proton.me';

const FAQ_ITEMS = [
    {
        q: '¿Cómo cambio mi contraseña?',
        a: 'Desde el login, usa la opción "¿Olvidaste tu contraseña?" para recibir instrucciones. Si no te llega o tienes problemas, escríbeme por aquí abajo o en Discord y te la reseteo a mano.',
    },
    {
        q: '¿Por qué no veo datos en Scanner o en Amplitud de Mercado?',
        a: 'Esos módulos dependen de un scan nocturno automático (GitHub Actions) que descarga el histórico de las ~500 acciones del S&P 500 una vez al día. Si acabas de registrarte o el scan de esa noche falló, puede que veas menos datos de lo normal — se recupera solo en el siguiente ciclo, no hace falta hacer nada.',
    },
    {
        q: '¿Cómo recibo avisos de mis alertas de Watchlist?',
        a: 'Por ahora, solo dentro de la propia terminal: verás una campanita roja junto a "Watchlist" en el menú cuando salte una alerta. Todavía no hay notificación por email ni por Discord/Telegram fuera de la app — está en el roadmap para cuando montemos los agentes de comunidad.',
    },
    {
        q: '¿Qué diferencia hay entre los planes (Free, Tier 1, Tier S)?',
        a: 'Ahora mismo casi todo está disponible para todo el mundo mientras seguimos puliendo la herramienta. La segmentación por planes de pago llegará más adelante — cuando se active, se avisará con tiempo en Discord y aquí en Comunidad de qué pasa a ser de pago y qué se queda gratis.',
    },
    {
        q: '¿Dónde aprendo a usar bien la metodología de RSU?',
        a: 'En la sección Academia — más de 20 módulos que cubren desde análisis técnico básico hasta las herramientas propias de RSU (RSU Score, El Triángulo RSU, RS/RW). Es el mejor punto de partida antes de operar con convicción usando lo que ves en la terminal.',
    },
];

function authHeader() {
    const token = sessionStorage.getItem('rsu_token') || localStorage.getItem('rsu_token');
    return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export async function render(container) {
    container.innerHTML = pageShell();
    wireFaq(container);
    wireForm(container);
}

function wireFaq(container) {
    container.querySelectorAll('.faq-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const answer = btn.nextElementSibling;
            const arrow  = btn.querySelector('.faq-arrow');
            const isOpen = answer.style.display === 'block';
            answer.style.display = isOpen ? 'none' : 'block';
            arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
        });
    });
}

function shell(title, content, subtitle) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;text-shadow:var(--glow-text);">' + title + '</div>'
        + (subtitle ? '<div style="color:var(--color-muted);font-size:10px;">' + subtitle + '</div>' : '')
        + '</div>'
        + content
        + '</div>';
}

function pageShell() {
    const discordCard = shell('DISCORD', '<div style="padding:1.25rem;">'
        + '<p style="color:var(--color-text);font-size:13px;line-height:1.6;margin:0 0 1rem;">'
        + 'El servidor de Discord es donde vivimos el día a día: comparto análisis, respondo dudas y la comunidad discute setups en tiempo real. Si estás en RSU Terminal, este es el sitio para conocer a los demás usuarios y estar al tanto de lo que se cuece antes de que llegue a la propia terminal.'
        + '</p>'
        + '<a href="' + DISCORD_URL + '" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:8px;background:#5865F2;color:#fff;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:12px;text-decoration:none;letter-spacing:0.03em;">'
        + '💬 UNIRME AL DISCORD ↗</a>'
        + '</div>');

    const feedbackCard = shell('BUGS Y SUGERENCIAS', '<div style="padding:1.25rem;">'
        + '<p style="color:var(--color-text);font-size:13px;line-height:1.6;margin:0 0 1rem;">'
        + 'RSU Terminal se mejora constantemente a partir de lo que reporta la propia comunidad. Si algo no funciona, algo no cuadra, o se te ocurre algo que le vendría bien a la herramienta, este es el sitio — lo leo todo personalmente.'
        + '</p>'

        + '<div style="display:flex;gap:8px;margin-bottom:0.75rem;flex-wrap:wrap;">'
        + '<select id="fb-tipo" style="background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '<option value="bug">🐞 Reportar un bug</option>'
        + '<option value="sugerencia">💡 Sugerencia</option>'
        + '<option value="otro">✉️ Otro</option>'
        + '</select>'
        + '<input id="fb-contacto" type="email" placeholder="Tu email (opcional, para poder responderte)" style="flex:1;min-width:220px;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;">'
        + '</div>'

        + '<textarea id="fb-mensaje" rows="4" maxlength="3000" placeholder="Cuéntame qué ha pasado o qué se te ha ocurrido..." style="width:100%;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;outline:none;box-sizing:border-box;resize:vertical;margin-bottom:0.75rem;"></textarea>'

        + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
        + '<button id="fb-submit-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:9px 22px;font-family:var(--font-mono);font-size:12px;cursor:pointer;font-weight:500;">ENVIAR</button>'
        + '<span id="fb-msg" style="font-size:11px;color:var(--color-muted);"></span>'
        + '<a href="mailto:' + CONTACT_EMAIL + '?subject=RSU%20Terminal" style="color:var(--color-muted);font-size:11px;text-decoration:none;border-bottom:1px dotted var(--color-muted);">o escríbeme directo a ' + CONTACT_EMAIL + '</a>'
        + '</div>'
        + '</div>');

    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">👥 COMUNIDAD</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Discord, soporte y sugerencias — abierto para todos los usuarios de RSU Terminal</div>'
        + '</div>'
        + discordCard
        + faqCard()
        + feedbackCard;
}

function faqCard() {
    const items = FAQ_ITEMS.map((item, i) =>
        '<div class="faq-item" style="border-bottom:1px solid var(--color-border);">'
        + '<button class="faq-question" data-idx="' + i + '" style="width:100%;display:flex;justify-content:space-between;align-items:center;gap:8px;background:none;border:none;padding:12px 0;cursor:pointer;text-align:left;color:var(--color-text);font-family:var(--font-mono);font-size:13px;">'
        + '<span>' + item.q + '</span>'
        + '<span class="faq-arrow" style="color:var(--color-muted);font-size:11px;flex-shrink:0;transition:transform .15s;">▼</span>'
        + '</button>'
        + '<div class="faq-answer" style="display:none;padding:0 0 14px;color:var(--color-muted);font-size:12px;line-height:1.6;">' + item.a + '</div>'
        + '</div>'
    ).join('');

    return shell('PREGUNTAS FRECUENTES', '<div style="padding:0.25rem 1.25rem 0.5rem;">' + items + '</div>');
}

function wireForm(container) {
    const btn  = container.querySelector('#fb-submit-btn');
    const msg  = container.querySelector('#fb-msg');

    btn.addEventListener('click', async () => {
        const tipo     = container.querySelector('#fb-tipo').value;
        const mensaje  = container.querySelector('#fb-mensaje').value.trim();
        const contacto = container.querySelector('#fb-contacto').value.trim();

        if (!mensaje) {
            msg.style.color = '#f23645';
            msg.textContent = 'Escribe un mensaje antes de enviar';
            return;
        }

        btn.disabled = true;
        msg.style.color = 'var(--color-muted)';
        msg.textContent = 'Enviando...';

        try {
            const res  = await fetch('/api/v1/community/feedback', {
                method: 'POST', headers: authHeader(),
                body: JSON.stringify({ tipo, mensaje, contacto }),
            });
            const data = await res.json();
            if (data.ok) {
                msg.style.color = '#00ffad';
                msg.textContent = '¡Gracias! Mensaje recibido ✓';
                container.querySelector('#fb-mensaje').value = '';
                container.querySelector('#fb-contacto').value = '';
            } else {
                msg.style.color = '#f23645';
                msg.textContent = data.error || 'No se pudo enviar el mensaje';
            }
        } catch (e) {
            msg.style.color = '#f23645';
            msg.textContent = 'Error de red: ' + e.message;
        } finally {
            btn.disabled = false;
        }
    });
}