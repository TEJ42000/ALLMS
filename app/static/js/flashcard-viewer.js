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
        this.container = document.getElementById(containerId);
        this.flashcards = flashcards;
        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards = new Set();
        this.knownCards = new Set();
        this.starredCards = new Set();
        
        // Event listeners for cleanup
        this.eventListeners = [];
        
        if (this.container && this.flashcards.length > 0) {
            this.init();
        }
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
     */
    render() {
        const currentCard = this.flashcards[this.currentIndex];
        const progress = ((this.currentIndex + 1) / this.flashcards.length) * 100;
        
        this.container.innerHTML = `
            <div class="flashcard-viewer">
                <!-- Progress Bar -->
                <div class="flashcard-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">
                        Card ${this.currentIndex + 1} of ${this.flashcards.length}
                    </div>
                </div>

                <!-- Flashcard Container -->
                <div class="flashcard-container">
                    <div class="flashcard ${this.isFlipped ? 'flipped' : ''}" id="flashcard">
                        <div class="flashcard-inner">
                            <!-- Front of Card -->
                            <div class="flashcard-front">
                                <div class="card-label">Question</div>
                                <div class="card-content">
                                    ${this.escapeHtml(currentCard.question || currentCard.term || '')}
                                </div>
                                <div class="card-hint">Click to flip</div>
                            </div>
                            
                            <!-- Back of Card -->
                            <div class="flashcard-back">
                                <div class="card-label">Answer</div>
                                <div class="card-content">
                                    ${this.escapeHtml(currentCard.answer || currentCard.definition || '')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Navigation Controls -->
                <div class="flashcard-controls">
                    <button class="btn-control" id="btn-previous" ${this.currentIndex === 0 ? 'disabled' : ''}>
                        <span class="icon">←</span>
                        <span class="label">Previous</span>
                    </button>
                    
                    <button class="btn-control btn-flip" id="btn-flip">
                        <span class="icon">↻</span>
                        <span class="label">Flip</span>
                    </button>
                    
                    <button class="btn-control" id="btn-next" ${this.currentIndex === this.flashcards.length - 1 ? 'disabled' : ''}>
                        <span class="label">Next</span>
                        <span class="icon">→</span>
                    </button>
                </div>

                <!-- Card Actions -->
                <div class="flashcard-actions">
                    <button class="btn-action ${this.starredCards.has(this.currentIndex) ? 'active' : ''}" id="btn-star" title="Star this card">
                        <span class="icon">⭐</span>
                        <span class="label">Star</span>
                    </button>
                    
                    <button class="btn-action ${this.knownCards.has(this.currentIndex) ? 'active' : ''}" id="btn-know" title="Mark as known">
                        <span class="icon">✓</span>
                        <span class="label">Know</span>
                    </button>
                    
                    <button class="btn-action" id="btn-shuffle" title="Shuffle cards">
                        <span class="icon">🔀</span>
                        <span class="label">Shuffle</span>
                    </button>
                    
                    <button class="btn-action" id="btn-restart" title="Restart from beginning">
                        <span class="icon">↺</span>
                        <span class="label">Restart</span>
                    </button>
                </div>

                <!-- Study Stats -->
                <div class="flashcard-stats">
                    <div class="stat">
                        <span class="stat-label">Reviewed:</span>
                        <span class="stat-value">${this.reviewedCards.size}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Known:</span>
                        <span class="stat-value">${this.knownCards.size}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Starred:</span>
                        <span class="stat-value">${this.starredCards.size}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Remaining:</span>
                        <span class="stat-value">${this.flashcards.length - this.reviewedCards.size}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Setup event listeners for controls
     */
    setupEventListeners() {
        // Flip card on click
        const flashcard = document.getElementById('flashcard');
        if (flashcard) {
            const flipHandler = () => this.flipCard();
            flashcard.addEventListener('click', flipHandler);
            this.eventListeners.push({ element: flashcard, event: 'click', handler: flipHandler });
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
     */
    setupKeyboardShortcuts() {
        const keyHandler = (e) => {
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

        document.addEventListener('keydown', keyHandler);
        this.eventListeners.push({ element: document, event: 'keydown', handler: keyHandler });
    }

    /**
     * Setup touch gestures for mobile
     */
    setupTouchGestures() {
        const flashcard = document.getElementById('flashcard');
        if (!flashcard) return;

        let touchStartX = 0;
        let touchEndX = 0;

        const touchStartHandler = (e) => {
            touchStartX = e.changedTouches[0].screenX;
        };

        const touchEndHandler = (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe();
        };

        flashcard.addEventListener('touchstart', touchStartHandler);
        flashcard.addEventListener('touchend', touchEndHandler);

        this.eventListeners.push({ element: flashcard, event: 'touchstart', handler: touchStartHandler });
        this.eventListeners.push({ element: flashcard, event: 'touchend', handler: touchEndHandler });

        this.touchStartX = 0;
        this.touchEndX = 0;
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
     */
    shuffleCards() {
        // Fisher-Yates shuffle
        for (let i = this.flashcards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.flashcards[i], this.flashcards[j]] = [this.flashcards[j], this.flashcards[i]];
        }

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
     */
    showCompletionMessage() {
        const accuracy = this.knownCards.size / this.flashcards.length * 100;

        this.container.innerHTML = `
            <div class="flashcard-completion">
                <div class="completion-icon">🎉</div>
                <h2>Great Job!</h2>
                <p>You've completed all ${this.flashcards.length} flashcards!</p>

                <div class="completion-stats">
                    <div class="stat-large">
                        <div class="stat-value">${this.reviewedCards.size}</div>
                        <div class="stat-label">Cards Reviewed</div>
                    </div>
                    <div class="stat-large">
                        <div class="stat-value">${this.knownCards.size}</div>
                        <div class="stat-label">Marked as Known</div>
                    </div>
                    <div class="stat-large">
                        <div class="stat-value">${Math.round(accuracy)}%</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                </div>

                <div class="completion-actions">
                    <button class="btn-primary" id="btn-restart-completion">
                        Study Again
                    </button>
                    <button class="btn-secondary" id="btn-review-starred">
                        Review Starred (${this.starredCards.size})
                    </button>
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
    }

    /**
     * Review only starred cards
     */
    reviewStarredCards() {
        if (this.starredCards.size === 0) {
            alert('No starred cards to review!');
            return;
        }

        // Filter to only starred cards
        const starredIndices = Array.from(this.starredCards);
        this.flashcards = starredIndices.map(index => this.flashcards[index]);

        this.currentIndex = 0;
        this.isFlipped = false;
        this.reviewedCards.clear();
        this.knownCards.clear();
        this.starredCards.clear();

        this.render();
        this.setupEventListeners();
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
     */
    cleanup() {
        console.log('[FlashcardViewer] Cleaning up event listeners...');
        this.eventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.eventListeners = [];
    }
}

// Auto-cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.flashcardViewer && typeof window.flashcardViewer.cleanup === 'function') {
        window.flashcardViewer.cleanup();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlashcardViewer;
}

