// ─────────────────────────────────────────────────────────────────────────────
// PREVISIONES DEL ROADMAP, CON SU REVISIÓN FECHADA
//
// Una sola fuente para dos páginas: el Roadmap (donde está el texto original)
// y el Track Record (donde se ve si se cumplió). Antes el veredicto vivía
// escrito dentro de roadmap.js y el Track Record no lo mostraba.
//
// LAS REGLAS DE ESTE REGISTRO, que son lo que le da valor:
//   · La previsión se copia TAL CUAL se escribió. No se retoca nunca: una
//     previsión ajustada después de conocer el resultado deja de serlo.
//   · Una revisión NUEVA se AÑADE con su fecha; las anteriores no se borran ni
//     se reescriben. Si una previsión «cumplida» se estropea después, se añade
//     otra revisión que lo diga.
//   · Los veredictos los aprueba el autor. Los del 9/09/2026 los aprobó el
//     10/09/2026, y las cifras salen de cierres diarios de Yahoo Finance
//     (S&P 500, Nasdaq 100 y Russell 2000, datos hasta el 09/09).
//   · Lo que aún no se puede juzgar se marca PENDIENTE, con cuándo se revisará.
// ─────────────────────────────────────────────────────────────────────────────

export const ROADMAP_ESCRITO_EL = '20 de diciembre de 2025';

export const PREVISIONES = [
    {
        prevision: 'Corrección del 8% al 15% en los índices principales durante la primavera',
        seccion: '03 · La caída de primavera',
        revisiones: [
            { fecha: '2026-09-09', veredicto: 'cumplida',
              detalle: 'Se produjo, entre el 9% y el 12% en los tres índices, con el suelo el 30/03: S&P 500 −9,1%, Nasdaq 100 −11,8%, Russell 2000 −11,2%.' },
        ],
    },
    {
        prevision: 'Rebote fuerte tras la caída y recuperación en la segunda mitad del año',
        seccion: '06 · Segundo semestre',
        revisiones: [
            { fecha: '2026-09-09', veredicto: 'cumplida',
              detalle: 'Entre un 20% y un 28% desde el suelo: S&P 500 +20,4%, Nasdaq 100 +28,2%, Russell 2000 +21,0%.' },
        ],
    },
    {
        prevision: 'Inicio constructivo en enero–febrero y caída en primavera (el calendario)',
        seccion: '02 · Estructura temporal',
        revisiones: [
            { fecha: '2026-09-09', veredicto: 'parcial',
              detalle: 'El máximo llegó a finales de enero y el suelo el 30 de marzo, justo al empezar la primavera. La caída se adelantó unas semanas, y el «inicio constructivo de enero–febrero» duró solo enero.' },
        ],
    },
    {
        prevision: 'Cierre de año constructivo si el patrón electoral se mantiene',
        seccion: 'Conclusión',
        revisiones: [
            { fecha: null, veredicto: 'pendiente',
              detalle: 'No se puede juzgar hasta que acabe el año. Se revisará con el cierre de 2026.' },
        ],
    },
];

export const VEREDICTOS = {
    cumplida:  { icono: '✅', texto: 'Cumplida',  color: 'var(--color-accent)' },
    parcial:   { icono: '◐',  texto: 'A medias',  color: '#ffb800' },
    fallida:   { icono: '❌', texto: 'No se cumplió', color: '#f23645' },
    pendiente: { icono: '⏳', texto: 'Pendiente', color: 'var(--color-muted)' },
};

// La revisión que manda es la ÚLTIMA añadida: las anteriores se conservan.
export function ultimaRevision(p) {
    return p.revisiones[p.revisiones.length - 1];
}
