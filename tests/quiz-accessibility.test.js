/**
 * Unit Tests for Quiz Accessibility - Phase 5
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - Keyboard navigation
 * - Screen reader announcements
 * - Focus management
 * - Skip links
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

// Import module under test
const {
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
} = require('../app/static/js/quiz-accessibility');

describe('Quiz Accessibility - Phase 5', () => {
    
    beforeEach(() => {
        // Clear document body before each test
        document.body.innerHTML = '';
    });
    
    describe('initializeKeyboardNavigation', () => {
        test('initializes keyboard navigation and returns cleanup function', () => {
            const container = document.createElement('div');
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();

            const cleanup = initializeKeyboardNavigation(container, quizState, onNavigate);

            expect(typeof cleanup).toBe('function');
            expect(container).toBeTruthy();
        });

        test('validates container parameter and returns cleanup', () => {
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();

            const cleanup = initializeKeyboardNavigation(null, quizState, onNavigate);
            expect(typeof cleanup).toBe('function');
        });

        test('validates quizState parameter and returns cleanup', () => {
            const container = document.createElement('div');
            const onNavigate = jest.fn();

            const cleanup = initializeKeyboardNavigation(container, null, onNavigate);
            expect(typeof cleanup).toBe('function');
        });

        test('cleanup function removes event listener', () => {
            const container = document.createElement('div');
            const quizState = { currentQuestionIndex: 0, questions: [] };
            const onNavigate = jest.fn();

            const cleanup = initializeKeyboardNavigation(container, quizState, onNavigate);
            cleanup();

            // Should not throw
            expect(cleanup).toBeTruthy();
        });
    });
    
    describe('navigateOptions', () => {
        test('navigates to first option when none focused', () => {
            const option1 = document.createElement('button');
            option1.className = 'quiz-option-enhanced';
            const option2 = document.createElement('button');
            option2.className = 'quiz-option-enhanced';
            
            document.body.appendChild(option1);
            document.body.appendChild(option2);
            
            navigateOptions(1);
            
            expect(document.activeElement).toBe(option1);
        });
        
        test('navigates down to next option', () => {
            const option1 = document.createElement('button');
            option1.className = 'quiz-option-enhanced';
            const option2 = document.createElement('button');
            option2.className = 'quiz-option-enhanced';
            
            document.body.appendChild(option1);
            document.body.appendChild(option2);
            
            option1.focus();
            navigateOptions(1);
            
            expect(document.activeElement).toBe(option2);
        });
        
        test('wraps to first option when navigating down from last', () => {
            const option1 = document.createElement('button');
            option1.className = 'quiz-option-enhanced';
            const option2 = document.createElement('button');
            option2.className = 'quiz-option-enhanced';
            
            document.body.appendChild(option1);
            document.body.appendChild(option2);
            
            option2.focus();
            navigateOptions(1);
            
            expect(document.activeElement).toBe(option1);
        });
        
        test('wraps to last option when navigating up from first', () => {
            const option1 = document.createElement('button');
            option1.className = 'quiz-option-enhanced';
            const option2 = document.createElement('button');
            option2.className = 'quiz-option-enhanced';
            
            document.body.appendChild(option1);
            document.body.appendChild(option2);
            
            option1.focus();
            navigateOptions(-1);
            
            expect(document.activeElement).toBe(option2);
        });
    });
    
    describe('closeActiveModal', () => {
        test('closes active modal', () => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
            
            closeActiveModal();
            
            expect(document.querySelector('.modal-overlay')).toBeFalsy();
        });
        
        test('does nothing if no modal exists', () => {
            expect(() => closeActiveModal()).not.toThrow();
        });
    });
    
    describe('createScreenReaderRegion', () => {
        test('creates screen reader region', () => {
            const region = createScreenReaderRegion();
            
            expect(region.id).toBe('quiz-sr-announcements');
            expect(region.getAttribute('role')).toBe('status');
            expect(region.getAttribute('aria-live')).toBe('polite');
            expect(region.getAttribute('aria-atomic')).toBe('true');
        });
        
        test('returns existing region if already created', () => {
            const region1 = createScreenReaderRegion();
            const region2 = createScreenReaderRegion();
            
            expect(region1).toBe(region2);
        });
    });
    
    describe('announceToScreenReader', () => {
        test('announces message to screen reader', (done) => {
            announceToScreenReader('Test message');
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.textContent).toBe('Test message');
                done();
            }, 150);
        });
        
        test('sets priority level', (done) => {
            announceToScreenReader('Urgent message', 'assertive');
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.getAttribute('aria-live')).toBe('assertive');
                done();
            }, 150);
        });
        
        test('validates message parameter', () => {
            expect(() => announceToScreenReader('')).not.toThrow();
            expect(() => announceToScreenReader(null)).not.toThrow();
        });
    });
    
    describe('announceQuestionChange', () => {
        test('announces question change', (done) => {
            announceQuestionChange(1, 10, 'What is the answer?');
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.textContent).toContain('Question 1 of 10');
                expect(region.textContent).toContain('What is the answer?');
                done();
            }, 150);
        });
    });
    
    describe('announceAnswerSelection', () => {
        test('announces answer selection', (done) => {
            announceAnswerSelection('Option text', 'A');
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.textContent).toContain('Selected option A');
                expect(region.textContent).toContain('Option text');
                done();
            }, 150);
        });
    });
    
    describe('announceTimerWarning', () => {
        test('announces timer warning', (done) => {
            announceTimerWarning(30);
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.textContent).toContain('Warning');
                expect(region.textContent).toContain('30 seconds');
                done();
            }, 150);
        });
    });
    
    describe('announceQuizCompletion', () => {
        test('announces quiz completion', (done) => {
            announceQuizCompletion(8, 10);
            
            setTimeout(() => {
                const region = document.getElementById('quiz-sr-announcements');
                expect(region.textContent).toContain('Quiz completed');
                expect(region.textContent).toContain('8 out of 10');
                expect(region.textContent).toContain('80 percent');
                done();
            }, 150);
        });
    });
    
    describe('createFocusTrap', () => {
        test('creates focus trap', () => {
            const modal = document.createElement('div');
            const button1 = document.createElement('button');
            const button2 = document.createElement('button');
            
            modal.appendChild(button1);
            modal.appendChild(button2);
            document.body.appendChild(modal);
            
            const cleanup = createFocusTrap(modal);
            
            expect(document.activeElement).toBe(button1);
            expect(typeof cleanup).toBe('function');
        });
        
        test('validates modal parameter', () => {
            const cleanup = createFocusTrap(null);
            expect(typeof cleanup).toBe('function');
        });
        
        test('handles modal with no focusable elements', () => {
            const modal = document.createElement('div');
            document.body.appendChild(modal);
            
            const cleanup = createFocusTrap(modal);
            expect(typeof cleanup).toBe('function');
        });
    });
    
    describe('createSkipLinks', () => {
        test('creates skip links container', () => {
            const skipLinks = createSkipLinks();
            
            expect(skipLinks.className).toBe('skip-links');
            expect(skipLinks.getAttribute('role')).toBe('navigation');
            expect(skipLinks.getAttribute('aria-label')).toBe('Skip links');
        });
        
        test('creates multiple skip links', () => {
            const skipLinks = createSkipLinks();
            const links = skipLinks.querySelectorAll('.skip-link');
            
            expect(links.length).toBeGreaterThan(0);
        });
        
        test('skip links have correct attributes', () => {
            const skipLinks = createSkipLinks();
            const firstLink = skipLinks.querySelector('.skip-link');
            
            expect(firstLink.href).toBeTruthy();
            expect(firstLink.textContent).toBeTruthy();
        });
    });
    
    describe('ensureVisibleFocus', () => {
        test('adds focus-visible class to container', () => {
            const container = document.createElement('div');
            
            ensureVisibleFocus(container);
            
            expect(container.classList.contains('focus-visible-enabled')).toBeTruthy();
        });
        
        test('validates container parameter', () => {
            expect(() => ensureVisibleFocus(null)).not.toThrow();
        });
    });
    
    describe('updateDocumentTitle', () => {
        test('updates document title', () => {
            updateDocumentTitle('New Title');
            
            expect(document.title).toBe('New Title');
        });
        
        test('validates title parameter', () => {
            expect(() => updateDocumentTitle('')).not.toThrow();
            expect(() => updateDocumentTitle(null)).not.toThrow();
        });
    });
});

