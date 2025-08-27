// Configuration Firebase centralisée
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';
import { getFirestore } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js';

// Configuration Firebase (clés publiques sécurisées par domaine)
const firebaseConfig = {
    apiKey: "AIzaSyBUNmeroMLlCNzrpCi7-6VCGBGfJ4Eg4MQ",
    authDomain: "on-va-ou-470217.firebaseapp.com",
    projectId: "on-va-ou-470217",
    storageBucket: "on-va-ou-470217.firebasestorage.app",
    messagingSenderId: "565550488662",
    appId: "1:565550488662:web:8e5c6cdca70c7c81bfab31"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
