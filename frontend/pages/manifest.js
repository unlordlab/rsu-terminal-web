export async function render(container) {
    injectStyles();
    container.innerHTML = pageContent();
}

function injectStyles() {
    if (document.getElementById('manifest-styles')) return;
    const style = document.createElement('style');
    style.id = 'manifest-styles';
    style.textContent = '.manifest-cursor{display:inline-block;width:8px;height:14px;background:var(--color-accent);animation:manifest-blink 1s infinite;vertical-align:middle;margin-left:3px;}'
        + '@keyframes manifest-blink{0%,50%{opacity:1;}51%,100%{opacity:0;}}'
        + '.manifest-glitch::before,.manifest-glitch::after{content:attr(data-text);position:absolute;top:0;left:0;width:100%;height:100%;background:var(--color-bg);overflow:hidden;}'
        + '.manifest-glitch::before{left:2px;text-shadow:-1px 0 #f23645;clip:rect(24px,550px,90px,0);animation:manifest-glitch-1 2.5s infinite linear alternate-reverse;}'
        + '.manifest-glitch::after{left:-2px;text-shadow:-1px 0 var(--color-secondary);clip:rect(85px,550px,140px,0);animation:manifest-glitch-2 2.5s infinite linear alternate-reverse;}'
        + '@keyframes manifest-glitch-1{0%{clip:rect(20px,9999px,51px,0);}25%{clip:rect(89px,9999px,15px,0);}50%{clip:rect(10px,9999px,82px,0);}75%{clip:rect(65px,9999px,99px,0);}100%{clip:rect(34px,9999px,12px,0);}}'
        + '@keyframes manifest-glitch-2{0%{clip:rect(65px,9999px,99px,0);}25%{clip:rect(10px,9999px,82px,0);}50%{clip:rect(89px,9999px,15px,0);}75%{clip:rect(20px,9999px,51px,0);}100%{clip:rect(76px,9999px,43px,0);}}';
    document.head.appendChild(style);
}

function pageContent() {
    return header() + body() + footer();
}

function header() {
    return '<div style="text-align:center;margin-bottom:2rem;">'
        + '<div style="color:var(--color-muted);font-size:11px;letter-spacing:0.15em;margin-bottom:8px;">[SECURE CONNECTION ESTABLISHED // ENCRYPTION: AES-256]</div>'
        + '<div class="manifest-glitch" data-text=">> MANIFESTO_RSU.exe" style="position:relative;display:inline-block;color:var(--color-accent);font-size:32px;letter-spacing:0.1em;text-shadow:var(--glow-text);">'
        + '>> MANIFESTO_RSU.exe'
        + '</div>'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.2em;margin-top:8px;">PROTOCOLO DE DESPERTAR DE CLASE // CICLO PERMANENTE<span class="manifest-cursor"></span></div>'
        + '</div>'
        + divider();
}

function body() {
    const p = (text) => '<p style="color:var(--color-text);font-size:14px;line-height:1.9;margin-bottom:1.25rem;">' + text + '</p>';

    return '<div style="max-width:760px;margin:0 auto;">'

        + p('Vivimos en el <b style="color:var(--color-accent);">Realismo Capitalista</b>: esa atmósfera mental que nos impide imaginar un final para este sistema que no sea el colapso total. El neoliberalismo no es solo un modelo económico; es una tanatopolítica que nos precariza, nos enferma con ansiedad y luego nos vende el ansiolítico para que sigamos siendo productivos. Nos dijeron que el futuro había muerto, que el <code>"No Future"</code> punk era una profecía cumplida. Pero mientras nosotros nos hundíamos en la nostalgia y la precariedad, las élites seguían operando en una temporalidad distinta.')

        + p('Warren Buffett lo dijo sin necesidad de suavizarlo:')

        + quote('"Hay guerra de clases, y mi clase, la de los ricos, va ganando."', '— Warren Buffett [TARGET_ACQUIRED]', 'danger')

        + p('Esa frase es el punto de partida de todo lo demás. No es una metáfora ni una exageración retórica: es la confesión, desde dentro, de quien no tiene ningún incentivo para mentir sobre quién gana y quién pierde. Si la guerra de clases es real —y lo es, dicha por el bando que la libra y la gana— entonces la pregunta no es si existe, sino qué vamos a hacer al respecto. <b style="color:var(--color-accent);">RSU nace exactamente de esa pregunta. RSU nace para dejar de perder.</b>')

        + p('El mercado financiero no es un templo de libertad; es una picadora de carne diseñada para extraer valor de la base y concentrarlo en la cúspide. Quienes han trabajado desde dentro de las salas de mercado lo repiten sin pudor: la desigualdad no es un error del sistema, es su función principal. Mientras la inflación monetaria devora tus ahorros y tu tiempo de vida, las élites operan con información privilegiada y herramientas que tú no tienes. Es la misma guerra que describía Buffett, solo que librada con datos de flujo, órdenes institucionales y ventaja informativa en lugar de titulares.')

        + p('Pero incluso el bando que va ganando deja huellas. El mercado posee una vulnerabilidad: su propia infraestructura. Los gigantes no pueden moverse sin dejar rastro; sus órdenes alteran el tejido de la realidad gráfica, y ese rastro de liquidez es legible para quien sabe mirarlo. No somos inversores pasivos esperando migajas. Somos <b style="color:var(--color-accent);">hackers del flujo de capital</b>. Buscamos el rastro de las <code>"manos fuertes"</code>, identificamos sus zonas de manipulación y ejecutamos un exploit sobre su propia avaricia. Los análisis más lúcidos sobre el capital nunca partieron de amarlo, sino de diseccionarlo: entender el capital no es rendirle culto, es aprender su anatomía para sobrevivir a él y, si se puede, para dar la vuelta a la frase de Buffett a nuestro favor.')

        + p('Ahí fuera, tu género, tu raza y tu código postal predeterminan tu techo de cristal. El neoliberalismo privatiza tu malestar y te culpa de tu pobreza. Pero el gráfico no sabe quién eres. El mercado es un entorno hostil, sí, pero es uno de los pocos lugares donde el conocimiento técnico y la disciplina pueden superar a la herencia. Operar no es una terapia, pero la libertad financiera es la única cura real para la ansiedad estructural de la precariedad. Y aun así, operamos con los ricos sin volvernos como ellos: no buscamos la explotación del prójimo, sino la extracción de liquidez de un sistema amañado que lleva décadas robándonos el futuro. Si Buffett admite que su clase libra la guerra, nosotros elegimos no fingir que no existe.')

        + p('De ahí el código de RSU. Primero, <b style="color:var(--color-accent);">seguir el rastro</b>: donde hay manipulación, hay oportunidad; no operamos contra el mercado, operamos contra la ilusión que el mercado crea para las masas. Segundo, <b style="color:var(--color-accent);">solidaridad técnica</b>: el conocimiento bursátil ha sido propiedad exclusiva de las clases dominantes, y RSU democratiza el acceso a la <code>"caja negra"</code> del trading profesional. Tercero, <b style="color:var(--color-accent);">realismo operativo</b>: aceptamos que el capitalismo es una estructura impersonal y abstracta, y que para destruirla o escapar de ella primero debemos dominar su lenguaje —el precio y el tiempo—.')

        + p('El neoliberalismo controla tus deseos para que desees rendir. RSU hackea ese deseo. No queremos Lamborghinis; queremos nuestro tiempo de vuelta. Queremos la soberanía que nos fue arrebatada.')

        + quote('Si la guerra de clases es real, el gráfico es nuestro mapa de guerra.<br>Si ellos ganan porque tienen la información —como reconoció el propio Buffett—, nosotros ganaremos porque sabemos leer su rastro.', '', 'accent')

        + tags(['HACKEA EL DESEO', 'RECLAMA EL TIEMPO', 'LEE EL RASTRO', 'EJECUTA'])

        + '</div>';
}

