import { auth, db } from './firebase-config.js';
import { createUserWithEmailAndPassword, signInWithEmailAndPassword, onAuthStateChanged } from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');

    // Vérifier si l'utilisateur est déjà connecté
    onAuthStateChanged(auth, (user) => {
        if (user && (window.location.pathname.includes('login.html') || window.location.pathname.includes('register.html'))) {
            window.location.href = 'dashboard.html';
        }
    });

    // Inscription avec Firebase Auth côté client
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const firstName = e.target.firstName.value;
            const lastName = e.target.lastName.value;
            const email = e.target.email.value;
            const password = e.target.password.value;

            try {
                // Créer l'utilisateur avec Firebase Auth
                const userCredential = await createUserWithEmailAndPassword(auth, email, password);
                const user = userCredential.user;

                // Sauvegarder le profil dans Firestore
                await setDoc(doc(db, 'users', user.uid), {
                    firstName: firstName,
                    lastName: lastName,
                    email: email,
                    preferences: {},
                    address: '',
                    createdAt: new Date()
                });

                alert('Inscription réussie ! Vous pouvez maintenant vous connecter.');
                window.location.href = 'login.html';
            } catch (error) {
                console.error('Erreur inscription:', error);
                alert('Erreur: ' + error.message);
            }
        });
    }

    // Connexion avec Firebase Auth côté client
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = e.target.email.value;
            const password = e.target.password.value;

            try {
                await signInWithEmailAndPassword(auth, email, password);
                alert('Connexion réussie !');
                window.location.href = 'dashboard.html';
            } catch (error) {
                console.error('Erreur connexion:', error);
                alert('Erreur: ' + error.message);
            }
        });
    }
});