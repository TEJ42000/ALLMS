/**
 * Flashcard Page Controller
 *
 * Manages the flashcard sets page, including:
 * - Loading and displaying flashcard sets
 * - Starting flashcard study sessions
 * - Navigation between sets and viewer
 *
 * HIGH FIX: Moved from inline script for CSP compliance
 * Issue #167: Encapsulated module-level variables using IIFE pattern
 */

// Issue #167: Encapsulate module-level variables using IIFE
const FlashcardPage = (() => {
    // Private module state (not accessible from global scope)
    let flashcardViewer = null;
    let setsClickHandler = null;
    let flashcardSets = [];

    /**
     * Get the current flashcard viewer instance
     * Issue #167: Expose getter for external access (e.g., window.flashcardViewer)
     * @returns {FlashcardViewer|null} The current viewer or null
     */
    function getViewer() {
        return flashcardViewer;
    }

    /**
     * Set the flashcard viewer instance
     * Issue #167: Expose setter for external access
     * @param {FlashcardViewer|null} viewer - The viewer to set
     */
    function setViewer(viewer) {
        flashcardViewer = viewer;
    }

    /**
     * Get the flashcard sets
     * Issue #167: Expose getter for testing
     * @returns {Array} The flashcard sets
     */
    function getSets() {
        return flashcardSets;
    }

    /**
     * Initialize the flashcard page
     */
    async function init() {
        await loadFlashcardData();
        loadFlashcardSets();
        setupBackButton();
    }

    /**
     * Cleanup resources (for SPA navigation)
     * Issue #167: Proper cleanup for encapsulated state
     */
    function cleanup() {
        if (flashcardViewer) {
            flashcardViewer.cleanup();
            flashcardViewer = null;
        }
        if (setsClickHandler) {
            const setsContainer = document.querySelector('.sets-grid');
            if (setsContainer) {
                setsContainer.removeEventListener('click', setsClickHandler);
            }
            setsClickHandler = null;
        }
        flashcardSets = [];
    }

    /**
     * Validate flashcard set schema
     * HIGH FIX: Comprehensive JSON schema validation
     * @param {object} set - The flashcard set to validate
     * @param {number} index - The index of the set (for logging)
     * @returns {boolean} - True if valid, false otherwise
     */
    function validateFlashcardSet(set, index) {
        // Check if set is an object
        if (!set || typeof set !== 'object') {
            console.warn(`[FlashcardPage] Invalid set at index ${index}: not an object`);
            return false;
        }

        // Required fields
        if (typeof set.id !== 'number' || set.id <= 0) {
            console.warn(`[FlashcardPage] Invalid set at index ${index}: id must be positive number`);
            return false;
        }

        if (typeof set.title !== 'string' || set.title.trim().length === 0) {
            console.warn(`[FlashcardPage] Invalid set at index ${index}: title must be non-empty string`);
            return false;
        }

        if (!Array.isArray(set.cards)) {
            console.warn(`[FlashcardPage] Invalid set at index ${index}: cards must be array`);
            return false;
        }

        if (set.cards.length === 0) {
            console.warn(`[FlashcardPage] Empty set at index ${index}: ${set.title}`);
            return false;
        }

        // Validate each card
        // Issue #166: Use optional chaining for defensive property access
        const validCards = set?.cards?.every((card, cardIndex) => {
            if (!card || typeof card !== 'object') {
                console.warn(`[FlashcardPage] Invalid card at set ${index}, card ${cardIndex}`);
                return false;
            }

            // Card must have either question/answer OR term/definition
            // Issue #166: Use optional chaining with safe trim access
            const hasQuestionAnswer =
                typeof card?.question === 'string' && card?.question?.trim()?.length > 0 &&
                typeof card?.answer === 'string' && card?.answer?.trim()?.length > 0;

            const hasTermDefinition =
                typeof card?.term === 'string' && card?.term?.trim()?.length > 0 &&
                typeof card?.definition === 'string' && card?.definition?.trim()?.length > 0;

            if (!hasQuestionAnswer && !hasTermDefinition) {
                console.warn(`[FlashcardPage] Invalid card at set ${index}, card ${cardIndex}: missing content`);
                    return false;
            }

            return true;
        }) ?? false;

        return validCards;
    }

    /**
     * Load flashcard data from JSON file
     * MEDIUM FIX: Separate data from code
     * HIGH FIX: Comprehensive JSON schema validation
     */
    async function loadFlashcardData() {
        try {
            const response = await fetch('/static/data/flashcard-sets.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // HIGH FIX: Validate JSON structure
            if (!Array.isArray(data)) {
                throw new Error('Invalid data format: expected array');
            }

            // HIGH FIX: Validate each flashcard set with comprehensive schema validation
            const validSets = data.filter((set, index) => validateFlashcardSet(set, index));

            if (validSets.length === 0) {
                throw new Error('No valid flashcard sets found');
            }

            flashcardSets = validSets;
            console.log('[FlashcardPage] Loaded', flashcardSets.length, 'flashcard sets');
        } catch (error) {
            console.error('[FlashcardPage] Error loading flashcard data:', error);
            showError('Failed to load flashcard sets. Please refresh the page.');
        }
    }

    /**
     * Load and display flashcard sets
     */
    function loadFlashcardSets() {
        const setsContainer = document.querySelector('.sets-grid');

        if (!setsContainer) {
            console.error('[FlashcardPage] Sets container not found');
            return;
        }

        if (flashcardSets.length === 0) {
            setsContainer.innerHTML = '<p class="no-sets">No flashcard sets available yet.</p>';
            return;
        }

        // Issue #166: Use optional chaining for defensive property access
        setsContainer.innerHTML = flashcardSets.map(set => `
            <div class="flashcard-set-card" data-set-id="${set?.id}">
                <div class="set-icon" aria-hidden="true">📚</div>
                <h3>${escapeHtml(set?.title ?? '')}</h3>
                <p>${escapeHtml(set?.description ?? '')}</p>
                <div class="set-meta">
                    <span class="card-count">${set?.cards?.length ?? 0} cards</span>
                </div>
                <button class="btn-study" data-set-id="${set?.id}" aria-label="Start studying ${escapeHtml(set?.title ?? '')}">
                    Start Studying
                </button>
                </div>
        `).join('');

        // MEDIUM FIX: Remove old event listener before adding new one
        if (setsClickHandler) {
            setsContainer.removeEventListener('click', setsClickHandler);
        }

        // HIGH FIX: Use event delegation instead of inline onclick
        setsClickHandler = function(e) {
            if (e.target.classList.contains('btn-study')) {
                const setId = parseInt(e.target.getAttribute('data-set-id'));

                // MEDIUM FIX: Validate setId is a valid number
                if (isNaN(setId) || setId <= 0) {
                    console.error('[FlashcardPage] Invalid set ID:', setId);
                    showError('Invalid flashcard set. Please try again.');
                    return;
                }

                startFlashcards(setId);
            }
        };
        setsContainer.addEventListener('click', setsClickHandler);
    }

    /**
     * Start studying a flashcard set
     */
    function startFlashcards(setId) {
        const set = flashcardSets.find(s => s.id === setId);
        if (!set) {
            console.error('[FlashcardPage] Flashcard set not found:', setId);
            return;
        }

        // Hide sets, show viewer
        const setsElement = document.getElementById('flashcard-sets');
        const viewerContainer = document.getElementById('flashcard-viewer-container');
        const setTitle = document.getElementById('set-title');

        if (!setsElement || !viewerContainer || !setTitle) {
            console.error('[FlashcardPage] Required elements not found');
            return;
        }

        setsElement.style.display = 'none';
        viewerContainer.style.display = 'block';
        setTitle.textContent = set.title;

        // Initialize flashcard viewer
        if (flashcardViewer) {
            flashcardViewer.cleanup();
        }

        try {
            flashcardViewer = new FlashcardViewer('flashcard-viewer', set.cards);
            window.flashcardViewer = flashcardViewer;
        } catch (error) {
            console.error('[FlashcardPage] Error initializing flashcard viewer:', error);
            showError('Failed to start flashcard viewer. Please try again.');
        }
    }

    /**
     * Setup back button
     */
    function setupBackButton() {
        const btnBack = document.getElementById('btn-back-to-sets');
        if (!btnBack) {
            console.warn('[FlashcardPage] Back button not found');
            return;
        }

        btnBack.addEventListener('click', function() {
            // Cleanup viewer
            if (flashcardViewer) {
                flashcardViewer.cleanup();
                flashcardViewer = null;
            }

            // Show sets, hide viewer
            const setsElement = document.getElementById('flashcard-sets');
            const viewerContainer = document.getElementById('flashcard-viewer-container');

            if (setsElement && viewerContainer) {
                setsElement.style.display = 'block';
                viewerContainer.style.display = 'none';
            }
        });
    }

    /**
     * MEDIUM FIX: escapeHtml() is now in utils.js (shared across files)
     */

    /**
     * Show error message with better UI
     * MEDIUM FIX: Replace generic alert with styled error message
     * CRITICAL FIX: Prevent memory leak in ESC handler
     */
    function showError(message) {
        // Create error overlay
        const overlay = document.createElement('div');
        overlay.className = 'error-overlay';
        overlay.innerHTML = `
            <div class="error-dialog" role="alertdialog" aria-labelledby="error-title" aria-describedby="error-message">
                <div class="error-icon" aria-hidden="true">⚠️</div>
                <h2 id="error-title">Error</h2>
                <p id="error-message">${escapeHtml(message)}</p>
                <button class="btn-primary" id="btn-close-error" autofocus>OK</button>
            </div>
        `;

        document.body.appendChild(overlay);

        // CRITICAL FIX: Shared cleanup function to prevent memory leak
        const closeDialog = () => {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            // CRITICAL FIX: Always remove ESC handler
            document.removeEventListener('keydown', escHandler);
        };

        // Close on button click
        const btnClose = document.getElementById('btn-close-error');
        if (btnClose) {
            btnClose.addEventListener('click', closeDialog);
            btnClose.focus();
        }

        // Close on ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                closeDialog();
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    // Issue #167: Return public API
    return {
        init,
        cleanup,
        getViewer,
        setViewer,
        getSets
    };
})();

// Issue #167: Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    FlashcardPage.init();
});
