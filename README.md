# On va où ? 🗺️🍺

Application web de géolocalisation sociale pour organiser des sorties entre amis et trouver les bars optimaux.

## Fonctionnalités

- **Authentification** : Connexion sécurisée avec Firebase
- **Profils** : Gestion des informations personnelles avec adresse et mode de transport
- **Amis** : Système de demandes et acceptation d'amis
- **Carte interactive** : Visualisation des positions de tous vos amis
- **Recherche de bars optimaux** : Trouve automatiquement les meilleurs bars pour se retrouver entre amis
- **Géolocalisation** : Conversion automatique des adresses en coordonnées

## Méthodologie de recherche

L'algorithme de recherche de bars optimaux utilise une approche **entièrement basée sur l'équilibre des temps de trajet** pour garantir l'équité entre tous les participants :

### 1. Sélection des participants
- L'utilisateur choisit les amis qui participent à la sortie
- Vérification que tous ont une adresse valide dans leur profil
- Récupération des modes de transport préférés de chaque participant

### 2. Calcul du point de rencontre optimal
- **Géocodage** : Conversion des adresses en coordonnées GPS via l'API Geocoding
- **Centroïde géographique** : Calcul du point central entre toutes les positions
- **Zone de recherche étendue** : Rayon jusqu'à 2,5km pour maximiser les choix

### 3. Recherche extensive des bars candidats
- **API Google Places** : Recherche dans un rayon étendu (min. 2km) autour du centre
- **Filtrage intelligent** : 
  - Exclusion des hôtels et établissements non-bars
  - Focus sur les vrais bars/pubs/brasseries
  - Pré-filtrage par note (≥3.0) si suffisamment de choix
- **Optimisation candidats** : Limitation à 25 bars max (contrainte API Distance Matrix)

### 4. Calcul optimisé des temps de trajet
- **Respect des limites API** : Maximum 25 origines × 25 destinations par requête
- **Groupement par transport** : Regroupement des calculs par walking/driving/bicycling/transit
- **Traitement en batch** : Appels API optimisés pour minimiser le nombre de requêtes
- **Calcul de métriques** :
  - Temps moyen par bar
  - Écart entre temps min/max (time_spread)
  - **Score d'équilibre** : `time_spread / avg_time` (plus bas = plus équitable)

### 5. Nouveau système de classement par équité
- **Critère prioritaire** : **Score d'équilibre des temps** (croissant)
  - Favorise les bars où tous arrivent dans des temps similaires
  - Filtre automatique des bars trop déséquilibrés (>75% du temps moyen)
- **Critère secondaire** : **Temps de trajet moyen** (croissant)
  - À équilibre égal, privilégie les bars plus rapides d'accès
- **Critère tertiaire** : **Note Google** (décroissant)
  - À temps égal, favorise les bars mieux notés

### 6. Affichage des résultats optimisés
- **Indicateurs visuels d'équilibre** :
  - 🟢 Équilibré : Écart ≤25% du temps moyen
  - 🟠 Acceptable : Écart 25-50% du temps moyen  
  - 🔴 Déséquilibré : Écart >50% du temps moyen
- **Détails par participant** : Temps individuel avec mode de transport
- **Maximum de résultats** : Jusqu'à 25 bars (optimisé pour les limites API)

### Optimisations techniques
- **Performance** : Algorithme optimisé pour respecter les limites Google Maps API (25×25 max)
- **Traitement intelligent** : Pré-filtrage des candidats par distance au centre et qualité
- **Équité garantie** : Système de score d'équilibre pour éviter les temps de trajet déséquilibrés
- **Batch processing** : Groupement optimal des appels API par mode de transport
- **Interface responsive** : Indicateurs visuels d'équilibre et détails de temps par participant

Cette approche révolutionnaire **privilégie l'équité entre participants** plutôt que la note absolue des bars, garantissant que personne ne soit désavantagé par un temps de trajet excessif.

## Technologies

- **Frontend** : HTML/CSS/JavaScript vanilla
- **Backend** : Firebase (Auth, Firestore, Cloud Functions)
- **Cartes** : Google Maps JavaScript API
- **APIs** : Google Places API, Distance Matrix API, Geocoding API
- **Calculs** : Algorithmes de géolocalisation et optimisation de trajets
- **Déploiement** : Firebase Hosting + GitHub Actions

## Utilisation

1. Créer un compte et compléter son profil avec une adresse et mode de transport
2. Ajouter des amis via leur email
3. Sur la page d'accueil, sélectionner les amis avec qui sortir
4. Cliquer sur "Trouver des bars" pour obtenir les meilleures recommandations
5. Choisir un bar dans la liste et s'y retrouver !

---

**URL** : https://on-va-ou-470217.web.app/
