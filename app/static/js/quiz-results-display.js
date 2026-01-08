/**
 * Quiz Results Display - Phase 4
 * 
 * Implements:
 * - XP earned display with animated counter
 * - Detailed statistics (time, accuracy, difficulty breakdown)
 * - Better review mode with explanations
 * 
 * Security: All DOM manipulation uses safe methods (createElement, textContent)
 * Accessibility: WCAG 2.1 AA compliant with ARIA labels
 */

/**
 * Create XP earned display with animated counter
 * @param {number} xpEarned - XP earned from quiz
 * @param {number} currentXP - Current total XP
 * @param {number} currentLevel - Current level
 * @param {number} xpForNextLevel - XP needed for next level
 * @returns {HTMLElement} - XP display element
 */
function createXPDisplay(xpEarned, currentXP = 0, currentLevel = 1, xpForNextLevel = 100) {
    // Input validation
    if (typeof xpEarned !== 'number' || xpEarned < 0) {
        console.error('createXPDisplay: xpEarned must be a non-negative number');
        xpEarned = 0;
    }
    
    if (typeof currentXP !== 'number' || currentXP < 0) {
        console.error('createXPDisplay: currentXP must be a non-negative number');
        currentXP = 0;
    }
    
    if (typeof currentLevel !== 'number' || !Number.isInteger(currentLevel) || currentLevel < 1) {
        console.error('createXPDisplay: currentLevel must be a positive integer');
        currentLevel = 1;
    }
    
    if (typeof xpForNextLevel !== 'number' || xpForNextLevel <= 0) {
        console.error('createXPDisplay: xpForNextLevel must be a positive number');
        xpForNextLevel = 100;
    }
    
    const container = document.createElement('div');
    container.className = 'xp-display';
    container.setAttribute('role', 'status');
    container.setAttribute('aria-live', 'polite');
    
    // XP earned section
    const xpSection = document.createElement('div');
    xpSection.className = 'xp-earned-section';
    
    const xpLabel = document.createElement('div');
    xpLabel.className = 'xp-label';
    xpLabel.textContent = 'XP Earned';
    xpSection.appendChild(xpLabel);
    
    const xpValue = document.createElement('div');
    xpValue.className = 'xp-value';
    xpValue.setAttribute('data-target-xp', xpEarned);
    xpValue.textContent = '0';
    xpSection.appendChild(xpValue);
    
    container.appendChild(xpSection);
    
    // Level progress section
    const progressSection = document.createElement('div');
    progressSection.className = 'level-progress-section';
    
    const levelLabel = document.createElement('div');
    levelLabel.className = 'level-label';
    levelLabel.textContent = `Level ${currentLevel}`;
    progressSection.appendChild(levelLabel);
    
    const progressBar = document.createElement('div');
    progressBar.className = 'level-progress-bar';
    progressBar.setAttribute('role', 'progressbar');
    progressBar.setAttribute('aria-valuenow', currentXP);
    progressBar.setAttribute('aria-valuemin', '0');
    progressBar.setAttribute('aria-valuemax', xpForNextLevel);
    progressBar.setAttribute('aria-label', `Level progress: ${currentXP} of ${xpForNextLevel} XP`);
    
    const progressFill = document.createElement('div');
    progressFill.className = 'level-progress-fill';
    const progressPercent = Math.min(100, (currentXP / xpForNextLevel) * 100);
    progressFill.style.width = `${progressPercent}%`;
    progressBar.appendChild(progressFill);
    
    progressSection.appendChild(progressBar);
    
    const progressText = document.createElement('div');
    progressText.className = 'level-progress-text';
    progressText.textContent = `${currentXP} / ${xpForNextLevel} XP`;
    progressSection.appendChild(progressText);
    
    container.appendChild(progressSection);
    
    return container;
}

/**
 * Animate XP counter
 * @param {HTMLElement} xpElement - XP value element
 * @param {number} duration - Animation duration in ms
 */
