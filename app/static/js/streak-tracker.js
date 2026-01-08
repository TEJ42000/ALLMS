/**
 * Streak Tracker
 * 
 * Provides streak calendar visualization and weekly consistency tracking.
 */

class StreakTracker {
    constructor() {
        this.calendarData = null;
        this.consistencyData = null;
        this.init();
    }

    async init() {
        console.log('[StreakTracker] Initializing...');
        await this.loadStreakData();
        this.renderCalendar();
        this.renderConsistencyTracker();
        this.setupEventListeners();
        console.log('[StreakTracker] Initialized');
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

    /**
     * Load streak calendar and consistency data
     */
    async loadStreakData() {
        try {
            // Load calendar data (30 days)
            const calendarResponse = await fetch('/api/gamification/streak/calendar?days=30');
            if (calendarResponse.ok) {
                this.calendarData = await calendarResponse.json();
                console.log('[StreakTracker] Calendar data loaded:', this.calendarData);
            }

            // Load consistency data
            const consistencyResponse = await fetch('/api/gamification/streak/consistency');
            if (consistencyResponse.ok) {
                this.consistencyData = await consistencyResponse.json();
                console.log('[StreakTracker] Consistency data loaded:', this.consistencyData);
            }
        } catch (error) {
            console.error('[StreakTracker] Error loading streak data:', error);
        }
    }

    /**
     * Render streak calendar
     */
    renderCalendar() {
        const container = document.getElementById('streak-calendar');
        if (!container || !this.calendarData) return;

        const { days, current_streak, longest_streak, freezes_available } = this.calendarData;

        // CRITICAL: Sanitize all user-controlled data to prevent XSS
        const safeCurrentStreak = this.safeParseInt(current_streak, 0);
        const safeLongestStreak = this.safeParseInt(longest_streak, 0);
        const safeFreezesAvailable = this.safeParseInt(freezes_available, 0);

        // Create calendar HTML
        let html = `
            <div class="streak-calendar-header">
                <div class="streak-stat">
                    <span class="streak-icon">🔥</span>
                    <span class="streak-count">${safeCurrentStreak}</span>
                    <span class="streak-label">Day Streak</span>
                </div>
                <div class="streak-stat">
                    <span class="streak-icon">❄️</span>
                    <span class="streak-count">${safeFreezesAvailable}</span>
                    <span class="streak-label">Freezes</span>
                </div>
                <div class="streak-stat">
                    <span class="streak-icon">🏆</span>
                    <span class="streak-count">${safeLongestStreak}</span>
                    <span class="streak-label">Best Streak</span>
                </div>
            </div>
            <div class="streak-calendar-grid">
        `;

        // Render calendar days (5 rows x 6 columns = 30 days)
        days.forEach((day, index) => {
            const dayClass = this.getDayClass(day);
            const tooltip = this.getDayTooltip(day);

            // CRITICAL: Sanitize date and counts to prevent XSS
            const safeDate = this.sanitizeHTML(day.date);
            const safeTooltip = this.sanitizeHTML(tooltip);
            const safeDayNumber = this.safeParseInt(new Date(day.date).getDate(), 1);
            const safeActivityCount = this.safeParseInt(day.activity_count, 0);

            html += `
                <div class="calendar-day ${dayClass}"
                     data-date="${safeDate}"
                     title="${safeTooltip}">
                    <div class="day-number">${safeDayNumber}</div>
                    ${day.freeze_used ? '<div class="freeze-indicator">❄️</div>' : ''}
                    ${safeActivityCount > 0 ? `<div class="activity-count">${safeActivityCount}</div>` : ''}
                </div>
            `;
        });

        html += `
            </div>
            <div class="calendar-legend">
                <div class="legend-item">
                    <div class="legend-square active"></div>
                    <span>Activity</span>
                </div>
                <div class="legend-item">
                    <div class="legend-square freeze"></div>
                    <span>Freeze Used</span>
                </div>
                <div class="legend-item">
                    <div class="legend-square inactive"></div>
                    <span>No Activity</span>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Get CSS class for calendar day
     */
    getDayClass(day) {
        if (day.freeze_used) return 'freeze';
        if (day.has_activity) return 'active';
        return 'inactive';
    }

    /**
     * Get tooltip text for calendar day
     */
    getDayTooltip(day) {
        const date = new Date(day.date).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
        
        if (day.freeze_used) {
            return `${date} - Freeze used (${day.activity_count} activities)`;
        }
        if (day.has_activity) {
            return `${date} - ${day.activity_count} ${day.activity_count === 1 ? 'activity' : 'activities'}`;
        }
        return `${date} - No activity`;
    }

    /**
     * Render weekly consistency tracker
     */
    renderConsistencyTracker() {
        const container = document.getElementById('consistency-tracker');
        if (!container || !this.consistencyData) return;

        const { categories, bonus_active, bonus_multiplier, progress, completed_count, total_count } = this.consistencyData;

        // CRITICAL: Sanitize all numeric values to prevent XSS
        const safeProgress = Math.min(Math.max(this.safeParseInt(progress, 0), 0), 100);
        const safeCompletedCount = this.safeParseInt(completed_count, 0);
        const safeTotalCount = this.safeParseInt(total_count, 4);
        const safeBonusMultiplier = parseFloat(bonus_multiplier) || 1.0;

        const categoryIcons = {
            flashcards: '📇',
            quiz: '📝',
            evaluation: '⚖️',
            guide: '📖'
        };

        const categoryLabels = {
            flashcards: 'Flashcards',
            quiz: 'Quiz',
            evaluation: 'Evaluation',
            guide: 'Study Guide'
        };

        let html = `
            <div class="consistency-header">
                <h3>Weekly Consistency Bonus</h3>
                <div class="consistency-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${safeProgress}%"></div>
                    </div>
                    <span class="progress-text">${safeCompletedCount}/${safeTotalCount} Complete</span>
                </div>
            </div>
            <div class="consistency-categories">
        `;

        // Render each category
        Object.entries(categories).forEach(([key, completed]) => {
            html += `
                <div class="consistency-category ${completed ? 'completed' : ''}">
                    <div class="category-icon">${categoryIcons[key]}</div>
                    <div class="category-label">${categoryLabels[key]}</div>
                    <div class="category-check">${completed ? '✓' : ''}</div>
                </div>
            `;
        });

        html += `
            </div>
            <div class="consistency-bonus">
                ${bonus_active ? `
                    <div class="bonus-active">
                        <span class="bonus-icon">🎉</span>
                        <span class="bonus-text">Bonus Active! ${Math.round((bonus_multiplier - 1) * 100)}% Extra XP</span>
                    </div>
                ` : `
                    <div class="bonus-inactive">
                        <span class="bonus-text">Complete all 4 categories to earn XP bonus next week!</span>
                    </div>
                `}
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for activity events to refresh data
        document.addEventListener('gamification:xpgain', () => {
            this.refresh();
        });

        // Refresh every 5 minutes
        setInterval(() => this.refresh(), 5 * 60 * 1000);
    }

    /**
     * Refresh streak data
     */
    async refresh() {
        await this.loadStreakData();
        this.renderCalendar();
        this.renderConsistencyTracker();
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.streakTracker = new StreakTracker();
    });
} else {
    window.streakTracker = new StreakTracker();
}

