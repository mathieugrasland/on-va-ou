// Import des fonctions Firestore v9+
import { doc, getDoc, updateDoc } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js';
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
                zoom: 12, // Zoom intermédiaire entre 11 et 12
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
            
            // Charger notre propre position depuis les coordonnées stockées
            if (userData.coordinates && userData.coordinates.lat && userData.coordinates.lng) {
                const location = {
                    lat: userData.coordinates.lat,
                    lng: userData.coordinates.lng
                };
                this.addUserMarker(location, userData.firstName || 'Vous');
                console.log('Position utilisateur chargée depuis le cache:', location);
            } else if (userData.address) {
                console.log('Coordonnées utilisateur manquantes, géocodage requis pour:', userData.address);
                // Fallback : géocoder si pas de coordonnées (utilisateurs anciens)
                try {
                    const location = await this.geocodingService.geocodeAddress(userData.address);
                    this.addUserMarker(location, userData.firstName || 'Vous');
                    
                    // Sauvegarder les coordonnées pour la prochaine fois
                    await updateDoc(userDocRef, {
                        coordinates: {
                            lat: location.lat,
                            lng: location.lng,
                            formatted_address: location.formatted_address,
                            geocoded_at: new Date().toISOString()
                        }
                    });
                    console.log('Coordonnées utilisateur sauvegardées pour cache futur');
                } catch (error) {
                    console.error('Erreur géocodage utilisateur:', error);
                }
            }

            if (friends.length === 0) return;

            // Charger les positions des amis depuis leurs coordonnées stockées
            const friendsNeedingGeocode = [];
            let loadedFromCache = 0;

            for (const friendId of friends) {
                try {
                    const friendDoc = await getDoc(doc(this.db, 'users', friendId));
                    if (!friendDoc.exists()) continue;

                    const friendData = friendDoc.data();
                    
                    // Priorité 1: Utiliser les coordonnées stockées
                    if (friendData.coordinates && friendData.coordinates.lat && friendData.coordinates.lng) {
                        const location = {
                            lat: friendData.coordinates.lat,
                            lng: friendData.coordinates.lng
                        };
                        this.addFriendMarker(location, friendData.firstName || 'Ami', friendId);
                        loadedFromCache++;
                    } else if (friendData.address) {
                        // Priorité 2: Marquer pour géocodage si pas de coordonnées
                        friendsNeedingGeocode.push({
                            id: friendId,
                            address: friendData.address,
                            name: friendData.firstName || 'Ami',
                            docRef: doc(this.db, 'users', friendId)
                        });
                    }
                } catch (error) {
                    console.error(`Erreur chargement ami ${friendId}:`, error);
                }
            }

            console.log(`${loadedFromCache} amis chargés depuis le cache, ${friendsNeedingGeocode.length} nécessitent un géocodage`);

            // Géocoder seulement les amis sans coordonnées (fallback pour anciens utilisateurs)
            if (friendsNeedingGeocode.length > 0) {
                console.log('Géocodage de sauvegarde pour amis sans coordonnées...');
                
                for (const friendInfo of friendsNeedingGeocode) {
                    try {
                        const location = await this.geocodingService.geocodeAddress(friendInfo.address);
                        this.addFriendMarker(location, friendInfo.name, friendInfo.id);
                        
                        // Sauvegarder les coordonnées pour la prochaine fois
                        await updateDoc(friendInfo.docRef, {
                            coordinates: {
                                lat: location.lat,
                                lng: location.lng,
                                formatted_address: location.formatted_address,
                                geocoded_at: new Date().toISOString()
                            }
                        });
                        console.log(`Coordonnées sauvegardées pour ${friendInfo.name}`);
                    } catch (error) {
                        console.error(`Erreur géocodage ami ${friendInfo.name}:`, error);
                    }
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
                text: 'Moi',
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
