/**
 * Unit Tests for Quiz Navigation Controls - Phase 3
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - Flag button creation
 * - Question status determination
 * - Navigation sidebar creation
 * - Confirmation dialog creation
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
    createFlagButton,
    getQuestionStatus,
    createQuestionNavSidebar,
    createSubmitConfirmationDialog
} = require('../app/static/js/quiz-navigation-controls');

describe('Quiz Navigation Controls - Phase 3', () => {
    
    describe('createFlagButton', () => {
        test('creates basic flag button', () => {
            const button = createFlagButton(0, false);
            
            expect(button.tagName).toBe('BUTTON');
            expect(button.className).toContain('quiz-flag-btn');
            expect(button.getAttribute('type')).toBe('button');
            expect(button.getAttribute('data-question-index')).toBe('0');
        });
        
        test('creates unflagged button with correct text', () => {
            const button = createFlagButton(0, false);
            
            expect(button.classList.contains('flagged')).toBeFalsy();
            expect(button.getAttribute('aria-pressed')).toBe('false');
            expect(button.querySelector('.flag-text').textContent).toBe('Flag for Review');
        });
        
        test('creates flagged button with correct text', () => {
            const button = createFlagButton(0, true);
            
            expect(button.classList.contains('flagged')).toBeTruthy();
            expect(button.getAttribute('aria-pressed')).toBe('true');
            expect(button.querySelector('.flag-text').textContent).toBe('Flagged');
        });
        
        test('includes flag icon', () => {
            const button = createFlagButton(0, false);
            const icon = button.querySelector('.flag-icon');
            
            expect(icon).toBeTruthy();
            expect(icon.textContent).toBe('🚩');
        });
        
        test('validates questionIndex parameter', () => {
            // Should default to 0 for invalid index
            const button1 = createFlagButton(-1, false);
            expect(button1.getAttribute('data-question-index')).toBe('0');
            
            const button2 = createFlagButton('invalid', false);
            expect(button2.getAttribute('data-question-index')).toBe('0');
        });
        
        test('validates isFlagged parameter', () => {
            // Should default to false for non-boolean
            const button = createFlagButton(0, 'true');
            expect(button.classList.contains('flagged')).toBeFalsy();
        });
    });
    
    describe('getQuestionStatus', () => {
        const mockQuizState = {
            currentQuestionIndex: 1,
            userAnswers: [0, null, 2, null],
            flaggedQuestions: [2, 3]
        };
        
        test('returns current status', () => {
            const status = getQuestionStatus(1, mockQuizState);
            expect(status).toContain('current');
        });
        
        test('returns answered status', () => {
            const status = getQuestionStatus(0, mockQuizState);
            expect(status).toContain('answered');
        });
        
        test('returns flagged status', () => {
            const status = getQuestionStatus(2, mockQuizState);
            expect(status).toContain('flagged');
        });
        
        test('returns multiple statuses', () => {
            const status = getQuestionStatus(2, mockQuizState);
            expect(status).toContain('answered');
            expect(status).toContain('flagged');
        });
        
        test('returns empty string for no status', () => {
            const status = getQuestionStatus(3, mockQuizState);
            expect(status).toContain('flagged');
            expect(status).not.toContain('answered');
        });
        
        test('validates index parameter', () => {
            const status = getQuestionStatus(-1, mockQuizState);
            expect(status).toBe('');
        });
        
        test('validates quizState parameter', () => {
            const status = getQuestionStatus(0, null);
            expect(status).toBe('');
        });
    });
    
    describe('createQuestionNavSidebar', () => {
        const mockQuizState = {
            currentQuestionIndex: 1,
            questions: [
                { id: 1 },
                { id: 2 },
                { id: 3 },
                { id: 4 }
            ],
            userAnswers: [0, null, 2, null],
            flaggedQuestions: [2]
        };
        
        test('creates navigation sidebar', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            
            expect(sidebar.tagName).toBe('NAV');
            expect(sidebar.className).toBe('question-nav-sidebar');
            expect(sidebar.getAttribute('aria-label')).toBe('Question navigation');
        });
        
        test('includes header with title', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const title = sidebar.querySelector('h3');
            
            expect(title.textContent).toBe('Questions');
        });
        
        test('creates navigation buttons for all questions', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const buttons = sidebar.querySelectorAll('.question-nav-btn');
            
            expect(buttons).toHaveLength(4);
        });
        
        test('marks current question', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const currentBtn = sidebar.querySelector('[data-question-index="1"]');
            
            expect(currentBtn.classList.contains('current')).toBeTruthy();
            expect(currentBtn.getAttribute('aria-current')).toBe('true');
        });
        
        test('marks answered questions', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const answeredBtn = sidebar.querySelector('[data-question-index="0"]');
            
            expect(answeredBtn.classList.contains('answered')).toBeTruthy();
        });
        
        test('marks flagged questions', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const flaggedBtn = sidebar.querySelector('[data-question-index="2"]');
            
            expect(flaggedBtn.classList.contains('flagged')).toBeTruthy();
        });
        
        test('includes legend', () => {
            const sidebar = createQuestionNavSidebar(mockQuizState, jest.fn());
            const legend = sidebar.querySelector('.nav-sidebar-legend');
            
            expect(legend).toBeTruthy();
            expect(legend.querySelectorAll('.legend-item')).toHaveLength(3);
        });
        
        test('validates quizState parameter', () => {
            const sidebar = createQuestionNavSidebar(null, jest.fn());
            expect(sidebar.textContent).toBe('Navigation unavailable');
        });
        
        test('validates questions array', () => {
            const invalidState = { questions: [] };
            const sidebar = createQuestionNavSidebar(invalidState, jest.fn());
            expect(sidebar.textContent).toBe('No questions available');
        });
    });
    
    describe('createSubmitConfirmationDialog', () => {
        const mockQuizState = {
            questions: [
                { id: 1 },
                { id: 2 },
                { id: 3 },
                { id: 4 }
            ],
            userAnswers: [0, null, 2, null],
            flaggedQuestions: [2]
        };
        
        test('creates confirmation dialog', () => {
            const dialog = createSubmitConfirmationDialog(mockQuizState, jest.fn(), jest.fn());
            
            expect(dialog.className).toBe('modal-overlay');
            expect(dialog.getAttribute('role')).toBe('dialog');
            expect(dialog.getAttribute('aria-modal')).toBe('true');
        });
        
        test('includes title', () => {
            const dialog = createSubmitConfirmationDialog(mockQuizState, jest.fn(), jest.fn());
            const title = dialog.querySelector('h2');
            
            expect(title.textContent).toBe('Submit Quiz?');
        });
        
        test('shows unanswered questions warning', () => {
            const dialog = createSubmitConfirmationDialog(mockQuizState, jest.fn(), jest.fn());
            const warning = dialog.querySelector('.warning-box');
            
            expect(warning).toBeTruthy();
            expect(warning.textContent).toContain('2 Unanswered Questions');
            expect(warning.textContent).toContain('2, 4');
        });
        
        test('shows flagged questions info', () => {
            const dialog = createSubmitConfirmationDialog(mockQuizState, jest.fn(), jest.fn());
            const info = dialog.querySelector('.info-box');
            
            expect(info).toBeTruthy();
            expect(info.textContent).toContain('1 Flagged Question');
            expect(info.textContent).toContain('3');
        });
        
        test('includes action buttons', () => {
            const dialog = createSubmitConfirmationDialog(mockQuizState, jest.fn(), jest.fn());
            const buttons = dialog.querySelectorAll('.modal-actions button');
            
            expect(buttons).toHaveLength(2);
            expect(buttons[0].textContent).toBe('Go Back');
            expect(buttons[1].textContent).toBe('Submit Quiz');
        });
        
        test('validates quizState parameter', () => {
            const dialog = createSubmitConfirmationDialog(null, jest.fn(), jest.fn());
            expect(dialog).toBeNull();
        });
        
        test('handles all questions answered', () => {
            const allAnsweredState = {
                questions: [{ id: 1 }, { id: 2 }],
                userAnswers: [0, 1],
                flaggedQuestions: []
            };
            
            const dialog = createSubmitConfirmationDialog(allAnsweredState, jest.fn(), jest.fn());
            const warning = dialog.querySelector('.warning-box');
            
            expect(warning).toBeFalsy();
        });
        
        test('handles no flagged questions', () => {
            const noFlaggedState = {
                questions: [{ id: 1 }, { id: 2 }],
                userAnswers: [0, null],
                flaggedQuestions: []
            };
            
            const dialog = createSubmitConfirmationDialog(noFlaggedState, jest.fn(), jest.fn());
            const info = dialog.querySelector('.info-box');
            
            expect(info).toBeFalsy();
        });
    });
});

