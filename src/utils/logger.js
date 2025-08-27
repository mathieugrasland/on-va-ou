/**
 * @fileoverview Système de logging centralisé
 * @author On va où ? Team
 * @version 1.0.0
 */

/**
 * Niveaux de log
 */
const LogLevel = {
    ERROR: 0,
    WARN: 1,
    INFO: 2,
    DEBUG: 3
};

/**
 * Configuration du logger
 */
const loggerConfig = {
    level: LogLevel.INFO, // Niveau minimum en production
    enableConsole: true,
    enableRemote: false, // Pour analytics futures
    maxEntries: 100
};

/**
 * Service de logging centralisé
 */
export class Logger {
    
    static logs = [];
    
    /**
     * Log d'erreur
     * @param {string} message - Message
     * @param {Error|Object} error - Erreur ou données
     */
    static error(message, error = null) {
        this.log(LogLevel.ERROR, message, error);
    }
    
    /**
     * Log d'avertissement
     * @param {string} message - Message
     * @param {Object} data - Données optionnelles
     */
    static warn(message, data = null) {
        this.log(LogLevel.WARN, message, data);
    }
    
    /**
     * Log d'information
     * @param {string} message - Message
     * @param {Object} data - Données optionnelles
     */
    static info(message, data = null) {
        this.log(LogLevel.INFO, message, data);
    }
    
    /**
     * Log de debug
     * @param {string} message - Message
     * @param {Object} data - Données optionnelles
     */
    static debug(message, data = null) {
        this.log(LogLevel.DEBUG, message, data);
    }
    
    /**
     * Fonction de log principale
     * @param {number} level - Niveau de log
     * @param {string} message - Message
     * @param {any} data - Données optionnelles
     */
    static log(level, message, data = null) {
        if (level > loggerConfig.level) return;
        
        const timestamp = new Date().toISOString();
        const levelName = Object.keys(LogLevel)[level];
        
        const logEntry = {
            timestamp,
            level: levelName,
            message,
            data,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        // Stocker dans l'historique
        this.logs.push(logEntry);
        if (this.logs.length > loggerConfig.maxEntries) {
            this.logs.shift();
        }
        
        // Console
        if (loggerConfig.enableConsole) {
            const consoleMethod = this.getConsoleMethod(level);
            const formattedMessage = `[${timestamp}] ${levelName}: ${message}`;
            
            if (data) {
                consoleMethod(formattedMessage, data);
            } else {
                consoleMethod(formattedMessage);
            }
        }
        
        // Analytics distant (futur)
        if (loggerConfig.enableRemote && level <= LogLevel.WARN) {
            this.sendToRemote(logEntry);
        }
    }
    
    /**
     * Obtenir la méthode console appropriée
     * @param {number} level - Niveau de log
     * @returns {Function} Méthode console
     */
    static getConsoleMethod(level) {
        switch (level) {
            case LogLevel.ERROR: return console.error;
            case LogLevel.WARN: return console.warn;
            case LogLevel.INFO: return console.info;
            case LogLevel.DEBUG: return console.debug;
            default: return console.log;
        }
    }
    
    /**
     * Envoyer les logs vers un service distant
     * @param {Object} logEntry - Entrée de log
     */
    static sendToRemote(logEntry) {
        // Implementation future pour analytics
        // fetch('/api/logs', { method: 'POST', body: JSON.stringify(logEntry) });
    }
    
    /**
     * Obtenir l'historique des logs
     * @returns {Array} Historique des logs
     */
    static getHistory() {
        return [...this.logs];
    }
    
    /**
     * Vider l'historique des logs
     */
    static clearHistory() {
        this.logs = [];
    }
    
    /**
     * Configurer le logger
     * @param {Object} config - Configuration
     */
    static configure(config) {
        Object.assign(loggerConfig, config);
    }
}
