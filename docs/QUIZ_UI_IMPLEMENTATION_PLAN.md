# Quiz UI Implementation Plan

**Issue:** #157 - Complete Quiz Display UI Implementation  
**Priority:** HIGH  
**Branch:** `feature/complete-quiz-ui-157`

---

## Current State Analysis

### Existing Implementation
The quiz UI currently has:
- ✅ Basic question display with difficulty badges
- ✅ Answer options with hover effects
- ✅ Progress tracking (current/total)
- ✅ Score display
- ✅ Results screen with performance feedback
- ✅ Quiz history tracking
- ✅ Saved quizzes functionality

### Missing Features (from Issue #157)
- ❌ Question type indicator
- ❌ Timer display (for timed quizzes)
- ❌ Enhanced progress bar (visual)
- ❌ "Flag for review" functionality
- ❌ Question navigation sidebar
- ❌ Confirmation dialog before submission
- ❌ XP earned display in results
- ❌ Comprehensive accessibility features
- ❌ Mobile-optimized touch interactions
- ❌ Swipe gestures for navigation

---

## Implementation Phases

### Phase 1: Enhanced Question Display ✅ IN PROGRESS

**Files to Modify:**
- `app/static/css/styles.css` - Add new styles
- `app/static/js/app.js` - Update displayCurrentQuestion()
- `templates/index.html` - Update quiz container structure

**Features:**
1. **Question Type Indicator**
   - Display question type (Multiple Choice, True/False, etc.)
   - Visual badge similar to difficulty badge

2. **Timer Display** (Optional)
   - Countdown timer for timed quizzes
   - Visual warning when time is running low
   - Auto-submit when time expires

3. **Enhanced Progress Bar**
   - Visual progress bar (not just text)
   - Color-coded based on completion
   - Animated transitions

**Implementation:**
```css
/* Progress Bar */
.quiz-progress-bar {
    width: 100%;
    height: 8px;
    background: var(--border-color);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 20px;
}

.quiz-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--gold), var(--gold-light));
    transition: width 0.3s ease;
}

/* Question Type Badge */
.question-type-badge {
    padding: 5px 12px;
    border-radius: 15px;
    font-size: 0.8em;
    background: rgba(100, 149, 237, 0.2);
    color: #6495ED;
    font-weight: 600;
}

/* Timer Display */
.quiz-timer {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.1em;
    color: var(--text-secondary);
}

.quiz-timer.warning {
    color: var(--warning);
    animation: pulse 1s infinite;
}

.quiz-timer.danger {
    color: var(--error);
    animation: pulse 0.5s infinite;
}
```

---

### Phase 2: Improved Answer Options

**Features:**
1. **Enhanced Hover Effects**
   - Smooth transitions
   - Visual feedback
   - Accessibility-friendly

2. **Better Selected State**
   - Clear visual distinction
   - Checkmark icon
   - Disabled state after answer

3. **Answer Feedback**
   - Correct/incorrect indicators
   - Explanation display
   - Visual animations

---

### Phase 3: Navigation Controls

**Features:**
1. **Flag for Review**
   - Flag button on each question
   - Visual indicator of flagged questions
   - Review flagged questions before submission

2. **Question Navigation Sidebar**
   - Grid of question numbers
   - Click to jump to any question
   - Visual status (answered, flagged, current)
   - Collapsible on mobile

3. **Confirmation Dialog**
   - Modal before final submission
   - Show unanswered questions
   - Show flagged questions
   - Confirm or go back

**Implementation:**
```javascript
// Question Navigation Sidebar (XSS-safe)
function createQuestionNav(quizState) {
    const nav = document.createElement('div');
    nav.className = 'question-nav-sidebar';

    // Create title
    const title = document.createElement('h4');
    title.textContent = 'Questions';
    nav.appendChild(title);

    // Create grid container
    const grid = document.createElement('div');
    grid.className = 'question-nav-grid';

    // Create buttons using DOM methods (XSS-safe)
    quizState.questions.forEach((q, index) => {
        const button = document.createElement('button');
        button.className = `question-nav-btn ${getQuestionStatus(index, quizState)}`;
        button.setAttribute('data-question-index', index);
        button.setAttribute('aria-label', `Go to question ${index + 1}`);
        button.textContent = index + 1;  // Automatically escapes
        grid.appendChild(button);
    });

    nav.appendChild(grid);
    return nav;
}

function getQuestionStatus(index, quizState) {
    const classes = [];
    if (index === quizState.currentQuestionIndex) classes.push('current');
    if (quizState.userAnswers && quizState.userAnswers[index] !== null) classes.push('answered');
    if (quizState.flaggedQuestions?.includes(index)) classes.push('flagged');
    return classes.join(' ');
}
```

---

### Phase 4: Enhanced Results Display

