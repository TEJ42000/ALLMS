/**
 * Gamification UI
 * 
 * Handles displaying gamification data in the dashboard UI.
 */

class GamificationUI {
    constructor() {
        this.stats = null;
        this.levelProgressBar = null;
        this.listeners = {}; // Store listener references for cleanup
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

        // Create progress bar container using CSS classes (Issue #179 - CSP compliance)
        const progressContainer = document.createElement('div');
        progressContainer.className = 'level-progress-container';

        // Calculate progress percentage
        const totalXPForLevel = this.stats.xp_to_next_level + (this.stats.total_xp % 100);
        const currentXPInLevel = this.stats.total_xp % 100;
        const progressPercent = (currentXPInLevel / totalXPForLevel) * 100;

        // Create progress bar - use CSS custom property for dynamic width
        const progressBar = document.createElement('div');
        progressBar.className = 'level-progress-bar';
        progressBar.style.width = `${progressPercent}%`;  // width is CSP-safe

        progressContainer.appendChild(progressBar);
        header.classList.add('header-with-progress');  // CSS handles position: relative
        header.appendChild(progressContainer);

        this.levelProgressBar = progressBar;
    }
    
    /**
     * Setup event listeners for XP updates
     */
    setupEventListeners() {
        // Store bound listener functions for cleanup
        this.listeners = {
            'xp-awarded': (event) => this.handleXPAwarded(event.detail),
            'level-up': (event) => this.handleLevelUp(event.detail),
            'streak-updated': (event) => this.handleStreakUpdated(event.detail),
            'freeze-used': (event) => this.handleFreezeUsed(event.detail),
            'badge-earned': (event) => this.handleBadgeEarned(event.detail)
        };

        // Add event listeners
        Object.entries(this.listeners).forEach(([eventName, handler]) => {
            document.addEventListener(eventName, handler);
        });

        // Listen for tab changes to load badges when badges tab is opened
        document.addEventListener('tab-changed', (event) => {
            if (event.detail.tab === 'badges') {
                this.loadBadges();
            }
        });
    }

    /**
     * Cleanup event listeners to prevent memory leaks
     * Call this method when destroying the GamificationUI instance
     */
    cleanup() {
        // Remove all event listeners
        Object.entries(this.listeners).forEach(([eventName, handler]) => {
            document.removeEventListener(eventName, handler);
        });
        this.listeners = {};
        console.log('[GamificationUI] Cleaned up event listeners');
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
     * Handle streak updated event
     */
    handleStreakUpdated(data) {
        console.log('[GamificationUI] Streak updated:', data);

        // Check for milestone streaks
        const milestones = [7, 14, 30, 60, 100];
        if (milestones.includes(data.new_streak_count)) {
            this.showStreakMilestoneNotification(data.new_streak_count);
        }
    }

    /**
     * Handle freeze used event
     */
    handleFreezeUsed(data) {
        console.log('[GamificationUI] Freeze used:', data);

        // Show freeze used notification
        this.showFreezeUsedNotification(data.new_streak_count);
    }

    /**
     * Show XP notification (CSP-safe, Issue #179)
     */
    showXPNotification(xpAwarded, newTotal) {
        // Create notification element using CSS classes
        const notification = document.createElement('div');
        notification.className = 'xp-notification';

        notification.innerHTML = `
            <div class="xp-notification-amount">+${this.escapeHtml(xpAwarded)} XP</div>
            <div class="xp-notification-total">Total: ${this.escapeHtml(newTotal.toLocaleString())} XP</div>
        `;

        document.body.appendChild(notification);

        // Remove after animation
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    /**
     * Show level up animation (CSP-safe, Issue #179)
     */
    showLevelUpAnimation(newLevel, newLevelTitle) {
        // Create overlay using CSS classes
        const overlay = document.createElement('div');
        overlay.className = 'level-up-overlay';

        // Create level up card using CSS classes
        const card = document.createElement('div');
        card.className = 'level-up-card';

        card.innerHTML = `
            <div class="level-up-emoji">🎉</div>
            <div class="level-up-title">Level Up!</div>
            <div class="level-up-level">Level ${this.escapeHtml(newLevel)}</div>
            <div class="level-up-level-title">${this.escapeHtml(newLevelTitle)}</div>
        `;

        // Create continue button with CSS class
        const continueBtn = document.createElement('button');
        continueBtn.className = 'level-up-continue-btn';
        continueBtn.textContent = 'Continue';
        continueBtn.addEventListener('click', () => {
            if (overlay.parentNode) {
                overlay.remove();
            }
        });
        card.appendChild(continueBtn);

        overlay.appendChild(card);
        document.body.appendChild(overlay);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (overlay.parentNode) {
                overlay.remove();
            }
        }, 5000);
    }

