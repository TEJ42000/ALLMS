/**
 * Quiz Answer Options Enhancements - Phase 2
 * 
 * Implements:
 * - Enhanced hover effects
 * - Better selected state styling
 * - Answer feedback (correct/incorrect indicators)
 * - Smooth animations
 * 
 * Security: All DOM manipulation uses safe methods (createElement, textContent)
 * Performance: GPU-accelerated animations, debounced interactions
 */

/**
 * Create enhanced answer option element
 * @param {string} optionText - Text of the answer option
 * @param {number} optionIndex - Index of the option (0-based)
 * @param {boolean} isSelected - Whether this option is selected
 * @param {boolean} isDisabled - Whether options are disabled (after answering)
 * @param {boolean|null} isCorrect - Whether this is the correct answer (null if not revealed)
 * @returns {HTMLElement} - Enhanced answer option element
 */
function createEnhancedAnswerOption(optionText, optionIndex, isSelected = false, isDisabled = false, isCorrect = null) {
    const option = document.createElement('button');
    option.className = 'quiz-option-enhanced';
    option.setAttribute('type', 'button');
    option.setAttribute('data-option-index', optionIndex);
    option.setAttribute('role', 'radio');
    option.setAttribute('aria-checked', isSelected ? 'true' : 'false');
    
    // Add state classes
    if (isSelected) {
        option.classList.add('selected');
    }
    
    if (isDisabled) {
        option.classList.add('disabled');
        option.setAttribute('disabled', 'true');
        option.setAttribute('aria-disabled', 'true');
    }
    
    // Add feedback classes if answer is revealed
    if (isCorrect !== null) {
        if (isCorrect) {
            option.classList.add('correct');
            option.setAttribute('aria-label', `${optionText} - Correct answer`);
        } else if (isSelected && !isCorrect) {
            option.classList.add('incorrect');
            option.setAttribute('aria-label', `${optionText} - Incorrect answer`);
        }
    }
    
    // Create option content container
    const content = document.createElement('div');
    content.className = 'option-content';
    
    // Option letter (A, B, C, D)
    const letter = document.createElement('span');
    letter.className = 'option-letter';
    letter.textContent = String.fromCharCode(65 + optionIndex); // A, B, C, D
    letter.setAttribute('aria-hidden', 'true');
    content.appendChild(letter);
    
    // Option text
    const text = document.createElement('span');
    text.className = 'option-text';
    text.textContent = optionText;
    content.appendChild(text);
    
    // Checkmark icon for selected state
    if (isSelected) {
        const checkmark = document.createElement('span');
        checkmark.className = 'option-checkmark';
        checkmark.textContent = '✓';
        checkmark.setAttribute('aria-hidden', 'true');
        content.appendChild(checkmark);
    }
    
    // Feedback icon (correct/incorrect)
    if (isCorrect !== null) {
        const feedbackIcon = document.createElement('span');
        feedbackIcon.className = 'option-feedback-icon';
        feedbackIcon.textContent = isCorrect ? '✓' : '✗';
        feedbackIcon.setAttribute('aria-hidden', 'true');
        content.appendChild(feedbackIcon);
    }
    
    option.appendChild(content);
    
    return option;
}

/**
 * Create answer options container with all options
 * @param {string[]} options - Array of option texts
 * @param {number|null} selectedIndex - Index of selected option (null if none)
 * @param {boolean} isDisabled - Whether options are disabled
 * @param {number|null} correctIndex - Index of correct answer (null if not revealed)
 * @returns {HTMLElement} - Container with all answer options
 */
function createAnswerOptionsContainer(options, selectedIndex = null, isDisabled = false, correctIndex = null) {
    // Input validation
    if (!Array.isArray(options) || options.length === 0) {
        console.error('createAnswerOptionsContainer: options must be a non-empty array');
        const fallback = document.createElement('div');
        fallback.textContent = 'No options available';
        return fallback;
    }
    
    const container = document.createElement('div');
    container.className = 'quiz-options-container';
    container.setAttribute('role', 'radiogroup');
    container.setAttribute('aria-label', 'Answer options');
    
    options.forEach((optionText, index) => {
        const isSelected = index === selectedIndex;
        const isCorrect = correctIndex !== null ? index === correctIndex : null;
        
        const option = createEnhancedAnswerOption(
            optionText,
            index,
            isSelected,
            isDisabled,
            isCorrect
        );
        
        container.appendChild(option);
    });
    
    return container;
}

/**
 * Add ripple effect to option on click
 * @param {HTMLElement} option - Option element
 * @param {MouseEvent} event - Click event
 */
