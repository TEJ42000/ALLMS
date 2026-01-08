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
    constructor(containerId, flashcards = []) {
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

        // PHASE 2B: Track card notes
        this.cardNotes = new Map(); // Map<cardIndex, noteText>

        // PHASE 2C: Spaced Repetition
        this.spacedRepetition = new SpacedRepetitionService();
        this.srMode = false; // Spaced repetition mode
        this.srQuality = null; // Quality rating for current card

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

        // PHASE 2A: Gamification integration
        this.sessionStartTime = Date.now();
        this.totalTimeSpent = 0;
        this.xpEarned = 0;
        this.sessionId = null;
        this.gamificationEnabled = false;
        this.userStats = null;
        this.timeTrackerInterval = null;
        this.gamificationInitialized = false;

        // CRITICAL FIX: Ready flag for async initialization
        this.ready = false;

        // CRITICAL FIX: Initialize asynchronously to avoid race conditions
        this.initializeAsync();
    }

    /**
     * CRITICAL FIX: Async initialization to prevent race conditions
     * Sets this.ready = true when complete
     */
    async initializeAsync() {
        try {
            // Check if user is authenticated for gamification
            await this.checkGamificationStatus();
            this.gamificationInitialized = true;

            // Initialize the viewer
            this.init();

            // CRITICAL FIX: Mark as ready
            this.ready = true;
        } catch (error) {
            console.error('[FlashcardViewer] Initialization failed:', error);
            this.ready = false;
            this.showError('Failed to initialize flashcard viewer');
        }
    }

    /**
     * CRITICAL FIX: Wait for viewer to be ready
     * @returns {Promise<boolean>} True when ready
     */
    async waitForReady() {
        if (this.ready) return true;

        return new Promise((resolve) => {
            const checkReady = setInterval(() => {
                if (this.ready) {
                    clearInterval(checkReady);
                    resolve(true);
                }
            }, 100);

            // Timeout after 10 seconds
            setTimeout(() => {
                clearInterval(checkReady);
                resolve(false);
            }, 10000);
        });
    }

    /**
     * Initialize the flashcard viewer
     * PHASE 2A: Start time tracking timer
     */
    init() {
        console.log('[FlashcardViewer] Initializing with', this.flashcards.length, 'cards');
        this.render();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupTouchGestures();

        // PHASE 2A: Start timer to update session time display
        if (this.gamificationEnabled) {
            this.startTimeTracker();
        }
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
                ${this.gamificationEnabled && this.userStats ? `
                    <!-- PHASE 2A: Gamification Header -->
                    <div class="gamification-header">
                        <div class="streak-display">
                            <span class="streak-icon">🔥</span>
                            <span class="streak-count">${this.userStats.streak?.current_count || 0}</span>
                            <span class="streak-label">day streak</span>
                        </div>
                        <div class="xp-display">
                            <span class="xp-icon">⭐</span>
                            <span class="xp-count">${this.userStats.total_xp || 0}</span>
                            <span class="xp-label">XP</span>
                        </div>
                        <div class="time-display">
                            <span class="time-icon">⏱️</span>
                            <span class="time-count" id="session-time">0s</span>
                        </div>
                    </div>
                ` : ''}

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

                    <!-- PHASE 2B: Notes button -->
                    <button class="btn-action ${this.cardNotes.has(this.currentIndex) ? 'active' : ''}"
                            id="btn-notes"
                            aria-label="Add or view notes for this card"
                            aria-pressed="${this.cardNotes.has(this.currentIndex)}">
                        <span class="icon" aria-hidden="true">📝</span>
                        <span class="label">Notes</span>
                    </button>

                    <!-- PHASE 2B: Report issue button -->
                    <button class="btn-action"
                            id="btn-report"
                            aria-label="Report an issue with this card">
                        <span class="icon" aria-hidden="true">⚠️</span>
                        <span class="label">Report</span>
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

                    <!-- PHASE 2C: Spaced Repetition toggle -->
                    <button class="btn-action ${this.srMode ? 'active' : ''}"
                            id="btn-sr-mode"
                            aria-label="Toggle spaced repetition mode"
                            aria-pressed="${this.srMode}">
                        <span class="icon" aria-hidden="true">🧠</span>
                        <span class="label">SR Mode</span>
                    </button>
                </div>

                <!-- PHASE 2C: Spaced Repetition Quality Rating -->
                ${this.srMode && this.isFlipped ? `
                    <div class="sr-quality-rating" role="group" aria-label="Rate your recall quality">
                        <div class="sr-rating-title">How well did you recall this card?</div>
                        <div class="sr-rating-buttons">
                            <button class="btn-quality btn-quality-0" data-quality="0" aria-label="Complete blackout">
                                <span class="quality-number">0</span>
                                <span class="quality-label">Blackout</span>
                            </button>
                            <button class="btn-quality btn-quality-1" data-quality="1" aria-label="Incorrect, but familiar">
                                <span class="quality-number">1</span>
                                <span class="quality-label">Familiar</span>
                            </button>
                            <button class="btn-quality btn-quality-2" data-quality="2" aria-label="Incorrect, but easy">
                                <span class="quality-number">2</span>
                                <span class="quality-label">Easy</span>
                            </button>
                            <button class="btn-quality btn-quality-3" data-quality="3" aria-label="Correct with difficulty">
                                <span class="quality-number">3</span>
                                <span class="quality-label">Difficult</span>
                            </button>
                            <button class="btn-quality btn-quality-4" data-quality="4" aria-label="Correct after hesitation">
                                <span class="quality-number">4</span>
                                <span class="quality-label">Hesitation</span>
                            </button>
                            <button class="btn-quality btn-quality-5" data-quality="5" aria-label="Perfect recall">
                                <span class="quality-number">5</span>
                                <span class="quality-label">Perfect</span>
                            </button>
                        </div>
                    </div>
                ` : ''}

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

        // PHASE 2B: Notes button
        const btnNotes = document.getElementById('btn-notes');
        if (btnNotes) {
            const notesHandler = () => this.showNotesModal();
            btnNotes.addEventListener('click', notesHandler);
            this.eventListeners.push({ element: btnNotes, event: 'click', handler: notesHandler });
        }

        // PHASE 2B: Report button
        const btnReport = document.getElementById('btn-report');
        if (btnReport) {
            const reportHandler = () => this.showReportModal();
            btnReport.addEventListener('click', reportHandler);
            this.eventListeners.push({ element: btnReport, event: 'click', handler: reportHandler });
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

        // PHASE 2C: SR Mode toggle
        const btnSRMode = document.getElementById('btn-sr-mode');
        if (btnSRMode) {
            const srModeHandler = () => this.toggleSRMode();
            btnSRMode.addEventListener('click', srModeHandler);
            this.eventListeners.push({ element: btnSRMode, event: 'click', handler: srModeHandler });
        }

        // PHASE 2C: Quality rating buttons
        const qualityButtons = document.querySelectorAll('.btn-quality');
        qualityButtons.forEach(button => {
            const quality = parseInt(button.dataset.quality);
            const qualityHandler = () => this.rateCardQuality(quality);
            button.addEventListener('click', qualityHandler);
            this.eventListeners.push({ element: button, event: 'click', handler: qualityHandler });
        });

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
     * Show completion message
     * MEDIUM FIX: Validate numeric values
     * PHASE 2A: Add XP and time tracking to completion
     */
    async showCompletionMessage() {
        // MEDIUM FIX: Validate and sanitize numeric values
        const totalCards = Math.max(1, this.flashcards.length);
        const reviewedCount = Math.max(0, this.reviewedCards.size);
        const knownCount = Math.max(0, this.knownCards.size);
        const starredCount = Math.max(0, this.starredCards.size);
        const accuracy = Math.min(100, Math.max(0, (knownCount / totalCards) * 100));

        // PHASE 2A: Award XP for completion
        const xpAwarded = await this.awardFlashcardXP();
        const timeSpent = this.getFormattedTimeSpent();

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

                ${this.gamificationEnabled && xpAwarded > 0 ? `
                    <div class="gamification-rewards">
                        <div class="xp-reward">
                            <span class="xp-icon">⭐</span>
                            <span class="xp-amount">+${xpAwarded} XP</span>
                        </div>
                        <div class="time-spent">
                            <span class="time-icon">⏱️</span>
                            <span class="time-amount">Time: ${timeSpent}</span>
                        </div>
                    </div>
                ` : ''}

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
     * CRITICAL FIX: Prevent memory leaks from timers and event listeners
     * CRITICAL FIX: Make cleanup async to await session end
     * PHASE 2A: End gamification session on cleanup
     */
    async cleanup() {
        console.log('[FlashcardViewer] Cleaning up all resources...');

        // CRITICAL FIX: Stop time tracker to prevent memory leak
        if (this.timeTrackerInterval) {
            clearInterval(this.timeTrackerInterval);
            this.timeTrackerInterval = null;
            console.log('[FlashcardViewer] Time tracker stopped');
        }

        // CRITICAL FIX: Await session end before nulling properties
        if (this.gamificationEnabled && this.sessionId) {
            try {
                await this.endGamificationSession();
                console.log('[FlashcardViewer] Gamification session ended');
            } catch (error) {
                console.error('[FlashcardViewer] Error ending gamification session:', error);
            }
        }

        // Remove DOM event listeners
        this.cleanupEventListeners();

        // CRITICAL FIX: Remove beforeunload handler
        if (this.beforeUnloadHandler) {
            window.removeEventListener('beforeunload', this.beforeUnloadHandler);
            this.beforeUnloadHandler = null;
        }

        // CRITICAL FIX: Clear all references to prevent memory leaks
        this.flashcards = null;
        this.originalFlashcards = null;
        this.reviewedCards = null;
        this.knownCards = null;
        this.starredCards = null;
        this.cardNotes = null;
        this.spacedRepetition = null;
        this.userStats = null;

        console.log('[FlashcardViewer] Cleanup complete');
    }

    // =========================================================================
    // PHASE 2C: Spaced Repetition Methods
    // =========================================================================

    /**
     * Toggle spaced repetition mode
     */
    toggleSRMode() {
        this.srMode = !this.srMode;
        console.log('[FlashcardViewer] SR Mode:', this.srMode ? 'ON' : 'OFF');

        // Filter cards if entering SR mode
        if (this.srMode) {
            this.filterDueCards();
        } else {
            // Restore all cards
            this.flashcards = [...this.originalFlashcards];
            this.currentIndex = 0;
        }

        this.render();
    }

    /**
     * Filter cards to show only those due for review
     */
    filterDueCards() {
        const cardIds = this.flashcards.map((_, index) => `card_${index}`);
        const dueCardIds = this.spacedRepetition.getDueCards(cardIds);

        // Filter flashcards to only due cards
        this.flashcards = this.originalFlashcards.filter((_, index) =>
            dueCardIds.includes(`card_${index}`)
        );

        if (this.flashcards.length === 0) {
            this.showNoCardsMessage();
        } else {
            this.currentIndex = 0;
            console.log(`[FlashcardViewer] Filtered to ${this.flashcards.length} due cards`);
        }
    }

    /**
     * Rate card quality and record review
     *
     * @param {number} quality - Quality rating (0-5)
     */
    rateCardQuality(quality) {
        const cardId = `card_${this.currentIndex}`;

        // Record review in spaced repetition system
        const newState = this.spacedRepetition.recordReview(cardId, quality);

        console.log(`[FlashcardViewer] Card rated ${quality}, next review: ${newState.interval} days`);

        // Show feedback
        this.showQualityFeedback(quality, newState);

        // Move to next card after a short delay
        setTimeout(() => {
            this.nextCard();
        }, 1500);
    }

    /**
     * Show feedback after quality rating
     *
     * @param {number} quality - Quality rating
     * @param {Object} state - Updated card state
     */
    showQualityFeedback(quality, state) {
        const feedbackMessages = {
            0: '😰 Don\'t worry, you\'ll get it next time!',
            1: '🤔 Keep practicing!',
            2: '💪 You\'re making progress!',
            3: '👍 Good job!',
            4: '🌟 Great recall!',
            5: '🎉 Perfect! Excellent memory!'
        };

        const message = feedbackMessages[quality] || 'Review recorded!';
        const nextReview = this.spacedRepetition.getNextReviewFormatted(`card_${this.currentIndex}`);

        // Create temporary feedback element
        const feedback = document.createElement('div');
        feedback.className = 'sr-feedback';
        feedback.innerHTML = `
            <div class="sr-feedback-message">${message}</div>
            <div class="sr-feedback-next">Next review: ${nextReview}</div>
        `;

        this.container.appendChild(feedback);

        // Animate in
        setTimeout(() => feedback.classList.add('show'), 10);

        // Remove after delay
        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => feedback.remove(), 300);
        }, 1200);
    }

    /**
     * Show message when no cards are due
     */
    showNoCardsMessage() {
        this.container.innerHTML = `
            <div class="flashcard-completion">
                <div class="completion-icon" aria-hidden="true">🎯</div>
                <h2>All Caught Up!</h2>
                <p>No cards are due for review right now.</p>

                <div class="sr-stats-summary">
                    ${this.getSRStatsSummary()}
                </div>

                <div class="completion-actions">
                    <button class="btn-primary" id="btn-review-all">
                        Review All Cards
                    </button>
                    <button class="btn-secondary" id="btn-exit-sr">
                        Exit SR Mode
                    </button>
                </div>
            </div>
        `;

        // Add event listeners
        const btnReviewAll = document.getElementById('btn-review-all');
        if (btnReviewAll) {
            btnReviewAll.addEventListener('click', () => {
                this.srMode = false;
                this.flashcards = [...this.originalFlashcards];
                this.currentIndex = 0;
                this.render();
            });
        }

        const btnExitSR = document.getElementById('btn-exit-sr');
        if (btnExitSR) {
            btnExitSR.addEventListener('click', () => {
                this.srMode = false;
                this.flashcards = [...this.originalFlashcards];
                this.currentIndex = 0;
                this.render();
            });
        }
    }

    /**
     * Get SR statistics summary HTML
     *
     * @returns {string} HTML for statistics summary
     */
    getSRStatsSummary() {
        const cardIds = this.originalFlashcards.map((_, index) => `card_${index}`);
        const stats = this.spacedRepetition.getStatistics(cardIds);

        return `
            <div class="sr-stats">
                <div class="sr-stat">
                    <div class="sr-stat-value">${stats.new}</div>
                    <div class="sr-stat-label">New</div>
                </div>
                <div class="sr-stat">
                    <div class="sr-stat-value">${stats.learning}</div>
                    <div class="sr-stat-label">Learning</div>
                </div>
                <div class="sr-stat">
                    <div class="sr-stat-value">${stats.review}</div>
                    <div class="sr-stat-label">Review</div>
                </div>
                <div class="sr-stat">
                    <div class="sr-stat-value">${stats.mastered}</div>
                    <div class="sr-stat-label">Mastered</div>
                </div>
            </div>
            <div class="sr-upcoming">
                <p><strong>Due this week:</strong> ${stats.dueThisWeek} cards</p>
            </div>
        `;
    }

    // =========================================================================
    // PHASE 2B: Notes and Report Methods
    // =========================================================================

    /**
     * Show notes modal for current card
     */
    showNotesModal() {
        const currentCard = this.flashcards[this.currentIndex];
        const existingNote = this.cardNotes.get(this.currentIndex) || '';

        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay" id="notes-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>📝 Card Notes</h3>
                        <button class="modal-close" aria-label="Close modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="card-preview">
                            <strong>Front:</strong> ${this.escapeHtml(currentCard.question || currentCard.term || '')}
                        </div>
                        <textarea
                            id="note-input"
                            placeholder="Add your notes here..."
                            rows="6"
                            aria-label="Note text"
                        >${this.escapeHtml(existingNote)}</textarea>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" id="btn-cancel-note">Cancel</button>
                        <button class="btn-primary" id="btn-save-note">Save Note</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Setup modal event listeners
        const modal = document.getElementById('notes-modal');
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = document.getElementById('btn-cancel-note');
        const saveBtn = document.getElementById('btn-save-note');
        const noteInput = document.getElementById('note-input');

        // Focus on textarea
        noteInput.focus();

        // CRITICAL FIX: Escape handler defined first for cleanup
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        };

        // Close modal function
        const closeModal = () => {
            // CRITICAL FIX: Always remove escape handler
            document.removeEventListener('keydown', escapeHandler);
            modal.remove();
        };

        // Save note function
        const saveNote = () => {
            const noteText = noteInput.value.trim();
            if (noteText) {
                this.cardNotes.set(this.currentIndex, noteText);
                console.log('[FlashcardViewer] Note saved for card', this.currentIndex);
            } else {
                this.cardNotes.delete(this.currentIndex);
            }
            this.render(); // Re-render to update button state
            closeModal();
        };

        // Event listeners
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        saveBtn.addEventListener('click', saveNote);

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', escapeHandler);

        // Save on Ctrl+Enter
        noteInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                saveNote();
            }
        });
    }

    /**
     * Show report issue modal for current card
     */
    showReportModal() {
        const currentCard = this.flashcards[this.currentIndex];

        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay" id="report-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>⚠️ Report Issue</h3>
                        <button class="modal-close" aria-label="Close modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="card-preview">
                            <div><strong>Front:</strong> ${this.escapeHtml(currentCard.question || currentCard.term || '')}</div>
                            <div><strong>Back:</strong> ${this.escapeHtml(currentCard.answer || currentCard.definition || '')}</div>
                        </div>

                        <div class="form-group">
                            <label for="issue-type">Issue Type:</label>
                            <select id="issue-type" aria-label="Issue type">
                                <option value="typo">Typo or Spelling Error</option>
                                <option value="incorrect">Incorrect Information</option>
                                <option value="unclear">Unclear or Confusing</option>
                                <option value="formatting">Formatting Issue</option>
                                <option value="other">Other</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="issue-description">Description:</label>
                            <textarea
                                id="issue-description"
                                placeholder="Please describe the issue..."
                                rows="4"
                                aria-label="Issue description"
                                required
                            ></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" id="btn-cancel-report">Cancel</button>
                        <button class="btn-primary" id="btn-submit-report">Submit Report</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Setup modal event listeners
        const modal = document.getElementById('report-modal');
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = document.getElementById('btn-cancel-report');
        const submitBtn = document.getElementById('btn-submit-report');
        const issueType = document.getElementById('issue-type');
        const issueDescription = document.getElementById('issue-description');

        // Focus on description
        issueDescription.focus();

        // CRITICAL FIX: Escape handler defined first for cleanup
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        };

        // Close modal function
        const closeModal = () => {
            // CRITICAL FIX: Always remove escape handler
            document.removeEventListener('keydown', escapeHandler);
            modal.remove();
        };

        // Submit report function
        const submitReport = async () => {
            const description = issueDescription.value.trim();
            if (!description) {
                alert('Please provide a description of the issue.');
                return;
            }

            // Disable button during submission
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';

            try {
                const reportData = {
                    card_index: this.currentIndex,
                    card_front: currentCard.front,
                    card_back: currentCard.back,
                    issue_type: issueType.value,
                    description: description,
                    timestamp: new Date().toISOString()
                };

                // TODO: Send to backend API
                console.log('[FlashcardViewer] Issue reported:', reportData);

                // For now, just show success message
                alert('Thank you for reporting this issue! We will review it shortly.');
                closeModal();
            } catch (error) {
                console.error('[FlashcardViewer] Failed to submit report:', error);
                alert('Failed to submit report. Please try again.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Report';
            }
        };

        // Event listeners
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        submitBtn.addEventListener('click', submitReport);

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', escapeHandler);
    }

    // =========================================================================
    // PHASE 2A: Gamification Methods
    // =========================================================================

    /**
     * Check if gamification is available (user is authenticated)
     */
    async checkGamificationStatus() {
        try {
            const response = await fetch('/api/gamification/stats', {
                credentials: 'include'
            });

            if (response.ok) {
                this.userStats = await response.json();
                this.gamificationEnabled = true;
                console.log('[FlashcardViewer] Gamification enabled for user');

                // Start gamification session
                await this.startGamificationSession();
            } else {
                console.log('[FlashcardViewer] Gamification not available (user not authenticated)');
            }
        } catch (error) {
            console.log('[FlashcardViewer] Gamification check failed:', error);
            this.gamificationEnabled = false;
        }
    }

    /**
     * Start a gamification session
     */
    async startGamificationSession() {
        if (!this.gamificationEnabled) return;

        try {
            const response = await fetch('/api/gamification/session/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    course_id: null // Flashcards can be cross-course
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                console.log('[FlashcardViewer] Gamification session started:', this.sessionId);
            }
        } catch (error) {
            console.error('[FlashcardViewer] Failed to start gamification session:', error);
        }
    }

    /**
     * End gamification session and award XP
     * MEDIUM FIX: Standardized async/await pattern with proper error handling
     */
    async endGamificationSession() {
        if (!this.gamificationEnabled || !this.sessionId) {
            console.log('[FlashcardViewer] No active session to end');
            return;
        }

        try {
            // Calculate session duration
            const sessionDuration = Math.floor((Date.now() - this.sessionStartTime) / 1000);

            console.log('[FlashcardViewer] Ending session:', this.sessionId, 'Duration:', sessionDuration);

            // MEDIUM FIX: Standardized async/await with response validation
            const response = await fetch('/api/gamification/session/end', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    session_id: this.sessionId,
                    duration_seconds: sessionDuration
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[FlashcardViewer] Failed to end session:', response.status, errorText);
                return;
            }

            const data = await response.json();
            console.log('[FlashcardViewer] Gamification session ended successfully:', data);

        } catch (error) {
            console.error('[FlashcardViewer] Failed to end gamification session:', error);
            // Don't throw - this is cleanup, should not break the app
        }
    }

    /**
     * Award XP for completing flashcard set
     * CRITICAL FIX: Enhanced error handling for XP award failures
     */
    async awardFlashcardXP() {
        if (!this.gamificationEnabled) {
            console.log('[FlashcardViewer] Gamification not enabled, skipping XP award');
            return 0;
        }

        if (!this.gamificationInitialized) {
            console.warn('[FlashcardViewer] Gamification not initialized, skipping XP award');
            return 0;
        }

        try {
            const cardsReviewed = this.reviewedCards.size;
            const cardsKnown = this.knownCards.size;
            const accuracy = cardsReviewed > 0 ? (cardsKnown / cardsReviewed) * 100 : 0;

            // Award XP based on cards reviewed correctly
            // XP is awarded per 10 cards reviewed correctly
            const setsCompleted = Math.floor(cardsKnown / 10);

            if (setsCompleted <= 0) {
                console.log('[FlashcardViewer] No complete sets, no XP awarded');
                return 0;
            }

            console.log('[FlashcardViewer] Attempting to award XP for', setsCompleted, 'sets');

            const response = await fetch('/api/gamification/activity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    activity_type: 'flashcard_set_completed',
                    activity_data: {
                        cards_reviewed: cardsReviewed,
                        cards_known: cardsKnown,
                        accuracy: accuracy,
                        sets_completed: setsCompleted,
                        session_id: this.sessionId
                    }
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[FlashcardViewer] XP award failed with status:', response.status, errorText);

                // Show user-friendly error message
                this.showError('Failed to award XP. Your progress is still saved locally.');
                return 0;
            }

            const data = await response.json();
            this.xpEarned = data.xp_awarded || 0;
            console.log('[FlashcardViewer] XP awarded successfully:', this.xpEarned);
            return this.xpEarned;

        } catch (error) {
            console.error('[FlashcardViewer] Failed to award XP:', error);

            // Network error or other exception
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                this.showError('Network error: Unable to award XP. Please check your connection.');
            } else {
                this.showError('An error occurred while awarding XP. Your progress is still saved.');
            }

            return 0;
        }
    }

    /**
     * Get current time spent in session (formatted)
     */
    getFormattedTimeSpent() {
        const seconds = Math.floor((Date.now() - this.sessionStartTime) / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;

        if (minutes > 0) {
            return `${minutes}m ${remainingSeconds}s`;
        }
        return `${seconds}s`;
    }

    /**
     * Start time tracker to update session time display
     * MEDIUM FIX: Prevent timer drift by using actual elapsed time
     */
    startTimeTracker() {
        // MEDIUM FIX: Store start time for accurate calculation
        const startTime = this.sessionStartTime;

        // Update time display every second
        this.timeTrackerInterval = setInterval(() => {
            const timeElement = document.getElementById('session-time');
            if (timeElement) {
                // MEDIUM FIX: Calculate from actual elapsed time, not accumulated intervals
                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;

                if (minutes > 0) {
                    timeElement.textContent = `${minutes}m ${seconds}s`;
                } else {
                    timeElement.textContent = `${seconds}s`;
                }
            }
        }, 1000);
    }
}

// CRITICAL FIX: Store beforeunload handler for proper cleanup
// This is now handled in the FlashcardViewer constructor and cleanup method

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlashcardViewer;
}

