// app.js - Frontend JavaScript for LLS Study Portal

const API_BASE = '';  // Empty for same origin

// ========== Course Context ==========
// Get course context from window object (set by template)
const COURSE_ID = window.COURSE_CONTEXT?.courseId || null;
const COURSE_NAME = window.COURSE_CONTEXT?.courseName || 'LLS';
const COURSE = window.COURSE_CONTEXT?.course || null;

/**
 * Add course_id parameter to API requests if in course context
 */
function addCourseContext(params = {}) {
    if (COURSE_ID) {
        params.course_id = COURSE_ID;
    }
    return params;
}

/**
 * Build URL with query parameters
 */
function buildUrl(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
            url.searchParams.append(key, params[key]);
        }
    });
    return url.toString();
}

// ========== Tab Navigation ==========
document.addEventListener('DOMContentLoaded', () => {
    // Verify course context is set
    if (!COURSE_ID) {
        console.error('No course ID set - redirecting to course selection');
        window.location.href = '/';
        return;
    }

    // Log course context for debugging
    console.log('✅ Course Context Loaded:', {
        courseId: COURSE_ID,
        courseName: COURSE_NAME,
        course: COURSE
    });

    const tabs = document.querySelectorAll('.nav-tab');
    const sections = document.querySelectorAll('.section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show corresponding section
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === `${tabName}-section`) {
                    section.classList.add('active');
                }
            });
        });
    });

    // Initialize event listeners
    initDashboard();
    initTutorListeners();
    initAssessmentListeners();
    initQuizListeners();
    initStudyListeners();
    initFlashcardListeners();
});

