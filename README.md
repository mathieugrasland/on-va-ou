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

L'algorithme de recherche de bars optimaux utilise une approche **entièrement adaptative et équitable** pour garantir l'optimalité entre tous les participants :

### 1. Sélection et validation des participants
- L'utilisateur choisit les amis qui participent à la sortie
- Vérification que tous ont une adresse valide dans leur profil
- Récupération des modes de transport préférés de chaque participant
- Minimum requis : 2 participants avec adresses valides

### 2. Calcul du centre de recherche optimal
- **Géocodage** : Conversion des adresses en coordonnées GPS via l'API Geocoding
- **Optimisation du centre** : 
  - Test de 9 points candidats dans une grille 3×3 autour du centroïde géographique
  - Sélection du point minimisant la variance des temps de trajet estimés
  - Prise en compte des modes de transport de chaque participant

### 3. Calcul du rayon de recherche adaptatif
- **Rayon intelligent** : Distance maximale entre n'importe quel participant et le centre optimal
- **Garantie d'inclusion** : Tous les participants sont dans la zone de recherche des bars
- **Minimum de sécurité** : 500m minimum pour garantir des choix variés
- **Pas de maximum** : Le rayon peut s'étendre selon la dispersion géographique du groupe

### 4. Recherche extensive des bars candidats
- **API Google Places** : Recherche autour du centre optimal avec le rayon adaptatif
- **Retry automatique** : En cas d'absence de résultats, élargissement automatique (×1.5 puis ×2.5)
- **Filtrage intelligent** : 
  - Exclusion des hôtels et établissements non-bars
  - Focus sur les vrais bars/pubs/brasseries/cafés
  - Recherche multi-pages pour maximiser les candidats (jusqu'à 50 bars)
- **Scoring d'équité géographique** : Pré-filtrage des 25 meilleurs candidats basé sur l'équilibre des distances

### 5. Clustering adaptatif des participants
- **Distance de clustering intelligent** :
  - **Groupe compact** (< 1km) : clusters serrés (300-600m)
  - **Groupe moyen** (1-3km) : clusters proportionnels (400m-1km)
  - **Groupe dispersé** (> 3km) : clusters larges (800m-1.5km)
- **Optimisation du scoring** : Les participants proches sont groupés pour éviter la sur-pondération

### 6. Calcul optimisé des temps de trajet
- **Respect des limites API** : Maximum 25 origines × 25 destinations par requête
- **Groupement par transport** : Regroupement des calculs par walking/driving/bicycling/transit
- **Traitement en batch** : Appels API optimisés pour minimiser le nombre de requêtes
- **Métriques par cluster** :
  - Temps moyen par cluster (pas par individu)
  - Écart entre clusters min/max 
  - **Score d'équilibre** : `écart_clusters / temps_moyen_clusters`

### 7. Système de classement par équité des clusters
- **Critère prioritaire** : **Score d'équilibre entre clusters** (croissant)
  - Favorise les bars où tous les groupes arrivent dans des temps similaires
  - Filtre automatique des bars trop déséquilibrés (>75% du temps moyen)
- **Critère secondaire** : **Temps de trajet moyen des clusters** (croissant)
  - À équilibre égal, privilégie les bars plus rapides d'accès
- **Critère tertiaire** : **Note Google** (décroissant)
  - À temps égal, favorise les bars mieux notés

### 8. Affichage des résultats optimisés
- **Marqueurs spéciaux** :
  - ⚡ Bar le plus rapide (temps moyen minimal)
  - ⚖️ Bar le plus équitable (écart minimal entre groupes)
  - ⚡⚖️ Bar optimal (à la fois rapide ET équitable)
- **Détails par participant** : Temps individuel avec mode de transport
- **Informations de groupes** : Nombre de clusters formés
- **Maximum de résultats** : Jusqu'à 25 bars (optimisé pour les limites API)

### Avantages de cette approche révolutionnaire

1. **Équité garantie** : Personne n'est désavantagé par un temps de trajet excessif
2. **Adaptation automatique** : S'ajuste à n'importe quelle configuration géographique
3. **Intelligence géospatiale** : Clustering adaptatif selon la dispersion du groupe
4. **Performance optimisée** : Respect des limites API avec retry automatique
5. **Transparence** : Logs détaillés de toute la logique de calcul
6. **Robustesse** : Fallbacks automatiques en cas d'erreur

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
