/**
 * @fileoverview Service de gestion des utilisateurs
 * @author On va où ? Team
 * @version 1.0.0
 */

import { doc, setDoc, getDoc, updateDoc } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js';
import { db, appConfig } from '../config/firebase.js';
import { Logger } from '../utils/logger.js';

/**
 * Service de gestion des profils utilisateurs
 */
export class UserService {
    
    /**
     * Créer un profil utilisateur
     * @param {string} uid - ID utilisateur
     * @param {Object} profileData - Données du profil
     * @returns {Promise<void>}
     */
    static async createProfile(uid, profileData) {
        try {
            Logger.info('UserService: Création profil', { uid });
            
            const userRef = doc(db, 'users', uid);
            await setDoc(userRef, profileData);
            
            Logger.info('UserService: Profil créé avec succès');
            
        } catch (error) {
            Logger.error('UserService: Erreur création profil', error);
            throw error;
        }
    }
    
    /**
     * Récupérer un profil utilisateur
     * @param {string} uid - ID utilisateur
     * @returns {Promise<Object|null>} Données du profil ou null
     */
    static async getProfile(uid) {
        try {
            Logger.info('UserService: Récupération profil', { uid });
            
            const userRef = doc(db, 'users', uid);
            const userDoc = await getDoc(userRef);
            
            if (userDoc.exists()) {
                const data = userDoc.data();
                Logger.info('UserService: Profil trouvé');
                return data;
            } else {
                Logger.warn('UserService: Profil non trouvé', { uid });
                return null;
            }
            
        } catch (error) {
            Logger.error('UserService: Erreur récupération profil', error);
            throw error;
        }
    }
    
    /**
     * Mettre à jour un profil utilisateur
     * @param {string} uid - ID utilisateur
     * @param {Object} updates - Données à mettre à jour
     * @returns {Promise<void>}
     */
    static async updateProfile(uid, updates) {
        try {
            Logger.info('UserService: Mise à jour profil', { uid, updates });
            
            const userRef = doc(db, 'users', uid);
            await updateDoc(userRef, {
                ...updates,
                updatedAt: new Date()
            });
            
            Logger.info('UserService: Profil mis à jour avec succès');
            
        } catch (error) {
            Logger.error('UserService: Erreur mise à jour profil', error);
            throw error;
        }
    }
    
    /**
     * Obtenir le nom d'affichage d'un utilisateur
     * @param {Object} profile - Profil utilisateur
     * @returns {string} Nom d'affichage
     */
    static getDisplayName(profile) {
        if (!profile) return appConfig.messages.defaultUserName;
        
        if (profile.firstName && profile.lastName) {
            return `${profile.firstName} ${profile.lastName}`;
        }
        
        if (profile.firstName) return profile.firstName;
        if (profile.displayName) return profile.displayName;
        if (profile.email) return profile.email.split('@')[0];
        
        return appConfig.messages.defaultUserName;
    }
}
