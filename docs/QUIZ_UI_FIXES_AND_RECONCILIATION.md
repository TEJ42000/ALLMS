# Quiz UI Fixes and Reconciliation

**Related:** Issue #157, PR #175  
**Priority:** CRITICAL

---

## MUST FIX Items

### 1. ✅ Fix XSS Vulnerability in createQuestionNav()

**Issue:** Template literals with unescaped user input

**UNSAFE Code:**
```javascript
// ❌ VULNERABLE - Direct template literal injection
function createQuestionNav() {
    const nav = document.createElement('div');
    nav.className = 'question-nav-sidebar';
    nav.innerHTML = `
        <h4>Questions</h4>
        <div class="question-nav-grid">
            ${quizState.questions.map((q, index) => `
                <button 
                    class="question-nav-btn ${getQuestionStatus(index)}"
                    data-question-index="${index}"
                    aria-label="Go to question ${index + 1}"
                >
                    ${index + 1}
                </button>
            `).join('')}
        </div>
    `;
    return nav;
}
```

**SAFE Code:**
```javascript
// ✅ SAFE - Use DOM methods instead of innerHTML
function createQuestionNav() {
    const nav = document.createElement('div');
    nav.className = 'question-nav-sidebar';
    
    const title = document.createElement('h4');
    title.textContent = 'Questions';
    nav.appendChild(title);
    
    const grid = document.createElement('div');
    grid.className = 'question-nav-grid';
    
    quizState.questions.forEach((q, index) => {
        const button = document.createElement('button');
        button.className = `question-nav-btn ${getQuestionStatus(index)}`;
        button.setAttribute('data-question-index', index);
        button.setAttribute('aria-label', `Go to question ${index + 1}`);
        button.textContent = index + 1;
        grid.appendChild(button);
    });
    
    nav.appendChild(grid);
    return nav;
}
```

---

### 2. ✅ Remove Inline onclick from Error Fallback UI

**Issue:** CSP violation with inline event handlers

**UNSAFE Code:**
```javascript
// ❌ CSP VIOLATION - Inline onclick
quizContainer.innerHTML = `
    <div class="error-state">
        <h3>Unable to load question</h3>
        <p>There was a problem loading this question.</p>
        <button onclick="location.reload()" class="btn-primary">
            Reload Quiz
        </button>
    </div>
`;
```

**SAFE Code:**
```javascript
// ✅ SAFE - Event listener
quizContainer.innerHTML = `
    <div class="error-state">
        <h3>Unable to load question</h3>
        <p>There was a problem loading this question.</p>
        <button id="reload-quiz-btn" class="btn-primary">
            Reload Quiz
        </button>
    </div>
`;

// Add event listener after DOM insertion
const reloadBtn = document.getElementById('reload-quiz-btn');
if (reloadBtn) {
    reloadBtn.addEventListener('click', () => location.reload());
}
```

---

### 3. ✅ Add flagQuestion() Implementation with Validation

**Complete Implementation:**
```javascript
/**
 * Flag or unflag a question for review
 * @param {number} questionIndex - Index of question to flag
 * @param {Object} quizState - Current quiz state
 * @returns {boolean} - Success status
 */
function flagQuestion(questionIndex, quizState) {
    // Validate quiz state
    if (!quizState || !Array.isArray(quizState.questions)) {
        console.error('Invalid quiz state');
        return false;
    }
    
    // Validate question index type
    if (typeof questionIndex !== 'number' || !Number.isInteger(questionIndex)) {
        console.error('Question index must be an integer');
        return false;
    }
    
    // Validate bounds
    if (questionIndex < 0 || questionIndex >= quizState.questions.length) {
        console.error(`Question index ${questionIndex} out of bounds (0-${quizState.questions.length - 1})`);
        return false;
    }
    
    // Initialize flaggedQuestions array if it doesn't exist
    if (!Array.isArray(quizState.flaggedQuestions)) {
        quizState.flaggedQuestions = [];
    }
    
    // Toggle flag
    const flagIndex = quizState.flaggedQuestions.indexOf(questionIndex);
    if (flagIndex > -1) {
        // Unflag
        quizState.flaggedQuestions.splice(flagIndex, 1);
    } else {
        // Flag
        quizState.flaggedQuestions.push(questionIndex);
    }
    
    // Update UI
    updateQuestionNavigation();
    
    // Persist to backend (optional)
    if (quizState.quizId) {
        saveFlaggedQuestions(quizState.quizId, quizState.flaggedQuestions);
    }
    
    return true;
}

/**
 * Get status classes for a question in navigation
 * @param {number} index - Question index
 * @param {Object} quizState - Current quiz state
 * @returns {string} - Space-separated class names
 */
function getQuestionStatus(index, quizState) {
    const classes = [];
    
    if (index === quizState.currentQuestionIndex) {
        classes.push('current');
    }
    
    if (quizState.userAnswers && quizState.userAnswers[index] !== null && quizState.userAnswers[index] !== undefined) {
        classes.push('answered');
    }
    
    if (Array.isArray(quizState.flaggedQuestions) && quizState.flaggedQuestions.includes(index)) {
        classes.push('flagged');
    }
    
    return classes.join(' ');
}

/**
 * Save flagged questions to backend
 * @param {string} quizId - Quiz ID
 * @param {number[]} flaggedQuestions - Array of flagged question indices
 */
async function saveFlaggedQuestions(quizId, flaggedQuestions) {
    try {
        await fetch(`${API_BASE}/api/quiz/${quizId}/flags`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken(),
                'X-User-ID': getUserId()
            },
            body: JSON.stringify({ flagged_questions: flaggedQuestions })
        });
    } catch (error) {
        console.error('Error saving flagged questions:', error);
        // Don't throw - flagging is not critical
    }
}
```