// ========== Loading State ==========
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// ========== Markdown Formatting ==========
function formatMarkdown(text) {
    if (!text) return '';

    // Split into lines for processing
    const lines = text.split('\n');
    let html = '';
    let inList = false;
    let inNumberedList = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        // Skip empty lines but add spacing
        if (line.trim() === '') {
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            if (inNumberedList) {
                html += '</ol>';
                inNumberedList = false;
            }
            html += '<br>';
            continue;
        }

        // Headers
        if (line.startsWith('## ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<h2 class="md-h2">${escapeHtml(line.substring(3))}</h2>`;
            continue;
        }
        if (line.startsWith('### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<h3 class="md-h3">${escapeHtml(line.substring(4))}</h3>`;
            continue;
        }

        // Special callout boxes
        if (line.startsWith('💡 ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="callout callout-tip">💡 ${formatInline(line.substring(3))}</div>`;
            continue;
        }
        if (line.startsWith('✅ ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="callout callout-success">✅ ${formatInline(line.substring(3))}</div>`;
            continue;
        }
        if (line.startsWith('❌ ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="callout callout-error">❌ ${formatInline(line.substring(3))}</div>`;
            continue;
        }
        if (line.startsWith('⚠️ ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="callout callout-warning">⚠️ ${formatInline(line.substring(3))}</div>`;
            continue;
        }
        if (line.startsWith('❓ ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="callout callout-question">❓ ${formatInline(line.substring(3))}</div>`;
            continue;
        }

        // STEP markers
        if (line.match(/^STEP \d+:/)) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<div class="step-marker">${formatInline(line)}</div>`;
            continue;
        }

        // Bullet lists (• or -)
        if (line.match(/^[•\-] /)) {
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            if (!inList) {
                html += '<ul class="md-list">';
                inList = true;
            }
            html += `<li>${formatInline(line.substring(2))}</li>`;
            continue;
        }

        // Numbered lists
        if (line.match(/^\d+\. /)) {
            if (inList) { html += '</ul>'; inList = false; }
            if (!inNumberedList) {
                html += '<ol class="md-list-numbered">';
                inNumberedList = true;
            }
            const content = line.replace(/^\d+\. /, '');
            html += `<li>${formatInline(content)}</li>`;
            continue;
        }

        // Regular paragraph
        if (inList) { html += '</ul>'; inList = false; }
        if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
        html += `<p class="md-p">${formatInline(line)}</p>`;
    }

    // Close any open lists
    if (inList) html += '</ul>';
    if (inNumberedList) html += '</ol>';

    return html;
}

// Format inline markdown (bold, italic, code, etc.)
function formatInline(text) {
    // First escape HTML to prevent XSS
    text = escapeHtml(text);

    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="md-bold">$1</strong>');
    // Italic
    text = text.replace(/\*(.*?)\*/g, '<em class="md-italic">$1</em>');
    // Code/Articles
    text = text.replace(/`(.*?)`/g, '<code class="md-code">$1</code>');
    // Article references (Art. X:XX format)
    text = text.replace(/Art\. ([\d:]+\s+[A-Z]+)/g, '<span class="article-ref">Art. $1</span>');

    return text;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== AI Tutor ==========
function initTutorListeners() {
    const askBtn = document.getElementById('ask-btn');
    const input = document.getElementById('tutor-input');
    
    askBtn.addEventListener('click', askTutor);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            askTutor();
        }
    });
}

async function askTutor() {
    const message = document.getElementById('tutor-input').value.trim();
    const context = document.getElementById('context-select').value;
    const messagesDiv = document.getElementById('chat-messages');
    
    if (!message) return;
    
    // Add user message
    addMessage('user', message);
    document.getElementById('tutor-input').value = '';
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/tutor/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(addCourseContext({message, context}))
        });
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        const data = await response.json();
        addMessage('assistant', data.content);
        
    } catch (error) {
        console.error('Error:', error);
        addMessage('error', 'Sorry, there was an error processing your request.');
    } finally {
        hideLoading();
    }
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    messageDiv.innerHTML = formatMarkdown(content);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ========== Assessment ==========
function initAssessmentListeners() {
    document.getElementById('assess-btn').addEventListener('click', assessAnswer);
}

async function assessAnswer() {
    const topic = document.getElementById('assessment-topic').value;
    const question = document.getElementById('assessment-question').value.trim();
    const answer = document.getElementById('assessment-answer').value.trim();
    const resultDiv = document.getElementById('assessment-result');
    
    if (!answer) {
        alert('Please enter your answer');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/assessment/assess`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(addCourseContext({topic, question: question || null, answer}))
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `API error: ${response.status}`;
            throw new Error(errorMessage);
        }

        const data = await response.json();
        resultDiv.innerHTML = `
            <div class="assessment-feedback">
                ${formatMarkdown(data.feedback)}
            </div>
        `;
        resultDiv.style.display = 'block';

    } catch (error) {
        console.error('Error:', error);
        const errorMessage = error.message || 'Error getting assessment. Please try again.';
        resultDiv.innerHTML = `<p class="error">${escapeHtml(errorMessage)}</p>`;
    } finally {
        hideLoading();
    }
}

// ========== Quiz Generator ==========
// Quiz state management
let quizState = {
    quizId: null,        // ID of the current quiz (for persisted quizzes)
    courseId: null,      // Course ID
    questions: [],
    currentQuestionIndex: 0,
    userAnswers: [],
    score: 0,
    isComplete: false,
    startTime: null      // Track quiz start time
};

// Race condition protection - prevent multiple simultaneous quiz generations
let isGeneratingQuiz = false;

// Simulated user ID (stored in localStorage until real auth)
function getUserId() {
    let userId = localStorage.getItem('allms_user_id');
    if (!userId) {
        userId = 'sim-' + crypto.randomUUID();
        localStorage.setItem('allms_user_id', userId);
    }
    return userId;
}

function initQuizListeners() {
    const startBtn = document.getElementById('start-quiz-btn');
    if (startBtn) startBtn.addEventListener('click', generateQuiz);

    // Tab navigation
    document.querySelectorAll('.quiz-tab').forEach(tab => {
        tab.addEventListener('click', () => switchQuizTab(tab.dataset.quizTab));
    });

    // Back button
    const backBtn = document.getElementById('back-to-quizzes-btn');
    if (backBtn) backBtn.addEventListener('click', backToQuizList);

    // Load saved quizzes on init
    loadSavedQuizzes();
}

function switchQuizTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.quiz-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.quizTab === tabName);
    });

    // Update tab content
    document.getElementById('saved-quizzes-tab')?.classList.toggle('hidden', tabName !== 'saved');
    document.getElementById('new-quiz-tab')?.classList.toggle('hidden', tabName !== 'new');
    document.getElementById('history-tab')?.classList.toggle('hidden', tabName !== 'history');

    // Load data for the tab
    if (tabName === 'saved') {
        loadSavedQuizzes();
    } else if (tabName === 'history') {
        loadQuizHistory();
    }
}

async function loadSavedQuizzes() {
    const container = document.getElementById('saved-quizzes-list');
    if (!container || !COURSE_ID) return;

    container.innerHTML = '<p class="loading-text">Loading saved quizzes...</p>';

    try {
        const response = await fetch(`${API_BASE}/api/quizzes/courses/${COURSE_ID}`);
        if (!response.ok) throw new Error('Failed to load quizzes');

        const data = await response.json();
        const quizzes = data.quizzes || [];

        if (quizzes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📚</div>
                    <p>No saved quizzes yet. Create your first quiz!</p>
                    <button class="btn btn-primary" onclick="switchQuizTab('new')">Create New Quiz</button>
                </div>
            `;
            return;
        }

        container.innerHTML = quizzes.map(quiz => `
            <div class="saved-quiz-card" data-quiz-id="${quiz.id}">
                <div class="saved-quiz-info">
                    <h4>${escapeHtml(quiz.title || quiz.topic)}</h4>
                    <div class="saved-quiz-meta">
                        <span>📝 ${quiz.numQuestions} questions</span>
                        <span>🎯 ${quiz.difficulty}</span>
                        ${quiz.weekNumber ? `<span>📅 Week ${quiz.weekNumber}</span>` : ''}
                        <span>📅 ${formatDate(quiz.createdAt)}</span>
                    </div>
                </div>
                <div class="saved-quiz-actions">
                    <button class="btn btn-primary btn-small start-saved-quiz">Start Quiz</button>
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.start-saved-quiz').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const quizId = btn.closest('.saved-quiz-card').dataset.quizId;
                startSavedQuiz(quizId);
            });
        });

    } catch (error) {
        console.error('Error loading quizzes:', error);
        container.innerHTML = `<p class="error">Error loading quizzes: ${error.message}</p>`;
    }
}

