/**
 * Quiz Accessibility Features - Phase 5
 * 
 * Implements:
 * - Enhanced keyboard navigation (arrow keys, Enter, Space, Escape)
 * - Screen reader announcements (live regions)
 * - Focus management (trap, restore, visible indicators)
 * - Skip links for quick navigation
 * 
 * Security: All DOM manipulation uses safe methods
 * Accessibility: WCAG 2.1 AA compliant
 */

/**
 * Initialize keyboard navigation for quiz
 * @param {HTMLElement} container - Quiz container element
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Callback when navigation occurs
 * @returns {Function} - Cleanup function to remove event listener
 */
function initializeKeyboardNavigation(container, quizState, onNavigate) {
    // Input validation
    if (!container || !(container instanceof HTMLElement)) {
        console.error('initializeKeyboardNavigation: container must be an HTMLElement');
        return () => {};
    }

    if (!quizState || typeof quizState !== 'object') {
        console.error('initializeKeyboardNavigation: quizState must be an object');
        return () => {};
    }

    // Create handler function
    const handler = (event) => {
        handleQuizKeydown(event, quizState, onNavigate);
    };

    // Add keyboard event listener
    container.addEventListener('keydown', handler);

    // Return cleanup function
    return () => {
        container.removeEventListener('keydown', handler);
    };
}

/**
 * Handle keyboard events for quiz navigation
 * @param {KeyboardEvent} event - Keyboard event
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Navigation callback
 */
function handleQuizKeydown(event, quizState, onNavigate) {
    const key = event.key;
    
    // Arrow key navigation for options
    if (key === 'ArrowUp' || key === 'ArrowDown') {
        event.preventDefault();
        navigateOptions(key === 'ArrowDown' ? 1 : -1);
    }
    
    // Arrow key navigation for questions
    if (key === 'ArrowLeft' || key === 'ArrowRight') {
        const currentIndex = quizState.currentQuestionIndex;
        const totalQuestions = quizState.questions.length;
        
        if (key === 'ArrowLeft' && currentIndex > 0) {
            event.preventDefault();
            if (onNavigate) onNavigate(currentIndex - 1);
        } else if (key === 'ArrowRight' && currentIndex < totalQuestions - 1) {
            event.preventDefault();
            if (onNavigate) onNavigate(currentIndex + 1);
        }
    }
    
    // Escape to close modals
    if (key === 'Escape') {
        closeActiveModal();
    }
}

/**
 * Navigate between answer options using arrow keys
 * @param {number} direction - Direction to navigate (1 for down, -1 for up)
 */
function navigateOptions(direction) {
    const options = Array.from(document.querySelectorAll('.quiz-option-enhanced'));
    if (options.length === 0) return;
    
    const currentFocus = document.activeElement;
    const currentIndex = options.indexOf(currentFocus);
    
    let nextIndex;
    if (currentIndex === -1) {
        // No option focused, focus first
        nextIndex = 0;
    } else {
        // Navigate to next/previous option
        nextIndex = currentIndex + direction;
        if (nextIndex < 0) nextIndex = options.length - 1;
        if (nextIndex >= options.length) nextIndex = 0;
    }
    
    options[nextIndex].focus();
}

/**
 * Close active modal (if any)
 */
function closeActiveModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
        announceToScreenReader('Dialog closed');
    }
}

/**
 * Create screen reader announcement region
 * @returns {HTMLElement} - Live region element
 */
function createScreenReaderRegion() {
    const existing = document.getElementById('quiz-sr-announcements');
    if (existing) return existing;
    
    const region = document.createElement('div');
    region.id = 'quiz-sr-announcements';
    region.className = 'sr-only';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'true');
    
    document.body.appendChild(region);
    return region;
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 * @param {string} priority - Priority level ('polite' or 'assertive')
 */
function announceToScreenReader(message, priority = 'polite') {
    // Input validation
    if (typeof message !== 'string' || message.trim() === '') {
        console.error('announceToScreenReader: message must be a non-empty string');
        return;
    }
    
    const region = createScreenReaderRegion();
    region.setAttribute('aria-live', priority);
    
    // Clear and set new message
    region.textContent = '';
    setTimeout(() => {
        region.textContent = message;
    }, 100);
}

/**
 * Announce question change to screen readers
 * @param {number} questionNumber - Current question number (1-based)
 * @param {number} totalQuestions - Total number of questions
 * @param {string} questionText - Question text
 */
function announceQuestionChange(questionNumber, totalQuestions, questionText) {
    const message = `Question ${questionNumber} of ${totalQuestions}: ${questionText}`;
    announceToScreenReader(message);
}

/**
 * Announce answer selection to screen readers
 * @param {string} optionText - Selected option text
 * @param {string} optionLetter - Option letter (A, B, C, D)
 */
function announceAnswerSelection(optionText, optionLetter) {
    const message = `Selected option ${optionLetter}: ${optionText}`;
    announceToScreenReader(message);
}

/**
 * Announce timer warning to screen readers
 * @param {number} secondsRemaining - Seconds remaining
 */
function announceTimerWarning(secondsRemaining) {
    const message = `Warning: ${secondsRemaining} seconds remaining`;
    announceToScreenReader(message, 'assertive');
}

