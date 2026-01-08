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

    async init() {
        console.log('[BadgeShowcase] Initializing...');
        await this.loadBadgeData();
        this.renderBadgeShowcase();
        this.setupEventListeners();
        console.log('[BadgeShowcase] Initialized');
    }

    /**
     * Load badge data from API
     */
    async loadBadgeData() {
        try {
            // Load user's earned badges
            const userBadgesResponse = await fetch('/api/gamification/badges');
            if (userBadgesResponse.ok) {
                const data = await userBadgesResponse.json();
                this.userBadges = data.badges || [];
                console.log('[BadgeShowcase] User badges loaded:', this.userBadges.length);
            }

            // Load all badge definitions
            const definitionsResponse = await fetch('/api/gamification/badges/definitions');
            if (definitionsResponse.ok) {
                const data = await definitionsResponse.json();
                this.badgeDefinitions = data.badge_definitions || [];
                console.log('[BadgeShowcase] Badge definitions loaded:', this.badgeDefinitions.length);
            }
        } catch (error) {
            console.error('[BadgeShowcase] Error loading badge data:', error);
        }
    }

    /**
     * Render badge showcase
     */
    renderBadgeShowcase() {
        const container = document.getElementById('badge-showcase');
        if (!container) return;

        // Create header with stats and filters
        const earnedCount = this.userBadges.length;
        const totalCount = this.badgeDefinitions.length;
        const completionRate = totalCount > 0 ? Math.round((earnedCount / totalCount) * 100) : 0;

        let html = `
            <div class="badge-showcase-header">
                <div class="badge-stats">
                    <div class="badge-stat">
                        <span class="stat-icon">🏆</span>
                        <span class="stat-value">${earnedCount}/${totalCount}</span>
                        <span class="stat-label">Badges Earned</span>
                    </div>
                    <div class="badge-stat">
                        <span class="stat-icon">📊</span>
                        <span class="stat-value">${completionRate}%</span>
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
                            <option value="tier" ${this.currentSort === 'tier' ? 'selected' : ''}>Tier</option>
                            <option value="category" ${this.currentSort === 'category' ? 'selected' : ''}>Category</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="badge-grid">
        `;

        // Get filtered and sorted badges
        const badges = this.getFilteredAndSortedBadges();

        // Render each badge
        badges.forEach(badge => {
            html += this.renderBadgeCard(badge);
        });

        html += `
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Get filtered and sorted badges
     */
    getFilteredAndSortedBadges() {
        // Create map of earned badges
        const earnedMap = {};
        this.userBadges.forEach(badge => {
            earnedMap[badge.badge_id] = badge;
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
                    return new Date(b.userBadge.earned_at) - new Date(a.userBadge.earned_at);
                
                case 'name':
                    return a.name.localeCompare(b.name);
                
                case 'tier':
                    if (!a.earned && !b.earned) return 0;
                    if (!a.earned) return 1;
                    if (!b.earned) return -1;
                    const tierOrder = { gold: 0, silver: 1, bronze: 2 };
                    return tierOrder[a.userBadge.tier] - tierOrder[b.userBadge.tier];
                
                case 'category':
                    return a.category.localeCompare(b.category);
                
                default:
                    return 0;
            }
        });

        return badges;
    }

    /**
     * Render individual badge card
     */
    renderBadgeCard(badge) {
        const isEarned = badge.earned;
        const userBadge = badge.userBadge;
        const tier = userBadge ? userBadge.tier : 'bronze';
        const timesEarned = userBadge ? userBadge.times_earned : 0;
        
        // Calculate progress to next tier
        const progress = this.calculateTierProgress(badge, timesEarned);

        return `
            <div class="badge-card ${isEarned ? 'earned' : 'locked'} tier-${tier}">
                <div class="badge-icon ${isEarned ? '' : 'grayscale'}">
                    ${badge.icon}
                </div>
                <div class="badge-info">
                    <h4 class="badge-name">${badge.name}</h4>
                    <p class="badge-description">${badge.description}</p>
                    <div class="badge-category">${this.formatCategory(badge.category)}</div>
                </div>
                ${isEarned ? `
                    <div class="badge-tier-info">
                        <div class="tier-badge tier-${tier}">${tier.toUpperCase()}</div>
                        <div class="times-earned">${timesEarned}x earned</div>
                    </div>
                    ${progress.showProgress ? `
                        <div class="tier-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                            </div>
                            <div class="progress-text">${progress.current}/${progress.required} to ${progress.nextTier}</div>
                        </div>
                    ` : ''}
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
     * Calculate progress to next tier
     */
    calculateTierProgress(badge, timesEarned) {
        const tierOrder = ['bronze', 'silver', 'gold'];
        const currentTierIndex = tierOrder.findIndex(t => 
            timesEarned >= badge.tier_requirements[t]
        );
        
        if (currentTierIndex === -1 || currentTierIndex === tierOrder.length - 1) {
            return { showProgress: false };
        }

        const nextTier = tierOrder[currentTierIndex + 1];
        const required = badge.tier_requirements[nextTier];
        const percentage = Math.min((timesEarned / required) * 100, 100);

        return {
            showProgress: true,
            current: timesEarned,
            required: required,
            nextTier: nextTier,
            percentage: percentage
        };
    }

    /**
     * Format category name
     */
    formatCategory(category) {
        const categoryMap = {
            'behavioral': '🎯 Behavioral',
            'achievement': '🏆 Achievement',
            'milestone': '📍 Milestone'
        };
        return categoryMap[category] || category;
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
     */
    showBadgeNotification(badgeData) {
        const { badge_id, badge_name, badge_icon, tier, is_new } = badgeData;

        const notification = document.createElement('div');
        notification.className = 'badge-notification';
        notification.innerHTML = `
            <div class="badge-notification-content">
                <div class="notification-icon">${badge_icon}</div>
                <div class="notification-text">
                    <h3>${is_new ? 'Badge Earned!' : 'Badge Upgraded!'}</h3>
                    <p>${badge_name}</p>
                    <span class="tier-badge tier-${tier}">${tier.toUpperCase()}</span>
                </div>
            </div>
        `;

        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Play sound if available
        if (window.gamificationAnimations) {
            window.gamificationAnimations.playSound('badgeEarned');
        }

        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
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

