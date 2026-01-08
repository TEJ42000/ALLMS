/**
 * Flashcard Page Controller
 * 
 * Manages the flashcard sets page, including:
 * - Loading and displaying flashcard sets
 * - Starting flashcard study sessions
 * - Navigation between sets and viewer
 * 
 * HIGH FIX: Moved from inline script for CSP compliance
 */

// Flashcard data and initialization
let flashcardViewer = null;

// MEDIUM FIX: Track event listeners for cleanup
let setsClickHandler = null;

// MEDIUM FIX: Load flashcard sets from JSON file instead of hardcoding
let flashcardSets = [];

// Load flashcard sets on page load
document.addEventListener('DOMContentLoaded', async function() {
    await loadFlashcardData();
    loadFlashcardSets();
    setupBackButton();
});

/**
 * Load flashcard data from JSON file
 * MEDIUM FIX: Separate data from code
 */
async function loadFlashcardData() {
    try {
        const response = await fetch('/static/data/flashcard-sets.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        flashcardSets = await response.json();
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

    setsContainer.innerHTML = flashcardSets.map(set => `
        <div class="flashcard-set-card" data-set-id="${set.id}">
            <div class="set-icon" aria-hidden="true">📚</div>
            <h3>${escapeHtml(set.title)}</h3>
            <p>${escapeHtml(set.description)}</p>
            <div class="set-meta">
                <span class="card-count">${set.cardCount} cards</span>
            </div>
            <button class="btn-study" data-set-id="${set.id}" aria-label="Start studying ${escapeHtml(set.title)}">
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
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error message with better UI
 * MEDIUM FIX: Replace generic alert with styled error message
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

    // Close on button click
    const btnClose = document.getElementById('btn-close-error');
    if (btnClose) {
        btnClose.addEventListener('click', () => {
            document.body.removeChild(overlay);
        });
        btnClose.focus();
    }

    // Close on ESC key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            document.body.removeChild(overlay);
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

