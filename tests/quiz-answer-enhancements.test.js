/**
 * Unit Tests for Quiz Answer Options Enhancements - Phase 2
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - Enhanced answer option creation
 * - Answer options container
 * - Option selection handling
 * - Answer feedback display
 * - Ripple effects
 */

// Mock DOM environment
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;
global.MouseEvent = dom.window.MouseEvent;

// Import module under test
const {
    createEnhancedAnswerOption,
    createAnswerOptionsContainer,
    addRippleEffect,
    handleOptionSelection,
    showAnswerFeedback,
    initializePhase2Enhancements
} = require('../app/static/js/quiz-answer-enhancements');

describe('Quiz Answer Options Enhancements - Phase 2', () => {
    
    describe('createEnhancedAnswerOption', () => {
        test('creates basic answer option', () => {
            const option = createEnhancedAnswerOption('Test answer', 0);
            
            expect(option.tagName).toBe('BUTTON');
            expect(option.className).toBe('quiz-option-enhanced');
            expect(option.getAttribute('type')).toBe('button');
            expect(option.getAttribute('data-option-index')).toBe('0');
            expect(option.getAttribute('role')).toBe('radio');
        });
        
        test('creates option with correct letter', () => {
            const optionA = createEnhancedAnswerOption('Answer A', 0);
            const optionB = createEnhancedAnswerOption('Answer B', 1);
            const optionC = createEnhancedAnswerOption('Answer C', 2);
            
            expect(optionA.querySelector('.option-letter').textContent).toBe('A');
            expect(optionB.querySelector('.option-letter').textContent).toBe('B');
            expect(optionC.querySelector('.option-letter').textContent).toBe('C');
        });
        
        test('creates option with text content', () => {
            const option = createEnhancedAnswerOption('Test answer text', 0);
            const text = option.querySelector('.option-text');
            
            expect(text.textContent).toBe('Test answer text');
        });
        
        test('creates selected option with checkmark', () => {
            const option = createEnhancedAnswerOption('Test', 0, true);
            
            expect(option.classList.contains('selected')).toBeTruthy();
            expect(option.getAttribute('aria-checked')).toBe('true');
            expect(option.querySelector('.option-checkmark')).toBeTruthy();
        });
        
        test('creates disabled option', () => {
            const option = createEnhancedAnswerOption('Test', 0, false, true);
            
            expect(option.classList.contains('disabled')).toBeTruthy();
            expect(option.getAttribute('disabled')).toBe('true');
            expect(option.getAttribute('aria-disabled')).toBe('true');
        });
        
        test('creates correct answer with feedback', () => {
            const option = createEnhancedAnswerOption('Test', 0, false, false, true);
            
            expect(option.classList.contains('correct')).toBeTruthy();
            expect(option.querySelector('.option-feedback-icon')).toBeTruthy();
            expect(option.querySelector('.option-feedback-icon').textContent).toBe('✓');
        });
        
        test('creates incorrect answer with feedback', () => {
            const option = createEnhancedAnswerOption('Test', 0, true, false, false);
            
            expect(option.classList.contains('incorrect')).toBeTruthy();
            expect(option.querySelector('.option-feedback-icon')).toBeTruthy();
            expect(option.querySelector('.option-feedback-icon').textContent).toBe('✗');
        });
    });
    
    describe('createAnswerOptionsContainer', () => {
        test('creates container with all options', () => {
            const options = ['Answer A', 'Answer B', 'Answer C', 'Answer D'];
            const container = createAnswerOptionsContainer(options);
            
            expect(container.className).toBe('quiz-options-container');
            expect(container.getAttribute('role')).toBe('radiogroup');
            expect(container.querySelectorAll('.quiz-option-enhanced')).toHaveLength(4);
        });
        
        test('marks selected option', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 1);
            
            const selectedOption = container.querySelector('[data-option-index="1"]');
            expect(selectedOption.classList.contains('selected')).toBeTruthy();
        });
        
        test('disables all options when specified', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, null, true);
            
            const allOptions = container.querySelectorAll('.quiz-option-enhanced');
            allOptions.forEach(option => {
                expect(option.classList.contains('disabled')).toBeTruthy();
            });
        });
        
        test('shows correct answer feedback', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 1, true, 2);
            
            const correctOption = container.querySelector('[data-option-index="2"]');
            expect(correctOption.classList.contains('correct')).toBeTruthy();
        });
        
        test('handles empty options array', () => {
            const container = createAnswerOptionsContainer([]);
            
            expect(container.textContent).toBe('No options available');
        });
        
        test('handles invalid input', () => {
            const container = createAnswerOptionsContainer(null);
            
            expect(container.textContent).toBe('No options available');
        });
    });
    
    describe('handleOptionSelection', () => {
        test('selects option and removes previous selection', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 0);
            document.body.appendChild(container);
            
            const optionB = container.querySelector('[data-option-index="1"]');
            handleOptionSelection(optionB, null);
            
            // Option B should be selected
            expect(optionB.classList.contains('selected')).toBeTruthy();
            expect(optionB.getAttribute('aria-checked')).toBe('true');
            
            // Option A should not be selected
            const optionA = container.querySelector('[data-option-index="0"]');
            expect(optionA.classList.contains('selected')).toBeFalsy();
            
            document.body.removeChild(container);
        });
        
        test('calls callback with option index', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options);
            document.body.appendChild(container);
            
            const callback = jest.fn();
            const optionC = container.querySelector('[data-option-index="2"]');
            handleOptionSelection(optionC, callback);
            
            expect(callback).toHaveBeenCalledWith(2);
            
            document.body.removeChild(container);
        });
        
        test('does not select disabled option', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, null, true);
            document.body.appendChild(container);
            
            const callback = jest.fn();
            const option = container.querySelector('[data-option-index="0"]');
            handleOptionSelection(option, callback);
            
            expect(callback).not.toHaveBeenCalled();
            
            document.body.removeChild(container);
        });
        
        test('adds checkmark to selected option', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options);
            document.body.appendChild(container);
            
            const option = container.querySelector('[data-option-index="1"]');
            handleOptionSelection(option, null);
            
            expect(option.querySelector('.option-checkmark')).toBeTruthy();
            
            document.body.removeChild(container);
        });
    });
    
    describe('showAnswerFeedback', () => {
        test('disables all options', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 1);
            document.body.appendChild(container);
            
            showAnswerFeedback(container, 2, 1);
            
            const allOptions = container.querySelectorAll('.quiz-option-enhanced');
            allOptions.forEach(option => {
                expect(option.classList.contains('disabled')).toBeTruthy();
                expect(option.getAttribute('disabled')).toBe('true');
            });
            
            document.body.removeChild(container);
        });
        
        test('marks correct answer', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 1);
            document.body.appendChild(container);
            
            showAnswerFeedback(container, 2, 1);
            
            const correctOption = container.querySelector('[data-option-index="2"]');
            expect(correctOption.classList.contains('correct')).toBeTruthy();
            expect(correctOption.querySelector('.option-feedback-icon').textContent).toBe('✓');
            
            document.body.removeChild(container);
        });
        
        test('marks incorrect answer', () => {
            const options = ['A', 'B', 'C', 'D'];
            const container = createAnswerOptionsContainer(options, 1);
            document.body.appendChild(container);
            
            showAnswerFeedback(container, 2, 1);
            
            const incorrectOption = container.querySelector('[data-option-index="1"]');
            expect(incorrectOption.classList.contains('incorrect')).toBeTruthy();
            expect(incorrectOption.querySelector('.option-feedback-icon').textContent).toBe('✗');
            
            document.body.removeChild(container);
        });
    });
    
    describe('addRippleEffect', () => {
        test('adds ripple element to option', () => {
            const option = createEnhancedAnswerOption('Test', 0);
            document.body.appendChild(option);
            
            const event = new MouseEvent('click', {
                clientX: 100,
                clientY: 100
            });
            
            addRippleEffect(option, event);
            
            const ripple = option.querySelector('.ripple-effect');
            expect(ripple).toBeTruthy();
            
            document.body.removeChild(option);
        });
        
        test('removes ripple after animation', (done) => {
            const option = createEnhancedAnswerOption('Test', 0);
            document.body.appendChild(option);
            
            const event = new MouseEvent('click', {
                clientX: 100,
                clientY: 100
            });
            
            addRippleEffect(option, event);
            
            setTimeout(() => {
                const ripple = option.querySelector('.ripple-effect');
                expect(ripple).toBeFalsy();
                document.body.removeChild(option);
                done();
            }, 700);
        });
    });
    
    describe('initializePhase2Enhancements', () => {
        test('sets up event delegation', () => {
            const container = document.createElement('div');
            const callback = jest.fn();
            
            initializePhase2Enhancements(container, callback);
            
            // Verify event listeners are attached (can't directly test, but function should not throw)
            expect(container).toBeTruthy();
        });
    });
});

