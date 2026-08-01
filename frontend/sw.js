// Service Worker de RSU Terminal.
//
// POR QUÉ CAMBIÓ LA ESTRATEGIA (01/08/2026)
//
// La versión anterior servía TODO lo que no fuera /api/ con "caché primero
// y refresco en segundo plano" (`return cached || fetchPromise`). Eso hace
// que, tras un despliegue, la primera visita reciba la versión VIEJA de
// cada fichero y descargue la nueva para la visita SIGUIENTE.
//
// Con una app de módulos ES que se importan entre sí, eso no deja la app
// "un poco desactualizada": la deja ROTA A MEDIAS, porque cada fichero se
// cachea por separado y se refresca a su propio ritmo. Caso real que lo
// destapó: al publicar el módulo 27 de Academy, el navegador ya tenía el
// academy.js nuevo (y por eso pintaba la tarjeta del módulo, que sale de
// MODULES, dentro de ese fichero) pero seguía con el academy_manifest.js
// viejo (y por eso el módulo aparecía SIN NINGUNA LECCIÓN, porque la lista
// sale de LESSON_INDEX, que vive en el manifiesto). Módulo construido,
// contenido invisible, y ningún error en consola que lo explicara.
//
// Además, CACHE_NAME nunca se versionaba, así que el `activate` —que borra
// las cachés cuyo nombre no coincide— no llegaba a limpiar nada nunca.
//
// ESTRATEGIA ACTUAL, POR TIPO DE PETICIÓN
//
// - /api/*              → red primero, caché solo si no hay conexión. Los
//                         datos de mercado nunca deben servirse de caché
//                         habiendo red (sin cambios respecto a antes).
// - Código de la app    → red primero, caché solo si no hay conexión. Es el
//   (HTML/JS/CSS/JSON)    grafo de módulos: o va entero al día, o va entero
//                         atrasado, pero nunca mitad y mitad.
// - Estáticos inmutables → caché primero con refresco en segundo plano.
//   (imágenes, iconos,     Son pesados y no cambian entre despliegues; ahí
//    fuentes)              esa estrategia sí es la correcta.
//
// La app sigue abriendo sin conexión: lo que cambia es que, HABIENDO red,
// se sirve siempre una versión coherente consigo misma.
//
// No precachea una lista fija de archivos — la app tiene demasiadas páginas
// cargadas de forma dinámica (import() por ruta) como para mantener esa
// lista a mano sin que se desactualice. Cachea lo que se va pidiendo.

const CACHE_NAME = 'rsu-terminal-v2';

// Extensiones que forman el código de la aplicación. Si algún día se importa
// desde JS un tipo de fichero nuevo, tiene que entrar en esta lista o volverá
// el problema de arriba.
const EXT_CODIGO = /\.(js|mjs|css|html|json)$/i;

function esCodigoDeLaApp(request, url) {
    // Una navegación (cargar la propia página) va siempre por red primero:
    // es el punto de entrada del grafo de módulos.
    if (request.mode === 'navigate') return true;
    return EXT_CODIGO.test(url.pathname);
}

async function redPrimero(request) {
    try {
        const res = await fetch(request);
        // Solo se cachean respuestas buenas: si durante un despliegue el
        // servidor devuelve un 404 o un 500, no debe quedarse guardado como
        // si fuera el contenido válido de ese fichero.
        if (res && res.ok) {
            const copia = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, copia));
        }
        return res;
    } catch (err) {
        // Sin conexión: se sirve lo último que se vio. Si tampoco hay nada
        // cacheado, se deja que el fallo llegue al navegador tal cual, en vez
        // de inventar una respuesta vacía que parecería válida.
        const cacheado = await caches.match(request);
        if (cacheado) return cacheado;
        throw err;
    }
}

function cachePrimeroConRefresco(request) {
    return caches.match(request).then(cacheado => {
        const enRed = fetch(request).then(res => {
            if (res && res.ok) {
                const copia = res.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(request, copia));
            }
            return res;
        }).catch(() => cacheado);
        return cacheado || enRed;
    });
}

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // Al subir CACHE_NAME a v2, esto borra de una vez la caché v1 de todos
    // los usuarios — que es justo la que puede arrastrar la mezcla de
    // ficheros viejos y nuevos de despliegues anteriores. clients.claim()
    // va DENTRO del waitUntil para que no corra antes de que la limpieza
    // haya terminado.
    event.waitUntil(
        caches.keys()
            .then(nombres => Promise.all(
                nombres.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;

    // Solo GET — nunca cachear POST/PUT/DELETE (mutaciones no deben
    // servirse de caché).
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    // Peticiones a otros dominios: que las gestione el navegador.
    if (url.origin !== self.location.origin) return;

    if (url.pathname.startsWith('/api/') || esCodigoDeLaApp(request, url)) {
        event.respondWith(redPrimero(request));
        return;
    }

    event.respondWith(cachePrimeroConRefresco(request));
});
