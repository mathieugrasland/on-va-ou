/**
 * Module de recherche de bars optimaux - On va où ?
 * Gère la sélection d'amis et la recherche de bars équidistants en temps
 */

export class BarFinder {
    constructor(auth, db, mapManager) {
        this.auth = auth;
        this.db = db;
        this.mapManager = mapManager;
        this.selectedFriends = new Set();
        this.currentUser = null;
        this.bars = [];
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Bouton de recherche de bars
        const findBarsBtn = document.getElementById('find-bars-btn');
        if (findBarsBtn) {
            findBarsBtn.addEventListener('click', () => this.findOptimalBars());
        }
    }

    setCurrentUser(user) {
        this.currentUser = user;
    }

    /**
     * Gère la sélection/déselection d'un ami
     */
    toggleFriendSelection(friendId, friendCard) {
        if (this.selectedFriends.has(friendId)) {
            this.selectedFriends.delete(friendId);
            friendCard.classList.remove('selected');
        } else {
            this.selectedFriends.add(friendId);
            friendCard.classList.add('selected');
        }
        
        this.updateSelectionUI();
    }

    /**
     * Met à jour l'interface de sélection
     */
    updateSelectionUI() {
        const selectedCount = this.selectedFriends.size;
        const selectedCountEl = document.getElementById('selected-count');
        const findBarsBtn = document.getElementById('find-bars-btn');
        const searchSection = document.getElementById('search-section');
        
        if (selectedCountEl) {
            selectedCountEl.textContent = selectedCount;
        }
        
        if (searchSection) {
            if (selectedCount > 0) {
                searchSection.classList.remove('hidden');
            } else {
                searchSection.classList.add('hidden');
            }
        }
        
        if (findBarsBtn) {
            findBarsBtn.disabled = selectedCount === 0;
        }
    }

    /**
     * Trouve les bars optimaux pour les amis sélectionnés
     */
    async findOptimalBars() {
        if (this.selectedFriends.size === 0) return;

        const statusEl = document.getElementById('search-status');
        const findBarsBtn = document.getElementById('find-bars-btn');
        
        try {
            // Mise à jour de l'UI
            findBarsBtn.disabled = true;
            findBarsBtn.textContent = '⏳ Recherche en cours...';
            statusEl.textContent = 'Récupération des positions...';
            
            // Récupérer les positions de tous les amis sélectionnés + utilisateur actuel
            const positions = await this.getFriendsPositions();
            
            if (positions.length < 1) {
                throw new Error('Aucune position valide trouvée. Vérifiez que vous et vos amis avez renseigné une adresse dans leur profil.');
            }
            
            if (positions.length < 2) {
                throw new Error(`Seulement ${positions.length} position(s) trouvée(s). Il faut au moins 2 personnes avec des adresses valides.`);
            }
            
            statusEl.textContent = 'Calcul du point optimal et recherche de bars (600m)...';
            
            // Appeler la Cloud Function pour trouver les bars
            const bars = await this.callFindBarsCloudFunction(positions);
            
            if (bars && bars.length > 0) {
                statusEl.textContent = `${bars.length} bar(s) bien noté(s) trouvé(s) !`;
                this.displayBars(bars);
                this.showBarsOnMap(bars);
            } else {
                throw new Error('Aucun bar bien noté trouvé dans un rayon de 600m');
            }
            
        } catch (error) {
            console.error('Erreur recherche bars:', error);
            statusEl.textContent = `Erreur: ${error.message}`;
            this.showMessage('Erreur lors de la recherche de bars', 'error');
        } finally {
            // Restaurer l'UI
            findBarsBtn.disabled = this.selectedFriends.size === 0;
            findBarsBtn.textContent = '🔍 Trouver des bars';
        }
    }

    /**
     * Récupère les positions des amis sélectionnés + utilisateur actuel
     */
    async getFriendsPositions() {
        const positions = [];
        
        try {
            // Import dynamique
            const { doc, getDoc } = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js');
            
            console.log('Récupération positions pour:', {
                userId: this.currentUser.uid,
                selectedFriends: Array.from(this.selectedFriends)
            });
            
            // Ajouter la position de l'utilisateur actuel
            const userDoc = await getDoc(doc(this.db, 'users', this.currentUser.uid));
            if (userDoc.exists()) {
                const userData = userDoc.data();
                console.log('Données utilisateur:', userData);
                
                // Chercher location ou coordinates (ancien format)
                const userLocation = userData.location || userData.coordinates;
                
                if (userLocation && userLocation.lat && userLocation.lng) {
                    positions.push({
                        id: this.currentUser.uid,
                        name: `${userData.firstName || 'Vous'}`,
                        location: userLocation,
                        transportMode: userData.transportMode || 'walking'
                    });
                    console.log('Position utilisateur ajoutée:', userLocation);
                } else {
                    console.warn('Utilisateur sans position valide:', userLocation);
                }
            } else {
                console.warn('Document utilisateur non trouvé');
            }
            
            // Ajouter les positions des amis sélectionnés
            for (const friendId of this.selectedFriends) {
                console.log('Récupération ami:', friendId);
                const friendDoc = await getDoc(doc(this.db, 'users', friendId));
                if (friendDoc.exists()) {
                    const friendData = friendDoc.data();
                    console.log('Données ami:', friendData);
                    
                    // Chercher location ou coordinates (ancien format)
                    const friendLocation = friendData.location || friendData.coordinates;
                    
                    if (friendLocation && friendLocation.lat && friendLocation.lng) {
                        positions.push({
                            id: friendId,
                            name: `${friendData.firstName || 'Ami'}`,
                            location: friendLocation,
                            transportMode: friendData.transportMode || 'walking'
                        });
                        console.log('Position ami ajoutée:', friendLocation);
                    } else {
                        console.warn('Ami sans position valide:', friendId, friendLocation);
                    }
                } else {
                    console.warn('Document ami non trouvé:', friendId);
                }
            }
            
            console.log('Positions finales récupérées:', positions);
            
        } catch (error) {
            console.error('Erreur récupération positions:', error);
            throw new Error('Impossible de récupérer les positions des amis');
        }
        
        return positions;
    }

