/**
 * Quiz Display Enhancements - Phase 1
 * 
 * Implements:
 * - Question type indicator
 * - Timer display (for timed quizzes)
 * - Visual progress bar
 * - Animated transitions
 * 
 * Security: All DOM manipulation uses safe methods (createElement, textContent)
 * Performance: Optimized for 60fps animations
 */

/**
 * Create question type indicator badge
 * @param {string} questionType - Type of question (multiple_choice, true_false, etc.)
 * @returns {HTMLElement} - Question type badge element
 */
function createQuestionTypeBadge(questionType) {
    const badge = document.createElement('span');
    badge.className = 'question-type-badge';
    
    // Map question types to display text
    const typeMap = {
        'multiple_choice': 'Multiple Choice',
        'true_false': 'True/False',
        'short_answer': 'Short Answer'
    };
    
    badge.textContent = typeMap[questionType] || 'Multiple Choice';
    badge.setAttribute('aria-label', `Question type: ${badge.textContent}`);
    
    return badge;
}

/**
 * Create visual progress bar
 * @param {number} current - Current question index (0-based)
 * @param {number} total - Total number of questions
 * @returns {HTMLElement} - Progress bar container element
 */
function createProgressBar(current, total) {
    // HIGH #3: Input validation
    if (typeof current !== 'number' || !Number.isInteger(current)) {
        console.error('createProgressBar: current must be an integer');
        current = 0;
    }

    if (typeof total !== 'number' || !Number.isInteger(total) || total <= 0) {
        console.error('createProgressBar: total must be a positive integer');
        total = 1;
    }

    if (current < 0) {
        console.error('createProgressBar: current cannot be negative');
        current = 0;
    }

    if (current >= total) {
        console.error('createProgressBar: current cannot be >= total');
        current = total - 1;
    }

    const container = document.createElement('div');
    container.className = 'quiz-progress-bar';
    container.setAttribute('role', 'progressbar');
    container.setAttribute('aria-valuenow', current + 1);
    container.setAttribute('aria-valuemin', '1');
    container.setAttribute('aria-valuemax', total);
    container.setAttribute('aria-label', `Question ${current + 1} of ${total}`);

    const fill = document.createElement('div');
    fill.className = 'quiz-progress-fill';

    // Calculate percentage (0-100)
    const percentage = ((current + 1) / total) * 100;
    fill.style.width = `${percentage}%`;

    // Add transition for smooth animation
    fill.style.transition = 'width 0.3s ease';

    container.appendChild(fill);

    return container;
}

/**
 * Timer class for timed quizzes
 */
class QuizTimer {
    constructor(timeLimit, onTick, onExpire) {
        this.timeLimit = timeLimit; // in seconds
        this.timeRemaining = timeLimit;
        this.onTick = onTick;
        this.onExpire = onExpire;
        this.intervalId = null;
        this.isPaused = false;
        this.isExpired = false;  // HIGH #4: Prevent race condition
    }