async function loadQuizHistory() {
    const container = document.getElementById('quiz-history-list');
    if (!container) return;

    container.innerHTML = '<p class="loading-text">Loading quiz history...</p>';

    try {
        const userId = getUserId();
        const response = await fetch(`${API_BASE}/api/quizzes/history/${userId}`, {
            headers: { 'X-User-ID': userId }
        });

        if (!response.ok) throw new Error('Failed to load history');

        const data = await response.json();
        const history = data.history || [];

        if (history.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <p>No quiz history yet. Take a quiz to see your results!</p>
                    <button class="btn btn-primary" onclick="switchQuizTab('saved')">Browse Quizzes</button>
                </div>
            `;
            return;
        }

        container.innerHTML = history.map(item => {
            const perfClass = getPerformanceClass(item.percentage);
            return `
                <div class="history-item">
                    <div class="history-info">
                        <h4>${escapeHtml(item.quizTitle || item.topic || 'Quiz')}</h4>
                        <span class="history-date">${formatDateTime(item.completedAt)}</span>
                    </div>
                    <div class="history-score">
                        <div class="percentage ${perfClass}">${item.percentage}%</div>
                        <div class="fraction">${item.score}/${item.totalQuestions}</div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading history:', error);
        container.innerHTML = `<p class="error">Error loading history: ${error.message}</p>`;
    }
}

function getPerformanceClass(percentage) {
    if (percentage >= 90) return 'excellent';
    if (percentage >= 70) return 'good';
    if (percentage >= 50) return 'average';
    return 'poor';
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString();
}

function formatDateTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString();
}

async function startSavedQuiz(quizId) {
    if (!COURSE_ID) return;

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/quizzes/courses/${COURSE_ID}/${quizId}`);
        if (!response.ok) throw new Error('Failed to load quiz');

        const data = await response.json();
        const quiz = data.quiz;

        // Reset quiz state
        quizState = {
            quizId: quiz.id,
            courseId: COURSE_ID,
            questions: quiz.questions,
            currentQuestionIndex: 0,
            userAnswers: new Array(quiz.questions.length).fill(null),
            score: 0,
            isComplete: false,
            startTime: Date.now()
        };

        // Show quiz content
        showQuizContent();

    } catch (error) {
        console.error('Error starting quiz:', error);
        alert('Error loading quiz: ' + error.message);
    } finally {
        hideLoading();
    }
}

function showQuizContent() {
    const selectionView = document.getElementById('quiz-selection-view');
    const quizContent = document.getElementById('quiz-content');
    const questionContainer = document.getElementById('quiz-question-container');

    if (selectionView) selectionView.classList.add('hidden');
    if (quizContent) quizContent.classList.remove('hidden');

    displayQuiz(quizContent, questionContainer);
}

function backToQuizList() {
    const selectionView = document.getElementById('quiz-selection-view');
    const quizContent = document.getElementById('quiz-content');

    if (quizContent) quizContent.classList.add('hidden');
    if (selectionView) selectionView.classList.remove('hidden');

    // Reload saved quizzes
    loadSavedQuizzes();
}

async function generateQuiz() {
    // Prevent multiple simultaneous quiz generation requests
    if (isGeneratingQuiz) {
        console.log('Quiz generation already in progress');
        return;
    }

    if (!COURSE_ID) {
        alert('No course selected. Please select a course first.');
        return;
    }

    const topicSelect = document.getElementById('quiz-topic-select');
    const difficultySelect = document.getElementById('quiz-difficulty-select');
    const numQuestionsSelect = document.getElementById('quiz-num-questions');
    const topic = topicSelect ? topicSelect.value : 'all';
    const difficulty = difficultySelect ? difficultySelect.value : 'medium';
    const num_questions = numQuestionsSelect ? parseInt(numQuestionsSelect.value) : 10;

    isGeneratingQuiz = true;
    showLoading();

    try {
        // Use the new quiz persistence API
        const response = await fetch(`${API_BASE}/api/quizzes/courses/${COURSE_ID}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': getUserId()
            },
            body: JSON.stringify({
                course_id: COURSE_ID,
                topic: topic,
                num_questions: num_questions,
                difficulty: difficulty,
                allow_duplicate: false
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `API error: ${response.status}`;
            throw new Error(errorMessage);
        }

        const data = await response.json();
        const quiz = data.quiz;

        if (!quiz || !quiz.questions || quiz.questions.length === 0) {
            throw new Error('No questions generated');
        }

        // Reset quiz state with the new quiz
        quizState = {
            quizId: quiz.id,
            courseId: COURSE_ID,
            questions: quiz.questions,
            currentQuestionIndex: 0,
            userAnswers: new Array(quiz.questions.length).fill(null),
            score: 0,
            isComplete: false,
            startTime: Date.now()
        };

        // Show notification if this was an existing quiz
        if (!data.is_new) {
            console.log('Loaded existing quiz with matching content');
        }

        // Show quiz content
        showQuizContent();

    } catch (error) {
        console.error('Error:', error);
        // Define questionContainer in error handler scope
        const questionContainer = document.getElementById('quiz-question-container');
        const quizContent = document.getElementById('quiz-content');

        if (questionContainer) {
            const errorMessage = error.message || 'Error generating quiz. Please try again.';
            questionContainer.innerHTML = `<p class="error">${escapeHtml(errorMessage)}</p>`;
        }
        if (quizContent) quizContent.classList.remove('hidden');
    } finally {
        isGeneratingQuiz = false;
        hideLoading();
    }
}