    /**
     * Appelle la Cloud Function pour trouver les bars optimaux
     */
    async callFindBarsCloudFunction(positions) {
        console.log('Appel Cloud Function avec positions:', positions);
        
        const idToken = await this.currentUser.getIdToken();
        console.log('Token récupéré, longueur:', idToken.length);
        
        try {
            // Utiliser l'URL directe de la Cloud Function pour le moment
            const response = await fetch('https://us-central1-on-va-ou-c6d7f.cloudfunctions.net/find_optimal_bars', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    positions: positions,
                    max_bars: 5,
                    search_radius: 600 // 600m de rayon
                })
            });

            console.log('Réponse reçue:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erreur API (text):', errorText);
                
                // Essayer de parser en JSON si possible
                try {
                    const errorData = JSON.parse(errorText);
                    throw new Error(errorData.error || 'Erreur serveur');
                } catch {
                    throw new Error(`Erreur serveur: ${response.status} ${response.statusText}`);
                }
            }

            const data = await response.json();
            console.log('Données reçues:', data);
            return data.bars || [];
            
        } catch (error) {
            console.error('Erreur lors de l\'appel API:', error);
            throw error;
        }
    }

    /**
     * Affiche les bars dans la liste
     */
    displayBars(bars) {
        this.bars = bars;
        const barsResults = document.getElementById('bars-results');
        const barsList = document.getElementById('bars-list');
        
        if (!barsResults || !barsList) return;
        
        // Afficher la section des résultats
        barsResults.classList.remove('hidden');
        
        // Vider et remplir la liste
        barsList.innerHTML = '';
        
        bars.forEach((bar, index) => {
            const barCard = this.createBarCard(bar, index);
            barsList.appendChild(barCard);
        });
        
        // Scroll vers les résultats
        barsResults.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Crée une carte pour un bar
     */
    createBarCard(bar, index) {
        const card = document.createElement('div');
        card.className = 'bar-card';
        
        const avgTime = Math.round(bar.avg_travel_time);
        const rating = bar.rating ? bar.rating.toFixed(1) : 'N/A';
        
        card.innerHTML = `
            <div class="bar-name">${bar.name}</div>
            <div class="bar-address">${bar.address}</div>
            <div class="bar-info">
                <span class="bar-rating">⭐ ${rating}</span>
                <span class="bar-distance">⏱️ ~${avgTime} min</span>
            </div>
            <div class="bar-actions">
                <button class="bar-action-btn maps-btn" onclick="window.open('https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(bar.name + ' ' + bar.address)}', '_blank')">
                    📍 Voir sur Maps
                </button>
                <button class="bar-action-btn" onclick="barFinder.centerMapOnBar(${index})">
                    🗺️ Centrer carte
                </button>
            </div>
        `;
        
        return card;
    }

    /**
     * Affiche les bars sur la carte
     */
    showBarsOnMap(bars) {
        if (this.mapManager && this.mapManager.addBarMarkers) {
            this.mapManager.addBarMarkers(bars);
        }
    }

    /**
     * Centre la carte sur un bar spécifique
     */
    centerMapOnBar(barIndex) {
        if (this.bars[barIndex] && this.mapManager && this.mapManager.centerOnLocation) {
            const bar = this.bars[barIndex];
            this.mapManager.centerOnLocation(bar.location.lat, bar.location.lng);
        }
    }

    /**
     * Affiche un message à l'utilisateur
     */
    showMessage(text, type = 'info') {
        if (window.showMessage) {
            window.showMessage(text, type);
        }
    }

    /**
     * Réinitialise la sélection
     */
    clearSelection() {
        this.selectedFriends.clear();
        
        // Retirer la classe selected de toutes les cartes d'amis
        document.querySelectorAll('.friend-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Masquer la section de recherche
        const searchSection = document.getElementById('search-section');
        if (searchSection) {
            searchSection.classList.add('hidden');
        }
        
        // Masquer les résultats
        const barsResults = document.getElementById('bars-results');
        if (barsResults) {
            barsResults.classList.add('hidden');
        }
        
        this.updateSelectionUI();
    }
}

// Rendre la classe disponible globalement
window.BarFinder = BarFinder;
