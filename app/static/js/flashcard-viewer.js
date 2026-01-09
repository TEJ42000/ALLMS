/**
 * Flashcard Viewer Component
 *
 * Provides interactive flashcard study interface with:
 * - Card flip animation
 * - Navigation controls
 * - Progress tracking
 * - Keyboard shortcuts
 * - Mobile touch gestures
 */

// MEDIUM FIX: Extract magic numbers to constants
const FLASHCARD_CONSTANTS = {
    MAX_CARD_LENGTH: 5000,
    NAVIGATION_LOCK_MS: 50,
    SWIPE_THRESHOLD_PX: 50,
    FLIP_ANIMATION_MS: 600
};

class FlashcardViewer {
    constructor(containerId, flashcards = [], options = {}) {
        // HIGH: Validate containerId
        if (!containerId || typeof containerId !== 'string') {
            console.error('[FlashcardViewer] Invalid containerId:', containerId);
            throw new Error('FlashcardViewer requires a valid containerId string');
        }

        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[FlashcardViewer] Container element not found:', containerId);
            throw new Error(`Container element with id "${containerId}" not found`);
        }

        // HIGH: Validate and filter flashcards
        if (!Array.isArray(flashcards)) {
            console.error('[FlashcardViewer] flashcards must be an array');
            throw new Error('flashcards parameter must be an array');
        }

        // NEW: Study mode configuration
        this.studyMode = options.studyMode || 'standard'; // 'standard', 'quiz', 'spaced'
        this.showXP = options.showXP !== false; // Show XP by default
        this.onComplete = options.onComplete || null; // Callback when set completed

        // HIGH FIX: Enhanced input validation with comprehensive checks
        this.flashcards = flashcards.filter((card, index) => {
            if (!card || typeof card !== 'object') {
                console.warn(`[FlashcardViewer] Skipping invalid card at index ${index}:`, card);
                return false;
            }

            // HIGH FIX: Validate string types and non-empty content
            const hasQuestionAnswer =
                typeof card.question === 'string' && card.question.trim().length > 0 &&
                typeof card.answer === 'string' && card.answer.trim().length > 0;

            const hasTermDefinition =
                typeof card.term === 'string' && card.term.trim().length > 0 &&
                typeof card.definition === 'string' && card.definition.trim().length > 0;

            if (!hasQuestionAnswer && !hasTermDefinition) {
                console.warn(`[FlashcardViewer] Skipping card at index ${index} without valid content:`, card);
                return false;
            }

            // HIGH FIX: Validate content length (prevent extremely long cards)
            // MEDIUM FIX: Use constant instead of magic number
            const content = card.question || card.term || '';
            const answer = card.answer || card.definition || '';

            if (content.length > FLASHCARD_CONSTANTS.MAX_CARD_LENGTH ||
                answer.length > FLASHCARD_CONSTANTS.MAX_CARD_LENGTH) {
                console.warn(`[FlashcardViewer] Skipping card at index ${index} with content exceeding ${FLASHCARD_CONSTANTS.MAX_CARD_LENGTH} characters`);
                return false;
            }

            return true;
        });

        if (this.flashcards.length === 0) {
            console.warn('[FlashcardViewer] No valid flashcards provided');
            this.showEmptyState();
            return;
        }

        console.log(`[FlashcardViewer] Initialized with ${this.flashcards.length} valid cards`);

        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards = new Set();
        this.knownCards = new Set();
        this.starredCards = new Set();

        // NEW: Quiz mode tracking
        this.quizAnswers = new Map(); // Map<cardIndex, 'correct'|'incorrect'|'skip'>
        this.quizScore = 0;
        this.quizStartTime = null;

        // NEW: XP tracking
        this.xpEarned = 0;
        this.xpPerCard = 1; // Base XP per card reviewed

        // Store original flashcards for restoration after filtering
        this.originalFlashcards = [...this.flashcards];

        // Event listeners for cleanup
        this.eventListeners = [];

        // HIGH FIX: Prevent keyboard shortcut race conditions
        this.isNavigating = false;

        // CRITICAL FIX: Prevent touch gesture race conditions
        this.isSwiping = false;

        // HIGH FIX: beforeUnloadHandler is now set up only when needed (when user has progress)
        this.beforeUnloadHandler = null;

