/**
 * Onboarding Tour
 * 
 * Provides an interactive tour for new users to learn about gamification features.
 */

class OnboardingTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [
            {
                target: '.level-info',
                title: '⭐ XP & Levels',
                content: 'Earn XP by completing quizzes, study guides, and evaluations. Level up to unlock new titles and show your progress!',
                position: 'bottom'
            },
            {
                target: '.streak-info',
                title: '🔥 Streaks',
                content: 'Build your study streak by earning XP every day. Use streak freezes to protect your streak when you need a break!',
                position: 'bottom'
            },
            {
                target: '.tab-button[data-tab="badges"]',
                title: '🏆 Badges',
                content: 'Earn badges by completing special achievements. Collect Bronze, Silver, and Gold tiers for each badge!',
                position: 'bottom'
            },
            {
                target: '.gamification-dashboard',
                title: '📊 Your Dashboard',
                content: 'Track all your stats, activities, and progress here. See how close you are to your next level!',
                position: 'top'
            },
            {
                target: '.share-section',
                title: '📤 Share Your Progress',
                content: 'Create beautiful graphics to share your achievements on social media or download for your records!',
                position: 'top'
            }
        ];

        this.init();
    }

    /**
     * Escape HTML to prevent XSS attacks
     */
    escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    init() {
        // Check if user has completed tour
        if (localStorage.getItem('onboarding_completed') === 'true') {
            return;
        }

        // Check if this is first visit
        const visitCount = parseInt(localStorage.getItem('visit_count') || '0');
        localStorage.setItem('visit_count', (visitCount + 1).toString());

        if (visitCount === 0) {
            // Show tour on first visit
            setTimeout(() => this.start(), 2000);
        }
    }

    /**
     * Start the tour
     */
    start() {
        console.log('[OnboardingTour] Starting tour...');
        
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay active';
        document.body.appendChild(this.overlay);

        // Show first step
        this.currentStep = 0;
        this.showStep(this.currentStep);
    }

    /**
     * Show a specific step
     */
    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) {
            this.complete();
            return;
        }

        const step = this.steps[stepIndex];
        const target = document.querySelector(step.target);

        if (!target) {
            console.warn('[OnboardingTour] Target not found:', step.target);
            this.next();
            return;
        }

        // Remove previous tooltip
        const existingTooltip = document.querySelector('.onboarding-tooltip');
        if (existingTooltip) {
            existingTooltip.remove();
        }

        // Highlight target
        this.highlightElement(target);

        // Create tooltip
        const tooltip = this.createTooltip(step, stepIndex);
        document.body.appendChild(tooltip);

        // Position tooltip
        this.positionTooltip(tooltip, target, step.position);
    }

    /**
     * Highlight target element
     */
    highlightElement(element) {
        // Remove previous highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });

        // Add highlight
        element.classList.add('onboarding-highlight');
        element.style.position = 'relative';
        element.style.zIndex = '10003';
    }

    /**
     * Create tooltip element
     */
    createTooltip(step, stepIndex) {
        const tooltip = document.createElement('div');
        tooltip.className = 'onboarding-tooltip';

        // Sanitize step data
        const safeTitle = this.escapeHtml(step.title);
        const safeContent = this.escapeHtml(step.content);
        const safeStepIndex = parseInt(stepIndex, 10);
        const safeStepsLength = parseInt(this.steps.length, 10);

        tooltip.innerHTML = `
            <div class="onboarding-tooltip-title">${safeTitle}</div>
            <div class="onboarding-tooltip-content">${safeContent}</div>
            <div class="onboarding-tooltip-buttons">
                <button class="onboarding-btn onboarding-btn-skip">Skip Tour</button>
                ${safeStepIndex > 0 ? '<button class="onboarding-btn onboarding-btn-back">Back</button>' : ''}
                <button class="onboarding-btn onboarding-btn-next">
                    ${safeStepIndex === safeStepsLength - 1 ? 'Finish' : 'Next'}
                </button>
            </div>
            <div class="onboarding-progress">
                Step ${safeStepIndex + 1} of ${safeStepsLength}
            </div>
        `;

        // Add event listeners with { once: true }
        tooltip.querySelector('.onboarding-btn-skip').addEventListener('click', () => this.skip(), { once: true });

        const backBtn = tooltip.querySelector('.onboarding-btn-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.back(), { once: true });
        }

        tooltip.querySelector('.onboarding-btn-next').addEventListener('click', () => this.next(), { once: true });

        return tooltip;
    }

    /**
     * Position tooltip relative to target
     */
    positionTooltip(tooltip, target, position) {
        const targetRect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top, left;

        switch (position) {
            case 'top':
                top = targetRect.top - tooltipRect.height - 20;
                left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = targetRect.bottom + 20;
                left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
                left = targetRect.left - tooltipRect.width - 20;
                break;
            case 'right':
                top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
                left = targetRect.right + 20;
                break;
            default:
                top = targetRect.bottom + 20;
                left = targetRect.left;
        }

        // Keep tooltip within viewport
        const margin = 20;
        top = Math.max(margin, Math.min(top, window.innerHeight - tooltipRect.height - margin));
        left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }

    /**
     * Go to next step
     */
    next() {
        this.currentStep++;
        this.showStep(this.currentStep);
    }

    /**
     * Go to previous step
     */
    back() {
        this.currentStep--;
        this.showStep(this.currentStep);
    }

    /**
     * Skip tour
     */
    skip() {
        if (confirm('Are you sure you want to skip the tour? You can restart it from settings.')) {
            this.complete();
        }
    }

    /**
     * Complete tour
     */
    complete() {
        console.log('[OnboardingTour] Tour completed');

        // Remove overlay and tooltip
        if (this.overlay) {
            this.overlay.remove();
        }

        const tooltip = document.querySelector('.onboarding-tooltip');
        if (tooltip) {
            tooltip.remove();
        }

        // Remove highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
            el.style.position = '';
            el.style.zIndex = '';
        });

        // Mark as completed
        localStorage.setItem('onboarding_completed', 'true');

        // Show completion message
        this.showCompletionMessage();
    }

    /**
     * Show completion message
     */
    showCompletionMessage() {
        const message = document.createElement('div');
        message.className = 'download-notification';
        message.innerHTML = `
            <div class="download-notification-content">
                🎉 Welcome to LLS Study Portal! Start earning XP now!
            </div>
        `;

        document.body.appendChild(message);

        setTimeout(() => message.classList.add('show'), 10);

        setTimeout(() => {
            message.classList.remove('show');
            setTimeout(() => message.remove(), 300);
        }, 4000);
    }

    /**
     * Restart tour (can be called from settings)
     */
    restart() {
        localStorage.removeItem('onboarding_completed');
        this.start();
    }
}

// Add CSS for highlight effect
const style = document.createElement('style');
style.textContent = `
    .onboarding-highlight {
        box-shadow: 0 0 0 4px rgba(212, 175, 55, 0.5), 0 0 0 9999px rgba(0, 0, 0, 0.5) !important;
        border-radius: 10px;
    }
`;
document.head.appendChild(style);

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.onboardingTour = new OnboardingTour();
    });
} else {
    window.onboardingTour = new OnboardingTour();
}

// Add restart button to settings (if settings exist)
document.addEventListener('DOMContentLoaded', () => {
    const settingsSection = document.querySelector('.settings-section');
    if (settingsSection) {
        const restartButton = document.createElement('button');
        restartButton.className = 'btn btn-secondary';
        restartButton.textContent = '🎓 Restart Onboarding Tour';
        restartButton.addEventListener('click', () => {
            if (window.onboardingTour) {
                window.onboardingTour.restart();
            }
        });
        settingsSection.appendChild(restartButton);
    }
});