/**
 * Announce quiz completion to screen readers
 * @param {number} score - Quiz score
 * @param {number} total - Total questions
 */
function announceQuizCompletion(score, total) {
    const percentage = Math.round((score / total) * 100);
    const message = `Quiz completed. You scored ${score} out of ${total}, ${percentage} percent`;
    announceToScreenReader(message, 'assertive');
}

/**
 * Create focus trap for modal dialogs
 * @param {HTMLElement} modal - Modal element
 * @returns {Function} - Cleanup function
 */
function createFocusTrap(modal) {
    // Input validation
    if (!modal || !(modal instanceof HTMLElement)) {
        console.error('createFocusTrap: modal must be an HTMLElement');
        return () => {};
    }
    
    // Get all focusable elements
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = Array.from(modal.querySelectorAll(focusableSelector));
    
    if (focusableElements.length === 0) {
        console.warn('createFocusTrap: no focusable elements found in modal');
        return () => {};
    }
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    // Store previously focused element
    const previouslyFocused = document.activeElement;
    
    // Focus first element
    firstElement.focus();
    
    // Trap focus handler
    const trapFocus = (event) => {
        if (event.key !== 'Tab') return;
        
        if (event.shiftKey) {
            // Shift + Tab
            if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            }
        } else {
            // Tab
            if (document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    };
    
    modal.addEventListener('keydown', trapFocus);
    
    // Return cleanup function
    return () => {
        modal.removeEventListener('keydown', trapFocus);
        if (previouslyFocused && previouslyFocused.focus) {
            previouslyFocused.focus();
        }
    };
}

/**
 * Create skip links for quick navigation
 * @returns {HTMLElement} - Skip links container
 */
function createSkipLinks() {
    const container = document.createElement('div');
    container.className = 'skip-links';
    container.setAttribute('role', 'navigation');
    container.setAttribute('aria-label', 'Skip links');
    
    const links = [
        { text: 'Skip to quiz content', target: '#quiz-container' },
        { text: 'Skip to navigation', target: '#quiz-nav-sidebar-container' },
        { text: 'Skip to results', target: '#quiz-results' }
    ];
    
    links.forEach(link => {
        const anchor = document.createElement('a');
        anchor.href = link.target;
        anchor.className = 'skip-link';
        anchor.textContent = link.text;
        
        // Handle skip link click
        anchor.addEventListener('click', (event) => {
            event.preventDefault();
            const target = document.querySelector(link.target);
            if (target) {
                target.setAttribute('tabindex', '-1');
                target.focus();
                // Use smooth scrolling if supported, otherwise fallback to instant
                if ('scrollBehavior' in document.documentElement.style) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                    target.scrollIntoView();
                }
            } else {
                console.warn(`Skip link target not found: ${link.target}`);
            }
        });
        
        container.appendChild(anchor);
    });
    
    return container;
}

/**
 * Ensure visible focus indicators
 * @param {HTMLElement} container - Container to apply focus styles
 */
function ensureVisibleFocus(container) {
    // Input validation
    if (!container || !(container instanceof HTMLElement)) {
        console.error('ensureVisibleFocus: container must be an HTMLElement');
        return;
    }

    // Add focus-visible class to container
    container.classList.add('focus-visible-enabled');

    // Use event delegation instead of individual listeners to prevent memory leaks
    container.addEventListener('focusin', (event) => {
        if (event.target.matches('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')) {
            event.target.classList.add('has-focus');
        }
    });

    container.addEventListener('focusout', (event) => {
        if (event.target.matches('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')) {
            event.target.classList.remove('has-focus');
        }
    });
}

/**
 * Update document title for screen readers
 * @param {string} title - New title
 */
function updateDocumentTitle(title) {
    if (typeof title !== 'string' || title.trim() === '') {
        console.error('updateDocumentTitle: title must be a non-empty string');
        return;
    }
    
    document.title = title;
}

// Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        initializeKeyboardNavigation,
        handleQuizKeydown,
        navigateOptions,
        closeActiveModal,
        createScreenReaderRegion,
        announceToScreenReader,
        announceQuestionChange,
        announceAnswerSelection,
        announceTimerWarning,
        announceQuizCompletion,
        createFocusTrap,
        createSkipLinks,
        ensureVisibleFocus,
        updateDocumentTitle
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.initializeKeyboardNavigation = initializeKeyboardNavigation;
    window.handleQuizKeydown = handleQuizKeydown;
    window.navigateOptions = navigateOptions;
    window.closeActiveModal = closeActiveModal;
    window.createScreenReaderRegion = createScreenReaderRegion;
    window.announceToScreenReader = announceToScreenReader;
    window.announceQuestionChange = announceQuestionChange;
    window.announceAnswerSelection = announceAnswerSelection;
    window.announceTimerWarning = announceTimerWarning;
    window.announceQuizCompletion = announceQuizCompletion;
    window.createFocusTrap = createFocusTrap;
    window.createSkipLinks = createSkipLinks;
    window.ensureVisibleFocus = ensureVisibleFocus;
    window.updateDocumentTitle = updateDocumentTitle;
}