        this.init();
    }

    /**
     * Initialize the flashcard viewer
     */
    init() {
        console.log('[FlashcardViewer] Initializing with', this.flashcards.length, 'cards');
        this.render();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupTouchGestures();
    }

    /**
     * Render the flashcard viewer UI
     * MEDIUM FIX: Add error handling
     */
    render() {
        try {
            // MEDIUM: Validate current index
            if (this.currentIndex < 0 || this.currentIndex >= this.flashcards.length) {
                console.error('[FlashcardViewer] Invalid currentIndex:', this.currentIndex);
                this.currentIndex = 0;
            }

            const currentCard = this.flashcards[this.currentIndex];
            if (!currentCard) {
                console.error('[FlashcardViewer] No card at index:', this.currentIndex);
                this.showError('Unable to load flashcard');
                return;
            }

            // MEDIUM FIX: Validate numeric values before interpolation
            const currentIndex = Math.max(0, Math.min(this.currentIndex, this.flashcards.length - 1));
            const totalCards = Math.max(1, this.flashcards.length);
            const cardNumber = currentIndex + 1;
            const progress = Math.min(100, Math.max(0, (cardNumber / totalCards) * 100));
        
        this.container.innerHTML = `
            <div class="flashcard-viewer">
                <!-- Progress Bar -->
                <div class="flashcard-progress">
                    <div class="progress-bar" role="progressbar"
                         aria-valuenow="${cardNumber}"
                         aria-valuemin="1"
                         aria-valuemax="${totalCards}"
                         aria-label="Flashcard progress">
                        <div class="progress-fill" style="width: ${progress.toFixed(2)}%"></div>
                    </div>
                    <div class="progress-text" aria-live="polite" aria-atomic="true">
                        Card ${cardNumber} of ${totalCards}
                    </div>
                </div>

                <!-- Flashcard Container -->
                <div class="flashcard-container">
                    <div class="flashcard ${this.isFlipped ? 'flipped' : ''}"
                         id="flashcard"
                         role="button"
                         tabindex="0"
                         aria-label="Flashcard ${cardNumber} of ${totalCards}. Click or press Enter to flip."
                         aria-pressed="${this.isFlipped}">
                        <div class="flashcard-inner">
                            <!-- Front of Card -->
                            <div class="flashcard-front" aria-hidden="${this.isFlipped}">
                                <div class="card-label">Question</div>
                                <div class="card-content">
                                    ${this.escapeHtml(currentCard.question || currentCard.term || '')}
                                </div>
                                <div class="card-hint">Click to flip</div>
                            </div>

                            <!-- Back of Card -->
                            <div class="flashcard-back" aria-hidden="${!this.isFlipped}">
                                <div class="card-label">Answer</div>
                                <div class="card-content">
                                    ${this.escapeHtml(currentCard.answer || currentCard.definition || '')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Navigation Controls -->
                <div class="flashcard-controls" role="navigation" aria-label="Flashcard navigation">
                    <button class="btn-control"
                            id="btn-previous"
                            ${this.currentIndex === 0 ? 'disabled' : ''}
                            aria-label="Go to previous flashcard">
                        <span class="icon" aria-hidden="true">←</span>
                        <span class="label">Previous</span>
                    </button>

                    <button class="btn-control btn-flip"
                            id="btn-flip"
                            aria-label="Flip flashcard to see ${this.isFlipped ? 'question' : 'answer'}">
                        <span class="icon" aria-hidden="true">↻</span>
                        <span class="label">Flip</span>
                    </button>

                    <button class="btn-control"
                            id="btn-next"
                            ${this.currentIndex === this.flashcards.length - 1 ? 'disabled' : ''}
                            aria-label="Go to next flashcard">
                        <span class="label">Next</span>
                        <span class="icon" aria-hidden="true">→</span>
                    </button>
                </div>

                <!-- Card Actions -->
                <div class="flashcard-actions" role="toolbar" aria-label="Flashcard actions">
                    ${this.studyMode === 'quiz' && this.isFlipped ? this.renderQuizActions() : this.renderStandardActions()}
                </div>

                <!-- Study Stats -->
                <!-- MEDIUM FIX: Add ARIA live region to stats -->
                <div class="flashcard-stats" role="status" aria-live="polite" aria-atomic="false">
                    <div class="stat">
                        <span class="stat-label">Reviewed:</span>
                        <span class="stat-value">${Math.max(0, this.reviewedCards.size)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Known:</span>
                        <span class="stat-value">${Math.max(0, this.knownCards.size)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Starred:</span>
                        <span class="stat-value">${Math.max(0, this.starredCards.size)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Remaining:</span>
                        <span class="stat-value">${Math.max(0, totalCards - this.reviewedCards.size)}</span>
                    </div>
                </div>
            </div>
        `;
        } catch (error) {
            // MEDIUM FIX: Catch and handle rendering errors
            console.error('[FlashcardViewer] Error rendering:', error);
            this.showError('An error occurred while displaying the flashcard');
        }
    }

    /**
     * Render standard mode actions (star, know, shuffle, restart)
     * NEW: Extracted for quiz mode support
     */
    renderStandardActions() {
        return `
            <button class="btn-action ${this.starredCards.has(this.currentIndex) ? 'active' : ''}"
                    id="btn-star"
                    aria-label="${this.starredCards.has(this.currentIndex) ? 'Unstar' : 'Star'} this card for later review"
                    aria-pressed="${this.starredCards.has(this.currentIndex)}">
                <span class="icon" aria-hidden="true">⭐</span>
                <span class="label">Star</span>
            </button>

            <button class="btn-action ${this.knownCards.has(this.currentIndex) ? 'active' : ''}"
                    id="btn-know"
                    aria-label="${this.knownCards.has(this.currentIndex) ? 'Unmark' : 'Mark'} as known"
                    aria-pressed="${this.knownCards.has(this.currentIndex)}">
                <span class="icon" aria-hidden="true">✓</span>
                <span class="label">Know</span>
            </button>

            <button class="btn-action"
                    id="btn-shuffle"
                    aria-label="Shuffle all flashcards">
                <span class="icon" aria-hidden="true">🔀</span>
                <span class="label">Shuffle</span>
            </button>

            <button class="btn-action"
                    id="btn-restart"
                    aria-label="Restart from the beginning">
                <span class="icon" aria-hidden="true">↺</span>
                <span class="label">Restart</span>
            </button>
        `;
    }

    /**
     * Render quiz mode actions (correct, incorrect, skip)
     * NEW: Self-assessment buttons for quiz mode
     */
    renderQuizActions() {
        const currentAnswer = this.quizAnswers.get(this.currentIndex);
        return `
            <button class="btn-action btn-quiz-correct ${currentAnswer === 'correct' ? 'active' : ''}"
                    id="btn-quiz-correct"
                    aria-label="Mark as correct"
                    aria-pressed="${currentAnswer === 'correct'}">
                <span class="icon" aria-hidden="true">✓</span>
                <span class="label">Correct</span>
            </button>

            <button class="btn-action btn-quiz-incorrect ${currentAnswer === 'incorrect' ? 'active' : ''}"
                    id="btn-quiz-incorrect"
                    aria-label="Mark as incorrect"
                    aria-pressed="${currentAnswer === 'incorrect'}">
                <span class="icon" aria-hidden="true">✗</span>
                <span class="label">Incorrect</span>
            </button>

            <button class="btn-action btn-quiz-skip ${currentAnswer === 'skip' ? 'active' : ''}"
                    id="btn-quiz-skip"
                    aria-label="Skip this card"
                    aria-pressed="${currentAnswer === 'skip'}">
                <span class="icon" aria-hidden="true">→</span>
                <span class="label">Skip</span>
            </button>

            <button class="btn-action"
                    id="btn-star"
                    aria-label="${this.starredCards.has(this.currentIndex) ? 'Unstar' : 'Star'} this card for later review"
                    aria-pressed="${this.starredCards.has(this.currentIndex)}">
                <span class="icon" aria-hidden="true">⭐</span>
                <span class="label">Star</span>
            </button>
        `;
    }

    /**
     * Setup event listeners for controls
     * MEDIUM FIX: Add keyboard handler for flashcard div
     * MEDIUM FIX: Add try-catch for error handling
     */
    setupEventListeners() {
        try {
            // Flip card on click
            const flashcard = document.getElementById('flashcard');
            if (flashcard) {
                const flipHandler = () => this.flipCard();
                flashcard.addEventListener('click', flipHandler);
                this.eventListeners.push({ element: flashcard, event: 'click', handler: flipHandler });

                // MEDIUM FIX: Add keyboard handler for Enter/Space on flashcard
                const keyHandler = (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        this.flipCard();
                    }
                };
                flashcard.addEventListener('keydown', keyHandler);
                this.eventListeners.push({ element: flashcard, event: 'keydown', handler: keyHandler });
            }

        // Navigation buttons
        const btnPrevious = document.getElementById('btn-previous');
        if (btnPrevious) {
            const prevHandler = () => this.previousCard();
            btnPrevious.addEventListener('click', prevHandler);
            this.eventListeners.push({ element: btnPrevious, event: 'click', handler: prevHandler });
        }

        const btnNext = document.getElementById('btn-next');
        if (btnNext) {
            const nextHandler = () => this.nextCard();
            btnNext.addEventListener('click', nextHandler);
            this.eventListeners.push({ element: btnNext, event: 'click', handler: nextHandler });
        }

        const btnFlip = document.getElementById('btn-flip');
        if (btnFlip) {
            const flipBtnHandler = () => this.flipCard();
            btnFlip.addEventListener('click', flipBtnHandler);
            this.eventListeners.push({ element: btnFlip, event: 'click', handler: flipBtnHandler });
        }

        // Action buttons
        const btnStar = document.getElementById('btn-star');
        if (btnStar) {
            const starHandler = () => this.toggleStar();
            btnStar.addEventListener('click', starHandler);
            this.eventListeners.push({ element: btnStar, event: 'click', handler: starHandler });
        }

        const btnKnow = document.getElementById('btn-know');
        if (btnKnow) {
            const knowHandler = () => this.toggleKnown();
            btnKnow.addEventListener('click', knowHandler);
            this.eventListeners.push({ element: btnKnow, event: 'click', handler: knowHandler });
        }

        const btnShuffle = document.getElementById('btn-shuffle');
        if (btnShuffle) {
            const shuffleHandler = () => this.shuffleCards();
            btnShuffle.addEventListener('click', shuffleHandler);
            this.eventListeners.push({ element: btnShuffle, event: 'click', handler: shuffleHandler });
        }

        const btnRestart = document.getElementById('btn-restart');
        if (btnRestart) {
            const restartHandler = () => this.restart();
            btnRestart.addEventListener('click', restartHandler);
            this.eventListeners.push({ element: btnRestart, event: 'click', handler: restartHandler });
        }

        // NEW: Quiz mode buttons
        const btnQuizCorrect = document.getElementById('btn-quiz-correct');
        if (btnQuizCorrect) {
            const correctHandler = () => this.markQuizAnswer('correct');
            btnQuizCorrect.addEventListener('click', correctHandler);
            this.eventListeners.push({ element: btnQuizCorrect, event: 'click', handler: correctHandler });
        }

        const btnQuizIncorrect = document.getElementById('btn-quiz-incorrect');
        if (btnQuizIncorrect) {
            const incorrectHandler = () => this.markQuizAnswer('incorrect');
            btnQuizIncorrect.addEventListener('click', incorrectHandler);
            this.eventListeners.push({ element: btnQuizIncorrect, event: 'click', handler: incorrectHandler });
        }

        const btnQuizSkip = document.getElementById('btn-quiz-skip');
        if (btnQuizSkip) {
            const skipHandler = () => this.markQuizAnswer('skip');
            btnQuizSkip.addEventListener('click', skipHandler);
            this.eventListeners.push({ element: btnQuizSkip, event: 'click', handler: skipHandler });
        }
        } catch (error) {
            // MEDIUM FIX: Catch and log setup errors
            console.error('[FlashcardViewer] Error setting up event listeners:', error);
            this.showError('Failed to setup flashcard controls');
        }
    }

    /**
     * Setup keyboard shortcuts
     * CRITICAL FIX: Store handler as instance property for proper cleanup
     */
    setupKeyboardShortcuts() {
        // Store as instance property for cleanup
        this.keyHandler = (e) => {
            // Ignore if user is typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.previousCard();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.nextCard();
                    break;
                case ' ':
                case 'Enter':
                    e.preventDefault();
                    this.flipCard();
                    break;
                case 's':
                    e.preventDefault();
                    this.toggleStar();
                    break;
                case 'k':
                    e.preventDefault();
                    this.toggleKnown();
                    break;
            }
        };

        document.addEventListener('keydown', this.keyHandler);
        this.eventListeners.push({ element: document, event: 'keydown', handler: this.keyHandler });
    }

    /**
     * Setup touch gestures for mobile
     * CRITICAL FIX: Use instance properties instead of local variables
     */
    setupTouchGestures() {
        const flashcard = document.getElementById('flashcard');
        if (!flashcard) return;

        // CRITICAL FIX: Initialize instance properties (not local variables)
        this.touchStartX = 0;
        this.touchEndX = 0;

        const touchStartHandler = (e) => {
            // CRITICAL FIX: Set instance property, not local variable
            this.touchStartX = e.changedTouches[0].screenX;
        };

        const touchEndHandler = (e) => {
            // CRITICAL FIX: Set instance property, not local variable
            this.touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe();
        };

        flashcard.addEventListener('touchstart', touchStartHandler);
        flashcard.addEventListener('touchend', touchEndHandler);

        this.eventListeners.push({ element: flashcard, event: 'touchstart', handler: touchStartHandler });
        this.eventListeners.push({ element: flashcard, event: 'touchend', handler: touchEndHandler });
    }

    /**
     * Handle swipe gesture
     * CRITICAL FIX: Prevent race conditions with swipe lock
     * MEDIUM FIX: Use constant instead of magic number
     */
    handleSwipe() {
        // CRITICAL FIX: Prevent overlapping swipes
        if (this.isSwiping) {
            return;
        }

        // MEDIUM FIX: Use constant instead of magic number
        const diff = this.touchStartX - this.touchEndX;

        if (Math.abs(diff) > FLASHCARD_CONSTANTS.SWIPE_THRESHOLD_PX) {
            this.isSwiping = true;

            if (diff > 0) {
                // Swipe left - next card
                this.nextCard();
            } else {
                // Swipe right - previous card
                this.previousCard();
            }

            // Release lock after navigation completes
            setTimeout(() => {
                this.isSwiping = false;
            }, FLASHCARD_CONSTANTS.NAVIGATION_LOCK_MS);
        }
    }

    /**
     * Flip the current card
     * HIGH FIX: Set up beforeUnloadHandler when user makes progress
     */
    flipCard() {
        this.isFlipped = !this.isFlipped;
        const flashcard = document.getElementById('flashcard');
        if (flashcard) {
            flashcard.classList.toggle('flipped');
        }

        // Mark as reviewed when flipped
        if (this.isFlipped) {
            this.reviewedCards.add(this.currentIndex);
            // HIGH FIX: Set up beforeUnloadHandler now that user has progress
            this.setupBeforeUnloadHandler();
        }
    }

    /**
     * Navigate to previous card
     * CRITICAL FIX: Remove old listeners before adding new ones
     * HIGH FIX: Prevent race conditions with navigation lock
     */
    previousCard() {
        // HIGH FIX: Prevent race condition from rapid key presses
        if (this.isNavigating) {
            return;
        }

        if (this.currentIndex > 0) {
            this.isNavigating = true;
            this.currentIndex--;
            this.isFlipped = false;
            this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
            this.render();
            this.setupEventListeners();

            // Release lock after render completes
            // MEDIUM FIX: Use constant instead of magic number
            setTimeout(() => {
                this.isNavigating = false;
            }, FLASHCARD_CONSTANTS.NAVIGATION_LOCK_MS);
        }
    }

    /**
     * Navigate to next card
     * CRITICAL FIX: Remove old listeners before adding new ones
     * HIGH FIX: Prevent race conditions with navigation lock
     */
    nextCard() {
        // HIGH FIX: Prevent race condition from rapid key presses
        if (this.isNavigating) {
            return;
        }

        if (this.currentIndex < this.flashcards.length - 1) {
            this.isNavigating = true;
            this.currentIndex++;
            this.isFlipped = false;
            this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
            this.render();
            this.setupEventListeners();

            // Release lock after render completes
            // MEDIUM FIX: Use constant instead of magic number
            setTimeout(() => {
                this.isNavigating = false;
            }, FLASHCARD_CONSTANTS.NAVIGATION_LOCK_MS);
        } else {
            // Completed all cards
            this.showCompletionMessage();
        }
    }

    /**
     * Toggle star on current card
     * CRITICAL FIX: Remove old listeners before re-rendering
     * HIGH FIX: Set up beforeUnloadHandler when user makes progress
     */
    toggleStar() {
        if (this.starredCards.has(this.currentIndex)) {
            this.starredCards.delete(this.currentIndex);
        } else {
            this.starredCards.add(this.currentIndex);
            // HIGH FIX: Set up beforeUnloadHandler now that user has progress
            this.setupBeforeUnloadHandler();
        }
        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Toggle known status on current card
     * CRITICAL FIX: Remove old listeners before re-rendering
     * HIGH FIX: Set up beforeUnloadHandler when user makes progress
     */
    toggleKnown() {
        if (this.knownCards.has(this.currentIndex)) {
            this.knownCards.delete(this.currentIndex);
        } else {
            this.knownCards.add(this.currentIndex);
            // HIGH FIX: Set up beforeUnloadHandler now that user has progress
            this.setupBeforeUnloadHandler();
        }
        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Shuffle the flashcards
     * HIGH FIX: Clear tracking sets since indices will be invalid after shuffle
     * MEDIUM FIX: Use styled confirm dialog instead of native confirm()
     */
    async shuffleCards() {
        // HIGH FIX: Warn user that progress will be reset
        // MEDIUM FIX: Use styled confirm dialog
        if (this.reviewedCards.size > 0 || this.knownCards.size > 0 || this.starredCards.size > 0) {
            const confirmed = await this.showConfirm(
                'Shuffling will reset your progress (reviewed, known, and starred cards). Continue?'
            );
            if (!confirmed) {
                return;
            }
        }

        // Fisher-Yates shuffle
        for (let i = this.flashcards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.flashcards[i], this.flashcards[j]] = [this.flashcards[j], this.flashcards[i]];
        }

        // HIGH FIX: Clear all tracking sets since indices are now invalid
        this.reviewedCards.clear();
        this.knownCards.clear();
        this.starredCards.clear();

        this.currentIndex = 0;
        this.isFlipped = false;
        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Restart from the beginning
     * CRITICAL FIX: Remove old listeners before re-rendering
     * MEDIUM FIX: Add confirmation dialog with styled modal
     */
    async restart() {
        // MEDIUM FIX: Confirm restart if user has progress
        // MEDIUM FIX: Use styled confirm dialog
        if (this.reviewedCards.size > 0 || this.knownCards.size > 0 || this.starredCards.size > 0) {
            const confirmed = await this.showConfirm(
                'Restarting will reset all your progress (reviewed, known, and starred cards). Continue?'
            );
            if (!confirmed) {
                return;
            }
        }

        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards.clear();
        this.knownCards.clear();
        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Mark quiz answer (correct, incorrect, skip)
     * NEW: Self-assessment for quiz mode
     */
    markQuizAnswer(answer) {
        if (this.studyMode !== 'quiz') {
            console.warn('[FlashcardViewer] markQuizAnswer called in non-quiz mode');
            return;
        }

        // Start quiz timer on first answer
        if (!this.quizStartTime) {
            this.quizStartTime = Date.now();
        }

        // Store answer
        const previousAnswer = this.quizAnswers.get(this.currentIndex);
        this.quizAnswers.set(this.currentIndex, answer);

        // Update score
        if (answer === 'correct' && previousAnswer !== 'correct') {
            this.quizScore++;
            this.xpEarned += this.xpPerCard;
        } else if (previousAnswer === 'correct' && answer !== 'correct') {
            this.quizScore--;
            this.xpEarned = Math.max(0, this.xpEarned - this.xpPerCard);
        }

        // Mark as reviewed
        this.reviewedCards.add(this.currentIndex);
        this.setupBeforeUnloadHandler();

        // Re-render to update button states
        this.cleanupEventListeners();
        this.render();
        this.setupEventListeners();

        // Auto-advance after marking (optional)
        if (this.currentIndex < this.flashcards.length - 1) {
            setTimeout(() => {
                this.nextCard();
            }, 300); // Small delay for visual feedback
        } else {
            // Quiz complete
            this.showQuizResults();
        }
    }

    /**
     * Format time in seconds to MM:SS
     * NEW: Helper for quiz results
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Show quiz results
     * NEW: Display quiz completion with score and XP
     */
    showQuizResults() {
        const totalCards = this.flashcards.length;
        const correctCount = this.quizScore;
        const incorrectCount = Array.from(this.quizAnswers.values()).filter(a => a === 'incorrect').length;
        const skippedCount = Array.from(this.quizAnswers.values()).filter(a => a === 'skip').length;
        const percentage = Math.round((correctCount / totalCards) * 100);
        const timeTaken = this.quizStartTime ? Math.round((Date.now() - this.quizStartTime) / 1000) : 0;

        this.container.innerHTML = `
            <div class="flashcard-completion quiz-results" role="status" aria-live="polite">
                <div class="completion-icon" aria-hidden="true">🎯</div>
                <h2>Quiz Complete!</h2>

                <div class="quiz-score">
                    <div class="score-circle">
                        <div class="score-percentage">${percentage}%</div>
                        <div class="score-fraction">${correctCount}/${totalCards}</div>
                    </div>
                </div>

                <div class="quiz-stats">
                    <div class="quiz-stat">
                        <span class="stat-icon correct">✓</span>
                        <span class="stat-label">Correct:</span>
                        <span class="stat-value">${correctCount}</span>
                    </div>
                    <div class="quiz-stat">
                        <span class="stat-icon incorrect">✗</span>
                        <span class="stat-label">Incorrect:</span>
                        <span class="stat-value">${incorrectCount}</span>
                    </div>
                    <div class="quiz-stat">
                        <span class="stat-icon skip">→</span>
                        <span class="stat-label">Skipped:</span>
                        <span class="stat-value">${skippedCount}</span>
                    </div>
                    ${timeTaken > 0 ? `
                    <div class="quiz-stat">
                        <span class="stat-icon">⏱️</span>
                        <span class="stat-label">Time:</span>
                        <span class="stat-value">${this.formatTime(timeTaken)}</span>
                    </div>
                    ` : ''}
                    ${this.showXP ? `
                    <div class="quiz-stat xp-earned">
                        <span class="stat-icon">⭐</span>
                        <span class="stat-label">XP Earned:</span>
                        <span class="stat-value">+${this.xpEarned}</span>
                    </div>
                    ` : ''}
                </div>

                <div class="completion-actions">
                    <button class="btn-primary" id="btn-review-incorrect">
                        Review Incorrect
                    </button>
                    <button class="btn-secondary" id="btn-restart-quiz">
                        Restart Quiz
                    </button>
                    <button class="btn-secondary" id="btn-back-quiz">
                        Back to Sets
                    </button>
                </div>
            </div>
        `;

        // Set up button handlers
        const btnReviewIncorrect = document.getElementById('btn-review-incorrect');
        if (btnReviewIncorrect) {
            btnReviewIncorrect.addEventListener('click', () => this.reviewIncorrectCards());
        }

        const btnRestartQuiz = document.getElementById('btn-restart-quiz');
        if (btnRestartQuiz) {
            btnRestartQuiz.addEventListener('click', () => this.restart());
        }

        const btnBackQuiz = document.getElementById('btn-back-quiz');
        if (btnBackQuiz) {
            btnBackQuiz.addEventListener('click', () => {
                if (this.onComplete) {
                    this.onComplete({ score: correctCount, total: totalCards, xp: this.xpEarned });
                }
            });
        }

        // Trigger XP gain event for gamification integration
        if (this.showXP && this.xpEarned > 0) {
            document.dispatchEvent(new CustomEvent('gamification:xpgain', {
                detail: { xp: this.xpEarned, source: 'flashcard_quiz' }
            }));
        }
    }

    /**
     * Review only incorrect cards from quiz
     * NEW: Filter to incorrect answers
     */
    reviewIncorrectCards() {
        const incorrectIndices = [];
        this.quizAnswers.forEach((answer, index) => {
            if (answer === 'incorrect') {
                incorrectIndices.push(index);
            }
        });

        if (incorrectIndices.length === 0) {
            this.showError('No incorrect cards to review!');
            return;
        }

        // Store original state
        if (!this.isFilteredView) {
            this.originalFlashcards = [...this.flashcards];
            this.originalReviewedCards = new Set(this.reviewedCards);
            this.originalKnownCards = new Set(this.knownCards);
            this.originalStarredCards = new Set(this.starredCards);
        }

        // Filter to incorrect cards
        this.flashcards = incorrectIndices.map(index => this.originalFlashcards[index]);
        this.isFilteredView = true;
        this.currentIndex = 0;
        this.isFlipped = false;

        // Reset quiz state for review
        this.quizAnswers.clear();
        this.quizScore = 0;
        this.quizStartTime = null;

        this.cleanupEventListeners();
        this.render();
        this.setupEventListeners();
    }

    /**
     * Show completion message
     * MEDIUM FIX: Validate numeric values
     */
    showCompletionMessage() {
        // MEDIUM FIX: Validate and sanitize numeric values
        const totalCards = Math.max(1, this.flashcards.length);
        const reviewedCount = Math.max(0, this.reviewedCards.size);
        const knownCount = Math.max(0, this.knownCards.size);
        const starredCount = Math.max(0, this.starredCards.size);
        const accuracy = Math.min(100, Math.max(0, (knownCount / totalCards) * 100));

        this.container.innerHTML = `
            <div class="flashcard-completion">
                <div class="completion-icon" aria-hidden="true">🎉</div>
                <h2>Great Job!</h2>
                <p>You've completed all ${totalCards} flashcards!</p>

                <div class="completion-stats">
                    <div class="stat-large">
                        <div class="stat-value">${reviewedCount}</div>
                        <div class="stat-label">Cards Reviewed</div>
                    </div>
                    <div class="stat-large">
                        <div class="stat-value">${knownCount}</div>
                        <div class="stat-label">Marked as Known</div>
                    </div>
                    <div class="stat-large">
                        <div class="stat-value">${accuracy.toFixed(0)}%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                </div>

                <div class="completion-actions">
                    <button class="btn-primary" id="btn-restart-completion">
                        Study Again
                    </button>
                    <button class="btn-secondary" id="btn-review-starred">
                        Review Starred (${starredCount})
                    </button>
                    ${this.isFilteredView ? `
                        <button class="btn-secondary" id="btn-back-to-full">
                            Back to Full Deck
                        </button>
                    ` : ''}
                </div>
            </div>
        `;

        // Setup completion buttons
        const btnRestartCompletion = document.getElementById('btn-restart-completion');
        if (btnRestartCompletion) {
            btnRestartCompletion.addEventListener('click', () => this.restart());
        }

        const btnReviewStarred = document.getElementById('btn-review-starred');
        if (btnReviewStarred) {
            btnReviewStarred.addEventListener('click', () => this.reviewStarredCards());
        }

        const btnBackToFull = document.getElementById('btn-back-to-full');
        if (btnBackToFull) {
            btnBackToFull.addEventListener('click', () => this.restoreFullDeck());
        }
    }

    /**
     * Review only starred cards
     * HIGH FIX: Don't lose original flashcards - store them for restoration
     * HIGH FIX: Validate starred indices to prevent corruption
     */
    reviewStarredCards() {
        // CRITICAL FIX: Replace alert() with showError()
        if (this.starredCards.size === 0) {
            this.showError('No starred cards to review!');
            return;
        }

        // HIGH FIX: Store original flashcards if not already stored
        if (!this.isFilteredView) {
            this.originalFlashcards = [...this.flashcards];
            this.originalReviewedCards = new Set(this.reviewedCards);
            this.originalKnownCards = new Set(this.knownCards);
            this.originalStarredCards = new Set(this.starredCards);
        }

        // HIGH FIX: Filter to only starred cards with index validation
        const starredIndices = Array.from(this.starredCards);
        const validIndices = starredIndices.filter(index => {
            return index >= 0 && index < this.originalFlashcards.length;
        });

        // CRITICAL FIX: Replace alert() with showError()
        if (validIndices.length === 0) {
            this.showError('No valid starred cards found!');
            return;
        }

        this.flashcards = validIndices.map(index => this.originalFlashcards[index]);

        this.isFilteredView = true;
        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards.clear();
        this.knownCards.clear();
        this.starredCards.clear();

        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Restore full deck from filtered view
     * HIGH FIX: Allow users to return to full deck
     * CRITICAL FIX: Remove old listeners before re-rendering
     */
    restoreFullDeck() {
        if (!this.isFilteredView || !this.originalFlashcards) {
            return;
        }

        this.flashcards = [...this.originalFlashcards];
        this.reviewedCards = new Set(this.originalReviewedCards);
        this.knownCards = new Set(this.originalKnownCards);
        this.starredCards = new Set(this.originalStarredCards);

        this.isFilteredView = false;
        this.currentIndex = 0;
        this.isFlipped = false;

        this.cleanupEventListeners();  // CRITICAL: Remove old listeners first
        this.render();
        this.setupEventListeners();
    }

    /**
     * Show empty state when no valid flashcards
     * HIGH: Handle empty flashcard arrays gracefully
     */
    showEmptyState() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="flashcard-empty-state" role="alert">
                <div class="empty-icon" aria-hidden="true">📭</div>
                <h2>No Flashcards Available</h2>
                <p>There are no valid flashcards to display.</p>
                <p class="empty-hint">Please check that your flashcards have either question/answer or term/definition fields.</p>
            </div>
        `;
    }

    /**
     * Show error message
     * MEDIUM FIX: User-friendly error handling
     * HIGH FIX: Remove inline onclick for CSP compliance
     */
    showError(message) {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="flashcard-error" role="alert">
                <div class="error-icon" aria-hidden="true">⚠️</div>
                <h2>Oops! Something went wrong</h2>
                <p>${this.escapeHtml(message)}</p>
                <button class="btn-primary" id="btn-reload-error">
                    Reload Page
                </button>
            </div>
        `;

        // HIGH FIX: Add event listener instead of inline onclick
        const btnReload = document.getElementById('btn-reload-error');
        if (btnReload) {
            btnReload.addEventListener('click', () => {
                location.reload();
            });
        }
    }

    /**
     * MEDIUM FIX: escapeHtml() is now in utils.js (shared across files)
     * Use global escapeHtml() function instead of instance method
     */
    escapeHtml(text) {
        return escapeHtml(text);
    }

    /**
     * Show confirmation dialog
     * MEDIUM FIX: Replace native confirm() with styled modal
     * @param {string} message - The confirmation message
     * @returns {Promise<boolean>} - True if confirmed, false if cancelled
     */
    showConfirm(message) {
        return new Promise((resolve) => {
            // Create confirmation overlay
            const overlay = document.createElement('div');
            overlay.className = 'error-overlay'; // Reuse error overlay styles
            overlay.innerHTML = `
                <div class="error-dialog" role="alertdialog" aria-labelledby="confirm-title" aria-describedby="confirm-message">
                    <div class="error-icon" aria-hidden="true">⚠️</div>
                    <h2 id="confirm-title">Confirm Action</h2>
                    <p id="confirm-message">${this.escapeHtml(message)}</p>
                    <div class="confirm-buttons">
                        <button class="btn-secondary" id="btn-cancel-confirm">Cancel</button>
                        <button class="btn-primary" id="btn-confirm-confirm" autofocus>Continue</button>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);

            // CRITICAL FIX: Shared cleanup function
            const closeDialog = (result) => {
                if (document.body.contains(overlay)) {
                    document.body.removeChild(overlay);
                }
                document.removeEventListener('keydown', escHandler);
                resolve(result);
            };

            // Handle button clicks
            const btnCancel = document.getElementById('btn-cancel-confirm');
            const btnConfirm = document.getElementById('btn-confirm-confirm');

            if (btnCancel) {
                btnCancel.addEventListener('click', () => closeDialog(false));
            }

            if (btnConfirm) {
                btnConfirm.addEventListener('click', () => closeDialog(true));
                btnConfirm.focus();
            }

            // Handle ESC key (cancel)
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    closeDialog(false);
                }
            };
            document.addEventListener('keydown', escHandler);
        });
    }

    /**
     * Setup beforeUnloadHandler to warn user about losing progress
     * HIGH FIX: Only set up when user has actual progress to lose
     */
    setupBeforeUnloadHandler() {
        // Only set up if not already set up
        if (this.beforeUnloadHandler) {
            return;
        }

        // Only warn if user has progress
        const hasProgress = this.reviewedCards.size > 0 ||
                           this.knownCards.size > 0 ||
                           this.starredCards.size > 0;

        if (!hasProgress) {
            return;
        }

        this.beforeUnloadHandler = (e) => {
            // Modern browsers ignore custom messages, but we still need to return a value
            e.preventDefault();
            e.returnValue = '';
            return '';
        };

        window.addEventListener('beforeunload', this.beforeUnloadHandler);
    }

    /**
     * Cleanup event listeners (internal use for re-rendering)
     * CRITICAL FIX: Remove only DOM event listeners, not beforeunload
     */
    cleanupEventListeners() {
        this.eventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.eventListeners = [];
    }

    /**
     * Cleanup all resources including beforeunload handler
     * CRITICAL FIX: Full cleanup when destroying viewer
     */
    cleanup() {
        console.log('[FlashcardViewer] Cleaning up all resources...');

        // Remove DOM event listeners
        this.cleanupEventListeners();

        // CRITICAL FIX: Remove beforeunload handler
        if (this.beforeUnloadHandler) {
            window.removeEventListener('beforeunload', this.beforeUnloadHandler);
            this.beforeUnloadHandler = null;
        }
    }
}

// CRITICAL FIX: Store beforeunload handler for proper cleanup
// This is now handled in the FlashcardViewer constructor and cleanup method

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlashcardViewer;
}

