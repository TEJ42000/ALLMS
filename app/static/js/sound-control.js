/**
 * Sound Control
 * 
 * Provides a UI control for enabling/disabling sound effects.
 */

class SoundControl {
    constructor() {
        this.enabled = localStorage.getItem('gamification_sound') !== 'false';
        this.init();
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
     * Toggle sound
     */
    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('gamification_sound', this.enabled);
        this.updateIcon();

        // Notify animations component
        if (window.gamificationAnimations) {
            window.gamificationAnimations.soundEnabled = this.enabled;
        }

        // Show feedback
        this.showFeedback();
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

