import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os

# Initialisation optimisée de Firebase
if not firebase_admin._apps:
    # Utilise les variables d'environnement en production
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        firebase_admin.initialize_app()
    else:
        # Pour le développement local
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

# Client Firestore global (réutilisé entre les invocations)
db = firestore.client()

@functions_framework.http
def get_user_profile(request):
    """Récupère le profil utilisateur - Cloud Function optimisée"""
    # CORS headers pour les requêtes cross-origin
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # Vérification du token d'authentification
        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            return jsonify({"error": "Token d'authentification manquant"}), 401, headers

        id_token = authorization.split(' ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Récupération du profil utilisateur
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "Profil utilisateur non trouvé"}), 404, headers

        user_data = user_doc.to_dict()
        # Ne pas exposer d'informations sensibles
        safe_data = {
            'firstName': user_data.get('firstName', ''),
            'lastName': user_data.get('lastName', ''),
            'email': user_data.get('email', ''),
            'preferences': user_data.get('preferences', {}),
            'address': user_data.get('address', '')
        }

        return jsonify(safe_data), 200, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except Exception as e:
        print(f"Erreur: {e}")  # Pour les logs
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers

@functions_framework.http
def update_user_profile(request):
    """Met à jour le profil utilisateur"""
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # Vérification du token
        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            return jsonify({"error": "Token d'authentification manquant"}), 401, headers

        id_token = authorization.split(' ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Données à mettre à jour
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "Données manquantes"}), 400, headers

        # Champs autorisés à être mis à jour
        allowed_fields = ['firstName', 'lastName', 'address', 'preferences']
        update_data = {k: v for k, v in request_json.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({"error": "Aucun champ valide à mettre à jour"}), 400, headers

        # Mise à jour dans Firestore
        user_ref = db.collection('users').document(uid)
        user_ref.update(update_data)

        return jsonify({"message": "Profil mis à jour avec succès"}), 200, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers