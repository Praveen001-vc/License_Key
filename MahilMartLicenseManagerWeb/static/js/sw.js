const CACHE_VERSION = "mmlm-v8";
const SHELL_CACHE = `shell-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;

const SHELL_ASSETS = [
  "/",
  "/manifest.webmanifest",
  "/static/css/app.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/favicon-32.png",
  "/static/icons/favicon.ico",
];

function isSameOrigin(request) {
  const url = new URL(request.url);
  return url.origin === self.location.origin;
}

function isCssOrJs(request) {
  if (!isSameOrigin(request)) return false;
  const url = new URL(request.url);
  return /\.(?:css|js)$/i.test(url.pathname);
}

function isStaticAsset(request) {
  if (!isSameOrigin(request)) return false;
  const url = new URL(request.url);
  return (
    url.pathname.startsWith("/static/") ||
    url.pathname === "/manifest.webmanifest" ||
    /\.(?:ico|png|jpg|jpeg|svg|webmanifest|woff2?)$/i.test(url.pathname)
  );
}

async function putInRuntimeCache(request, response) {
  if (!response || !response.ok) return response;
  const cache = await caches.open(RUNTIME_CACHE);
  await cache.put(request, response.clone());
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== SHELL_CACHE && key !== RUNTIME_CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(SHELL_CACHE);
        const fallback = await cache.match("/");
        return fallback || Response.error();
      })
    );
    return;
  }

  if (isCssOrJs(request)) {
    event.respondWith(
      fetch(request)
        .then((response) => putInRuntimeCache(request, response))
        .catch(async () => {
          const cached = await caches.match(request);
          return cached || Response.error();
        })
    );
    return;
  }

  if (isStaticAsset(request)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const networkFetch = fetch(request)
          .then((response) => putInRuntimeCache(request, response))
          .catch(() => null);

        if (cached) {
          event.waitUntil(networkFetch);
          return cached;
        }

        return networkFetch.then((response) => response || Response.error());
      })
    );
  }
});
