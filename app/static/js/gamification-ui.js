/**
 * Gamification UI
 * 
 * Handles displaying gamification data in the dashboard UI.
 */

class GamificationUI {
    constructor() {
        this.stats = null;
        this.levelProgressBar = null;
        this.init();
    }
    
    /**
     * Initialize the gamification UI
     */
    async init() {
        console.log('[GamificationUI] Initializing...');
        
        // Load stats
        await this.loadStats();
        
        // Update dashboard
        this.updateDashboard();
        
        // Add level progress bar to header
        this.addLevelProgressBar();
        
        // Listen for XP updates
        this.setupEventListeners();
        
        console.log('[GamificationUI] Initialized');
    }
    
    /**
     * Load user stats from API
     */
    async loadStats() {
        try {
            const response = await fetch('/api/gamification/stats');
            if (response.ok) {
                this.stats = await response.json();
                console.log('[GamificationUI] Stats loaded:', this.stats);
            } else {
                console.error('[GamificationUI] Failed to load stats:', response.status);
            }
        } catch (error) {
            console.error('[GamificationUI] Error loading stats:', error);
        }
    }
    
    /**
     * Update dashboard stat cards
     */
    updateDashboard() {
        if (!this.stats) return;
        
        // Update Total Points card
        const pointsEl = document.getElementById('stat-points');
        if (pointsEl) {
            pointsEl.textContent = this.stats.total_xp.toLocaleString();
            
            // Update label to show level
            const pointsLabel = pointsEl.nextElementSibling;
            if (pointsLabel) {
                pointsLabel.innerHTML = `
                    <div style="font-size: 0.9em; font-weight: 600; color: var(--primary-color);">
                        ${this.stats.level_title}
                    </div>
                    <div style="font-size: 0.75em; opacity: 0.8;">
                        Level ${this.stats.current_level} • ${this.stats.xp_to_next_level} XP to next
                    </div>
                `;
            }
        }
        
        // Update Day Streak card
        const streakEl = document.getElementById('stat-streak');
        if (streakEl) {
            streakEl.textContent = this.stats.streak.current_count;
            
            // Update label to show freezes
            const streakLabel = streakEl.nextElementSibling;
            if (streakLabel && this.stats.streak.freezes_available > 0) {
                streakLabel.innerHTML = `
                    Day Streak
                    <div style="font-size: 0.75em; opacity: 0.8;">
                        ❄️ ${this.stats.streak.freezes_available} freeze${this.stats.streak.freezes_available !== 1 ? 's' : ''} available
                    </div>
                `;
            }
        }
        
        // Update Topics Studied card
        const topicsEl = document.getElementById('stat-topics');
        if (topicsEl) {
            const completed = this.stats.activities.guides_completed;
            topicsEl.textContent = `${completed}/5`;
        }
        
        // Update Quizzes Completed card
        const quizzesEl = document.getElementById('stat-quizzes');
        if (quizzesEl) {
            const completed = this.stats.activities.quizzes_completed;
            const passed = this.stats.activities.quizzes_passed;
            quizzesEl.textContent = completed;
            
            // Update label to show pass rate
            const quizzesLabel = quizzesEl.nextElementSibling;
            if (quizzesLabel && completed > 0) {
                const passRate = Math.round((passed / completed) * 100);
                quizzesLabel.innerHTML = `
                    Quizzes Completed
                    <div style="font-size: 0.75em; opacity: 0.8;">
                        ${passRate}% pass rate
                    </div>
                `;
            }
        }
    }
    
