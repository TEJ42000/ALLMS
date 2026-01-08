# Quiz UI Security and Error Handling

**Related:** Issue #157 - Complete Quiz Display UI Implementation  
**Priority:** CRITICAL

---

## Security Requirements

### XSS Prevention

**All user input and dynamic content MUST be sanitized.**

**Secure Code Examples:**

```javascript
// ❌ UNSAFE - Direct innerHTML injection
function displayQuestion(question) {
    document.getElementById('question-text').innerHTML = question.text;
}

// ✅ SAFE - Use textContent or sanitize HTML
function displayQuestion(question) {
    // Option 1: Use textContent (preferred for plain text)
    document.getElementById('question-text').textContent = question.text;
    
    // Option 2: Sanitize HTML if formatting needed
    const sanitized = DOMPurify.sanitize(question.text);
    document.getElementById('question-text').innerHTML = sanitized;
}

// ❌ UNSAFE - Template literals without escaping
function createOption(option, index) {
    return `<button class="quiz-option">${option}</button>`;
}

// ✅ SAFE - Escape HTML entities
function createOption(option, index) {
    const escaped = escapeHtml(option);
    return `<button class="quiz-option">${escaped}</button>`;
}

/**
 * Escape HTML entities to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} - HTML-safe text
 */
function escapeHtml(text) {
    if (typeof text !== 'string') {
        return '';
    }

    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Alternative implementation using replace (faster for simple cases)
function escapeHtmlFast(text) {
    if (typeof text !== 'string') {
        return '';
    }

    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ✅ BEST - Use DOM methods
function createOption(option, index) {
    const button = document.createElement('button');
    button.className = 'quiz-option';
    button.textContent = option;  // Automatically escapes
    button.setAttribute('data-index', index);
    return button;
}
```

### Input Validation

**All inputs MUST be validated before processing.**

```javascript
// ✅ SAFE - Validate array access
function navigateToQuestion(index, quizState) {
    // Validate index is a number
    if (typeof index !== 'number' || !Number.isInteger(index)) {
        console.error('Invalid question index: must be an integer');
        return false;
    }
    
    // Validate bounds
    if (index < 0 || index >= quizState.questions.length) {
        console.error(`Question index ${index} out of bounds (0-${quizState.questions.length - 1})`);
        return false;
    }
    
    // Validate questions array exists
    if (!Array.isArray(quizState.questions)) {
        console.error('Invalid quiz state: questions is not an array');
        return false;
    }
    
    quizState.currentQuestionIndex = index;
    displayCurrentQuestion();
    return true;
}

// ✅ SAFE - Validate user answer
function submitAnswer(questionId, answer) {
    // Validate question ID
    if (!questionId || typeof questionId !== 'string') {
        throw new Error('Invalid question ID');
    }
    
    // Validate answer is not empty
    if (answer === null || answer === undefined || answer === '') {
        throw new Error('Answer cannot be empty');
    }
    
    // Sanitize answer before sending to backend
    const sanitizedAnswer = typeof answer === 'string' 
        ? answer.trim().substring(0, 1000)  // Limit length
        : answer;
    
    return fetch(`/api/quiz/${quizState.quizId}/answer`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': getCsrfToken()  // CSRF protection
        },
        body: JSON.stringify({
            question_id: questionId,
            answer: sanitizedAnswer
        })
    });
}
```

### Event Delegation Pattern

**Use event delegation to prevent memory leaks and improve performance.**

```javascript
// ❌ UNSAFE - Individual event listeners (memory leak risk)
function displayOptions(options) {
    options.forEach((option, index) => {
        const button = createOptionButton(option, index);
        button.addEventListener('click', () => selectOption(index));
        container.appendChild(button);
    });
}

// ✅ SAFE - Event delegation
function initializeQuizEventListeners() {
    const quizContainer = document.getElementById('quiz-container');
    
    // Single event listener for all options
    quizContainer.addEventListener('click', (event) => {
        const optionButton = event.target.closest('.quiz-option');
        if (optionButton) {
            const index = parseInt(optionButton.getAttribute('data-index'), 10);
            if (!isNaN(index)) {
                selectOption(index);
            }
        }
    });
    
    // Single event listener for navigation
    quizContainer.addEventListener('click', (event) => {
        const navButton = event.target.closest('.question-nav-btn');
        if (navButton) {
            const index = parseInt(navButton.getAttribute('data-question-index'), 10);
            if (!isNaN(index)) {
                navigateToQuestion(index, quizState);
            }
        }
    });
    
    // Single event listener for flag button
    quizContainer.addEventListener('click', (event) => {
        if (event.target.closest('.flag-question-btn')) {
            toggleQuestionFlag(quizState.currentQuestionIndex);
        }
    });
}

// Call once on page load
document.addEventListener('DOMContentLoaded', initializeQuizEventListeners);
```

