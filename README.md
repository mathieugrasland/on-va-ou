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
- L'application cherche tous les bars dans un rayon de **600 mètres** autour du point optimal
- Seuls les établissements de type "bar" avec une note d'au moins 3/5 sont pris en compte

### Étape 5 : Calcul des temps de trajet précis
- Pour chaque bar trouvé, l'application utilise **l'API Google Maps Distance Matrix** pour calculer les temps de trajet réels
- Le mode de transport de chaque personne est rigoureusement respecté :
  - 🚗 Voiture : itinéraires routiers en temps réel
  - 🚲 Vélo : pistes cyclables et routes adaptées
  - 🚌 Transport en commun : horaires et correspondances en temps réel
  - 🚶 À pied : itinéraires piétons optimisés
- Si l'API ne peut pas calculer un itinéraire (par exemple, pas de transport en commun disponible), le bar est écarté

### Étape 6 : Sélection des meilleurs bars
- Les bars sont classés selon deux critères principaux :
  1. **Note Google** : Les bars les mieux notés sont priorisés
  2. **Temps de trajet moyen** : En cas d'égalité de notes, le temps moyen départage
- Les **5 meilleurs bars** selon ces critères sont sélectionnés et affichés

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
