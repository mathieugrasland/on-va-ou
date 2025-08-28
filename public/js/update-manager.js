// Gestionnaire de mises à jour pour "On va où ?"
class UpdateManager {
    constructor() {
        this.currentVersion = '1.0.0';
        this.checkInterval = 300000; // Vérifier toutes les 5 minutes (au lieu de 30 sec)
        this.isUpdateAvailable = false;
        this.serviceWorker = null;
        this.lastCheckTime = 0;
        this.minCheckInterval = 60000; // Minimum 1 minute entre les vérifications
        
        this.init();
    }
    
    async init() {
        // Enregistrer le service worker
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                this.serviceWorker = registration;
                console.log('✅ Service Worker enregistré');
                
                // Écouter les mises à jour du service worker
                registration.addEventListener('updatefound', () => {
                    console.log('🔄 Nouvelle version détectée');
                    this.handleUpdateAvailable();
                });
                
                // Vérifier si une mise à jour est déjà en attente
                if (registration.waiting) {
                    this.handleUpdateAvailable();
                }
                
            } catch (error) {
                console.error('❌ Erreur enregistrement Service Worker:', error);
            }
        }
        
        // Vérifier périodiquement les mises à jour (désactivé temporairement)
        // this.startUpdateCheck();
        
        // Vérifier seulement au focus de la fenêtre (throttled)
        let focusCheckTimeout;
        window.addEventListener('focus', () => {
            clearTimeout(focusCheckTimeout);
            focusCheckTimeout = setTimeout(() => this.checkForUpdates(), 2000);
        });
    }
    
    startUpdateCheck() {
        setInterval(() => {
            this.checkForUpdates();
        }, this.checkInterval);
    }
    
    async checkForUpdates() {
        const now = Date.now();
        
        // Throttling: éviter les vérifications trop fréquentes
        if (now - this.lastCheckTime < this.minCheckInterval) {
            console.log('⏳ Vérification trop récente, ignorée');
            return;
        }
        
        this.lastCheckTime = now;
        
        try {
            // Vérifier si les fichiers ont changé avec un timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // Timeout de 5 secondes
            
            const response = await fetch('/index.html?' + now, { 
                method: 'HEAD',
                cache: 'no-cache',
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                console.log('📡 Réponse non OK pour la vérification de mise à jour');
                return;
            }
            
            const lastModified = response.headers.get('Last-Modified');
            const etag = response.headers.get('ETag');
            
            const currentLastModified = localStorage.getItem('app-last-modified');
            const currentEtag = localStorage.getItem('app-etag');
            
            if ((lastModified && lastModified !== currentLastModified) ||
                (etag && etag !== currentEtag)) {
                
                console.log('🆕 Mise à jour disponible');
                localStorage.setItem('app-last-modified', lastModified || '');
                localStorage.setItem('app-etag', etag || '');
                
                this.handleUpdateAvailable();
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('⏰ Vérification de mise à jour timeout');
            } else {
                console.log('📡 Pas de réseau pour vérifier les mises à jour');
            }
        }
    }
    
    handleUpdateAvailable() {
        if (this.isUpdateAvailable) return; // Éviter les doublons
        
        this.isUpdateAvailable = true;
        this.showUpdateNotification();
    }
    
    showUpdateNotification() {
        // Créer une notification discrète
        const notification = document.createElement('div');
        notification.id = 'update-notification';
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #4CAF50, #45a049);
                color: white;
                padding: 15px 20px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                z-index: 10000;
                max-width: 300px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                animation: slideIn 0.3s ease-out;
            ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 20px;">🚀</span>
                    <strong>Mise à jour disponible!</strong>
                </div>
                <p style="margin: 0 0 15px 0; font-size: 14px; opacity: 0.9;">
                    Une nouvelle version est disponible. Rechargez pour obtenir les dernières améliorations.
                </p>
                <div style="display: flex; gap: 10px;">
                    <button onclick="updateManager.applyUpdate()" style="
                        background: rgba(255,255,255,0.2);
                        border: 1px solid rgba(255,255,255,0.3);
                        color: white;
                        padding: 8px 15px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 12px;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.3)'" 
                       onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                        Recharger maintenant
                    </button>
                    <button onclick="updateManager.dismissNotification()" style="
                        background: transparent;
                        border: 1px solid rgba(255,255,255,0.3);
                        color: white;
                        padding: 8px 15px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 12px;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.1)'" 
                       onmouseout="this.style.background='transparent'">
                        Plus tard
                    </button>
                </div>
            </div>
            
            <style>
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            </style>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss après 10 secondes
        setTimeout(() => {
            this.dismissNotification();
        }, 10000);
    }
    
    async applyUpdate() {
        console.log('🔄 Application de la mise à jour...');
        
        // Afficher un loader
        this.showUpdateLoader();
        
        try {
            // Forcer la mise à jour du service worker
            if (this.serviceWorker && this.serviceWorker.waiting) {
                this.serviceWorker.waiting.postMessage({ type: 'SKIP_WAITING' });
            }
            
            // Vider tous les caches
            if ('caches' in window) {
                const cacheNames = await caches.keys();
                await Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                );
            }
            
            // Vider le localStorage des versions
            localStorage.removeItem('app-last-modified');
            localStorage.removeItem('app-etag');
            
            // Recharger la page avec cache-busting
            window.location.href = window.location.href + '?v=' + Date.now();
            
        } catch (error) {
            console.error('❌ Erreur lors de la mise à jour:', error);
            // Fallback: rechargement simple
            window.location.reload(true);
        }
    }
    
    showUpdateLoader() {
        const loader = document.createElement('div');
        loader.id = 'update-loader';
        loader.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 20000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            ">
                <div style="font-size: 48px; margin-bottom: 20px;">🚀</div>
                <h2 style="margin: 0 0 10px 0; color: #333;">Mise à jour en cours...</h2>
                <p style="margin: 0; color: #666; text-align: center;">
                    Application des dernières améliorations<br>
                    Veuillez patienter quelques instants
                </p>
                <div style="
                    width: 200px;
                    height: 4px;
                    background: #e0e0e0;
                    border-radius: 2px;
                    margin-top: 30px;
                    overflow: hidden;
                ">
                    <div style="
                        width: 100%;
                        height: 100%;
                        background: linear-gradient(90deg, #4CAF50, #45a049);
                        animation: loading 2s ease-in-out infinite;
                    "></div>
                </div>
            </div>
            
            <style>
                @keyframes loading {
                    0% { transform: translateX(-100%); }
                    50% { transform: translateX(0%); }
                    100% { transform: translateX(100%); }
                }
            </style>
        `;
        
        document.body.appendChild(loader);
    }
    
    dismissNotification() {
        const notification = document.getElementById('update-notification');
        if (notification) {
            notification.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => notification.remove(), 300);
        }
        
        // Réinitialiser le flag
        this.isUpdateAvailable = false;
    }
    
    // Force une vérification manuelle
    async forceCheck() {
        console.log('🔍 Vérification forcée des mises à jour...');
        
        // Reset du throttling pour la vérification forcée
        this.lastCheckTime = 0;
        localStorage.removeItem('app-last-modified');
        localStorage.removeItem('app-etag');
        
        await this.checkForUpdates();
    }
}

// Initialiser le gestionnaire de mises à jour
const updateManager = new UpdateManager();

// Exposer globalement pour les boutons
window.updateManager = updateManager;

export default UpdateManager;