    /**
     * Add level progress bar to header
     */
    addLevelProgressBar() {
        if (!this.stats) return;
        
        const header = document.querySelector('.header-top');
        if (!header) return;
        
        // Create progress bar container
        const progressContainer = document.createElement('div');
        progressContainer.className = 'level-progress-container';
        progressContainer.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            overflow: hidden;
        `;
        
        // Calculate progress percentage
        const totalXPForLevel = this.stats.xp_to_next_level + (this.stats.total_xp % 100);
        const currentXPInLevel = this.stats.total_xp % 100;
        const progressPercent = (currentXPInLevel / totalXPForLevel) * 100;
        
        // Create progress bar
        const progressBar = document.createElement('div');
        progressBar.className = 'level-progress-bar';
        progressBar.style.cssText = `
            height: 100%;
            width: ${progressPercent}%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.5s ease;
        `;
        
        progressContainer.appendChild(progressBar);
        header.style.position = 'relative';
        header.appendChild(progressContainer);
        
        this.levelProgressBar = progressBar;
    }
    
    /**
     * Setup event listeners for XP updates
     */
    setupEventListeners() {
        // Listen for custom XP update events
        document.addEventListener('xp-awarded', (event) => {
            this.handleXPAwarded(event.detail);
        });

        document.addEventListener('level-up', (event) => {
            this.handleLevelUp(event.detail);
        });
    }

    /**
     * Handle XP awarded event
     */
    async handleXPAwarded(data) {
        console.log('[GamificationUI] XP awarded:', data);

        // Reload stats
        await this.loadStats();

        // Update dashboard
        this.updateDashboard();

        // Update progress bar
        if (this.levelProgressBar && this.stats) {
            const totalXPForLevel = this.stats.xp_to_next_level + (this.stats.total_xp % 100);
            const currentXPInLevel = this.stats.total_xp % 100;
            const progressPercent = (currentXPInLevel / totalXPForLevel) * 100;
            this.levelProgressBar.style.width = `${progressPercent}%`;
        }

        // Show XP notification
        this.showXPNotification(data.xp_awarded, data.new_total_xp);
    }

    /**
     * Handle level up event
     */
    handleLevelUp(data) {
        console.log('[GamificationUI] Level up!', data);

        // Show level up animation
        this.showLevelUpAnimation(data.new_level, data.new_level_title);
    }

    /**
     * Show XP notification
     */
    showXPNotification(xpAwarded, newTotal) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'xp-notification';
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            animation: slideInRight 0.3s ease, fadeOut 0.3s ease 2.7s;
            font-weight: 600;
        `;

        notification.innerHTML = `
            <div style="font-size: 1.2em;">+${xpAwarded} XP</div>
            <div style="font-size: 0.9em; opacity: 0.9;">Total: ${newTotal.toLocaleString()} XP</div>
        `;

        document.body.appendChild(notification);

        // Remove after animation
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Show level up animation
     */
    showLevelUpAnimation(newLevel, newLevelTitle) {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'level-up-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10001;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        `;

        // Create level up card
        const card = document.createElement('div');
        card.className = 'level-up-card';
        card.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: scaleIn 0.5s ease;
            max-width: 400px;
        `;

        card.innerHTML = `
            <div style="font-size: 4em; margin-bottom: 1rem;">🎉</div>
            <div style="font-size: 2em; font-weight: 700; margin-bottom: 0.5rem;">Level Up!</div>
            <div style="font-size: 1.5em; margin-bottom: 0.5rem;">Level ${newLevel}</div>
            <div style="font-size: 1.2em; opacity: 0.9;">${newLevelTitle}</div>
            <button onclick="this.closest('.level-up-overlay').remove()"
                    style="margin-top: 2rem; padding: 0.75rem 2rem; background: white; color: #667eea;
                           border: none; border-radius: 8px; font-size: 1em; font-weight: 600;
                           cursor: pointer;">
                Continue
            </button>
        `;

        overlay.appendChild(card);
        document.body.appendChild(overlay);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (overlay.parentNode) {
                overlay.remove();
            }
        }, 5000);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes scaleIn {
        from {
            transform: scale(0.8);
            opacity: 0;
        }
        to {
            transform: scale(1);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// Initialize UI when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gamificationUI = new GamificationUI();
    });
} else {
    window.gamificationUI = new GamificationUI();
}

// Export for use in other scripts
window.GamificationUI = GamificationUI;

