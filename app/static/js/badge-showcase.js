/**
 * Badge Showcase
 * 
 * Displays user badges, progress tracking, and badge notifications.
 */

class BadgeShowcase {
    constructor() {
        this.userBadges = [];
        this.badgeDefinitions = [];
        this.currentFilter = 'all';
        this.currentSort = 'recent';
        this.init();
    }

    /**
     * Sanitize HTML to prevent XSS attacks
     * CRITICAL: Security best practice - always sanitize user input
     */
    sanitizeHTML(str) {
        if (typeof str !== 'string') {
            return String(str);
        }
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Safely parse integer to prevent injection
     */
    safeParseInt(value, defaultValue = 0) {
        const parsed = parseInt(value, 10);
        return isNaN(parsed) ? defaultValue : parsed;
    }

    async init() {
        console.log('[BadgeShowcase] Initializing...');
        await this.loadBadgeData();
        this.renderBadgeShowcase();
        this.setupEventListeners();
        console.log('[BadgeShowcase] Initialized');
    }

    /**
     * Load badge data from API
     * CRITICAL: Fixed incorrect API endpoint URLs
     */
    async loadBadgeData() {
        try {
            // Load user's earned badges
            // CRITICAL: Fixed endpoint from /badges to /badges/earned
            const userBadgesResponse = await fetch('/api/gamification/badges/earned');
            if (userBadgesResponse.ok) {
                const data = await userBadgesResponse.json();
                this.userBadges = data.badges || [];
                console.log('[BadgeShowcase] User badges loaded:', this.userBadges.length);
            } else {
                console.error('[BadgeShowcase] Failed to load user badges:', userBadgesResponse.status);
                this.showError('Failed to load your earned badges. Please refresh the page.');
            }

            // Load all badge definitions
            // CRITICAL: Fixed endpoint from /badges/definitions to /badges
            const definitionsResponse = await fetch('/api/gamification/badges');
            if (definitionsResponse.ok) {
                const data = await definitionsResponse.json();
                this.badgeDefinitions = data.badges || [];
                console.log('[BadgeShowcase] Badge definitions loaded:', this.badgeDefinitions.length);
            } else {
                console.error('[BadgeShowcase] Failed to load badge definitions:', definitionsResponse.status);
                this.showError('Failed to load badge information. Please refresh the page.');
            }
        } catch (error) {
            console.error('[BadgeShowcase] Error loading badge data:', error);
            this.showError('An error occurred while loading badges. Please try again later.');
        }
    }

    /**
     * Render badge showcase
     * CRITICAL: Added sanitization and bounds checking
     */
    renderBadgeShowcase() {
        const container = document.getElementById('badge-showcase');
        if (!container) return;

        // CRITICAL: Validate arrays before accessing
        const earnedCount = Array.isArray(this.userBadges) ? this.userBadges.length : 0;
        const totalCount = Array.isArray(this.badgeDefinitions) ? this.badgeDefinitions.length : 0;
        const completionRate = totalCount > 0 ? Math.round((earnedCount / totalCount) * 100) : 0;

        // CRITICAL: Sanitize numeric values
        const safeEarnedCount = this.safeParseInt(earnedCount, 0);
        const safeTotalCount = this.safeParseInt(totalCount, 0);
        const safeCompletionRate = this.safeParseInt(completionRate, 0);

        let html = `
            <div class="badge-showcase-header">
                <div class="badge-stats">
                    <div class="badge-stat">
                        <span class="stat-icon">🏆</span>
                        <span class="stat-value">${safeEarnedCount}/${safeTotalCount}</span>
                        <span class="stat-label">Badges Earned</span>
                    </div>
                    <div class="badge-stat">
                        <span class="stat-icon">📊</span>
                        <span class="stat-value">${safeCompletionRate}%</span>
                        <span class="stat-label">Completion</span>
                    </div>
                </div>
                <div class="badge-controls">
                    <div class="badge-filter">
                        <button class="filter-btn ${this.currentFilter === 'all' ? 'active' : ''}" data-filter="all">All</button>
                        <button class="filter-btn ${this.currentFilter === 'earned' ? 'active' : ''}" data-filter="earned">Earned</button>
                        <button class="filter-btn ${this.currentFilter === 'locked' ? 'active' : ''}" data-filter="locked">Locked</button>
                    </div>
                    <div class="badge-sort">
                        <select class="sort-select" id="badge-sort">
                            <option value="recent" ${this.currentSort === 'recent' ? 'selected' : ''}>Most Recent</option>
                            <option value="name" ${this.currentSort === 'name' ? 'selected' : ''}>Name</option>
                            <option value="rarity" ${this.currentSort === 'rarity' ? 'selected' : ''}>Rarity</option>
                            <option value="category" ${this.currentSort === 'category' ? 'selected' : ''}>Category</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="badge-grid">
        `;

        // Get filtered and sorted badges
        const badges = this.getFilteredAndSortedBadges();

        // CRITICAL: Validate badges array before rendering
        if (Array.isArray(badges) && badges.length > 0) {
            badges.forEach(badge => {
                html += this.renderBadgeCard(badge);
            });
        } else {
            html += `
                <div class="no-badges-message">
                    <p>No badges to display. ${this.currentFilter === 'earned' ? 'Start earning badges by completing activities!' : 'Check back later for new badges.'}</p>
                </div>
            `;
        }

        html += `
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Get filtered and sorted badges
     * CRITICAL: Added bounds checking and validation
     */
    getFilteredAndSortedBadges() {
        // CRITICAL: Validate arrays before processing
        if (!Array.isArray(this.userBadges) || !Array.isArray(this.badgeDefinitions)) {
            console.warn('[BadgeShowcase] Invalid badge data');
            return [];
        }

        // Create map of earned badges
        const earnedMap = {};
        this.userBadges.forEach(badge => {
            if (badge && badge.badge_id) {
                earnedMap[badge.badge_id] = badge;
            }
        });

        // Combine definitions with earned status
        let badges = this.badgeDefinitions.map(def => {
            const earned = earnedMap[def.badge_id];
            return {
                ...def,
                earned: !!earned,
                userBadge: earned || null
            };
        });

        // Apply filter
        if (this.currentFilter === 'earned') {
            badges = badges.filter(b => b.earned);
        } else if (this.currentFilter === 'locked') {
            badges = badges.filter(b => !b.earned);
        }

        // Apply sort
        badges.sort((a, b) => {
            switch (this.currentSort) {
                case 'recent':
                    if (!a.earned && !b.earned) return 0;
                    if (!a.earned) return 1;
                    if (!b.earned) return -1;
                    // CRITICAL: Validate earned_at exists
                    const aDate = a.userBadge?.earned_at ? new Date(a.userBadge.earned_at) : new Date(0);
                    const bDate = b.userBadge?.earned_at ? new Date(b.userBadge.earned_at) : new Date(0);
                    return bDate - aDate;

                case 'name':
                    // CRITICAL: Validate name exists
                    const aName = a.name || '';
                    const bName = b.name || '';
                    return aName.localeCompare(bName);

                case 'rarity':
                    // CRITICAL: Changed from 'tier' to 'rarity' to match badge model
                    const rarityOrder = { legendary: 0, epic: 1, rare: 2, uncommon: 3, common: 4 };
                    const aRarity = a.rarity || 'common';
                    const bRarity = b.rarity || 'common';
                    return (rarityOrder[aRarity] || 4) - (rarityOrder[bRarity] || 4);

                case 'category':
                    // CRITICAL: Validate category exists
                    const aCat = a.category || '';
                    const bCat = b.category || '';
                    return aCat.localeCompare(bCat);

                default:
                    return 0;
            }
        });

        return badges;
    }

    /**
     * Render individual badge card
     * CRITICAL: Added XSS protection via sanitization
     */
    renderBadgeCard(badge) {
        // CRITICAL: Validate badge object
        if (!badge || typeof badge !== 'object') {
            console.warn('[BadgeShowcase] Invalid badge object');
            return '';
        }

        const isEarned = badge.earned;
        const userBadge = badge.userBadge;

        // CRITICAL: Sanitize all user-facing strings
        const safeName = this.sanitizeHTML(badge.name || 'Unknown Badge');
        const safeDescription = this.sanitizeHTML(badge.description || 'No description available');
        const safeIcon = this.sanitizeHTML(badge.icon || '🏆');
        const safeCategory = this.formatCategory(badge.category);
        const safeRarity = this.sanitizeHTML(badge.rarity || 'common');

        return `
            <div class="badge-card ${isEarned ? 'earned' : 'locked'} rarity-${safeRarity}">
                <div class="badge-icon ${isEarned ? '' : 'grayscale'}">
                    ${safeIcon}
                </div>
                <div class="badge-info">
                    <h4 class="badge-name">${safeName}</h4>
                    <p class="badge-description">${safeDescription}</p>
                    <div class="badge-category">${safeCategory}</div>
                    <div class="badge-rarity rarity-${safeRarity}">${safeRarity.toUpperCase()}</div>
                </div>
                ${isEarned ? `
                    <div class="badge-earned-info">
                        <div class="earned-date">Earned ${this.formatDate(userBadge?.earned_at)}</div>
                    </div>
                ` : `
                    <div class="badge-locked">
                        <span class="lock-icon">🔒</span>
                        <span class="lock-text">Not yet earned</span>
                    </div>
                `}
            </div>
        `;
    }

    /**
     * Format category name
     * CRITICAL: Added sanitization and new categories
     */
    formatCategory(category) {
        // CRITICAL: Sanitize category input
        const safeCategory = this.sanitizeHTML(category || '');

        const categoryMap = {
            'streak': '🔥 Streak',
            'xp': '⭐ XP',
            'activity': '📚 Activity',
            'consistency': '🏆 Consistency',
            'special': '🌟 Special',
            // Legacy categories
            'behavioral': '🎯 Behavioral',
            'achievement': '🏆 Achievement',
            'milestone': '📍 Milestone'
        };
        return categoryMap[safeCategory] || safeCategory;
    }

    /**
     * Format date for display
     * CRITICAL: Added date formatting helper
     */
    formatDate(dateString) {
        if (!dateString) return 'Unknown';

        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return 'Unknown';

            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            return date.toLocaleDateString();
        } catch (e) {
            console.error('[BadgeShowcase] Error formatting date:', e);
            return 'Unknown';
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentFilter = e.target.dataset.filter;
                this.renderBadgeShowcase();
            });
        });

        // Sort select
        const sortSelect = document.getElementById('badge-sort');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.currentSort = e.target.value;
                this.renderBadgeShowcase();
            });
        }

        // Listen for badge earned events
        document.addEventListener('gamification:badgeearned', (e) => {
            this.showBadgeNotification(e.detail);
            this.refresh();
        });
    }

    /**
     * Show badge earned notification
     * CRITICAL: Added XSS protection via sanitization
     */
    showBadgeNotification(badgeData) {
        // CRITICAL: Validate and sanitize badge data
        if (!badgeData || typeof badgeData !== 'object') {
            console.warn('[BadgeShowcase] Invalid badge notification data');
            return;
        }

        const safeBadgeName = this.sanitizeHTML(badgeData.badge_name || 'Unknown Badge');
        const safeBadgeIcon = this.sanitizeHTML(badgeData.badge_icon || '🏆');
        const isNew = badgeData.is_new !== false; // Default to true

        const notification = document.createElement('div');
        notification.className = 'badge-notification';

        // CRITICAL: Use textContent for user-controlled data
        const contentDiv = document.createElement('div');
        contentDiv.className = 'badge-notification-content';

        const iconDiv = document.createElement('div');
        iconDiv.className = 'notification-icon';
        iconDiv.textContent = safeBadgeIcon;

        const textDiv = document.createElement('div');
        textDiv.className = 'notification-text';

        const heading = document.createElement('h3');
        heading.textContent = isNew ? 'Badge Earned!' : 'Badge Progress!';

        const para = document.createElement('p');
        para.textContent = safeBadgeName;

        textDiv.appendChild(heading);
        textDiv.appendChild(para);
        contentDiv.appendChild(iconDiv);
        contentDiv.appendChild(textDiv);
        notification.appendChild(contentDiv);

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Play sound if available
        if (window.gamificationAnimations && typeof window.gamificationAnimations.playSound === 'function') {
            try {
                window.gamificationAnimations.playSound('badgeEarned');
            } catch (e) {
                console.warn('[BadgeShowcase] Error playing sound:', e);
            }
        }

        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Show error message to user
     * CRITICAL: User-facing error messages
     * CRITICAL: CSP compliant - no inline onclick handlers
     */
    showError(message) {
        const container = document.getElementById('badge-showcase');
        if (!container) {
            console.error('[BadgeShowcase] Container not found for error message');
            return;
        }

        const safeMessage = this.sanitizeHTML(message || 'An error occurred');

        const errorDiv = document.createElement('div');
        errorDiv.className = 'badge-error-message';

        // CRITICAL: Build DOM elements instead of innerHTML to avoid CSP violation
        const iconDiv = document.createElement('div');
        iconDiv.className = 'error-icon';
        iconDiv.textContent = '⚠️';

        const textDiv = document.createElement('div');
        textDiv.className = 'error-text';
        textDiv.textContent = safeMessage;

        const dismissBtn = document.createElement('button');
        dismissBtn.className = 'error-dismiss';
        dismissBtn.textContent = 'Dismiss';
        // CRITICAL: Use event listener instead of inline onclick (CSP compliance)
        dismissBtn.addEventListener('click', () => {
            errorDiv.remove();
        });

        errorDiv.appendChild(iconDiv);
        errorDiv.appendChild(textDiv);
        errorDiv.appendChild(dismissBtn);

        container.insertBefore(errorDiv, container.firstChild);

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 10000);
    }

    /**
     * Refresh badge data
     */
    async refresh() {
        await this.loadBadgeData();
        this.renderBadgeShowcase();
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.badgeShowcase = new BadgeShowcase();
    });
} else {
    window.badgeShowcase = new BadgeShowcase();
}

