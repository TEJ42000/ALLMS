/**
 * Badges Page UI
 * Displays all achievements in a grid with progress tracking
 */

/**
 * Initialize badges page
 */
function initBadgesPage() {
    console.log('[Badges] Initializing badges page');
    renderBadgesPage();
}

/**
 * Render the badges page
 */
function renderBadgesPage() {
    const container = document.getElementById('badges-content');
    if (!container) return;
    
    const earnedCount = userStats.achievements.length;
    const totalCount = ACHIEVEMENTS.length;
    const completionPercent = Math.round((earnedCount / totalCount) * 100);
    
    container.innerHTML = `
        <div class="badges-header">
            <h2>🏆 Achievements</h2>
            <div class="badges-stats">
                <div class="stat-card">
                    <div class="stat-value">${userStats.totalPoints.toLocaleString()}</div>
                    <div class="stat-label">Total Points</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${earnedCount}/${totalCount}</div>
                    <div class="stat-label">Badges Earned</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${completionPercent}%</div>
                    <div class="stat-label">Completion</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${userStats.currentStreak} 🔥</div>
                    <div class="stat-label">Current Streak</div>
                </div>
            </div>
        </div>
        
        <div class="badges-grid">
            ${ACHIEVEMENTS.map(achievement => renderBadgeCard(achievement)).join('')}
        </div>
    `;
}

/**
 * Render a single badge card
 */
function renderBadgeCard(achievement) {
    const isEarned = userStats.achievements.includes(achievement.id);
    const progress = getAchievementProgress(achievement);
    
    let progressHTML = '';
    if (!isEarned && progress) {
        const percent = Math.min(100, Math.round((progress.current / progress.target) * 100));
        progressHTML = `
            <div class="badge-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percent}%"></div>
                </div>
                <div class="progress-text">${progress.current}/${progress.target}</div>
            </div>
        `;
    }
    
    return `
        <div class="badge-card ${isEarned ? 'earned' : 'locked'}">
            <div class="badge-icon-container">
                <div class="badge-icon">${achievement.icon}</div>
                ${!isEarned ? '<div class="badge-lock">🔒</div>' : ''}
                ${isEarned ? '<div class="badge-glow"></div>' : ''}
            </div>
            <div class="badge-info">
                <div class="badge-name">${achievement.name}</div>
                <div class="badge-desc">${achievement.desc}</div>
                ${progressHTML}
                <div class="badge-points">
                    ${isEarned ? '✓ ' : ''}${achievement.points} points
                </div>
            </div>
        </div>
    `;
}

/**
 * Update badges UI (called when stats change)
 */
function updateBadgesUI() {
    const container = document.getElementById('badges-content');
    if (container && container.innerHTML) {
        renderBadgesPage();
    }
}

// Export for use in other modules
window.initBadgesPage = initBadgesPage;
window.updateBadgesUI = updateBadgesUI;