### Content Security Policy (CSP)

**Ensure all code is CSP-compliant (no inline scripts).**

```html
<!-- ❌ UNSAFE - Inline event handlers -->
<button onclick="submitQuiz()">Submit</button>

<!-- ✅ SAFE - Event listeners in external JS -->
<button id="submit-quiz-btn" class="btn-primary">Submit</button>

<script src="/static/js/quiz.js"></script>
```

```javascript
// In quiz.js
document.getElementById('submit-quiz-btn').addEventListener('click', submitQuiz);
```

### CSRF Protection

**All POST requests MUST include CSRF token.**

```javascript
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

function makeSecureRequest(url, method, data) {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (method !== 'GET') {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        headers['X-CSRF-Token'] = csrfToken;
    }
    
    return fetch(url, {
        method,
        headers,
        body: method !== 'GET' ? JSON.stringify(data) : undefined,
        credentials: 'same-origin'  // Include cookies
    });
}
```

---

## Error Handling Strategy

### Error Boundaries

**Implement graceful degradation for all features.**

```javascript
class QuizErrorBoundary {
    constructor() {
        this.errors = [];
        this.setupGlobalErrorHandler();
    }
    
    setupGlobalErrorHandler() {
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'Global error');
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'Unhandled promise rejection');
        });
    }
    
    handleError(error, context) {
        console.error(`[${context}]`, error);
        this.errors.push({ error, context, timestamp: new Date() });
        
        // Show user-friendly error message
        this.showErrorMessage('Something went wrong. Please try again.');
        
        // Log to error tracking service
        this.logToErrorService(error, context);
    }
    
    showErrorMessage(message) {
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.classList.add('visible');
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorContainer.classList.remove('visible');
            }, 5000);
        }
    }
    
    logToErrorService(error, context) {
        // Send to backend error logging
        fetch('/api/log-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                error: error.toString(),
                stack: error.stack,
                context,
                userAgent: navigator.userAgent,
                url: window.location.href
            })
        }).catch(() => {
            // Silently fail - don't want error logging to cause more errors
        });
    }
}

// Initialize error boundary
const errorBoundary = new QuizErrorBoundary();
```

### API Error Handling

**Handle all API errors gracefully with user feedback.**

```javascript
async function submitQuizAnswer(questionId, answer) {
    try {
        const response = await makeSecureRequest(
            `/api/quiz/${quizState.quizId}/answer`,
            'POST',
            { question_id: questionId, answer }
        );
        
        if (!response.ok) {
            // Handle HTTP errors
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        // Network error or parsing error
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            showErrorNotification('Network error. Please check your connection.');
        } else if (error.name === 'SyntaxError') {
            showErrorNotification('Invalid response from server.');
        } else {
            showErrorNotification(error.message || 'Failed to submit answer.');
        }
        
        // Log error
        console.error('Submit answer error:', error);
        errorBoundary.handleError(error, 'submitQuizAnswer');
        
        // Return null to indicate failure
        return null;
    }
}
```

### Fallback UI States

**Provide fallback UI for all error scenarios.**

```javascript
function displayCurrentQuestion() {
    try {
        // Validate quiz state
        if (!quizState || !quizState.questions) {
            throw new Error('Invalid quiz state');
        }
        
        const currentIndex = quizState.currentQuestionIndex;
        
        // Validate index
        if (currentIndex < 0 || currentIndex >= quizState.questions.length) {
            throw new Error('Invalid question index');
        }
        
        const question = quizState.questions[currentIndex];
        
        // Validate question object
        if (!question || !question.text) {
            throw new Error('Invalid question data');
        }
        
        // Display question
        document.getElementById('question-text').textContent = question.text;
        displayOptions(question.options || []);
        updateProgressBar();
        
    } catch (error) {
        console.error('Error displaying question:', error);
        
        // Show fallback UI
        const quizContainer = document.getElementById('quiz-container');
        quizContainer.innerHTML = `
            <div class="error-state">
                <h3>Unable to load question</h3>
                <p>There was a problem loading this question.</p>
                <button onclick="location.reload()" class="btn-primary">
                    Reload Quiz
                </button>
            </div>
        `;
    }
}
```