function displayQuiz(quizContent, questionContainer) {
    if (!quizContent || !questionContainer) return;

    quizContent.classList.remove('hidden');

    // Update progress
    updateQuizProgress();

    // Display current question
    displayCurrentQuestion(questionContainer);
}

function updateQuizProgress() {
    const currentSpan = document.getElementById('quiz-current');
    const totalSpan = document.getElementById('quiz-total');
    const scoreSpan = document.getElementById('quiz-score');

    if (currentSpan) currentSpan.textContent = quizState.currentQuestionIndex + 1;
    if (totalSpan) totalSpan.textContent = quizState.questions.length;
    if (scoreSpan) scoreSpan.textContent = quizState.score;
}

function displayCurrentQuestion(container) {
    if (quizState.isComplete) {
        displayQuizResults(container);
        return;
    }

    const question = quizState.questions[quizState.currentQuestionIndex];

    // Validate question structure before rendering
    if (!question || !Array.isArray(question.options) || typeof question.correct_index !== 'number') {
        container.innerHTML = '<p class="error">Invalid question data. Please try generating a new quiz.</p>';
        return;
    }

    const questionNum = quizState.currentQuestionIndex + 1;
    const userAnswer = quizState.userAnswers[quizState.currentQuestionIndex];

    let html = `
        <div class="quiz-question-card">
            <div class="question-header">
                <h3>Question ${questionNum}</h3>
                ${question.difficulty ? `<span class="difficulty-badge difficulty-${question.difficulty}">${question.difficulty}</span>` : ''}
            </div>
            <p class="question-text">${escapeHtml(question.question)}</p>
            ${question.articles && question.articles.length > 0 ? `
                <div class="question-articles">
                    <strong>Related Articles:</strong> ${question.articles.map(a => escapeHtml(a)).join(', ')}
                </div>
            ` : ''}
            <div class="quiz-options">
                ${question.options.map((option, index) => `
                    <button
                        class="quiz-option ${userAnswer === index ? 'selected' : ''}"
                        data-answer-index="${index}"
                        ${userAnswer !== null ? 'disabled' : ''}
                    >
                        <span class="option-letter">${String.fromCharCode(65 + index)}</span>
                        <span class="option-text">${escapeHtml(option)}</span>
                    </button>
                `).join('')}
            </div>
            ${userAnswer !== null ? `
                <div class="answer-feedback ${userAnswer === question.correct_index ? 'correct' : 'incorrect'}">
                    <strong>${userAnswer === question.correct_index ? '✓ Correct!' : '✗ Incorrect'}</strong>
                    ${question.explanation ? `<p>${escapeHtml(question.explanation)}</p>` : ''}
                    ${userAnswer !== question.correct_index ? `<p><strong>Correct answer:</strong> ${String.fromCharCode(65 + question.correct_index)}) ${escapeHtml(question.options[question.correct_index])}</p>` : ''}
                </div>
            ` : ''}
            <div class="quiz-navigation">
                <button
                    class="btn btn-secondary nav-prev-btn"
                    ${quizState.currentQuestionIndex === 0 ? 'disabled' : ''}
                >
                    ← Previous
                </button>
                <button
                    class="btn btn-primary nav-next-btn"
                    ${userAnswer === null ? 'disabled' : ''}
                >
                    ${quizState.currentQuestionIndex === quizState.questions.length - 1 ? 'Finish Quiz' : 'Next →'}
                </button>
            </div>
        </div>
    `;

    container.innerHTML = html;

    // Use event delegation on the container to avoid memory leaks from per-element listeners
    container.addEventListener('click', handleQuizContainerClick);
}

