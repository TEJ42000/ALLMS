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
// Question Navigation Sidebar
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

function getQuestionStatus(index) {
    const classes = [];
    if (index === quizState.currentQuestionIndex) classes.push('current');
    if (quizState.userAnswers[index] !== null) classes.push('answered');
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

**Test Framework:** pytest
**Coverage Target:** 80%+ for new code

**Test Files:**
- `tests/test_quiz_ui_components.py` - Component rendering tests
- `tests/test_quiz_navigation.py` - Navigation logic tests
- `tests/test_quiz_accessibility.py` - Accessibility compliance tests
- `tests/test_quiz_state_management.py` - State management tests

**Example Unit Test:**
```python
import pytest
from unittest.mock import Mock, patch
from app.static.js import quiz_navigation

class TestQuestionNavigation:
    """Test question navigation functionality."""

    def test_create_question_nav_with_valid_questions(self):
        """Test navigation sidebar creation with valid questions."""
        questions = [
            {"id": 1, "text": "Question 1"},
            {"id": 2, "text": "Question 2"},
            {"id": 3, "text": "Question 3"}
        ]

        nav = quiz_navigation.createQuestionNav(questions)

        assert nav is not None
        assert len(nav.querySelectorAll('.question-nav-btn')) == 3

    def test_get_question_status_current(self):
        """Test question status for current question."""
        quiz_state = {
            'currentQuestionIndex': 1,
            'userAnswers': [None, None, None],
            'flaggedQuestions': []
        }

        status = quiz_navigation.getQuestionStatus(1, quiz_state)

        assert 'current' in status
        assert 'answered' not in status

    def test_flag_question_validation(self):
        """Test question flagging with bounds checking."""
        quiz_state = {'questions': [1, 2, 3], 'flaggedQuestions': []}

        # Valid index
        result = quiz_navigation.flagQuestion(1, quiz_state)
        assert result is True
        assert 1 in quiz_state['flaggedQuestions']

        # Invalid index (out of bounds)
        result = quiz_navigation.flagQuestion(10, quiz_state)
        assert result is False

        # Invalid index (negative)
        result = quiz_navigation.flagQuestion(-1, quiz_state)
        assert result is False
```

### Integration Tests

**Test Files:**
- `tests/integration/test_quiz_flow.py` - End-to-end quiz flow
- `tests/integration/test_quiz_api.py` - API integration

**Example Integration Test:**
```python
class TestQuizFlow:
    """Test complete quiz flow."""

    @patch('app.routes.quiz.get_quiz_questions')
    def test_complete_quiz_flow(self, mock_get_questions, client):
        """Test user can complete entire quiz."""
        # Setup
        mock_get_questions.return_value = [
            {"id": 1, "text": "Q1", "options": ["A", "B", "C", "D"]},
            {"id": 2, "text": "Q2", "options": ["A", "B", "C", "D"]}
        ]

        # Start quiz
        response = client.post('/api/quiz/start', json={'topic': 'test'})
        assert response.status_code == 200
        quiz_id = response.json()['quiz_id']

        # Answer questions
        response = client.post(f'/api/quiz/{quiz_id}/answer',
                              json={'question_id': 1, 'answer': 'A'})
        assert response.status_code == 200

        # Submit quiz
        response = client.post(f'/api/quiz/{quiz_id}/submit')
        assert response.status_code == 200
        assert 'score' in response.json()
        assert 'xp_earned' in response.json()
```

### Accessibility Tests

**Tools:** axe-core, pa11y
**Standards:** WCAG 2.1 AA

**Example Accessibility Test:**
```python
from selenium import webdriver
from axe_selenium_python import Axe

class TestQuizAccessibility:
    """Test quiz UI accessibility."""

    def test_quiz_page_wcag_compliance(self):
        """Test quiz page meets WCAG AA standards."""
        driver = webdriver.Chrome()
        driver.get('http://localhost:8000/quiz')

        axe = Axe(driver)
        axe.inject()
        results = axe.run()

        # Should have no violations
        assert len(results['violations']) == 0

        driver.quit()

    def test_keyboard_navigation(self):
        """Test all quiz functions accessible via keyboard."""
        driver = webdriver.Chrome()
        driver.get('http://localhost:8000/quiz')

        # Tab through all interactive elements
        body = driver.find_element_by_tag_name('body')
        for _ in range(20):
            body.send_keys(Keys.TAB)
            active = driver.switch_to.active_element
            # Verify focus is visible
            assert active.value_of_css_property('outline') != 'none'

        driver.quit()
```

### Performance Tests

**Metrics:**
- First Contentful Paint (FCP) < 1.5s
- Time to Interactive (TTI) < 3.5s
- Animation frame rate: 60fps
- Memory usage < 50MB

**Example Performance Test:**
```python
import time
from selenium import webdriver

class TestQuizPerformance:
    """Test quiz UI performance."""

    def test_quiz_load_time(self):
        """Test quiz loads within performance budget."""
        driver = webdriver.Chrome()

        start_time = time.time()
        driver.get('http://localhost:8000/quiz')

        # Wait for quiz to be interactive
        driver.find_element_by_class_name('quiz-container')
        load_time = time.time() - start_time

        assert load_time < 3.5  # TTI < 3.5s

        driver.quit()

    def test_animation_performance(self):
        """Test animations run at 60fps."""
        # Use Chrome DevTools Protocol to measure FPS
        # Implementation depends on specific animation
        pass
```

---

## Backend Requirements

### API Endpoints

**Required Endpoints:**

1. **Start Quiz**
   ```
   POST /api/quiz/start
   Request: {
       "topic": "string",
       "difficulty": "easy|medium|hard",
       "question_count": number,
       "timed": boolean,
       "time_limit": number (seconds, optional)
   }
   Response: {
       "quiz_id": "string",
       "questions": [
           {
               "id": "string",
               "text": "string",
               "type": "multiple_choice|true_false|short_answer",
               "options": ["string"],
               "difficulty": "easy|medium|hard"
           }
       ],
       "time_limit": number (optional)
   }
   ```

2. **Submit Answer**
   ```
   POST /api/quiz/{quiz_id}/answer
   Request: {
       "question_id": "string",
       "answer": "string|number|boolean"
   }
   Response: {
       "success": boolean,
       "message": "string"
   }
   ```

3. **Flag Question**
   ```
   POST /api/quiz/{quiz_id}/flag
   Request: {
       "question_id": "string",
       "flagged": boolean
   }
   Response: {
       "success": boolean
   }
   ```

4. **Submit Quiz**
   ```
   POST /api/quiz/{quiz_id}/submit
   Response: {
       "score": number,
       "total_questions": number,
       "correct_answers": number,
       "xp_earned": number,
       "time_taken": number,
       "results": [
           {
               "question_id": "string",
               "user_answer": "string",
               "correct_answer": "string",
               "is_correct": boolean,
               "explanation": "string"
           }
       ]
   }
   ```

5. **Get Quiz State**
   ```
   GET /api/quiz/{quiz_id}/state
   Response: {
       "quiz_id": "string",
       "current_question_index": number,
       "answered_questions": ["string"],
       "flagged_questions": ["string"],
       "time_remaining": number (optional)
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

### Database Schema

**Tables Required:**

1. **quiz_sessions**
   - id (UUID, primary key)
   - user_id (UUID, foreign key)
   - topic (VARCHAR)
   - difficulty (ENUM)
   - start_time (TIMESTAMP)
   - end_time (TIMESTAMP, nullable)
   - time_limit (INTEGER, nullable)
   - completed (BOOLEAN)

2. **quiz_answers**
   - id (UUID, primary key)
   - quiz_session_id (UUID, foreign key)
   - question_id (UUID, foreign key)
   - user_answer (TEXT)
   - is_correct (BOOLEAN)
   - answered_at (TIMESTAMP)

3. **quiz_flags**
   - id (UUID, primary key)
   - quiz_session_id (UUID, foreign key)
   - question_id (UUID, foreign key)
   - flagged (BOOLEAN)
   - flagged_at (TIMESTAMP)

---

**Status:** Planning Complete - Ready for Implementation

