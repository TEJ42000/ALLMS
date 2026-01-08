/**
 * Quiz Navigation Controls - Phase 3
 * 
 * Implements:
 * - Flag for review functionality
 * - Question navigation sidebar
 * - Confirmation dialog before submission
 * 
 * Security: All DOM manipulation uses safe methods (createElement, textContent)
 * Accessibility: WCAG 2.1 AA compliant with ARIA labels and keyboard navigation
 */

/**
 * Create flag button for current question
 * @param {number} questionIndex - Index of the question
 * @param {boolean} isFlagged - Whether question is currently flagged
 * @returns {HTMLElement} - Flag button element
 */
function createFlagButton(questionIndex, isFlagged = false) {
    // Input validation
    if (typeof questionIndex !== 'number' || !Number.isInteger(questionIndex) || questionIndex < 0) {
        console.error('createFlagButton: questionIndex must be a non-negative integer');
        questionIndex = 0;
    }
    
    if (typeof isFlagged !== 'boolean') {
        console.error('createFlagButton: isFlagged must be a boolean');
        isFlagged = false;
    }
    
    const button = document.createElement('button');
    button.className = `quiz-flag-btn ${isFlagged ? 'flagged' : ''}`;
    button.setAttribute('type', 'button');
    button.setAttribute('data-question-index', questionIndex);
    button.setAttribute('aria-label', isFlagged ? 'Remove flag from this question' : 'Flag this question for review');
    button.setAttribute('aria-pressed', isFlagged ? 'true' : 'false');
    
    // Flag icon
    const icon = document.createElement('span');
    icon.className = 'flag-icon';
    icon.textContent = '🚩';
    icon.setAttribute('aria-hidden', 'true');
    button.appendChild(icon);
    
    // Flag text
    const text = document.createElement('span');
    text.className = 'flag-text';
    text.textContent = isFlagged ? 'Flagged' : 'Flag for Review';
    button.appendChild(text);
    
    return button;
}

/**
 * Get question status classes
 * @param {number} index - Question index
 * @param {Object} quizState - Current quiz state
 * @returns {string} - Space-separated class names
 */
function getQuestionStatus(index, quizState) {
    // Input validation
    if (typeof index !== 'number' || !Number.isInteger(index) || index < 0) {
        console.error('getQuestionStatus: index must be a non-negative integer');
        return '';
    }
    
    if (!quizState || typeof quizState !== 'object') {
        console.error('getQuestionStatus: quizState must be an object');
        return '';
    }
    
    const classes = [];
    
    if (index === quizState.currentQuestionIndex) {
        classes.push('current');
    }
    
    if (quizState.userAnswers && quizState.userAnswers[index] !== null && quizState.userAnswers[index] !== undefined) {
        classes.push('answered');
    }
    
    if (quizState.flaggedQuestions && Array.isArray(quizState.flaggedQuestions) && quizState.flaggedQuestions.includes(index)) {
        classes.push('flagged');
    }
    
    return classes.join(' ');
}

/**
 * Create question navigation sidebar
 * @param {Object} quizState - Current quiz state
 * @param {Function} onNavigate - Callback when question is clicked
 * @returns {HTMLElement} - Navigation sidebar element
 */
function createQuestionNavSidebar(quizState, onNavigate) {
    // Input validation
    if (!quizState || typeof quizState !== 'object') {
        console.error('createQuestionNavSidebar: quizState must be an object');
        const fallback = document.createElement('div');
        fallback.textContent = 'Navigation unavailable';
        return fallback;
    }
    
    if (!Array.isArray(quizState.questions) || quizState.questions.length === 0) {
        console.error('createQuestionNavSidebar: quizState.questions must be a non-empty array');
        const fallback = document.createElement('div');
        fallback.textContent = 'No questions available';
        return fallback;
    }
    
    const nav = document.createElement('nav');
    nav.className = 'question-nav-sidebar';
    nav.setAttribute('aria-label', 'Question navigation');
    
    // Header
    const header = document.createElement('div');
    header.className = 'nav-sidebar-header';
    
    const title = document.createElement('h3');
    title.textContent = 'Questions';
    header.appendChild(title);
    
    // Toggle button for mobile
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'nav-sidebar-toggle';
    toggleBtn.setAttribute('type', 'button');
    toggleBtn.setAttribute('aria-label', 'Toggle question navigation');
    toggleBtn.setAttribute('aria-expanded', 'true');
    toggleBtn.textContent = '−';
    header.appendChild(toggleBtn);
    
    nav.appendChild(header);
    
    // Grid container
    const grid = document.createElement('div');
    grid.className = 'question-nav-grid';
    grid.setAttribute('role', 'list');
    
    // Create navigation buttons
    quizState.questions.forEach((question, index) => {
        const button = document.createElement('button');
        button.className = `question-nav-btn ${getQuestionStatus(index, quizState)}`;
        button.setAttribute('type', 'button');
        button.setAttribute('data-question-index', index);
        button.setAttribute('role', 'listitem');
        button.setAttribute('aria-label', `Question ${index + 1}${quizState.userAnswers && quizState.userAnswers[index] !== null ? ' (answered)' : ''}${quizState.flaggedQuestions?.includes(index) ? ' (flagged)' : ''}`);
        button.setAttribute('aria-current', index === quizState.currentQuestionIndex ? 'true' : 'false');
        button.textContent = index + 1;
        
        grid.appendChild(button);
    });
    
    nav.appendChild(grid);
    
    // Legend
    const legend = document.createElement('div');
    legend.className = 'nav-sidebar-legend';
    
    const legendItems = [
        { class: 'current', label: 'Current' },
        { class: 'answered', label: 'Answered' },
        { class: 'flagged', label: 'Flagged' }
    ];
    
    legendItems.forEach(item => {
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        
        const indicator = document.createElement('span');
        indicator.className = `legend-indicator ${item.class}`;
        indicator.setAttribute('aria-hidden', 'true');
        legendItem.appendChild(indicator);
        
        const label = document.createElement('span');
        label.textContent = item.label;
        legendItem.appendChild(label);
        
        legend.appendChild(legendItem);
    });
    
    nav.appendChild(legend);
    
    return nav;
}

