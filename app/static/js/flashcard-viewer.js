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

        // Filter out invalid cards
        this.flashcards = flashcards.filter(card => {
            if (!card || typeof card !== 'object') {
                console.warn('[FlashcardViewer] Skipping invalid card:', card);
                return false;
            }

            // Card must have either question/answer OR term/definition
            const hasQuestionAnswer = card.question && card.answer;
            const hasTermDefinition = card.term && card.definition;

            if (!hasQuestionAnswer && !hasTermDefinition) {
                console.warn('[FlashcardViewer] Skipping card without valid content:', card);
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

        // Store original flashcards for restoration after filtering
        this.originalFlashcards = [...this.flashcards];

        // Event listeners for cleanup
        this.eventListeners = [];

        // CRITICAL FIX: Store beforeunload handler as instance property
        this.beforeUnloadHandler = () => {
            this.cleanup();
        };
        window.addEventListener('beforeunload', this.beforeUnloadHandler);

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
                </div>

                <!-- Study Stats -->
                <div class="flashcard-stats">
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
     */
    setupEventListeners() {
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
     */
    handleSwipe() {
        const swipeThreshold = 50;
        const diff = this.touchStartX - this.touchEndX;

        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                // Swipe left - next card
                this.nextCard();
            } else {
                // Swipe right - previous card
                this.previousCard();
            }
        }
    }

    /**
     * Flip the current card
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
        }
    }

    /**
     * Navigate to previous card
     */
    previousCard() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.isFlipped = false;
            this.render();
            this.setupEventListeners();
        }
    }

    /**
     * Navigate to next card
     */
    nextCard() {
        if (this.currentIndex < this.flashcards.length - 1) {
            this.currentIndex++;
            this.isFlipped = false;
            this.render();
            this.setupEventListeners();
        } else {
            // Completed all cards
            this.showCompletionMessage();
        }
    }

    /**
     * Toggle star on current card
     */
    toggleStar() {
        if (this.starredCards.has(this.currentIndex)) {
            this.starredCards.delete(this.currentIndex);
        } else {
            this.starredCards.add(this.currentIndex);
        }
        this.render();
        this.setupEventListeners();
    }

    /**
     * Toggle known status on current card
     */
    toggleKnown() {
        if (this.knownCards.has(this.currentIndex)) {
            this.knownCards.delete(this.currentIndex);
        } else {
            this.knownCards.add(this.currentIndex);
        }
        this.render();
        this.setupEventListeners();
    }

    /**
     * Shuffle the flashcards
     * HIGH FIX: Clear tracking sets since indices will be invalid after shuffle
     */
    shuffleCards() {
        // HIGH FIX: Warn user that progress will be reset
        if (this.reviewedCards.size > 0 || this.knownCards.size > 0 || this.starredCards.size > 0) {
            const confirmed = confirm(
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
        this.render();
        this.setupEventListeners();
    }

    /**
     * Restart from the beginning
     */
    restart() {
        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards.clear();
        this.knownCards.clear();
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
     */
    reviewStarredCards() {
        if (this.starredCards.size === 0) {
            alert('No starred cards to review!');
            return;
        }

        // HIGH FIX: Store original flashcards if not already stored
        if (!this.isFilteredView) {
            this.originalFlashcards = [...this.flashcards];
            this.originalReviewedCards = new Set(this.reviewedCards);
            this.originalKnownCards = new Set(this.knownCards);
            this.originalStarredCards = new Set(this.starredCards);
        }

        // Filter to only starred cards
        const starredIndices = Array.from(this.starredCards);
        this.flashcards = starredIndices.map(index => this.originalFlashcards[index]);

        this.isFilteredView = true;
        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards.clear();
        this.knownCards.clear();
        this.starredCards.clear();

        this.render();
        this.setupEventListeners();
    }

    /**
     * Restore full deck from filtered view
     * HIGH FIX: Allow users to return to full deck
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
     */
    showError(message) {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="flashcard-error" role="alert">
                <div class="error-icon" aria-hidden="true">⚠️</div>
                <h2>Oops! Something went wrong</h2>
                <p>${this.escapeHtml(message)}</p>
                <button class="btn-primary" onclick="location.reload()">
                    Reload Page
                </button>
            </div>
        `;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Cleanup event listeners
     * CRITICAL FIX: Also remove beforeunload handler
     */
    cleanup() {
        console.log('[FlashcardViewer] Cleaning up event listeners...');
        this.eventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.eventListeners = [];

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

