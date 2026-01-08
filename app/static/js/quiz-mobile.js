/**
 * Quiz Mobile Responsiveness - Phase 6
 * 
 * Implements:
 * - Swipe gestures for navigation
 * - Touch-friendly interactions
 * - Mobile-specific optimizations
 * - Responsive layout enhancements
 * 
 * Security: All DOM manipulation uses safe methods
 * Accessibility: Touch targets meet WCAG 2.1 AA (44x44px minimum)
 */

/**
 * Initialize mobile features for quiz
 * @param {HTMLElement} container - Quiz container element
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Navigation callback
 * @returns {Function} - Cleanup function
 */
function initializeMobileFeatures(container, quizState, onNavigate) {
    // Input validation
    if (!container || !(container instanceof HTMLElement)) {
        console.error('initializeMobileFeatures: container must be an HTMLElement');
        return () => {};
    }
    
    if (!quizState || typeof quizState !== 'object') {
        console.error('initializeMobileFeatures: quizState must be an object');
        return () => {};
    }
    
    // Check if device supports touch
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    if (!isTouchDevice) {
        // Not a touch device, skip mobile features
        return () => {};
    }
    
    // Initialize swipe gestures
    const swipeCleanup = initializeSwipeGestures(container, quizState, onNavigate);
    
    // Add mobile-specific class
    container.classList.add('mobile-enabled');
    
    // Return cleanup function
    return () => {
        swipeCleanup();
        container.classList.remove('mobile-enabled');
    };
}

/**
 * Initialize swipe gestures for navigation
 * @param {HTMLElement} container - Quiz container element
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Navigation callback
 * @returns {Function} - Cleanup function
 */
function initializeSwipeGestures(container, quizState, onNavigate) {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    let isSwiping = false;
    
    const minSwipeDistance = 50; // Minimum distance for swipe (px)
    const maxVerticalDistance = 100; // Maximum vertical movement for horizontal swipe
    
    /**
     * Handle touch start
     */
    const handleTouchStart = (event) => {
        // Only handle single touch
        if (event.touches.length !== 1) return;
        
        const touch = event.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        isSwiping = true;
        
        // Add visual feedback
        container.classList.add('swiping');
    };
    
    /**
     * Handle touch move
     */
    const handleTouchMove = (event) => {
        if (!isSwiping) return;
        
        const touch = event.touches[0];
        touchEndX = touch.clientX;
        touchEndY = touch.clientY;
        
        // Calculate distances
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // If horizontal swipe is detected, prevent default scroll
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
            event.preventDefault();
        }
    };
    
    /**
     * Handle touch end
     */
    const handleTouchEnd = (event) => {
        if (!isSwiping) return;
        
        isSwiping = false;
        container.classList.remove('swiping');
        
        // Calculate swipe distance
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Check if it's a horizontal swipe
        if (Math.abs(deltaY) > maxVerticalDistance) {
            // Too much vertical movement, not a horizontal swipe
            return;
        }
        
        // Swipe left (next question)
        if (deltaX < -minSwipeDistance) {
            handleSwipeLeft(quizState, onNavigate);
        }
        // Swipe right (previous question)
        else if (deltaX > minSwipeDistance) {
            handleSwipeRight(quizState, onNavigate);
        }
        
        // Reset
        touchStartX = 0;
        touchStartY = 0;
        touchEndX = 0;
        touchEndY = 0;
    };
    
    /**
     * Handle touch cancel
     */
    const handleTouchCancel = () => {
        isSwiping = false;
        container.classList.remove('swiping');
        touchStartX = 0;
        touchStartY = 0;
        touchEndX = 0;
        touchEndY = 0;
    };
    
    // Add event listeners
    container.addEventListener('touchstart', handleTouchStart, { passive: true });
    container.addEventListener('touchmove', handleTouchMove, { passive: false });
    container.addEventListener('touchend', handleTouchEnd, { passive: true });
    container.addEventListener('touchcancel', handleTouchCancel, { passive: true });
    
    // Return cleanup function
    return () => {
        container.removeEventListener('touchstart', handleTouchStart);
        container.removeEventListener('touchmove', handleTouchMove);
        container.removeEventListener('touchend', handleTouchEnd);
        container.removeEventListener('touchcancel', handleTouchCancel);
    };
}

/**
 * Handle swipe left (next question)
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Navigation callback
 */