/**
 * Event delegation handler for quiz container clicks.
 * Handles all button clicks within the quiz question container.
 */
function handleQuizContainerClick(event) {
    const target = event.target;

    // Handle quiz option selection
    const optionBtn = target.closest('.quiz-option');
    if (optionBtn && !optionBtn.disabled) {
        const index = parseInt(optionBtn.dataset.answerIndex, 10);
        selectAnswer(index);
        return;
    }

    // Handle previous button
    if (target.closest('.nav-prev-btn') && !target.closest('.nav-prev-btn').disabled) {
        previousQuestion();
        return;
    }

    // Handle next button
    if (target.closest('.nav-next-btn') && !target.closest('.nav-next-btn').disabled) {
        nextQuestion();
        return;
    }
}

function selectAnswer(answerIndex) {
    if (quizState.userAnswers[quizState.currentQuestionIndex] !== null) {
        return; // Already answered
    }

    const question = quizState.questions[quizState.currentQuestionIndex];

    // Validate answerIndex is within bounds
    if (typeof answerIndex !== 'number' || answerIndex < 0 || answerIndex >= question.options.length) {
        console.error('Invalid answer index:', answerIndex);
        return;
    }

    quizState.userAnswers[quizState.currentQuestionIndex] = answerIndex;

    // Update score if correct
    if (answerIndex === question.correct_index) {
        quizState.score++;
    }

    // Always update progress display after answering
    updateQuizProgress();

    // Re-render to show feedback
    const container = document.getElementById('quiz-question-container');
    if (container) {
        displayCurrentQuestion(container);
    }
}

function previousQuestion() {
    if (quizState.currentQuestionIndex > 0) {
        quizState.currentQuestionIndex--;
        updateQuizProgress();
        const container = document.getElementById('quiz-question-container');
        if (container) {
            displayCurrentQuestion(container);
        }
    }
}

function nextQuestion() {
    if (quizState.currentQuestionIndex < quizState.questions.length - 1) {
        quizState.currentQuestionIndex++;
        updateQuizProgress();
        const container = document.getElementById('quiz-question-container');
        if (container) {
            displayCurrentQuestion(container);
        }
    } else {
        // Quiz complete
        quizState.isComplete = true;

        // Submit results to backend
        submitQuizResults();

        const container = document.getElementById('quiz-question-container');
        if (container) {
            displayQuizResults(container);
        }
    }
}

