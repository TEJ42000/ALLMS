/**
 * Achievements System
 * Tracks user progress and awards badges for milestones
 */

// Achievement definitions
const ACHIEVEMENTS = [
    { id: 'first_steps', name: 'First Steps', desc: 'Answer your first quiz question', points: 10, icon: '🎓', category: 'quiz' },
    { id: 'quiz_master', name: 'Quiz Master', desc: 'Answer 50 quiz questions correctly', points: 100, icon: '📚', category: 'quiz', target: 50 },
    { id: 'week_complete', name: 'Week Complete', desc: 'Complete all content for one week', points: 150, icon: '⭐', category: 'progress' },
    { id: 'exam_ready', name: 'Exam Ready', desc: 'Complete a full mock exam', points: 300, icon: '🏆', category: 'quiz' },
    { id: 'streak_7', name: 'Week Warrior', desc: 'Maintain 7-day streak', points: 100, icon: '🔥', category: 'streak', target: 7 },
    { id: 'streak_30', name: 'Month Master', desc: 'Maintain 30-day streak', points: 500, icon: '💪', category: 'streak', target: 30 },
    { id: 'point_1000', name: 'Point Collector', desc: 'Earn 1,000 points', points: 100, icon: '💰', category: 'points', target: 1000 },
    { id: 'point_5000', name: 'Overachiever', desc: 'Earn 5,000 points', points: 500, icon: '🌟', category: 'points', target: 5000 },
    { id: 'tripartite_master', name: 'Framework Guru', desc: 'Master tripartite framework', points: 200, icon: '🧠', category: 'special' },
    { id: 'echr_expert', name: 'ECHR Expert', desc: 'Master all Article 6 questions', points: 200, icon: '⚖️', category: 'special' }
];

// User stats (loaded from Firestore)
let userStats = {
    achievements: [],
    totalPoints: 0,
    quizQuestionsAnswered: 0,
    quizQuestionsCorrect: 0,
    flashcardsMastered: 0,
    currentStreak: 0,
    lastActivityDate: null,
    dailyLogins: 0
};

// Check interval
let achievementCheckInterval = null;

/**
 * Initialize achievements system
 */
async function initAchievements() {
    console.log('[Achievements] Initializing...');
    
    // Load user stats from Firestore
    await loadUserStats();
    
    // Update daily login streak
    await updateStreak();
    
    // Start periodic achievement checking
    if (achievementCheckInterval) {
        clearInterval(achievementCheckInterval);
    }
    achievementCheckInterval = setInterval(checkAchievements, 5000);
    
    // Initial check
    await checkAchievements();
    
    console.log('[Achievements] Initialized');
}

/**
 * Load user stats from Firestore gamification API
 *
 * FIX #278: Map from actual gamification API response format to local stats format.
 * The API returns: { total_xp, current_level, streak: {current_count, ...}, activities: {...} }
 * We also load from localStorage for achievement progress that doesn't map to the API.
 */
async function loadUserStats() {
    if (!COURSE_ID) return;

    // Load local achievement data from localStorage first
    const localData = localStorage.getItem('allms_achievements_data');
    if (localData) {
        try {
            const parsed = JSON.parse(localData);
            userStats = {
                achievements: parsed.achievements || [],
                totalPoints: parsed.totalPoints || 0,
                quizQuestionsAnswered: parsed.quizQuestionsAnswered || 0,
                quizQuestionsCorrect: parsed.quizQuestionsCorrect || 0,
                flashcardsMastered: parsed.flashcardsMastered || 0,
                currentStreak: parsed.currentStreak || 0,
                lastActivityDate: parsed.lastActivityDate || null,
                dailyLogins: parsed.dailyLogins || 0
            };
            console.log('[Achievements] Loaded local stats:', userStats);
        } catch (e) {
            console.error('[Achievements] Error parsing local stats:', e);
        }
    }

    // Also try to sync streak from gamification API
    try {
        const response = await secureFetch(`${API_BASE}/api/gamification/stats`);
        if (response.ok) {
            const data = await response.json();
            // Sync streak from gamification API (this is the authoritative source)
            if (data.streak && typeof data.streak.current_count === 'number') {
                userStats.currentStreak = data.streak.current_count;
            }
            // Sync XP as points (convert from gamification system)
            if (typeof data.total_xp === 'number') {
                userStats.totalPoints = Math.max(userStats.totalPoints, data.total_xp);
            }
            console.log('[Achievements] Synced with gamification API, streak:', userStats.currentStreak);
        }
    } catch (error) {
        console.error('[Achievements] Error syncing with gamification API:', error);
    }
}

/**
 * Update streak based on last activity
 */
async function updateStreak() {
    const today = new Date().toISOString().split('T')[0];
    const lastDate = userStats.lastActivityDate;
    
    if (!lastDate) {
        // First login
        userStats.currentStreak = 1;
        userStats.lastActivityDate = today;
        await awardPoints(5, 'daily_login');
    } else if (lastDate !== today) {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toISOString().split('T')[0];
        
        if (lastDate === yesterdayStr) {
            // Consecutive day
            userStats.currentStreak++;
            await awardPoints(5, 'daily_login');
        } else {
            // Streak broken
            userStats.currentStreak = 1;
        }
        
        userStats.lastActivityDate = today;
        userStats.dailyLogins++;
        await saveUserStats();
    }
}

/**
 * Check for new achievements
 */
