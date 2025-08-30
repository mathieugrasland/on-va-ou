import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask import jsonify
import os
import requests
import statistics
import time
from typing import List, Dict, Tuple, Optional

# ===== CONSTANTES =====
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyBUNmeroMLlCNzrpCi7-6VCGBGfJ4Eg4MQ')

# Limites API et timeouts
API_TIMEOUT = 15
MAX_BARS_DEFAULT = 25
MAX_API_ORIGINS = 5
MAX_API_DESTINATIONS = 25
MAX_SEARCH_PAGES = 2
PAGE_TOKEN_DELAY = 2

# Paramètres de géolocalisation
KM_PER_DEGREE_LAT = 111
KM_PER_DEGREE_LNG_FR = 69.1  # À la latitude française (~46°)
MIN_SEARCH_RADIUS = 500
DEFAULT_CLUSTER_DISTANCE = 0.6

# Vitesses moyennes (km/h)
TRANSPORT_SPEEDS = {
    'driving': 25,
    'bicycling': 15, 
    'transit': 20,
    'walking': 4
}

# Mapping modes de transport
TRANSPORT_MODE_MAPPING = {
    'car': 'driving',
    'bicycle': 'bicycling',
    'public_transport': 'transit',
    'walking': 'walking'
}

# Headers CORS standard
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}
CORS_PREFLIGHT_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '3600'
}

# ===== INITIALISATION FIREBASE =====
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

# ===== UTILITAIRES =====

def handle_cors_preflight(request):
    """Gère les requêtes preflight CORS"""
    if request.method == 'OPTIONS':
        return ('', 204, CORS_PREFLIGHT_HEADERS)
    return None

def verify_auth_token(request) -> Optional[str]:
    """Vérifie et retourne le token d'authentification"""
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    id_token = authorization.split(' ')[1]
    try:
        auth.verify_id_token(id_token)
        return id_token
    except:
        return None