---

### 4. ✅ Update Test Framework from Python pytest to JavaScript

**Issue:** Tests should be in JavaScript, not Python

**Correct Test Framework:** Jest or Vitest

**Example Test (Jest):**
```javascript
// tests/quiz-navigation.test.js
import { flagQuestion, getQuestionStatus } from '../app/static/js/quiz-navigation';

describe('Quiz Navigation', () => {
    describe('flagQuestion', () => {
        let quizState;
        
        beforeEach(() => {
            quizState = {
                questions: [
                    { id: 1, text: 'Q1' },
                    { id: 2, text: 'Q2' },
                    { id: 3, text: 'Q3' }
                ],
                currentQuestionIndex: 0,
                userAnswers: [null, null, null],
                flaggedQuestions: []
            };
        });
        
        test('flags a valid question', () => {
            const result = flagQuestion(1, quizState);
            
            expect(result).toBe(true);
            expect(quizState.flaggedQuestions).toContain(1);
        });
        
        test('rejects out of bounds index', () => {
            const result = flagQuestion(10, quizState);
            
            expect(result).toBe(false);
            expect(quizState.flaggedQuestions).toHaveLength(0);
        });
        
        test('rejects negative index', () => {
            const result = flagQuestion(-1, quizState);
            
            expect(result).toBe(false);
        });
        
        test('rejects non-integer index', () => {
            const result = flagQuestion(1.5, quizState);
            
            expect(result).toBe(false);
        });
        
        test('toggles flag on second call', () => {
            flagQuestion(1, quizState);
            expect(quizState.flaggedQuestions).toContain(1);
            
            flagQuestion(1, quizState);
            expect(quizState.flaggedQuestions).not.toContain(1);
        });
    });
    
    describe('getQuestionStatus', () => {
        test('returns current class for current question', () => {
            const quizState = {
                currentQuestionIndex: 1,
                userAnswers: [null, null, null],
                flaggedQuestions: []
            };
            
            const status = getQuestionStatus(1, quizState);
            expect(status).toContain('current');
        });
        
        test('returns answered class for answered question', () => {
            const quizState = {
                currentQuestionIndex: 0,
                userAnswers: [null, 2, null],
                flaggedQuestions: []
            };
            
            const status = getQuestionStatus(1, quizState);
            expect(status).toContain('answered');
        });
        
        test('returns flagged class for flagged question', () => {
            const quizState = {
                currentQuestionIndex: 0,
                userAnswers: [null, null, null],
                flaggedQuestions: [1]
            };
            
            const status = getQuestionStatus(1, quizState);
            expect(status).toContain('flagged');
        });
    });
});
```

**Integration Test (Playwright):**
```javascript
// tests/e2e/quiz-flow.spec.js
import { test, expect } from '@playwright/test';

test.describe('Quiz Flow', () => {
    test('user can complete entire quiz', async ({ page }) => {
        await page.goto('/courses/echr/study-portal');
        
        // Start quiz
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Answer all questions
        const totalQuestions = await page.locator('#quiz-total').textContent();
        for (let i = 0; i < parseInt(totalQuestions); i++) {
            await page.click('.quiz-option:first-child');
            if (i < parseInt(totalQuestions) - 1) {
                await page.click('#next-question-btn');
            }
        }
        
        // Verify results displayed
        await expect(page.locator('.quiz-results')).toBeVisible();
        await expect(page.locator('.score-display')).toContainText('%');
    });
    
    test('user can flag questions for review', async ({ page }) => {
        await page.goto('/courses/echr/study-portal');
        await page.click('#start-quiz-btn');
        
        // Flag first question
        await page.click('.flag-question-btn');
        await expect(page.locator('.flag-question-btn')).toHaveClass(/flagged/);
        
        // Navigate to next question
        await page.click('#next-question-btn');
        
        // Open navigation sidebar
        await page.click('.question-nav-toggle');
        
        // Verify first question is marked as flagged
        await expect(page.locator('.question-nav-btn[data-question-index="0"]')).toHaveClass(/flagged/);
    });
});
```