function footer() {
    return divider()
        + '<div style="text-align:center;padding:1.5rem 0;">'
        + '<div style="color:var(--color-accent);font-size:26px;letter-spacing:0.15em;text-shadow:var(--glow-text);margin-bottom:6px;">BIENVENIDOS A RSU</div>'
        + '<div style="color:#f23645;font-size:14px;letter-spacing:0.1em;">El exploit ha comenzado<span class="manifest-cursor"></span></div>'
        + '</div>'
        + '<div style="text-align:center;color:var(--color-muted);font-size:10px;letter-spacing:0.15em;border-top:1px solid var(--color-border);padding-top:1rem;margin-top:1rem;">'
        + '[END OF TRANSMISSION // MANIFEST_RSU_v1.0]<br>'
        + '[TIMESTAMP: PERMANENTE]<br>'
        + '[LICENSE: COPYLEFT // STATUS: ACTIVE]'
        + '</div>';
}

// ── HELPERS ───────────────────────────────────────────────────────────────────

function divider() {
    return '<div style="height:1px;background:linear-gradient(90deg,transparent,var(--color-accent),transparent);margin:1.5rem 0;"></div>';
}

function quote(text, attribution, tone) {
    const color = tone === 'danger' ? '#f23645' : 'var(--color-accent)';
    const bg = tone === 'danger' ? 'rgba(242,54,69,0.06)' : 'rgba(0,255,173,0.06)';
    const border = tone === 'danger' ? 'rgba(242,54,69,0.25)' : 'rgba(0,255,173,0.2)';
    return '<div style="background:' + bg + ';border:1px solid ' + border + ';border-radius:var(--radius);padding:1.25rem 1.5rem;margin:1.5rem 0;text-align:center;">'
        + '<div style="color:' + color + ';font-size:19px;letter-spacing:0.03em;line-height:1.5;">' + text + '</div>'
        + (attribution ? '<div style="color:var(--color-muted);font-size:12px;margin-top:10px;letter-spacing:0.05em;">' + attribution + '</div>' : '')
        + '</div>';
}

function box(type, content) {
    const styles = {
        warning: 'border:1px solid rgba(255,152,0,0.3);background:rgba(255,152,0,0.04);color:#ff9800;',
        danger:  'border:1px solid rgba(242,54,69,0.3);background:rgba(242,54,69,0.04);color:#f23645;',
    };
    return '<div style="' + (styles[type] || styles.warning) + 'border-radius:var(--radius);padding:1rem 1.25rem;margin:1.25rem 0;font-size:13px;line-height:1.8;">'
        + content
        + '</div>';
}

function tags(items) {
    return '<div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:1.75rem 0 0.5rem;">'
        + items.map(t =>
            '<span style="background:rgba(0,255,173,0.08);color:var(--color-accent);border:1px solid rgba(0,255,173,0.3);border-radius:var(--radius);padding:8px 16px;font-size:12px;letter-spacing:0.08em;">'
            + t + '</span>'
        ).join('')
        + '</div>';
}