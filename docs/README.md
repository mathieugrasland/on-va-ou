# On va où ? - Documentation technique

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Structure du projet](#structure-du-projet)
4. [Services](#services)
5. [Composants](#composants)
6. [Déploiement](#déploiement)
7. [Développement](#développement)
8. [API](#api)

## 🎯 Vue d'ensemble

**On va où ?** est une application web progressive qui aide les groupes d'amis à trouver des bars optimalement situés entre leurs positions géographiques.

### Fonctionnalités principales

- ✅ Authentification utilisateur (Firebase Auth)
- ✅ Gestion de profil utilisateur
- ✅ Ajout et gestion d'amis
- ✅ Géolocalisation automatique
- ✅ Calcul du point central optimal
- ✅ Recherche de bars à proximité
- ✅ Interface responsive
- ✅ Déploiement automatique

### Technologies utilisées

- **Frontend**: Vanilla JavaScript ES6+, CSS3, HTML5
- **Backend**: Firebase Cloud Functions (Python 3.12)
- **Base de données**: Firestore
- **Authentification**: Firebase Auth
- **Hébergement**: Firebase Hosting
- **CI/CD**: GitHub Actions

## 🏗️ Architecture

### Architecture générale

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Firebase      │    │   Cloud         │
│   (JAMstack)    │◄──►│   Services      │◄──►│   Functions     │
│                 │    │                 │    │   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Files  │    │   Firestore     │    │   External      │
│   (Hosting)     │    │   (Database)    │    │   APIs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Flux de données

```
User Input → Component → Service → Firebase → Cloud Function → External API
                ↓                      ↓              ↓
           DOM Update ← Response ← Firestore ← Processing ← API Response
```

## 📁 Structure du projet

```
on-va-ou/
├── 📁 .github/                    # GitHub Actions workflows
│   └── 📁 workflows/
│       └── 📄 deploy.yml         # Pipeline CI/CD
├── 📁 docs/                      # Documentation
│   ├── 📄 README.md             # Documentation principale
│   ├── 📄 api.md                # Documentation API
│   └── 📄 deployment.md         # Guide de déploiement
├── 📁 functions/                 # Cloud Functions
│   ├── 📄 main.py               # Point d'entrée
│   └── 📄 requirements.txt      # Dépendances Python
├── 📁 public/                    # Files statiques
│   ├── 📄 index.html            # Page d'accueil
│   ├── 📄 login.html            # Page de connexion
│   ├── 📄 register.html         # Page d'inscription
│   ├── 📄 dashboard.html        # Tableau de bord
│   ├── 📄 style.css             # Styles globaux
│   └── 📁 images/               # Assets images
├── 📁 src/                       # Code source modulaire
│   ├── 📁 config/               # Configuration
│   │   └── 📄 firebase.js       # Config Firebase
│   ├── 📁 services/             # Services métier
│   │   ├── 📄 auth.service.js   # Service d'authentification
│   │   ├── 📄 user.service.js   # Service utilisateur
│   │   └── 📄 location.service.js # Service de localisation
│   ├── 📁 components/           # Composants UI
│   │   ├── 📄 login-form.js     # Formulaire de connexion
│   │   ├── 📄 register-form.js  # Formulaire d'inscription
│   │   └── 📄 dashboard.js      # Composant tableau de bord
│   ├── 📁 utils/                # Utilitaires
│   │   ├── 📄 logger.js         # Système de logs
│   │   └── 📄 helpers.js        # Fonctions utilitaires
│   └── 📁 styles/               # Styles modulaires
│       ├── 📄 variables.css     # Variables CSS
│       └── 📄 utilities.css     # Classes utilitaires
├── 📁 scripts/                   # Scripts de build/deploy
├── 📁 tests/                     # Tests
├── 📄 firebase.json              # Configuration Firebase
└── 📄 package.json              # Métadonnées du projet
```

## 🔧 Services

### AuthService (`src/services/auth.service.js`)

Service centralisé pour l'authentification Firebase.

#### Méthodes principales

```javascript
// Inscription
AuthService.register(userData)

// Connexion
AuthService.login(email, password)

// Déconnexion
AuthService.logout()

// Utilisateur actuel
AuthService.getCurrentUser()

// Observer les changements d'auth
AuthService.onAuthStateChanged(callback)
```

### UserService (`src/services/user.service.js`)

Service de gestion des profils utilisateur et des relations d'amitié.

#### Méthodes principales

```javascript
// Créer un profil
UserService.createUserProfile(userId, userData)

// Obtenir un profil
UserService.getUserProfile(userId)

// Ajouter un ami
UserService.addFriend(userId, friendEmail)

// Obtenir la liste d'amis
UserService.getFriends(userId)

// Mettre à jour la localisation
UserService.updateUserLocation(userId, location)
```

### LocationService (`src/services/location.service.js`)

Service de géolocalisation et recherche de lieux.

#### Méthodes principales

```javascript
// Position actuelle
LocationService.getCurrentPosition()

// Point central
LocationService.calculateCentralPoint(locations)

// Distance entre deux points
LocationService.calculateDistance(point1, point2)

// Recherche de bars
LocationService.findNearbyBars(location, radius)
```

## 🧩 Composants

### RegisterForm (`src/components/register-form.js`)

Composant de gestion du formulaire d'inscription.

#### Fonctionnalités

- Validation en temps réel
- Gestion des erreurs
- Intégration avec AuthService
- Redirection automatique

### LoginForm (`src/components/login-form.js`)

Composant de gestion du formulaire de connexion.

#### Fonctionnalités

- Validation des champs
- Gestion des erreurs d'auth
- Messages de feedback
- Redirection post-connexion

### Dashboard (`src/components/dashboard.js`)

Composant principal de l'application.

#### Fonctionnalités

- Affichage du profil utilisateur
- Gestion de la liste d'amis
- Recherche de bars
- Géolocalisation
- Interface responsive

## 🚀 Déploiement

### Pipeline CI/CD

Le déploiement est automatisé via GitHub Actions :

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
    paths: ['public/**', 'src/**', 'functions/**']

jobs:
  deploy:
    - Setup Node.js
    - Install dependencies
    - Build project
    - Deploy to Firebase
```

### Étapes de déploiement

1. **Push sur main** → Déclenche le workflow
2. **Build** → Compilation et optimisation
3. **Test** → Validation du code
4. **Deploy** → Publication sur Firebase Hosting

### Variables d'environnement

```bash
# GitHub Secrets requis
FIREBASE_SERVICE_ACCOUNT_KEY  # Clé du compte de service
FIREBASE_PROJECT_ID          # ID du projet Firebase
```

## 💻 Développement

### Prérequis

- Node.js 16+
- Firebase CLI
- Git
- Compte Firebase

### Installation locale

```bash
# 1. Cloner le repo
git clone https://github.com/your-username/on-va-ou.git
cd on-va-ou

# 2. Installer Firebase CLI
npm install -g firebase-tools

# 3. Se connecter à Firebase
firebase login

# 4. Initialiser le projet
firebase use --add

# 5. Servir localement
firebase serve
```

### Scripts de développement

```bash
# Servir l'app localement
firebase serve

# Déployer manuellement
firebase deploy

# Déployer seulement les fonctions
firebase deploy --only functions

# Déployer seulement l'hosting
firebase deploy --only hosting

# Voir les logs
firebase functions:log
```

### Structure du code

#### Conventions de nommage

- **Fichiers**: `kebab-case.js`
- **Classes**: `PascalCase`
- **Variables**: `camelCase`
- **Constantes**: `UPPER_SNAKE_CASE`

#### Documentation JSDoc

Tous les services et composants sont documentés avec JSDoc :

```javascript
/**
 * @fileoverview Description du fichier
 * @author On va où ? Team
 * @version 1.0.0
 */

/**
 * Description de la fonction
 * @param {string} param1 - Description du paramètre
 * @returns {Promise<Object>} Description du retour
 */
```

### Debugging

#### Logs

Le système de logs centralisé (`Logger`) offre différents niveaux :

```javascript
Logger.debug('Message de debug');
Logger.info('Information');
Logger.warn('Avertissement');
Logger.error('Erreur', error);
```

#### Firebase Emulator

Pour développer localement :

```bash
firebase emulators:start
```

## 📊 Monitoring

### Métriques Firebase

- **Performance**: Temps de chargement, Core Web Vitals
- **Analytics**: Utilisation, conversions
- **Crashlytics**: Erreurs JavaScript
- **Functions**: Latence, erreurs, utilisation

### Logs

Les logs sont centralisés dans :
- **Console navigateur** (développement)
- **Firebase Functions Logs** (production)
- **Google Cloud Logging** (analytics)

## 🔐 Sécurité

### Firestore Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users peuvent lire/écrire leur propre profil
    match /users/{userId} {
      allow read, write: if request.auth != null 
                        && request.auth.uid == userId;
    }
    
    // Lecture publique des profils pour les amis
    match /users/{userId} {
      allow read: if request.auth != null;
    }
  }
}
```

### Authentification

- Firebase Auth avec email/password
- Validation côté client et serveur
- Sessions sécurisées
- Protection CSRF automatique

## 🐛 Troubleshooting

### Problèmes courants

#### Erreur d'authentification
```bash
# Vérifier la config Firebase
firebase projects:list

# Re-connecter si nécessaire
firebase login --reauth
```

#### Erreur de déploiement
```bash
# Vérifier les permissions
firebase projects:list

# Nettoyer le cache
firebase functions:delete --force
```

#### Géolocalisation bloquée
- Vérifier les permissions du navigateur
- Utiliser HTTPS en production
- Implémenter une fallback

### Support

- 📧 Email: support@onvaou.com
- 💬 Discord: [Serveur communauté]
- 📚 Wiki: [Documentation étendue]
- 🐛 Issues: [GitHub Issues]

---

*Documentation maintenue par l'équipe On va où ? - Dernière mise à jour: $(date)*
