// Import des fonctions Firestore v9+
import { doc, getDoc } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js';
// Import de la configuration des couleurs
import { FRIEND_COLORS, getFriendColorById } from './color-config.js';

class SecureGeocodingService {
    constructor(auth = null) {
        this.baseUrl = 'https://on-va-ou-470217.web.app';  // URL de base de l'application
        this.auth = auth;
    }

    async geocodeAddress(address) {
        try {
            const user = this.auth?.currentUser;
            if (!user) {
                throw new Error('Utilisateur non authentifié');
            }

            const token = await user.getIdToken();
            
            const response = await fetch(`${this.baseUrl}/api/geocode`, {
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

    // Nouvelle méthode pour géocoder plusieurs adresses en une seule fois
    async geocodeMultipleAddresses(addressesData) {
        try {
            const user = this.auth?.currentUser;
            if (!user) {
                throw new Error('Utilisateur non authentifié');
            }

            const token = await user.getIdToken();
            
            const response = await fetch(`${this.baseUrl}/api/geocode-batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ addresses: addressesData })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erreur de géocodage batch');
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur géocodage batch');
            }

            return data.results; // Retourne un objet avec les résultats indexés par ID

        } catch (error) {
            console.error('Erreur géocodage batch:', error);
            throw error;
        }
    }

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

export class SecureMapManager {
    constructor(mapElementId, auth = null, db = null) {
        this.mapElementId = mapElementId;
        this.map = null;
        this.userMarker = null;
        this.friendMarkers = [];
        this.geocodingService = new SecureGeocodingService(auth);
        this.isInitialized = false;
        this.auth = auth;
        this.db = db;
        this.friendColors = FRIEND_COLORS;
    }

    async initializeMap() {
        try {
            const mapElement = document.getElementById(this.mapElementId);
            if (!mapElement) {
                throw new Error('Élément carte non trouvé');
            }

            console.log('Initialisation de la carte...');
            // Position par défaut (Paris) avec un zoom légèrement dézooomé
            const defaultPosition = { lat: 48.8566, lng: 2.3522 };

            this.map = new google.maps.Map(mapElement, {
                zoom: 11.5, // Zoom intermédiaire entre 11 et 12
                center: defaultPosition,
                mapTypeId: 'roadmap',
                mapTypeControl: false,
                streetViewControl: false,
                fullscreenControl: true,
                zoomControl: true,
                scrollwheel: true,
                gestureHandling: 'auto'
            });

            this.isInitialized = true;
            console.log('Carte initialisée avec succès');

        } catch (error) {
            console.error('Erreur initialisation carte:', error);
            throw error;
        }
    }

    async loadFriendsLocations() {
        try {
            if (!this.isInitialized || !this.map) {
                throw new Error('Carte non initialisée');
            }

            const user = this.auth?.currentUser;
            if (!user || !this.db) return;

            const userDocRef = doc(this.db, 'users', user.uid);
            const userDoc = await getDoc(userDocRef);

            if (!userDoc.exists()) return;

            const userData = userDoc.data();
            const friends = userData.friends || [];
            
            // Préparer toutes les adresses à géocoder en une fois
            const addressesToGeocode = [];
            
            // Ajouter l'adresse de l'utilisateur
            if (userData.address) {
                addressesToGeocode.push({
                    id: 'user',
                    address: userData.address,
                    name: userData.firstName || 'Vous',
                    type: 'user'
                });
            }

            // Charger les données des amis et préparer leurs adresses
            for (const friendId of friends) {
                try {
                    const friendDoc = await getDoc(doc(this.db, 'users', friendId));
                    if (!friendDoc.exists()) continue;

                    const friendData = friendDoc.data();
                    if (friendData.address) {
                        addressesToGeocode.push({
                            id: friendId,
                            address: friendData.address,
                            name: friendData.firstName || 'Ami',
                            type: 'friend'
                        });
                    }
                } catch (error) {
                    console.error(`Erreur chargement ami ${friendId}:`, error);
                }
            }

            // Si aucune adresse à géocoder, on s'arrête
            if (addressesToGeocode.length === 0) return;

            // Un seul appel pour toutes les adresses !
            console.log(`Géocodage de ${addressesToGeocode.length} adresses en une seule fois...`);
            const geoResults = await this.geocodingService.geocodeMultipleAddresses(addressesToGeocode);

            // Traiter les résultats
            for (const addressData of addressesToGeocode) {
                const result = geoResults[addressData.id];
                if (result && result.success) {
                    const location = {
                        lat: result.location.lat,
                        lng: result.location.lng
                    };

                    if (addressData.type === 'user') {
                        this.addUserMarker(location, addressData.name);
                    } else {
                        this.addFriendMarker(location, addressData.name, addressData.id);
                    }
                } else {
                    console.warn(`Géocodage échoué pour ${addressData.name}:`, result?.error);
                }
            }

        } catch (error) {
            console.error('Erreur chargement positions:', error);
            throw error;
        }
    }

    addUserMarker(location, name) {
        if (this.userMarker) {
            this.userMarker.setMap(null);
        }

        this.userMarker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: `Moi`,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: '#5d4037', // Couleur marron fixe pour l'utilisateur
                fillOpacity: 0.9,
                strokeColor: '#ffffff',
                strokeWeight: 2,
                strokeOpacity: 1,
                labelOrigin: new google.maps.Point(0, -2) // Décale le label au-dessus
            },
            label: {
                text: name,
                color: '#5d4037',
                fontSize: '11px',
                fontWeight: '500'
            },
            zIndex: 1000 // S'assurer que le marqueur utilisateur est au-dessus
        });
    }

    addFriendMarker(location, name, friendId) {
        const colorIndex = this.friendMarkers.length % this.friendColors.length;
        const color = this.friendColors[colorIndex];
        
        const marker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: `${name}`,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 6,
                fillColor: color,
                fillOpacity: 0.8,
                strokeColor: '#ffffff',
                strokeWeight: 2,
                strokeOpacity: 1,
                labelOrigin: new google.maps.Point(0, -2) // Décale le label au-dessus
            },
            label: {
                text: name,
                color: color,
                fontSize: '11px',
                fontWeight: '500'
            },
            zIndex: 100
        });

        this.friendMarkers.push({ marker, friendId, name, color });
    }

    // Centrer la carte sur un ami spécifique
    centerOnFriend(friendId) {
        const friendMarker = this.friendMarkers.find(fm => fm.friendId === friendId);
        if (friendMarker && this.map) {
            this.map.panTo(friendMarker.marker.getPosition()); // Zoom plus proche pour mieux voir
        }
    }

    clearMarkers() {
        if (this.userMarker) {
            this.userMarker.setMap(null);
            this.userMarker = null;
        }

        this.friendMarkers.forEach(({ marker }) => marker.setMap(null));
        this.friendMarkers = [];
    }
}
