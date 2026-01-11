/**
 * Shared Utility Functions
 *
 * Common utilities used across multiple JavaScript files.
 *
 * Security utilities:
 * - escapeHtml: XSS prevention
 * - getCSRFToken: CSRF token retrieval
 * - secureFetch: Fetch wrapper with CSRF protection
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

/**
 * CSRF Protection Utilities
 *
 * Implements client-side support for double-submit cookie CSRF pattern.
 * Issue: #204
 */

const CSRF_COOKIE_NAME = 'csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * Get CSRF token from cookie
 *
 * @returns {string|null} - The CSRF token or null if not found
 *
 * @example
 * const token = getCSRFToken();
 * if (token) {
 *     headers['X-CSRF-Token'] = token;
 * }
 */
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === CSRF_COOKIE_NAME) {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/**
 * Secure fetch wrapper that automatically includes CSRF token
 *
 * Use this for all mutating requests (POST, PUT, PATCH, DELETE).
 * GET/HEAD/OPTIONS requests don't need CSRF but can use this safely.
 *
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options (same as standard fetch)
 * @returns {Promise<Response>} - The fetch response
 *
 * @example
 * // POST request with automatic CSRF
 * const response = await secureFetch('/api/data', {
 *     method: 'POST',
 *     headers: {'Content-Type': 'application/json'},
 *     body: JSON.stringify(data)
 * });
 */
async function secureFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();

    // Only add CSRF token for mutating methods
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrfToken = getCSRFToken();

        if (csrfToken) {
            // Merge CSRF header with existing headers
            options.headers = {
                ...options.headers,
                [CSRF_HEADER_NAME]: csrfToken
            };
        } else {
            console.warn('[secureFetch] CSRF token not found. Request may fail.');
        }
    }

    return fetch(url, options);
}

/**
 * Add CSRF token to existing headers object
 *
 * Use this when you need to manually construct headers but still want CSRF.
 *
 * @param {Object} headers - Existing headers object
 * @returns {Object} - Headers with CSRF token added
 *
 * @example
 * const headers = addCSRFHeader({
 *     'Content-Type': 'application/json',
 *     'X-User-ID': userId
 * });
 */
function addCSRFHeader(headers = {}) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
        return {
            ...headers,
            [CSRF_HEADER_NAME]: csrfToken
        };
    }
    return headers;
}

/**
 * Enhanced Notification System
 *
 * Issue #208: Improve frontend error messages with actionable guidance
 *
 * Features:
 * - Action buttons (links or callbacks)
 * - Countdown timer for rate limits
 * - Dismissible notifications
 * - Accessible (screen reader friendly)
 */

class EnhancedNotification {
    /**
     * Create an enhanced notification
     *
     * @param {string} message - Message to display
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {Object} options - Additional options
     * @param {number} options.duration - Duration in ms (0 = manual close only)
     * @param {string} options.action - Action button text
     * @param {string} options.actionUrl - URL for action button (opens in same window)
     * @param {Function} options.actionCallback - Callback for action button
     * @param {number} options.countdown - Countdown timer in seconds
     * @param {boolean} options.dismissible - Whether notification can be closed
     */
    constructor(message, type, options = {}) {
        this.message = message;
        this.type = type || 'info';
        this.options = {
            duration: options.duration !== undefined ? options.duration : 5000,
            action: options.action || null,
            actionUrl: options.actionUrl || null,
            actionCallback: options.actionCallback || null,
            countdown: options.countdown || null,
            dismissible: options.dismissible !== false
        };
        this.element = null;
        this.countdownInterval = null;
    }

    /**
     * Show the notification
     */
    show() {
        // Remove existing notifications
        const existing = document.querySelectorAll('.enhanced-notification');
        existing.forEach(el => el.remove());

        this.element = this.createNotificationElement();
        document.body.appendChild(this.element);

        // Animate in
        setTimeout(() => this.element.classList.add('show'), 10);

        // Start countdown if specified
        if (this.options.countdown) {
            this.startCountdown();
        }

        // Auto-dismiss after duration
        if (this.options.duration && this.options.duration > 0 && !this.options.countdown) {
            setTimeout(() => this.dismiss(), this.options.duration);
        }
    }

    /**
     * Create the notification DOM element
     */
    createNotificationElement() {
        const div = document.createElement('div');
        div.className = `enhanced-notification notification-toast notification-${this.type}`;
        div.setAttribute('role', 'alert');
        div.setAttribute('aria-live', 'polite');

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        let html = `
            <div class="notification-content">
                <span class="notification-icon" aria-hidden="true">${icons[this.type] || icons.info}</span>
                <span class="notification-message">${escapeHtml(this.message)}</span>
                ${this.options.countdown ? `<span class="notification-countdown" aria-live="polite">${this.options.countdown}s</span>` : ''}
            </div>
        `;

        // Add action button if specified
        if (this.options.action) {
            if (this.options.actionUrl) {
                html += `<a href="${escapeHtml(this.options.actionUrl)}" class="notification-action">${escapeHtml(this.options.action)}</a>`;
            } else if (this.options.actionCallback) {
                html += `<button type="button" class="notification-action" data-action="callback">${escapeHtml(this.options.action)}</button>`;
            }
        }

        // Add close button
        if (this.options.dismissible) {
            html += '<button type="button" class="notification-close" aria-label="Close notification">&times;</button>';
        }

        div.innerHTML = html;

        // Attach event listeners
        const closeBtn = div.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.dismiss());
        }

        const actionBtn = div.querySelector('.notification-action[data-action="callback"]');
        if (actionBtn && this.options.actionCallback) {
            actionBtn.addEventListener('click', () => {
                this.options.actionCallback();
                this.dismiss();
            });
        }

        return div;
    }

    /**
     * Start countdown timer
     */
    startCountdown() {
        let remaining = this.options.countdown;
        const countdownEl = this.element.querySelector('.notification-countdown');
        const actionBtn = this.element.querySelector('.notification-action');

        // Disable action button during countdown
        if (actionBtn) {
            actionBtn.disabled = true;
            actionBtn.classList.add('disabled');
        }

        this.countdownInterval = setInterval(() => {
            remaining--;
            if (countdownEl) {
                countdownEl.textContent = `${remaining}s`;
            }

            if (remaining <= 0) {
                clearInterval(this.countdownInterval);
                if (actionBtn) {
                    actionBtn.disabled = false;
                    actionBtn.classList.remove('disabled');
                }
                if (countdownEl) {
                    countdownEl.textContent = 'Ready';
                }
            }
        }, 1000);
    }

    /**
     * Dismiss the notification
     */
    dismiss() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        if (this.element) {
            this.element.classList.remove('show');
            setTimeout(() => {
                if (this.element && this.element.parentNode) {
                    this.element.remove();
                }
            }, 300);
        }
    }
}

/**
 * Show an enhanced notification with action buttons and countdown support
 *
 * @param {string} message - Message to display
 * @param {string} type - 'success', 'error', 'warning', 'info'
 * @param {Object} options - Additional options (action, actionUrl, actionCallback, countdown)
 * @returns {EnhancedNotification} - The notification instance
 *
 * @example
 * // Simple notification
 * showEnhancedNotification('File uploaded!', 'success');
 *
 * // With action button
 * showEnhancedNotification('Upload failed', 'error', {
 *     action: 'Retry',
 *     actionCallback: () => retryUpload()
 * });
 *
 * // With countdown
 * showEnhancedNotification('Rate limited', 'warning', {
 *     countdown: 60,
 *     action: 'Retry',
 *     actionCallback: () => retryUpload()
 * });
 */
function showEnhancedNotification(message, type, options = {}) {
    const notification = new EnhancedNotification(message, type, options);
    notification.show();
    return notification;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        showNotification,
        showEnhancedNotification,
        EnhancedNotification,
        getCSRFToken,
        secureFetch,
        addCSRFHeader
    };
}
