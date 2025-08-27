/**
 * @fileoverview Utilitaires généraux
 * @author On va où ? Team
 * @version 1.0.0
 */

/**
 * Utilitaires de validation
 */
export class Validator {
    
    /**
     * Valider une adresse email
     * @param {string} email - Email à valider
     * @returns {boolean} Validité de l'email
     */
    static isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    /**
     * Valider un mot de passe
     * @param {string} password - Mot de passe à valider
     * @returns {Object} Résultat de validation
     */
    static validatePassword(password) {
        const result = {
            isValid: true,
            errors: []
        };
        
        if (!password || password.length < 6) {
            result.isValid = false;
            result.errors.push('Le mot de passe doit contenir au moins 6 caractères');
        }
        
        return result;
    }
    
    /**
     * Valider les données d'inscription
     * @param {Object} data - Données à valider
     * @returns {Object} Résultat de validation
     */
    static validateRegistrationData(data) {
        const result = {
            isValid: true,
            errors: []
        };
        
        if (!data.firstName?.trim()) {
            result.errors.push('Le prénom est requis');
        }
        
        if (!data.lastName?.trim()) {
            result.errors.push('Le nom est requis');
        }
        
        if (!this.isValidEmail(data.email)) {
            result.errors.push('Adresse email invalide');
        }
        
        const passwordValidation = this.validatePassword(data.password);
        if (!passwordValidation.isValid) {
            result.errors.push(...passwordValidation.errors);
        }
        
        result.isValid = result.errors.length === 0;
        return result;
    }
}

/**
 * Utilitaires de manipulation du DOM
 */
export class DOMUtils {
    
    /**
     * Attendre que le DOM soit prêt
     * @returns {Promise<void>}
     */
    static ready() {
        return new Promise(resolve => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', resolve);
            } else {
                resolve();
            }
        });
    }
    
    /**
     * Obtenir un élément par ID de manière sécurisée
     * @param {string} id - ID de l'élément
     * @returns {HTMLElement|null} Élément ou null
     */
    static getElementById(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with ID '${id}' not found`);
        }
        return element;
    }
    
    /**
     * Afficher/masquer un élément
     * @param {HTMLElement} element - Élément
     * @param {boolean} show - Afficher ou masquer
     */
    static toggleElement(element, show) {
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }
    
    /**
     * Ajouter une classe CSS
     * @param {HTMLElement} element - Élément
     * @param {string} className - Classe CSS
     */
    static addClass(element, className) {
        if (element && className) {
            element.classList.add(className);
        }
    }
    
    /**
     * Supprimer une classe CSS
     * @param {HTMLElement} element - Élément
     * @param {string} className - Classe CSS
     */
    static removeClass(element, className) {
        if (element && className) {
            element.classList.remove(className);
        }
    }
}

/**
 * Utilitaires de navigation
 */
export class Router {
    
    /**
     * Naviguer vers une page
     * @param {string} page - Page de destination
     * @param {boolean} replace - Remplacer l'historique
     */
    static navigate(page, replace = false) {
        if (replace) {
            window.location.replace(page);
        } else {
            window.location.href = page;
        }
    }
    
    /**
     * Obtenir la page actuelle
     * @returns {string} Page actuelle
     */
    static getCurrentPage() {
        return window.location.pathname.split('/').pop() || 'index.html';
    }
    
    /**
     * Vérifier si on est sur une page spécifique
     * @param {string} page - Page à vérifier
     * @returns {boolean} Résultat de la vérification
     */
    static isCurrentPage(page) {
        return this.getCurrentPage() === page;
    }
}

/**
 * Utilitaires de formatage
 */
export class Formatter {
    
    /**
     * Formater une date
     * @param {Date} date - Date à formater
     * @returns {string} Date formatée
     */
    static formatDate(date) {
        return new Intl.DateTimeFormat('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(date);
    }
    
    /**
     * Formater un nom
     * @param {string} firstName - Prénom
     * @param {string} lastName - Nom
     * @returns {string} Nom formaté
     */
    static formatName(firstName, lastName) {
        const first = firstName?.trim();
        const last = lastName?.trim();
        
        if (first && last) {
            return `${first} ${last}`;
        }
        
        return first || last || 'Utilisateur';
    }
    
    /**
     * Capitaliser la première lettre
     * @param {string} str - Chaîne à capitaliser
     * @returns {string} Chaîne capitalisée
     */
    static capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }
}
