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
        + '<div style="color:var(--color-muted);font-size:12px;letter-spacing:0.1em;margin-bottom:10px;">&gt;&gt; MANIFESTO_RSU.exe</div>'
        + '<div class="manifest-glitch" data-text="REDISTRIBUTION RESEARCH UNIT (RSU)" style="position:relative;display:inline-block;color:var(--color-accent);font-size:28px;letter-spacing:0.06em;text-shadow:var(--glow-text);line-height:1.3;">'
        + 'REDISTRIBUTION RESEARCH UNIT (RSU)'
        + '</div>'
        + '<div style="color:var(--color-secondary);font-size:13px;letter-spacing:0.2em;margin-top:8px;">MANIFIESTO<span class="manifest-cursor"></span></div>'
        + '</div>'
        + divider();
}

function body() {
    const p = (text) => '<p style="color:var(--color-text);font-size:14px;line-height:1.9;margin-bottom:1.25rem;">' + text + '</p>';

    return '<div style="max-width:760px;margin:0 auto;">'

        + p('Vivimos en una atm\u00f3sfera mental que nos impide imaginar un final para este sistema que no sea el colapso total. El neoliberalismo no es solo un modelo econ\u00f3mico; es una tanatopol\u00edtica que nos precariza, nos enferma con ansiedad y luego nos vende el ansiol\u00edtico para que sigamos siendo productivos. Pero mientras nosotros nos hund\u00edamos en la nostalgia y la precariedad, las \u00e9lites segu\u00edan operando en una temporalidad distinta.')

        + p('Warren Buffett lo dijo sin necesidad de suavizarlo:')

        + quote('"Hay guerra de clases, y mi clase, la de los ricos, va ganando."', '', 'danger')

        + p('Esa frase es el punto de partida de todo lo dem\u00e1s. No es una met\u00e1fora ni una exageraci\u00f3n ret\u00f3rica: es la confesi\u00f3n, desde dentro, de quien no tiene ning\u00fan incentivo para mentir sobre qui\u00e9n gana y qui\u00e9n pierde. Si la guerra de clases es real \u2014y lo es, dicha por el bando que la libra y la gana\u2014 entonces la pregunta no es si existe, sino qu\u00e9 vamos a hacer al respecto.')

        + stmt('RSU nace exactamente de esa pregunta.')
        + stmt('RSU nace para dejar de perder.')

        + p('El mercado financiero no es un templo de libertad; es una picadora de carne dise\u00f1ada para extraer valor de la base y concentrarlo en la c\u00faspide. Quienes han trabajado desde dentro de las salas de mercado lo repiten sin pudor: la desigualdad no es un error del sistema, es su funci\u00f3n principal. Mientras la inflaci\u00f3n monetaria devora tus ahorros y consume tu tiempo de vida, las \u00e9lites operan con informaci\u00f3n privilegiada y herramientas que t\u00fa no tienes. Es la misma guerra que describ\u00eda Buffett, solo que librada con datos de flujo, \u00f3rdenes institucionales y ventaja informativa en lugar de titulares.')

        + stmt('Pero incluso el bando que va ganando deja huellas.')

        + p('El mercado posee una vulnerabilidad: su propia infraestructura. Los gigantes no pueden moverse sin dejar rastro. Sus \u00f3rdenes alteran el tejido de la realidad gr\u00e1fica, modifican la liquidez y crean patrones que pueden ser observados por quien sabe interpretarlos.')

        + stmt('No somos inversores pasivos esperando migajas.')
        + stmt('Somos hackers del flujo de capital.', true)

        + p('Buscamos el rastro de las manos fuertes, identificamos sus zonas de manipulaci\u00f3n, acumulaci\u00f3n y distribuci\u00f3n, y ejecutamos un exploit sobre su propia avaricia. Los an\u00e1lisis m\u00e1s l\u00facidos sobre el capital nunca partieron de amarlo, sino de diseccionarlo. Comprender el capital no significa rendirle culto, significa conocer su anatom\u00eda para sobrevivir dentro de \u00e9l.')

        + p('Ah\u00ed fuera, tu g\u00e9nero, tu raza y tu c\u00f3digo postal predeterminan tu techo de cristal. El neoliberalismo privatiza tu malestar y te culpa de tu pobreza.')

        + stmt('Pero el gr\u00e1fico no sabe qui\u00e9n eres.', true)

        + p('El mercado es un entorno hostil y profundamente desigual, s\u00ed, pero es uno de los pocos lugares donde el conocimiento t\u00e9cnico y la disciplina pueden superar a la herencia.')

        + stmt('Operar no es una terapia.')

        + p('La libertad financiera no resuelve todos los problemas, pero elimina uno de los mayores generadores de ansiedad estructural: la dependencia econ\u00f3mica. Tampoco pretendemos presentarnos como benefactores morales ni negar que toda operaci\u00f3n financiera tiene una contraparte.')

        + stmt('Operamos con los ricos sin volvernos como ellos.', true)

        + p('Nuestro objetivo no consiste en extraer rentas del trabajo ajeno, sino en competir dentro de un mercado que ya existe aprovechando ineficiencias, ventajas probabil\u00edsticas y una mejor interpretaci\u00f3n de la informaci\u00f3n disponible. No buscamos explotar personas; buscamos dejar de ser explotados por nuestra ignorancia financiera.')

        + stmt('Si Buffett admite que su clase libra la guerra, nosotros elegimos no fingir que no existe.')

        + divider()

        + p('De ah\u00ed la metodolog\u00eda de RSU.')

        + methodBlock('01', 'Seguir el rastro', 'All\u00ed donde aparece una gran concentraci\u00f3n de liquidez existe informaci\u00f3n. No operamos contra el mercado; operamos contra la ilusi\u00f3n que el mercado proyecta sobre las masas que confunden ruido con direcci\u00f3n.')
        + methodBlock('02', 'Solidaridad t\u00e9cnica', 'El conocimiento burs\u00e1til ha sido propiedad exclusiva de las clases dominantes, y RSU democratiza el acceso al conocimiento reservado hist\u00f3ricamente a las \u00e9lites como forma de redistribuci\u00f3n del poder.')
        + methodBlock('03', 'Realismo operativo', 'Aceptamos que el capitalismo es una estructura abstracta, compleja e impersonal. Precisamente por eso entendemos que, para transformarla o liberarnos parcialmente de sus consecuencias, primero debemos comprender su lenguaje: precio, tiempo, liquidez y probabilidad.')

        + divider()

        + p('El neoliberalismo controla tus deseos para que desees rendir y consumir.')
        + stmt('RSU hackea ese deseo.', true)

        + '<div style="text-align:center;margin:1.75rem 0;">'
            + stmtLine('No queremos Lamborghinis.')
            + stmtLine('Queremos recuperar nuestro tiempo.')
            + stmtLine('Queremos recuperar nuestra capacidad de decidir.')
            + stmtLine('Queremos dejar de vender nuestra vida \u00fanicamente para sobrevivir.')
        + '</div>'

        + stmt('RSU no existe para hacer ricos a unos pocos.')
        + stmt('Existe para devolver capacidad de decisi\u00f3n a quienes nunca la tuvieron.', true)

        + quote('Nuestra revoluci\u00f3n no comienza tomando el Palacio de Invierno.<br>Comienza leyendo correctamente una vela, entendiendo el flujo del capital y neg\u00e1ndonos a seguir siendo \u00fanicamente la liquidez de otros.', '', 'accent')

        + tags(['SEGUIR EL RASTRO', 'SOLIDARIDAD T\u00c9CNICA', 'REALISMO OPERATIVO', 'EJECUTAR'])

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

function stmt(text, emphasis) {
    const size = emphasis ? '17px' : '15px';
    const color = emphasis ? 'var(--color-accent)' : 'var(--color-secondary)';
    const glow = emphasis ? 'text-shadow:var(--glow-text);' : '';
    return '<p style="color:' + color + ';font-size:' + size + ';font-weight:600;letter-spacing:0.02em;text-align:center;margin:1.5rem 0;' + glow + '">' + text + '</p>';
}

function stmtLine(text) {
    return '<div style="color:var(--color-text);font-size:15px;line-height:2.1;">' + text + '</div>';
}

function methodBlock(num, title, text) {
    return '<div style="display:flex;gap:1rem;margin-bottom:1.5rem;align-items:flex-start;">'
        + '<div style="color:var(--color-accent);font-size:13px;letter-spacing:0.1em;flex-shrink:0;padding-top:2px;opacity:0.6;">' + num + '</div>'
        + '<div>'
        + '<div style="color:var(--color-accent);font-size:15px;letter-spacing:0.05em;margin-bottom:0.4rem;">' + title + '</div>'
        + '<div style="color:var(--color-text);font-size:13px;line-height:1.8;">' + text + '</div>'
        + '</div>'
        + '</div>';
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
            '<span style="background:rgba(0,255,173,0.08);color:var(--color-accent);border:1px solid rgba(0,255,173,0.3);border-radius:var(--radius);padding:8px 16px;margin:4px;font-size:12px;letter-spacing:0.08em;white-space:nowrap;">'
            + t + '</span>'
        ).join('')
        + '</div>';
}