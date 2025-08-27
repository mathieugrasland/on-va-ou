/**
 * @fileoverview Composant de tableau de bord principal
 * @author On va où ? Team
 * @version 1.0.0
 */

import { AuthService } from '../services/auth.service.js';
import { UserService } from '../services/user.service.js';
import { LocationService } from '../services/location.service.js';
import { DOMUtils, Router } from '../utils/helpers.js';
import { Logger } from '../utils/logger.js';

/**
 * Composant de gestion du tableau de bord
 */
export class Dashboard {
    
    constructor() {
        this.currentUser = null;
        this.friends = [];
        this.selectedFriends = [];
        this.isLoading = false;
        this.init();
    }
    
    /**
     * Initialiser le composant
     */
    async init() {
        await DOMUtils.ready();
        
        // Vérifier l'authentification
        this.currentUser = await AuthService.getCurrentUser();
        
        if (!this.currentUser) {
            Router.navigate('login.html');
            return;
        }
        
        this.bindEvents();
        await this.loadDashboard();
        Logger.info('Dashboard: Composant initialisé');
    }
    
    /**
     * Lier les événements
     */
    bindEvents() {
        // Bouton de déconnexion
        const logoutBtn = DOMUtils.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', this.handleLogout.bind(this));
        }
        
        // Formulaire d'ajout d'ami
        const addFriendForm = DOMUtils.getElementById('add-friend-form');
        if (addFriendForm) {
            addFriendForm.addEventListener('submit', this.handleAddFriend.bind(this));
        }
        
