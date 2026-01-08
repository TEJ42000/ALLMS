/**
 * Gamification Animations & Visual Effects
 * 
 * Provides enhanced animations for gamification events including:
 * - Level up celebrations with confetti
 * - XP gain animations
 * - Badge unlock effects
 * - Streak milestone celebrations
 * - Progress bar animations
 */

class GamificationAnimations {
    constructor() {
        this.animationQueue = [];
        this.isAnimating = false;
        this.soundEnabled = localStorage.getItem('gamification_sound') !== 'false';
        this.init();
    }

    init() {
        console.log('[GamificationAnimations] Initializing...');
        this.loadSounds();
        this.setupEventListeners();
    }

    /**
     * Load sound effects (optional)
     */
    loadSounds() {
        this.sounds = {
            levelUp: new Audio('/static/sounds/level-up.mp3'),
            badgeEarned: new Audio('/static/sounds/badge-earned.mp3'),
            xpGain: new Audio('/static/sounds/xp-gain.mp3'),
            streakMilestone: new Audio('/static/sounds/streak-milestone.mp3')
        };

        // Set volume
        Object.values(this.sounds).forEach(sound => {
            sound.volume = 0.3;
        });
    }

    /**
     * Play sound effect
     */
    playSound(soundName) {
        if (!this.soundEnabled || !this.sounds[soundName]) return;
        
        try {
            this.sounds[soundName].currentTime = 0;
            this.sounds[soundName].play().catch(e => {
                console.log('[GamificationAnimations] Sound play failed:', e);
            });
        } catch (e) {
            console.log('[GamificationAnimations] Sound error:', e);
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for gamification events
        document.addEventListener('gamification:levelup', (e) => this.showLevelUpAnimation(e.detail));
        document.addEventListener('gamification:xpgain', (e) => this.showXPGainAnimation(e.detail));
        document.addEventListener('gamification:badgeearned', (e) => this.showBadgeEarnedAnimation(e.detail));
        document.addEventListener('gamification:streakmilestone', (e) => this.showStreakMilestoneAnimation(e.detail));
    }

    /**
     * Show level up animation with confetti
     */
    showLevelUpAnimation(data) {
        const { newLevel, newLevelTitle, xpGained } = data;

        // Play sound
        this.playSound('levelUp');

        // Create level up modal
        const modal = document.createElement('div');
        modal.className = 'level-up-modal';
        modal.innerHTML = `
            <div class="level-up-content">
                <div class="level-up-icon">🎉</div>
                <h2 class="level-up-title">Level Up!</h2>
                <div class="level-up-level">Level ${newLevel}</div>
                <div class="level-up-rank">${newLevelTitle}</div>
                <div class="level-up-message">You've reached a new level!</div>
                <button class="level-up-close">Continue</button>
            </div>
        `;

        document.body.appendChild(modal);

        // Trigger entrance animation
        setTimeout(() => modal.classList.add('show'), 10);

        // Confetti celebration
        this.triggerConfetti('levelup');

        // Close button
        modal.querySelector('.level-up-close').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        });

