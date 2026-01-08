/**
 * Shareable Graphics Generator
 * 
 * Creates shareable graphics for social media including:
 * - Study Report Cards (weekly/monthly summaries)
 * - Badge Showcase graphics
 * - Level achievement graphics
 * - Streak milestone graphics
 */

class ShareableGraphics {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.isGenerating = false; // Prevent race conditions
        this.init();
    }

    init() {
        console.log('[ShareableGraphics] Initializing...');
        this.setupCanvas();
        this.addShareButtons();
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
     * Validate and sanitize numeric input
     */
    sanitizeNumber(value, defaultValue = 0) {
        const num = parseFloat(value);
        return isNaN(num) ? defaultValue : num;
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
     * Validate stats response data
     */
    validateStatsData(data) {
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid stats data: must be an object');
        }

        // Check for required fields
        const requiredFields = ['current_level', 'total_xp', 'level_title'];
        for (const field of requiredFields) {
            if (!(field in data)) {
                console.warn(`[ShareableGraphics] Missing field: ${field}`);
            }
        }

        return true;
    }

    /**
     * Validate badges response data
     */
    validateBadgesData(badges) {
        if (!Array.isArray(badges)) {
            throw new Error('Invalid badges data: must be an array');
        }

        // Validate each badge has required fields
        badges.forEach((badge, index) => {
            if (!badge || typeof badge !== 'object') {
                console.warn(`[ShareableGraphics] Invalid badge at index ${index}`);
            }
        });

        return true;
    }

    /**
     * Validate API endpoint
     */
    validateEndpoint(endpoint) {
        const validEndpoints = [
            '/api/gamification/stats',
            '/api/gamification/badges',
            '/api/gamification/leaderboard'
        ];

        if (!validEndpoints.includes(endpoint)) {
            throw new Error(`Invalid API endpoint: ${endpoint}`);
        }

        return endpoint;
    }

    /**
     * Safe fetch with validation
     */
    async safeFetch(endpoint, options = {}) {
        try {
            // Validate endpoint
            this.validateEndpoint(endpoint);

            // Fetch with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

            const response = await fetch(endpoint, {
                ...options,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // Validate response status
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return response;

        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    /**
     * Setup canvas for graphics generation
     */
    setupCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = 1200;
        this.canvas.height = 630; // Optimal for social media
        this.ctx = this.canvas.getContext('2d');
    }

    /**
     * Add share buttons to dashboard
     */
    addShareButtons() {
        const dashboard = document.querySelector('.gamification-dashboard');
        if (!dashboard) return;

        const shareSection = document.createElement('div');
        shareSection.className = 'share-section';
        shareSection.innerHTML = `
            <h3>📤 Share Your Progress</h3>
            <div class="share-buttons">
                <button class="share-btn" data-type="weekly-report">
                    📊 Weekly Report Card
                </button>
                <button class="share-btn" data-type="badge-showcase">
                    🏆 Badge Showcase
                </button>
                <button class="share-btn" data-type="level-achievement">
                    ⭐ Level Achievement
                </button>
            </div>
        `;

        dashboard.appendChild(shareSection);

        // Add event listeners with { once: false } for reusability
        shareSection.querySelectorAll('.share-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.dataset.type;
                this.generateAndShare(type);
            });
        });
    }

    /**
     * Generate and share graphic with race condition prevention and button disabling
     */
    async generateAndShare(type) {
        // Prevent race condition - only one generation at a time
        if (this.isGenerating) {
            console.log('[ShareableGraphics] Generation already in progress, ignoring click');
            return;
        }

        this.isGenerating = true;
        console.log('[ShareableGraphics] Generating:', type);

        // Disable all share buttons
        const shareButtons = document.querySelectorAll('.share-btn');
        shareButtons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('disabled');
        });

        try {
            // Fetch user stats
            const stats = await this.fetchUserStats();

            if (!stats) {
                console.error('[ShareableGraphics] Failed to fetch stats');
                return;
            }

            // Generate graphic based on type
            let canvas;
            switch (type) {
                case 'weekly-report':
                    canvas = await this.generateWeeklyReport(stats);
                    break;
                case 'badge-showcase':
                    canvas = await this.generateBadgeShowcase(stats);
                    break;
                case 'level-achievement':
                    canvas = await this.generateLevelAchievement(stats);
                    break;
                default:
                    console.error('[ShareableGraphics] Unknown type:', type);
                    return;
            }

            // Share or download
            await this.shareGraphic(canvas, type);
        } catch (error) {
            console.error('[ShareableGraphics] Error generating graphic:', error);
        } finally {
            // Always reset flag and re-enable buttons
            this.isGenerating = false;

            // Re-enable all share buttons
            const shareButtons = document.querySelectorAll('.share-btn');
            shareButtons.forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('disabled');
            });
        }
    }

    /**
     * Fetch user stats
     */
    async fetchUserStats() {
        try {
            const [statsRes, badgesRes] = await Promise.all([
                this.safeFetch('/api/gamification/stats'),
                this.safeFetch('/api/gamification/badges')
            ]);

            const stats = await statsRes.json();
            const badges = await badgesRes.json();

            // Validate data structure and types
            this.validateStatsData(stats);
            this.validateBadgesData(badges);

            return { ...stats, badges };
        } catch (error) {
            console.error('[ShareableGraphics] Error fetching stats:', error);
            return null;
        }
    }

    /**
     * Generate weekly report card
     */
    async generateWeeklyReport(stats) {
        const canvas = document.createElement('canvas');
        canvas.width = 1200;
        canvas.height = 630;
        const ctx = canvas.getContext('2d');

        // Background gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 630);
        gradient.addColorStop(0, '#1a1f35');
        gradient.addColorStop(1, '#2d3561');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1200, 630);

        // Title
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 60px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('📊 Weekly Study Report', 600, 100);

        // Subtitle
        ctx.fillStyle = '#e0e6ed';
        ctx.font = '30px Inter, sans-serif';
        const date = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        ctx.fillText(date, 600, 150);

        // Stats grid
        const statsData = [
            { label: 'Level', value: stats.current_level, icon: '⭐' },
            { label: 'Total XP', value: stats.total_xp, icon: '💎' },
            { label: 'Streak', value: stats.streak?.current_streak || 0, icon: '🔥' },
            { label: 'Badges', value: stats.badges?.length || 0, icon: '🏆' }
        ];

        const startY = 220;
        const spacing = 100;

        statsData.forEach((stat, index) => {
            const x = 200 + (index * 220);
            const y = startY;

            // Icon
            ctx.font = '50px Inter, sans-serif';
            ctx.fillText(stat.icon, x, y);

            // Value
            ctx.fillStyle = '#d4af37';
            ctx.font = 'bold 48px Inter, sans-serif';
            ctx.fillText(stat.value.toString(), x, y + 80);

            // Label
            ctx.fillStyle = '#a0aec0';
            ctx.font = '24px Inter, sans-serif';
            ctx.fillText(stat.label, x, y + 115);
        });

        // Level title (sanitized)
        ctx.fillStyle = '#e0e6ed';
        ctx.font = 'bold 36px Inter, sans-serif';
        const safeLevelTitle = this.sanitizeCanvasText(stats.level_title || 'Junior Clerk', 50);
        ctx.fillText(safeLevelTitle, 600, 400);

        // Activities summary
        ctx.fillStyle = '#a0aec0';
        ctx.font = '24px Inter, sans-serif';
        const activities = stats.activities || {};
        const quizzes = this.sanitizeNumber(activities.quiz_easy_passed, 0) + this.sanitizeNumber(activities.quiz_hard_passed, 0);
        const evaluations = this.sanitizeNumber(activities.evaluation_low, 0) + this.sanitizeNumber(activities.evaluation_high, 0);
        ctx.fillText(`${quizzes} Quizzes Passed • ${evaluations} Evaluations Completed`, 600, 460);

        // Footer
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 28px Inter, sans-serif';
        ctx.fillText('⚖️ LLS Study Portal', 600, 570);

        return canvas;
    }

    /**
     * Generate badge showcase
     */
    async generateBadgeShowcase(stats) {
        const canvas = document.createElement('canvas');
        canvas.width = 1200;
        canvas.height = 630;
        const ctx = canvas.getContext('2d');

        // Background
        const gradient = ctx.createLinearGradient(0, 0, 0, 630);
        gradient.addColorStop(0, '#1a1f35');
        gradient.addColorStop(1, '#2d3561');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1200, 630);

        // Title
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 60px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('🏆 My Badges', 600, 100);

        // Badge grid
        const badges = stats.badges || [];
        const earnedBadges = badges.filter(b => b.earned);
        
        if (earnedBadges.length === 0) {
            ctx.fillStyle = '#a0aec0';
            ctx.font = '32px Inter, sans-serif';
            ctx.fillText('No badges earned yet. Keep studying!', 600, 350);
        } else {
            const maxBadges = Math.min(6, earnedBadges.length);
            const startX = 200;
            const startY = 200;
            const spacing = 180;

            for (let i = 0; i < maxBadges; i++) {
                const badge = earnedBadges[i];
                const col = i % 3;
                const row = Math.floor(i / 3);
                const x = startX + (col * spacing * 2);
                const y = startY + (row * spacing);

                // Badge circle background
                ctx.fillStyle = 'rgba(212, 175, 55, 0.2)';
                ctx.beginPath();
                ctx.arc(x, y, 60, 0, Math.PI * 2);
                ctx.fill();

                // Badge icon (sanitized)
                ctx.font = '60px Inter, sans-serif';
                const safeIcon = this.sanitizeCanvasText(badge.icon || '🏆', 10);
                ctx.fillText(safeIcon, x, y + 20);

                // Badge name (sanitized)
                ctx.fillStyle = '#e0e6ed';
                ctx.font = '18px Inter, sans-serif';
                const safeName = this.sanitizeCanvasText(badge.name, 30);
                ctx.fillText(safeName, x, y + 90);

                // Tier (sanitized)
                ctx.fillStyle = this.getTierColor(badge.tier);
                ctx.font = 'bold 16px Inter, sans-serif';
                const safeTier = this.sanitizeCanvasText(badge.tier, 20).toUpperCase();
                ctx.fillText(safeTier, x, y + 115);
            }
        }

        // Footer
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 28px Inter, sans-serif';
        ctx.fillText('⚖️ LLS Study Portal', 600, 570);

        return canvas;
    }

    /**
     * Generate level achievement graphic
     */
    async generateLevelAchievement(stats) {
        const canvas = document.createElement('canvas');
        canvas.width = 1200;
        canvas.height = 630;
        const ctx = canvas.getContext('2d');

        // Background
        const gradient = ctx.createLinearGradient(0, 0, 0, 630);
        gradient.addColorStop(0, '#1a1f35');
        gradient.addColorStop(1, '#2d3561');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1200, 630);

        // Achievement banner
        ctx.fillStyle = 'rgba(212, 175, 55, 0.2)';
        ctx.fillRect(0, 200, 1200, 230);

        // Title
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 48px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('🎉 Level Achievement', 600, 150);

        // Level number (sanitized)
        ctx.fillStyle = '#e0e6ed';
        ctx.font = 'bold 120px Inter, sans-serif';
        const safeLevel = this.sanitizeNumber(stats.current_level, 1);
        ctx.fillText(`Level ${safeLevel}`, 600, 310);

        // Level title (sanitized)
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 48px Inter, sans-serif';
        const safeLevelTitle2 = this.sanitizeCanvasText(stats.level_title || 'Junior Clerk', 50);
        ctx.fillText(safeLevelTitle2, 600, 380);

        // XP info (sanitized)
        ctx.fillStyle = '#a0aec0';
        ctx.font = '28px Inter, sans-serif';
        const safeTotalXP = this.sanitizeNumber(stats.total_xp, 0);
        ctx.fillText(`${safeTotalXP} Total XP Earned`, 600, 480);

        // Footer
        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 28px Inter, sans-serif';
        ctx.fillText('⚖️ LLS Study Portal', 600, 570);

        return canvas;
    }

    /**
     * Get tier color
     */
    getTierColor(tier) {
        const colors = {
            bronze: '#cd7f32',
            silver: '#c0c0c0',
            gold: '#ffd700'
        };
        return colors[tier.toLowerCase()] || '#d4af37';
    }

    /**
     * Share graphic
     */
    async shareGraphic(canvas, type) {
        if (!canvas) {
            console.error('[ShareableGraphics] Canvas is null or undefined');
            return;
        }

        canvas.toBlob(async (blob) => {
            // Null check for blob
            if (!blob) {
                console.error('[ShareableGraphics] Failed to convert canvas to blob');
                return;
            }

            try {
                const safeType = this.escapeHtml(type);
                const file = new File([blob], `${safeType}.png`, { type: 'image/png' });

                // Try Web Share API
                if (navigator.share && navigator.canShare({ files: [file] })) {
                    try {
                        await navigator.share({
                            files: [file],
                            title: 'My Study Progress',
                            text: 'Check out my progress on LLS Study Portal!'
                        });
                        console.log('[ShareableGraphics] Shared successfully');
                    } catch (error) {
                        if (error.name !== 'AbortError') {
                            console.error('[ShareableGraphics] Share failed:', error);
                            this.downloadGraphic(blob, safeType);
                        }
                    }
                } else {
                    // Fallback: download
                    this.downloadGraphic(blob, safeType);
                }
            } catch (error) {
                console.error('[ShareableGraphics] Error in shareGraphic:', error);
            }
        });
    }

    /**
     * Download graphic
     */
    downloadGraphic(blob, type) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${type}-${Date.now()}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Show notification
        this.showDownloadNotification();
    }

    /**
     * Show download notification
     */
    showDownloadNotification() {
        const notification = document.createElement('div');
        notification.className = 'download-notification';
        notification.innerHTML = `
            <div class="download-notification-content">
                ✅ Graphic downloaded successfully!
            </div>
        `;

        document.body.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 10);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.shareableGraphics = new ShareableGraphics();
    });
} else {
    window.shareableGraphics = new ShareableGraphics();
}

