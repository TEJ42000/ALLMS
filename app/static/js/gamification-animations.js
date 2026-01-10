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
        this.soundEnabled = this.safeGetLocalStorage('gamification_sound') !== 'false';
        this.isSharing = false; // Prevent race conditions in share functionality
        this.eventListeners = []; // Track event listeners for cleanup
        this.init();
    }

    /**
     * Safe localStorage getter with error handling
     */
    safeGetLocalStorage(key, defaultValue = null) {
        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.warn('[GamificationAnimations] localStorage.getItem failed:', error.message);
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
                console.warn('[GamificationAnimations] localStorage quota exceeded, clearing old data');
                // Try to clear some space by removing old items
                this.clearOldLocalStorageData();
                // Try again
                try {
                    localStorage.setItem(key, value);
                    return true;
                } catch (retryError) {
                    console.error('[GamificationAnimations] localStorage.setItem failed after cleanup:', retryError.message);
                    return false;
                }
            } else {
                console.error('[GamificationAnimations] localStorage.setItem failed:', error.message);
                return false;
            }
        }
    }

    /**
     * Clear old localStorage data to free up space
     */
    clearOldLocalStorageData() {
        try {
            // List of non-essential keys that can be cleared
            const clearableKeys = [
                'lls-practice-count',
                'lls-last-visit',
                'temp-',
                'cache-'
            ];

            // Remove items matching clearable patterns
            for (let i = localStorage.length - 1; i >= 0; i--) {
                const key = localStorage.key(i);
                if (key && clearableKeys.some(pattern => key.startsWith(pattern))) {
                    localStorage.removeItem(key);
                    console.log('[GamificationAnimations] Cleared localStorage key:', key);
                }
            }
        } catch (error) {
            console.error('[GamificationAnimations] Error clearing localStorage:', error.message);
        }
    }

    init() {
        console.log('[GamificationAnimations] Initializing...');
        this.loadSounds();
        this.setupEventListeners();
    }

    /**
     * Cleanup method to remove event listeners
     */
    cleanup() {
        console.log('[GamificationAnimations] Cleaning up event listeners...');

        // Remove all tracked event listeners
        this.eventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.eventListeners = [];
    }

    /**
     * Load sound effects (optional) with lazy loading and error handling
     */
    loadSounds() {
        this.sounds = {};
        this.soundsLoaded = {};

        // Sound file paths
        this.soundPaths = {
            levelUp: '/static/sounds/level-up.mp3',
            badgeEarned: '/static/sounds/badge-earned.mp3',
            xpGain: '/static/sounds/xp-gain.mp3',
            streakMilestone: '/static/sounds/streak-milestone.mp3'
        };

        // Don't preload - will lazy load on first use
        console.log('[GamificationAnimations] Sound system initialized (lazy loading enabled)');
    }

    /**
     * Lazy load a sound file
     */
    async lazyLoadSound(soundName) {
        // Return if already loaded
        if (this.sounds[soundName]) {
            return this.sounds[soundName];
        }

        // Return null if already failed to load
        if (this.soundsLoaded[soundName] === false) {
            return null;
        }

        try {
            const audio = new Audio(this.soundPaths[soundName]);
            audio.volume = 0.3;

            // Wait for audio to be loadable
            await new Promise((resolve, reject) => {
                audio.addEventListener('canplaythrough', resolve, { once: true });
                audio.addEventListener('error', reject, { once: true });

                // Timeout after 3 seconds
                setTimeout(() => reject(new Error('Sound load timeout')), 3000);
            });

            this.sounds[soundName] = audio;
            this.soundsLoaded[soundName] = true;
            console.log(`[GamificationAnimations] Loaded sound: ${soundName}`);
            return audio;

        } catch (error) {
            console.warn(`[GamificationAnimations] Failed to load sound ${soundName}:`, error.message);
            this.soundsLoaded[soundName] = false;
            return null;
        }
    }

    /**
     * Play sound effect with lazy loading
     */
    async playSound(soundName) {
        if (!this.soundEnabled) return;

        try {
            // Lazy load sound if not already loaded
            const audio = await this.lazyLoadSound(soundName);

            if (!audio) {
                console.log(`[GamificationAnimations] Sound ${soundName} not available`);
                return;
            }

            // Reset and play
            audio.currentTime = 0;
            await audio.play().catch(e => {
                console.log('[GamificationAnimations] Sound play failed:', e.message);
            });
        } catch (e) {
            console.log('[GamificationAnimations] Sound error:', e.message);
        }
    }

    /**
     * Setup event listeners with tracking for cleanup
     */
    setupEventListeners() {
        // Create handlers
        const levelUpHandler = (e) => this.showLevelUpAnimation(e.detail);
        const xpGainHandler = (e) => this.showXPGainAnimation(e.detail);
        const badgeEarnedHandler = (e) => this.showBadgeEarnedAnimation(e.detail);
        const streakMilestoneHandler = (e) => this.showStreakMilestoneAnimation(e.detail);

        // Listen for gamification events
        document.addEventListener('gamification:levelup', levelUpHandler);
        document.addEventListener('gamification:xpgain', xpGainHandler);
        document.addEventListener('gamification:badgeearned', badgeEarnedHandler);
        document.addEventListener('gamification:streakmilestone', streakMilestoneHandler);

        // Track for cleanup
        this.eventListeners.push(
            { element: document, event: 'gamification:levelup', handler: levelUpHandler },
            { element: document, event: 'gamification:xpgain', handler: xpGainHandler },
            { element: document, event: 'gamification:badgeearned', handler: badgeEarnedHandler },
            { element: document, event: 'gamification:streakmilestone', handler: streakMilestoneHandler }
        );
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

    /**
     * Validate and sanitize numeric input with range validation
     */
    sanitizeNumber(value, defaultValue = 0, min = -Infinity, max = Infinity) {
        const num = parseInt(value, 10);

        if (isNaN(num)) {
            return defaultValue;
        }

        // Clamp to range
        return Math.max(min, Math.min(max, num));
    }

    /**
     * Sanitize text for canvas rendering
     * Canvas doesn't interpret HTML, so we just need to ensure safe strings
     */
    sanitizeCanvasText(text, maxLength = 100) {
        if (text === null || text === undefined) return '';

        // Convert to string and trim
        let sanitized = String(text).trim();

        // Remove control characters and non-printable characters
        sanitized = sanitized.replace(/[\x00-\x1F\x7F-\x9F]/g, '');

        // Limit length to prevent canvas overflow
        if (sanitized.length > maxLength) {
            sanitized = sanitized.substring(0, maxLength) + '...';
        }

        return sanitized;
    }

    /**
     * Show level up animation with confetti
     */
    showLevelUpAnimation(data) {
        const { newLevel, newLevelTitle, xpGained } = data;

        // Sanitize inputs with range validation
        const safeLevel = this.sanitizeNumber(newLevel, 1, 1, 100); // Level 1-100
        const safeTitle = this.escapeHtml(newLevelTitle);
        const safeXP = this.sanitizeNumber(xpGained, 0, 0, 10000); // XP 0-10000

        // Play sound
        this.playSound('levelUp');

        // Create level up modal
        const modal = document.createElement('div');
        modal.className = 'level-up-modal';
        modal.innerHTML = `
            <div class="level-up-content">
                <div class="level-up-icon">🎉</div>
                <h2 class="level-up-title">Level Up!</h2>
                <div class="level-up-level">Level ${safeLevel}</div>
                <div class="level-up-rank">${safeTitle}</div>
                <div class="level-up-message">You've reached a new level!</div>
                <button class="level-up-close">Continue</button>
            </div>
        `;

        document.body.appendChild(modal);

        // Trigger entrance animation
        setTimeout(() => modal.classList.add('show'), 10);

        // Confetti celebration
        this.triggerConfetti('levelup');

        // Close button with { once: true } to prevent multiple listeners
        modal.querySelector('.level-up-close').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }, { once: true });

        // Auto-close after 5 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            }
        }, 5000);
    }

    /**
     * Validate position coordinates
     */
    validatePosition(position) {
        if (!position || typeof position !== 'object') {
            return null;
        }

        // Validate x coordinate
        const x = this.sanitizeNumber(position.x, null, 0, window.innerWidth);
        const y = this.sanitizeNumber(position.y, null, 0, window.innerHeight);

        // Return null if either coordinate is invalid
        if (x === null || y === null) {
            return null;
        }

        return { x, y };
    }

    /**
     * Show XP gain animation with validated position
     */
    showXPGainAnimation(data) {
        const { xpGained, activityType, position } = data;

        // Sanitize inputs with range validation
        const safeXP = this.sanitizeNumber(xpGained, 0, 0, 1000); // XP 0-1000 per action

        // Play sound
        this.playSound('xpGain');

        // Create floating XP indicator
        const indicator = document.createElement('div');
        indicator.className = 'xp-gain-indicator';
        indicator.innerHTML = `
            <div class="xp-gain-content">
                <span class="xp-gain-icon">⭐</span>
                <span class="xp-gain-amount">+${safeXP} XP</span>
            </div>
        `;

        // Validate and position near the action (if provided)
        const validatedPosition = this.validatePosition(position);
        if (validatedPosition) {
            indicator.style.left = `${validatedPosition.x}px`;
            indicator.style.top = `${validatedPosition.y}px`;
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

        // Sanitize inputs
        const safeName = this.escapeHtml(badgeName);
        const safeIcon = this.escapeHtml(badgeIcon);
        const safeTier = this.escapeHtml(badgeTier);
        const safeDescription = this.escapeHtml(badgeDescription);

        // Validate tier
        const validTiers = ['bronze', 'silver', 'gold'];
        const tierClass = validTiers.includes(safeTier.toLowerCase()) ? safeTier.toLowerCase() : 'bronze';

        // Play sound
        this.playSound('badgeEarned');

        // Create badge modal
        const modal = document.createElement('div');
        modal.className = 'badge-earned-modal';
        modal.innerHTML = `
            <div class="badge-earned-content">
                <div class="badge-earned-icon">${safeIcon}</div>
                <h2 class="badge-earned-title">Badge Unlocked!</h2>
                <div class="badge-earned-name">${safeName}</div>
                <div class="badge-earned-tier ${tierClass}">${safeTier}</div>
                <div class="badge-earned-description">${safeDescription}</div>
                <button class="badge-earned-share">Share Achievement</button>
                <button class="badge-earned-close">Continue</button>
            </div>
        `;

        document.body.appendChild(modal);

        // Trigger entrance animation
        setTimeout(() => modal.classList.add('show'), 10);

        // Gold confetti for badges
        this.triggerConfetti('badge');

        // Share button with { once: true }
        modal.querySelector('.badge-earned-share').addEventListener('click', () => {
            this.shareAchievement(data);
        }, { once: true });

        // Close button with { once: true }
        modal.querySelector('.badge-earned-close').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }, { once: true });

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

        // Sanitize inputs with range validation
        const safeStreak = this.sanitizeNumber(streakCount, 0, 0, 365); // Streak 0-365 days

        // Play sound
        this.playSound('streakMilestone');

        // Create streak notification
        const notification = document.createElement('div');
        notification.className = 'streak-milestone-notification';
        notification.innerHTML = `
            <div class="streak-milestone-content">
                <div class="streak-milestone-icon">🔥</div>
                <div class="streak-milestone-text">
                    <div class="streak-milestone-title">${safeStreak} Day Streak!</div>
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
     * Share achievement (generates shareable image) with race condition prevention
     */
    async shareAchievement(data) {
        // Prevent race condition
        if (this.isSharing) {
            console.log('[GamificationAnimations] Share already in progress, ignoring');
            return;
        }

        this.isSharing = true;
        console.log('[GamificationAnimations] Sharing achievement:', data);

        try {
            // Create shareable graphic
            const canvas = await this.createShareableGraphic(data);

            if (!canvas) {
                console.error('[GamificationAnimations] Failed to create canvas');
                return;
            }

            // Convert to blob with null check
            canvas.toBlob(async (blob) => {
                // Null check for blob
                if (!blob) {
                    console.error('[GamificationAnimations] Failed to convert canvas to blob');
                    return;
                }

                try {
                    const file = new File([blob], 'achievement.png', { type: 'image/png' });

                    if (navigator.share && navigator.canShare({ files: [file] })) {
                        // Use Web Share API
                        await navigator.share({
                            files: [file],
                            title: 'My Achievement',
                            text: `I just earned the ${this.escapeHtml(data.badgeName)} badge!`
                        });
                    } else {
                        // Fallback: download image
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'achievement.png';
                        a.click();
                        URL.revokeObjectURL(url);
                    }
                } catch (e) {
                    console.error('[GamificationAnimations] Share failed:', e);
                }
            });
        } catch (error) {
            console.error('[GamificationAnimations] Error in shareAchievement:', error);
        } finally {
            // Always reset flag
            this.isSharing = false;
        }
    }

    /**
     * Create shareable graphic for badge achievement
     */
    async createShareableGraphic(data) {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = 1200;
            canvas.height = 630;
            const ctx = canvas.getContext('2d');

            if (!ctx) {
                console.error('[GamificationAnimations] Failed to get canvas context');
                return null;
            }

            // Sanitize data for canvas (not HTML)
            const safeName = this.sanitizeCanvasText(data.badgeName || 'Achievement', 50);
            const safeIcon = this.sanitizeCanvasText(data.badgeIcon || '🏆', 10);
            const safeTier = this.sanitizeCanvasText(data.badgeTier || 'Bronze', 20);

            // Background gradient
            const gradient = ctx.createLinearGradient(0, 0, 0, 630);
            gradient.addColorStop(0, '#1a1f35');
            gradient.addColorStop(1, '#2d3561');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 1200, 630);

            // Title
            ctx.fillStyle = '#d4af37';
            ctx.font = 'bold 48px Arial, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('🏆 Badge Unlocked!', 600, 100);

            // Badge icon (large)
            ctx.font = '120px Arial, sans-serif';
            ctx.fillText(safeIcon, 600, 280);

            // Badge name
            ctx.fillStyle = '#e0e6ed';
            ctx.font = 'bold 42px Arial, sans-serif';
            ctx.fillText(safeName, 600, 380);

            // Tier - validate against whitelist
            const validTiers = ['bronze', 'silver', 'gold'];
            const tierLower = safeTier.toLowerCase();
            const validatedTier = validTiers.includes(tierLower) ? tierLower : 'bronze';

            const tierColors = {
                'bronze': '#cd7f32',
                'silver': '#c0c0c0',
                'gold': '#ffd700'
            };
            ctx.fillStyle = tierColors[validatedTier];
            ctx.font = 'bold 32px Arial, sans-serif';
            ctx.fillText(validatedTier.toUpperCase(), 600, 430);

            // Footer
            ctx.fillStyle = '#d4af37';
            ctx.font = 'bold 28px Arial, sans-serif';
            ctx.fillText('⚖️ Cognitio Flow', 600, 570);

            return canvas;
        } catch (error) {
            console.error('[GamificationAnimations] Error creating shareable graphic:', error);
            return null;
        }
    }

    /**
     * Toggle sound effects with safe localStorage
     */
    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        this.safeSetLocalStorage('gamification_sound', this.soundEnabled);
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

// Cleanup on page unload to prevent memory leaks
window.addEventListener('beforeunload', () => {
    if (window.gamificationAnimations && typeof window.gamificationAnimations.cleanup === 'function') {
        window.gamificationAnimations.cleanup();
    }
});

