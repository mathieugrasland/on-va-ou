document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');

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
});