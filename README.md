# On va où ? 🗺️🍺

Application web de géolocalisation sociale pour organiser des sorties entre amis et trouver les bars optimaux.

## Fonctionnalités

- **Authentification** : Connexion sécurisée avec Firebase
- **Profils** : Gestion des informations personnelles avec adresse et mode de transport
- **Amis** : Système de demandes et acceptation d'amis
- **Carte interactive** : Visualisation des positions de tous vos amis
- **Recherche de bars optimaux** : Trouve automatiquement les meilleurs bars pour se retrouver entre amis
- **Géolocalisation** : Conversion automatique des adresses en coordonnées

## 🎯 Comment fonctionne la recherche de bars ?

### Étape 1 : Sélection des amis
- Sur la page d'accueil, vous voyez la carte avec les positions de tous vos amis
- Cliquez sur les amis avec qui vous voulez sortir pour les sélectionner
- Un compteur indique combien d'amis sont sélectionnés

### Étape 2 : Lancement de la recherche
- Une fois vos amis sélectionnés, cliquez sur "🔍 Trouver des bars"
- L'application calcule automatiquement le point de rendez-vous optimal

### Étape 3 : Calcul du point optimal
- L'algorithme trouve le point central équilibré entre toutes les positions sélectionnées
- Ce point prend en compte la position de chaque participant pour minimiser les déplacements

### Étape 4 : Recherche des bars
- L'application cherche tous les bars dans un rayon de 5km autour du point optimal
- Seuls les établissements de type "bar" sont pris en compte

### Étape 5 : Calcul des temps de trajet
- Pour chaque bar trouvé, l'application calcule le temps de trajet depuis la position de chaque participant
- Le mode de transport de chaque personne est pris en compte :
  - 🚗 Voiture : itinéraires routiers
  - 🚲 Vélo : pistes cyclables
  - 🚌 Transport en commun : réseau de transport public
  - 🚶 À pied : itinéraires piétons

### Étape 6 : Sélection des meilleurs bars
- Les bars sont classés selon deux critères principaux :
  1. **Temps moyen** : La moyenne des temps de trajet de tous les participants
  2. **Équité** : Bars où personne n'a un trajet beaucoup plus long que les autres
- Les 5 meilleurs bars sont sélectionnés et affichés

### Étape 7 : Résultats
- Les bars apparaissent sur la carte avec des marqueurs 🍺
- Une liste détaillée est affichée sous la carte avec :
  - Nom et adresse du bar
  - Note Google (si disponible)
  - Temps de trajet moyen estimé
  - Bouton pour voir sur Google Maps
  - Bouton pour centrer la carte sur le bar

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
