// Version simplifiée du gestionnaire de mises à jour
class SimpleUpdateManager {
    constructor() {
        this.isUpdateAvailable = false;
        console.log('🔧 Update Manager simplifié initialisé');
    }
    
    async forceCheck() {
        console.log('🔄 Nettoyage du cache...');
        
        try {
            // 1. Désinscrire le Service Worker
            if ('serviceWorker' in navigator) {
                const registrations = await navigator.serviceWorker.getRegistrations();
                for (const registration of registrations) {
                    await registration.unregister();
                    console.log('🗑️ Service Worker désinscrit');
                }
            }
            
            // 2. Vider tous les caches
            if ('caches' in window) {
                const cacheNames = await caches.keys();
                await Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                );
                console.log('✅ Cache vidé');
            }
            
            // 3. Vider le cache du navigateur via location.reload(true) équivalent
            // Utiliser window.location.replace() avec cache-busting agressif
            const url = new URL(window.location.href);
            url.searchParams.set('_cb', Date.now());
            url.searchParams.set('_force', '1');
            
            // Forcer un hard reload équivalent
            window.location.replace(url.toString());
            
        } catch (error) {
            console.error('❌ Erreur lors du nettoyage:', error);
            // Fallback: rechargement forcé moderne
            window.location.replace(window.location.href + (window.location.href.includes('?') ? '&' : '?') + '_force=' + Date.now());
        }
    }
    
    async applyUpdate() {
        await this.forceCheck();
    }
    
    dismissNotification() {
        console.log('🔕 Notification ignorée');
    }
}

// Initialiser la version simplifiée
const updateManager = new SimpleUpdateManager();

// Exposer globalement pour les boutons
window.updateManager = updateManager;

export default SimpleUpdateManager;