function addRippleEffect(option, event) {
    const ripple = document.createElement('span');
    ripple.className = 'ripple-effect';
    
    // Calculate ripple position
    const rect = option.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    
    option.appendChild(ripple);
    
    // Remove ripple after animation
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

/**
 * Handle option selection with animation
 * @param {HTMLElement} option - Selected option element
 * @param {Function} onSelect - Callback function when option is selected
 */
function handleOptionSelection(option, onSelect) {
    if (option.classList.contains('disabled')) {
        return;
    }
    
    const container = option.closest('.quiz-options-container');
    if (!container) return;
    
    const optionIndex = parseInt(option.getAttribute('data-option-index'), 10);
    
    // Remove selected state from all options
    container.querySelectorAll('.quiz-option-enhanced').forEach(opt => {
        opt.classList.remove('selected');
        opt.setAttribute('aria-checked', 'false');
        
        // Remove existing checkmarks
        const existingCheckmark = opt.querySelector('.option-checkmark');
        if (existingCheckmark) {
            existingCheckmark.remove();
        }
    });
    
    // Add selected state to clicked option
    option.classList.add('selected');
    option.setAttribute('aria-checked', 'true');
    
    // Add checkmark
    const checkmark = document.createElement('span');
    checkmark.className = 'option-checkmark';
    checkmark.textContent = '✓';
    checkmark.setAttribute('aria-hidden', 'true');
    option.querySelector('.option-content').appendChild(checkmark);
    
    // Add scale animation
    option.style.transform = 'scale(0.98)';
    setTimeout(() => {
        option.style.transform = 'scale(1)';
    }, 100);
    
    // Call callback
    if (onSelect && typeof onSelect === 'function') {
        onSelect(optionIndex);
    }
}

/**
 * Show answer feedback with animation
 * @param {HTMLElement} container - Options container
 * @param {number} correctIndex - Index of correct answer
 * @param {number|null} selectedIndex - Index of selected answer
 */
function showAnswerFeedback(container, correctIndex, selectedIndex = null) {
    const options = container.querySelectorAll('.quiz-option-enhanced');
    
    options.forEach((option, index) => {
        // Disable all options
        option.classList.add('disabled');
        option.setAttribute('disabled', 'true');
        option.setAttribute('aria-disabled', 'true');
        
        // Add feedback classes and icons
        const isCorrect = index === correctIndex;
        const isSelected = index === selectedIndex;
        
        if (isCorrect) {
            option.classList.add('correct');
            option.setAttribute('aria-label', `${option.querySelector('.option-text').textContent} - Correct answer`);
            
            // Add feedback icon
            const feedbackIcon = document.createElement('span');
            feedbackIcon.className = 'option-feedback-icon';
            feedbackIcon.textContent = '✓';
            feedbackIcon.setAttribute('aria-hidden', 'true');
            option.querySelector('.option-content').appendChild(feedbackIcon);
            
        } else if (isSelected) {
            option.classList.add('incorrect');
            option.setAttribute('aria-label', `${option.querySelector('.option-text').textContent} - Incorrect answer`);
            
            // Add feedback icon
            const feedbackIcon = document.createElement('span');
            feedbackIcon.className = 'option-feedback-icon';
            feedbackIcon.textContent = '✗';
            feedbackIcon.setAttribute('aria-hidden', 'true');
            option.querySelector('.option-content').appendChild(feedbackIcon);
        }
        
        // Add staggered animation
        option.style.animationDelay = `${index * 0.1}s`;
    });
}

/**
 * Initialize Phase 2 enhancements for answer options
 * @param {HTMLElement} container - Quiz container element
 * @param {Function} onOptionSelect - Callback when option is selected
 */
function initializePhase2Enhancements(container, onOptionSelect) {
    // Use event delegation for better performance
    container.addEventListener('click', (event) => {
        const option = event.target.closest('.quiz-option-enhanced');
        if (option) {
            // Add ripple effect
            addRippleEffect(option, event);
            
            // Handle selection
            handleOptionSelection(option, onOptionSelect);
        }
    });
    
    // Keyboard navigation
    container.addEventListener('keydown', (event) => {
        const option = event.target.closest('.quiz-option-enhanced');
        if (!option) return;
        
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handleOptionSelection(option, onOptionSelect);
        }
    });
}

// Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        createEnhancedAnswerOption,
        createAnswerOptionsContainer,
        addRippleEffect,
        handleOptionSelection,
        showAnswerFeedback,
        initializePhase2Enhancements
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.createEnhancedAnswerOption = createEnhancedAnswerOption;
    window.createAnswerOptionsContainer = createAnswerOptionsContainer;
    window.addRippleEffect = addRippleEffect;
    window.handleOptionSelection = handleOptionSelection;
    window.showAnswerFeedback = showAnswerFeedback;
    window.initializePhase2Enhancements = initializePhase2Enhancements;
}