**Features:**
1. **XP Earned Display**
   - Show XP earned from quiz
   - Animated counter
   - Level progress update

2. **Detailed Statistics**
   - Time taken
   - Accuracy percentage
   - Questions by difficulty
   - Comparison to previous attempts

3. **Better Review Mode**
   - Show all questions with answers
   - Highlight correct/incorrect
   - Show explanations
   - Jump to specific questions

---

### Phase 5: Accessibility Features

**WCAG AA Compliance:**

1. **ARIA Labels**
   ```html
   <button 
       class="quiz-option"
       role="radio"
       aria-checked="false"
       aria-label="Option A: ${optionText}"
   >
   ```

2. **Keyboard Navigation**
   - Arrow keys to navigate options
   - Enter/Space to select
   - Tab to navigate controls
   - Escape to close modals

3. **Screen Reader Support**
   - Announce question changes
   - Announce score updates
   - Announce timer warnings
   - Live regions for dynamic content

4. **Focus Management**
   - Visible focus indicators
   - Logical tab order
   - Focus trap in modals

---

### Phase 6: Mobile Responsiveness

**Features:**
1. **Touch-Friendly Buttons**
   - Minimum 44x44px touch targets
   - Increased padding on mobile
   - Larger font sizes

2. **Responsive Layout**
   - Stack navigation on mobile
   - Collapsible sidebar
   - Full-width options
   - Optimized spacing

3. **Swipe Gestures**
   - Swipe left for next question
   - Swipe right for previous question
   - Pull down to refresh
   - Touch feedback

**Implementation:**
```css
@media (max-width: 768px) {
    .quiz-question-card {
        padding: 20px;
    }
    
    .quiz-option {
        padding: 18px 15px;
        font-size: 1.05em;
        min-height: 60px;
    }
    
    .question-nav-sidebar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        transform: translateY(100%);
        transition: transform 0.3s ease;
    }
    
    .question-nav-sidebar.open {
        transform: translateY(0);
    }
}
```

---

## Testing Checklist

- [ ] All question types display correctly
- [ ] Timer functions properly (if enabled)
- [ ] Progress bar updates accurately
- [ ] Navigation sidebar works on all devices
- [ ] Flag for review persists across navigation
- [ ] Confirmation dialog shows correct information
- [ ] Results display XP earned
- [ ] Keyboard navigation works throughout
- [ ] Screen reader announces all changes
- [ ] Mobile layout is usable
- [ ] Swipe gestures work on touch devices
- [ ] All animations are smooth
- [ ] No console errors
- [ ] Passes WCAG AA validation

---

## Files to Modify

1. **`app/static/css/styles.css`** - Enhanced quiz styles
2. **`app/static/js/app.js`** - Quiz logic updates
3. **`templates/index.html`** - Quiz HTML structure
4. **`app/static/js/quiz-navigation.js`** (NEW) - Navigation sidebar logic
5. **`app/static/js/quiz-accessibility.js`** (NEW) - Accessibility features
6. **`app/static/js/quiz-mobile.js`** (NEW) - Mobile gestures

---

## Implementation Approach

**Phased Implementation:** Each phase will be completed, reviewed, and tested before proceeding to the next phase. This ensures quality and allows for feedback at each stage.

**Priority Order:**
1. Phase 1 (Enhanced Display) - Foundation
2. Phase 2 (Answer Options) - User interaction
3. Phase 3 (Navigation) - Advanced features
4. Phase 4 (Results) - Feedback
5. Phase 5 (Accessibility) - Compliance
6. Phase 6 (Mobile) - Optimization

---

## Next Steps

1. Create initial PR with this implementation plan
2. Implement Phase 1 (Enhanced Question Display)
3. Get feedback and iterate
4. Continue with subsequent phases
5. Comprehensive testing
6. Final review and merge

---

---

## Test Implementation Plan

### Unit Tests

**Test Framework:** Jest or Vitest
**Coverage Target:** 80%+ for new code

**Test Files:**
- `tests/quiz-ui-components.test.js` - Component rendering tests
- `tests/quiz-navigation.test.js` - Navigation logic tests
- `tests/quiz-accessibility.test.js` - Accessibility compliance tests
- `tests/quiz-state-management.test.js` - State management tests

