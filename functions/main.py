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
        max_bars = request_json.get('max_bars', 8)
        search_radius = min(request_json.get('search_radius', 400), 2500)  # Élargi jusqu'à 2.5km pour permettre les extensions
        
        if len(positions) < 2:
            return jsonify({"error": "Au moins 2 positions requises"}), 400, headers

        start_time = time.time()
        print(f"Début recherche bars pour {len(positions)} positions")

        # Calculer le point central optimal
        center_lat = statistics.mean([pos['location']['lat'] for pos in positions])
        center_lng = statistics.mean([pos['location']['lng'] for pos in positions])
        
        # Rechercher un grand nombre de bars candidats dans un rayon plus large
        search_start = time.time()
        extended_radius = max(search_radius * 2, 2000)  # Minimum 2km pour avoir plus de choix
        candidate_bars = search_bars_nearby(center_lat, center_lng, extended_radius, max_bars=100)  # Plus de choix avec limite API 100
        search_time = time.time() - search_start
        print(f"Recherche bars terminée: {len(candidate_bars)} bars trouvés en {search_time:.2f}s")
        
        if not candidate_bars:
            return jsonify({"error": "Aucun bar trouvé dans la zone étendue"}), 404, headers
        
        # Pré-filtrage des bars pour optimiser les calculs
        filter_start = time.time()
        # 1. Filtrer par note d'abord (optionnel mais améliore la qualité)
        quality_filtered_bars = []
        for bar in candidate_bars:
            # Garder les bars avec une note décente OU sans note (nouveaux bars)
            if not bar.get('rating') or bar.get('rating') >= 3.0:
                quality_filtered_bars.append(bar)
        
        # Si pas assez de bars avec notes, prendre tous les candidats
        if len(quality_filtered_bars) < 20:
            quality_filtered_bars = candidate_bars
        
        # 2. Prioriser les bars les plus proches du centre pour optimiser les temps
        for bar in quality_filtered_bars:
            bar_location = bar['geometry']['location']
            # Calculer distance approximative au centre
            distance_to_center = ((bar_location['lat'] - center_lat) ** 2 + 
                                 (bar_location['lng'] - center_lng) ** 2) ** 0.5
            bar['_distance_to_center'] = distance_to_center
        
        # Trier par distance au centre et adapter le nombre selon les positions
        quality_filtered_bars.sort(key=lambda x: x['_distance_to_center'])
        max_candidates = min(80, 90 // len(positions))  # Adapter selon le nombre de positions
        final_candidate_bars = quality_filtered_bars[:max_candidates]
        filter_time = time.time() - filter_start
        print(f"Filtrage terminé: {len(final_candidate_bars)} bars retenus en {filter_time:.2f}s")
        
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
        
        # Nouveau système de scoring basé uniquement sur les temps de trajet
        # 1. Filtrer les bars avec un déséquilibre trop important (> 50% du temps moyen)
        balanced_bars = [bar for bar in bars_with_times if bar['time_balance_score'] <= 0.5]
        
        # Si pas assez de bars équilibrés, prendre les meilleurs même s'ils sont déséquilibrés
        if len(balanced_bars) < max_bars:
            balanced_bars = bars_with_times
        
        # 2. Trier par temps moyen croissant (priorité absolue)
        # Puis par score de déséquilibre croissant (pour départager)
        balanced_bars.sort(key=lambda x: (
            x['avg_travel_time'],          # Temps moyen croissant (priorité 1)
            x['time_balance_score']        # Déséquilibre croissant (priorité 2)
        ))
        
        # Prendre les 8 meilleurs bars
        best_bars = balanced_bars[:max_bars]
        
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


def search_bars_nearby(lat, lng, radius, max_bars=100):
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
        max_pages = 3  # Limiter à 3 pages max pour éviter trop d'attente
        page_count = 0
        
        # Récupérer plusieurs pages de résultats pour avoir plus de bars candidats
        while len(all_bars) < max_bars and page_count < max_pages:
            if next_page_token:
                params['pagetoken'] = next_page_token
                # Attendre le minimum requis par l'API (2s) mais pas plus
                time.sleep(2)
            
            response = requests.get(url, params=params, timeout=15)  # Timeout réduit
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
        # Adapter le nombre selon les positions pour respecter la limite API de 100 éléments
        max_bars_to_process = min(80, 90 // len(positions))  # Garder une marge de sécurité
        limited_bars = bars[:max_bars_to_process]
        print(f"Traitement de {len(limited_bars)} bars pour {len(positions)} positions")
        
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
            # Traiter les requêtes par batch pour respecter les limites API (100 éléments max par requête)
            origins = [pos_info['origin'] for pos_info in group_positions]
            
            # Calculer le nombre max de destinations par requête en fonction du nombre d'origines
            # Limite API: origines × destinations ≤ 100
            max_destinations_per_request = 100 // len(origins) if origins else 0
            
            if max_destinations_per_request == 0:
                print(f"Trop d'origines ({len(origins)}) pour le mode {transport_mode}")
                continue
            
            print(f"Mode {transport_mode}: {len(origins)} origines, max {max_destinations_per_request} destinations par requête")
            
            # Découper les destinations par chunks selon la limite calculée
            for dest_start in range(0, len(destinations), max_destinations_per_request):
                dest_end = min(dest_start + max_destinations_per_request, len(destinations))
                chunk_destinations = destinations[dest_start:dest_end]
                
                # Vérification de sécurité
                total_elements = len(origins) * len(chunk_destinations)
                if total_elements > 100:
                    print(f"ERREUR: Tentative de requête avec {total_elements} éléments (limit: 100)")
                    continue
                
                print(f"Requête API: {len(origins)} origines × {len(chunk_destinations)} destinations = {total_elements} éléments")
                
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
                    response = requests.get(url, params=params, timeout=25)  # Timeout optimisé
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