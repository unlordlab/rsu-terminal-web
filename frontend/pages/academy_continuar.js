// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — ¿Por dónde sigue cada uno? (tarjeta del Dashboard)
//
// Qué módulo está COMPLETO lo decide el servidor (`pendientes` de
// /api/v1/academy/certificado, la misma regla que emite el certificado): aquí
// no se vuelve a calcular. Esto solo decide POR DÓNDE seguir: el módulo de la
// última lección leída mientras le falte algo, y si no, el siguiente pendiente
// en el orden en que Academy enseña los módulos.
//
// Sin imports a propósito: así se puede ejecutar fuera del navegador.
// ─────────────────────────────────────────────────────────────────────────────

// progreso:  { lessons: ['0-1', ...], ultima: '12-3' | null }
// cert:      { pendientes: [{modulo, quiz}], modulos_completos, modulos_total, emitido }
// catalogo:  { orden: [0, 1, 2, ...], modulos: { 12: { title, lecciones: [{key, title}] } } }
//
// Devuelve null cuando no hay nada que proponer, o
// { tipo: 'empezar' | 'seguir' | 'quiz' | 'nuevo' | 'certificado', ... }
export function siguientePaso(progreso, cert, catalogo) {
    const base = { completos: cert.modulos_completos, modulosTotal: cert.modulos_total };
    const pendientes = new Map((cert.pendientes || []).map(p => [p.modulo, p]));

    if (!pendientes.size) {
        // Todo completo: si aún no ha pedido el certificado, se le recuerda.
        return cert.emitido ? null : { ...base, tipo: 'certificado' };
    }

    const leidas = new Set(progreso.lessons || []);
    const orden = catalogo.orden.filter(id => catalogo.modulos[id]);
    const ultimo = progreso.ultima ? Number(String(progreso.ultima).split('-')[0]) : null;

    let actual;
    if (ultimo !== null && pendientes.has(ultimo)) {
        actual = ultimo;
    } else {
        // El siguiente pendiente DESPUÉS del último que tocó (y, si no queda
        // ninguno detrás, vuelta al principio); sin historial, el primero.
        const desde = ultimo !== null ? orden.indexOf(ultimo) + 1 : 0;
        const vuelta = orden.slice(desde).concat(orden.slice(0, desde));
        actual = vuelta.find(id => pendientes.has(id));
    }
    const m = catalogo.modulos[actual];
    if (m === undefined) return null;

    const siguiente = m.lecciones.find(l => !leidas.has(l.key)) || null;
    const quiz = pendientes.get(actual).quiz;
    // El servidor dice que falta algo y aquí no se ve qué (el progreso y el
    // certificado llegan en dos peticiones): mejor no enseñar nada que
    // enseñar algo que no cuadra.
    if (!siguiente && !quiz) return null;

    let tipo;
    if (!siguiente) tipo = 'quiz';
    else if (cert.emitido) tipo = 'nuevo';          // tiene el certificado y han salido módulos nuevos
    else if (!leidas.size) tipo = 'empezar';
    else tipo = 'seguir';

    return {
        ...base, tipo, quiz,
        modulo: { id: actual, title: m.title },
        leccion: siguiente,
        leidas: m.lecciones.filter(l => leidas.has(l.key)).length,
        total: m.lecciones.length,
    };
}