**Example Unit Test (Jest):**
```javascript
// tests/quiz-navigation.test.js
import { createQuestionNav, getQuestionStatus, flagQuestion } from '../app/static/js/quiz-navigation';

describe('Question Navigation', () => {
    describe('createQuestionNav', () => {
        test('creates navigation with valid questions', () => {
            const quizState = {
                questions: [
                    { id: 1, text: 'Question 1' },
                    { id: 2, text: 'Question 2' },
                    { id: 3, text: 'Question 3' }
                ],
                currentQuestionIndex: 0,
                userAnswers: [null, null, null],
                flaggedQuestions: []
            };

            const nav = createQuestionNav(quizState);

            expect(nav).not.toBeNull();
            expect(nav.querySelectorAll('.question-nav-btn')).toHaveLength(3);
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
            expect(status).not.toContain('answered');
        });
    });

    describe('flagQuestion', () => {
        test('flags a valid question', () => {
            const quizState = {
                questions: [{}, {}, {}],
                flaggedQuestions: []
            };

            const result = flagQuestion(1, quizState);

            expect(result).toBe(true);
            expect(quizState.flaggedQuestions).toContain(1);
        });

        test('rejects out of bounds index', () => {
            const quizState = {
                questions: [{}, {}, {}],
                flaggedQuestions: []
            };

            const result = flagQuestion(10, quizState);

            expect(result).toBe(false);
        });

        test('rejects negative index', () => {
            const quizState = {
                questions: [{}, {}, {}],
                flaggedQuestions: []
            };

            const result = flagQuestion(-1, quizState);

            expect(result).toBe(false);
        });
    });
});
```

### Integration Tests

**Test Framework:** Playwright or Cypress
**Test Files:**
- `tests/e2e/quiz-flow.spec.js` - End-to-end quiz flow
- `tests/e2e/quiz-api.spec.js` - API integration

**Example Integration Test (Playwright):**
```javascript
// tests/e2e/quiz-flow.spec.js
import { test, expect } from '@playwright/test';

test.describe('Quiz Flow', () => {
    test('user can complete entire quiz', async ({ page }) => {
        // Navigate to quiz page
        await page.goto('/courses/echr/study-portal');

        // Click quiz tab
        await page.click('[data-tab="quiz"]');

        // Start quiz
        await page.click('#start-quiz-btn');

        // Wait for quiz to load
        await page.waitForSelector('.quiz-question-card');

        // Get total questions
        const totalText = await page.locator('#quiz-total').textContent();
        const totalQuestions = parseInt(totalText);

        // Answer all questions
        for (let i = 0; i < totalQuestions; i++) {
            // Select first option
            await page.click('.quiz-option:first-child');

            // Click next (or finish on last question)
            if (i < totalQuestions - 1) {
                await page.click('#next-question-btn');
            }
        }

        // Verify results displayed
        await expect(page.locator('.quiz-results')).toBeVisible();
        await expect(page.locator('.score-display')).toContainText('%');
    });
});
```

### Accessibility Tests

**Tools:** axe-core with Playwright, jest-axe
**Standards:** WCAG 2.1 AA

**Example Accessibility Test (Playwright + axe):**
```javascript
// tests/e2e/quiz-accessibility.spec.js
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Quiz Accessibility', () => {
    test('quiz page meets WCAG AA standards', async ({ page }) => {
        await page.goto('/courses/echr/study-portal');
        await page.click('[data-tab="quiz"]');
        await page.click('#start-quiz-btn');

        // Run axe accessibility scan
        const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

        // Should have no violations
        expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('keyboard navigation works throughout quiz', async ({ page }) => {
        await page.goto('/courses/echr/study-portal');
        await page.click('[data-tab="quiz"]');
        await page.click('#start-quiz-btn');

        // Tab through interactive elements
        for (let i = 0; i < 10; i++) {
            await page.keyboard.press('Tab');

            // Get focused element
            const focusedElement = await page.evaluateHandle(() => document.activeElement);

            // Verify focus is visible
            const outline = await focusedElement.evaluate(el =>
                window.getComputedStyle(el).outline
            );
            expect(outline).not.toBe('none');
        }
    });
});
```

### Performance Tests

**Metrics:**
- First Contentful Paint (FCP) < 1.5s
- Time to Interactive (TTI) < 3.5s
- Animation frame rate: 60fps
- Memory usage < 50MB

**Example Performance Test (Playwright):**
```javascript
// tests/e2e/quiz-performance.spec.js
import { test, expect } from '@playwright/test';

test.describe('Quiz Performance', () => {
    test('quiz loads within performance budget', async ({ page }) => {
        // Start performance measurement
        const startTime = Date.now();

        await page.goto('/courses/echr/study-portal');
        await page.click('[data-tab="quiz"]');
        await page.click('#start-quiz-btn');

        // Wait for quiz to be interactive
        await page.waitForSelector('.quiz-container');

        const loadTime = Date.now() - startTime;

        // TTI should be < 3.5s
        expect(loadTime).toBeLessThan(3500);
    });

    test('measures Core Web Vitals', async ({ page }) => {
        await page.goto('/courses/echr/study-portal');

        // Get performance metrics
        const metrics = await page.evaluate(() => {
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(entry => entry.name === 'first-contentful-paint');

            return {
                fcp: fcp ? fcp.startTime : null
            };
        });

        // FCP should be < 1.5s
        expect(metrics.fcp).toBeLessThan(1500);
    });
});
```

