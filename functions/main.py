import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os
import requests

# Cloud Functions pour "On va où ?" - Version 1.0.0
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyBUNmeroMLlCNzrpCi7-6VCGBGfJ4Eg4MQ')

# Initialisation Firebase
if not firebase_admin._apps:
    if os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GITHUB_ACTIONS'):
        try:
            firebase_admin.initialize_app()
        except Exception as e:
            print(f"Warning: Could not initialize Firebase in CI/CD context: {e}")
            db = None
    else:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

db = None if not firebase_admin._apps else firestore.client()

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
        # Vérification du token
        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            return jsonify({"error": "Token d'authentification manquant"}), 401, headers

        id_token = authorization.split(' ')[1]
        auth.verify_id_token(id_token)
        
        # Récupération de l'adresse
        request_json = request.get_json(silent=True)
        if not request_json or 'address' not in request_json:
            return jsonify({"error": "Adresse manquante"}), 400, headers
        
        address = request_json['address'].strip()
        if not address:
            return jsonify({"error": "Adresse vide"}), 400, headers

        # Configuration des URLs
        places_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        # Essai avec Places API
        places_params = {
            'input': address,
            'key': GOOGLE_MAPS_API_KEY,
            'types': 'establishment|geocode',
            'language': 'fr',
            'components': 'country:fr'
        }
        
        # Essayer d'abord l'API Places
        places_response = requests.get(places_url, params=places_params, timeout=10)
        places_response.raise_for_status()
        places_data = places_response.json()
        
        if places_data['status'] == 'OK' and places_data['predictions']:
            place_id = places_data['predictions'][0]['place_id']
            
            geocoding_params = {'place_id': place_id, 'key': GOOGLE_MAPS_API_KEY}
            
            response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
            response.raise_for_status()
            geocoding_data = response.json()
            
            if geocoding_data['status'] == 'OK' and geocoding_data['results']:
                result = geocoding_data['results'][0]
                return jsonify({
                    "success": True,
                    "location": result['geometry']['location'],
                    "formatted_address": result['formatted_address']
                }), 200, headers
        
        # Si Places ne trouve rien, essayer le géocodage direct
        geocoding_params = {
            'address': address,
            'key': GOOGLE_MAPS_API_KEY,
            'region': 'fr'
        }
        
        response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
        response.raise_for_status()
        geocoding_data = response.json()
        
        if geocoding_data['status'] == 'OK' and geocoding_data['results']:
            result = geocoding_data['results'][0]
            return jsonify({
                "success": True,
                "location": result['geometry']['location'],
                "formatted_address": result['formatted_address']
            }), 200, headers
        
        return jsonify({"success": False, "error": "Adresse non trouvée"}), 404, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except requests.RequestException:
        return jsonify({"error": "Service de géolocalisation temporairement indisponible"}), 503, headers
    except Exception:
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers

@functions_framework.http
def geocode_batch(request):
    """Géocoder plusieurs adresses en une seule fois - Optimisation pour rester en free tier"""
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
        auth.verify_id_token(id_token)
        
        # Récupération des adresses
        request_json = request.get_json(silent=True)
        if not request_json or 'addresses' not in request_json:
            return jsonify({"error": "Liste d'adresses manquante"}), 400, headers
        
        addresses_data = request_json['addresses']
        if not isinstance(addresses_data, list) or len(addresses_data) == 0:
            return jsonify({"error": "Liste d'adresses vide ou invalide"}), 400, headers

        # Limite de sécurité pour éviter l'abus
        if len(addresses_data) > 20:
            return jsonify({"error": "Trop d'adresses (max 20)"}), 400, headers

        # Configuration des URLs
        places_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        results = {}
        
        # Traiter chaque adresse
        for address_info in addresses_data:
            if not isinstance(address_info, dict) or 'id' not in address_info or 'address' not in address_info:
                results[address_info.get('id', 'unknown')] = {
                    "success": False,
                    "error": "Format d'adresse invalide"
                }
                continue
                
            address_id = address_info['id']
            address = address_info['address'].strip()
            
            if not address:
                results[address_id] = {
                    "success": False,
                    "error": "Adresse vide"
                }
                continue

            try:
                # Essai avec Places API d'abord
                places_params = {
                    'input': address,
                    'key': GOOGLE_MAPS_API_KEY,
                    'types': 'establishment|geocode',
                    'language': 'fr',
                    'components': 'country:fr'
                }
                
                places_response = requests.get(places_url, params=places_params, timeout=10)
                places_response.raise_for_status()
                places_data = places_response.json()
                
                if places_data['status'] == 'OK' and places_data['predictions']:
                    place_id = places_data['predictions'][0]['place_id']
                    
                    geocoding_params = {'place_id': place_id, 'key': GOOGLE_MAPS_API_KEY}
                    
                    response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
                    response.raise_for_status()
                    geocoding_data = response.json()
                    
                    if geocoding_data['status'] == 'OK' and geocoding_data['results']:
                        result = geocoding_data['results'][0]
                        results[address_id] = {
                            "success": True,
                            "location": result['geometry']['location'],
                            "formatted_address": result['formatted_address']
                        }
                        continue
                
                # Si Places ne trouve rien, essayer le géocodage direct
                geocoding_params = {
                    'address': address,
                    'key': GOOGLE_MAPS_API_KEY,
                    'region': 'fr'
                }
                
                response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
                response.raise_for_status()
                geocoding_data = response.json()
                
                if geocoding_data['status'] == 'OK' and geocoding_data['results']:
                    result = geocoding_data['results'][0]
                    results[address_id] = {
                        "success": True,
                        "location": result['geometry']['location'],
                        "formatted_address": result['formatted_address']
                    }
                else:
                    results[address_id] = {
                        "success": False,
                        "error": "Adresse non trouvée"
                    }
                    
            except requests.RequestException as e:
                results[address_id] = {
                    "success": False,
                    "error": f"Erreur de géocodage: {str(e)}"
                }
            except Exception as e:
                results[address_id] = {
                    "success": False,
                    "error": f"Erreur interne: {str(e)}"
                }

        return jsonify({
            "success": True,
            "results": results,
            "processed_count": len(addresses_data)
        }), 200, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except Exception as e:
        return jsonify({"error": f"Erreur interne du serveur: {str(e)}"}), 500, headers

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