    /**
     * Show streak milestone notification (CSP-safe, Issue #179)
     */
    showStreakMilestoneNotification(streakCount) {
        const notification = document.createElement('div');
        notification.className = 'streak-milestone-notification';

        notification.innerHTML = `
            <div class="streak-milestone-title">🔥 ${this.escapeHtml(streakCount)} Day Streak!</div>
            <div class="streak-milestone-subtitle">Keep it going!</div>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 4000);
    }

    /**
     * Show freeze used notification (CSP-safe, Issue #179)
     */
    showFreezeUsedNotification(streakCount) {
        const notification = document.createElement('div');
        notification.className = 'freeze-used-notification';

        notification.innerHTML = `
            <div class="freeze-used-title">❄️ Streak Freeze Used!</div>
            <div class="freeze-used-subtitle">Your ${this.escapeHtml(streakCount)}-day streak is safe!</div>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 4000);
    }

    /**
     * Load and display badges
     */
    async loadBadges() {
        try {
            // Fetch user's earned badges
            const earnedResponse = await fetch('/api/gamification/badges');
            const earnedData = earnedResponse.ok ? await earnedResponse.json() : { badges: [] };
            const earnedBadges = earnedData.badges || [];

            // Fetch all badge definitions
            const defsResponse = await fetch('/api/gamification/badges/definitions');
            const defsData = defsResponse.ok ? await defsResponse.json() : { badge_definitions: [] };
            const allBadges = defsData.badge_definitions || [];

            console.log('[GamificationUI] Badges loaded:', { earned: earnedBadges.length, total: allBadges.length });

            // Render badges
            this.renderBadges(earnedBadges, allBadges);
        } catch (error) {
            console.error('[GamificationUI] Error loading badges:', error);
        }
    }

    /**
     * Render badges in the UI
     */
    renderBadges(earnedBadges, allBadges) {
        const earnedGrid = document.getElementById('earned-badges-grid');
        const availableGrid = document.getElementById('available-badges-grid');

        if (!earnedGrid || !availableGrid) return;

        // Create a map of earned badges for quick lookup
        const earnedMap = new Map(earnedBadges.map(b => [b.badge_id, b]));

        // Separate earned and available badges
        const earned = [];
        const available = [];

        allBadges.forEach(badge => {
            if (earnedMap.has(badge.badge_id)) {
                earned.push({ ...badge, ...earnedMap.get(badge.badge_id) });
            } else {
                available.push(badge);
            }
        });

        // Render earned badges
        if (earned.length > 0) {
            earnedGrid.innerHTML = earned.map(badge => this.createBadgeCard(badge, true)).join('');
        } else {
            earnedGrid.innerHTML = '<div class="loading-placeholder">No badges earned yet. Complete challenges to earn your first badge!</div>';
        }

        // Render available badges
        if (available.length > 0) {
            availableGrid.innerHTML = available.map(badge => this.createBadgeCard(badge, false)).join('');
        } else {
            availableGrid.innerHTML = '<div class="loading-placeholder">All badges earned! 🎉</div>';
        }
    }

    /**
     * Create a badge card HTML
     */
    createBadgeCard(badge, isEarned) {
        const tier = isEarned ? badge.tier : 'bronze';
        const timesEarned = isEarned ? badge.times_earned : 0;
        const nextTierIndex = badge.tiers.indexOf(tier) + 1;
        const nextTier = nextTierIndex < badge.tiers.length ? badge.tiers[nextTierIndex] : null;
        const nextTierRequirement = nextTier ? badge.tier_requirements[nextTier] : null;

        // Calculate progress to next tier
        let progressPercent = 0;
        let progressText = '';
        if (isEarned && nextTier) {
            progressPercent = (timesEarned / nextTierRequirement) * 100;
            progressText = `${timesEarned}/${nextTierRequirement} to ${nextTier}`;
        } else if (!isEarned) {
            progressText = 'Not earned yet';
        } else {
            progressText = 'Max tier reached!';
        }

        return `
            <div class="badge-card ${isEarned ? 'earned' : 'locked'}">
                <span class="badge-category-tag ${badge.category}">${badge.category}</span>
                <div class="badge-icon">${badge.icon}</div>
                <div class="badge-name">${badge.name}</div>
                ${isEarned ? `<div class="badge-tier ${tier}">${tier}</div>` : ''}
                <div class="badge-description">${badge.description}</div>
                ${isEarned && nextTier ? `
                    <div class="badge-progress">
                        <div class="badge-progress-label">
                            <span>Progress to ${nextTier}</span>
                            <span>${progressText}</span>
                        </div>
                        <div class="badge-progress-bar">
                            <div class="badge-progress-fill" style="width: ${progressPercent}%"></div>
                        </div>
                    </div>
                ` : ''}
                ${isEarned ? `<div class="badge-times-earned">Earned ${timesEarned} time${timesEarned !== 1 ? 's' : ''}</div>` : ''}
            </div>
        `;
    }

    /**
     * Handle badge earned event
     */
    async handleBadgeEarned(data) {
        console.log('[GamificationUI] Badge earned:', data);

        // Show badge notification with confetti
        this.showBadgeEarnedNotification(data);

        // Reload badges
        await this.loadBadges();
    }

    /**
     * Show badge earned notification with confetti
     */
    showBadgeEarnedNotification(data) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'badge-notification';

        notification.innerHTML = `
            <div class="badge-notification-icon">${data.badge_icon || '🏆'}</div>
            <div class="badge-notification-title">Badge Earned!</div>
            <div class="badge-notification-description">${data.badge_name}</div>
            ${data.tier ? `<div class="badge-tier ${data.tier}" style="margin-top: 0.5rem;">${data.tier}</div>` : ''}
        `;

        document.body.appendChild(notification);

        // Trigger confetti animation
        if (typeof confetti !== 'undefined') {
            // Gold confetti burst
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#FFD700', '#FFA500', '#FF8C00', '#d4af37']
            });

            // Second burst after a delay
            setTimeout(() => {
                confetti({
                    particleCount: 50,
                    angle: 60,
                    spread: 55,
                    origin: { x: 0 },
                    colors: ['#FFD700', '#FFA500', '#FF8C00', '#d4af37']
                });
            }, 250);

            setTimeout(() => {
                confetti({
                    particleCount: 50,
                    angle: 120,
                    spread: 55,
                    origin: { x: 1 },
                    colors: ['#FFD700', '#FFA500', '#FF8C00', '#d4af37']
                });
            }, 400);
        }

        // Remove after animation
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// CSS animations are now in gamification.css (Issue #179 - CSP compliance)
// No dynamic style injection needed

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

