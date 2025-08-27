/**
 * Service de géocodage sécurisé utilisant les Cloud Functions
 * Cette approche protège la clé API en la cachant côté serveur
 */

class SecureGeocodingService {
    constructor(auth = null) {
        this.baseUrl = 'https://us-central1-on-va-ou-470217.cloudfunctions.net';
        this.auth = auth;
    }

    /**
     * Géocoder une adresse via le service sécurisé
     * @param {string} address - Adresse à géocoder
     * @returns {Promise<{lat: number, lng: number, formatted_address: string}>}
     */
    async geocodeAddress(address) {
        try {
            const user = this.auth?.currentUser;
            if (!user) {
                throw new Error('Utilisateur non authentifié');
            }

            const token = await user.getIdToken();
            
            const response = await fetch(`${this.baseUrl}/geocode_address`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ address: address.trim() })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur de géocodage');
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Adresse non trouvée');
            }

            return {
                lat: data.location.lat,
                lng: data.location.lng,
                formatted_address: data.formatted_address
            };

        } catch (error) {
            console.error('Erreur géocodage sécurisé:', error);
            throw error;
        }
    }

    /**
     * Géocoder plusieurs adresses en parallèle
     * @param {string[]} addresses - Liste d'adresses
     * @returns {Promise<Array>}
     */
    async geocodeMultipleAddresses(addresses) {
        const promises = addresses.map(address => 
            this.geocodeAddress(address).catch(error => ({
                address,
                error: error.message
            }))
        );

        return Promise.all(promises);
    }
}

/**
 * Gestionnaire de carte sécurisée avec géocodage côté serveur
 */
class SecureMapManager {
    constructor(mapElementId, auth = null, db = null) {
        this.mapElementId = mapElementId;
        this.map = null;
        this.userMarker = null;
        this.friendMarkers = [];
        this.geocodingService = new SecureGeocodingService(auth);
        this.isInitialized = false;
        this.auth = auth;
        this.db = db;
    }

    /**
     * Initialiser la carte Google Maps
     * Note: La clé API est maintenant gérée côté client pour l'affichage uniquement
     */
    async initializeMap() {
        try {
            // Position par défaut (Paris)
            const defaultPosition = { lat: 48.8566, lng: 2.3522 };

            this.map = new google.maps.Map(document.getElementById(this.mapElementId), {
                zoom: 12,
                center: defaultPosition,
                mapTypeId: 'roadmap',        // Forcer le type "carte" uniquement
                mapTypeControl: false,       // Supprimer sélecteur map/satellite
                streetViewControl: false,    // Supprimer Street View
                fullscreenControl: true,     // Garder le plein écran
                zoomControl: false,          // Supprimer boutons +/-
                scrollwheel: true,           // Garder le zoom à la molette
                gestureHandling: 'auto'      // Gestes tactiles normaux
            });

            this.isInitialized = true;
            console.log('Carte initialisée avec succès');

            // Charger la position de l'utilisateur
            await this.loadUserLocation();

        } catch (error) {
            console.error('Erreur initialisation carte:', error);
            throw error;
        }
    }

    /**
     * Charger la position de l'utilisateur depuis son profil
     */
    async loadUserLocation() {
        try {
            const user = this.auth?.currentUser;
            if (!user || !this.db) return;

            const userDoc = await this.db
                .collection('users')
                .doc(user.uid)
                .get();

            if (userDoc.exists) {
                const userData = userDoc.data();
                const address = userData.address?.trim();

                if (address) {
                    const location = await this.geocodingService.geocodeAddress(address);
                    this.addUserMarker(location, userData.name || 'Vous');
                    this.map.setCenter(location);
                }
            }

        } catch (error) {
            console.error('Erreur chargement position utilisateur:', error);
        }
    }

    /**
     * Charger les positions des amis
     */
    async loadFriendsLocations() {
        try {
            const user = this.auth?.currentUser;
            if (!user || !this.db) return;

            const userDoc = await this.db
                .collection('users')
                .doc(user.uid)
                .get();

            if (!userDoc.exists) return;

            const friends = userDoc.data().friends || [];
            
            if (friends.length === 0) return;

            // Récupérer les données des amis
            const friendsData = await Promise.all(
                friends.map(async friendId => {
                    try {
                        const friendDoc = await this.db
                            .collection('users')
                            .doc(friendId)
                            .get();

                        if (friendDoc.exists) {
                            return { id: friendId, ...friendDoc.data() };
                        }
                        return null;
                    } catch (error) {
                        console.error(`Erreur récupération ami ${friendId}:`, error);
                        return null;
                    }
                })
            );

            // Filtrer les amis valides avec adresse
            const validFriends = friendsData
                .filter(friend => friend && friend.address?.trim())
                .map(friend => ({
                    id: friend.id,
                    name: friend.name,
                    address: friend.address.trim()
                }));

            if (validFriends.length === 0) return;

            // Géocoder les adresses des amis
            const addresses = validFriends.map(friend => friend.address);
            const geocodingResults = await this.geocodingService.geocodeMultipleAddresses(addresses);

            // Ajouter les marqueurs des amis
            geocodingResults.forEach((result, index) => {
                if (!result.error) {
                    const friend = validFriends[index];
                    this.addFriendMarker(result, friend.name, friend.id);
                }
            });

        } catch (error) {
            console.error('Erreur chargement positions amis:', error);
        }
    }

    /**
     * Ajouter un marqueur pour l'utilisateur
     */
    addUserMarker(location, name) {
        if (this.userMarker) {
            this.userMarker.setMap(null);
        }

        this.userMarker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: name,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10,
                fillColor: '#4285F4',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2
            }
        });

        const infoWindow = new google.maps.InfoWindow({
            content: `<div><strong>${name}</strong><br>Votre position</div>`
        });

        this.userMarker.addListener('click', () => {
            infoWindow.open(this.map, this.userMarker);
        });
    }

    /**
     * Ajouter un marqueur pour un ami
     */
    addFriendMarker(location, name, friendId) {
        const marker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: name,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: '#34A853',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2
            }
        });

        const infoWindow = new google.maps.InfoWindow({
            content: `<div><strong>${name}</strong><br>Ami</div>`
        });

        marker.addListener('click', () => {
            infoWindow.open(this.map, marker);
        });

        this.friendMarkers.push({ marker, friendId, name });
    }

    /**
     * Basculer la visibilité des amis
     */
    toggleFriendsVisibility(visible) {
        this.friendMarkers.forEach(({ marker }) => {
            marker.setVisible(visible);
        });
    }

    /**
     * Rafraîchir toutes les positions
     */
    async refreshAllLocations() {
        try {
            // Nettoyer les marqueurs existants
            this.clearAllMarkers();

            // Recharger les positions
            await this.loadUserLocation();
            await this.loadFriendsLocations();

        } catch (error) {
            console.error('Erreur rafraîchissement positions:', error);
        }
    }

    /**
     * Nettoyer tous les marqueurs
     */
    clearAllMarkers() {
        if (this.userMarker) {
            this.userMarker.setMap(null);
            this.userMarker = null;
        }

        this.friendMarkers.forEach(({ marker }) => {
            marker.setMap(null);
        });
        this.friendMarkers = [];
    }
}

// Export global pour utilisation dans dashboard.html
window.SecureMapManager = SecureMapManager;
window.SecureGeocodingService = SecureGeocodingService;