@functions_framework.http
def clean_duplicate_friend_requests(request):
    """Nettoyer les demandes d'amis dupliquées et les invitations bidirectionnelles"""
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
        user_uid = decoded_token['uid']
        
        db = firestore.client()
        user_ref = db.collection('users').document(user_uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "Utilisateur non trouvé"}), 404, headers
            
        user_data = user_doc.to_dict()
        friends = user_data.get('friends', [])
        friend_requests = user_data.get('friendRequests', {'sent': [], 'received': []})
        
        # Assurer la structure correcte
        if isinstance(friend_requests, list):
            friend_requests = {'sent': [], 'received': friend_requests}
        
        if 'sent' not in friend_requests:
            friend_requests['sent'] = []
        if 'received' not in friend_requests:
            friend_requests['received'] = []
            
        changes_made = False
        
        # Nettoyer les demandes envoyées si l'utilisateur est déjà ami
        original_sent = friend_requests['sent'].copy()
        friend_requests['sent'] = [uid for uid in friend_requests['sent'] if uid not in friends]
        if len(friend_requests['sent']) != len(original_sent):
            changes_made = True
            
        # Nettoyer les demandes reçues si l'utilisateur est déjà ami
        original_received = friend_requests['received'].copy()
        friend_requests['received'] = [uid for uid in friend_requests['received'] if uid not in friends]
        if len(friend_requests['received']) != len(original_received):
            changes_made = True
            
        # Gérer les invitations bidirectionnelles (auto-accepter si les deux ont envoyé)
        mutual_requests = []
        for sent_uid in friend_requests['sent']:
            if sent_uid in friend_requests['received']:
                mutual_requests.append(sent_uid)
                
        if mutual_requests:
            for friend_uid in mutual_requests:
                # Ajouter aux amis
                if friend_uid not in friends:
                    friends.append(friend_uid)
                    
                # Retirer des demandes
                if friend_uid in friend_requests['sent']:
                    friend_requests['sent'].remove(friend_uid)
                if friend_uid in friend_requests['received']:
                    friend_requests['received'].remove(friend_uid)
                    
                # Mettre à jour l'autre utilisateur aussi
                try:
                    other_user_ref = db.collection('users').document(friend_uid)
                    other_user_doc = other_user_ref.get()
                    if other_user_doc.exists:
                        other_data = other_user_doc.to_dict()
                        other_friends = other_data.get('friends', [])
                        other_requests = other_data.get('friendRequests', {'sent': [], 'received': []})
                        
                        if isinstance(other_requests, list):
                            other_requests = {'sent': [], 'received': other_requests}
                            
                        # Ajouter l'amitié mutuelle
                        if user_uid not in other_friends:
                            other_friends.append(user_uid)
                            
                        # Nettoyer les demandes
                        if 'sent' in other_requests and user_uid in other_requests['sent']:
                            other_requests['sent'].remove(user_uid)
                        if 'received' in other_requests and user_uid in other_requests['received']:
                            other_requests['received'].remove(user_uid)
                            
                        other_user_ref.update({
                            'friends': other_friends,
                            'friendRequests': other_requests
                        })
                except Exception as e:
                    print(f"Erreur mise à jour ami {friend_uid}: {e}")
                    
            changes_made = True
            
        # Sauvegarder les modifications si nécessaire
        if changes_made:
            user_ref.update({
                'friends': friends,
                'friendRequests': friend_requests
            })
            
        return jsonify({
            "message": "Nettoyage terminé",
            "changes_made": changes_made,
            "mutual_friends_added": len(mutual_requests),
            "requests_cleaned": {
                "sent_removed": len(original_sent) - len(friend_requests['sent']),
                "received_removed": len(original_received) - len(friend_requests['received'])
            }
        }), 200, headers

    except Exception as e:
        print(f"Erreur nettoyage: {str(e)}")
        return jsonify({"error": "Erreur lors du nettoyage"}), 500, headers