---

### 5. ✅ Update Database Schema for Firestore

**Issue:** SQL schema provided, but app uses Firestore

**Firestore Collections:**

```javascript
// Collection: quizzes
// Document ID: {quizId}
{
    id: string,
    courseId: string,
    userId: string,
    topic: string,
    difficulty: 'easy' | 'medium' | 'hard',
    numQuestions: number,
    questions: [
        {
            id: string,
            text: string,
            options: string[],
            correct_index: number,
            difficulty: string,
            explanation: string (optional)
        }
    ],
    createdAt: Timestamp,
    updatedAt: Timestamp
}

// Collection: quiz_results
// Document ID: {resultId}
{
    id: string,
    quizId: string,
    userId: string,
    courseId: string,
    score: number,
    totalQuestions: number,
    correctAnswers: number,
    userAnswers: number[],
    flaggedQuestions: number[],
    timeTaken: number (seconds),
    completedAt: Timestamp,
    percentage: number
}

// Collection: quiz_flags
// Document ID: {quizId}_{userId}
{
    quizId: string,
    userId: string,
    flaggedQuestions: number[],
    updatedAt: Timestamp
}
```

**Firestore Security Rules:**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Quiz documents
    match /quizzes/{quizId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null && request.resource.data.userId == request.auth.uid;
      allow update, delete: if request.auth != null && resource.data.userId == request.auth.uid;
    }
    
    // Quiz results
    match /quiz_results/{resultId} {
      allow read: if request.auth != null && resource.data.userId == request.auth.uid;
      allow create: if request.auth != null && request.resource.data.userId == request.auth.uid;
    }
    
    // Quiz flags
    match /quiz_flags/{flagId} {
      allow read, write: if request.auth != null && resource.data.userId == request.auth.uid;
    }
  }
}
```

---

## Comparison with Existing Implementation

### What Already Exists in app.js

**✅ Implemented:**
1. Quiz generation (`generateQuiz()`)
2. Question display (`displayCurrentQuestion()`)
3. Answer selection with validation (`selectAnswer()`)
4. Navigation (previous/next) (`previousQuestion()`, `nextQuestion()`)
5. Results display (`displayQuizResults()`)
6. Quiz review mode (`reviewQuiz()`)
7. Event delegation (`handleQuizContainerClick()`)
8. XSS prevention (`escapeHtml()` usage)
9. Array bounds checking
10. Saved quizzes (`loadSavedQuizzes()`, `startSavedQuiz()`)
11. Quiz history (`loadQuizHistory()`)
12. Result submission (`submitQuizResults()`)

**❌ Missing (from Issue #157):**
1. Question type indicator
2. Timer display (for timed quizzes)
3. Visual progress bar (only text progress exists)
4. Flag for review functionality
5. Question navigation sidebar
6. Confirmation dialog before submission
7. XP earned display in results
8. Comprehensive keyboard navigation
9. Screen reader announcements
10. Mobile swipe gestures

### API Endpoints - Existing vs Planned

**Existing Endpoints (from app.js):**
```
GET  /api/quizzes/courses/{courseId}           - List saved quizzes
POST /api/quizzes/courses/{courseId}           - Create new quiz
GET  /api/quizzes/courses/{courseId}/{quizId}  - Get specific quiz
GET  /api/quizzes/history/{userId}             - Get quiz history
POST /api/quizzes/submit                       - Submit quiz results
```

**Planned Endpoints (from implementation plan):**
```
POST /api/quiz/start                           - Start quiz (REDUNDANT)
POST /api/quiz/{quiz_id}/answer                - Submit answer (NEW)
POST /api/quiz/{quiz_id}/flag                  - Flag question (NEW)
POST /api/quiz/{quiz_id}/submit                - Submit quiz (REDUNDANT)
GET  /api/quiz/{quiz_id}/state                 - Get quiz state (NEW)
```

**Reconciliation:**
- Use existing `/api/quizzes/courses/{courseId}` for quiz creation
- Add `/api/quiz/{quiz_id}/flags` for flagging (NEW)
- Use existing `/api/quizzes/submit` for submission
- Add `/api/quiz/{quiz_id}/state` for state persistence (NEW)

---

**Status:** Fixes Documented - Ready for Implementation

