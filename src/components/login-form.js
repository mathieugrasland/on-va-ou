/**
 * @fileoverview Composant de formulaire de connexion
 * @author On va où ? Team
 * @version 1.0.0
 */

import { AuthService } from '../services/auth.service.js';
import { Validator, DOMUtils, Router } from '../utils/helpers.js';
import { Logger } from '../utils/logger.js';

/**
 * Composant de gestion du formulaire de connexion
 */
export class LoginForm {
    
    constructor() {
        this.form = null;
        this.isSubmitting = false;
        this.init();
    }
    
    /**
     * Initialiser le composant
     */
    async init() {
        await DOMUtils.ready();
        this.form = DOMUtils.getElementById('login-form');
        
        if (this.form) {
            this.bindEvents();
            Logger.info('LoginForm: Composant initialisé');
        }
    }
    
    /**
     * Lier les événements
     */
    bindEvents() {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        
        // Validation en temps réel
        const inputs = this.form.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('blur', this.validateField.bind(this));
        });
    }
    
    /**
     * Gérer la soumission du formulaire
     * @param {Event} event - Événement de soumission
     */
    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isSubmitting) return;
        
        const formData = this.getFormData();
        const validation = Validator.validateLoginData(formData);
        
        if (!validation.isValid) {
            this.showErrors(validation.errors);
            return;
        }
        
        this.setSubmitting(true);
        
        try {
            const result = await AuthService.login(formData.email, formData.password);
            
            if (result.success) {
                this.showSuccess('Connexion réussie ! Redirection...');
                setTimeout(() => Router.navigate('dashboard.html'), 1500);
            }
            
        } catch (error) {
            this.showError(error.message);
            Logger.error('LoginForm: Erreur connexion', error);
        } finally {
            this.setSubmitting(false);
        }
    }
    
    /**
     * Obtenir les données du formulaire
     * @returns {Object} Données du formulaire
     */
    getFormData() {
        const formData = new FormData(this.form);
        return {
            email: formData.get('email')?.trim(),
            password: formData.get('password')
        };
    }
    
    /**
     * Valider un champ spécifique
     * @param {Event} event - Événement de validation
     */
    validateField(event) {
        const field = event.target;
        const value = field.value.trim();
        
        this.clearFieldError(field);
        
        switch (field.name) {
            case 'email':
                if (!value) {
                    this.setFieldError(field, 'Email est requis');
                } else if (!Validator.isValidEmail(value)) {
                    this.setFieldError(field, 'Email invalide');
                }
                break;
                
            case 'password':
                if (!value) {
                    this.setFieldError(field, 'Mot de passe requis');
                }
                break;
        }
    }
    
    /**
     * Définir l'état de soumission
     * @param {boolean} isSubmitting - État de soumission
     */
    setSubmitting(isSubmitting) {
        this.isSubmitting = isSubmitting;
        const submitButton = this.form.querySelector('button[type="submit"]');
        
        if (submitButton) {
            submitButton.disabled = isSubmitting;
            submitButton.textContent = isSubmitting ? 'Connexion...' : 'Se connecter';
        }
    }
    
    /**
     * Afficher les erreurs
     * @param {Array<string>} errors - Liste des erreurs
     */
    showErrors(errors) {
        const errorContainer = this.getOrCreateErrorContainer();
        errorContainer.innerHTML = `
            <div class="error-message">
                ${errors.map(error => `<p>• ${error}</p>`).join('')}
            </div>
        `;
        errorContainer.style.display = 'block';
    }
    
    /**
     * Afficher une erreur
     * @param {string} message - Message d'erreur
     */
    showError(message) {
        this.showErrors([message]);
    }
    
    /**
     * Afficher un message de succès
     * @param {string} message - Message de succès
     */
    showSuccess(message) {
        const errorContainer = this.getOrCreateErrorContainer();
        errorContainer.innerHTML = `<div class="success-message">${message}</div>`;
        errorContainer.style.display = 'block';
    }
    
    /**
     * Obtenir ou créer le conteneur d'erreurs
     * @returns {HTMLElement} Conteneur d'erreurs
     */
    getOrCreateErrorContainer() {
        let container = this.form.querySelector('.message-container');
        
        if (!container) {
            container = document.createElement('div');
            container.className = 'message-container';
            this.form.insertBefore(container, this.form.firstChild);
        }
        
        return container;
    }
    
    /**
     * Définir une erreur sur un champ
     * @param {HTMLElement} field - Champ
     * @param {string} message - Message d'erreur
     */
    setFieldError(field, message) {
        DOMUtils.addClass(field, 'error');
        field.setAttribute('data-error', message);
    }
    
    /**
     * Effacer l'erreur d'un champ
     * @param {HTMLElement} field - Champ
     */
    clearFieldError(field) {
        DOMUtils.removeClass(field, 'error');
        field.removeAttribute('data-error');
    }
}
