// Version simplifiée du gestionnaire de mises à jour
class SimpleUpdateManager {
    constructor() {
        this.isUpdateAvailable = false;
        console.log('🔧 Update Manager simplifié initialisé');
    }
    
    async forceCheck() {
        console.log('🔄 Nettoyage du cache...');
        
        try {
            // Vider tous les caches
            if ('caches' in window) {
                const cacheNames = await caches.keys();
                await Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                );
                console.log('✅ Cache vidé');
            }
            
            // Recharger avec cache-busting
            window.location.href = window.location.href + '?v=' + Date.now();
            
        } catch (error) {
            console.error('❌ Erreur lors du nettoyage:', error);
            // Fallback: rechargement forcé
            window.location.reload(true);
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