        // Auto-close after 5 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            }
        }, 5000);
    }

    /**
     * Show XP gain animation
     */
    showXPGainAnimation(data) {
        const { xpGained, activityType, position } = data;

        // Play sound
        this.playSound('xpGain');

        // Create floating XP indicator
        const indicator = document.createElement('div');
        indicator.className = 'xp-gain-indicator';
        indicator.innerHTML = `
            <div class="xp-gain-content">
                <span class="xp-gain-icon">⭐</span>
                <span class="xp-gain-amount">+${xpGained} XP</span>
            </div>
        `;

        // Position near the action (if provided)
        if (position) {
            indicator.style.left = `${position.x}px`;
            indicator.style.top = `${position.y}px`;
        }

        document.body.appendChild(indicator);

        // Trigger animation
        setTimeout(() => indicator.classList.add('show'), 10);

        // Remove after animation
        setTimeout(() => {
            indicator.classList.remove('show');
            setTimeout(() => indicator.remove(), 500);
        }, 2000);

        // Update progress bar with animation
        this.animateProgressBar(xpGained);
    }

    /**
     * Animate progress bar fill
     */
    animateProgressBar(xpGained) {
        const progressBar = document.querySelector('.level-progress-fill');
        if (!progressBar) return;

        // Add pulse animation
        progressBar.classList.add('progress-pulse');
        setTimeout(() => progressBar.classList.remove('progress-pulse'), 600);
    }

    /**
     * Show badge earned animation
     */
    showBadgeEarnedAnimation(data) {
        const { badgeName, badgeIcon, badgeTier, badgeDescription } = data;

        // Play sound
        this.playSound('badgeEarned');

        // Create badge modal
        const modal = document.createElement('div');
        modal.className = 'badge-earned-modal';
        modal.innerHTML = `
            <div class="badge-earned-content">
                <div class="badge-earned-icon">${badgeIcon}</div>
                <h2 class="badge-earned-title">Badge Unlocked!</h2>
                <div class="badge-earned-name">${badgeName}</div>
                <div class="badge-earned-tier ${badgeTier.toLowerCase()}">${badgeTier}</div>
                <div class="badge-earned-description">${badgeDescription}</div>
                <button class="badge-earned-share">Share Achievement</button>
                <button class="badge-earned-close">Continue</button>
            </div>
        `;

        document.body.appendChild(modal);

        // Trigger entrance animation
        setTimeout(() => modal.classList.add('show'), 10);

        // Gold confetti for badges
        this.triggerConfetti('badge');

        // Share button
        modal.querySelector('.badge-earned-share').addEventListener('click', () => {
            this.shareAchievement(data);
        });

        // Close button
        modal.querySelector('.badge-earned-close').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        });

        // Auto-close after 6 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            }
        }, 6000);
    }

    /**
     * Show streak milestone animation
     */
    showStreakMilestoneAnimation(data) {
        const { streakCount } = data;

        // Play sound
        this.playSound('streakMilestone');

        // Create streak notification
        const notification = document.createElement('div');
        notification.className = 'streak-milestone-notification';
        notification.innerHTML = `
            <div class="streak-milestone-content">
                <div class="streak-milestone-icon">🔥</div>
                <div class="streak-milestone-text">
                    <div class="streak-milestone-title">${streakCount} Day Streak!</div>
                    <div class="streak-milestone-message">You're on fire! Keep it up!</div>
                </div>
            </div>
        `;

        document.body.appendChild(notification);

        // Trigger entrance animation
        setTimeout(() => notification.classList.add('show'), 10);

        // Fire confetti
        this.triggerConfetti('streak');

        // Remove after animation
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    /**
     * Trigger confetti animation
     */
    triggerConfetti(type = 'default') {
        if (typeof confetti === 'undefined') {
            console.log('[GamificationAnimations] Confetti library not loaded');
            return;
        }

        const configs = {
            levelup: {
                particleCount: 150,
                spread: 100,
                origin: { y: 0.6 },
                colors: ['#FFD700', '#FFA500', '#FF8C00', '#d4af37', '#DAA520']
            },
            badge: {
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#FFD700', '#FFA500', '#FF8C00', '#d4af37']
            },
            streak: {
                particleCount: 80,
                spread: 60,
                origin: { y: 0.7 },
                colors: ['#FF4500', '#FF6347', '#FF7F50', '#FFA500']
            },
            default: {
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            }
        };

        const config = configs[type] || configs.default;

        // Main burst
        confetti(config);

        // Side bursts for level up
        if (type === 'levelup') {
            setTimeout(() => {
                confetti({
                    ...config,
                    particleCount: 50,
                    angle: 60,
                    origin: { x: 0, y: 0.6 }
                });
            }, 250);

            setTimeout(() => {
                confetti({
                    ...config,
                    particleCount: 50,
                    angle: 120,
                    origin: { x: 1, y: 0.6 }
                });
            }, 400);
        }
    }

    /**
     * Share achievement (generates shareable image)
     */
    async shareAchievement(data) {
        console.log('[GamificationAnimations] Sharing achievement:', data);
        
        // Create shareable graphic
        const canvas = await this.createShareableGraphic(data);
        
        // Convert to blob
        canvas.toBlob(async (blob) => {
            if (navigator.share && navigator.canShare({ files: [new File([blob], 'achievement.png', { type: 'image/png' })] })) {
                // Use Web Share API
                try {
                    await navigator.share({
                        files: [new File([blob], 'achievement.png', { type: 'image/png' })],
                        title: 'My Achievement',
                        text: `I just earned the ${data.badgeName} badge!`
                    });
                } catch (e) {
                    console.log('[GamificationAnimations] Share cancelled or failed');
                }
            } else {
                // Fallback: download image
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'achievement.png';
                a.click();
                URL.revokeObjectURL(url);
            }
        });
    }

    /**
     * Create shareable graphic
     */
    async createShareableGraphic(data) {
        // This will be implemented in the shareable graphics component
        // For now, return a placeholder
        const canvas = document.createElement('canvas');
        canvas.width = 1200;
        canvas.height = 630;
        return canvas;
    }

    /**
     * Toggle sound effects
     */
    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('gamification_sound', this.soundEnabled);
        return this.soundEnabled;
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gamificationAnimations = new GamificationAnimations();
    });
} else {
    window.gamificationAnimations = new GamificationAnimations();
}

