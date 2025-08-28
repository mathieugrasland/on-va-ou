// Service Worker pour "On va où ?" - Gestion intelligente du cache
const CACHE_NAME = 'on-va-ou-v' + Date.now(); // Version unique basée sur le timestamp
const VERSION = '1.0.0';

// Fichiers à mettre en cache
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/dashboard.html', 
    '/profile.html',
    '/login.html',
    '/register.html',
    '/style.css',
    '/firebase-config.js',
    '/js/secure-maps.js',
    '/js/color-config.js',
    '/favicon.ico',
    '/android-chrome-192x192.png',
    '/android-chrome-512x512.png'
];

// Installation du service worker
self.addEventListener('install', (event) => {
    console.log('🔧 Service Worker: Installation...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('📦 Cache ouvert, ajout des assets...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('✅ Service Worker installé avec succès');
                self.skipWaiting(); // Force l'activation immédiate
            })
            .catch((error) => {
                console.error('❌ Erreur installation Service Worker:', error);
            })
    );
});

// Activation du service worker
self.addEventListener('activate', (event) => {
    console.log('🚀 Service Worker: Activation...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        // Supprimer les anciens caches
                        if (cacheName !== CACHE_NAME && cacheName.startsWith('on-va-ou-v')) {
                            console.log('🗑️ Suppression ancien cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('✅ Service Worker activé');
                return self.clients.claim(); // Prendre le contrôle immédiatement
            })
    );
});

// Stratégie de récupération des ressources
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Stratégie pour les fichiers HTML : toujours du réseau
    if (event.request.destination === 'document' || url.pathname.endsWith('.html')) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    // Mettre à jour le cache avec la nouvelle version
                    if (response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME)
                            .then((cache) => cache.put(event.request, responseClone));
                    }
                    return response;
                })
                .catch(() => {
                    // Fallback vers le cache si le réseau échoue
                    return caches.match(event.request);
                })
        );
        return;
    }
    
    // Stratégie pour les autres ressources : cache first avec revalidation
    if (STATIC_ASSETS.some(asset => url.pathname.includes(asset))) {
        event.respondWith(
            caches.match(event.request)
                .then((cachedResponse) => {
                    // Retourner le cache ET fetcher en arrière-plan
                    const fetchPromise = fetch(event.request)
                        .then((response) => {
                            if (response.status === 200) {
                                const responseClone = response.clone();
                                caches.open(CACHE_NAME)
                                    .then((cache) => cache.put(event.request, responseClone));
                            }
                            return response;
                        });
                    
                    // Retourner le cache s'il existe, sinon attendre le réseau
                    return cachedResponse || fetchPromise;
                })
        );
        return;
    }
    
    // Pour tout le reste : réseau d'abord
    event.respondWith(fetch(event.request));
});

// Écouter les messages du client principal
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FORCE_UPDATE') {
        console.log('🔄 Mise à jour forcée demandée');
        
        // Supprimer tous les caches
        event.waitUntil(
            caches.keys()
                .then((cacheNames) => {
                    return Promise.all(
                        cacheNames.map((cacheName) => {
                            if (cacheName.startsWith('on-va-ou-v')) {
                                return caches.delete(cacheName);
                            }
                        })
                    );
                })
                .then(() => {
                    // Redemander les ressources
                    return caches.open(CACHE_NAME);
                })
                .then((cache) => {
                    return cache.addAll(STATIC_ASSETS);
                })
                .then(() => {
                    // Notifier le client que c'est terminé
                    event.ports[0].postMessage({ type: 'UPDATE_COMPLETE' });
                })
        );
    }
    
    if (event.data && event.data.type === 'CHECK_VERSION') {
        event.ports[0].postMessage({ 
            type: 'VERSION_INFO', 
            version: VERSION,
            cache: CACHE_NAME
        });
    }
});