### User Feedback

**Always provide clear feedback for user actions.**

```javascript
/**
 * Show notification to user
 * @param {string} message - Message to display
 * @param {string} type - Notification type (info, success, error)
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'polite');

    const icon = type === 'error' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️';

    // Create elements using DOM methods (safer than innerHTML)
    const iconSpan = document.createElement('span');
    iconSpan.className = 'notification-icon';
    iconSpan.textContent = icon;

    const messageSpan = document.createElement('span');
    messageSpan.className = 'notification-message';
    messageSpan.textContent = message;  // Automatically escapes

    const closeBtn = document.createElement('button');
    closeBtn.className = 'notification-close';
    closeBtn.setAttribute('aria-label', 'Close notification');
    closeBtn.textContent = '×';

    notification.appendChild(iconSpan);
    notification.appendChild(messageSpan);
    notification.appendChild(closeBtn);

    document.body.appendChild(notification);

    // ✅ FIX: Store timeout IDs to clear them if notification is removed early
    let fadeTimeout, removeTimeout;

    // Function to remove notification and clean up
    const removeNotification = () => {
        // Clear timeouts to prevent memory leaks
        if (fadeTimeout) clearTimeout(fadeTimeout);
        if (removeTimeout) clearTimeout(removeTimeout);

        // Remove event listener before removing element
        closeBtn.removeEventListener('click', handleClose);

        // Remove from DOM
        notification.remove();
    };

    // Close button handler
    const handleClose = () => {
        notification.classList.add('fade-out');
        setTimeout(removeNotification, 300);
    };

    // Auto-remove after 5 seconds
    fadeTimeout = setTimeout(() => {
        notification.classList.add('fade-out');
        removeTimeout = setTimeout(removeNotification, 300);
    }, 5000);

    // Add close button listener
    closeBtn.addEventListener('click', handleClose);
}

// Usage examples
showNotification('Answer submitted successfully', 'success');
showNotification('Please select an answer', 'error');
showNotification('Question flagged for review', 'info');
```

---

## Performance Requirements

### Metrics

- **First Contentful Paint (FCP):** < 1.5s
- **Time to Interactive (TTI):** < 3.5s
- **Largest Contentful Paint (LCP):** < 2.5s
- **Cumulative Layout Shift (CLS):** < 0.1
- **First Input Delay (FID):** < 100ms
- **Animation Frame Rate:** 60fps (16.67ms per frame)
- **Memory Usage:** < 50MB
- **Bundle Size:** < 200KB (gzipped)

### Optimization Strategies

1. **Code Splitting**
   - Load quiz navigation module only when needed
   - Lazy load accessibility features
   - Defer mobile gesture handlers

2. **Debouncing/Throttling**
   ```javascript
   function debounce(func, wait) {
       let timeout;
       return function executedFunction(...args) {
           clearTimeout(timeout);
           timeout = setTimeout(() => func.apply(this, args), wait);
       };
   }
   
   // Use for search/filter
   const debouncedSearch = debounce(searchQuestions, 300);
   ```

3. **Virtual Scrolling**
   - For question navigation with 100+ questions
   - Render only visible items

4. **Request Batching**
   - Batch multiple flag operations
   - Debounce auto-save

---

## CSRF Implementation Details

### Backend (FastAPI)

