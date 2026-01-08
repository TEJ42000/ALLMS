/**
 * Unit Tests for Quiz Display Enhancements - Phase 1
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - Question type badge creation
 * - Progress bar functionality
 * - Timer functionality
 * - Enhanced header creation
 * - Animations
 */

// Mock DOM environment
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;

// Import module under test
const {
    createQuestionTypeBadge,
    createProgressBar,
    QuizTimer,
    createTimerDisplay,
    updateProgressBar,
    createEnhancedQuestionHeader,
    addFadeInAnimation
} = require('../app/static/js/quiz-display-enhancements');

describe('Quiz Display Enhancements - Phase 1', () => {
    
    describe('createQuestionTypeBadge', () => {
        test('creates badge for multiple choice question', () => {
            const badge = createQuestionTypeBadge('multiple_choice');
            
            expect(badge.tagName).toBe('SPAN');
            expect(badge.className).toBe('question-type-badge');
            expect(badge.textContent).toBe('Multiple Choice');
            expect(badge.getAttribute('aria-label')).toBe('Question type: Multiple Choice');
        });
        
        test('creates badge for true/false question', () => {
            const badge = createQuestionTypeBadge('true_false');
            
            expect(badge.textContent).toBe('True/False');
            expect(badge.getAttribute('aria-label')).toBe('Question type: True/False');
        });
        
        test('creates badge for short answer question', () => {
            const badge = createQuestionTypeBadge('short_answer');
            
            expect(badge.textContent).toBe('Short Answer');
        });
        
        test('defaults to multiple choice for unknown type', () => {
            const badge = createQuestionTypeBadge('unknown_type');
            
            expect(badge.textContent).toBe('Multiple Choice');
        });
    });
    
    describe('createProgressBar', () => {
        test('creates progress bar with correct structure', () => {
            const progressBar = createProgressBar(0, 10);
            
            expect(progressBar.className).toBe('quiz-progress-bar');
            expect(progressBar.getAttribute('role')).toBe('progressbar');
            expect(progressBar.getAttribute('aria-valuenow')).toBe('1');
            expect(progressBar.getAttribute('aria-valuemin')).toBe('1');
            expect(progressBar.getAttribute('aria-valuemax')).toBe('10');
        });
        
        test('calculates correct percentage for first question', () => {
            const progressBar = createProgressBar(0, 10);
            const fill = progressBar.querySelector('.quiz-progress-fill');
            
            expect(fill.style.width).toBe('10%');
        });
        
        test('calculates correct percentage for middle question', () => {
            const progressBar = createProgressBar(4, 10);
            const fill = progressBar.querySelector('.quiz-progress-fill');
            
            expect(fill.style.width).toBe('50%');
        });
        
        test('calculates correct percentage for last question', () => {
            const progressBar = createProgressBar(9, 10);
            const fill = progressBar.querySelector('.quiz-progress-fill');
            
            expect(fill.style.width).toBe('100%');
        });
        
        test('has transition for smooth animation', () => {
            const progressBar = createProgressBar(0, 10);
            const fill = progressBar.querySelector('.quiz-progress-fill');
            
            expect(fill.style.transition).toContain('width');
            expect(fill.style.transition).toContain('ease');
        });
    });
    
    describe('QuizTimer', () => {
        beforeEach(() => {
            jest.useFakeTimers();
        });
        
        afterEach(() => {
            jest.useRealTimers();
        });
        
        test('initializes with correct time limit', () => {
            const timer = new QuizTimer(300, null, null);
            
            expect(timer.timeLimit).toBe(300);
            expect(timer.timeRemaining).toBe(300);
        });
        
        test('counts down when started', () => {
            const onTick = jest.fn();
            const timer = new QuizTimer(10, onTick, null);
            
            timer.start();
            jest.advanceTimersByTime(3000);
            
            expect(timer.timeRemaining).toBe(7);
            expect(onTick).toHaveBeenCalledTimes(3);
        });
        
        test('calls onExpire when time runs out', () => {
            const onExpire = jest.fn();
            const timer = new QuizTimer(3, null, onExpire);
            
            timer.start();
            jest.advanceTimersByTime(3000);
            
            expect(onExpire).toHaveBeenCalledTimes(1);
            expect(timer.timeRemaining).toBe(0);
        });
        
        test('stops timer correctly', () => {
            const onTick = jest.fn();
            const timer = new QuizTimer(10, onTick, null);
            
            timer.start();
            jest.advanceTimersByTime(2000);
            timer.stop();
            jest.advanceTimersByTime(2000);
            
            expect(timer.timeRemaining).toBe(8);
            expect(onTick).toHaveBeenCalledTimes(2);
        });
        
        test('pauses and resumes correctly', () => {
            const timer = new QuizTimer(10, null, null);
            
            timer.start();
            jest.advanceTimersByTime(2000);
            timer.pause();
            jest.advanceTimersByTime(2000);
            timer.resume();
            jest.advanceTimersByTime(2000);
            
            expect(timer.timeRemaining).toBe(6);
        });
        
        test('formats time correctly (minutes:seconds)', () => {
            const timer = new QuizTimer(125, null, null);
            
            expect(timer.getFormattedTime()).toBe('2:05');
        });
        
        test('formats time with leading zero for seconds', () => {
            const timer = new QuizTimer(65, null, null);
            
            expect(timer.getFormattedTime()).toBe('1:05');
        });
        
        test('does not start multiple intervals', () => {
            const timer = new QuizTimer(10, null, null);
            
            timer.start();
            timer.start();
            timer.start();
            
            jest.advanceTimersByTime(1000);
            
            expect(timer.timeRemaining).toBe(9);
        });
    });
    
    describe('updateProgressBar', () => {
        test('updates progress bar width', () => {
            const progressBar = createProgressBar(0, 10);
            
            updateProgressBar(progressBar, 4, 10);
            
            const fill = progressBar.querySelector('.quiz-progress-fill');
            expect(fill.style.width).toBe('50%');
        });
        
        test('updates ARIA attributes', () => {
            const progressBar = createProgressBar(0, 10);
            
            updateProgressBar(progressBar, 4, 10);
            
            expect(progressBar.getAttribute('aria-valuenow')).toBe('5');
            expect(progressBar.getAttribute('aria-label')).toBe('Question 5 of 10');
        });
        
        test('handles missing fill element gracefully', () => {
            const progressBar = document.createElement('div');
            
            expect(() => {
                updateProgressBar(progressBar, 4, 10);
            }).not.toThrow();
        });
    });
    
    describe('createEnhancedQuestionHeader', () => {
        test('creates header with all components', () => {
            const question = {
                type: 'multiple_choice',
                difficulty: 'medium'
            };
            
            const header = createEnhancedQuestionHeader(question, 1, 10, null);
            
            expect(header.className).toBe('question-header-enhanced');
            expect(header.querySelector('h3').textContent).toBe('Question 1');
            expect(header.querySelector('.question-type-badge')).toBeTruthy();
            expect(header.querySelector('.difficulty-badge')).toBeTruthy();
            expect(header.querySelector('.quiz-progress-bar')).toBeTruthy();
        });
        
        test('includes timer when provided', () => {
            const question = { type: 'multiple_choice' };
            const timer = new QuizTimer(300, null, null);
            
            const header = createEnhancedQuestionHeader(question, 1, 10, timer);
            
            expect(header.querySelector('.quiz-timer')).toBeTruthy();
        });
        
        test('works without timer', () => {
            const question = { type: 'multiple_choice' };
            
            const header = createEnhancedQuestionHeader(question, 1, 10, null);
            
            expect(header.querySelector('.quiz-timer')).toBeFalsy();
        });
        
        test('works without difficulty', () => {
            const question = { type: 'multiple_choice' };
            
            const header = createEnhancedQuestionHeader(question, 1, 10, null);
            
            expect(header.querySelector('.difficulty-badge')).toBeFalsy();
        });
    });
    
    describe('addFadeInAnimation', () => {
        test('sets initial opacity and transform', () => {
            const element = document.createElement('div');
            
            addFadeInAnimation(element);
            
            expect(element.style.opacity).toBe('1');
            expect(element.style.transform).toBe('translateY(0)');
        });
        
        test('adds transition property', () => {
            const element = document.createElement('div');
            
            addFadeInAnimation(element);
            
            expect(element.style.transition).toContain('opacity');
            expect(element.style.transition).toContain('transform');
        });
    });
});