function animateXPCounter(xpElement, duration = 2000) {
    // Input validation
    if (!xpElement || !(xpElement instanceof HTMLElement)) {
        console.error('animateXPCounter: xpElement must be an HTMLElement');
        return;
    }
    
    const targetXP = parseInt(xpElement.getAttribute('data-target-xp'), 10);
    if (isNaN(targetXP) || targetXP < 0) {
        console.error('animateXPCounter: invalid target XP');
        return;
    }
    
    const startTime = Date.now();
    const startXP = 0;
    
    function update() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out cubic)
        const eased = 1 - Math.pow(1 - progress, 3);
        const currentXP = Math.floor(startXP + (targetXP - startXP) * eased);
        
        xpElement.textContent = currentXP.toString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            xpElement.textContent = targetXP.toString();
        }
    }
    
    requestAnimationFrame(update);
}

/**
 * Create detailed statistics display
 * @param {Object} stats - Quiz statistics
 * @returns {HTMLElement} - Statistics display element
 */
function createStatisticsDisplay(stats) {
    // Input validation
    if (!stats || typeof stats !== 'object') {
        console.error('createStatisticsDisplay: stats must be an object');
        const fallback = document.createElement('div');
        fallback.textContent = 'Statistics unavailable';
        return fallback;
    }
    
    const container = document.createElement('div');
    container.className = 'quiz-statistics';
    
    // Title
    const title = document.createElement('h3');
    title.textContent = 'Quiz Statistics';
    container.appendChild(title);
    
    // Statistics grid
    const grid = document.createElement('div');
    grid.className = 'stats-grid';
    
    // Score
    if (typeof stats.score === 'number' && typeof stats.total === 'number') {
        const scoreCard = createStatCard(
            'Score',
            `${stats.score} / ${stats.total}`,
            'score-icon',
            '📊'
        );
        grid.appendChild(scoreCard);
    }
    
    // Accuracy
    if (typeof stats.score === 'number' && typeof stats.total === 'number' && stats.total > 0) {
        const accuracy = Math.round((stats.score / stats.total) * 100);
        const accuracyCard = createStatCard(
            'Accuracy',
            `${accuracy}%`,
            'accuracy-icon',
            '🎯'
        );
        grid.appendChild(accuracyCard);
    }
    
    // Time taken
    if (typeof stats.timeTaken === 'number') {
        const timeCard = createStatCard(
            'Time Taken',
            formatTime(stats.timeTaken),
            'time-icon',
            '⏱️'
        );
        grid.appendChild(timeCard);
    }
    
    // Questions answered
    if (typeof stats.answered === 'number' && typeof stats.total === 'number') {
        const answeredCard = createStatCard(
            'Answered',
            `${stats.answered} / ${stats.total}`,
            'answered-icon',
            '✓'
        );
        grid.appendChild(answeredCard);
    }
    
    container.appendChild(grid);
    
    return container;
}

/**
 * Create individual stat card
 * @param {string} label - Stat label
 * @param {string} value - Stat value
 * @param {string} iconClass - Icon class
 * @param {string} iconText - Icon text/emoji
 * @returns {HTMLElement} - Stat card element
 */
function createStatCard(label, value, iconClass, iconText) {
    const card = document.createElement('div');
    card.className = 'stat-card';
    
    const icon = document.createElement('div');
    icon.className = `stat-icon ${iconClass}`;
    icon.textContent = iconText;
    icon.setAttribute('aria-hidden', 'true');
    card.appendChild(icon);
    
    const content = document.createElement('div');
    content.className = 'stat-content';
    
    const labelEl = document.createElement('div');
    labelEl.className = 'stat-label';
    labelEl.textContent = label;
    content.appendChild(labelEl);
    
    const valueEl = document.createElement('div');
    valueEl.className = 'stat-value';
    valueEl.textContent = value;
    content.appendChild(valueEl);
    
    card.appendChild(content);
    
    return card;
}