**Generate CSRF Token:**
```python
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import secrets
import hashlib
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Store CSRF tokens (use Redis in production)
csrf_tokens = {}

def generate_csrf_token(user_id: str) -> str:
    """Generate a CSRF token for a user."""
    token = secrets.token_urlsafe(32)
    timestamp = int(time.time())

    # Store token with timestamp
    csrf_tokens[user_id] = {
        'token': token,
        'timestamp': timestamp
    }

    return token

def verify_csrf_token(user_id: str, token: str) -> bool:
    """Verify a CSRF token."""
    if user_id not in csrf_tokens:
        return False

    stored = csrf_tokens[user_id]

    # Check token matches
    if stored['token'] != token:
        return False

    # Check token age (expire after 1 hour)
    if time.time() - stored['timestamp'] > 3600:
        del csrf_tokens[user_id]
        return False

    return True

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve index page with CSRF token."""
    user_id = request.state.user.user_id if hasattr(request.state, 'user') else 'anonymous'
    csrf_token = generate_csrf_token(user_id)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "csrf_token": csrf_token
    })

async def verify_csrf(request: Request):
    """Dependency to verify CSRF token."""
    user_id = request.state.user.user_id if hasattr(request.state, 'user') else 'anonymous'
    token = request.headers.get('X-CSRF-Token')

    if not token or not verify_csrf_token(user_id, token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

@app.post("/api/quiz/{quiz_id}/answer", dependencies=[Depends(verify_csrf)])
async def submit_answer(quiz_id: str, answer: dict):
    """Submit quiz answer (CSRF protected)."""
    # Process answer
    return {"success": True}
```

**Template (Jinja2):**
```html
<!DOCTYPE html>
<html>
<head>
    <meta name="csrf-token" content="{{ csrf_token }}">
</head>
<body>
    <!-- Content -->
</body>
</html>
```

### Frontend (JavaScript)

**Get CSRF Token:**
```javascript
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) {
        console.error('CSRF token not found in page');
        return null;
    }
    return meta.getAttribute('content');
}
```

**Use in Requests:**
```javascript
async function makeSecureRequest(url, method, data) {
    const headers = {
        'Content-Type': 'application/json'
    };

    // Add CSRF token for non-GET requests
    if (method !== 'GET') {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        headers['X-CSRF-Token'] = csrfToken;
    }

    const response = await fetch(url, {
        method,
        headers,
        body: method !== 'GET' ? JSON.stringify(data) : undefined,
        credentials: 'same-origin'  // Include cookies
    });

    if (!response.ok) {
        if (response.status === 403) {
            throw new Error('CSRF token invalid or expired. Please refresh the page.');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
}
```

---

## Fixed Selenium Test Examples

**Issue:** Deprecated Selenium methods

**OLD (Deprecated):**
```python
# ❌ DEPRECATED
driver.find_element_by_tag_name('body')
driver.find_element_by_class_name('quiz-container')
driver.find_element_by_id('submit-btn')
```

**NEW (Modern Selenium 4+):**
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class TestQuizAccessibility:
    """Test quiz UI accessibility."""

    def test_quiz_page_wcag_compliance(self):
        """Test quiz page meets WCAG AA standards."""
        driver = webdriver.Chrome()
        driver.get('http://localhost:8000/quiz')

        # Modern Selenium 4 syntax
        from axe_selenium_python import Axe
        axe = Axe(driver)
        axe.inject()
        results = axe.run()

        # Should have no violations
        assert len(results['violations']) == 0, f"Found {len(results['violations'])} accessibility violations"

        driver.quit()

    def test_keyboard_navigation(self):
        """Test all quiz functions accessible via keyboard."""
        driver = webdriver.Chrome()
        driver.get('http://localhost:8000/quiz')

        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'quiz-container')))

        # Get body element using modern syntax
        body = driver.find_element(By.TAG_NAME, 'body')

        # Tab through all interactive elements
        for _ in range(20):
            body.send_keys(Keys.TAB)
            active = driver.switch_to.active_element

            # Verify focus is visible
            outline = active.value_of_css_property('outline')
            assert outline != 'none', "Focus indicator not visible"

        driver.quit()

    def test_screen_reader_announcements(self):
        """Test screen reader announcements."""
        driver = webdriver.Chrome()
        driver.get('http://localhost:8000/quiz')

        wait = WebDriverWait(driver, 10)

        # Start quiz
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, 'start-quiz-btn')))
        start_btn.click()

        # Check for live region
        live_region = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-live="polite"]')))
        assert live_region is not None

        # Select an answer
        option = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'quiz-option')))
        option.click()

        # Verify announcement
        announcement = live_region.text
        assert len(announcement) > 0, "No screen reader announcement"

        driver.quit()
```

---

**Status:** All Fixes Documented and Implemented

