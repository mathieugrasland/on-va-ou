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
        
        if len(positions) < 2:
            return jsonify({"error": "Au moins 2 positions requises"}), 400, headers

        start_time = time.time()
        print(f"Début recherche bars pour {len(positions)} positions (rayon adaptatif)")

        # Calculer une zone de recherche optimisée basée sur la géométrie du groupe
        search_start = time.time()
        candidate_bars, center_lat, center_lng = search_bars_optimized_zone(positions)
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
        
        # Identifier les clusters de participants proches pour pondérer le scoring
        # Calculer une distance de clustering adaptative basée sur la dispersion du groupe
        adaptive_cluster_distance = calculate_adaptive_cluster_distance(positions)
        participant_clusters = cluster_nearby_participants(positions, distance_threshold_km=adaptive_cluster_distance)
        
        # Construire la liste des bars avec leurs métriques de temps de trajet pondérées
        bars_with_times = []
        for bar_idx, travel_times in travel_times_results.items():
            bar = final_candidate_bars[bar_idx]
            
            # Calculer les temps de trajet consolidés par cluster
            cluster_travel_times = []
            for cluster in participant_clusters:
                # Pour chaque cluster, prendre le temps moyen des participants du cluster
                cluster_times = [travel_times[participant_idx] for participant_idx in cluster]
                cluster_avg_time = statistics.mean(cluster_times)
                cluster_travel_times.append(cluster_avg_time)
            
            # Calculer les métriques basées sur les clusters (pas les participants individuels)
            avg_time = statistics.mean(cluster_travel_times)
            max_time = max(cluster_travel_times)
            min_time = min(cluster_travel_times)
            time_spread = max_time - min_time  # Écart entre clusters, pas entre individus
            
            # Score d'équilibre basé sur les clusters
            time_balance_score = time_spread / avg_time if avg_time > 0 else float('inf')
            
            # Garder aussi les temps individuels pour l'affichage
            individual_avg_time = statistics.mean(travel_times)
            individual_max_time = max(travel_times)
            individual_min_time = min(travel_times)
            
            bars_with_times.append({
                'name': bar['name'],
                'address': bar.get('formatted_address', bar.get('vicinity', '')),
                'location': bar['geometry']['location'],
                'rating': bar.get('rating'),
                'price_level': bar.get('price_level'),
                'place_id': bar['place_id'],
                'travel_times': travel_times,  # Temps individuels pour l'affichage
                'cluster_travel_times': cluster_travel_times,  # Temps par cluster pour le scoring
                'avg_travel_time': avg_time,  # Moyenne des clusters (pour le tri)
                'max_travel_time': max_time,  # Max des clusters
                'min_travel_time': min_time,  # Min des clusters
                'time_spread': time_spread,  # Écart entre clusters
                'time_balance_score': time_balance_score,  # Score basé sur clusters
                'individual_avg_time': individual_avg_time,  # Pour info/affichage
                'individual_max_time': individual_max_time,  # Pour info/affichage
                'individual_min_time': individual_min_time   # Pour info/affichage
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
        
        # Identifier les bars spéciaux pour l'affichage avec des emojis distinctifs
        if len(best_bars) > 0:
            # 1. Bar avec la plus petite moyenne de temps de trajet -> emoji éclair ⚡
            min_avg_time_bar = min(best_bars, key=lambda x: x['avg_travel_time'])
            
            # 2. Bar avec le plus petit écart de trajet -> emoji balance ⚖️
            min_spread_bar = min(best_bars, key=lambda x: x['time_balance_score'])
            
            # Initialiser tous les bars avec le type standard
            for bar in best_bars:
                bar['marker_types'] = []
                bar['marker_emojis'] = []
            
            # Marquer le bar le plus rapide
            min_avg_time_bar['marker_types'].append('fastest')
            min_avg_time_bar['marker_emojis'].append('⚡')
            
            # Marquer le bar le plus équitable
            min_spread_bar['marker_types'].append('most_balanced')
            min_spread_bar['marker_emojis'].append('⚖️')
            
            # Finaliser les marqueurs pour chaque bar
            for bar in best_bars:
                if len(bar['marker_types']) == 0:
                    # Bar standard
                    bar['marker_emoji'] = '📍'
                    bar['marker_type'] = 'standard'
                elif len(bar['marker_types']) == 1:
                    # Bar avec une seule spécialité
                    bar['marker_emoji'] = bar['marker_emojis'][0]
                    bar['marker_type'] = bar['marker_types'][0]
                else:
                    # Bar avec plusieurs spécialités (le plus rapide ET le plus équitable)
                    bar['marker_emoji'] = ''.join(bar['marker_emojis'])  # Combine les emojis
                    bar['marker_type'] = 'fastest_and_balanced'
                
                # Nettoyer les propriétés temporaires
                del bar['marker_types']
                del bar['marker_emojis']
        
        total_time = time.time() - start_time
        print(f"Recherche complète terminée en {total_time:.2f}s - {len(best_bars)} bars retournés (scoring basé sur {len(participant_clusters)} clusters)")
        
        return jsonify({
            "success": True,
            "bars": best_bars,
            "center_point": {"lat": center_lat, "lng": center_lng},
            "participant_clusters": len(participant_clusters)  # Info pour debug
        }), 200, headers

    except auth.InvalidIdTokenError as e:
        return jsonify({"error": "Token invalide"}), 401, headers
    except ValueError as e:
        return jsonify({"error": str(e)}), 400, headers
    except Exception as e:
        print(f"ERROR: Exception non gérée dans find_optimal_bars: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500, headers


def calculate_adaptive_cluster_distance(positions):
    """Calcule une distance de clustering adaptative basée sur la dispersion du groupe"""
    try:
        if len(positions) <= 2:
            # Pour 2 personnes ou moins, distance de clustering plus petite
            return 0.4  # 400m
        
        # Calculer toutes les distances entre participants
        distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                lat1, lng1 = positions[i]['location']['lat'], positions[i]['location']['lng']
                lat2, lng2 = positions[j]['location']['lat'], positions[j]['location']['lng']
                
                # Distance euclidienne approximative en km
                lat_diff = (lat2 - lat1) * 111
                lng_diff = (lng2 - lng1) * 111 * 0.64  # Correction longitude pour latitude française
                distance_km = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                distances.append(distance_km)
        
        if not distances:
            return 0.6  # Fallback par défaut
        
        # Calculer des métriques sur les distances
        avg_distance = statistics.mean(distances)
        min_distance = min(distances)
        
        # Distance de clustering adaptative : 
        # - Si les gens sont très proches en moyenne (< 1km), clustering serré (min 300m, max 600m)
        # - Si les gens sont dispersés (> 3km), clustering plus large (jusqu'à 1.5km)
        if avg_distance < 1.0:
            # Groupe compact : clustering serré basé sur la distance minimum
            adaptive_distance = max(0.3, min(0.6, min_distance * 1.5))
        elif avg_distance < 3.0:
            # Groupe moyen : clustering proportionnel
            adaptive_distance = max(0.4, min(1.0, avg_distance * 0.3))
        else:
            # Groupe très dispersé : clustering plus large
            adaptive_distance = max(0.8, min(1.5, avg_distance * 0.25))
        
        print(f"Clustering adaptatif: distance moy={avg_distance:.1f}km, distance min={min_distance:.1f}km, seuil cluster={adaptive_distance:.1f}km")
        return adaptive_distance
        
    except Exception as e:
        print(f"Erreur calcul clustering adaptatif: {e}")
        return 0.6  # Fallback vers la valeur par défaut


def cluster_nearby_participants(positions, distance_threshold_km=0.6):
    """Regroupe les participants qui sont à moins de distance_threshold_km les uns des autres"""
    try:
        clusters = []
        assigned = [False] * len(positions)
        
        for i, pos in enumerate(positions):
            if assigned[i]:
                continue
                
            # Créer un nouveau cluster avec cette position
            cluster = [i]
            assigned[i] = True
            
            # Chercher toutes les positions à moins de 600m de celle-ci
            lat1, lng1 = pos['location']['lat'], pos['location']['lng']
            
            for j, other_pos in enumerate(positions):
                if assigned[j] or i == j:
                    continue
                    
                lat2, lng2 = other_pos['location']['lat'], other_pos['location']['lng']
                
                # Calcul distance approximative en km (formule euclidienne simple)
                # 1 degré ≈ 111 km à nos latitudes
                lat_diff = (lat2 - lat1) * 111
                lng_diff = (lng2 - lng1) * 111 * 0.64  # Correction longitude pour latitude française ~46°
                distance_km = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                
                if distance_km <= distance_threshold_km:
                    cluster.append(j)
                    assigned[j] = True
            
            clusters.append(cluster)
        
        print(f"Clustering participants: {len(clusters)} groupes formés à partir de {len(positions)} participants (seuil: {distance_threshold_km:.1f}km)")
        for i, cluster in enumerate(clusters):
            if len(cluster) > 1:
                names = [positions[idx].get('name', f'Participant {idx}') for idx in cluster]
                print(f"  Groupe {i+1}: {len(cluster)} participants proches - {', '.join(names)}")
        
        return clusters
        
    except Exception as e:
        print(f"Erreur clustering: {e}")
        # Fallback: chaque participant est son propre cluster
        return [[i] for i in range(len(positions))]


def search_bars_optimized_zone(positions):
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
        
        # 2. Calculer le point central optimal pour minimiser les temps de trajet
        # Au lieu du geometric median basé sur les distances euclidiennes,
        # on va essayer plusieurs points candidats et choisir celui qui minimise
        # la variance des temps de trajet estimés
        
        # Point de départ : centre géométrique simple
        center_lat = statistics.mean(lats)
        center_lng = statistics.mean(lngs)
        
        # Créer une grille de points candidats autour du centre géométrique
        # pour trouver le meilleur point de recherche
        best_center_lat, best_center_lng = center_lat, center_lng
        min_time_variance = float('inf')
        
        # Taille de la grille de recherche basée sur la dispersion du groupe
        search_grid_size = max(max_distance * 50, 0.002)  # Environ 200m en degrés
        
        print(f"Recherche du centre optimal dans une grille de {search_grid_size:.4f}° autour du centre géométrique")
        
        # Tester 9 points dans une grille 3x3 autour du centre
        test_centers = []
        for lat_offset in [-search_grid_size, 0, search_grid_size]:
            for lng_offset in [-search_grid_size, 0, search_grid_size]:
                test_lat = center_lat + lat_offset
                test_lng = center_lng + lng_offset
                test_centers.append((test_lat, test_lng))
        
        for test_lat, test_lng in test_centers:
            # Estimer la variance des temps de trajet pour ce point
            estimated_times = []
            for pos in positions:
                participant_lat = pos['location']['lat']
                participant_lng = pos['location']['lng']
                
                # Distance euclidienne approximative en km
                lat_diff = (test_lat - participant_lat) * 111
                lng_diff = (test_lng - participant_lng) * 111 * 0.64
                distance_km = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                
                # Estimation grossière du temps de trajet (vitesse moyenne 4 km/h à pied)
                transport_mode = pos.get('transportMode', 'walking')
                if transport_mode == 'car':
                    speed_kmh = 25  # Vitesse urbaine avec embouteillages
                elif transport_mode == 'bicycle':
                    speed_kmh = 15  # Vitesse vélo urbain
                elif transport_mode == 'public_transport':
                    speed_kmh = 20  # Vitesse transports en commun avec attentes
                else:  # walking
                    speed_kmh = 4   # Vitesse piéton
                
                estimated_time = (distance_km / speed_kmh) * 60  # Conversion en minutes
                estimated_times.append(estimated_time)
            
            # Calculer la variance des temps estimés
            if len(estimated_times) > 1:
                time_variance = statistics.variance(estimated_times)
                
                # Si cette variance est plus faible, c'est un meilleur centre
                if time_variance < min_time_variance:
                    min_time_variance = time_variance
                    best_center_lat, best_center_lng = test_lat, test_lng
        
        center_lat, center_lng = best_center_lat, best_center_lng
        print(f"Centre optimal trouvé: ({center_lat:.4f},{center_lng:.4f}) avec variance temps: {min_time_variance:.2f}")
        
        # 3. Calculer le rayon basé sur la distance maximale de toutes les personnes au centre de recherche
        max_person_distance_km = 0
        for position in positions:
            person_lat = position['location']['lat']
            person_lng = position['location']['lng']
            
            # Distance euclidienne approximative en km
            lat_diff = (person_lat - center_lat) * 111
            lng_diff = (person_lng - center_lng) * 111 * 0.64  # Correction longitude pour latitude française
            distance_km = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
            max_person_distance_km = max(max_person_distance_km, distance_km)
        
        # Calculer le rayon adaptatif : distance maximale d'une personne au centre de recherche
        adaptive_radius = max_person_distance_km * 1000  # Conversion km -> mètres
        
        # Appliquer une limite minimale pour garder une recherche pratique
        adaptive_radius = max(adaptive_radius, 500)   # Minimum 500m pour avoir des choix
        
        print(f"Zone optimisée: centre=({center_lat:.4f},{center_lng:.4f}), rayon={adaptive_radius:.0f}m")
        print(f"Calcul du rayon: distance max personne->centre={max_person_distance_km:.1f}km, rayon={adaptive_radius:.0f}m")
        
        # 4. Rechercher dans la zone optimisée avec retry automatique si nécessaire
        candidate_bars = search_bars_nearby(center_lat, center_lng, adaptive_radius, max_bars=50)
        
        # Si aucun bar trouvé, essayer avec un rayon élargi (x1.5 puis x2.5)
        retry_count = 0
        while len(candidate_bars) == 0 and retry_count < 2:
            retry_count += 1
            expanded_radius = adaptive_radius * (1.5 if retry_count == 1 else 2.5)
            print(f"Aucun bar trouvé, tentative {retry_count}/2 avec rayon élargi: {expanded_radius:.0f}m")
            candidate_bars = search_bars_nearby(center_lat, center_lng, expanded_radius, max_bars=50)
        
        if len(candidate_bars) == 0:
            print(f"Aucun bar trouvé après {retry_count + 1} tentatives")
        else:
            print(f"Bars trouvés après {retry_count + 1} tentative(s): {len(candidate_bars)} bars")
        
        # 5. Filtrage équilibré basé sur l'équité géographique ET la qualité
        if len(candidate_bars) > 25:  # Si trop de candidats, filtrer plus intelligemment
            # Calculer pour chaque bar un score d'équité composite
            scored_bars = []
            for bar in candidate_bars:
                bar_lat = bar['geometry']['location']['lat']
                bar_lng = bar['geometry']['location']['lng']
                
                # 1. Calculer les distances approximatives à tous les participants
                distances_to_participants = []
                for pos in positions:
                    participant_lat = pos['location']['lat']
                    participant_lng = pos['location']['lng']
                    
                    # Distance euclidienne en km (approximative)
                    lat_diff = (bar_lat - participant_lat) * 111
                    lng_diff = (bar_lng - participant_lng) * 111 * 0.64
                    distance_km = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                    distances_to_participants.append(distance_km)
                
                # 2. Calculer des métriques d'équité
                avg_distance = statistics.mean(distances_to_participants)
                max_distance = max(distances_to_participants)
                min_distance = min(distances_to_participants)
                distance_spread = max_distance - min_distance
                
                # Score d'équité géographique (plus bas = plus équitable)
                equity_score = distance_spread / avg_distance if avg_distance > 0 else float('inf')
                
                # 3. Prendre en compte la qualité du bar
                rating = bar.get('rating', 3.0)  # Default rating si pas de note
                quality_bonus = (rating - 3.0) * 0.1  # Bonus/malus basé sur la note
                
                # 4. Score composite (équité + qualité)
                # Plus le score est bas, mieux c'est
                composite_score = equity_score - quality_bonus + avg_distance * 0.1
                
                bar['_equity_score'] = equity_score
                bar['_avg_distance'] = avg_distance
                bar['_max_distance'] = max_distance
                bar['_composite_score'] = composite_score
                scored_bars.append(bar)
            
            # Trier par score composite (équité + distance + qualité)
            scored_bars.sort(key=lambda x: x['_composite_score'])
            candidate_bars = scored_bars[:25]  # Limiter à 25 pour l'API
            
            print(f"Filtrage équilibré: gardé {len(candidate_bars)} bars les plus équitables (scores 0.{candidate_bars[0]['_composite_score']:.2f} à {candidate_bars[-1]['_composite_score']:.2f})")
        
        return candidate_bars, center_lat, center_lng
        
    except Exception as e:
        print(f"Erreur recherche optimisée: {e}")
        # Fallback vers l'ancienne méthode avec un rayon par défaut
        center_lat = statistics.mean([pos['location']['lat'] for pos in positions])
        center_lng = statistics.mean([pos['location']['lng'] for pos in positions])
        bars = search_bars_nearby(center_lat, center_lng, 2000, max_bars=25)  # 2km par défaut en cas d'erreur
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