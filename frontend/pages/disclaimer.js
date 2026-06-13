export async function render(container) {
    container.innerHTML = pageContent();
}

function pageContent() {
    return header() + sections() + footer();
}

function header() {
    return '<div style="text-align:center;margin-bottom:2rem;">'
        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.15em;margin-bottom:8px;">[SECURE CONNECTION ESTABLISHED // ENCRYPTION: AES-256]</div>'
        + '<div style="color:var(--color-accent);font-size:24px;letter-spacing:0.12em;text-shadow:var(--glow-text);margin-bottom:6px;">⚖️ DESCARGO DE RESPONSABILIDAD</div>'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.2em;">RSU TRADING COMMUNITY // TÉRMINOS Y CONDICIONES LEGALES</div>'
        + '</div>'
        + divider();
}

function sections() {
    return [

        section('01 // CARÁCTER EDUCATIVO E INFORMATIVO',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'Todo el contenido compartido en la comunidad <b style="color:var(--color-accent)">RSU</b>, incluyendo análisis de mercado, señales de trading, gráficos, videos y comentarios, tiene una finalidad <b style="color:var(--color-accent)">estrictamente educativa e informativa</b>.'
            + '</p>'
            + box('danger', '<p style="color:#f23645;font-size:13px;margin:0;"><b>⚠️ IMPORTANTE</b><br>Bajo ninguna circunstancia debe considerarse como asesoría financiera, recomendación de inversión o invitación a comprar/vender activos financieros.</p>')
            + badges([
                { text: 'Educativo',    color: 'var(--color-accent)' },
                { text: 'Informativo',  color: '#ff9800' },
                { text: 'No es Asesoría', color: '#f23645' },
            ])
        ),

        section('02 // RIESGO DE CAPITAL',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'El trading de activos financieros conlleva un <b style="color:#f23645;">alto nivel de riesgo</b> y puede no ser adecuado para todos los inversores. Existe la posibilidad de perder una parte o la totalidad del capital invertido.'
            + '</p>'
            + riskMeter()
            + box('warning', '<p style="color:#ff9800;font-size:13px;margin:0;"><b>🛑 ADVERTENCIA CRÍTICA</b><br><b style="color:var(--color-text);">Nunca operes con dinero que no puedas permitirte perder.</b> El apalancamiento puede amplificar tanto ganancias como pérdidas.</p>')
            + badges([
                { text: 'Forex',          color: '#f23645' },
                { text: 'Criptomonedas',  color: '#f23645' },
                { text: 'Acciones',       color: '#f23645' },
                { text: 'Futuros',        color: '#f23645' },
            ])
        ),

        section('03 // RESPONSABILIDAD INDIVIDUAL',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'Cada miembro de <b style="color:var(--color-accent)">RSU</b> es el <b style="color:var(--color-accent)">único responsable</b> de sus propias decisiones financieras y ejecuciones en el mercado. Los resultados pasados no garantizan rendimientos futuros.'
            + '</p>'
            + phaseBox([
                '✓ Tú eres responsable de tus decisiones de trading',
                '✓ Realiza tu propio análisis antes de operar',
                '✓ Gestiona tu riesgo adecuadamente',
            ])
            + box('danger', '<p style="color:#f23645;font-size:13px;margin:0;"><b>📋 LIMITACIÓN DE RESPONSABILIDAD</b><br>La comunidad y sus administradores <b>no se hacen responsables</b> de las pérdidas o daños económicos que puedan derivarse del uso de la información compartida.</p>')
        ),

        section('04 // NO SOMOS ASESORES FINANCIEROS',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'Los administradores y moderadores de <b style="color:var(--color-accent)">RSU</b> <b>no son asesores financieros titulados</b> ni gestores de patrimonio. Somos traders y entusiastas del mercado compartiendo conocimiento.'
            + '</p>'
            + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0;">'
            + stratCard('❌ NO ES', 'Asesoría financiera certificada', '#f23645')
            + stratCard('✅ SÍ ES', 'Conocimiento compartido entre traders', 'var(--color-accent)')
            + '</div>'
            + box('default', '<p style="color:var(--color-accent);font-size:13px;margin:0;"><b>👨‍💼 RECOMENDACIÓN PROFESIONAL</b><br><span style="color:var(--color-muted);">Te recomendamos encarecidamente que consultes con un <b style="color:var(--color-text);">profesional financiero certificado</b> antes de tomar cualquier decisión de inversión significativa.</span></p>')
        ),

        section('05 // RENDIMIENTOS PASADOS',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'Cualquier resultado, rendimiento o estadística mostrada en la comunidad hace referencia a resultados históricos. <b style="color:#f23645;">Los rendimientos pasados no son garantía de resultados futuros.</b>'
            + '</p>'
            + box('warning', '<p style="color:#ff9800;font-size:13px;margin:0;"><b>📊 NOTA SOBRE BACKTESTS</b><br>Los backtests y simulaciones tienen limitaciones inherentes y no reflejan las condiciones reales del mercado con comisiones, slippage y limitaciones de liquidez.</p>')
        ),

        section('06 // USO DE LA INFORMACIÓN',
            '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;margin-bottom:1rem;">'
            + 'La información proporcionada en RSU Terminal y la comunidad es para uso personal y educativo. Queda prohibida su redistribución comercial sin autorización expresa.'
            + '</p>'
            + phaseBox([
                '✓ Uso personal permitido',
                '✓ Compartir con fines educativos',
                '✗ Redistribución comercial sin autorización',
                '✗ Reproducción sin citar la fuente',
            ])
        ),

    ].join('');
}

