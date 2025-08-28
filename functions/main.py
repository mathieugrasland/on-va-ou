import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os
import requests
import json
import statistics
import time

# Cloud Functions pour "On va où ?" - Version optimisée
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
def find_optimal_bars(request):
    """Trouve les bars optimaux en temps pour un groupe d'amis"""
    # Headers CORS pour toutes les réponses
    headers = {'Access-Control-Allow-Origin': '*'}
    
    # Gestion preflight OPTIONS
    if request.method == 'OPTIONS':
        headers.update({
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        })
        return ('', 204, headers)

    try:
        print(f"=== DEBUT find_optimal_bars ===")
        print(f"Method: {request.method}")
        print(f"Headers: {dict(request.headers)}")
        
        # Vérification du token
        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            print("ERROR: Token d'authentification manquant")
            return jsonify({"error": "Token d'authentification manquant"}), 401, headers

        id_token = authorization.split(' ')[1]
        print(f"Token reçu, longueur: {len(id_token)}")
        
        # Vérification du token Firebase
        try:
            decoded_token = auth.verify_id_token(id_token)
            print(f"Token valide pour user: {decoded_token.get('uid', 'unknown')}")
        except Exception as e:
            print(f"ERROR: Token invalide: {e}")
            return jsonify({"error": "Token invalide"}), 401, headers
        
        # Récupération des données
        request_json = request.get_json(silent=True)
        print(f"Body reçu: {request_json}")
        
        if not request_json or 'positions' not in request_json:
            print("ERROR: Positions manquantes")
            return jsonify({"error": "Positions manquantes"}), 400, headers
        
        positions = request_json['positions']
        max_bars = request_json.get('max_bars', 5)
        search_radius = min(request_json.get('search_radius', 500), 800)  # Limiter entre 500-800m pour performance
        
        print(f"Positions reçues: {len(positions)}")
        print(f"Max bars: {max_bars}, Radius: {search_radius}")
        
        if len(positions) < 2:
            print("ERROR: Moins de 2 positions")
            return jsonify({"error": "Au moins 2 positions requises"}), 400, headers

        # Calculer le point central optimal
        print("Calcul du point central...")
        center_lat = statistics.mean([pos['location']['lat'] for pos in positions])
        center_lng = statistics.mean([pos['location']['lng'] for pos in positions])
        print(f"Point central: {center_lat}, {center_lng}")
        
        # Rechercher les bars autour du point central (optimisé)
        print(f"Recherche de bars dans un rayon optimisé de {search_radius}m...")
        bars = search_bars_nearby(center_lat, center_lng, search_radius)
        print(f"Bars trouvés: {len(bars) if bars else 0}")
        
        if not bars:
            print("ERROR: Aucun bar trouvé")
            return jsonify({"error": "Aucun bar trouvé dans la zone"}), 404, headers
        
        # Filtrer d'abord les bars avec une note suffisante
        print("Filtrage des bars par note...")
        quality_bars = []
        for bar in bars:
            if bar.get('rating') and bar.get('rating') >= 3.0:
                quality_bars.append(bar)
        
        print(f"Bars avec note ≥3.0: {len(quality_bars)} sur {len(bars)}")
        
        if not quality_bars:
            print("ERROR: Aucun bar avec une note suffisante")
            return jsonify({"error": "Aucun bar bien noté trouvé dans la zone"}), 404, headers
        
        # Calculer les temps de trajet en batch (beaucoup plus rapide)
        print("Calcul batch des temps de trajet...")
        travel_times_results = calculate_travel_times_batch(quality_bars, positions)
        
        # Construire la liste finale des bars avec leurs temps
        bars_with_times = []
        for bar_idx, travel_times in travel_times_results.items():
            bar = quality_bars[bar_idx]
            avg_time = statistics.mean(travel_times)
            max_time = max(travel_times)
            
            bars_with_times.append({
                'name': bar['name'],
                'address': bar.get('formatted_address', bar.get('vicinity', '')),
                'location': bar['geometry']['location'],
                'rating': bar.get('rating'),
                'price_level': bar.get('price_level'),
                'place_id': bar['place_id'],
                'travel_times': travel_times,
                'avg_travel_time': avg_time,
                'max_travel_time': max_time,
                'time_variance': statistics.variance(travel_times) if len(travel_times) > 1 else 0
            })
        
        print(f"Bars finaux avec temps: {len(bars_with_times)}")
        
        if not bars_with_times:
            print("ERROR: Aucun bar avec temps de trajet valides")
            return jsonify({"error": "Impossible de calculer les temps de trajet"}), 500, headers
        
        # Trier par note d'abord (décroissant), puis par temps moyen (croissant)
        bars_with_times.sort(key=lambda x: (-x['rating'], x['avg_travel_time']))
        
        # Prendre les meilleurs bars
        best_bars = bars_with_times[:max_bars]
        
        return jsonify({
            "success": True,
            "bars": best_bars,
            "center_point": {"lat": center_lat, "lng": center_lng}
        }), 200, headers

    except auth.InvalidIdTokenError as e:
        print(f"ERROR: Token invalide: {e}")
        return jsonify({"error": "Token invalide"}), 401, headers
    except ValueError as e:
        print(f"ERROR: Données invalides: {e}")
        return jsonify({"error": str(e)}), 400, headers
    except Exception as e:
        print(f"ERROR: Exception non gérée dans find_optimal_bars: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers


def search_bars_nearby(lat, lng, radius):
    """Recherche les bars autour d'un point"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': 'bar',
            'keyword': 'bar pub cocktail bière',  # Mots-clés pour cibler les vrais bars
            'key': GOOGLE_MAPS_API_KEY,
            'language': 'fr'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK':
            # Filtrer pour exclure les hôtels et autres établissements
            filtered_bars = []
            for place in data['results']:
                place_types = place.get('types', [])
                place_name = place.get('name', '').lower()
                
                # Exclure si c'est un hôtel ou contient des mots-clés d'hôtel
                is_hotel = ('lodging' in place_types or 
                           'hotel' in place_name or 
                           'hôtel' in place_name or
                           'auberge' in place_name or
                           'resort' in place_name)
                
                # Inclure seulement si c'est vraiment un bar
                is_real_bar = ('bar' in place_types or 
                              'night_club' in place_types or
                              'bar' in place_name or 
                              'pub' in place_name or
                              'café' in place_name or
                              'brasserie' in place_name)
                
                if is_real_bar and not is_hotel:
                    filtered_bars.append(place)
            
            print(f"Bars filtrés: {len(filtered_bars)} sur {len(data['results'])} résultats")
            return filtered_bars
        else:
            print(f"Places API error: {data['status']}")
            return []
            
    except Exception as e:
        print(f"Erreur recherche bars: {e}")
        return []


def calculate_travel_times_batch(bars, positions):
    """Calcule les temps de trajet pour tous les bars et positions en groupant par mode de transport"""
    try:
        if not bars or not positions:
            return {}
        
        # Limiter le nombre de bars pour éviter les timeouts (max 10 bars)
        limited_bars = bars[:10]
        
        # Grouper les positions par mode de transport
        transport_groups = {}
        for idx, position in enumerate(positions):
            transport_mode = position.get('transportMode', 'walking')
            
            # Mapper les modes de transport
            mode_mapping = {
                'car': 'driving',
                'bicycle': 'bicycling', 
                'public_transport': 'transit',
                'walking': 'walking'
            }
            google_mode = mode_mapping.get(transport_mode, 'walking')
            
            if google_mode not in transport_groups:
                transport_groups[google_mode] = []
            
            transport_groups[google_mode].append({
                'index': idx,
                'position': position,
                'origin': f"{position['location']['lat']},{position['location']['lng']}"
            })
        
        print(f"Groupes de transport: {list(transport_groups.keys())}")
        
        # Préparer toutes les destinations (bars)
        destinations = []
        for bar in limited_bars:
            bar_location = bar['geometry']['location']
            destination = f"{bar_location['lat']},{bar_location['lng']}"
            destinations.append(destination)
        
        # Résultats finaux : bar_idx -> [temps_personne_0, temps_personne_1, ...]
        final_results = {}
        
        # Faire une requête par groupe de transport
        all_travel_times = [None] * len(positions)  # Index par position originale
        
        for transport_mode, group_positions in transport_groups.items():
            print(f"Calcul pour mode {transport_mode}: {len(group_positions)} personnes")
            
            # Préparer les origines pour ce groupe
            origins = [pos_info['origin'] for pos_info in group_positions]
            
            # Appel à l'API Distance Matrix pour ce groupe
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                'origins': '|'.join(origins),
                'destinations': '|'.join(destinations),
                'mode': transport_mode,
                'language': 'fr',
                'key': GOOGLE_MAPS_API_KEY
            }
            
            if transport_mode == 'transit':
                params['departure_time'] = 'now'
            
            print(f"Requête batch {transport_mode}: {len(origins)} origines vers {len(destinations)} destinations")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'OK':
                print(f"API Distance Matrix error pour {transport_mode}: {data['status']}")
                continue
            
            # Parser les résultats pour ce groupe
            for person_idx_in_group, pos_info in enumerate(group_positions):
                original_person_idx = pos_info['index']
                person_times = []
                
                for bar_idx in range(len(limited_bars)):
                    try:
                        element = data['rows'][person_idx_in_group]['elements'][bar_idx]
                        if element['status'] == 'OK':
                            duration_minutes = element['duration']['value'] / 60
                            person_times.append(duration_minutes)
                        else:
                            person_times.append(None)
                    except (KeyError, IndexError):
                        person_times.append(None)
                
                all_travel_times[original_person_idx] = person_times
        
        # Construire les résultats finaux par bar
        for bar_idx in range(len(limited_bars)):
            travel_times_for_bar = []
            valid_times = True
            
            for person_idx in range(len(positions)):
                if (all_travel_times[person_idx] is not None and 
                    bar_idx < len(all_travel_times[person_idx]) and
                    all_travel_times[person_idx][bar_idx] is not None):
                    travel_times_for_bar.append(all_travel_times[person_idx][bar_idx])
                else:
                    valid_times = False
                    break
            
            if valid_times and len(travel_times_for_bar) == len(positions):
                final_results[bar_idx] = travel_times_for_bar
        
        print(f"Résultats batch finaux: {len(final_results)} bars avec temps valides pour tous les modes de transport")
        return final_results
        
    except Exception as e:
        print(f"Erreur calcul batch: {e}")
        return {}