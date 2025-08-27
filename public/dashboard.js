import { auth, db } from './firebase-config.js';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';

document.addEventListener('DOMContentLoaded', () => {
    const userNameElement = document.getElementById('user-name');
    const logoutBtn = document.getElementById('logout-btn');

    // Vérifier l'authentification
    onAuthStateChanged(auth, async (user) => {
        if (user) {
            try {
                // Récupérer les informations utilisateur depuis Firestore
                const userDoc = await getDoc(doc(db, 'users', user.uid));
                if (userDoc.exists()) {
                    const userData = userDoc.data();
                    userNameElement.textContent = userData.firstName || 'Utilisateur';
                } else {
                    userNameElement.textContent = 'Utilisateur';
                }
            } catch (error) {
                console.error('Erreur lors de la récupération du profil:', error);
                userNameElement.textContent = 'Utilisateur';
            }
        } else {
            // Rediriger vers la page de connexion si non authentifié
            window.location.href = 'login.html';
        }
    });

    // Gestion de la déconnexion
    logoutBtn.addEventListener('click', async () => {
        try {
            await signOut(auth);
            window.location.href = 'index.html';
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
            alert('Erreur lors de la déconnexion');
        }
    });
});
