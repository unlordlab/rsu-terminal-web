// Service Worker de RSU Terminal — estrategia deliberadamente simple:
//
// - Peticiones a /api/*: SIEMPRE red primero (los datos de mercado nunca
//   deben servirse de caché si hay conexión) — solo cae a caché si la red
//   falla del todo, y aun así, mejor una pantalla con datos de hace un rato
//   que una pantalla en blanco.
// - Todo lo demás (HTML/JS/CSS/iconos): caché primero, con refresco en
//   segundo plano — la app abre al instante aunque la red vaya lenta.
//
// No precachea una lista fija de archivos — la app tiene demasiadas páginas
// cargadas de forma dinámica (import() por ruta) como para mantener esa
// lista a mano sin que se desactualice. Cachea lo que se va pidiendo.

const CACHE_NAME = 'rsu-terminal-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(names =>
            Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Solo GET — nunca cachear POST/PUT/DELETE (mutaciones no deben servirse de caché)
    if (event.request.method !== 'GET') return;

    // API: red primero, caché como último recurso si no hay conexión
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then(res => {
                    const clone = res.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return res;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // Resto (HTML/JS/CSS/iconos): caché primero, refresco en segundo plano
    event.respondWith(
        caches.match(event.request).then(cached => {
            const fetchPromise = fetch(event.request).then(res => {
                const clone = res.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return res;
            }).catch(() => cached);
            return cached || fetchPromise;
        })
    );
});