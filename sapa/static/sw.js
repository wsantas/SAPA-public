const CACHE_NAME = 'sapa-v1';
const CACHED_URLS = ['/', '/manifest.json'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(CACHED_URLS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    // Network-first strategy: try fetch, cache response, fall back to cache
    if (event.request.method !== 'GET') return;

    // Skip WebSocket and API requests from caching
    const url = new URL(event.request.url);
    if (url.pathname.startsWith('/ws') || url.pathname.startsWith('/api/')) return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
