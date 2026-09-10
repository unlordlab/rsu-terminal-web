// ── FRASE DEL DÍA ────────────────────────────────────────────────────────────
// Cada frase con autor lleva su fuente, rastreada hasta el original. La que no
// se ha podido rastrear lleva su nombre, pero dice que es atribuida. Las que
// no tienen autor son dichos de mercado.
//
// Módulo aparte y sin imports para poder ejecutarlo fuera del navegador.

export const FRASES = [
    {
        texto: 'En un mercado alcista, las malas noticias se ignoran y las buenas se celebran; en un mercado bajista, las buenas se ignoran y las malas se exageran.',
        autor: '', fuente: '',
    },
    {
        texto: 'Hay una guerra de clases, de acuerdo, pero es mi clase, la clase rica, la que está haciendo la guerra, y la estamos ganando.',
        autor: 'Warren Buffett',
        fuente: 'a Ben Stein, The New York Times, 26 de noviembre de 2006',
    },
    {
        texto: 'El mercado no les gana. Se ganan ellos solos, porque aunque tienen cabeza, no saben quedarse quietos.',
        autor: 'Edwin Lefèvre',
        fuente: '«Reminiscences of a Stock Operator» (1923), la vida de Jesse Livermore novelada',
    },
    {
        texto: 'Las manos fuertes no compran en la euforia: compran cuando las manos débiles ya no pueden soportar más dolor.',
        autor: '', fuente: '',
    },
    {
        texto: 'La bolsa hace de centro de reubicación: el dinero pasa de los inversores activos a los pacientes.',
        autor: 'Warren Buffett',
        fuente: 'carta a los accionistas de Berkshire Hathaway, 1991',
    },
    {
        texto: 'Cuando el último escéptico se vuelve alcista, es hora de vender.',
        autor: '', fuente: '',
    },
    {
        texto: 'El mercado puede seguir siendo irracional más tiempo del que tú puedes seguir siendo solvente.',
        autor: 'A. Gary Shilling',
        fuente: 'economista, 1986. Se suele atribuir a Keynes, pero no hay constancia de que él la dijera ni la escribiera',
    },
    {
        texto: 'El éxito en el trading consiste en comprarles a los pesimistas y venderles a los optimistas.',
        autor: '', fuente: '',
    },
    {
        texto: 'La bolsa es un lugar donde las crisis se preparan... es el árbol donde los pequeños inversores son sacudidos para que sus ahorros caigan en los bolsillos de los grandes especuladores.',
        autor: 'Friedrich Engels',
        fuente: 'atribuida; no se ha localizado en sus obras',
    },
    {
        texto: 'He estado especulando, en parte con fondos americanos, pero sobre todo con acciones inglesas […]. Es un tipo de operación que exige poco tiempo, y merece la pena correr algún riesgo para aliviar al enemigo de su dinero.',
        autor: 'Karl Marx',
        fuente: 'carta a su tío Lion Philips, 25 de junio de 1864',
    },
];

// Número de día en el calendario de Madrid: la frase cambia a medianoche de
// Madrid y es la misma para todos durante ese día, esté donde esté cada uno.
export function diaDeMadrid(fecha = new Date()) {
    const partes = {};
    for (const p of new Intl.DateTimeFormat('en-US', {
        timeZone: 'Europe/Madrid', year: 'numeric', month: 'numeric', day: 'numeric',
    }).formatToParts(fecha)) partes[p.type] = Number(p.value);
    return Math.floor(Date.UTC(partes.year, partes.month - 1, partes.day) / 86400000);
}

// Días seguidos, frases seguidas: ninguna se repite hasta haber salido todas.
export function fraseDelDia(fecha = new Date()) {
    return FRASES[diaDeMadrid(fecha) % FRASES.length];
}
