// Configuration Google Maps - ATTENTION: Sécuriser en production
// TODO: Utiliser des variables d'environnement ou restrictions de domaine
export const GOOGLE_MAPS_API_KEY = "AIzaSyBUNmeroMLlCNzrpCi7-6VCGBGfJ4Eg4MQ";

// Charger l'API Google Maps dynamiquement
export function loadGoogleMapsAPI() {
    return new Promise((resolve, reject) => {
        // Vérifier si l'API est déjà chargée
        if (window.google && window.google.maps) {
            resolve();
            return;
        }

        // Créer le script sans callback (chargement manuel)
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
        script.async = true;
        script.defer = true;
        
        script.onload = () => {
            // Attendre un peu que l'API soit complètement initialisée
            setTimeout(() => resolve(), 100);
        };
        script.onerror = () => reject(new Error('Erreur chargement Google Maps API'));
        
        document.head.appendChild(script);
    });
}
