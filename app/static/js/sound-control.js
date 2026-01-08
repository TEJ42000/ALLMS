/**
 * Sound Control
 * 
 * Provides a UI control for enabling/disabling sound effects.
 */

class SoundControl {
    constructor() {
        this.enabled = this.safeGetLocalStorage('gamification_sound') !== 'false';
        this.init();
    }

    /**
     * Safe localStorage getter with error handling
     */
    safeGetLocalStorage(key, defaultValue = null) {
        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.warn('[SoundControl] localStorage.getItem failed:', error.message);
            return defaultValue;
        }
    }

    /**
     * Safe localStorage setter with QuotaExceededError handling
     */
    safeSetLocalStorage(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (error) {
            if (error.name === 'QuotaExceededError') {
                console.warn('[SoundControl] localStorage quota exceeded');
                // Show user notification
                this.showQuotaError();
                return false;
            } else {
                console.error('[SoundControl] localStorage.setItem failed:', error.message);
                return false;
            }
        }
    }

    init() {
        console.log('[SoundControl] Initializing...');
        this.createControl();
        this.updateIcon();
    }

    /**
     * Create sound control button
     */
    createControl() {
        const control = document.createElement('div');
        control.className = 'sound-control';
        control.setAttribute('role', 'button');
        control.setAttribute('aria-label', 'Toggle sound effects');
        control.setAttribute('tabindex', '0');
        control.innerHTML = `
            <span class="sound-control-icon">🔊</span>
        `;

        // Event listeners don't need { once: true } as control persists
        control.addEventListener('click', () => this.toggle());
        control.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.toggle();
            }
        });

        document.body.appendChild(control);
        this.control = control;
    }

    /**
     * Toggle sound with safe localStorage
     */
    toggle() {
        this.enabled = !this.enabled;
        this.safeSetLocalStorage('gamification_sound', this.enabled);
        this.updateIcon();

        // Notify animations component
        if (window.gamificationAnimations) {
            window.gamificationAnimations.soundEnabled = this.enabled;
        }

        // Show feedback
        this.showFeedback();
    }

    /**
     * Show quota exceeded error
     */
    showQuotaError() {
        const feedback = document.createElement('div');
        feedback.className = 'download-notification';
        feedback.style.background = '#e74c3c';
        feedback.innerHTML = `
            <div class="download-notification-content">
                ⚠️ Storage quota exceeded. Please clear browser data.
            </div>
        `;

        document.body.appendChild(feedback);
        setTimeout(() => feedback.classList.add('show'), 10);
        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => feedback.remove(), 300);
        }, 4000);
    }

    /**
     * Update icon
     */
    updateIcon() {
        const icon = this.control.querySelector('.sound-control-icon');
        icon.textContent = this.enabled ? '🔊' : '🔇';
        this.control.setAttribute('aria-label', 
            this.enabled ? 'Mute sound effects' : 'Unmute sound effects'
        );
    }

    /**
     * Show feedback
     */
    showFeedback() {
        const feedback = document.createElement('div');
        feedback.className = 'download-notification';
        feedback.innerHTML = `
            <div class="download-notification-content">
                ${this.enabled ? '🔊 Sound effects enabled' : '🔇 Sound effects muted'}
            </div>
        `;

        document.body.appendChild(feedback);

        setTimeout(() => feedback.classList.add('show'), 10);

        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => feedback.remove(), 300);
        }, 2000);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.soundControl = new SoundControl();
    });
} else {
    window.soundControl = new SoundControl();
}

