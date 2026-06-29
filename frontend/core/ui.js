// Helpers de UI compartidos entre páginas — evita duplicar HTML de error
// en cada módulo. Pensado para crecer con otros patrones comunes (loading,
// empty state, etc.) si hace falta en el futuro.

const RATE_LIMIT_PATTERN = /demasiadas peticiones|rate limit|máximo \d+ requests/i;

/**
 * Detecta si un mensaje de error corresponde a un rate limit (429),
 * para poder darle un tratamiento visual distinto del de un error real.
 */
export function isRateLimitMessage(msg) {
    return RATE_LIMIT_PATTERN.test(msg || '');
}

/**
 * HTML de error genérico para insertar en un contenedor de widget.
 * Si el mensaje es de rate limit, usa color ámbar + icono de reloj en vez
 * del rojo/✗ de un fallo real — comunica "espera un momento", no "algo falló".
 */
export function errorMessage(msg, opts = {}) {
    const padding = opts.padding || '1rem';
    const fontSize = opts.fontSize || '12px';
    const extraStyle = opts.extraStyle || '';

    if (isRateLimitMessage(msg)) {
        return '<div style="padding:' + padding + ';color:#ffb800;font-size:' + fontSize + ';display:flex;align-items:center;gap:6px;' + extraStyle + '">'
            + '<span style="font-size:14px;">⏱</span><span>' + msg + '</span></div>';
    }
    return '<div style="padding:' + padding + ';color:#f23645;font-size:' + fontSize + ';' + extraStyle + '">✗ ' + msg + '</div>';
}