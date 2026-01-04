// app.js - Frontend JavaScript for LLS Study Portal

const API_BASE = '';  // Empty for same origin

// ========== Tab Navigation ==========
document.addEventListener('DOMContentLoaded', () => {
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
            body: JSON.stringify({message, context})
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
            body: JSON.stringify({topic, question: question || null, answer})
        });
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        const data = await response.json();
        resultDiv.innerHTML = `
            <div class="assessment-feedback">
                ${formatMarkdown(data.feedback)}
            </div>
        `;
        resultDiv.style.display = 'block';
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<p class="error">Error getting assessment. Please try again.</p>';
    } finally {
        hideLoading();
    }
}

// ========== Quiz Generator ==========
function initQuizListeners() {
    const startBtn = document.getElementById('start-quiz-btn');
    if (startBtn) startBtn.addEventListener('click', generateQuiz);
}

async function generateQuiz() {
    const topicSelect = document.getElementById('quiz-topic-select');
    const topic = topicSelect ? topicSelect.value : 'all';
    const num_questions = 5; // Default to 5 questions
    const quizContent = document.getElementById('quiz-content');
    const questionContainer = document.getElementById('quiz-question-container');
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/files-content/quiz`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({topic, num_questions, difficulty: 'medium'})
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);

        const data = await response.json();
        displayQuiz(data.quiz, quizContent, questionContainer);

    } catch (error) {
        console.error('Error:', error);
        if (questionContainer) {
            questionContainer.innerHTML = '<p class="error">Error generating quiz. Please try again.</p>';
        }
        if (quizContent) quizContent.classList.remove('hidden');
    } finally {
        hideLoading();
    }
}

function displayQuiz(quiz, quizContent, questionContainer) {
    if (!quizContent || !questionContainer) return;

    quizContent.classList.remove('hidden');

    // Update totals
    const totalSpan = document.getElementById('quiz-total');
    if (totalSpan) totalSpan.textContent = quiz.length || 5;

    // Display the quiz content
    if (typeof quiz === 'string') {
        questionContainer.innerHTML = `<div class="quiz-generated">${formatMarkdown(quiz)}</div>`;
    } else if (Array.isArray(quiz)) {
        let quizHtml = '';
        quiz.forEach((q, i) => {
            quizHtml += `<div class="quiz-question"><h4>Question ${i + 1}</h4><p>${escapeHtml(q.question || q)}</p></div>`;
        });
        questionContainer.innerHTML = quizHtml;
    } else {
        questionContainer.innerHTML = formatMarkdown(JSON.stringify(quiz, null, 2));
    }
}

// ========== Study Guide Generator ==========
function initStudyListeners() {
    document.getElementById('generate-study-btn').addEventListener('click', generateStudyGuide);
}

async function generateStudyGuide() {
    const topic = document.getElementById('study-topic').value;
    const resultDiv = document.getElementById('study-result');
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/files-content/study-guide`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({topic})
        });
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        const data = await response.json();
        resultDiv.innerHTML = `<div class="study-guide">${formatMarkdown(data.guide)}</div>`;
        resultDiv.style.display = 'block';
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<p class="error">Error generating study guide. Please try again.</p>';
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
// NOTE: Flashcard data is currently static for the MVP.
// TODO: Issue #XX - Implement /api/files-content/flashcards endpoint to load flashcards dynamically
// TODO: Persist flashcard progress (known/unknown) to localStorage

let flashcards = [];
let currentCardIndex = 0;

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

    if (flipBtn) flipBtn.addEventListener('click', flipCard);
    if (prevBtn) prevBtn.addEventListener('click', () => navigateCard(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateCard(1));
    if (knowBtn) knowBtn.addEventListener('click', () => markCard('known'));
    if (studyBtn) studyBtn.addEventListener('click', () => markCard('study'));
    if (categorySelect) categorySelect.addEventListener('change', loadFlashcards);

    loadFlashcards();
}

function loadFlashcards() {
    flashcards = [
        {question: "What is the principle of legality in criminal law?", answer: "No punishment without law (nullum crimen sine lege). A person can only be punished if their act was criminally punishable at the time it was committed.", category: "criminal", known: false},
        {question: "What are the three elements of a crime?", answer: "1) Actus reus (criminal act), 2) Mens rea (criminal intent), 3) No justification or excuse", category: "criminal", known: false},
        {question: "What is breach of contract?", answer: "Failure to perform a contractual obligation without lawful excuse. It gives rise to remedies including damages, specific performance, or termination.", category: "private", known: false},
        {question: "What is the Trias Politica?", answer: "The separation of powers into three branches: Legislative (makes laws), Executive (enforces laws), and Judicial (interprets laws).", category: "constitutional", known: false},
        {question: "What is an administrative order (beschikking)?", answer: "A written decision by an administrative authority concerning a public law matter, directed at a specific person or situation.", category: "administrative", known: false}
    ];

    const category = document.getElementById('flashcard-category').value;
    if (category !== 'all') {
        flashcards = flashcards.filter(card => card.category === category);
    }

    currentCardIndex = 0;
    updateFlashcardDisplay();
    updateFlashcardStats();
}

function flipCard() {
    document.getElementById('flashcard').classList.toggle('flipped');
}

function navigateCard(direction) {
    currentCardIndex += direction;
    if (currentCardIndex < 0) currentCardIndex = flashcards.length - 1;
    if (currentCardIndex >= flashcards.length) currentCardIndex = 0;

    document.getElementById('flashcard').classList.remove('flipped');
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