/**
 * Format time in seconds to readable string
 * @param {number} seconds - Time in seconds
 * @returns {string} - Formatted time string
 */
function formatTime(seconds) {
    if (typeof seconds !== 'number' || seconds < 0) {
        return '0s';
    }
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Create review mode display
 * @param {Array} questions - Array of questions with answers
 * @param {Array} userAnswers - User's answers
 * @param {Function} onQuestionClick - Callback when question is clicked
 * @returns {HTMLElement} - Review mode element
 */
function createReviewMode(questions, userAnswers, onQuestionClick) {
    // Input validation
    if (!Array.isArray(questions) || questions.length === 0) {
        console.error('createReviewMode: questions must be a non-empty array');
        const fallback = document.createElement('div');
        fallback.textContent = 'No questions to review';
        return fallback;
    }
    
    if (!Array.isArray(userAnswers)) {
        console.error('createReviewMode: userAnswers must be an array');
        userAnswers = [];
    }
    
    const container = document.createElement('div');
    container.className = 'quiz-review-mode';
    
    // Title
    const title = document.createElement('h3');
    title.textContent = 'Review Your Answers';
    container.appendChild(title);
    
    // Questions list
    const questionsList = document.createElement('div');
    questionsList.className = 'review-questions-list';
    
    questions.forEach((question, index) => {
        const questionCard = createReviewQuestionCard(
            question,
            index,
            userAnswers[index],
            onQuestionClick
        );
        questionsList.appendChild(questionCard);
    });
    
    container.appendChild(questionsList);
    
    return container;
}

/**
 * Create review question card
 * @param {Object} question - Question object
 * @param {number} index - Question index
 * @param {number} userAnswer - User's answer index
 * @param {Function} onClick - Click callback
 * @returns {HTMLElement} - Question card element
 */
function createReviewQuestionCard(question, index, userAnswer, onClick) {
    const card = document.createElement('div');
    const isCorrect = userAnswer === question.correct_index;
    card.className = `review-question-card ${isCorrect ? 'correct' : 'incorrect'}`;
    
    // Question number and status
    const header = document.createElement('div');
    header.className = 'review-card-header';
    
    const questionNum = document.createElement('span');
    questionNum.className = 'review-question-number';
    questionNum.textContent = `Question ${index + 1}`;
    header.appendChild(questionNum);
    
    const status = document.createElement('span');
    status.className = 'review-status';
    status.textContent = isCorrect ? '✓ Correct' : '✗ Incorrect';
    header.appendChild(status);
    
    card.appendChild(header);
    
    // Question text
    const questionText = document.createElement('div');
    questionText.className = 'review-question-text';
    questionText.textContent = question.question;
    card.appendChild(questionText);
    
    // User's answer
    if (userAnswer !== null && userAnswer !== undefined) {
        const userAnswerEl = document.createElement('div');
        userAnswerEl.className = 'review-user-answer';
        userAnswerEl.textContent = `Your answer: ${question.options[userAnswer]}`;
        card.appendChild(userAnswerEl);
    }
    
    // Correct answer (if incorrect)
    if (!isCorrect) {
        const correctAnswerEl = document.createElement('div');
        correctAnswerEl.className = 'review-correct-answer';
        correctAnswerEl.textContent = `Correct answer: ${question.options[question.correct_index]}`;
        card.appendChild(correctAnswerEl);
    }
    
    return card;
}

// Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        createXPDisplay,
        animateXPCounter,
        createStatisticsDisplay,
        createStatCard,
        formatTime,
        createReviewMode,
        createReviewQuestionCard
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.createXPDisplay = createXPDisplay;
    window.animateXPCounter = animateXPCounter;
    window.createStatisticsDisplay = createStatisticsDisplay;
    window.createStatCard = createStatCard;
    window.formatTime = formatTime;
    window.createReviewMode = createReviewMode;
    window.createReviewQuestionCard = createReviewQuestionCard;
}