async function submitQuizResults() {
    // Only submit if we have both quiz ID and course ID (persisted quiz)
    if (!quizState.quizId || !quizState.courseId) {
        console.log('Quiz not persisted or missing course ID, skipping result submission');
        return;
    }

    const timeTaken = quizState.startTime
        ? Math.round((Date.now() - quizState.startTime) / 1000)
        : null;

    try {
        const response = await fetch(`${API_BASE}/api/quizzes/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': getUserId()
            },
            body: JSON.stringify({
                quiz_id: quizState.quizId,
                course_id: quizState.courseId,
                answers: quizState.userAnswers,
                user_id: getUserId(),
                time_taken_seconds: timeTaken
            })
        });

        if (!response.ok) {
            console.error('Failed to submit quiz results:', response.status);
            return;
        }

        const data = await response.json();
        console.log('Quiz results submitted:', data);

        // Update local stats
        updateLocalQuizStats();

    } catch (error) {
        console.error('Error submitting quiz results:', error);
    }
}

function updateLocalQuizStats() {
    const currentQuizzes = parseInt(localStorage.getItem('lls_quizzes') || '0');
    localStorage.setItem('lls_quizzes', currentQuizzes + 1);

    // Update points based on score
    const currentPoints = parseInt(localStorage.getItem('lls_points') || '0');
    localStorage.setItem('lls_points', currentPoints + quizState.score * 10);
}

function displayQuizResults(container) {
    const totalQuestions = quizState.questions.length;
    const correctAnswers = quizState.score;
    const percentage = Math.round((correctAnswers / totalQuestions) * 100);

    let performanceMessage = '';
    let performanceClass = '';

    if (percentage >= 90) {
        performanceMessage = 'Excellent! You have mastered this material!';
        performanceClass = 'excellent';
    } else if (percentage >= 70) {
        performanceMessage = 'Good job! You have a solid understanding.';
        performanceClass = 'good';
    } else if (percentage >= 50) {
        performanceMessage = 'Not bad, but there\'s room for improvement.';
        performanceClass = 'average';
    } else {
        performanceMessage = 'Keep studying! Review the material and try again.';
        performanceClass = 'needs-improvement';
    }

    let html = `
        <div class="quiz-results ${performanceClass}">
            <div class="results-header">
                <h2>Quiz Complete!</h2>
                <div class="results-score">
                    <div class="score-circle">
                        <span class="score-percentage">${percentage}%</span>
                        <span class="score-fraction">${correctAnswers}/${totalQuestions}</span>
                    </div>
                </div>
                <p class="performance-message">${performanceMessage}</p>
            </div>

            <div class="results-breakdown">
                <h3>Question Review</h3>
                <div class="question-list">
                    ${quizState.questions.map((q, index) => {
                        const userAnswer = quizState.userAnswers[index];
                        const isCorrect = userAnswer === q.correct_index;
                        const isValidAnswer = userAnswer !== null && userAnswer >= 0 && userAnswer < q.options.length;
                        const userAnswerText = isValidAnswer
                            ? `${String.fromCharCode(65 + userAnswer)}) ${escapeHtml(q.options[userAnswer])}`
                            : 'No answer';
                        return `
                            <div class="question-summary ${isCorrect ? 'correct' : 'incorrect'}">
                                <div class="question-summary-header">
                                    <span class="question-number">Q${index + 1}</span>
                                    <span class="question-result">${isCorrect ? '✓' : '✗'}</span>
                                </div>
                                <p class="question-summary-text">${escapeHtml(q.question)}</p>
                                <div class="question-summary-answers">
                                    <p><strong>Your answer:</strong> ${userAnswerText}</p>
                                    ${!isCorrect ? `<p><strong>Correct answer:</strong> ${String.fromCharCode(65 + q.correct_index)}) ${escapeHtml(q.options[q.correct_index])}</p>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>

            <div class="results-actions">
                <button class="btn btn-primary restart-quiz-btn">Take Another Quiz</button>
                <button class="btn btn-secondary review-quiz-btn">Review Answers</button>
            </div>
        </div>
    `;

    container.innerHTML = html;

    // Use event delegation for results buttons
    container.addEventListener('click', handleResultsContainerClick);
}

/**
 * Event delegation handler for quiz results container clicks.
 */
function handleResultsContainerClick(event) {
    if (event.target.closest('.restart-quiz-btn')) {
        restartQuiz();
        return;
    }

    if (event.target.closest('.review-quiz-btn')) {
        reviewQuiz();
        return;
    }
}

function restartQuiz() {
    // Reset state
    quizState = {
        quizId: null,
        courseId: null,
        questions: [],
        currentQuestionIndex: 0,
        userAnswers: [],
        score: 0,
        isComplete: false,
        startTime: null
    };

    // Go back to quiz list
    backToQuizList();

    // Scroll to quiz section
    const quizSection = document.getElementById('quiz-section');
    if (quizSection) {
        quizSection.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Review quiz answers after completion.
 * This shows questions in read-only mode with the user's previous answers preserved.
 * Users can navigate through questions to see their answers and the correct ones.
 * Note: userAnswers are intentionally NOT reset - this is review mode, not retake mode.
 * To retake the quiz with new questions, use restartQuiz() instead.
 */
function reviewQuiz() {
    quizState.currentQuestionIndex = 0;
    quizState.isComplete = false;

    const container = document.getElementById('quiz-question-container');
    if (container) {
        displayCurrentQuestion(container);
    }
}

// ========== Study Guide Generator ==========
function initStudyListeners() {
    document.getElementById('generate-study-btn').addEventListener('click', generateStudyGuide);
}

async function generateStudyGuide() {
    const resultDiv = document.getElementById('study-result');

    showLoading();

    try {
        // Build request with course context (course_id will be added if available)
        const requestBody = addCourseContext({});

        const response = await fetch(`${API_BASE}/api/files-content/study-guide`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `API error: ${response.status}`;
            throw new Error(errorMessage);
        }

        const data = await response.json();
        resultDiv.innerHTML = `<div class="study-guide">${formatMarkdown(data.guide)}</div>`;
        resultDiv.style.display = 'block';

    } catch (error) {
        console.error('Error:', error);
        // Backend now provides user-friendly error messages directly
        const errorMessage = error.message || 'Error generating study guide. Please try again.';
        resultDiv.innerHTML = `<p class="error">${escapeHtml(errorMessage)}</p>`;
        resultDiv.style.display = 'block';
    } finally {
        hideLoading();
    }
}

// ========== Dashboard ==========
// Helper to safely parse integer from localStorage with NaN validation
function safeParseInt(value, fallback = 0) {
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? fallback : parsed;
}

function initDashboard() {
    // Add course-specific information banner to dashboard
    const dashboardSection = document.getElementById('dashboard-section');
    if (dashboardSection && COURSE_ID) {
        // Check if course info banner already exists
        let courseInfoBanner = dashboardSection.querySelector('.course-info-banner');
        if (!courseInfoBanner) {
            courseInfoBanner = document.createElement('div');
            courseInfoBanner.className = 'course-info-banner';
            // Use CSS classes instead of inline styles for CSP compliance
            courseInfoBanner.innerHTML = `
                <span class="course-info-icon">📚</span>
                <div class="course-info-text">
                    <div class="course-info-name">Active Course: ${escapeHtml(COURSE_NAME)}</div>
                    <div class="course-info-id">Course ID: ${escapeHtml(COURSE_ID)}</div>
                </div>
                <span class="course-info-badge">✓ Course-Specific Content</span>
            `;
            // Insert at the top of the dashboard section
            const sectionTitle = dashboardSection.querySelector('.section-title');
            if (sectionTitle && sectionTitle.nextSibling) {
                dashboardSection.insertBefore(courseInfoBanner, sectionTitle.nextSibling);
            } else {
                dashboardSection.insertBefore(courseInfoBanner, dashboardSection.firstChild);
            }
        }
    }

    // Validate topics format (should be like "2/5")
    const topicsValue = localStorage.getItem('lls_topics');
    const validTopics = topicsValue && /^\d+\/\d+$/.test(topicsValue) ? topicsValue : '0/5';

    const stats = {
        points: safeParseInt(localStorage.getItem('lls_points')),
        streak: safeParseInt(localStorage.getItem('lls_streak')),
        topics: validTopics,
        quizzes: safeParseInt(localStorage.getItem('lls_quizzes'))
    };

    // Safely update DOM elements with null checks
    const statPoints = document.getElementById('stat-points');
    const statStreak = document.getElementById('stat-streak');
    const statTopics = document.getElementById('stat-topics');
    const statQuizzes = document.getElementById('stat-quizzes');

    if (statPoints) statPoints.textContent = stats.points;
    if (statStreak) statStreak.textContent = stats.streak;
    if (statTopics) statTopics.textContent = stats.topics;
    if (statQuizzes) statQuizzes.textContent = stats.quizzes;

    // Add topic card click handlers with context passing
    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const topic = card.dataset.topic;
            const tutorTab = document.querySelector('.nav-tab[data-tab="tutor"]');
            if (tutorTab) tutorTab.click();

            // Set the context select to match the clicked topic
            const contextSelect = document.getElementById('context-select');
            if (contextSelect && topic) {
                const topicMap = {
                    'criminal': 'Criminal Law',
                    'private': 'Private Law',
                    'constitutional': 'Constitutional Law',
                    'administrative': 'Administrative Law',
                    'international': 'International Law'
                };
                if (topicMap[topic]) {
                    contextSelect.value = topicMap[topic];
                }
            }
        });
    });
}

// ========== Flashcards ==========
// Course-aware flashcard system - loads flashcards dynamically from backend API
// Flashcards are generated from actual course materials using FilesAPIService

// Constants
const DEFAULT_FLASHCARD_COUNT = 20;

// State
let flashcards = [];
let currentCardIndex = 0;
let isLoadingFlashcards = false;

/**
 * Initialize event listeners for flashcard navigation and interaction
 */
function initFlashcardListeners() {
    const flipBtn = document.getElementById('flip-card-btn');
    const prevBtn = document.getElementById('prev-card-btn');
    const nextBtn = document.getElementById('next-card-btn');
    const knowBtn = document.getElementById('know-btn');
    const studyBtn = document.getElementById('study-btn');
    const categorySelect = document.getElementById('flashcard-category');
    const loadBtn = document.getElementById('load-flashcards-btn');

    if (flipBtn) flipBtn.addEventListener('click', flipCard);
    if (prevBtn) prevBtn.addEventListener('click', () => navigateCard(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateCard(1));
    if (knowBtn) knowBtn.addEventListener('click', () => markCard('known'));
    if (studyBtn) studyBtn.addEventListener('click', () => markCard('study'));
    if (categorySelect) categorySelect.addEventListener('change', filterFlashcards);
    if (loadBtn) loadBtn.addEventListener('click', loadFlashcards);

    // Load flashcards on init if course is selected
    if (COURSE_ID) {
        loadFlashcards();
    }
}

/**
 * Load flashcards from backend API using course context
 */
async function loadFlashcards() {
    // Prevent multiple simultaneous requests
    if (isLoadingFlashcards) {
        console.log('Flashcards already loading');
        showFlashcardError('Flashcards are already loading. Please wait...');
        return;
    }

    if (!COURSE_ID) {
        showFlashcardError('No course selected. Please select a course first.');
        return;
    }

    isLoadingFlashcards = true;
    showFlashcardLoading();

    try {
        // Build request with course context
        const requestBody = addCourseContext({
            num_cards: DEFAULT_FLASHCARD_COUNT
        });

        const response = await fetch(`${API_BASE}/api/files-content/flashcards`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `API error: ${response.status}`;
            throw new Error(errorMessage);
        }

        const data = await response.json();

        // Validate response format
        if (!data.flashcards || !Array.isArray(data.flashcards)) {
            throw new Error('Invalid flashcards format from server');
        }

        if (data.flashcards.length === 0) {
            throw new Error('No flashcards generated. Please try again.');
        }

        // Transform backend format (front/back) to frontend format (question/answer)
        flashcards = data.flashcards.map(card => ({
            question: card.front || card.question || 'No question',
            answer: card.back || card.answer || 'No answer',
            category: 'course',  // All course-specific flashcards
            known: false
        }));

        currentCardIndex = 0;
        hideFlashcardLoading();
        updateFlashcardDisplay();
        updateFlashcardStats();

        console.log(`Loaded ${flashcards.length} flashcards for course ${COURSE_ID}`);

    } catch (error) {
        console.error('Error loading flashcards:', error);
        showFlashcardError(error.message || 'Error loading flashcards. Please try again.');
        // Add debounce on error to prevent rapid retries that could DDoS the backend
        // Don't reset flag immediately - wait 2 seconds
        setTimeout(() => {
            isLoadingFlashcards = false;
        }, 2000);
        return; // Exit early so finally block doesn't reset flag
    } finally {
        // Only reset immediately on success (no error thrown)
        isLoadingFlashcards = false;
    }
}

/**
 * Filter flashcards by category (for future use if categories are added)
 */
function filterFlashcards() {
    const category = document.getElementById('flashcard-category')?.value;
    if (!category || category === 'all') {
        updateFlashcardDisplay();
        updateFlashcardStats();
        return;
    }

    // Filter logic can be added here if categories are implemented
    updateFlashcardDisplay();
    updateFlashcardStats();
}

/**
 * Show loading state for flashcards
 */
function showFlashcardLoading() {
    const questionEl = document.getElementById('flashcard-question');
    const answerEl = document.getElementById('flashcard-answer');

    if (questionEl) questionEl.textContent = 'Loading flashcards from course materials...';
    if (answerEl) answerEl.textContent = 'Please wait...';

    // Disable navigation buttons
    const buttons = ['flip-card-btn', 'prev-card-btn', 'next-card-btn', 'know-btn', 'study-btn'];
    buttons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = true;
    });
}

/**
 * Hide loading state for flashcards
 */
function hideFlashcardLoading() {
    // Enable navigation buttons
    const buttons = ['flip-card-btn', 'prev-card-btn', 'next-card-btn', 'know-btn', 'study-btn'];
    buttons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = false;
    });
}

/**
 * Show error message for flashcards
 */
function showFlashcardError(message) {
    const questionEl = document.getElementById('flashcard-question');
    const answerEl = document.getElementById('flashcard-answer');

    if (questionEl) questionEl.textContent = 'Error';
    if (answerEl) answerEl.innerHTML = `<span class="error">${escapeHtml(message)}</span>`;

    flashcards = [];
    updateFlashcardStats();
}

function flipCard() {
    const flashcard = document.getElementById('flashcard');
    if (flashcard) {
        flashcard.classList.toggle('flipped');
    }
}

function navigateCard(direction) {
    // Don't navigate if no flashcards available
    if (flashcards.length === 0) {
        return;
    }

    currentCardIndex += direction;
    if (currentCardIndex < 0) currentCardIndex = flashcards.length - 1;
    if (currentCardIndex >= flashcards.length) currentCardIndex = 0;

    const flashcard = document.getElementById('flashcard');
    if (flashcard) {
        flashcard.classList.remove('flipped');
    }
    updateFlashcardDisplay();
}

function markCard(status) {
    if (flashcards[currentCardIndex]) {
        flashcards[currentCardIndex].known = (status === 'known');
        updateFlashcardStats();
        navigateCard(1);
    }
}

function updateFlashcardDisplay() {
    const questionEl = document.getElementById('flashcard-question');
    const answerEl = document.getElementById('flashcard-answer');

    if (flashcards.length === 0) {
        if (questionEl) questionEl.textContent = 'No flashcards available';
        if (answerEl) answerEl.textContent = '';
        return;
    }

    const card = flashcards[currentCardIndex];
    if (questionEl) questionEl.textContent = card.question;
    if (answerEl) answerEl.textContent = card.answer;
}

function updateFlashcardStats() {
    const mastered = flashcards.filter(card => card.known).length;
    const masteredEl = document.getElementById('cards-mastered');
    const totalEl = document.getElementById('cards-total');

    if (masteredEl) masteredEl.textContent = mastered;
    if (totalEl) totalEl.textContent = flashcards.length;
}
