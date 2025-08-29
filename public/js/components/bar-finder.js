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
     * Retourne l'icône correspondant au mode de transport
     */
    getTransportIcon(transportMode) {
        const icons = {
            'walking': '🚶',
            'car': '🚗',              // Valeur réelle stockée en DB
            'bicycle': '🚲',          // Valeur réelle stockée en DB  
            'public_transport': '🚌', // Valeur réelle stockée en DB
            // Anciens mappings pour compatibilité
            'driving': '🚗',
            'bicycling': '🚲',
            'transit': '🚌'
        };
        return icons[transportMode] || '🚶'; // Par défaut : piéton
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
    async findOptimalBars(retryCount = 0) {
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
            
            // Stocker les positions pour l'affichage des détails
            this.lastUsedPositions = positions;
            
            if (positions.length < 1) {
                throw new Error('Aucune position valide trouvée. Vérifiez que vous et vos amis avez renseigné une adresse dans leur profil.');
            }
            
            if (positions.length < 2) {
                throw new Error(`Seulement ${positions.length} position(s) trouvée(s). Il faut au moins 2 personnes avec des adresses valides.`);
            }
            
            statusEl.textContent = `Recherche de bars candidats et calcul des temps de trajet (zone adaptative)...`;
            
            // Appeler la Cloud Function pour trouver les bars
            const bars = await this.callFindBarsCloudFunction(positions);
            
            if (bars && bars.length > 0) {
                statusEl.textContent = `${bars.length} bar(s) optimal(s) trouvé(s) selon les temps de trajet !`;
                this.displayBars(bars);
                await this.showBarsOnMap(bars);
            } else {
                throw new Error('Aucun bar accessible trouvé avec des temps de trajet équilibrés');
            }
            
        } catch (error) {
            console.error('Erreur recherche bars:', error);
            console.log('Détails erreur - status:', error.status, 'message:', error.message, 'rawResponse:', error.rawResponse);
            
            // Vérifier si c'est une erreur 404 avec "Aucun bar trouvé dans la zone"
            const isNoBarFoundError = (
                error.status === 404 || 
                error.message.includes('Aucun bar trouvé dans la zone') ||
                (error.rawResponse && error.rawResponse.includes('Aucun bar trouvé dans la zone'))
            );
            
            console.log('isNoBarFoundError:', isNoBarFoundError);
            
            if (isNoBarFoundError) {
                await this.handleNoBarFoundError(retryCount);
            } else {
                statusEl.textContent = `Erreur: ${error.message}`;
                this.showMessage('Erreur lors de la recherche de bars', 'error');
            }
        } finally {
            // Restaurer l'UI
            findBarsBtn.disabled = this.selectedFriends.size === 0;
            findBarsBtn.textContent = '🔍 Trouver des bars';
        }
    }

    /**
     * Gère le cas où aucun bar n'est trouvé et propose de réessayer avec une zone élargie
     */
    async handleNoBarFoundError(retryCount) {
        const statusEl = document.getElementById('search-status');
        
        statusEl.textContent = `Aucun bar trouvé dans la zone adaptative`;
        
        // Proposer de réessayer seulement si on n'a pas déjà essayé plusieurs fois
        if (retryCount < 2) { // Limite à 2 tentatives supplémentaires
            const attemptNumber = retryCount + 1;
            
            const userWantsRetry = confirm(
                `Aucun bar trouvé avec le calcul automatique de la zone.\n\n` +
                `Voulez-vous réessayer avec une zone élargie (tentative ${attemptNumber + 1}/3) ?`
            );
            
            if (userWantsRetry) {
                statusEl.textContent = `Nouvelle tentative avec zone élargie (${attemptNumber + 1}/3)...`;
                await this.findOptimalBars(retryCount + 1);
                return;
            }
        }
        
        // Si l'utilisateur refuse ou si on a atteint la limite
        this.showMessage(
            `Aucun bar trouvé après ${retryCount + 1} tentative(s). Essayez avec d'autres amis ou une configuration différente.`, 
            'info'
        );
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
        console.log('Utilisation du rayon adaptatif automatique');
        
        const idToken = await this.currentUser.getIdToken();
        console.log('Token récupéré, longueur:', idToken.length);
        
        try {
            // Utiliser le routage Firebase au lieu de l'URL directe avec timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
            
            const response = await fetch('/api/find-bars', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    positions: positions,
                    max_bars: 25  // Demander le maximum possible avec la limite API
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            console.log('Réponse reçue:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erreur API (text):', errorText);
                
                // Essayer de parser en JSON si possible
                try {
                    const errorData = JSON.parse(errorText);
                    const errorMessage = errorData.error || 'Erreur serveur';
                    
                    // Créer une erreur avec des informations complètes pour la détection
                    const error = new Error(errorMessage);
                    error.status = response.status;
                    error.rawResponse = errorText;
                    throw error;
                } catch (parseError) {
                    const error = new Error(`Erreur serveur: ${response.status} ${response.statusText}`);
                    error.status = response.status;
                    error.rawResponse = errorText;
                    throw error;
                }
            }

            const data = await response.json();
            console.log('Données reçues:', data);
            return data.bars || [];
            
        } catch (error) {
            console.error('Erreur lors de l\'appel API:', error);
            
            // Gestion spécifique du timeout
            if (error.name === 'AbortError') {
                const timeoutError = new Error('La recherche a pris trop de temps. Essayez avec moins d\'amis ou une zone plus petite.');
                timeoutError.status = 408;
                throw timeoutError;
            }
            
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
        
        // Identifier et réorganiser les bars spéciaux
        const specialBars = [];
        const regularBars = [];
        
        bars.forEach((bar, originalIndex) => {
            bar.originalIndex = originalIndex; // Conserver l'index original pour les callbacks
            
            if (bar.marker_type === 'fastest_and_balanced') {
                specialBars.unshift(bar); // Le bar combiné (rapide ET équitable) en tout premier
            } else if (bar.marker_type === 'most_balanced') {
                specialBars.push(bar); // Le plus équitable après le combiné s'il existe
            } else if (bar.marker_type === 'fastest') {
                specialBars.push(bar); // Le plus rapide après les autres spéciaux
            } else {
                regularBars.push(bar);
            }
        });
        
        // Réorganiser : bars spéciaux en premier, puis le reste
        const orderedBars = [...specialBars, ...regularBars];
        
        // Créer une correspondance entre place_id et position d'affichage
        this.displayIndexMap = new Map();
        
        orderedBars.forEach((bar, displayIndex) => {
            this.displayIndexMap.set(bar.place_id, displayIndex);
            const barCard = this.createBarCard(bar, bar.originalIndex, displayIndex);
            barsList.appendChild(barCard);
        });
        
        // Scroll vers les résultats
        barsResults.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Affiche/cache les détails des temps de trajet pour un bar
     */
    toggleBarDetails(barIndex) {
        const detailsEl = document.getElementById(`bar-details-${barIndex}`);
        const timesEl = document.getElementById(`travel-times-${barIndex}`);
        const button = document.querySelector(`button[onclick="barFinder.toggleBarDetails(${barIndex})"]`);
        
        if (!detailsEl || !timesEl) return;
        
        if (detailsEl.classList.contains('hidden')) {
            // Afficher les détails
            this.populateBarDetails(barIndex, timesEl);
            detailsEl.classList.remove('hidden');
            button.textContent = '📊 Masquer détails';
        } else {
            // Masquer les détails
            detailsEl.classList.add('hidden');
            button.textContent = '📊 Détails temps';
        }
    }

    /**
     * Remplit les détails des temps de trajet
     */
    populateBarDetails(barIndex, container) {
        const bar = this.bars[barIndex];
        if (!bar || !bar.travel_times || !this.lastUsedPositions) return;
        
        container.innerHTML = '';
        
        // Créer une liste des temps par personne
        bar.travel_times.forEach((time, index) => {
            if (index < this.lastUsedPositions.length) {
                const position = this.lastUsedPositions[index];
                const timeEl = document.createElement('div');
                timeEl.className = 'travel-time-item';
                
                // Utiliser "Moi" pour l'utilisateur actuel
                const displayName = position.id === this.currentUser.uid ? 'Moi' : position.name;
                
                // Obtenir l'icône du mode de transport
                const transportIcon = this.getTransportIcon(position.transportMode);
                
                timeEl.innerHTML = `
                    <span class="person-name">${transportIcon} ${displayName}</span>
                    <span class="travel-time">⏱️ ${Math.round(time)} min</span>
                `;
                
                container.appendChild(timeEl);
            }
        });
    }

    /**
     * Crée une carte pour un bar
     */
    createBarCard(bar, originalIndex, displayIndex = null) {
        const card = document.createElement('div');
        card.className = 'bar-card';
        
        const avgTime = Math.round(bar.avg_travel_time);
        const rating = bar.rating ? bar.rating.toFixed(1) : 'N/A';
        const timeSpread = Math.round(bar.time_spread || 0);
        
        // Créer un indicateur de déséquilibre
        let balanceIndicator = '';
        const balanceScore = bar.time_balance_score || 0;
        if (balanceScore <= 0.2) {
            balanceIndicator = '<span class="balance-good">⚖️ Équilibré</span>';
        } else if (balanceScore <= 0.5) {
            balanceIndicator = '<span class="balance-ok">⚖️ Correct</span>';
        } else {
            balanceIndicator = '<span class="balance-poor">⚖️ Déséquilibré</span>';
        }
        
        // Déterminer l'affichage du badge spécial (sans mentions top choice)
        let specialBadge = '';
        
        // Gérer tous les types de bars spéciaux avec seulement les badges
        if (bar.marker_emoji && bar.marker_type) {
            let badgeClass = '';
            let badgeText = '';
            
            switch (bar.marker_type) {
                case 'fastest':
                    badgeClass = 'special-badge fastest-badge';
                    badgeText = `${bar.marker_emoji} Plus rapide`;
                    break;
                case 'most_balanced':
                    badgeClass = 'special-badge balanced-badge';
                    badgeText = `${bar.marker_emoji} Plus équitable`;
                    break;
                case 'fastest_and_balanced':
                    badgeClass = 'special-badge combined-badge';
                    badgeText = `${bar.marker_emoji} Plus équitable ET plus rapide`;
                    break;
            }
            
            if (badgeClass) {
                specialBadge = `<div class="${badgeClass}">${badgeText}</div>`;
            }
        }
        
        card.innerHTML = `
            ${specialBadge}
            <div class="bar-name">${bar.name}</div>
            <div class="bar-address">${bar.address}</div>
            <div class="bar-info">
                <span class="bar-rating">⭐ ${rating}</span>
                <span class="bar-distance">⏱️ ~${avgTime} min (moyenne)</span>
            </div>
            <div class="bar-time-info">
                <span class="time-spread">📊 Écart: ${timeSpread} min</span>
                ${balanceIndicator}
            </div>
            <div class="bar-details hidden" id="bar-details-${originalIndex}">
                <div class="travel-times">
                    <h4>Temps de trajet détaillés :</h4>
                    <div id="travel-times-${originalIndex}"></div>
                </div>
            </div>
            <div class="bar-actions">
                <button class="bar-action-btn details-btn" onclick="barFinder.toggleBarDetails(${originalIndex})">
                    📊 Détails temps
                </button>
                <button class="bar-action-btn maps-btn" onclick="window.open('https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(bar.name + ' ' + bar.address)}', '_blank')">
                    📍 Voir sur Maps
                </button>
                <button class="bar-action-btn" onclick="barFinder.centerMapOnBar(${originalIndex})">
                    🗺️ Centrer carte
                </button>
            </div>
        `;
        
        return card;
    }

    /**
     * Affiche les bars sur la carte
     */
    async showBarsOnMap(bars) {
        if (this.mapManager && this.mapManager.addBarMarkers) {
            // Charger seulement les amis sélectionnés sur la carte
            if (this.mapManager.loadSelectedFriendsLocations) {
                const selectedFriendIds = Array.from(this.selectedFriends);
                await this.mapManager.loadSelectedFriendsLocations(selectedFriendIds);
            }
            
            // Puis afficher les bars
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
     * Affiche les détails d'un bar sélectionné depuis la carte
     */
    showBarDetailsInMap(placeId) {
        // Trouver le bar dans la liste
        const barIndex = this.bars.findIndex(bar => bar.place_id === placeId);
        if (barIndex === -1) return;
        
        // Fermer toutes les InfoWindows
        if (this.mapManager && this.mapManager.closeAllBarInfoWindows) {
            this.mapManager.closeAllBarInfoWindows();
        }
        
        // Faire défiler vers la liste et afficher les détails
        const barsResults = document.getElementById('bars-results');
        if (barsResults) {
            barsResults.scrollIntoView({ behavior: 'smooth' });
            
            // Attendre que le scroll soit terminé puis ouvrir les détails
            setTimeout(() => {
                this.toggleBarDetails(barIndex);
                
                // Trouver la position d'affichage du bar
                const displayIndex = this.displayIndexMap ? this.displayIndexMap.get(placeId) : barIndex;
                
                // Highlight temporairement la carte du bar
                const barCard = document.querySelector(`.bar-card:nth-child(${displayIndex + 1})`);
                if (barCard) {
                    barCard.style.border = '2px solid #ff9800';
                    barCard.style.boxShadow = '0 4px 12px rgba(255, 152, 0, 0.3)';
                    barCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    // Retirer le highlight après 3 secondes
                    setTimeout(() => {
                        barCard.style.border = '';
                        barCard.style.boxShadow = '';
                    }, 3000);
                }
            }, 800);
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