        // Bouton de recherche de bar
        const findBarBtn = DOMUtils.getElementById('find-bar-btn');
        if (findBarBtn) {
            findBarBtn.addEventListener('click', this.handleFindBar.bind(this));
        }
    }
    
    /**
     * Charger le tableau de bord
     */
    async loadDashboard() {
        this.setLoading(true);
        
        try {
            // Charger les informations utilisateur
            const userProfile = await UserService.getUserProfile(this.currentUser.uid);
            this.updateUserInfo(userProfile);
            
            // Charger la liste des amis
            this.friends = await UserService.getFriends(this.currentUser.uid);
            this.renderFriendsList();
            
        } catch (error) {
            this.showError('Erreur lors du chargement du tableau de bord');
            Logger.error('Dashboard: Erreur chargement', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Gérer la déconnexion
     */
    async handleLogout() {
        try {
            await AuthService.logout();
            Router.navigate('index.html');
        } catch (error) {
            this.showError('Erreur lors de la déconnexion');
            Logger.error('Dashboard: Erreur déconnexion', error);
        }
    }
    
    /**
     * Gérer l'ajout d'ami
     * @param {Event} event - Événement de soumission
     */
    async handleAddFriend(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const friendEmail = formData.get('friendEmail')?.trim();
        
        if (!friendEmail) return;
        
        try {
            const result = await UserService.addFriend(this.currentUser.uid, friendEmail);
            
            if (result.success) {
                this.showSuccess('Ami ajouté avec succès !');
                await this.loadDashboard(); // Recharger la liste
                event.target.reset(); // Réinitialiser le formulaire
            }
            
        } catch (error) {
            this.showError(error.message);
            Logger.error('Dashboard: Erreur ajout ami', error);
        }
    }
    
    /**
     * Gérer la recherche de bar
     */
    async handleFindBar() {
        const selectedFriends = this.getSelectedFriends();
        
        if (selectedFriends.length === 0) {
            this.showError('Veuillez sélectionner au moins un ami');
            return;
        }
        
        this.setLoading(true);
        
        try {
            // Obtenir les positions des amis sélectionnés
            const locations = await this.getFriendLocations(selectedFriends);
            
            if (locations.length === 0) {
                this.showError('Aucune localisation disponible pour les amis sélectionnés');
                return;
            }
            
            // Calculer le point central
            const centralPoint = LocationService.calculateCentralPoint(locations);
            
            // Rechercher les bars à proximité
            const bars = await LocationService.findNearbyBars(centralPoint);
            
            this.renderBarsResults(bars, centralPoint);
            
        } catch (error) {
            this.showError('Erreur lors de la recherche de bars');
            Logger.error('Dashboard: Erreur recherche bars', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Mettre à jour les informations utilisateur
     * @param {Object} userProfile - Profil utilisateur
     */
    updateUserInfo(userProfile) {
        const userNameElement = DOMUtils.getElementById('user-name');
        if (userNameElement && userProfile) {
            userNameElement.textContent = `${userProfile.firstName} ${userProfile.lastName}`;
        }
    }
    
    /**
     * Rendre la liste des amis
     */
    renderFriendsList() {
        const friendsList = DOMUtils.getElementById('friends-list');
        if (!friendsList) return;
        
        if (this.friends.length === 0) {
            friendsList.innerHTML = '<p class="no-friends">Aucun ami ajouté pour le moment</p>';
            return;
        }
        
        friendsList.innerHTML = this.friends.map(friend => `
            <div class="friend-item">
                <label>
                    <input type="checkbox" value="${friend.id}" class="friend-checkbox">
                    <span class="friend-name">${friend.firstName} ${friend.lastName}</span>
                    <span class="friend-email">${friend.email}</span>
                </label>
            </div>
        `).join('');
    }
    
    /**
     * Obtenir les amis sélectionnés
     * @returns {Array} Liste des amis sélectionnés
     */
    getSelectedFriends() {
        const checkboxes = document.querySelectorAll('.friend-checkbox:checked');
        return Array.from(checkboxes).map(checkbox => {
            const friendId = checkbox.value;
            return this.friends.find(friend => friend.id === friendId);
        }).filter(Boolean);
    }
    
    /**
     * Obtenir les localisations des amis
     * @param {Array} friends - Liste des amis
     * @returns {Promise<Array>} Locations des amis
     */
    async getFriendLocations(friends) {
        const locations = [];
        
        for (const friend of friends) {
            try {
                const location = await UserService.getUserLocation(friend.id);
                if (location) {
                    locations.push({
                        ...location,
                        friendName: `${friend.firstName} ${friend.lastName}`
                    });
                }
            } catch (error) {
                Logger.warn(`Impossible d'obtenir la localisation de ${friend.firstName}`, error);
            }
        }
        
        return locations;
    }
    
    /**
     * Rendre les résultats de bars
     * @param {Array} bars - Liste des bars
     * @param {Object} centralPoint - Point central
     */
    renderBarsResults(bars, centralPoint) {
        const resultsContainer = DOMUtils.getElementById('bars-results');
        if (!resultsContainer) return;
        
        if (bars.length === 0) {
            resultsContainer.innerHTML = '<p class="no-results">Aucun bar trouvé dans la zone</p>';
            return;
        }
        
        resultsContainer.innerHTML = `
            <h3>Bars recommandés</h3>
            <div class="bars-list">
                ${bars.map(bar => `
                    <div class="bar-item">
                        <h4>${bar.name}</h4>
                        <p class="bar-address">${bar.address}</p>
                        <p class="bar-distance">À ${bar.distance.toFixed(1)} km du point central</p>
                        <div class="bar-rating">
                            ${'★'.repeat(Math.floor(bar.rating || 0))}${'☆'.repeat(5 - Math.floor(bar.rating || 0))}
                            <span>(${bar.rating || 'N/A'})</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        resultsContainer.style.display = 'block';
    }
    
    /**
     * Définir l'état de chargement
     * @param {boolean} isLoading - État de chargement
     */
    setLoading(isLoading) {
        this.isLoading = isLoading;
        
        const loadingIndicator = DOMUtils.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = isLoading ? 'block' : 'none';
        }
        
        const findBarBtn = DOMUtils.getElementById('find-bar-btn');
        if (findBarBtn) {
            findBarBtn.disabled = isLoading;
            findBarBtn.textContent = isLoading ? 'Recherche...' : 'Trouver un bar';
        }
    }
    
    /**
     * Afficher un message d'erreur
     * @param {string} message - Message d'erreur
     */
    showError(message) {
        const errorContainer = this.getOrCreateMessageContainer();
        errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
        errorContainer.style.display = 'block';
        
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }
    
    /**
     * Afficher un message de succès
     * @param {string} message - Message de succès
     */
    showSuccess(message) {
        const messageContainer = this.getOrCreateMessageContainer();
        messageContainer.innerHTML = `<div class="success-message">${message}</div>`;
        messageContainer.style.display = 'block';
        
        setTimeout(() => {
            messageContainer.style.display = 'none';
        }, 3000);
    }
    
    /**
     * Obtenir ou créer le conteneur de messages
     * @returns {HTMLElement} Conteneur de messages
     */
    getOrCreateMessageContainer() {
        let container = DOMUtils.getElementById('message-container');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'message-container';
            container.className = 'message-container';
            document.body.insertBefore(container, document.body.firstChild);
        }
        
        return container;
    }
}
