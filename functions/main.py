import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os
import requests
import json
import statistics
from geopy.distance import geodesic
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
        
        # Récupération des données
        request_json = request.get_json(silent=True)
        if not request_json or 'positions' not in request_json:
            return jsonify({"error": "Positions manquantes"}), 400, headers
        
        positions = request_json['positions']
        max_bars = request_json.get('max_bars', 5)
        search_radius = request_json.get('search_radius', 5000)  # 5km par défaut
        
        if len(positions) < 2:
            return jsonify({"error": "Au moins 2 positions requises"}), 400, headers

        # Calculer le point central optimal
        center_lat = statistics.mean([pos['location']['lat'] for pos in positions])
        center_lng = statistics.mean([pos['location']['lng'] for pos in positions])
        
        # Rechercher les bars autour du point central
        bars = search_bars_nearby(center_lat, center_lng, search_radius)
        
        if not bars:
            return jsonify({"error": "Aucun bar trouvé dans la zone"}), 404, headers
        
        # Calculer les temps de trajet pour chaque bar
        bars_with_times = []
        for bar in bars[:max_bars * 2]:  # Prendre plus que nécessaire pour le filtrage
            try:
                travel_times = calculate_travel_times(bar, positions)
                if travel_times:
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
            except Exception as e:
                print(f"Erreur calcul temps pour bar {bar.get('name', 'Unknown')}: {e}")
                continue
        
        # Trier par temps moyen puis par variance (équité)
        bars_with_times.sort(key=lambda x: (x['avg_travel_time'], x['time_variance']))
        
        # Prendre les meilleurs bars
        best_bars = bars_with_times[:max_bars]
        
        return jsonify({
            "success": True,
            "bars": best_bars,
            "center_point": {"lat": center_lat, "lng": center_lng}
        }), 200, headers

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, headers
    except Exception as e:
        print(f"Erreur find_optimal_bars: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers


def search_bars_nearby(lat, lng, radius):
    """Recherche les bars autour d'un point"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': 'bar',
            'key': GOOGLE_MAPS_API_KEY,
            'language': 'fr'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK':
            return data['results']
        else:
            print(f"Places API error: {data['status']}")
            return []
            
    except Exception as e:
        print(f"Erreur recherche bars: {e}")
        return []


def calculate_travel_times(bar, positions):
    """Calcule les temps de trajet pour chaque position vers un bar"""
    try:
        bar_location = bar['geometry']['location']
        travel_times = []
        
        # Préparer les destinations et origines pour l'API
        destinations = f"{bar_location['lat']},{bar_location['lng']}"
        
        for position in positions:
            origin = f"{position['location']['lat']},{position['location']['lng']}"
            transport_mode = position.get('transportMode', 'walking')
            
            # Mapper les modes de transport
            mode_mapping = {
                'car': 'driving',
                'bicycle': 'bicycling',
                'public_transport': 'transit',
                'walking': 'walking'
            }
            google_mode = mode_mapping.get(transport_mode, 'walking')
            
            # Appel à Distance Matrix API
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                'origins': origin,
                'destinations': destinations,
                'mode': google_mode,
                'language': 'fr',
                'key': GOOGLE_MAPS_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if (data['status'] == 'OK' and 
                data['rows'] and 
                data['rows'][0]['elements'] and 
                data['rows'][0]['elements'][0]['status'] == 'OK'):
                
                duration = data['rows'][0]['elements'][0]['duration']['value']
                travel_times.append(duration / 60)  # Convertir en minutes
            else:
                # Si l'API échoue, estimer avec la distance à vol d'oiseau
                distance_km = geodesic(
                    (position['location']['lat'], position['location']['lng']),
                    (bar_location['lat'], bar_location['lng'])
                ).kilometers
                
                # Estimation grossière selon le mode de transport
                speed_kmh = {'driving': 30, 'bicycling': 15, 'transit': 20, 'walking': 5}
                estimated_time = (distance_km / speed_kmh.get(google_mode, 5)) * 60
                travel_times.append(estimated_time)
            
            # Petite pause pour éviter les rate limits
            time.sleep(0.1)
        
        return travel_times
        
    except Exception as e:
        print(f"Erreur calcul temps de trajet: {e}")
        return []