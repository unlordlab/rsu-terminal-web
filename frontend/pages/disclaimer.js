export async function render(container) {
    container.innerHTML = pageContent();
}

function pageContent() {
    return header() + sections() + footer();
}

function header() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">DESCARGO DE RESPONSABILIDAD</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">RSU Terminal · Términos y condiciones legales</div>'
        + '</div>';
}

function sections() {
    return [

        section('01', 'CARÁCTER EDUCATIVO E INFORMATIVO',
            p('Todo el contenido compartido en la comunidad RSU, incluyendo análisis de mercado, señales de trading, gráficos, vídeos y comentarios, tiene una finalidad estrictamente educativa e informativa.')
            + highlight('Bajo ninguna circunstancia debe considerarse como asesoría financiera, recomendación de inversión o invitación a comprar/vender activos financieros.')
        ),

        section('02', 'RIESGO DE CAPITAL',
            p('El trading de activos financieros conlleva un nivel de riesgo alto y puede no ser adecuado para todos los inversores. Existe la posibilidad de perder una parte o la totalidad del capital invertido — incluye acciones, forex, criptomonedas y futuros.')
            + highlight('Nunca operes con dinero que no puedas permitirte perder. El apalancamiento puede amplificar tanto ganancias como pérdidas.')
        ),

        section('03', 'RESPONSABILIDAD INDIVIDUAL',
            p('Cada miembro de RSU es el único responsable de sus propias decisiones financieras y ejecuciones en el mercado. Los resultados pasados no garantizan rendimientos futuros.')
            + list([
                'Eres responsable de tus propias decisiones de trading',
                'Realiza tu propio análisis antes de operar',
                'Gestiona tu riesgo de forma adecuada',
            ])
            + highlight('La comunidad y sus administradores no se hacen responsables de las pérdidas o daños económicos que puedan derivarse del uso de la información compartida.')
        ),

        section('04', 'NO SOMOS ASESORES FINANCIEROS',
            p('Los administradores y moderadores de RSU no son asesores financieros titulados ni gestores de patrimonio. Somos traders y entusiastas del mercado compartiendo conocimiento entre nosotros — no asesoría certificada.')
            + highlight('Te recomendamos encarecidamente que consultes con un profesional financiero certificado antes de tomar cualquier decisión de inversión significativa.')
        ),

        section('05', 'RENDIMIENTOS PASADOS',
            p('Cualquier resultado, rendimiento o estadística mostrada en la comunidad hace referencia a resultados históricos. Los rendimientos pasados no son garantía de resultados futuros.')
            + highlight('Los backtests y simulaciones tienen limitaciones inherentes y no reflejan las condiciones reales del mercado con comisiones, slippage y limitaciones de liquidez.')
        ),

        section('06', 'USO DE LA INFORMACIÓN',
            p('La información proporcionada en RSU Terminal y la comunidad es para uso personal y educativo. Queda prohibida su redistribución comercial sin autorización expresa.')
            + list([
                'Uso personal permitido',
                'Compartir con fines educativos',
                'Redistribución comercial sin autorización — no permitido',
                'Reproducción sin citar la fuente — no permitido',
            ])
        ),

    ].join('');
}

function footer() {
    return '<div style="border-top:1px solid var(--color-border);padding-top:1.5rem;margin-top:0.5rem;">'
        + '<p style="color:var(--color-muted);font-size:12px;line-height:1.7;max-width:640px;">'
        + 'Al utilizar RSU Terminal y participar en la comunidad, declaras comprender y aceptar los riesgos inherentes al trading y liberas a RSU de cualquier responsabilidad legal o financiera derivada del uso de este contenido.'
        + '</p>'
        // La versión debe coincidir con users_service.DISCLAIMER_VERSION: al
        // cambiar este texto hay que subir aquel número, y entonces a todos
        // los usuarios se les vuelve a pedir la aceptación con el texto nuevo
        // (antes solo se guardaba la fecha, así que un cambio de texto dejaba
        // a los usuarios existentes bajo condiciones que nunca vieron).
        + '<div style="color:var(--color-muted);font-size:10px;letter-spacing:0.05em;margin-top:1rem;opacity:0.6;">Versión 1 · Última actualización: febrero 2025</div>'
        + '</div>';
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function section(num, title, content) {
    return '<div style="margin-bottom:1.75rem;padding-bottom:1.75rem;border-bottom:1px solid var(--color-border);">'
        + '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:0.75rem;">'
        + '<span style="color:var(--color-accent);font-size:11px;letter-spacing:0.05em;">' + num + '</span>'
        + '<span style="color:var(--color-text);font-size:13px;letter-spacing:0.06em;">' + title + '</span>'
        + '</div>'
        + content
        + '</div>';
}

function p(text) {
    return '<p style="color:var(--color-muted);font-size:13px;line-height:1.75;margin:0 0 0.85rem;">' + text + '</p>';
}

// Único estilo de énfasis para todo el documento — antes había tres cajas de
// colores distintos (verde/naranja/rojo) compitiendo entre sí; ahora es un
// único formato sobrio, coherente con el resto de la terminal.
function highlight(text) {
    return '<div style="border-left:2px solid var(--color-accent);background:var(--color-surface);border-radius:0 var(--radius) var(--radius) 0;padding:0.7rem 1rem;margin:0.85rem 0;">'
        + '<p style="color:var(--color-text);font-size:12.5px;line-height:1.6;margin:0;">' + text + '</p>'
        + '</div>';
}

function list(items) {
    return '<div style="margin:0.85rem 0;">'
        + items.map(item => {
            const negative = item.includes(' — no permitido');
            const clean    = item.replace(' — no permitido', '');
            return '<div style="display:flex;align-items:flex-start;gap:8px;padding:3px 0;font-size:12.5px;">'
                + '<span style="color:var(--color-muted);flex-shrink:0;">' + (negative ? '✕' : '·') + '</span>'
                + '<span style="color:var(--color-muted);">' + clean + '</span>'
                + '</div>';
        }).join('')
        + '</div>';
}