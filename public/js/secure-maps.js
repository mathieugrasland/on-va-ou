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
            const userLocation = userData.location || userData.coordinates;
            if (userLocation && userLocation.lat && userLocation.lng) {
                const location = {
                    lat: userLocation.lat,
                    lng: userLocation.lng
                };
                this.addUserMarker(location, userData.firstName || 'Vous');
                console.log('Position utilisateur chargée depuis le cache:', location);
            } else if (userData.address) {
                console.log('Coordonnées utilisateur manquantes, géocodage requis pour:', userData.address);
                // Fallback : géocoder si pas de coordonnées (utilisateurs anciens)
                try {
                    const location = await this.geocodingService.geocodeAddress(userData.address);
                    this.addUserMarker(location, userData.firstName || 'Vous');
                    
                    // Sauvegarder les coordonnées pour la prochaine fois (nouveau format + ancien)
                    await updateDoc(userDocRef, {
                        location: {
                            lat: location.lat,
                            lng: location.lng
                        },
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
                    
                    // Priorité 1: Utiliser les coordonnées stockées (nouveau ou ancien format)
                    const friendLocation = friendData.location || friendData.coordinates;
                    if (friendLocation && friendLocation.lat && friendLocation.lng) {
                        const location = {
                            lat: friendLocation.lat,
                            lng: friendLocation.lng
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
                        
                        // Sauvegarder les coordonnées pour la prochaine fois (nouveau format + ancien)
                        await updateDoc(friendInfo.docRef, {
                            location: {
                                lat: location.lat,
                                lng: location.lng
                            },
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

    /**
     * Charge seulement les amis sélectionnés pour la recherche de bars
     */
    async loadSelectedFriendsLocations(selectedFriendIds) {
        try {
            if (!this.isInitialized || !this.map) {
                throw new Error('Carte non initialisée');
            }

            // Effacer les marqueurs d'amis existants
            this.clearFriendMarkers();

            const user = this.auth?.currentUser;
            if (!user || !this.db) return;

            console.log(`Chargement des positions pour ${selectedFriendIds.length} amis sélectionnés`);

            // Charger les positions des amis sélectionnés uniquement
            for (const friendId of selectedFriendIds) {
                try {
                    const friendDoc = await getDoc(doc(this.db, 'users', friendId));
                    if (!friendDoc.exists()) continue;

                    const friendData = friendDoc.data();
                    
                    // Utiliser les coordonnées stockées
                    const friendLocation = friendData.location || friendData.coordinates;
                    if (friendLocation && friendLocation.lat && friendLocation.lng) {
                        const location = {
                            lat: friendLocation.lat,
                            lng: friendLocation.lng
                        };
                        this.addFriendMarker(location, friendData.firstName || 'Ami', friendId);
                    } else if (friendData.address) {
                        // Géocoder si nécessaire
                        try {
                            const location = await this.geocodingService.geocodeAddress(friendData.address);
                            this.addFriendMarker(location, friendData.firstName || 'Ami', friendId);
                        } catch (error) {
                            console.error(`Erreur géocodage ami ${friendId}:`, error);
                        }
                    }
                } catch (error) {
                    console.error(`Erreur chargement ami ${friendId}:`, error);
                }
            }

        } catch (error) {
            console.error('Erreur chargement positions amis sélectionnés:', error);
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

    /**
     * Efface seulement les marqueurs d'amis (pas l'utilisateur ou les bars)
     */
    clearFriendMarkers() {
        if (this.friendMarkers) {
            this.friendMarkers.forEach(({ marker }) => {
                if (marker) marker.setMap(null);
            });
            this.friendMarkers = [];
        }
    }

    /**
     * Ajoute des marqueurs pour les bars sur la carte
     */
    addBarMarkers(bars) {
        if (!this.map || !bars) return;

        // Supprimer les anciens marqueurs de bars s'il y en a
        this.clearBarMarkers();

        // Initialiser le tableau des marqueurs de bars
        if (!this.barMarkers) {
            this.barMarkers = [];
        }

        bars.forEach((bar, index) => {
            const marker = new google.maps.Marker({
                position: {
                    lat: bar.location.lat,
                    lng: bar.location.lng
                },
                map: this.map,
                title: bar.name,
                icon: {
                    url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
                        <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                            <path d="M10 2 L18 16 L2 16 Z" fill="#d4a574" stroke="#fff" stroke-width="2"/>
                        </svg>
                    `),
                    scaledSize: new google.maps.Size(20, 20),
                    anchor: new google.maps.Point(10, 16)
                },
                zIndex: 1000 + index
            });

            // Info window pour afficher les détails du bar
            const infoWindow = new google.maps.InfoWindow({
                content: this.createBarInfoWindowContent(bar)
            });

            marker.addListener('click', () => {
                // Fermer toutes les autres info windows
                this.closeAllBarInfoWindows();
                infoWindow.open(this.map, marker);
            });

            this.barMarkers.push({
                marker: marker,
                infoWindow: infoWindow,
                bar: bar
            });
        });

        // Ajuster la vue pour inclure tous les marqueurs
        this.fitMapToIncludeAllMarkers();
    }

    /**
     * Crée le contenu HTML pour l'info window d'un bar
     */
    createBarInfoWindowContent(bar) {
        const rating = bar.rating ? bar.rating.toFixed(1) : 'N/A';
        const avgTime = Math.round(bar.avg_travel_time);
        
        return `
            <div style="max-width: 250px; font-family: Arial, sans-serif;">
                <h3 style="margin: 0 0 10px 0; color: #5d4037; font-size: 16px;">${bar.name}</h3>
                <p style="margin: 0 0 8px 0; color: #666; font-size: 13px;">${bar.address}</p>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #ff9800; font-size: 13px;">⭐ ${rating}</span>
                    <span style="color: #4caf50; font-size: 13px; font-weight: bold;">⏱️ ~${avgTime} min</span>
                </div>
                <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(bar.name + ' ' + bar.address)}" 
                   target="_blank" 
                   style="display: inline-block; background: #4285f4; color: white; padding: 6px 12px; 
                          text-decoration: none; border-radius: 4px; font-size: 12px;">
                    📍 Voir sur Maps
                </a>
            </div>
        `;
    }

    /**
     * Ferme toutes les info windows des bars
     */
    closeAllBarInfoWindows() {
        if (this.barMarkers) {
            this.barMarkers.forEach(({ infoWindow }) => {
                infoWindow.close();
            });
        }
    }

    /**
     * Supprime tous les marqueurs de bars
     */
    clearBarMarkers() {
        if (this.barMarkers) {
            this.barMarkers.forEach(({ marker, infoWindow }) => {
                infoWindow.close();
                marker.setMap(null);
            });
            this.barMarkers = [];
        }
    }

    /**
     * Ajuste la vue de la carte pour inclure tous les marqueurs
     */
    fitMapToIncludeAllMarkers() {
        if (!this.map) return;

        const bounds = new google.maps.LatLngBounds();
        let hasMarkers = false;

        // Inclure les marqueurs d'amis
        this.friendMarkers.forEach(({ marker }) => {
            bounds.extend(marker.getPosition());
            hasMarkers = true;
        });

        // Inclure le marqueur utilisateur
        if (this.userMarker) {
            bounds.extend(this.userMarker.getPosition());
            hasMarkers = true;
        }

        // Inclure les marqueurs de bars
        if (this.barMarkers) {
            this.barMarkers.forEach(({ marker }) => {
                bounds.extend(marker.getPosition());
                hasMarkers = true;
            });
        }

        if (hasMarkers) {
            this.map.fitBounds(bounds);
            
            // S'assurer que le zoom n'est pas trop élevé
            google.maps.event.addListenerOnce(this.map, 'bounds_changed', () => {
                if (this.map.getZoom() > 15) {
                    this.map.setZoom(15);
                }
            });
        }
    }

    /**
     * Centre la carte sur une position spécifique
     */
    centerOnLocation(lat, lng, zoom = 14) {
        if (this.map) {
            this.map.setCenter({ lat, lng });
            this.map.setZoom(zoom);
        }
    }
}
