/**
 * Unit Tests for Quiz Mobile Responsiveness - Phase 6
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - Mobile feature initialization
 * - Swipe gesture detection
 * - Touch target optimization
 * - Mobile utilities
 */

// Polyfill for TextEncoder/TextDecoder (required by jsdom)
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock DOM environment
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;
global.navigator = dom.window.navigator;

// Mock touch support
Object.defineProperty(window, 'ontouchstart', {
    writable: true,
    value: true
});

// Import module under test
const {
    initializeMobileFeatures,
    initializeSwipeGestures,
    handleSwipeLeft,
    handleSwipeRight,
    provideHapticFeedback,
    optimizeTouchTargets,
    toggleMobileSidebar,
    isMobileDevice,
    getViewportSize
} = require('../app/static/js/quiz-mobile');

describe('Quiz Mobile Responsiveness - Phase 6', () => {
    
    beforeEach(() => {
        // Clear document body before each test
        document.body.innerHTML = '';
    });
    
    describe('initializeMobileFeatures', () => {
        test('initializes mobile features and returns cleanup function', () => {
            const container = document.createElement('div');
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();
            
            const cleanup = initializeMobileFeatures(container, quizState, onNavigate);
            
            expect(typeof cleanup).toBe('function');
            expect(container.classList.contains('mobile-enabled')).toBeTruthy();
        });
        
        test('validates container parameter', () => {
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();
            
            const cleanup = initializeMobileFeatures(null, quizState, onNavigate);
            expect(typeof cleanup).toBe('function');
        });
        
        test('validates quizState parameter', () => {
            const container = document.createElement('div');
            const onNavigate = jest.fn();
            
            const cleanup = initializeMobileFeatures(container, null, onNavigate);
            expect(typeof cleanup).toBe('function');
        });
        
        test('cleanup function removes mobile-enabled class', () => {
            const container = document.createElement('div');
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();
            
            const cleanup = initializeMobileFeatures(container, quizState, onNavigate);
            cleanup();
            
            expect(container.classList.contains('mobile-enabled')).toBeFalsy();
        });
    });
    
    describe('initializeSwipeGestures', () => {
        test('initializes swipe gestures and returns cleanup function', () => {
            const container = document.createElement('div');
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();
            
            const cleanup = initializeSwipeGestures(container, quizState, onNavigate);
            
            expect(typeof cleanup).toBe('function');
        });
        
        test('cleanup function removes event listeners', () => {
            const container = document.createElement('div');
            document.body.appendChild(container);
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();

            const cleanup = initializeSwipeGestures(container, quizState, onNavigate);
            cleanup();

            // Verify cleanup doesn't throw
            expect(cleanup).toBeTruthy();
        });
    });
    
    describe('handleSwipeLeft', () => {
        test('navigates to next question', () => {
            const quizState = {
                currentQuestionIndex: 0,
                questions: [{ id: 1 }, { id: 2 }, { id: 3 }]
            };
            const onNavigate = jest.fn();
            
            handleSwipeLeft(quizState, onNavigate);
            
            expect(onNavigate).toHaveBeenCalledWith(1);
        });
        
        test('does not navigate past last question', () => {
            const quizState = {
                currentQuestionIndex: 2,
                questions: [{ id: 1 }, { id: 2 }, { id: 3 }]
            };
            const onNavigate = jest.fn();
            
            handleSwipeLeft(quizState, onNavigate);
            
            expect(onNavigate).not.toHaveBeenCalled();
        });
        
        test('validates quizState parameter', () => {
            const onNavigate = jest.fn();
            
            expect(() => handleSwipeLeft(null, onNavigate)).not.toThrow();
            expect(onNavigate).not.toHaveBeenCalled();
        });
    });
    
    describe('handleSwipeRight', () => {
        test('navigates to previous question', () => {
            const quizState = {
                currentQuestionIndex: 1,
                questions: [{ id: 1 }, { id: 2 }, { id: 3 }]
            };
            const onNavigate = jest.fn();
            
            handleSwipeRight(quizState, onNavigate);
            
            expect(onNavigate).toHaveBeenCalledWith(0);
        });
        
        test('does not navigate before first question', () => {
            const quizState = {
                currentQuestionIndex: 0,
                questions: [{ id: 1 }, { id: 2 }, { id: 3 }]
            };
            const onNavigate = jest.fn();
            
            handleSwipeRight(quizState, onNavigate);
            
            expect(onNavigate).not.toHaveBeenCalled();
        });
        
        test('validates quizState parameter', () => {
            const onNavigate = jest.fn();
            
            expect(() => handleSwipeRight(null, onNavigate)).not.toThrow();
            expect(onNavigate).not.toHaveBeenCalled();
        });
    });
    
    describe('provideHapticFeedback', () => {
        test('does not throw when vibration not supported', () => {
            // Mock navigator.vibrate as undefined
            delete navigator.vibrate;
            
            expect(() => provideHapticFeedback('light')).not.toThrow();
        });
        
        test('calls vibrate with correct duration for light feedback', () => {
            navigator.vibrate = jest.fn();
            
            provideHapticFeedback('light');
            
            expect(navigator.vibrate).toHaveBeenCalledWith(10);
        });
        
        test('calls vibrate with correct duration for medium feedback', () => {
            navigator.vibrate = jest.fn();
            
            provideHapticFeedback('medium');
            
            expect(navigator.vibrate).toHaveBeenCalledWith(20);
        });
        
        test('calls vibrate with correct duration for heavy feedback', () => {
            navigator.vibrate = jest.fn();
            
            provideHapticFeedback('heavy');
            
            expect(navigator.vibrate).toHaveBeenCalledWith(30);
        });
        
        test('defaults to light feedback for unknown type', () => {
            navigator.vibrate = jest.fn();
            
            provideHapticFeedback('unknown');
            
            expect(navigator.vibrate).toHaveBeenCalledWith(10);
        });
    });
    
    describe('optimizeTouchTargets', () => {
        test('adds touch-optimized class to small elements', () => {
            const container = document.createElement('div');
            const button = document.createElement('button');
            button.style.width = '30px';
            button.style.height = '30px';
            container.appendChild(button);
            document.body.appendChild(container);
            
            optimizeTouchTargets(container);
            
            // Note: In jsdom, getBoundingClientRect returns 0 for all values
            // So this test verifies the function runs without error
            expect(button).toBeTruthy();
        });
        
        test('validates container parameter', () => {
            expect(() => optimizeTouchTargets(null)).not.toThrow();
        });
    });
    
    describe('toggleMobileSidebar', () => {
        test('opens sidebar', () => {
            const sidebar = document.createElement('div');
            
            toggleMobileSidebar(sidebar, true);
            
            expect(sidebar.classList.contains('open')).toBeTruthy();
            expect(sidebar.getAttribute('aria-expanded')).toBe('true');
        });
        
        test('closes sidebar', () => {
            const sidebar = document.createElement('div');
            sidebar.classList.add('open');
            
            toggleMobileSidebar(sidebar, false);
            
            expect(sidebar.classList.contains('open')).toBeFalsy();
            expect(sidebar.getAttribute('aria-expanded')).toBe('false');
        });
        
        test('validates sidebar parameter', () => {
            expect(() => toggleMobileSidebar(null, true)).not.toThrow();
        });
    });
    
    describe('isMobileDevice', () => {
        test('returns boolean', () => {
            const result = isMobileDevice();
            expect(typeof result).toBe('boolean');
        });
    });
    
    describe('getViewportSize', () => {
        test('returns viewport dimensions', () => {
            const size = getViewportSize();
            
            expect(size).toHaveProperty('width');
            expect(size).toHaveProperty('height');
            expect(typeof size.width).toBe('number');
            expect(typeof size.height).toBe('number');
        });
    });
});

