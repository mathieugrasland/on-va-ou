import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os
import requests

# 🚀 Cloud Functions pour "On va où ?" - Version 1.0.0
# Dernière modification: 2025-08-27
# Fonctions pour gestion des utilisateurs et recommandations de bars

# Configuration sécurisée
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyBUNmeroMLlCNzrpCi7-6VCGBGfJ4Eg4MQ')

# Initialisation optimisée de Firebase
if not firebase_admin._apps:
    # En CI/CD ou production avec ADC (Application Default Credentials)
    if os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GITHUB_ACTIONS'):
        try:
            firebase_admin.initialize_app()
        except Exception as e:
            print(f"Warning: Could not initialize Firebase in CI/CD context: {e}")
            # On skip l'initialisation en mode analyse/compilation
            db = None
    else:
        # Pour le développement local
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

# Client Firestore global (réutilisé entre les invocations)
# Initialisation paresseuse pour éviter les erreurs en CI/CD
db = None
if firebase_admin._apps:
    try:
        db = firestore.client()
    except Exception as e:
        print(f"Warning: Could not initialize Firestore client: {e}")

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
        update_data = {}
        
        # Validation et nettoyage des données
        for k, v in request_json.items():
            if k in allowed_fields:
                if isinstance(v, str):
                    # Nettoyer les chaînes avec strip() (équivalent de trim() en JS)
                    cleaned_value = v.strip()
                    if cleaned_value:  # Ne pas accepter les chaînes vides après nettoyage
                        update_data[k] = cleaned_value
                elif v is not None:  # Accepter les autres types non-null
                    update_data[k] = v
        
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

@functions_framework.http
def geocode_address(request):
    """Géocoder une adresse de manière sécurisée via Google Maps API"""
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
        
        # Récupérer l'adresse depuis la requête
        request_json = request.get_json(silent=True)
        if not request_json or 'address' not in request_json:
            return jsonify({"error": "Adresse manquante"}), 400, headers
        
        address = request_json['address'].strip()
        if not address:
            return jsonify({"error": "Adresse vide"}), 400, headers
        
        # Appel sécurisé à l'API Google Geocoding
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address,
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(geocoding_url, params=params, timeout=10)
        response.raise_for_status()
        
        geocoding_data = response.json()
        
        if geocoding_data['status'] == 'OK' and geocoding_data['results']:
            result = geocoding_data['results'][0]
            location = result['geometry']['location']
            
            return jsonify({
                "success": True,
                "location": {
                    "lat": location['lat'],
                    "lng": location['lng']
                },
                "formatted_address": result['formatted_address']
            }), 200, headers
        else:
            return jsonify({
                "success": False,
                "error": "Adresse non trouvée",
                "status": geocoding_data['status']
            }), 404, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except requests.RequestException as e:
        print(f"Erreur API Google: {e}")
        return jsonify({"error": "Erreur service de géolocalisation"}), 503, headers
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers

@functions_framework.http
def send_friend_request(request):
    """Envoyer une demande d'ami"""
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
        sender_uid = decoded_token['uid']
        
        # Récupérer l'email de l'ami depuis la requête
        request_json = request.get_json(silent=True)
        if not request_json or 'friend_email' not in request_json:
            return jsonify({"error": "Email de l'ami manquant"}), 400, headers
        
        friend_email = request_json['friend_email'].strip()
        if not friend_email:
            return jsonify({"error": "Email vide"}), 400, headers

        # Rechercher l'utilisateur par email
        db = firestore.client()
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', friend_email).limit(1)
        results = query.stream()
        
        friend_user = None
        for doc in results:
            friend_user = doc
            break
            
        if not friend_user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404, headers
            
        friend_uid = friend_user.id
        
        # Vérifier qu'on ne s'ajoute pas soi-même
        if sender_uid == friend_uid:
            return jsonify({"error": "Impossible de s'ajouter soi-même"}), 400, headers
            
        # Ajouter la demande d'ami
        friend_doc_ref = db.collection('users').document(friend_uid)
        friend_doc_ref.update({
            'friendRequests': firestore.ArrayUnion([sender_uid])
        })
        
        return jsonify({"message": "Demande d'ami envoyée avec succès"}), 200, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers