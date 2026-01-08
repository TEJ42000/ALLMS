/**
 * Cookie Consent Banner
 * GDPR-compliant cookie consent management
 */

(function() {
    'use strict';

    const COOKIE_CONSENT_KEY = 'cookie_consent';
    const COOKIE_CONSENT_VERSION = '1.0';

    // Check if consent has already been given
    function hasConsent() {
        const consent = localStorage.getItem(COOKIE_CONSENT_KEY);
        if (!consent) return false;
        
        try {
            const consentData = JSON.parse(consent);
            return consentData.version === COOKIE_CONSENT_VERSION;
        } catch (e) {
            return false;
        }
    }

    // Get current consent preferences
    function getConsentPreferences() {
        const consent = localStorage.getItem(COOKIE_CONSENT_KEY);
        if (!consent) {
            return {
                essential: true,
                functional: false,
                analytics: false,
                timestamp: null,
                version: COOKIE_CONSENT_VERSION
            };
        }
        
        try {
            return JSON.parse(consent);
        } catch (e) {
            return {
                essential: true,
                functional: false,
                analytics: false,
                timestamp: null,
                version: COOKIE_CONSENT_VERSION
            };
        }
    }

    // Save consent preferences
    function saveConsentPreferences(preferences) {
        const consentData = {
            ...preferences,
            timestamp: new Date().toISOString(),
            version: COOKIE_CONSENT_VERSION
        };
        localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(consentData));
        
        // Apply consent preferences
        applyConsentPreferences(preferences);
        
        // Send to backend if user is logged in
        sendConsentToBackend(preferences);
    }

    // Apply consent preferences (enable/disable features)
    function applyConsentPreferences(preferences) {
        // Functional cookies
        if (!preferences.functional) {
            // Disable functional features
            console.log('Functional cookies disabled');
        }
        
        // Analytics cookies
        if (!preferences.analytics) {
            // Disable analytics
            console.log('Analytics cookies disabled');
            // Disable Google Analytics, etc.
        } else {
            // Enable analytics
            console.log('Analytics cookies enabled');
        }
    }

    // Get user ID from localStorage or generate new one
    function getUserId() {
        let userId = localStorage.getItem('allms_user_id');
        if (!userId) {
            userId = 'sim-' + crypto.randomUUID();
            localStorage.setItem('allms_user_id', userId);
        }
        return userId;
    }

    // Send consent to backend
    async function sendConsentToBackend(preferences) {
        try:
            // Only send if user is logged in
            const userId = getUserId();
            if (!userId) return;
            
            // Send each consent type
            const consentTypes = [
                { type: 'functional', enabled: preferences.functional },
                { type: 'analytics', enabled: preferences.analytics }
            ];
            
            for (const consent of consentTypes) {
                await fetch('/api/gdpr/consent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-ID': userId
                    },
                    body: JSON.stringify({
                        consent_type: consent.type,
                        status: consent.enabled ? 'granted' : 'revoked'
                    })
                });
            }
        } catch (error) {
            console.error('Error sending consent to backend:', error);
        }
    }

    // Create cookie consent banner HTML
    function createConsentBanner() {
        const banner = document.createElement('div');
        banner.id = 'cookie-consent-banner';
        banner.innerHTML = `
            <div class="cookie-consent-content">
                <div class="cookie-consent-text">
                    <h3>🍪 We use cookies</h3>
                    <p>We use cookies to enhance your experience, analyze site usage, and provide personalized content. You can customize your preferences or accept all cookies.</p>
                </div>
                <div class="cookie-consent-buttons">
                    <button id="cookie-accept-all" class="cookie-btn cookie-btn-primary">Accept All</button>
                    <button id="cookie-customize" class="cookie-btn cookie-btn-secondary">Customize</button>
                    <button id="cookie-reject-optional" class="cookie-btn cookie-btn-tertiary">Reject Optional</button>
                </div>
            </div>
            <div id="cookie-preferences" class="cookie-preferences" style="display: none;">
                <h3>Cookie Preferences</h3>
                <div class="cookie-option">
                    <label>
                        <input type="checkbox" id="consent-essential" checked disabled>
                        <span class="cookie-label">
                            <strong>Essential Cookies</strong>
                            <small>Required for basic functionality (cannot be disabled)</small>
                        </span>
                    </label>
                </div>
                <div class="cookie-option">
                    <label>
                        <input type="checkbox" id="consent-functional">
                        <span class="cookie-label">
                            <strong>Functional Cookies</strong>
                            <small>Remember your preferences and settings</small>
                        </span>
                    </label>
                </div>
                <div class="cookie-option">
                    <label>
                        <input type="checkbox" id="consent-analytics">
                        <span class="cookie-label">
                            <strong>Analytics Cookies</strong>
                            <small>Help us understand how you use the site</small>
                        </span>
                    </label>
                </div>
                <div class="cookie-preferences-buttons">
                    <button id="cookie-save-preferences" class="cookie-btn cookie-btn-primary">Save Preferences</button>
                    <button id="cookie-cancel" class="cookie-btn cookie-btn-secondary">Cancel</button>
                </div>
                <p class="cookie-policy-link">
                    <a href="/privacy-policy" target="_blank">Privacy Policy</a> | 
                    <a href="/cookie-policy" target="_blank">Cookie Policy</a>
                </p>
            </div>
        `;
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #cookie-consent-banner {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: white;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
                z-index: 10000;
                padding: 20px;
                animation: slideUp 0.3s ease-out;
            }
            @keyframes slideUp {
                from { transform: translateY(100%); }
                to { transform: translateY(0); }
            }
            .cookie-consent-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
            }
            .cookie-consent-text h3 {
                margin: 0 0 10px 0;
                color: #2c3e50;
            }
            .cookie-consent-text p {
                margin: 0;
                color: #555;
                font-size: 14px;
            }
            .cookie-consent-buttons {
                display: flex;
                gap: 10px;
                flex-shrink: 0;
            }
            .cookie-btn {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s;
            }
            .cookie-btn-primary {
                background: #3498db;
                color: white;
            }
            .cookie-btn-primary:hover {
                background: #2980b9;
            }
            .cookie-btn-secondary {
                background: #ecf0f1;
                color: #2c3e50;
            }
            .cookie-btn-secondary:hover {
                background: #d5dbdb;
            }
            .cookie-btn-tertiary {
                background: transparent;
                color: #7f8c8d;
                border: 1px solid #bdc3c7;
            }
            .cookie-btn-tertiary:hover {
                background: #f8f9fa;
            }
            .cookie-preferences {
                max-width: 1200px;
                margin: 20px auto 0;
                padding-top: 20px;
                border-top: 1px solid #ecf0f1;
            }
            .cookie-preferences h3 {
                margin: 0 0 15px 0;
                color: #2c3e50;
            }
            .cookie-option {
                margin-bottom: 15px;
            }
            .cookie-option label {
                display: flex;
                align-items: flex-start;
                cursor: pointer;
            }
            .cookie-option input[type="checkbox"] {
                margin-right: 10px;
                margin-top: 3px;
            }
            .cookie-label {
                flex: 1;
            }
            .cookie-label strong {
                display: block;
                color: #2c3e50;
                margin-bottom: 3px;
            }
            .cookie-label small {
                display: block;
                color: #7f8c8d;
                font-size: 13px;
            }
            .cookie-preferences-buttons {
                margin-top: 20px;
                display: flex;
                gap: 10px;
            }
            .cookie-policy-link {
                margin-top: 15px;
                font-size: 13px;
                color: #7f8c8d;
            }
            .cookie-policy-link a {
                color: #3498db;
                text-decoration: none;
            }
            .cookie-policy-link a:hover {
                text-decoration: underline;
            }
            @media (max-width: 768px) {
                .cookie-consent-content {
                    flex-direction: column;
                    align-items: stretch;
                }
                .cookie-consent-buttons {
                    flex-direction: column;
                }
            }
        `;
        document.head.appendChild(style);
        
        return banner;
    }

    // Show cookie consent banner
    function showConsentBanner() {
        const banner = createConsentBanner();
        document.body.appendChild(banner);
        
        // Event listeners
        document.getElementById('cookie-accept-all').addEventListener('click', () => {
            saveConsentPreferences({
                essential: true,
                functional: true,
                analytics: true
            });
            banner.remove();
        });
        
        document.getElementById('cookie-reject-optional').addEventListener('click', () => {
            saveConsentPreferences({
                essential: true,
                functional: false,
                analytics: false
            });
            banner.remove();
        });
        
        document.getElementById('cookie-customize').addEventListener('click', () => {
            document.getElementById('cookie-preferences').style.display = 'block';
            document.querySelector('.cookie-consent-content').style.display = 'none';
        });
        
        document.getElementById('cookie-cancel').addEventListener('click', () => {
            document.getElementById('cookie-preferences').style.display = 'none';
            document.querySelector('.cookie-consent-content').style.display = 'flex';
        });
        
        document.getElementById('cookie-save-preferences').addEventListener('click', () => {
            const preferences = {
                essential: true,
                functional: document.getElementById('consent-functional').checked,
                analytics: document.getElementById('consent-analytics').checked
            };
            saveConsentPreferences(preferences);
            banner.remove();
        });
    }

    // Initialize cookie consent
    function initCookieConsent() {
        if (!hasConsent()) {
            // Show banner after a short delay
            setTimeout(showConsentBanner, 1000);
        } else {
            // Apply existing preferences
            const preferences = getConsentPreferences();
            applyConsentPreferences(preferences);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCookieConsent);
    } else {
        initCookieConsent();
    }

    // Expose function to re-show consent banner
    window.showCookieConsent = showConsentBanner;
})();

