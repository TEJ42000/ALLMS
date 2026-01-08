/**
 * Shared Utility Functions
 * 
 * Common utilities used across multiple JavaScript files.
 * MEDIUM FIX: Consolidate duplicate functions to avoid code duplication.
 */

/**
 * Escape HTML to prevent XSS attacks
 * 
 * Converts special characters to HTML entities to prevent script injection.
 * This is the single source of truth for HTML escaping across the application.
 * 
 * @param {string} text - The text to escape
 * @returns {string} - The escaped HTML-safe text
 * 
 * @example
 * escapeHtml('<script>alert("xss")</script>')
 * // Returns: '&lt;script&gt;alert("xss")&lt;/script&gt;'
 */
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { escapeHtml };
}