def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calcule la distance euclidienne approximative en km"""
    lat_diff = (lat2 - lat1) * KM_PER_DEGREE_LAT
    lng_diff = (lng2 - lng1) * KM_PER_DEGREE_LNG_FR
    return (lat_diff ** 2 + lng_diff ** 2) ** 0.5

def estimate_travel_time(distance_km: float, transport_mode: str) -> float:
    """Estime le temps de trajet en minutes"""
    speed = TRANSPORT_SPEEDS.get(transport_mode, TRANSPORT_SPEEDS['walking'])
    return (distance_km / speed) * 60

# ===== FONCTIONS PRINCIPALES =====

@functions_framework.http
def geocode_address(request):
    """Géocoder une adresse de manière sécurisée via Google Maps API"""
    # Gestion CORS preflight
    cors_response = handle_cors_preflight(request)
    if cors_response:
        return cors_response

    try:
        # Vérification authentification
        if not verify_auth_token(request):
            return jsonify({"error": "Token d'authentification manquant ou invalide"}), 401, CORS_HEADERS
        
        # Validation des données
        request_json = request.get_json(silent=True)
        if not request_json or 'address' not in request_json:
            return jsonify({"error": "Adresse manquante"}), 400, CORS_HEADERS
        
        address = request_json['address'].strip()
        if not address:
            return jsonify({"error": "Adresse vide"}), 400, CORS_HEADERS

        # Tentative avec Places API puis géocodage direct
        result = geocode_with_places_api(address) or geocode_direct(address)
        
        if result:
            return jsonify({
                "success": True,
                "location": result['geometry']['location'],
                "formatted_address": result['formatted_address']
            }), 200, CORS_HEADERS
        
        return jsonify({"success": False, "error": "Adresse non trouvée"}), 404, CORS_HEADERS

    except auth.InvalidIdTokenError:
        return jsonify({"error": "Token invalide"}), 401, CORS_HEADERS
    except requests.RequestException:
        return jsonify({"error": "Service de géolocalisation temporairement indisponible"}), 503, CORS_HEADERS
    except Exception as e:
        print(f"Erreur geocode_address: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, CORS_HEADERS

def geocode_with_places_api(address: str) -> Optional[Dict]:
    """Tentative de géocodage via Places API"""
    try:
        places_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        places_params = {
            'input': address,
            'key': GOOGLE_MAPS_API_KEY,
            'types': 'establishment|geocode',
            'language': 'fr',
            'components': 'country:fr'
        }
        
        response = requests.get(places_url, params=places_params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['predictions']:
            place_id = data['predictions'][0]['place_id']
            return geocode_by_place_id(place_id)
        
        return None
    except Exception:
        return None

def geocode_by_place_id(place_id: str) -> Optional[Dict]:
    """Géocode par Place ID"""
    try:
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {'place_id': place_id, 'key': GOOGLE_MAPS_API_KEY}
        
        response = requests.get(geocoding_url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            return data['results'][0]
        return None
    except Exception:
        return None

def geocode_direct(address: str) -> Optional[Dict]:
    """Géocodage direct par adresse"""
    try:
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address,
            'key': GOOGLE_MAPS_API_KEY,
            'region': 'fr'
        }
        
        response = requests.get(geocoding_url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            return data['results'][0]
        return None
    except Exception:
        return None


@functions_framework.http
def find_optimal_bars(request):
    """Trouve les bars optimaux en temps pour un groupe d'amis"""
    # Gestion CORS preflight
    cors_response = handle_cors_preflight(request)
    if cors_response:
        return cors_response

    try:
        # Vérification authentification
        if not verify_auth_token(request):
            return jsonify({"error": "Token d'authentification manquant ou invalide"}), 401, CORS_HEADERS
        
        # Validation des données
        request_json = request.get_json(silent=True)
        if not request_json or 'positions' not in request_json:
            return jsonify({"error": "Positions manquantes"}), 400, CORS_HEADERS
        
        positions = request_json['positions']
        max_bars = request_json.get('max_bars', MAX_BARS_DEFAULT)
        
        if len(positions) < 2:
            return jsonify({"error": "Au moins 2 positions requises"}), 400, CORS_HEADERS

        start_time = time.time()
        print(f"Recherche bars pour {len(positions)} positions")

        # Recherche des bars dans une zone optimisée
        candidate_bars, center_lat, center_lng = search_bars_optimized_zone(positions, max_bars)
        
        if not candidate_bars:
            return jsonify({"error": "Aucun bar trouvé dans la zone optimisée"}), 404, CORS_HEADERS
        
        # Calcul des temps de trajet
        travel_times_results = calculate_travel_times_batch(candidate_bars[:max_bars], positions, max_bars)
        
        if not travel_times_results:
            return jsonify({"error": "Impossible de calculer les temps de trajet"}), 500, CORS_HEADERS
        
        # Clustering des participants proches
        adaptive_cluster_distance = calculate_adaptive_cluster_distance(positions)
        participant_clusters = cluster_nearby_participants(positions, adaptive_cluster_distance)
        
        # Construction et scoring des bars
        bars_with_times = build_bars_with_metrics(candidate_bars, travel_times_results, participant_clusters)
        best_bars = score_and_rank_bars(bars_with_times, max_bars)
        
        # Ajout des marqueurs spéciaux
        add_special_markers(best_bars)
        
        total_time = time.time() - start_time
        print(f"Recherche terminée en {total_time:.2f}s - {len(best_bars)} bars retournés")
        
        return jsonify({
            "success": True,
            "bars": best_bars,
            "center_point": {"lat": center_lat, "lng": center_lng},
            "participant_clusters": len(participant_clusters)
        }), 200, CORS_HEADERS

    except Exception as e:
        print(f"Erreur find_optimal_bars: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, CORS_HEADERS

def build_bars_with_metrics(candidate_bars: List[Dict], travel_times_results: Dict, 
                           participant_clusters: List[List[int]]) -> List[Dict]:
    """Construit la liste des bars avec leurs métriques"""
    bars_with_times = []
    
    for bar_idx, travel_times in travel_times_results.items():
        bar = candidate_bars[bar_idx]
        
        # Calcul des temps par cluster
        cluster_travel_times = []
        for cluster in participant_clusters:
            cluster_times = [travel_times[participant_idx] for participant_idx in cluster]
            cluster_travel_times.append(statistics.mean(cluster_times))
        
        # Métriques basées sur les clusters
        avg_time = statistics.mean(cluster_travel_times)
        std_time = statistics.stdev(cluster_travel_times)
        max_time = max(cluster_travel_times)
        min_time = min(cluster_travel_times)
        time_spread = max_time - min_time
        time_balance_score = time_spread / avg_time if avg_time > 0 else float('inf')
        optimization_score = std_time * avg_time
        
        # Métriques individuelles pour l'affichage
        individual_avg = statistics.mean(travel_times)
        individual_max = max(travel_times)
        individual_min = min(travel_times)
        
        bars_with_times.append({
            'name': bar['name'],
            'address': bar.get('formatted_address', bar.get('vicinity', '')),
            'location': bar['geometry']['location'],
            'rating': bar.get('rating'),
            'price_level': bar.get('price_level'),
            'place_id': bar['place_id'],
            'travel_times': travel_times,
            'cluster_travel_times': cluster_travel_times,
            'avg_travel_time': avg_time,
            'max_travel_time': max_time,
            'min_travel_time': min_time,
            'time_spread': time_spread,
            'time_balance_score': time_balance_score,
            'optimization_score': optimization_score,
            'individual_avg_time': individual_avg,
            'individual_max_time': individual_max,
            'individual_min_time': individual_min
        })
    
    return bars_with_times

def score_and_rank_bars(bars_with_times: List[Dict], max_bars: int) -> List[Dict]:
    """Score et classe les bars par équilibre et qualité"""
    # Filtrer les bars trop déséquilibrés
    balanced_bars = [bar for bar in bars_with_times if bar['time_balance_score'] <= 0.75]
    
    # Si pas assez de bars équilibrés, prendre tous les bars
    if len(balanced_bars) < max_bars:
        balanced_bars = bars_with_times
    
    # Tri par équilibre, temps moyen, puis note
    balanced_bars.sort(key=lambda x: (
        x['time_balance_score'],
        x['avg_travel_time'],
        -x['rating'] if x['rating'] else -1
    ))
    
    return balanced_bars[:max_bars]

def add_special_markers(bars: List[Dict]) -> None:
    """Ajoute des marqueurs spéciaux aux bars remarquables"""
    if not bars:
        return
    
    # Identifier les bars spéciaux
    fastest_bar = min(bars, key=lambda x: x['avg_travel_time'])
    most_balanced_bar = min(bars, key=lambda x: x['time_balance_score'])
    most_optimized_bar = min(bars, key=lambda x: x['optimization_score'])
    
    # Initialiser tous les bars
    for bar in bars:
        bar['marker_types'] = []
        bar['marker_emojis'] = []
    
    # Réorganiser les bars dans l'ordre d'affichage souhaité
    bars.sort(key=lambda x: (
        0 if x == most_optimized_bar else 1,
        0 if x == most_balanced_bar else 1,
        0 if x == fastest_bar else 1
    ))
    
    # Marquer les bars spéciaux
    if most_optimized_bar:
        most_optimized_bar['marker_types'].append('most_optimized')
        most_optimized_bar['marker_emojis'].append('🎯')
    
    if most_balanced_bar:
        most_balanced_bar['marker_types'].append('most_balanced')
        most_balanced_bar['marker_emojis'].append('⚖️')
    
    if fastest_bar:
        fastest_bar['marker_types'].append('fastest')
        fastest_bar['marker_emojis'].append('⚡')
    
    # Finaliser les marqueurs
    for bar in bars:
        if not bar['marker_types']:
            bar['marker_emoji'] = '📍'
            bar['marker_type'] = 'standard'
        elif len(bar['marker_types']) == 1:
            bar['marker_emoji'] = bar['marker_emojis'][0]
            bar['marker_type'] = bar['marker_types'][0]
        else:
            bar['marker_emoji'] = ''.join(bar['marker_emojis'])
            bar['marker_type'] = 'fastest_and_balanced'
        
        # Nettoyer les propriétés temporaires
        del bar['marker_types']
        del bar['marker_emojis']


def calculate_adaptive_cluster_distance(positions: List[Dict]) -> float:
    """Calcule une distance de clustering adaptative basée sur la dispersion du groupe"""
    try:
        if len(positions) <= 2:
            return 0.4  # 400m pour 2 personnes ou moins
        
        # Calculer toutes les distances entre participants
        distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                pos1 = positions[i]['location']
                pos2 = positions[j]['location']
                distance_km = calculate_distance_km(pos1['lat'], pos1['lng'], pos2['lat'], pos2['lng'])
                distances.append(distance_km)
        
        if not distances:
            return DEFAULT_CLUSTER_DISTANCE
        
        avg_distance = statistics.mean(distances)
        min_distance = min(distances)
        
        # Distance de clustering adaptative
        if avg_distance < 1.0:
            # Groupe compact
            adaptive_distance = max(0.3, min(0.6, min_distance * 1.5))
        elif avg_distance < 3.0:
            # Groupe moyen
            adaptive_distance = max(0.4, min(1.0, avg_distance * 0.3))
        else:
            # Groupe dispersé
            adaptive_distance = max(0.8, min(1.5, avg_distance * 0.25))
        
        print(f"Clustering adaptatif: distance moy={avg_distance:.1f}km, seuil={adaptive_distance:.1f}km")
        return adaptive_distance
        
    except Exception as e:
        print(f"Erreur calcul clustering: {e}")
        return DEFAULT_CLUSTER_DISTANCE

def cluster_nearby_participants(positions: List[Dict], distance_threshold_km: float = DEFAULT_CLUSTER_DISTANCE) -> List[List[int]]:
    """Regroupe les participants proches géographiquement"""
    try:
        clusters = []
        assigned = [False] * len(positions)
        
        for i, pos in enumerate(positions):
            if assigned[i]:
                continue
                
            # Créer un nouveau cluster
            cluster = [i]
            assigned[i] = True
            pos_location = pos['location']
            
            # Chercher les positions proches
            for j, other_pos in enumerate(positions):
                if assigned[j] or i == j:
                    continue
                    
                other_location = other_pos['location']
                distance_km = calculate_distance_km(
                    pos_location['lat'], pos_location['lng'],
                    other_location['lat'], other_location['lng']
                )
                
                if distance_km <= distance_threshold_km:
                    cluster.append(j)
                    assigned[j] = True
            
            clusters.append(cluster)
        
        print(f"Clustering: {len(clusters)} groupes formés à partir de {len(positions)} participants")
        return clusters
        
    except Exception as e:
        print(f"Erreur clustering: {e}")
        return [[i] for i in range(len(positions))]


def search_bars_optimized_zone(positions: List[Dict], max_bars: int = MAX_BARS_DEFAULT) -> Tuple[List[Dict], float, float]:
    """Recherche des bars dans une zone optimisée basée sur la géométrie du groupe"""
    try:
        # Calculer les coordonnées de base
        lats = [pos['location']['lat'] for pos in positions]
        lngs = [pos['location']['lng'] for pos in positions]
        
        # Trouver le centre optimal pour minimiser les temps de trajet
        center_lat, center_lng = find_optimal_center(positions, lats, lngs)
        
        # Calculer le rayon adaptatif
        adaptive_radius = calculate_adaptive_radius(positions, center_lat, center_lng)
        
        print(f"Zone optimisée: centre=({center_lat:.4f},{center_lng:.4f}), rayon={adaptive_radius:.0f}m")
        
        # Rechercher avec retry automatique
        candidate_bars = search_bars_with_retry(center_lat, center_lng, adaptive_radius, max_bars)
        
        # Filtrage intelligent si trop de candidats
        if len(candidate_bars) > max_bars:
            candidate_bars = filter_bars_by_equity(candidate_bars, positions, max_bars)
        
        return candidate_bars, center_lat, center_lng
        
    except Exception as e:
        print(f"Erreur recherche optimisée: {e}")
        # Fallback vers l'ancienne méthode
        center_lat = statistics.mean(lats)
        center_lng = statistics.mean(lngs)
        bars = search_bars_nearby(center_lat, center_lng, 2000, max_bars)
        return bars, center_lat, center_lng

def find_optimal_center(positions: List[Dict], lats: List[float], lngs: List[float]) -> Tuple[float, float]:
    """Trouve le centre optimal pour minimiser la variance des temps de trajet"""
    center_lat = statistics.mean(lats)
    center_lng = statistics.mean(lngs)
    
    # Calculer la dispersion pour déterminer la taille de la grille de recherche
    max_distance = 0
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            pos1 = positions[i]['location']
            pos2 = positions[j]['location']
            distance = ((pos2['lat'] - pos1['lat']) ** 2 + (pos2['lng'] - pos1['lng']) ** 2) ** 0.5
            max_distance = max(max_distance, distance)
    
    search_grid_size = max(max_distance * 50, 0.002)  # ~200m en degrés
    best_center_lat, best_center_lng = center_lat, center_lng
    min_time_variance = float('inf')
    
    # Tester une grille 3x3 autour du centre géométrique
    for lat_offset in [-search_grid_size, 0, search_grid_size]:
        for lng_offset in [-search_grid_size, 0, search_grid_size]:
            test_lat = center_lat + lat_offset
            test_lng = center_lng + lng_offset
            
            # Calculer la variance des temps estimés pour ce point
            estimated_times = []
            for pos in positions:
                participant_lat = pos['location']['lat']
                participant_lng = pos['location']['lng']
                distance_km = calculate_distance_km(test_lat, test_lng, participant_lat, participant_lng)
                
                transport_mode = TRANSPORT_MODE_MAPPING.get(pos.get('transportMode', 'walking'), 'walking')
                estimated_time = estimate_travel_time(distance_km, transport_mode)
                estimated_times.append(estimated_time)
            
            if len(estimated_times) > 1:
                time_variance = statistics.variance(estimated_times)
                if time_variance < min_time_variance:
                    min_time_variance = time_variance
                    best_center_lat, best_center_lng = test_lat, test_lng
    
    print(f"Centre optimal: variance temps {min_time_variance:.2f}")
    return best_center_lat, best_center_lng

def calculate_adaptive_radius(positions: List[Dict], center_lat: float, center_lng: float) -> float:
    """Calcule le rayon adaptatif basé sur la distance maximale au centre"""
    max_distance_km = 0
    for position in positions:
        pos_lat = position['location']['lat']
        pos_lng = position['location']['lng']
        distance_km = calculate_distance_km(center_lat, center_lng, pos_lat, pos_lng)
        max_distance_km = max(max_distance_km, distance_km)
    
    # Convertir en mètres avec minimum pratique
    adaptive_radius = max(max_distance_km * 1000, MIN_SEARCH_RADIUS)
    print(f"Rayon adaptatif: {adaptive_radius:.0f}m (distance max au centre: {max_distance_km:.1f}km)")
    return adaptive_radius

def search_bars_with_retry(lat: float, lng: float, radius: float, max_bars: int) -> List[Dict]:
    """Recherche des bars avec retry automatique si aucun résultat"""
    candidate_bars = search_bars_nearby(lat, lng, radius, max_bars)
    
    retry_count = 0
    while len(candidate_bars) == 0 and retry_count < 2:
        retry_count += 1
        expanded_radius = radius * (1.5 if retry_count == 1 else 2.5)
        print(f"Retry {retry_count}/2 avec rayon élargi: {expanded_radius:.0f}m")
        candidate_bars = search_bars_nearby(lat, lng, expanded_radius, max_bars)
    
    print(f"Bars trouvés après {retry_count + 1} tentative(s): {len(candidate_bars)}")
    return candidate_bars

def filter_bars_by_equity(bars: List[Dict], positions: List[Dict], max_bars: int) -> List[Dict]:
    """Filtre les bars par équité géographique et qualité"""
    scored_bars = []
    
    for bar in bars:
        bar_lat = bar['geometry']['location']['lat']
        bar_lng = bar['geometry']['location']['lng']
        
        # Calculer les distances à tous les participants
        distances = []
        for pos in positions:
            participant_lat = pos['location']['lat']
            participant_lng = pos['location']['lng']
            distance_km = calculate_distance_km(bar_lat, bar_lng, participant_lat, participant_lng)
            distances.append(distance_km)
        
        # Métriques d'équité
        avg_distance = statistics.mean(distances)
        max_distance = max(distances)
        min_distance = min(distances)
        distance_spread = max_distance - min_distance
        
        # Score d'équité géographique
        equity_score = distance_spread / avg_distance if avg_distance > 0 else float('inf')
        
        # Bonus qualité
        rating = bar.get('rating', 3.0)
        quality_bonus = (rating - 3.0) * 0.1
        
        # Score composite
        composite_score = equity_score - quality_bonus + avg_distance * 0.1
        
        bar['_composite_score'] = composite_score
        scored_bars.append(bar)
    
    # Trier par score composite
    scored_bars.sort(key=lambda x: x['_composite_score'])
    filtered_bars = scored_bars[:max_bars]
    
    print(f"Filtrage équilibré: gardé {len(filtered_bars)} bars")
    return filtered_bars


def search_bars_nearby(lat: float, lng: float, radius: float, max_bars: int = MAX_BARS_DEFAULT) -> List[Dict]:
    """Recherche les bars autour d'un point avec filtrage intelligent"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius': int(radius),
            'type': 'bar',
            'keyword': 'bar pub cocktail bière',
            'key': GOOGLE_MAPS_API_KEY,
            'language': 'fr'
        }
        
        all_bars = []
        next_page_token = None
        page_count = 0
        
        # Récupérer jusqu'à MAX_SEARCH_PAGES pages
        while len(all_bars) < max_bars and page_count < MAX_SEARCH_PAGES:
            if next_page_token:
                params['pagetoken'] = next_page_token
                time.sleep(PAGE_TOKEN_DELAY)  # Attente requise par l'API
            
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        
            if data['status'] == 'OK':
                # Filtrer pour garder seulement les vrais bars
                page_bars = filter_real_bars(data['results'])
                all_bars.extend(page_bars[:max_bars - len(all_bars)])
                
                next_page_token = data.get('next_page_token')
                if not next_page_token:
                    break
            else:
                print(f"API Error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                break
            
            page_count += 1
        
        return all_bars
            
    except Exception as e:
        print(f"Erreur recherche bars: {e}")
        return []

def filter_real_bars(places: List[Dict]) -> List[Dict]:
    """Filtre pour garder seulement les vrais bars en excluant les hôtels"""
    filtered_bars = []
    
    for place in places:
        place_types = place.get('types', [])
        place_name = place.get('name', '').lower()
        
        # Exclure les hôtels
        is_hotel = ('lodging' in place_types or 
                   any(keyword in place_name for keyword in ['hotel', 'hôtel', 'auberge', 'resort']))
        
        # Inclure seulement les vrais bars
        is_real_bar = ('bar' in place_types or 
                      'night_club' in place_types or
                      any(keyword in place_name for keyword in ['bar', 'pub', 'café', 'brasserie']))
        
        if is_real_bar and not is_hotel:
            filtered_bars.append(place)
    
    return filtered_bars


def calculate_travel_times_batch(bars: List[Dict], positions: List[Dict], max_bars: int = MAX_BARS_DEFAULT) -> Dict[int, List[float]]:
    """Calcule les temps de trajet pour tous les bars et positions en groupant par mode de transport"""
    try:
        if not bars or not positions:
            return {}
        
        # Limiter le nombre de bars pour respecter les limites API
        max_bars_to_process = min(max_bars, len(bars))
        limited_bars = bars[:max_bars_to_process]
        print(f"Traitement de {len(limited_bars)} bars pour {len(positions)} positions")
        
        # Grouper les positions par mode de transport
        transport_groups = group_positions_by_transport(positions)
        
        # Préparer les destinations (bars)
        destinations = prepare_destinations(limited_bars)
        
        # Calculer les temps de trajet par groupe de transport
        all_travel_times = process_transport_groups(transport_groups, destinations, positions)
        
        # Construire les résultats finaux par bar
        return build_final_results(all_travel_times, len(limited_bars), len(positions))
        
    except Exception as e:
        print(f"Erreur calcul batch: {e}")
        return {}

def group_positions_by_transport(positions: List[Dict]) -> Dict[str, List[Dict]]:
    """Groupe les positions par mode de transport"""
    transport_groups = {}
    
    for idx, position in enumerate(positions):
        transport_mode = position.get('transportMode', 'walking')
        google_mode = TRANSPORT_MODE_MAPPING.get(transport_mode, 'walking')
        
        if google_mode not in transport_groups:
            transport_groups[google_mode] = []
        
        transport_groups[google_mode].append({
            'index': idx,
            'position': position,
            'origin': f"{position['location']['lat']},{position['location']['lng']}"
        })
    
    return transport_groups

def prepare_destinations(bars: List[Dict]) -> List[str]:
    """Prépare la liste des destinations (bars) pour l'API"""
    destinations = []
    for bar in bars:
        bar_location = bar['geometry']['location']
        destination = f"{bar_location['lat']},{bar_location['lng']}"
        destinations.append(destination)
    return destinations

def process_transport_groups(transport_groups: Dict[str, List[Dict]], destinations: List[str], 
                           positions: List[Dict]) -> List[Optional[List[float]]]:
    """Traite chaque groupe de transport et calcule les temps de trajet"""
    all_travel_times = [None] * len(positions)
    
    for transport_mode, group_positions in transport_groups.items():
        origins = [pos_info['origin'] for pos_info in group_positions]
        
        # Respecter la limite de 5 origines
        if len(origins) > MAX_API_ORIGINS:
            print(f"Limitation de {len(origins)} à {MAX_API_ORIGINS} origines pour {transport_mode}")
            origins = origins[:MAX_API_ORIGINS]
            group_positions = group_positions[:MAX_API_ORIGINS]
        
        # Traiter par chunks de destinations
        process_destination_chunks(transport_mode, origins, group_positions, destinations, all_travel_times)
    
    return all_travel_times

def process_destination_chunks(transport_mode: str, origins: List[str], group_positions: List[Dict],
                             destinations: List[str], all_travel_times: List[Optional[List[float]]]) -> None:
    """Traite les destinations par chunks pour respecter les limites API"""
    request_count = 0
    
    for dest_start in range(0, len(destinations), MAX_API_DESTINATIONS):
        dest_end = min(dest_start + MAX_API_DESTINATIONS, len(destinations))
        chunk_destinations = destinations[dest_start:dest_end]
        request_count += 1
        
        if len(origins) > MAX_API_ORIGINS or len(chunk_destinations) > MAX_API_DESTINATIONS:
            print(f"ERREUR: Dépassement limites API - {len(origins)}×{len(chunk_destinations)}")
            continue
        
        print(f"Requête {request_count} pour {transport_mode}: {len(origins)}×{len(chunk_destinations)}")
        
        # Appel à l'API Distance Matrix
        try:
            data = call_distance_matrix_api(origins, chunk_destinations, transport_mode)
            if data and data['status'] == 'OK':
                parse_distance_matrix_results(data, group_positions, all_travel_times, dest_start)
        except Exception as e:
            print(f"Erreur requête Distance Matrix: {e}")

def call_distance_matrix_api(origins: List[str], destinations: List[str], transport_mode: str) -> Optional[Dict]:
    """Appelle l'API Distance Matrix de Google"""
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
    
    response = requests.get(url, params=params, timeout=API_TIMEOUT)
    response.raise_for_status()
    return response.json()

def parse_distance_matrix_results(data: Dict, group_positions: List[Dict], 
                                all_travel_times: List[Optional[List[float]]], dest_start: int) -> None:
    """Parse les résultats de l'API Distance Matrix"""
    for person_idx_in_group, pos_info in enumerate(group_positions):
        original_person_idx = pos_info['index']
        
        if all_travel_times[original_person_idx] is None:
            all_travel_times[original_person_idx] = [None] * len(data['destination_addresses'])
        
        for chunk_bar_idx, element in enumerate(data['rows'][person_idx_in_group]['elements']):
            actual_bar_idx = dest_start + chunk_bar_idx
            
            if element['status'] == 'OK':
                duration_minutes = element['duration']['value'] / 60
                if len(all_travel_times[original_person_idx]) <= actual_bar_idx:
                    # Étendre la liste si nécessaire
                    all_travel_times[original_person_idx].extend([None] * (actual_bar_idx + 1 - len(all_travel_times[original_person_idx])))
                all_travel_times[original_person_idx][actual_bar_idx] = duration_minutes

def build_final_results(all_travel_times: List[Optional[List[float]]], num_bars: int, num_positions: int) -> Dict[int, List[float]]:
    """Construit les résultats finaux par bar"""
    final_results = {}
    
    for bar_idx in range(num_bars):
        travel_times_for_bar = []
        valid_times = True
        
        for person_idx in range(num_positions):
            if (all_travel_times[person_idx] is not None and 
                bar_idx < len(all_travel_times[person_idx]) and
                all_travel_times[person_idx][bar_idx] is not None):
                travel_times_for_bar.append(all_travel_times[person_idx][bar_idx])
            else:
                valid_times = False
                break
        
        if valid_times and len(travel_times_for_bar) == num_positions:
            final_results[bar_idx] = travel_times_for_bar
    
    return final_results