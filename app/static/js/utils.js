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

/**
 * CRITICAL FIX: Show styled notification instead of alert()
 *
 * Displays a styled toast notification with auto-dismiss.
 * Replaces browser alert() for better UX.
 *
 * @param {string} message - Message to display
 * @param {string} type - Notification type: 'info', 'warning', 'error', 'success'
 * @param {number} duration - Duration in milliseconds (0 = manual close only)
 *
 * @example
 * showNotification('Data saved successfully!', 'success', 3000);
 * showNotification('Storage quota exceeded', 'error', 0);
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notification if any
    const existing = document.querySelector('.notification-toast');
    if (existing) {
        existing.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-toast notification-${type}`;

    // Icon based on type
    const icons = {
        info: 'ℹ️',
        warning: '⚠️',
        error: '❌',
        success: '✅'
    };

    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${icons[type] || icons.info}</span>
            <span class="notification-message">${escapeHtml(message)}</span>
            <button class="notification-close" aria-label="Close notification">×</button>
        </div>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    });

    // Auto-close after duration
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { escapeHtml, showNotification };
}
