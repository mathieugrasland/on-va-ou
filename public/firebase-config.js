// Configuration Firebase centralisée
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';
import { getFirestore } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js';

// ATTENTION: Ces clés doivent être sécurisées en production
// Utiliser des variables d'environnement ou Firebase Hosting
const firebaseConfig = {
    apiKey: "AIzaSyBs1O6cYYxNLE2vB9gEcmhEhONrditDyCo",
    authDomain: "on-va-ou-470217.firebaseapp.com",
    projectId: "on-va-ou-470217",
    storageBucket: "on-va-ou-470217.firebasestorage.app",
    messagingSenderId: "687464295451",
    appId: "1:687464295451:web:b228ea2a0ddc668e5f1cbe",
    measurementId: "G-2PCHXTT6DW"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
