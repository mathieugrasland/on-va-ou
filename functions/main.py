import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Initialisation de l'application Firebase (une seule fois)
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

db = firestore.client()

@functions_framework.http
def register_user(request):
    """HTTP Cloud Function pour l'inscription."""
    try:
        request_json = request.get_json(silent=True)
        if not request_json or not all(k in request_json for k in ('email', 'password', 'firstName', 'lastName')):
            return {"error": "Les données d'inscription sont incomplètes."}, 400

        email = request_json['email']
        password = request_json['password']
        firstName = request_json['firstName']
        lastName = request_json['lastName']

        # 1. Créer l'utilisateur dans Firebase Authentication
        user_record = auth.create_user(
            email=email,
            password=password
        )

        # 2. Sauvegarder les informations supplémentaires dans Cloud Firestore
        user_ref = db.collection('users').document(user_record.uid)
        user_ref.set({
            'firstName': firstName,
            'lastName': lastName,
            'email': email,
            'preferences': {},
            'address': '',
            'createdAt': firestore.SERVER_TIMESTAMP
        })

        return {"message": "Inscription réussie", "uid": user_record.uid}, 201

    except auth.EmailAlreadyExistsError:
        return {"error": "Cette adresse e-mail est déjà utilisée."}, 409
    except Exception as e:
        return {"error": f"Erreur interne : {e}"}, 500