async function checkAchievements() {
    for (const achievement of ACHIEVEMENTS) {
        // Skip if already earned
        if (userStats.achievements.includes(achievement.id)) {
            continue;
        }
        
        let earned = false;
        
        switch (achievement.id) {
            case 'first_steps':
                earned = userStats.quizQuestionsAnswered >= 1;
                break;
            case 'quiz_master':
                earned = userStats.quizQuestionsCorrect >= 50;
                break;
            case 'streak_7':
                earned = userStats.currentStreak >= 7;
                break;
            case 'streak_30':
                earned = userStats.currentStreak >= 30;
                break;
            case 'point_1000':
                earned = userStats.totalPoints >= 1000;
                break;
            case 'point_5000':
                earned = userStats.totalPoints >= 5000;
                break;
            // Add more achievement checks as needed
        }
        
        if (earned) {
            await unlockAchievement(achievement);
        }
    }
}

/**
 * Unlock an achievement
 */
async function unlockAchievement(achievement) {
    console.log('[Achievements] Unlocking:', achievement.name);
    
    // Add to earned achievements
    userStats.achievements.push(achievement.id);
    
    // Award points
    await awardPoints(achievement.points, 'achievement');
    
    // Save to Firestore
    await saveUserStats();
    
    // Show notification
    showAchievementNotification(achievement);
    
    // Trigger confetti
    triggerConfetti();
}

/**
 * Award points to user
 */
async function awardPoints(points, reason) {
    userStats.totalPoints += points;
    console.log(`[Achievements] Awarded ${points} points for ${reason}. Total: ${userStats.totalPoints}`);
    
    // Update UI if on badges page
    updateBadgesUI();
}

/**
 * Save user stats to localStorage
 *
 * FIX #278: Save to localStorage instead of non-existent POST endpoint.
 * The gamification API doesn't have a POST /stats endpoint - it uses /activity
 * for logging. Achievement progress is tracked locally until proper backend integration.
 */
async function saveUserStats() {
    if (!COURSE_ID) return;

    try {
        const dataToSave = {
            achievements: userStats.achievements,
            totalPoints: userStats.totalPoints,
            quizQuestionsAnswered: userStats.quizQuestionsAnswered,
            quizQuestionsCorrect: userStats.quizQuestionsCorrect,
            flashcardsMastered: userStats.flashcardsMastered,
            currentStreak: userStats.currentStreak,
            lastActivityDate: userStats.lastActivityDate,
            dailyLogins: userStats.dailyLogins,
            lastSaved: new Date().toISOString()
        };
        localStorage.setItem('allms_achievements_data', JSON.stringify(dataToSave));
        console.log('[Achievements] Saved stats to localStorage');
    } catch (error) {
        console.error('[Achievements] Error saving stats:', error);
    }
}

/**
 * Show achievement notification popup
 */
function showAchievementNotification(achievement) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'achievement-notification';
    notification.innerHTML = `
        <div class="achievement-icon">${achievement.icon}</div>
        <div class="achievement-content">
            <div class="achievement-title">Achievement Unlocked!</div>
            <div class="achievement-name">${achievement.name}</div>
            <div class="achievement-points">+${achievement.points} points</div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Trigger slide-in animation
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

/**
 * Trigger confetti effect
 */
function triggerConfetti() {
    // Simple confetti effect using emoji
    const confettiContainer = document.createElement('div');
    confettiContainer.className = 'confetti-container';
    document.body.appendChild(confettiContainer);
    
    const emojis = ['🎉', '⭐', '✨', '🏆', '🎊'];
    for (let i = 0; i < 30; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.textContent = emojis[Math.floor(Math.random() * emojis.length)];
        confetti.style.left = Math.random() * 100 + '%';
        confetti.style.animationDelay = Math.random() * 0.5 + 's';
        confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
        confettiContainer.appendChild(confetti);
    }
    
    setTimeout(() => confettiContainer.remove(), 4000);
}

/**
 * Record quiz answer
 */
async function recordQuizAnswer(correct) {
    userStats.quizQuestionsAnswered++;
    if (correct) {
        userStats.quizQuestionsCorrect++;
        await awardPoints(10, 'quiz_correct');
    }
    await saveUserStats();
    await checkAchievements();
}

/**
 * Record flashcard mastered
 */
async function recordFlashcardMastered() {
    userStats.flashcardsMastered++;
    await awardPoints(5, 'flashcard_mastered');
    await saveUserStats();
    await checkAchievements();
}

/**
 * Get achievement progress
 */
function getAchievementProgress(achievement) {
    switch (achievement.id) {
        case 'quiz_master':
            return { current: userStats.quizQuestionsCorrect, target: 50 };
        case 'streak_7':
            return { current: userStats.currentStreak, target: 7 };
        case 'streak_30':
            return { current: userStats.currentStreak, target: 30 };
        case 'point_1000':
            return { current: userStats.totalPoints, target: 1000 };
        case 'point_5000':
            return { current: userStats.totalPoints, target: 5000 };
        default:
            return null;
    }
}

// Export functions for use in other modules
window.initAchievements = initAchievements;
window.recordQuizAnswer = recordQuizAnswer;
window.recordFlashcardMastered = recordFlashcardMastered;
window.userStats = userStats;
window.ACHIEVEMENTS = ACHIEVEMENTS;
window.getAchievementProgress = getAchievementProgress;