    start() {
        if (this.intervalId) return; // Already running

        this.intervalId = setInterval(() => {
            if (!this.isPaused && !this.isExpired) {
                this.timeRemaining--;

                // HIGH #4: Call onTick in try-catch to prevent errors from breaking timer
                if (this.onTick) {
                    try {
                        this.onTick(this.timeRemaining);
                    } catch (error) {
                        console.error('Error in timer onTick callback:', error);
                    }
                }

                if (this.timeRemaining <= 0 && !this.isExpired) {
                    // HIGH #4: Set flag before calling callbacks to prevent race condition
                    this.isExpired = true;
                    this.stop();

                    // HIGH #4: Call onExpire in try-catch and use setTimeout to avoid blocking
                    if (this.onExpire) {
                        setTimeout(() => {
                            try {
                                this.onExpire();
                            } catch (error) {
                                console.error('Error in timer onExpire callback:', error);
                            }
                        }, 0);
                    }
                }
            }
        }, 1000);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    pause() {
        this.isPaused = true;
    }
    
    resume() {
        this.isPaused = false;
    }
    
    getTimeRemaining() {
        return this.timeRemaining;
    }
    
    getFormattedTime() {
        const minutes = Math.floor(this.timeRemaining / 60);
        const seconds = this.timeRemaining % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}

/**
 * Create timer display element
 * @param {QuizTimer} timer - Timer instance
 * @returns {HTMLElement} - Timer display element
 */
function createTimerDisplay(timer) {
    const container = document.createElement('div');
    container.className = 'quiz-timer';
    container.setAttribute('role', 'timer');
    container.setAttribute('aria-live', 'polite');
    
    const icon = document.createElement('span');
    icon.className = 'timer-icon';
    icon.textContent = '⏱️';
    icon.setAttribute('aria-hidden', 'true');
    
    const timeText = document.createElement('span');
    timeText.className = 'timer-text';
    timeText.textContent = timer.getFormattedTime();
    timeText.setAttribute('aria-label', `Time remaining: ${timer.getFormattedTime()}`);
    
    container.appendChild(icon);
    container.appendChild(timeText);
    
    // Update display every second
    timer.onTick = (timeRemaining) => {
        timeText.textContent = timer.getFormattedTime();
        timeText.setAttribute('aria-label', `Time remaining: ${timer.getFormattedTime()}`);
        
        // Add warning class when time is running low (< 1 minute)
        if (timeRemaining < 60 && timeRemaining >= 10) {
            container.classList.add('warning');
            container.classList.remove('danger');
        } else if (timeRemaining < 10) {
            container.classList.add('danger');
            container.classList.remove('warning');
        } else {
            container.classList.remove('warning', 'danger');
        }
    };
    
    return container;
}

/**
 * Update progress bar animation
 * @param {HTMLElement} progressBar - Progress bar container
 * @param {number} current - Current question index
 * @param {number} total - Total questions
 */
function updateProgressBar(progressBar, current, total) {
    const fill = progressBar.querySelector('.quiz-progress-fill');
    if (!fill) return;
    
    const percentage = ((current + 1) / total) * 100;
    fill.style.width = `${percentage}%`;
    
    // Update ARIA attributes
    progressBar.setAttribute('aria-valuenow', current + 1);
    progressBar.setAttribute('aria-label', `Question ${current + 1} of ${total}`);
}

/**
 * Enhanced question header with all Phase 1 features
 * @param {Object} question - Question object
 * @param {number} questionNum - Question number (1-based)
 * @param {number} totalQuestions - Total number of questions
 * @param {QuizTimer} timer - Timer instance (optional)
 * @returns {HTMLElement} - Enhanced question header
 */
function createEnhancedQuestionHeader(question, questionNum, totalQuestions, timer = null) {
    const header = document.createElement('div');
    header.className = 'question-header-enhanced';
    
    // Top row: Question number and type
    const topRow = document.createElement('div');
    topRow.className = 'header-top-row';
    
    const questionTitle = document.createElement('h3');
    questionTitle.textContent = `Question ${questionNum}`;
    topRow.appendChild(questionTitle);
    
    // Question type badge
    const questionType = question.type || 'multiple_choice';
    const typeBadge = createQuestionTypeBadge(questionType);
    topRow.appendChild(typeBadge);
    
    // Difficulty badge (existing)
    if (question.difficulty) {
        const difficultyBadge = document.createElement('span');
        difficultyBadge.className = `difficulty-badge difficulty-${question.difficulty}`;
        difficultyBadge.textContent = question.difficulty;
        topRow.appendChild(difficultyBadge);
    }
    
    header.appendChild(topRow);
    
    // Middle row: Progress bar
    const progressBar = createProgressBar(questionNum - 1, totalQuestions);
    header.appendChild(progressBar);
    
    // Bottom row: Timer (if timed quiz)
    if (timer) {
        const timerDisplay = createTimerDisplay(timer);
        header.appendChild(timerDisplay);
    }
    
    return header;
}

/**
 * Add fade-in animation to question card
 * Uses CSS classes for CSP compliance (Issue #179)
 * @param {HTMLElement} element - Element to animate
 */
function addFadeInAnimation(element) {
    // Add hidden state class
    element.classList.add('quiz-fade-in-hidden');

    // Trigger reflow to ensure initial state is applied
    element.offsetHeight;

    // Transition to visible state using CSS class
    element.classList.remove('quiz-fade-in-hidden');
    element.classList.add('quiz-fade-in-visible');
}

/**
 * Initialize Phase 1 enhancements
 * @param {Object} quizState - Current quiz state
 * @returns {Object} - Enhancement utilities
 */
function initializePhase1Enhancements(quizState) {
    let timer = null;
    
    // Create timer if quiz is timed
    if (quizState.timeLimit) {
        timer = new QuizTimer(
            quizState.timeLimit,
            null, // onTick handled by createTimerDisplay
            () => {
                // Auto-submit quiz when time expires
                console.log('Quiz time expired - auto-submitting');
                if (typeof submitQuiz === 'function') {
                    submitQuiz();
                }
            }
        );
        timer.start();
    }
    
    return {
        timer,
        createEnhancedQuestionHeader,
        updateProgressBar,
        addFadeInAnimation
    };
}

// HIGH #6: Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        createQuestionTypeBadge,
        createProgressBar,
        QuizTimer,
        createTimerDisplay,
        updateProgressBar,
        createEnhancedQuestionHeader,
        addFadeInAnimation,
        initializePhase1Enhancements
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.createQuestionTypeBadge = createQuestionTypeBadge;
    window.createProgressBar = createProgressBar;
    window.QuizTimer = QuizTimer;
    window.createTimerDisplay = createTimerDisplay;
    window.updateProgressBar = updateProgressBar;
    window.createEnhancedQuestionHeader = createEnhancedQuestionHeader;
    window.addFadeInAnimation = addFadeInAnimation;
    window.initializePhase1Enhancements = initializePhase1Enhancements;
}

