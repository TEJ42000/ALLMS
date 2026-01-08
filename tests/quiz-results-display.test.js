/**
 * Unit Tests for Quiz Results Display - Phase 4
 * 
 * Test Framework: Jest
 * Coverage Target: 80%+
 * 
 * Tests:
 * - XP display creation
 * - XP counter animation
 * - Statistics display
 * - Review mode
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
global.requestAnimationFrame = (callback) => setTimeout(callback, 16);

// Import module under test
const {
    createXPDisplay,
    animateXPCounter,
    createStatisticsDisplay,
    createStatCard,
    formatTime,
    createReviewMode,
    createReviewQuestionCard
} = require('../app/static/js/quiz-results-display');

describe('Quiz Results Display - Phase 4', () => {
    
    describe('createXPDisplay', () => {
        test('creates XP display element', () => {
            const xpDisplay = createXPDisplay(100, 50, 1, 100);
            
            expect(xpDisplay.className).toBe('xp-display');
            expect(xpDisplay.getAttribute('role')).toBe('status');
            expect(xpDisplay.getAttribute('aria-live')).toBe('polite');
        });
        
        test('displays XP earned section', () => {
            const xpDisplay = createXPDisplay(100);
            const xpValue = xpDisplay.querySelector('.xp-value');
            
            expect(xpValue).toBeTruthy();
            expect(xpValue.getAttribute('data-target-xp')).toBe('100');
            expect(xpValue.textContent).toBe('0');
        });
        
        test('displays level progress section', () => {
            const xpDisplay = createXPDisplay(100, 50, 1, 100);
            const levelLabel = xpDisplay.querySelector('.level-label');
            const progressBar = xpDisplay.querySelector('.level-progress-bar');
            
            expect(levelLabel.textContent).toBe('Level 1');
            expect(progressBar).toBeTruthy();
            expect(progressBar.getAttribute('aria-valuenow')).toBe('50');
            expect(progressBar.getAttribute('aria-valuemax')).toBe('100');
        });
        
        test('calculates progress percentage correctly', () => {
            const xpDisplay = createXPDisplay(100, 50, 1, 100);
            const progressFill = xpDisplay.querySelector('.level-progress-fill');
            
            expect(progressFill.style.width).toBe('50%');
        });
        
        test('validates xpEarned parameter', () => {
            const xpDisplay = createXPDisplay(-10);
            const xpValue = xpDisplay.querySelector('.xp-value');
            
            expect(xpValue.getAttribute('data-target-xp')).toBe('0');
        });
        
        test('validates currentLevel parameter', () => {
            const xpDisplay = createXPDisplay(100, 50, 0, 100);
            const levelLabel = xpDisplay.querySelector('.level-label');
            
            expect(levelLabel.textContent).toBe('Level 1');
        });
    });
    
    describe('animateXPCounter', () => {
        test('animates XP counter', (done) => {
            const xpValue = document.createElement('div');
            xpValue.setAttribute('data-target-xp', '100');
            xpValue.textContent = '0';
            
            animateXPCounter(xpValue, 100);
            
            setTimeout(() => {
                const currentValue = parseInt(xpValue.textContent, 10);
                expect(currentValue).toBeGreaterThan(0);
                done();
            }, 150);
        });
        
        test('validates xpElement parameter', () => {
            expect(() => animateXPCounter(null, 100)).not.toThrow();
            expect(() => animateXPCounter('not an element', 100)).not.toThrow();
        });
    });
    
    describe('createStatisticsDisplay', () => {
        const mockStats = {
            score: 8,
            total: 10,
            timeTaken: 125,
            answered: 10
        };
        
        test('creates statistics display', () => {
            const statsDisplay = createStatisticsDisplay(mockStats);
            
            expect(statsDisplay.className).toBe('quiz-statistics');
            expect(statsDisplay.querySelector('h3').textContent).toBe('Quiz Statistics');
        });
        
        test('displays score card', () => {
            const statsDisplay = createStatisticsDisplay(mockStats);
            const statCards = statsDisplay.querySelectorAll('.stat-card');
            
            expect(statCards.length).toBeGreaterThan(0);
        });
        
        test('calculates accuracy correctly', () => {
            const statsDisplay = createStatisticsDisplay(mockStats);
            const statValues = Array.from(statsDisplay.querySelectorAll('.stat-value'))
                .map(el => el.textContent);
            
            expect(statValues).toContain('80%');
        });
        
        test('formats time correctly', () => {
            const statsDisplay = createStatisticsDisplay(mockStats);
            const statValues = Array.from(statsDisplay.querySelectorAll('.stat-value'))
                .map(el => el.textContent);
            
            expect(statValues).toContain('2m 5s');
        });
        
        test('validates stats parameter', () => {
            const statsDisplay = createStatisticsDisplay(null);
            
            expect(statsDisplay.textContent).toBe('Statistics unavailable');
        });
    });
    
    describe('createStatCard', () => {
        test('creates stat card', () => {
            const card = createStatCard('Score', '8 / 10', 'score-icon', '📊');
            
            expect(card.className).toBe('stat-card');
            expect(card.querySelector('.stat-label').textContent).toBe('Score');
            expect(card.querySelector('.stat-value').textContent).toBe('8 / 10');
            expect(card.querySelector('.stat-icon').textContent).toBe('📊');
        });
    });
    
    describe('formatTime', () => {
        test('formats seconds only', () => {
            expect(formatTime(45)).toBe('45s');
        });
        
        test('formats minutes and seconds', () => {
            expect(formatTime(125)).toBe('2m 5s');
        });
        
        test('formats hours, minutes, and seconds', () => {
            expect(formatTime(3665)).toBe('1h 1m 5s');
        });
        
        test('handles zero', () => {
            expect(formatTime(0)).toBe('0s');
        });
        
        test('handles negative numbers', () => {
            expect(formatTime(-10)).toBe('0s');
        });
    });
    
    describe('createReviewMode', () => {
        const mockQuestions = [
            {
                question: 'Question 1?',
                options: ['A', 'B', 'C', 'D'],
                correct_index: 0
            },
            {
                question: 'Question 2?',
                options: ['A', 'B', 'C', 'D'],
                correct_index: 1
            }
        ];
        
        const mockUserAnswers = [0, 2];
        
        test('creates review mode display', () => {
            const reviewMode = createReviewMode(mockQuestions, mockUserAnswers, jest.fn());
            
            expect(reviewMode.className).toBe('quiz-review-mode');
            expect(reviewMode.querySelector('h3').textContent).toBe('Review Your Answers');
        });
        
        test('displays all questions', () => {
            const reviewMode = createReviewMode(mockQuestions, mockUserAnswers, jest.fn());
            const questionCards = reviewMode.querySelectorAll('.review-question-card');
            
            expect(questionCards).toHaveLength(2);
        });
        
        test('marks correct answers', () => {
            const reviewMode = createReviewMode(mockQuestions, mockUserAnswers, jest.fn());
            const firstCard = reviewMode.querySelector('.review-question-card');
            
            expect(firstCard.classList.contains('correct')).toBeTruthy();
        });
        
        test('marks incorrect answers', () => {
            const reviewMode = createReviewMode(mockQuestions, mockUserAnswers, jest.fn());
            const cards = reviewMode.querySelectorAll('.review-question-card');
            const secondCard = cards[1];
            
            expect(secondCard.classList.contains('incorrect')).toBeTruthy();
        });
        
        test('validates questions parameter', () => {
            const reviewMode = createReviewMode([], mockUserAnswers, jest.fn());
            
            expect(reviewMode.textContent).toBe('No questions to review');
        });
        
        test('validates userAnswers parameter', () => {
            const reviewMode = createReviewMode(mockQuestions, null, jest.fn());
            
            expect(reviewMode.querySelectorAll('.review-question-card')).toHaveLength(2);
        });
    });
    
    describe('createReviewQuestionCard', () => {
        const mockQuestion = {
            question: 'Test question?',
            options: ['A', 'B', 'C', 'D'],
            correct_index: 0
        };
        
        test('creates correct answer card', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 0, jest.fn());
            
            expect(card.classList.contains('correct')).toBeTruthy();
            expect(card.querySelector('.review-status').textContent).toBe('✓ Correct');
        });
        
        test('creates incorrect answer card', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 1, jest.fn());
            
            expect(card.classList.contains('incorrect')).toBeTruthy();
            expect(card.querySelector('.review-status').textContent).toBe('✗ Incorrect');
        });
        
        test('displays question text', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 0, jest.fn());
            
            expect(card.querySelector('.review-question-text').textContent).toBe('Test question?');
        });
        
        test('displays user answer', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 1, jest.fn());
            
            expect(card.querySelector('.review-user-answer').textContent).toBe('Your answer: B');
        });
        
        test('displays correct answer for incorrect responses', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 1, jest.fn());
            
            expect(card.querySelector('.review-correct-answer').textContent).toBe('Correct answer: A');
        });
        
        test('does not display correct answer for correct responses', () => {
            const card = createReviewQuestionCard(mockQuestion, 0, 0, jest.fn());
            
            expect(card.querySelector('.review-correct-answer')).toBeFalsy();
        });
    });
});

