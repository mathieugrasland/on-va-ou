#!/usr/bin/env node

/**
 * @fileoverview Script de build pour l'application On va où ?
 * @author On va où ? Team
 * @version 1.0.0
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const CONFIG = {
    srcDir: 'src',
    publicDir: 'public',
    distDir: 'dist',
    assetsDir: 'assets',
    minify: process.env.NODE_ENV === 'production'
};

// Couleurs pour les logs
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

/**
 * Logger coloré
 */
class Logger {
    static info(message) {
        console.log(`${colors.blue}ℹ${colors.reset} ${message}`);
    }
    
    static success(message) {
        console.log(`${colors.green}✓${colors.reset} ${message}`);
    }
    
    static warn(message) {
        console.log(`${colors.yellow}⚠${colors.reset} ${message}`);
    }
    
    static error(message) {
        console.log(`${colors.red}✗${colors.reset} ${message}`);
    }
    
    static step(message) {
        console.log(`${colors.cyan}➤${colors.reset} ${colors.bright}${message}${colors.reset}`);
    }
}

/**
 * Gestionnaire de fichiers
 */
class FileManager {
    /**
     * Vérifier si un fichier existe
     */
    static exists(filePath) {
        return fs.existsSync(filePath);
    }
    
    /**
     * Créer un répertoire récursivement
     */
    static createDir(dirPath) {
        if (!this.exists(dirPath)) {
            fs.mkdirSync(dirPath, { recursive: true });
            Logger.info(`Répertoire créé: ${dirPath}`);
        }
    }
    
    /**
     * Copier un fichier
     */
    static copyFile(source, destination) {
        this.createDir(path.dirname(destination));
        fs.copyFileSync(source, destination);
        Logger.info(`Fichier copié: ${source} → ${destination}`);
    }
    
    /**
     * Copier un répertoire récursivement
     */
    static copyDir(source, destination) {
        this.createDir(destination);
        
        const items = fs.readdirSync(source);
        
        items.forEach(item => {
            const sourcePath = path.join(source, item);
            const destPath = path.join(destination, item);
            
            if (fs.statSync(sourcePath).isDirectory()) {
                this.copyDir(sourcePath, destPath);
            } else {
                this.copyFile(sourcePath, destPath);
            }
        });
    }
    
    /**
     * Lire un fichier
     */
    static readFile(filePath) {
        return fs.readFileSync(filePath, 'utf8');
    }
    
    /**
     * Écrire un fichier
     */
    static writeFile(filePath, content) {
        this.createDir(path.dirname(filePath));
        fs.writeFileSync(filePath, content, 'utf8');
        Logger.info(`Fichier écrit: ${filePath}`);
    }
    
    /**
     * Nettoyer un répertoire
     */
    static cleanDir(dirPath) {
        if (this.exists(dirPath)) {
            fs.rmSync(dirPath, { recursive: true, force: true });
            Logger.info(`Répertoire nettoyé: ${dirPath}`);
        }
    }
}

/**
 * Processeur CSS
 */
class CSSProcessor {
    /**
     * Concaténer plusieurs fichiers CSS
     */
    static concatenate(cssFiles, outputPath) {
        let concatenatedCSS = '';
        
        cssFiles.forEach(filePath => {
            if (FileManager.exists(filePath)) {
                const content = FileManager.readFile(filePath);
                concatenatedCSS += `/* === ${path.basename(filePath)} === */\n`;
                concatenatedCSS += content + '\n\n';
            }
        });
        
        FileManager.writeFile(outputPath, concatenatedCSS);
        Logger.success(`CSS concaténé: ${outputPath}`);
        
        return concatenatedCSS;
    }
    
