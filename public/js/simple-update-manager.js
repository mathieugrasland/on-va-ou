// Version simplifiée du gestionnaire de mises à jour
class SimpleUpdateManager {
    constructor() {
        this.isUpdateAvailable = false;
        console.log('🔧 Update Manager simplifié initialisé');
    }
    
    async forceCheck() {
        console.log('🔄 Simulation d\'un Ctrl+F5 (Hard Refresh)...');
        
        try {
            // 1. Désinscrire TOUS les Service Workers
            if ('serviceWorker' in navigator) {
                const registrations = await navigator.serviceWorker.getRegistrations();
                for (const registration of registrations) {
                    await registration.unregister();
                }
                console.log('🗑️ Service Workers désinscrit');
            }
            
            // 2. Vider TOUS les caches
            if ('caches' in window) {
                const cacheNames = await caches.keys();
                await Promise.all(cacheNames.map(cache => caches.delete(cache)));
                console.log('🗑️ Caches vidés');
            }
            
            // 3. Vider le localStorage et sessionStorage 
            if (typeof(Storage) !== "undefined") {
                localStorage.clear();
                sessionStorage.clear();
                console.log('🗑️ Storage vidé');
            }
            
            console.log('🔄 Hard refresh...');
            
            // 4. TECHNIQUE ULTIME : Simuler un Ctrl+F5
            // Créer une nouvelle window avec cache disabled
            const currentUrl = window.location.href.split('?')[0];
            const hardRefreshUrl = `${currentUrl}?_hardRefresh=${Date.now()}&_t=${Math.random()}`;
            
            // Force replacement sans cache
            window.location.href = hardRefreshUrl;
            
        } catch (error) {
            console.error('❌ Erreur critique:', error);
            // ULTIME fallback
            window.location.href = window.location.href + '?_emergency=' + Date.now();
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
