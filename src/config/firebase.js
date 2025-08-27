/**
 * @fileoverview Configuration Firebase centralisée
 * @author On va où ? Team
 * @version 1.0.0
 */

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';
import { getFirestore } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js';

/**
 * Configuration Firebase pour l'environnement de production
 * Ces clés sont publiques et sécurisées par les règles Firestore
 */
const firebaseConfig = {
    apiKey: "AIzaSyBs1O6cYYxNLE2vB9gEcmhEhONrditDyCo",
    authDomain: "on-va-ou-470217.firebaseapp.com",
    projectId: "on-va-ou-470217",
    storageBucket: "on-va-ou-470217.firebasestorage.app",
    messagingSenderId: "687464295451",
    appId: "1:687464295451:web:b228ea2a0ddc668e5f1cbe",
    measurementId: "G-2PCHXTT6DW"
};

/**
 * Instance Firebase initialisée
 */
export const app = initializeApp(firebaseConfig);

/**
 * Service d'authentification Firebase
 */
export const auth = getAuth(app);

/**
 * Base de données Firestore
 */
export const db = getFirestore(app);

/**
 * Configuration de l'application
 */
export const appConfig = {
    name: 'On va où ?',
    version: '1.0.0',
    description: 'Application pour trouver le bar idéal entre amis',
    author: 'On va où ? Team',
    environment: 'production',
    
    // URLs
    urls: {
        homepage: 'https://on-va-ou-470217.web.app',
        repository: 'https://github.com/mathieugrasland/on-va-ou'
    },
    
    // Timeouts et délais (en ms)
    timeouts: {
        authTokenRefresh: 1000,
        defaultRequest: 10000,
        debounceSearch: 300
    },
    
    // Messages par défaut
    messages: {
        defaultUserName: 'Utilisateur',
        loadingAuth: 'Vérification de l\'authentification...',
        errorGeneric: 'Une erreur s\'est produite. Veuillez réessayer.'
    }
};