    /**
     * Minifier le CSS (basique)
     */
    static minify(css) {
        if (!CONFIG.minify) return css;
        
        return css
            // Supprimer les commentaires
            .replace(/\/\*[\s\S]*?\*\//g, '')
            // Supprimer les espaces multiples
            .replace(/\s+/g, ' ')
            // Supprimer les espaces autour des caractères spéciaux
            .replace(/\s*([{}:;,>+~])\s*/g, '$1')
            // Supprimer les points-virgules avant les accolades fermantes
            .replace(/;}/g, '}')
            // Supprimer les espaces en début et fin
            .trim();
    }
}

/**
 * Processeur JavaScript
 */
class JSProcessor {
    /**
     * Traiter les imports ES6 pour les rendre compatibles
     */
    static processImports(jsContent, basePath) {
        // Remplacer les imports relatifs par des chemins absolus
        return jsContent.replace(
            /import\s+.*?\s+from\s+['"](\..+?)['"];?/g,
            (match, importPath) => {
                const absolutePath = path.resolve(basePath, importPath);
                const relativePath = path.relative(CONFIG.publicDir, absolutePath);
                return match.replace(importPath, './' + relativePath.replace(/\\/g, '/'));
            }
        );
    }
    
    /**
     * Minifier le JavaScript (basique)
     */
    static minify(js) {
        if (!CONFIG.minify) return js;
        
        return js
            // Supprimer les commentaires de ligne
            .replace(/\/\/.*$/gm, '')
            // Supprimer les commentaires multilignes
            .replace(/\/\*[\s\S]*?\*\//g, '')
            // Supprimer les espaces multiples
            .replace(/\s+/g, ' ')
            // Supprimer les espaces autour des opérateurs
            .replace(/\s*([=+\-*/{}();,])\s*/g, '$1')
            .trim();
    }
}

/**
 * Gestionnaire de build principal
 */
class BuildManager {
    constructor() {
        this.startTime = Date.now();
    }
    
    /**
     * Nettoyer le répertoire de build
     */
    clean() {
        Logger.step('Nettoyage du répertoire de build');
        FileManager.cleanDir(CONFIG.distDir);
        FileManager.createDir(CONFIG.distDir);
        Logger.success('Nettoyage terminé');
    }
    
    /**
     * Copier les fichiers statiques
     */
    copyStaticFiles() {
        Logger.step('Copie des fichiers statiques');
        
        // Copier le contenu de public/ vers dist/
        if (FileManager.exists(CONFIG.publicDir)) {
            const items = fs.readdirSync(CONFIG.publicDir);
            
            items.forEach(item => {
                const sourcePath = path.join(CONFIG.publicDir, item);
                const destPath = path.join(CONFIG.distDir, item);
                
                if (fs.statSync(sourcePath).isDirectory()) {
                    FileManager.copyDir(sourcePath, destPath);
                } else {
                    FileManager.copyFile(sourcePath, destPath);
                }
            });
        }
        
        Logger.success('Fichiers statiques copiés');
    }
    
    /**
     * Construire les styles CSS
     */
    buildStyles() {
        Logger.step('Construction des styles CSS');
        
        const cssFiles = [
            path.join(CONFIG.srcDir, 'styles', 'variables.css'),
            path.join(CONFIG.srcDir, 'styles', 'utilities.css'),
            path.join(CONFIG.publicDir, 'style.css')
        ];
        
        const outputPath = path.join(CONFIG.distDir, 'styles', 'app.css');
        let css = CSSProcessor.concatenate(cssFiles, outputPath);
        
        // Minifier si en production
        if (CONFIG.minify) {
            css = CSSProcessor.minify(css);
            FileManager.writeFile(outputPath, css);
            Logger.info('CSS minifié');
        }
        
        Logger.success('Styles CSS construits');
        return outputPath;
    }
    
    /**
     * Construire les scripts JavaScript
     */
    buildScripts() {
        Logger.step('Construction des scripts JavaScript');
        
        const srcScriptsDir = path.join(CONFIG.srcDir);
        const distScriptsDir = path.join(CONFIG.distDir, 'js');
        
        if (FileManager.exists(srcScriptsDir)) {
            FileManager.copyDir(srcScriptsDir, distScriptsDir);
            
            // Traiter tous les fichiers JS
            this.processJSFiles(distScriptsDir);
        }
        
        Logger.success('Scripts JavaScript construits');
    }
    
    /**
     * Traiter les fichiers JavaScript
     */
    processJSFiles(directory) {
        const items = fs.readdirSync(directory);
        
        items.forEach(item => {
            const itemPath = path.join(directory, item);
            
            if (fs.statSync(itemPath).isDirectory()) {
                this.processJSFiles(itemPath);
            } else if (path.extname(item) === '.js') {
                let content = FileManager.readFile(itemPath);
                
                // Traiter les imports
                content = JSProcessor.processImports(content, path.dirname(itemPath));
                
                // Minifier si nécessaire
                if (CONFIG.minify) {
                    content = JSProcessor.minify(content);
                }
                
                FileManager.writeFile(itemPath, content);
            }
        });
    }
    
    /**
     * Mettre à jour les références dans les fichiers HTML
     */
    updateHTMLReferences() {
        Logger.step('Mise à jour des références HTML');
        
        const htmlFiles = ['index.html', 'login.html', 'register.html', 'dashboard.html'];
        
        htmlFiles.forEach(htmlFile => {
            const htmlPath = path.join(CONFIG.distDir, htmlFile);
            
            if (FileManager.exists(htmlPath)) {
                let content = FileManager.readFile(htmlPath);
                
                // Mettre à jour les références CSS
                content = content.replace(
                    /<link[^>]+href="[^"]*style\.css"[^>]*>/gi,
                    '<link rel="stylesheet" href="./styles/app.css">'
                );
                
                // Ajouter le préfixe pour les scripts src/
                content = content.replace(
                    /src="\.\/src\//g,
                    'src="./js/'
                );
                
                FileManager.writeFile(htmlPath, content);
            }
        });
        
        Logger.success('Références HTML mises à jour');
    }
    
    /**
     * Générer le manifeste des assets
     */
    generateManifest() {
        Logger.step('Génération du manifeste');
        
        const manifest = {
            name: 'On va où ?',
            version: '1.0.0',
            buildTime: new Date().toISOString(),
            files: {}
        };
        
        // Lister tous les fichiers construits
        this.listFiles(CONFIG.distDir, manifest.files);
        
        const manifestPath = path.join(CONFIG.distDir, 'manifest.json');
        FileManager.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
        
        Logger.success('Manifeste généré');
    }
    
    /**
     * Lister récursivement les fichiers
     */
    listFiles(directory, filesList, prefix = '') {
        const items = fs.readdirSync(directory);
        
        items.forEach(item => {
            const itemPath = path.join(directory, item);
            const relativePath = prefix + item;
            
            if (fs.statSync(itemPath).isDirectory()) {
                this.listFiles(itemPath, filesList, relativePath + '/');
            } else {
                const stats = fs.statSync(itemPath);
                filesList[relativePath] = {
                    size: stats.size,
                    modified: stats.mtime.toISOString()
                };
            }
        });
    }
    
    /**
     * Exécuter le build complet
     */
    async build() {
        Logger.info(`${colors.magenta}🚀 Début du build pour On va où ?${colors.reset}`);
        
        try {
            this.clean();
            this.copyStaticFiles();
            this.buildStyles();
            this.buildScripts();
            this.updateHTMLReferences();
            this.generateManifest();
            
            const buildTime = Date.now() - this.startTime;
            Logger.success(`${colors.green}✨ Build terminé en ${buildTime}ms${colors.reset}`);
            
        } catch (error) {
            Logger.error(`Erreur durant le build: ${error.message}`);
            process.exit(1);
        }
    }
}

// Exécution du script
if (require.main === module) {
    const builder = new BuildManager();
    builder.build();
}

module.exports = { BuildManager, FileManager, CSSProcessor, JSProcessor };
