document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');

    // Logique pour l'inscription (déjà présente)
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const firstName = e.target.firstName.value;
            const lastName = e.target.lastName.value;
            const email = e.target.email.value;
            const password = e.target.password.value;

            try {
                const response = await fetch('/registerUser', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, firstName, lastName })
                });
                const result = await response.json();
                if (response.ok) {
                    alert('Inscription réussie ! Vous pouvez maintenant vous connecter.');
                    window.location.href = 'login.html';
                } else {
                    alert('Erreur: ' + result.error);
                }
            } catch (error) {
                alert('Une erreur s\'est produite. Veuillez réessayer.');
                console.error(error);
            }
        });
    }

    // Nouvelle logique pour la connexion
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = e.target.email.value;
            const password = e.target.password.value;

            try {
                const response = await fetch('/loginUser', { // Requête vers la future Cloud Function de connexion
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const result = await response.json();
                if (response.ok) {
                    alert('Connexion réussie !');
                    // On peut rediriger vers la page du profil ou la carte
                    window.location.href = 'dashboard.html';
                } else {
                    alert('Erreur: ' + result.error);
                }
            } catch (error) {
                alert('Une erreur s\'est produite. Veuillez réessayer.');
                console.error(error);
            }
        });
    }
});