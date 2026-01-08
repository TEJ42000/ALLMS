/**
 * Spaced Repetition Service
 * Implements the SM-2 (SuperMemo 2) algorithm for optimal flashcard review scheduling
 * 
 * Phase 2C: Spaced Repetition Implementation
 * Issue: #158
 */

class SpacedRepetitionService {
    constructor() {
        // SM-2 algorithm constants
        this.MIN_EASINESS_FACTOR = 1.3;
        this.DEFAULT_EASINESS_FACTOR = 2.5;
        
        // Storage key for card data
        this.STORAGE_KEY = 'flashcard_sr_data';
        
        // Load existing data
        this.cardData = this.loadCardData();
    }

    /**
     * Calculate next review date using SM-2 algorithm
     * 
     * @param {number} quality - Quality of recall (0-5)
     *   5 - Perfect response
     *   4 - Correct response after hesitation
     *   3 - Correct response with difficulty
     *   2 - Incorrect response; correct answer seemed easy to recall
     *   1 - Incorrect response; correct answer seemed familiar
     *   0 - Complete blackout
     * 
     * @param {Object} cardState - Current state of the card
     * @returns {Object} Updated card state with next review date
     */
    calculateNextReview(quality, cardState = null) {
        // Initialize card state if not provided
        if (!cardState) {
            cardState = {
                easinessFactor: this.DEFAULT_EASINESS_FACTOR,
                interval: 0,
                repetitions: 0,
                lastReviewed: null,
                nextReview: new Date()
            };
        }

        // Clone the state to avoid mutations
        const newState = { ...cardState };

        // Update easiness factor based on quality
        // EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        const qualityFactor = 5 - quality;
        newState.easinessFactor = Math.max(
            this.MIN_EASINESS_FACTOR,
            newState.easinessFactor + (0.1 - qualityFactor * (0.08 + qualityFactor * 0.02))
        );

        // If quality < 3, reset repetitions and interval
        if (quality < 3) {
            newState.repetitions = 0;
            newState.interval = 0;
        } else {
            // Increment repetitions
            newState.repetitions += 1;

            // Calculate new interval
            if (newState.repetitions === 1) {
                newState.interval = 1; // 1 day
            } else if (newState.repetitions === 2) {
                newState.interval = 6; // 6 days
            } else {
                // interval(n) = interval(n-1) * EF
                newState.interval = Math.round(newState.interval * newState.easinessFactor);
            }
        }

        // Calculate next review date
        const now = new Date();
        newState.lastReviewed = now.toISOString();
        
        const nextReviewDate = new Date(now);
        nextReviewDate.setDate(nextReviewDate.getDate() + newState.interval);
        newState.nextReview = nextReviewDate.toISOString();

        return newState;
    }

    /**
     * Record a card review
     * 
     * @param {string} cardId - Unique identifier for the card
     * @param {number} quality - Quality of recall (0-5)
     * @returns {Object} Updated card state
     */
    recordReview(cardId, quality) {
        // Get current card state
        const currentState = this.cardData[cardId] || null;

        // Calculate next review
        const newState = this.calculateNextReview(quality, currentState);

        // Store updated state
        this.cardData[cardId] = newState;
        this.saveCardData();

        console.log(`[SpacedRepetition] Card ${cardId} reviewed with quality ${quality}`);
        console.log(`[SpacedRepetition] Next review in ${newState.interval} days`);

        return newState;
    }

    /**
     * Get card state
     * 
     * @param {string} cardId - Unique identifier for the card
     * @returns {Object|null} Card state or null if not found
     */
    getCardState(cardId) {
        return this.cardData[cardId] || null;
    }

    /**
     * Check if a card is due for review
     * 
     * @param {string} cardId - Unique identifier for the card
     * @returns {boolean} True if card is due for review
     */
    isCardDue(cardId) {
        const state = this.getCardState(cardId);
        
        if (!state || !state.nextReview) {
            return true; // New cards are always due
        }

        const nextReview = new Date(state.nextReview);
        const now = new Date();

        return now >= nextReview;
    }

