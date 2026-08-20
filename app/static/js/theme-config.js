/**
 * Theme & Color Palette Manager for NexusSaaS
 * Allows changing and previewing color palettes dynamically.
 */
(function() {
    window.NexusTheme = {
        /**
         * Set the active theme preset ('slate', 'charcoal', 'indigo', 'emerald', 'midnight')
         * @param {string} presetName 
         */
        setPreset: function(presetName) {
            if (!presetName || presetName === 'slate' || presetName === 'default') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.removeItem('nexus_palette_preset');
            } else {
                document.documentElement.setAttribute('data-theme', presetName);
                localStorage.setItem('nexus_palette_preset', presetName);
            }
        },

        /**
         * Get the currently active theme preset
         */
        getPreset: function() {
            return localStorage.getItem('nexus_palette_preset') || 'slate';
        },

        /**
         * Set a custom primary hex color on the fly
         * @param {string} hexColor e.g. '#0f172a'
         */
        setCustomPrimary: function(hexColor) {
            document.documentElement.style.setProperty('--brand-primary', hexColor);
            localStorage.setItem('nexus_custom_primary', hexColor);
        },

        /**
         * Initialize saved palette on load
         */
        init: function() {
            const savedPreset = localStorage.getItem('nexus_palette_preset');
            if (savedPreset) {
                document.documentElement.setAttribute('data-theme', savedPreset);
            }
            const customPrimary = localStorage.getItem('nexus_custom_primary');
            if (customPrimary) {
                document.documentElement.style.setProperty('--brand-primary', customPrimary);
            }
        }
    };

    // Run initialization immediately
    window.NexusTheme.init();
})();