/**
 * Create confirmation dialog before quiz submission
 * @param {Object} quizState - Current quiz state
 * @param {Function} onConfirm - Callback when confirmed
 * @param {Function} onCancel - Callback when cancelled
 * @returns {HTMLElement} - Confirmation dialog element
 */
function createSubmitConfirmationDialog(quizState, onConfirm, onCancel) {
    // Input validation
    if (!quizState || typeof quizState !== 'object') {
        console.error('createSubmitConfirmationDialog: quizState must be an object');
        return null;
    }
    
    // Calculate unanswered and flagged questions
    const unansweredQuestions = [];
    const flaggedQuestions = quizState.flaggedQuestions || [];
    
    if (Array.isArray(quizState.questions)) {
        quizState.questions.forEach((q, index) => {
            if (!quizState.userAnswers || quizState.userAnswers[index] === null || quizState.userAnswers[index] === undefined) {
                unansweredQuestions.push(index + 1);
            }
        });
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'submit-dialog-title');
    
    // Create modal content
    const modal = document.createElement('div');
    modal.className = 'submit-confirmation-modal';
    
    // Title
    const title = document.createElement('h2');
    title.id = 'submit-dialog-title';
    title.textContent = 'Submit Quiz?';
    modal.appendChild(title);
    
    // Content
    const content = document.createElement('div');
    content.className = 'modal-content';
    
    // Summary
    const summary = document.createElement('p');
    summary.textContent = `You are about to submit your quiz with ${quizState.questions?.length || 0} questions.`;
    content.appendChild(summary);
    
    // Unanswered questions warning
    if (unansweredQuestions.length > 0) {
        const warning = document.createElement('div');
        warning.className = 'warning-box';
        
        const warningTitle = document.createElement('strong');
        warningTitle.textContent = `⚠️ ${unansweredQuestions.length} Unanswered Question${unansweredQuestions.length > 1 ? 's' : ''}`;
        warning.appendChild(warningTitle);
        
        const warningText = document.createElement('p');
        warningText.textContent = `Questions: ${unansweredQuestions.join(', ')}`;
        warning.appendChild(warningText);
        
        content.appendChild(warning);
    }
    
    // Flagged questions info
    if (flaggedQuestions.length > 0) {
        const info = document.createElement('div');
        info.className = 'info-box';
        
        const infoTitle = document.createElement('strong');
        infoTitle.textContent = `🚩 ${flaggedQuestions.length} Flagged Question${flaggedQuestions.length > 1 ? 's' : ''}`;
        info.appendChild(infoTitle);
        
        const infoText = document.createElement('p');
        infoText.textContent = `Questions: ${flaggedQuestions.map(i => i + 1).join(', ')}`;
        info.appendChild(infoText);
        
        content.appendChild(info);
    }
    
    modal.appendChild(content);
    
    // Actions
    const actions = document.createElement('div');
    actions.className = 'modal-actions';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.setAttribute('type', 'button');
    cancelBtn.textContent = 'Go Back';
    actions.appendChild(cancelBtn);
    
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.setAttribute('type', 'button');
    confirmBtn.textContent = 'Submit Quiz';
    actions.appendChild(confirmBtn);
    
    modal.appendChild(actions);
    overlay.appendChild(modal);
    
    return overlay;
}

// Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        createFlagButton,
        getQuestionStatus,
        createQuestionNavSidebar,
        createSubmitConfirmationDialog
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.createFlagButton = createFlagButton;
    window.getQuestionStatus = getQuestionStatus;
    window.createQuestionNavSidebar = createQuestionNavSidebar;
    window.createSubmitConfirmationDialog = createSubmitConfirmationDialog;
}

