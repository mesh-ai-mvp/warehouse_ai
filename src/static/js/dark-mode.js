// Set initial theme immediately to prevent flash
(function () {
    const storageKey = 'inventory-app-theme';
    const savedTheme = localStorage.getItem(storageKey);

    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
})();

// Dark mode functionality
class DarkModeManager {
    constructor() {
        this.themeToggle = null;
        // Get the current theme from the HTML element that was set by the IIFE
        this.currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        this.storageKey = 'inventory-app-theme';

        this.init();
    }

    init() {
        this.themeToggle = document.getElementById('themeToggle');
        this.loadSavedTheme();
        this.setupEventListeners();
        this.setupSystemThemeListener();
    }

    setupEventListeners() {
        if (this.themeToggle) {
            this.themeToggle.addEventListener('change', (e) => {
                this.toggleTheme();
            });
        }
    }

    setupSystemThemeListener() {
        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addListener((e) => {
            // Only auto-switch if user hasn't manually set a preference
            const savedTheme = localStorage.getItem(this.storageKey);
            if (!savedTheme) {
                this.setTheme(e.matches ? 'dark' : 'light', false);
            }
        });
    }

    loadSavedTheme() {
        // Sync the toggle button with the current theme (already set by IIFE)
        if (this.themeToggle) {
            this.themeToggle.checked = this.currentTheme === 'dark';
        }
        console.log(`Current theme initialized as: ${this.currentTheme}`);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme, true);
    }

    setTheme(theme, save = true) {
        const previousTheme = this.currentTheme;
        this.currentTheme = theme;

        // Add transition class to prevent flash
        document.documentElement.classList.add('theme-transitioning');

        // Update data attribute
        document.documentElement.setAttribute('data-theme', theme);

        // Update toggle button
        if (this.themeToggle) {
            this.themeToggle.checked = theme === 'dark';
        }

        // Save preference
        if (save) {
            localStorage.setItem(this.storageKey, theme);
        }

        // Remove transition class after animation completes
        setTimeout(() => {
            document.documentElement.classList.remove('theme-transitioning');
        }, 250);

        // Dispatch theme change event
        this.dispatchThemeChangeEvent(theme, previousTheme);
    }

    dispatchThemeChangeEvent(theme, previousTheme) {
        const event = new CustomEvent('themechange', {
            detail: { theme, previousTheme }
        });
        window.dispatchEvent(event);
    }

    getCurrentTheme() {
        return this.currentTheme;
    }

    isDarkMode() {
        return this.currentTheme === 'dark';
    }

    isLightMode() {
        return this.currentTheme === 'light';
    }

    // Method to programmatically set theme (for use by other components)
    setDarkMode() {
        this.setTheme('dark', true);
    }

    setLightMode() {
        this.setTheme('light', true);
    }

    // Reset to system preference
    resetToSystemTheme() {
        localStorage.removeItem(this.storageKey);
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.setTheme(prefersDark ? 'dark' : 'light', false);
    }

    // Theme-aware color utilities
    getThemeColors() {
        const style = getComputedStyle(document.documentElement);
        return {
            bgPrimary: style.getPropertyValue('--bg-primary').trim(),
            bgSecondary: style.getPropertyValue('--bg-secondary').trim(),
            textPrimary: style.getPropertyValue('--text-primary').trim(),
            textSecondary: style.getPropertyValue('--text-secondary').trim(),
            accentBlue: style.getPropertyValue('--accent-blue').trim(),
            success: style.getPropertyValue('--success').trim(),
            warning: style.getPropertyValue('--warning').trim(),
            danger: style.getPropertyValue('--danger').trim()
        };
    }

    // Apply theme to dynamically created elements
    applyThemeToElement(element) {
        if (!element) return;

        // This method can be used to ensure dynamically created elements
        // properly inherit the current theme
        const currentTheme = this.getCurrentTheme();
        element.setAttribute('data-theme', currentTheme);
    }

    // Theme transition animations
    enableTransitions() {
        document.documentElement.style.setProperty(
            '--transition-theme',
            'background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease'
        );
    }

    disableTransitions() {
        document.documentElement.style.setProperty('--transition-theme', 'none');
    }

    // Accessibility helpers
    announceThemeChange() {
        const announcement = this.isDarkMode() ?
            'Switched to dark mode' :
            'Switched to light mode';

        // Create an accessible announcement
        const ariaLive = document.createElement('div');
        ariaLive.setAttribute('aria-live', 'polite');
        ariaLive.setAttribute('aria-atomic', 'true');
        ariaLive.className = 'sr-only';
        ariaLive.textContent = announcement;

        document.body.appendChild(ariaLive);

        // Remove after announcement
        setTimeout(() => {
            if (ariaLive.parentNode) {
                ariaLive.parentNode.removeChild(ariaLive);
            }
        }, 1000);
    }

    // Debug method
    logThemeInfo() {
        console.log('Theme Manager Info:', {
            currentTheme: this.currentTheme,
            savedTheme: localStorage.getItem(this.storageKey),
            systemPreference: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
            colors: this.getThemeColors()
        });
    }
}

// Initialize dark mode manager
document.addEventListener('DOMContentLoaded', () => {
    window.darkModeManager = new DarkModeManager();

    // Listen for theme change events
    window.addEventListener('themechange', (e) => {
        // Update any components that need to know about theme changes
        console.log(`Theme changed from ${e.detail.previousTheme} to ${e.detail.theme}`);

        // Debug: Check if data-theme attribute is actually set
        const currentDataTheme = document.documentElement.getAttribute('data-theme');
        console.log(`Data-theme attribute is now: ${currentDataTheme}`);

        // Example: Update chart colors, refresh images, etc.
        // if (window.chartManager) {
        //     window.chartManager.updateTheme(e.detail.theme);
        // }
    });
});

// Add CSS for screen reader only content
document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
    `;
    document.head.appendChild(style);
});