---

## Backend Requirements

### API Endpoints

**Existing Endpoints (from app.js):**

1. **List Saved Quizzes**
   ```
   GET /api/quizzes/courses/{courseId}
   Response: [
       {
           "id": "string",
           "topic": "string",
           "difficulty": "easy|medium|hard",
           "numQuestions": number,
           "createdAt": "timestamp"
       }
   ]
   ```

2. **Create New Quiz**
   ```
   POST /api/quizzes/courses/{courseId}
   Request: {
       "topic": "string",
       "difficulty": "easy|medium|hard",
       "numQuestions": number
   }
   Response: {
       "id": "string",
       "questions": [
           {
               "id": "string",
               "text": "string",
               "options": ["string"],
               "correct_index": number,
               "difficulty": "string"
           }
       ]
   }
   ```

3. **Get Specific Quiz**
   ```
   GET /api/quizzes/courses/{courseId}/{quizId}
   Response: {
       "id": "string",
       "questions": [...],
       "createdAt": "timestamp"
   }
   ```

4. **Submit Quiz Results**
   ```
   POST /api/quizzes/submit
   Request: {
       "quizId": "string",
       "courseId": "string",
       "userAnswers": number[],
       "timeTaken": number
   }
   Response: {
       "score": number,
       "totalQuestions": number,
       "correctAnswers": number,
       "percentage": number
   }
   ```

5. **Get Quiz History**
   ```
   GET /api/quizzes/history/{userId}
   Response: [
       {
           "id": "string",
           "courseId": "string",
           "score": number,
           "completedAt": "timestamp"
       }
   ]
   ```

**New Endpoints Needed:**

6. **Save Flagged Questions**
   ```
   POST /api/quizzes/{quizId}/flags
   Request: {
       "flaggedQuestions": number[]
   }
   Response: {
       "success": boolean
   }
   ```

7. **Get Quiz State** (for persistence)
   ```
   GET /api/quizzes/{quizId}/state
   Response: {
       "currentQuestionIndex": number,
       "userAnswers": number[],
       "flaggedQuestions": number[],
       "timeRemaining": number (optional)
   }
   ```

### Data Models

**Quiz Model:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Question(BaseModel):
    id: str = Field(..., description="Unique question identifier")
    text: str = Field(..., description="Question text")
    type: QuestionType = Field(..., description="Question type")
    options: List[str] = Field(default=[], description="Answer options")
    correct_answer: str = Field(..., description="Correct answer")
    explanation: Optional[str] = Field(None, description="Answer explanation")
    difficulty: Difficulty = Field(..., description="Question difficulty")

class QuizState(BaseModel):
    quiz_id: str = Field(..., description="Unique quiz identifier")
    user_id: str = Field(..., description="User identifier")
    questions: List[Question] = Field(..., description="Quiz questions")
    current_question_index: int = Field(0, description="Current question index")
    user_answers: dict = Field(default_factory=dict, description="User answers")
    flagged_questions: List[str] = Field(default_factory=list, description="Flagged question IDs")
    start_time: datetime = Field(..., description="Quiz start time")
    time_limit: Optional[int] = Field(None, description="Time limit in seconds")
    completed: bool = Field(False, description="Quiz completion status")

class QuizResult(BaseModel):
    quiz_id: str
    score: float = Field(..., ge=0, le=100, description="Score percentage")
    total_questions: int = Field(..., gt=0)
    correct_answers: int = Field(..., ge=0)
    xp_earned: int = Field(..., ge=0)
    time_taken: int = Field(..., ge=0, description="Time in seconds")
    results: List[dict]
```

### Database Schema (Firestore)

**Collections:**

1. **quizzes** (Collection)
   ```javascript
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
   ```

2. **quiz_results** (Collection)
   ```javascript
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
       timeTaken: number,  // seconds
       completedAt: Timestamp,
       percentage: number
   }
   ```

3. **quiz_flags** (Collection)
   ```javascript
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
      allow create: if request.auth != null &&
                      request.resource.data.userId == request.auth.uid;
      allow update, delete: if request.auth != null &&
                              resource.data.userId == request.auth.uid;
    }

    // Quiz results
    match /quiz_results/{resultId} {
      allow read: if request.auth != null &&
                    resource.data.userId == request.auth.uid;
      allow create: if request.auth != null &&
                      request.resource.data.userId == request.auth.uid;
    }

    // Quiz flags
    match /quiz_flags/{flagId} {
      allow read, write: if request.auth != null &&
                           resource.data.userId == request.auth.uid;
    }
  }
}
```

---

**Status:** Planning Complete - Ready for Implementation

