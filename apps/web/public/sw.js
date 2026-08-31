const CACHE_NAME = 'sunybot-cache-v4'

const APP_SHELL = [
    '/',
    '/index.html',
    '/manifest.webmanifest',
    '/icons/icon-192.png',
    '/icons/icon-512.png'
]

function isDynamicBackendRequest(request) {
    const url = new URL(request.url)
    if (url.origin !== self.location.origin) return false

    return (
        url.pathname.startsWith('/api/') ||
        url.pathname === '/health' ||
        url.pathname === '/status' ||
        url.pathname === '/chat' ||
        url.pathname === '/command'
    )
}

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    )
    self.skipWaiting()
})

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        ))
    )
    self.clients.claim()
})

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return

    // Live API, health and MJPEG stream responses must never come from
    // CacheStorage. Let the browser go to Nginx -> Gateway -> Vision directly.
    if (isDynamicBackendRequest(event.request)) return

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) return cachedResponse

            return fetch(event.request)
                .then((networkResponse) => {
                    if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                        return networkResponse
                    }
                    const responseClone = networkResponse.clone()
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone))
                    return networkResponse
                })
                .catch(() => caches.match('/index.html'))
        })
    )
})
