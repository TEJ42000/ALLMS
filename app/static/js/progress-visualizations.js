/**
 * Progress Visualizations
 * 
 * Provides enhanced progress visualizations including:
 * - Color-transitioning progress bars (red → yellow → green)
 * - Circular progress indicators
 * - Animated stat cards
 * - Real-time progress updates
 */

class ProgressVisualizations {
    constructor() {
        this.init();
    }

    init() {
        console.log('[ProgressVisualizations] Initializing...');
        this.enhanceProgressBars();
        this.createCircularIndicators();
        this.enhanceStatCards();
        this.setupRealTimeUpdates();
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
     * Enhance progress bars with color transitions
     */
    enhanceProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar, .level-progress-fill');
        
        progressBars.forEach(bar => {
            this.updateProgressBarColor(bar);
            
            // Watch for changes
            const observer = new MutationObserver(() => {
                this.updateProgressBarColor(bar);
            });
            
            observer.observe(bar, {
                attributes: true,
                attributeFilter: ['style']
            });
        });
    }

    /**
     * Update progress bar color based on percentage
     */
    updateProgressBarColor(bar) {
        const width = parseFloat(bar.style.width) || 0;
        const percentage = Math.min(100, Math.max(0, width));
        
        // Calculate color based on percentage
        let color;
        if (percentage < 33) {
            // Red to Yellow (0-33%)
            const ratio = percentage / 33;
            color = this.interpolateColor('#f56565', '#ecc94b', ratio);
        } else if (percentage < 66) {
            // Yellow to Light Green (33-66%)
            const ratio = (percentage - 33) / 33;
            color = this.interpolateColor('#ecc94b', '#9ae6b4', ratio);
        } else {
            // Light Green to Dark Green (66-100%)
            const ratio = (percentage - 66) / 34;
            color = this.interpolateColor('#9ae6b4', '#48bb78', ratio);
        }
        
        bar.style.backgroundColor = color;
        bar.style.transition = 'all 0.5s ease';
    }

    /**
     * Interpolate between two hex colors
     */
    interpolateColor(color1, color2, ratio) {
        const hex = (color) => {
            const c = color.substring(1);
            return parseInt(c, 16);
        };
        
        const r1 = (hex(color1) >> 16) & 0xff;
        const g1 = (hex(color1) >> 8) & 0xff;
        const b1 = hex(color1) & 0xff;
        
        const r2 = (hex(color2) >> 16) & 0xff;
        const g2 = (hex(color2) >> 8) & 0xff;
        const b2 = hex(color2) & 0xff;
        
        const r = Math.round(r1 + (r2 - r1) * ratio);
        const g = Math.round(g1 + (g2 - g1) * ratio);
        const b = Math.round(b1 + (b2 - b1) * ratio);
        
        return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
    }

    /**
     * Create circular progress indicators
     */
    createCircularIndicators() {
        // Add circular progress to header
        this.addHeaderCircularProgress();
        
        // Add exam readiness circle
        this.addExamReadinessCircle();
    }

    /**
     * Add circular progress indicator to header
     */
    addHeaderCircularProgress() {
        const levelInfo = document.querySelector('.level-info');
        if (!levelInfo) return;

        const circularProgress = document.createElement('div');
        circularProgress.className = 'circular-progress-container';
        circularProgress.innerHTML = `
            <svg class="circular-progress" width="60" height="60">
                <circle class="circular-progress-bg" cx="30" cy="30" r="25"></circle>
                <circle class="circular-progress-fill" cx="30" cy="30" r="25"></circle>
            </svg>
            <div class="circular-progress-text">
                <span class="circular-progress-level">1</span>
            </div>
        `;

        levelInfo.insertBefore(circularProgress, levelInfo.firstChild);
        
        // Update with actual data
        this.updateHeaderCircularProgress();
    }

