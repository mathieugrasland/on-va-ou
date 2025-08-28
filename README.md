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

L'algorithme de recherche de bars optimaux suit une approche sophistiquée en plusieurs étapes :

### 1. Sélection des participants
- L'utilisateur choisit les amis qui participent à la sortie
- Vérification que tous ont une adresse valide dans leur profil
- Récupération des modes de transport préférés de chaque participant

### 2. Calcul du point de rencontre optimal
- **Géocodage** : Conversion des adresses en coordonnées GPS via l'API Geocoding
- **Centroïde géographique** : Calcul du point central entre toutes les positions
- **Point optimal** : Moyenne pondérée des coordonnées pour minimiser les distances

### 3. Recherche des bars dans la zone
- **Rayon de recherche** : 400 mètres autour du point optimal
- **API Google Places** : Recherche des établissements de type "bar" dans la zone
- **Filtrage** : Exclusion des bars fermés ou sans note suffisante

### 4. Calcul optimisé des temps de trajet
- **Groupement par mode de transport** : Regroupement des calculs par walking/driving/transit
- **API Distance Matrix en batch** : Appels groupés pour minimiser la latence
- **Optimisation des requêtes** : Réduction de 30+ appels individuels à 3-4 appels groupés
- **Calcul des moyennes** : Temps moyen pondéré pour chaque bar selon les participants

### 5. Classement intelligent
- **Critère principal** : Temps de trajet moyen croissant
- **Critère secondaire** : Note Google décroissante (si disponible)
- **Pondération** : Les bars les plus accessibles et mieux notés en premier

### 6. Affichage des résultats
- **Marqueurs personnalisés** : Étoiles fuchsia pour distinguer les bars des amis
- **Détails expandables** : Temps de trajet détaillé par participant et mode de transport
- **Intégration carte** : Centrage automatique et liens vers Google Maps

### Optimisations techniques
- **Performance** : Réduction du temps de réponse de ~15 secondes à ~3 secondes
- **Cache intelligent** : Évite les recalculs inutiles lors des interactions
- **Batch processing** : Groupement des appels API pour minimiser la latence
- **Interface responsive** : Adaptation mobile et desktop avec UX optimisée

Cette approche garantit des recommandations pertinentes en minimisant le temps de trajet total pour tous les participants tout en privilégiant la qualité des établissements.

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
