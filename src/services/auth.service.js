/**
 * @fileoverview Service d'authentification Firebase
 * @author On va où ? Team
 * @version 1.0.0
 */

import { 
    createUserWithEmailAndPassword, 
    signInWithEmailAndPassword, 
    signOut, 
    onAuthStateChanged,
    updateProfile 
} from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';
import { auth, appConfig } from '../config/firebase.js';
import { UserService } from './user.service.js';
import { Logger } from '../utils/logger.js';

/**
 * Service de gestion de l'authentification
 */
export class AuthService {
    
    /**
     * Inscription d'un nouvel utilisateur
     * @param {Object} userData - Données utilisateur
     * @param {string} userData.firstName - Prénom
     * @param {string} userData.lastName - Nom
     * @param {string} userData.email - Email
     * @param {string} userData.password - Mot de passe
     * @returns {Promise<Object>} Résultat de l'inscription
     */
    static async register({ firstName, lastName, email, password }) {
        try {
            Logger.info('AuthService: Début inscription', { email });
            
            // Créer l'utilisateur dans Firebase Auth
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;
            
            Logger.info('AuthService: Utilisateur créé', { uid: user.uid });
            
            // Mettre à jour le profil utilisateur
            await updateProfile(user, {
                displayName: `${firstName} ${lastName}`
            });
            
            // Attendre la propagation du token
            await new Promise(resolve => setTimeout(resolve, appConfig.timeouts.authTokenRefresh));
            
            // Sauvegarder le profil dans Firestore
            await UserService.createProfile(user.uid, {
                firstName,
                lastName,
                email,
                preferences: {},
                address: '',
                createdAt: new Date()
            });
            
            Logger.info('AuthService: Profil utilisateur créé avec succès');
            
            return {
                success: true,
                user: user,
                message: 'Inscription réussie'
            };
            
        } catch (error) {
            Logger.error('AuthService: Erreur inscription', error);
            throw this.handleAuthError(error);
        }
    }
    
    /**
     * Connexion d'un utilisateur
     * @param {string} email - Email
     * @param {string} password - Mot de passe
     * @returns {Promise<Object>} Résultat de la connexion
     */
    static async login(email, password) {
        try {
            Logger.info('AuthService: Tentative de connexion', { email });
            
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            
            Logger.info('AuthService: Connexion réussie', { uid: userCredential.user.uid });
            
            return {
                success: true,
                user: userCredential.user,
                message: 'Connexion réussie'
            };
            
        } catch (error) {
            Logger.error('AuthService: Erreur connexion', error);
            throw this.handleAuthError(error);
        }
    }
    
    /**
     * Déconnexion
     * @returns {Promise<Object>} Résultat de la déconnexion
     */
    static async logout() {
        try {
            Logger.info('AuthService: Déconnexion');
            await signOut(auth);
            
            return {
                success: true,
                message: 'Déconnexion réussie'
            };
            
        } catch (error) {
            Logger.error('AuthService: Erreur déconnexion', error);
            throw error;
        }
    }
    
    /**
     * Observer des changements d'authentification
     * @param {Function} callback - Fonction appelée lors du changement
     * @returns {Function} Fonction de désabonnement
     */
    static onAuthStateChange(callback) {
        return onAuthStateChanged(auth, callback);
    }
    
    /**
     * Gestion des erreurs d'authentification
     * @param {Error} error - Erreur Firebase
     * @returns {Error} Erreur formatée
     */
    static handleAuthError(error) {
        const errorMessages = {
            'auth/email-already-in-use': 'Cette adresse email est déjà utilisée',
            'auth/weak-password': 'Le mot de passe doit contenir au moins 6 caractères',
            'auth/invalid-email': 'Adresse email invalide',
            'auth/user-not-found': 'Aucun utilisateur trouvé avec cet email',
            'auth/wrong-password': 'Mot de passe incorrect',
            'auth/too-many-requests': 'Trop de tentatives. Réessayez plus tard',
            'permission-denied': 'Erreur de permissions'
        };
        
        const message = errorMessages[error.code] || error.message || appConfig.messages.errorGeneric;
        
        const formattedError = new Error(message);
        formattedError.code = error.code;
        formattedError.originalError = error;
        
        return formattedError;
    }
}