    /**
     * Get all cards due for review
     * 
     * @param {Array} cardIds - Array of card identifiers
     * @returns {Array} Array of card IDs that are due for review
     */
    getDueCards(cardIds) {
        return cardIds.filter(cardId => this.isCardDue(cardId));
    }

    /**
     * Get cards due today
     * 
     * @param {Array} cardIds - Array of card identifiers
     * @returns {Array} Array of card IDs due today
     */
    getCardsForToday(cardIds) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        return cardIds.filter(cardId => {
            const state = this.getCardState(cardId);
            
            if (!state || !state.nextReview) {
                return true; // New cards count as due today
            }

            const nextReview = new Date(state.nextReview);
            return nextReview >= today && nextReview < tomorrow;
        });
    }

    /**
     * Get review statistics
     * 
     * @param {Array} cardIds - Array of card identifiers
     * @returns {Object} Statistics about card reviews
     */
    getStatistics(cardIds) {
        const stats = {
            total: cardIds.length,
            new: 0,
            learning: 0,
            review: 0,
            mastered: 0,
            dueToday: 0,
            dueThisWeek: 0
        };

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const weekFromNow = new Date(today);
        weekFromNow.setDate(weekFromNow.getDate() + 7);

        cardIds.forEach(cardId => {
            const state = this.getCardState(cardId);

            if (!state) {
                stats.new++;
                stats.dueToday++;
            } else {
                const nextReview = new Date(state.nextReview);

                // Categorize by repetitions
                if (state.repetitions === 0) {
                    stats.learning++;
                } else if (state.repetitions < 5) {
                    stats.review++;
                } else {
                    stats.mastered++;
                }

                // Check if due
                if (nextReview <= today) {
                    stats.dueToday++;
                } else if (nextReview <= weekFromNow) {
                    stats.dueThisWeek++;
                }
            }
        });

        return stats;
    }

    /**
     * Get formatted next review date
     * 
     * @param {string} cardId - Unique identifier for the card
     * @returns {string} Formatted next review date
     */
    getNextReviewFormatted(cardId) {
        const state = this.getCardState(cardId);
        
        if (!state || !state.nextReview) {
            return 'Not reviewed yet';
        }

        const nextReview = new Date(state.nextReview);
        const now = new Date();
        
        const diffTime = nextReview - now;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 0) {
            return 'Overdue';
        } else if (diffDays === 0) {
            return 'Today';
        } else if (diffDays === 1) {
            return 'Tomorrow';
        } else if (diffDays < 7) {
            return `In ${diffDays} days`;
        } else if (diffDays < 30) {
            const weeks = Math.floor(diffDays / 7);
            return `In ${weeks} week${weeks > 1 ? 's' : ''}`;
        } else {
            const months = Math.floor(diffDays / 30);
            return `In ${months} month${months > 1 ? 's' : ''}`;
        }
    }

    /**
     * Load card data from localStorage
     * 
     * @returns {Object} Card data
     */
    loadCardData() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        } catch (error) {
            console.error('[SpacedRepetition] Failed to load card data:', error);
            return {};
        }
    }

    /**
     * Save card data to localStorage
     */
    saveCardData() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.cardData));
        } catch (error) {
            console.error('[SpacedRepetition] Failed to save card data:', error);
        }
    }

    /**
     * Reset card data (for testing or clearing progress)
     * 
     * @param {string} cardId - Optional card ID to reset (resets all if not provided)
     */
    resetCardData(cardId = null) {
        if (cardId) {
            delete this.cardData[cardId];
        } else {
            this.cardData = {};
        }
        this.saveCardData();
    }

    /**
     * Export card data (for backup or migration)
     * 
     * @returns {string} JSON string of card data
     */
    exportData() {
        return JSON.stringify(this.cardData, null, 2);
    }

    /**
     * Import card data (for restore or migration)
     * 
     * @param {string} jsonData - JSON string of card data
     * @returns {boolean} Success status
     */
    importData(jsonData) {
        try {
            const data = JSON.parse(jsonData);
            this.cardData = data;
            this.saveCardData();
            return true;
        } catch (error) {
            console.error('[SpacedRepetition] Failed to import data:', error);
            return false;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpacedRepetitionService;
}

