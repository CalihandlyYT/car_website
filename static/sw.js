// Версия кеша - обновляйте при каждом изменении
const CACHE_NAME = 'autoreview-v' + new Date().getTime();
const STATIC_CACHE = 'static-v' + new Date().getTime();

// Статические файлы, которые можно кешировать надолго
const staticFilesToCache = [
  '/static/manifest.json',
  '/static/icon-192x192.png',
  '/static/icon-96x96.png',
  '/static/icon-152x152.png',
  '/static/favicon.ico'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Service Worker: Caching static files');
        return cache.addAll(staticFilesToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Удаляем все старые кеши
          if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => self.clients.claim())
  );
});

// Перехват запросов
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Для HTML страниц - всегда загружаем из сети, но используем кеш как fallback
  if (request.method === 'GET' && request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .then((response) => {
          // Клонируем ответ для кеша
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
          });
          return response;
        })
        .catch(() => {
          // Если сеть недоступна, используем кеш
          return caches.match(request);
        })
    );
  }
  // Для статических файлов - сначала кеш, потом сеть
  else if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            // Проверяем обновления в фоне
            fetch(request).then((networkResponse) => {
              if (networkResponse.ok) {
                caches.open(STATIC_CACHE).then((cache) => {
                  cache.put(request, networkResponse.clone());
                });
              }
            });
            return cachedResponse;
          }
          // Если нет в кеше, загружаем из сети
          return fetch(request).then((response) => {
            if (response.ok) {
              const responseToCache = response.clone();
              caches.open(STATIC_CACHE).then((cache) => {
                cache.put(request, responseToCache);
              });
            }
            return response;
          });
        })
    );
  }
  // Для остальных запросов - сеть с fallback на кеш
  else {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match(request))
    );
  }
});