function footer() {
    return '<div style="background:rgba(0,255,173,0.03);border:1px solid var(--color-accent);border-radius:var(--radius);padding:2rem;text-align:center;margin-top:2rem;">'
        + '<div style="font-size:2rem;margin-bottom:1rem;">📜</div>'
        + '<div style="color:var(--color-accent);font-size:16px;letter-spacing:0.1em;margin-bottom:0.75rem;">NOTA IMPORTANTE</div>'
        + '<p style="color:var(--color-muted);font-size:13px;line-height:1.8;max-width:600px;margin:0 auto 1.5rem;">'
        + 'Al permanecer en esta comunidad y utilizar nuestro contenido, declaras comprender y aceptar los riesgos inherentes al trading y '
        + '<b style="color:#f23645;">liberas a RSU de cualquier responsabilidad legal o financiera</b>.'
        + '</p>'
        + '<div style="border-top:1px solid var(--color-border);padding-top:1rem;color:var(--color-muted);font-size:10px;letter-spacing:0.15em;">'
        + '[END OF DISCLAIMER // RSU_LEGAL_v2025]<br>'
        + '[ÚLTIMA ACTUALIZACIÓN: FEBRERO 2025]<br>'
        + '[STATUS: ACTIVE]'
        + '</div>'
        + '</div>';
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function section(title, content) {
    return '<div style="margin-bottom:2rem;">'
        + '<div style="color:var(--color-secondary);font-size:14px;letter-spacing:0.1em;border-left:3px solid var(--color-accent);padding-left:10px;margin-bottom:1rem;">' + title + '</div>'
        + content
        + '</div>'
        + divider();
}

function divider() {
    return '<div style="height:1px;background:linear-gradient(90deg,transparent,var(--color-accent),transparent);margin:1.5rem 0;"></div>';
}

function box(type, content) {
    const styles = {
        default: 'border:1px solid rgba(0,255,173,0.2);background:rgba(0,255,173,0.03);',
        warning: 'border:1px solid rgba(255,152,0,0.3);background:rgba(255,152,0,0.03);',
        danger:  'border:1px solid rgba(242,54,69,0.3);background:rgba(242,54,69,0.03);',
    };
    return '<div style="' + (styles[type] || styles.default) + 'border-radius:var(--radius);padding:1rem 1.25rem;margin:1rem 0;">'
        + content
        + '</div>';
}

function phaseBox(items) {
    return '<div style="border-left:3px solid var(--color-accent);padding:1rem 1.25rem;margin:1rem 0;background:var(--color-surface);border-radius:0 var(--radius) var(--radius) 0;">'
        + items.map(item => {
            const isOk = item.startsWith('✓');
            const color = isOk ? 'var(--color-accent)' : '#f23645';
            return '<div style="display:flex;align-items:flex-start;gap:10px;padding:6px 0;font-size:13px;">'
                + '<span style="color:' + color + ';flex-shrink:0;">' + item.substring(0,1) + '</span>'
                + '<span style="color:var(--color-muted);">' + item.substring(2) + '</span>'
                + '</div>';
        }).join('')
        + '</div>';
}

function badges(items) {
    return '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:1rem;">'
        + items.map(b =>
            '<span style="background:' + b.color + '18;color:' + b.color + ';border:1px solid ' + b.color + '44;border-radius:20px;padding:3px 14px;font-size:11px;letter-spacing:0.05em;">'
            + b.text + '</span>'
        ).join('')
        + '</div>';
}

function riskMeter() {
    return '<div style="display:flex;align-items:center;gap:1rem;padding:1rem;background:var(--color-surface);border-radius:var(--radius);margin:1rem 0;">'
        + '<span style="color:var(--color-muted);font-size:12px;flex-shrink:0;">RIESGO:</span>'
        + '<div style="flex:1;height:8px;background:var(--color-bg,#0a0a0a);border-radius:4px;position:relative;">'
        + '<div style="width:85%;height:100%;background:linear-gradient(90deg,var(--color-accent) 0%,#ff9800 50%,#f23645 100%);border-radius:4px;"></div>'
        + '<div style="position:absolute;top:-4px;left:85%;transform:translateX(-50%);width:16px;height:16px;background:#fff;border:3px solid #f23645;border-radius:50%;box-shadow:0 0 8px #f2364566;"></div>'
        + '</div>'
        + '<span style="color:#f23645;font-size:14px;font-weight:500;flex-shrink:0;">ALTO</span>'
        + '</div>';
}

function stratCard(title, text, color) {
    return '<div style="background:var(--color-surface);border:1px solid ' + color + '33;border-radius:var(--radius);padding:1.25rem;text-align:center;">'
        + '<div style="color:' + color + ';font-size:14px;letter-spacing:0.05em;margin-bottom:8px;">' + title + '</div>'
        + '<p style="color:' + color + ';font-size:13px;margin:0;">' + text + '</p>'
        + '</div>';
}