function handleSwipeLeft(quizState, onNavigate) {
    // Input validation
    if (!quizState || !Array.isArray(quizState.questions)) {
        console.error('handleSwipeLeft: invalid quizState');
        return;
    }
    
    const currentIndex = quizState.currentQuestionIndex;
    const totalQuestions = quizState.questions.length;
    
    // Check if we can go to next question
    if (currentIndex < totalQuestions - 1) {
        if (onNavigate && typeof onNavigate === 'function') {
            onNavigate(currentIndex + 1);
        }
        
        // Provide haptic feedback if supported
        provideHapticFeedback('light');
    }
}

/**
 * Handle swipe right (previous question)
 * @param {Object} quizState - Quiz state object
 * @param {Function} onNavigate - Navigation callback
 */
function handleSwipeRight(quizState, onNavigate) {
    // Input validation
    if (!quizState || !Array.isArray(quizState.questions)) {
        console.error('handleSwipeRight: invalid quizState');
        return;
    }
    
    const currentIndex = quizState.currentQuestionIndex;
    
    // Check if we can go to previous question
    if (currentIndex > 0) {
        if (onNavigate && typeof onNavigate === 'function') {
            onNavigate(currentIndex - 1);
        }
        
        // Provide haptic feedback if supported
        provideHapticFeedback('light');
    }
}

/**
 * Provide haptic feedback (if supported)
 * @param {string} type - Feedback type ('light', 'medium', 'heavy')
 */
function provideHapticFeedback(type = 'light') {
    // Check if Vibration API is supported
    if (!navigator.vibrate) {
        return;
    }
    
    // Vibration patterns for different feedback types
    const patterns = {
        light: 10,
        medium: 20,
        heavy: 30
    };
    
    const duration = patterns[type] || patterns.light;
    navigator.vibrate(duration);
}

/**
 * Optimize touch targets for mobile
 * @param {HTMLElement} container - Container element
 */
function optimizeTouchTargets(container) {
    // Input validation
    if (!container || !(container instanceof HTMLElement)) {
        console.error('optimizeTouchTargets: container must be an HTMLElement');
        return;
    }
    
    // Find all interactive elements
    const interactiveElements = container.querySelectorAll(
        'button, a, input, select, textarea, [role="button"], .quiz-option-enhanced'
    );
    
    interactiveElements.forEach(element => {
        // Check current size
        const rect = element.getBoundingClientRect();
        const minSize = 44; // WCAG 2.1 AA minimum
        
        // Add touch-optimized class if element is too small
        if (rect.width < minSize || rect.height < minSize) {
            element.classList.add('touch-optimized');
        }
    });
}

/**
 * Toggle mobile sidebar
 * @param {HTMLElement} sidebar - Sidebar element
 * @param {boolean} open - Whether to open or close
 */
function toggleMobileSidebar(sidebar, open) {
    // Input validation
    if (!sidebar || !(sidebar instanceof HTMLElement)) {
        console.error('toggleMobileSidebar: sidebar must be an HTMLElement');
        return;
    }
    
    if (open) {
        sidebar.classList.add('open');
        sidebar.setAttribute('aria-expanded', 'true');
    } else {
        sidebar.classList.remove('open');
        sidebar.setAttribute('aria-expanded', 'false');
    }
}

/**
 * Check if device is mobile
 * @returns {boolean} - True if mobile device
 */
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           window.innerWidth <= 768;
}

/**
 * Get viewport size
 * @returns {Object} - Viewport width and height
 */
function getViewportSize() {
    return {
        width: window.innerWidth || document.documentElement.clientWidth,
        height: window.innerHeight || document.documentElement.clientHeight
    };
}

// Export for use in main app.js (both Node.js and browser)
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        initializeMobileFeatures,
        initializeSwipeGestures,
        handleSwipeLeft,
        handleSwipeRight,
        provideHapticFeedback,
        optimizeTouchTargets,
        toggleMobileSidebar,
        isMobileDevice,
        getViewportSize
    };
} else if (typeof window !== 'undefined') {
    // Browser global exports
    window.initializeMobileFeatures = initializeMobileFeatures;
    window.initializeSwipeGestures = initializeSwipeGestures;
    window.handleSwipeLeft = handleSwipeLeft;
    window.handleSwipeRight = handleSwipeRight;
    window.provideHapticFeedback = provideHapticFeedback;
    window.optimizeTouchTargets = optimizeTouchTargets;
    window.toggleMobileSidebar = toggleMobileSidebar;
    window.isMobileDevice = isMobileDevice;
    window.getViewportSize = getViewportSize;
}

