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
        # Vérification du token
        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            return jsonify({"error": "Token d'authentification manquant"}), 401, headers

        id_token = authorization.split(' ')[1]
        
        # Vérification du token Firebase
        try:
            decoded_token = auth.verify_id_token(id_token)
        except Exception as e:
            return jsonify({"error": "Token invalide"}), 401, headers
        
        # Récupération des données
        request_json = request.get_json(silent=True)
        
        if not request_json or 'positions' not in request_json:
            return jsonify({"error": "Positions manquantes"}), 400, headers
        
        positions = request_json['positions']
        max_bars = request_json.get('max_bars', 25)  # Augmenté pour profiter de la limite API
        search_radius = min(request_json.get('search_radius', 400), 2500)  # Élargi jusqu'à 2.5km pour permettre les extensions
        
        if len(positions) < 2:
            return jsonify({"error": "Au moins 2 positions requises"}), 400, headers

        start_time = time.time()
        print(f"Début recherche bars pour {len(positions)} positions")

        # Calculer une zone de recherche optimisée basée sur la géométrie du groupe
        search_start = time.time()
        candidate_bars, center_lat, center_lng = search_bars_optimized_zone(positions, search_radius)
        search_time = time.time() - search_start
        print(f"Recherche bars terminée: {len(candidate_bars)} bars trouvés en {search_time:.2f}s")
        
        if not candidate_bars:
            return jsonify({"error": "Aucun bar trouvé dans la zone optimisée"}), 404, headers
        
        # Les bars sont déjà optimisés et filtrés par la nouvelle fonction
        # Limitation finale à 25 bars maximum pour respecter l'API
        final_candidate_bars = candidate_bars[:25]
        print(f"Bars finaux sélectionnés: {len(final_candidate_bars)} bars pour calcul des temps")
        
        # Calculer les temps de trajet pour les bars sélectionnés
        travel_start = time.time()
        travel_times_results = calculate_travel_times_batch(final_candidate_bars, positions)
        travel_time = time.time() - travel_start
        print(f"Calcul temps de trajet terminé: {len(travel_times_results)} bars avec temps en {travel_time:.2f}s")
        
        # Construire la liste des bars avec leurs métriques de temps de trajet
        bars_with_times = []
        for bar_idx, travel_times in travel_times_results.items():
            bar = final_candidate_bars[bar_idx]
            
            # Calculer les métriques de temps
            avg_time = statistics.mean(travel_times)
            max_time = max(travel_times)
            min_time = min(travel_times)
            time_spread = max_time - min_time  # Écart entre le plus long et le plus court
            
            # Calculer un score de déséquilibre (plus c'est bas, mieux c'est)
            # Si tous les temps sont similaires, le déséquilibre est faible
            time_balance_score = time_spread / avg_time if avg_time > 0 else float('inf')
            
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
                'min_travel_time': min_time,
                'time_spread': time_spread,
                'time_balance_score': time_balance_score
            })
        
        if not bars_with_times:
            return jsonify({"error": "Impossible de calculer les temps de trajet"}), 500, headers
        
        # Nouveau système de scoring basé sur l'équilibre des temps de trajet
        # 1. Filtrer les bars avec un déséquilibre trop important (> 75% du temps moyen)
        balanced_bars = [bar for bar in bars_with_times if bar['time_balance_score'] <= 0.75]
        
        # Si pas assez de bars équilibrés, prendre les meilleurs même s'ils sont déséquilibrés
        if len(balanced_bars) < max_bars:
            balanced_bars = bars_with_times
        
        # 2. Nouveau tri : écart de temps (croissant) -> temps moyen (croissant) -> note (décroissant)
        balanced_bars.sort(key=lambda x: (
            x['time_balance_score'],       # Équilibre croissant (priorité 1) - plus équilibré = mieux
            x['avg_travel_time'],          # Temps moyen croissant (priorité 2) - plus court = mieux
            -x['rating'] if x['rating'] else -1  # Note décroissante (priorité 3) - meilleure note = mieux
        ))
        
        # Retourner autant de bars que possible (jusqu'à 25 avec la limite API)
        best_bars = balanced_bars[:min(max_bars, len(balanced_bars))]
        
        total_time = time.time() - start_time
        print(f"Recherche complète terminée en {total_time:.2f}s - {len(best_bars)} bars retournés")
        
        return jsonify({
            "success": True,
            "bars": best_bars,
            "center_point": {"lat": center_lat, "lng": center_lng}
        }), 200, headers

    except auth.InvalidIdTokenError as e:
        return jsonify({"error": "Token invalide"}), 401, headers
    except ValueError as e:
        return jsonify({"error": str(e)}), 400, headers
    except Exception as e:
        print(f"ERROR: Exception non gérée dans find_optimal_bars: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers


def search_bars_optimized_zone(positions, base_radius):
    """Recherche des bars dans une zone optimisée basée sur la géométrie du groupe"""
    try:
        # 1. Analyser la dispersion géographique du groupe
        lats = [pos['location']['lat'] for pos in positions]
        lngs = [pos['location']['lng'] for pos in positions]
        
        # Calculer les limites géographiques du groupe
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        
        # Calculer la dispersion du groupe (distance max entre participants)
        max_distance = 0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                lat1, lng1 = positions[i]['location']['lat'], positions[i]['location']['lng']
                lat2, lng2 = positions[j]['location']['lat'], positions[j]['location']['lng']
                # Distance euclidienne approximative (suffisante pour la comparaison)
                distance = ((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2) ** 0.5
                max_distance = max(max_distance, distance)
        
        # 2. Calculer le point central pondéré (geometric median approximé)
        center_lat = statistics.mean(lats)
        center_lng = statistics.mean(lngs)
        
        # Affiner le centre en calculant le point qui minimise la somme des distances
        # (Algorithme de Weiszfeld simplifié)
        for iteration in range(3):  # Quelques itérations suffisent
            total_weight = 0
            weighted_lat = 0
            weighted_lng = 0
            
            for pos in positions:
                lat, lng = pos['location']['lat'], pos['location']['lng']
                # Distance au centre actuel
                dist = ((lat - center_lat) ** 2 + (lng - center_lng) ** 2) ** 0.5
                if dist > 0:
                    weight = 1 / dist  # Poids inversement proportionnel à la distance
                    weighted_lat += lat * weight
                    weighted_lng += lng * weight
                    total_weight += weight
            
            if total_weight > 0:
                center_lat = weighted_lat / total_weight
                center_lng = weighted_lng / total_weight
        
        # 3. Calculer un rayon adaptatif basé sur la dispersion
        # Le rayon doit couvrir une zone où tous peuvent se retrouver équitablement
        group_span_km = max_distance * 111  # Conversion approximative degrés -> km
        adaptive_radius = max(
            base_radius,
            group_span_km * 300,  # 30% de la distance max du groupe
            800  # Minimum 800m pour avoir des choix
        )
        adaptive_radius = min(adaptive_radius, 2000)  # Maximum 2km pour éviter trop de dispersion
        
        print(f"Zone optimisée: centre=({center_lat:.4f},{center_lng:.4f}), rayon={adaptive_radius:.0f}m, dispersion_groupe={group_span_km:.1f}km")
        
        # 4. Rechercher dans la zone optimisée
        candidate_bars = search_bars_nearby(center_lat, center_lng, adaptive_radius, max_bars=50)
        
        # 5. Filtrage supplémentaire basé sur la distance aux participants extrêmes
        if len(candidate_bars) > 25:  # Si trop de candidats, filtrer plus finement
            # Calculer pour chaque bar sa distance aux participants les plus éloignés
            filtered_bars = []
            for bar in candidate_bars:
                bar_lat = bar['geometry']['location']['lat']
                bar_lng = bar['geometry']['location']['lng']
                
                # Calculer la distance max du bar à tous les participants
                max_distance_to_participants = 0
                for pos in positions:
                    participant_lat = pos['location']['lat']
                    participant_lng = pos['location']['lng']
                    distance = ((bar_lat - participant_lat) ** 2 + 
                               (bar_lng - participant_lng) ** 2) ** 0.5
                    max_distance_to_participants = max(max_distance_to_participants, distance)
                
                bar['_max_distance_to_participants'] = max_distance_to_participants
                filtered_bars.append(bar)
            
            # Trier par distance maximale aux participants (plus équitable)
            filtered_bars.sort(key=lambda x: x['_max_distance_to_participants'])
            candidate_bars = filtered_bars[:25]  # Limiter à 25 pour l'API
        
        return candidate_bars, center_lat, center_lng
        
    except Exception as e:
        print(f"Erreur recherche optimisée: {e}")
        # Fallback vers l'ancienne méthode
        center_lat = statistics.mean([pos['location']['lat'] for pos in positions])
        center_lng = statistics.mean([pos['location']['lng'] for pos in positions])
        bars = search_bars_nearby(center_lat, center_lng, max(base_radius * 2, 2000), max_bars=25)
        return bars, center_lat, center_lng


def search_bars_nearby(lat, lng, radius, max_bars=50):
    """Recherche les bars autour d'un point avec possibilité de récupérer plus de résultats"""
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
        
        all_bars = []
        next_page_token = None
        max_pages = 2  # Réduire à 2 pages pour optimiser le temps
        page_count = 0
        
        # Récupérer plusieurs pages de résultats pour avoir plus de bars candidats
        while len(all_bars) < max_bars and page_count < max_pages:
            if next_page_token:
                params['pagetoken'] = next_page_token
                # Attendre le minimum requis par l'API (2s) mais pas plus
                time.sleep(2)
            
            response = requests.get(url, params=params, timeout=12)  # Timeout réduit
            response.raise_for_status()
            data = response.json()
        
            if data['status'] == 'OK':
                # Filtrer pour exclure les hôtels et autres établissements
                page_bars = []
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
                        page_bars.append(place)
                
                # Ajouter les bars de cette page
                all_bars.extend(page_bars[:max_bars - len(all_bars)])
                
                # Vérifier s'il y a une page suivante
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


def calculate_travel_times_batch(bars, positions):
    """Calcule les temps de trajet pour tous les bars et positions en groupant par mode de transport"""
    try:
        if not bars or not positions:
            return {}
        
        # Optimisation : limiter dès le début pour éviter trop de calculs
        # Adapter le nombre selon les positions pour respecter la limite API de 25x25
        # Limite réelle : 25 origines × 25 destinations maximum
        max_bars_to_process = min(25, len(bars))  # Maximum 25 destinations
        limited_bars = bars[:max_bars_to_process]
        print(f"Traitement de {len(limited_bars)} bars pour {len(positions)} positions (limite API: 25×25)")
        
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
        
        # Préparer toutes les destinations (bars)
        destinations = []
        for bar in limited_bars:
            bar_location = bar['geometry']['location']
            destination = f"{bar_location['lat']},{bar_location['lng']}"
            destinations.append(destination)
        
        # Faire une requête par groupe de transport avec gestion des limites API
        all_travel_times = [None] * len(positions)  # Index par position originale
        
        for transport_mode, group_positions in transport_groups.items():
            # Traiter les requêtes par batch pour respecter les limites API (25×25 max)
            origins = [pos_info['origin'] for pos_info in group_positions]
            
            # Vérifier que nous ne dépassons pas 25 origines
            if len(origins) > 25:
                print(f"Trop d'origines ({len(origins)}) pour le mode {transport_mode}, limitation à 25")
                origins = origins[:25]
                group_positions = group_positions[:25]
            
            # Calculer le nombre max de destinations par requête (25 max)
            max_destinations_per_request = min(25, len(destinations))
            
            print(f"Mode {transport_mode}: {len(origins)} origines, max {max_destinations_per_request} destinations par requête")
            
            # Découper les destinations par chunks de 25 maximum
            request_count = 0
            for dest_start in range(0, len(destinations), max_destinations_per_request):
                dest_end = min(dest_start + max_destinations_per_request, len(destinations))
                chunk_destinations = destinations[dest_start:dest_end]
                request_count += 1
                
                # Vérification de sécurité pour 25×25
                if len(origins) > 25 or len(chunk_destinations) > 25:
                    print(f"ERREUR: Dépassement limites API - {len(origins)} origines × {len(chunk_destinations)} destinations")
                    continue
                
                print(f"Requête {request_count} pour {transport_mode}: {len(origins)} origines × {len(chunk_destinations)} destinations")
                
                # Appel à l'API Distance Matrix pour ce chunk
                url = "https://maps.googleapis.com/maps/api/distancematrix/json"
                params = {
                    'origins': '|'.join(origins),
                    'destinations': '|'.join(chunk_destinations),
                    'mode': transport_mode,
                    'language': 'fr',
                    'key': GOOGLE_MAPS_API_KEY
                }
                
                if transport_mode == 'transit':
                    params['departure_time'] = 'now'
                
                try:
                    response = requests.get(url, params=params, timeout=20)  # Timeout optimisé pour éviter timeouts
                    response.raise_for_status()
                    data = response.json()
                    
                    if data['status'] != 'OK':
                        print(f"API Error pour {transport_mode}: {data.get('status')} - {data.get('error_message', '')}")
                        continue
                    
                    # Parser les résultats pour ce chunk
                    for person_idx_in_group, pos_info in enumerate(group_positions):
                        original_person_idx = pos_info['index']
                        
                        # Initialiser la liste des temps si pas encore fait
                        if all_travel_times[original_person_idx] is None:
                            all_travel_times[original_person_idx] = [None] * len(limited_bars)
                        
                        for chunk_bar_idx in range(len(chunk_destinations)):
                            actual_bar_idx = dest_start + chunk_bar_idx
                            try:
                                element = data['rows'][person_idx_in_group]['elements'][chunk_bar_idx]
                                if element['status'] == 'OK':
                                    duration_minutes = element['duration']['value'] / 60
                                    all_travel_times[original_person_idx][actual_bar_idx] = duration_minutes
                            except (KeyError, IndexError) as e:
                                # Garder None pour ce bar/personne
                                pass
                
                except requests.RequestException as e:
                    print(f"Erreur requête Distance Matrix: {e}")
                    continue
        
        # Construire les résultats finaux par bar
        final_results = {}
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
        
        return final_results
        
    except Exception as e:
        print(f"Erreur calcul batch: {e}")
        return {}