    /**
     * Update header circular progress
     */
    async updateHeaderCircularProgress() {
        try {
            const response = await fetch('/api/gamification/stats');

            // Validate response status
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Validate data structure
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response data');
            }

            const circle = document.querySelector('.circular-progress-fill');
            const levelText = document.querySelector('.circular-progress-level');

            if (!circle || !levelText) return;

            // Calculate progress percentage with sanitized values
            const totalXP = this.sanitizeNumber(data.total_xp, 0);
            const xpToNext = this.sanitizeNumber(data.xp_to_next_level, 100);
            const currentLevelXP = totalXP % xpToNext;
            const percentage = xpToNext > 0 ? (currentLevelXP / xpToNext) * 100 : 0;

            // Update circle
            const circumference = 2 * Math.PI * 25;
            const offset = circumference - (percentage / 100) * circumference;

            circle.style.strokeDasharray = `${circumference} ${circumference}`;
            circle.style.strokeDashoffset = offset;
            circle.style.transition = 'stroke-dashoffset 1s ease';

            // Update level text with sanitized value
            const currentLevel = this.sanitizeNumber(data.current_level, 1);
            levelText.textContent = currentLevel;

            // Update color based on progress
            const color = this.getProgressColor(percentage);
            circle.style.stroke = color;

        } catch (error) {
            console.error('[ProgressVisualizations] Error updating circular progress:', error);
        }
    }

    /**
     * Add exam readiness circular indicator
     */
    addExamReadinessCircle() {
        const dashboard = document.querySelector('.gamification-dashboard');
        if (!dashboard) return;

        const readinessCard = document.createElement('div');
        readinessCard.className = 'stat-card exam-readiness-card';
        readinessCard.innerHTML = `
            <h3>📊 Exam Readiness</h3>
            <div class="exam-readiness-circle-container">
                <svg class="exam-readiness-circle" width="150" height="150">
                    <circle class="exam-circle-bg" cx="75" cy="75" r="60"></circle>
                    <circle class="exam-circle-fill" cx="75" cy="75" r="60"></circle>
                </svg>
                <div class="exam-readiness-percentage">
                    <span class="exam-percentage-value">0</span>%
                </div>
            </div>
            <div class="exam-readiness-label">Based on your progress</div>
        `;

        dashboard.appendChild(readinessCard);
        
        // Update with actual data
        this.updateExamReadiness();
    }

    /**
     * Update exam readiness indicator
     */
    async updateExamReadiness() {
        try {
            const response = await fetch('/api/gamification/stats');

            // Validate response status
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Validate data structure
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response data');
            }

            const circle = document.querySelector('.exam-circle-fill');
            const percentageText = document.querySelector('.exam-percentage-value');

            if (!circle || !percentageText) return;

            // Calculate readiness based on activities with sanitized values
            const activities = data.activities || {};
            const quizEasy = this.sanitizeNumber(activities.quiz_easy_passed, 0);
            const quizHard = this.sanitizeNumber(activities.quiz_hard_passed, 0);
            const evalLow = this.sanitizeNumber(activities.evaluation_low, 0);
            const evalHigh = this.sanitizeNumber(activities.evaluation_high, 0);
            const studyGuides = this.sanitizeNumber(activities.study_guide_completed, 0);

            const quizzesPassed = quizEasy + quizHard;
            const evaluationsCompleted = evalLow + evalHigh;

            // Simple readiness formula (can be enhanced)
            const readiness = Math.min(100, Math.max(0, Math.round(
                (quizzesPassed * 10) +
                (evaluationsCompleted * 15) +
                (studyGuides * 5)
            )));

            // Animate circle
            const circumference = 2 * Math.PI * 60;
            const offset = circumference - (readiness / 100) * circumference;

            circle.style.strokeDasharray = `${circumference} ${circumference}`;
            circle.style.strokeDashoffset = offset;
            circle.style.transition = 'stroke-dashoffset 1.5s ease';

            // Animate percentage
            this.animateNumber(percentageText, 0, readiness, 1500);

            // Update color
            const color = this.getProgressColor(readiness);
            circle.style.stroke = color;

        } catch (error) {
            console.error('[ProgressVisualizations] Error updating exam readiness:', error);
        }
    }

    /**
     * Get color based on progress percentage
     */
    getProgressColor(percentage) {
        if (percentage < 33) return '#f56565'; // Red
        if (percentage < 66) return '#ecc94b'; // Yellow
        return '#48bb78'; // Green
    }

    /**
     * Animate number counter
     */
    animateNumber(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.round(current);
        }, 16);
    }

    /**
     * Enhance stat cards with micro-interactions
     */
    enhanceStatCards() {
        const statCards = document.querySelectorAll('.stat-card');
        
        statCards.forEach(card => {
            // Add hover effect
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-8px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
            });
            
            // Add click animation
            card.addEventListener('click', () => {
                card.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    card.style.transform = 'translateY(-8px) scale(1.02)';
                }, 100);
            });
        });
    }

    /**
     * Setup real-time progress updates
     */
    setupRealTimeUpdates() {
        // Listen for XP updates with { once: false } (default, but explicit for clarity)
        document.addEventListener('gamification:xpgain', () => {
            this.updateHeaderCircularProgress();
            this.updateExamReadiness();
        });

        // Listen for level ups
        document.addEventListener('gamification:levelup', () => {
            this.updateHeaderCircularProgress();
        });

        // Periodic refresh (every 30 seconds)
        setInterval(() => {
            this.updateHeaderCircularProgress();
            this.updateExamReadiness();
        }, 30000);
    }

    /**
     * Add trend indicators to stat cards
     */
    addTrendIndicators(card, currentValue, previousValue) {
        const trend = currentValue - previousValue;
        const trendElement = document.createElement('div');
        trendElement.className = 'stat-trend';
        
        if (trend > 0) {
            trendElement.innerHTML = `<span class="trend-up">↑ ${trend}</span>`;
            trendElement.classList.add('positive');
        } else if (trend < 0) {
            trendElement.innerHTML = `<span class="trend-down">↓ ${Math.abs(trend)}</span>`;
            trendElement.classList.add('negative');
        } else {
            trendElement.innerHTML = `<span class="trend-neutral">→ 0</span>`;
            trendElement.classList.add('neutral');
        }
        
        card.appendChild(trendElement);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.progressVisualizations = new ProgressVisualizations();
    });
} else {
    window.progressVisualizations = new ProgressVisualizations();
}

