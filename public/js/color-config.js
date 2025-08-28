/**
 * Configuration centralisée des couleurs pour l'application "On va où ?"
 * Ce fichier centralise toutes les palettes de couleurs utilisées dans l'application
 * pour maintenir la cohérence visuelle et faciliter les mises à jour.
 */

// Palette principale de l'interface (déjà définie dans style.css)
export const INTERFACE_COLORS = {
    primary: '#5d4037',      // Marron foncé
    accent: '#ffb74d',       // Orange clair
    lightBg: '#ffffff',      // Fond blanc pur
    darkText: '#333',        // Texte sombre
    lightText: '#fff',       // Texte clair
    inputBorder: '#e0e0e0',  // Bordures douces
};

// Palette moderne pour les marqueurs d'amis
// Cette palette respecte l'harmonie avec les couleurs de l'interface
// tout en offrant une bonne visibilité sur les cartes
export const FRIEND_COLORS = [
    '#5d4037', // Marron (cohérent avec l'interface)
    '#ad1457', // Rose bordeaux
    '#00695c', // Vert émeraude
    '#b65b00ff', // Ambre doré
    '#455a64', // Gris bleu
    '#6a1b9a',  // Violet améthyste
    '#2e7d32', // Vert forêt
    '#d84315', // Rouge terre cuite moderne
    '#7b1fa2', // Violet profond
    '#ef6c00', // Orange brûlé
];

// Couleurs spéciales pour les statuts
export const STATUS_COLORS = {
    success: '#2e7d32',  // Vert forêt
    error: '#c62828',    // Rouge d'erreur
    warning: '#ef6c00',  // Orange d'avertissement
    info: '#1565c0',     // Bleu d'information
    logout: '#EA4335',   // Rouge Google pour déconnexion
    logoutHover: '#D33B2C' // Rouge Google hover
};

// Fonction utilitaire pour obtenir une couleur d'ami par index
export function getFriendColor(index) {
    return FRIEND_COLORS[index % FRIEND_COLORS.length];
}

// Fonction utilitaire pour obtenir une couleur d'ami par ID (plus stable)
export function getFriendColorById(friendId) {
    // Utilise un hash simple de l'ID pour une couleur consistante
    let hash = 0;
    for (let i = 0; i < friendId.length; i++) {
        const char = friendId.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convertit en 32bit
    }
    const index = Math.abs(hash) % FRIEND_COLORS.length;
    return FRIEND_COLORS[index];
}

// Export par défaut pour faciliter l'import
export default {
    INTERFACE_COLORS,
    FRIEND_COLORS,
    STATUS_COLORS,
    getFriendColor,
    getFriendColorById
};
