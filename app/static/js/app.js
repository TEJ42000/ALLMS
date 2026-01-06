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
// Configure marked.js for rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });
}

// Initialize Mermaid for diagram rendering
if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose'
    });
}

/**
 * Pre-process text to wrap ASCII art diagrams in code fences
 * Detects box-drawing characters and wraps them properly
 */
function preprocessAsciiArt(text) {
    if (!text) return text;

    // Box-drawing characters pattern
    const boxChars = /[┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬]/;

    const lines = text.split('\n');
    const result = [];
    let inAsciiBlock = false;
    let asciiBuffer = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const hasBoxChars = boxChars.test(line);

        if (hasBoxChars && !inAsciiBlock) {
            // Start of ASCII art block
            inAsciiBlock = true;
            asciiBuffer = [line];
        } else if (hasBoxChars && inAsciiBlock) {
            // Continue ASCII art block
            asciiBuffer.push(line);
        } else if (!hasBoxChars && inAsciiBlock) {
            // End of ASCII art block - wrap in code fence
            result.push('```');
            result.push(...asciiBuffer);
            result.push('```');
            result.push(line);
            inAsciiBlock = false;
            asciiBuffer = [];
        } else {
            result.push(line);
        }
    }

    // Handle case where ASCII art is at the end
    if (inAsciiBlock && asciiBuffer.length > 0) {
        result.push('```');
        result.push(...asciiBuffer);
        result.push('```');
    }

    return result.join('\n');
}

/**
 * Format markdown text using marked.js library
 * Falls back to simple formatting if marked is not available
 */
function formatMarkdown(text) {
    if (!text) return '';

    // Pre-process to wrap ASCII art in code fences
    text = preprocessAsciiArt(text);

    // Use marked.js if available
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Marked.js error:', e);
            return formatMarkdownFallback(text);
        }
    }

    return formatMarkdownFallback(text);
}

/**
 * Render Mermaid diagrams in a container
 * Call this after inserting HTML with mermaid code blocks
 */
async function renderMermaidDiagrams(container) {
    if (typeof mermaid === 'undefined') return;

    // Mermaid diagram type keywords
    const mermaidKeywords = [
        'graph ', 'graph\n', 'flowchart ', 'flowchart\n',
        'sequenceDiagram', 'classDiagram', 'stateDiagram',
        'erDiagram', 'gantt', 'pie', 'journey', 'gitGraph',
        'mindmap', 'timeline', 'quadrantChart', 'xychart'
    ];

    // Find all code blocks that might be mermaid
    const codeBlocks = container.querySelectorAll('pre code');
    for (const block of codeBlocks) {
        const text = block.textContent.trim();

        // Check if text contains mermaid keywords (anywhere, not just at start)
        // This handles cases where there's a title before the diagram definition
        const isMermaid = mermaidKeywords.some(keyword => text.includes(keyword));

        if (isMermaid) {
            try {
                const pre = block.parentElement;
                const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);

                // Extract just the mermaid code (skip title lines before graph/flowchart)
                let mermaidCode = text;
                const lines = text.split('\n');
                const diagramStartIndex = lines.findIndex(line =>
                    mermaidKeywords.some(kw => line.trim().startsWith(kw.trim()))
                );
                if (diagramStartIndex > 0) {
                    // There's a title - extract just the diagram part
                    mermaidCode = lines.slice(diagramStartIndex).join('\n');
                }

                const { svg } = await mermaid.render(id, mermaidCode);

                // Create container with optional title
                const div = document.createElement('div');
                div.className = 'mermaid-container';

                // Add title if present
                if (diagramStartIndex > 0) {
                    const title = lines.slice(0, diagramStartIndex).join(' ').trim();
                    if (title) {
                        const titleEl = document.createElement('div');
                        titleEl.className = 'mermaid-title';
                        titleEl.textContent = title;
                        div.appendChild(titleEl);
                    }
                }

                const diagramDiv = document.createElement('div');
                diagramDiv.className = 'mermaid';
                diagramDiv.innerHTML = svg;
                div.appendChild(diagramDiv);

                pre.replaceWith(div);
            } catch (e) {
                console.warn('Mermaid rendering failed:', e);
                // Leave the code block as-is for debugging
            }
        }
    }
}

/**
 * Fallback simple markdown formatting when marked.js is not available
 */
function formatMarkdownFallback(text) {
    if (!text) return '';

    const lines = text.split('\n');
    let html = '';
    let inList = false;
    let inNumberedList = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        if (line.trim() === '') {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += '<br>';
            continue;
        }

        // Headers
        if (line.startsWith('# ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<h1>${escapeHtml(line.substring(2))}</h1>`;
            continue;
        }
        if (line.startsWith('## ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<h2>${escapeHtml(line.substring(3))}</h2>`;
            continue;
        }
        if (line.startsWith('### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            html += `<h3>${escapeHtml(line.substring(4))}</h3>`;
            continue;
        }

        // Bullet lists
        if (line.match(/^[•\-\*] /)) {
            if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${formatInline(line.substring(2))}</li>`;
            continue;
        }

        // Numbered lists
        if (line.match(/^\d+\. /)) {
            if (inList) { html += '</ul>'; inList = false; }
            if (!inNumberedList) { html += '<ol>'; inNumberedList = true; }
            const content = line.replace(/^\d+\. /, '');
            html += `<li>${formatInline(content)}</li>`;
            continue;
        }

        // Regular paragraph
        if (inList) { html += '</ul>'; inList = false; }
        if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
        html += `<p>${formatInline(line)}</p>`;
    }

    if (inList) html += '</ul>';
    if (inNumberedList) html += '</ol>';

    return html;
}

// Format inline markdown (bold, italic, code, etc.)
function formatInline(text) {
    text = escapeHtml(text);
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
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
    const contextSelect = document.getElementById('context-select');
    const contextValue = contextSelect.value;
    const messagesDiv = document.getElementById('chat-messages');

    if (!message) return;

    // Parse context value to extract week number if present
    // Format from template: "Week X: Topic Name" stored as topic name,
    // but option value could be topic name directly
    let context = contextValue;
    let week_number = null;

    // Check if a week-specific option was selected by looking at the option text
    const selectedOption = contextSelect.options[contextSelect.selectedIndex];
    if (selectedOption && selectedOption.text.startsWith('Week ')) {
        // Extract week number from "Week X: Topic Name"
        const weekMatch = selectedOption.text.match(/^Week (\d+):/);
        if (weekMatch) {
            week_number = parseInt(weekMatch[1]);
        }
    }

    // Add user message
    addMessage('user', message);
    document.getElementById('tutor-input').value = '';

    // Show typing indicator (bouncing dots)
    showTypingIndicator();

    try {
        // Build request with optional week_number
        const requestBody = addCourseContext({message, context});
        if (week_number !== null) {
            requestBody.week_number = week_number;
        }

        const response = await fetch(`${API_BASE}/api/tutor/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);

        const data = await response.json();

        // Hide typing indicator and show response
        hideTypingIndicator();
        addMessage('assistant', data.content);

    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        addMessage('error', 'Sorry, there was an error processing your request.');
    }
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');

    // Create wrapper for avatar + message bubble layout
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = `message-wrapper ${role}`;

    // Create avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    if (role === 'user') {
        avatarDiv.textContent = '👤';
    } else if (role === 'assistant') {
        avatarDiv.textContent = '🤖';
    } else {
        avatarDiv.textContent = '⚠️';
    }

    // Create message bubble
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = formatMarkdown(content);

    // Assemble
    wrapperDiv.appendChild(avatarDiv);
    wrapperDiv.appendChild(messageDiv);
    messagesDiv.appendChild(wrapperDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function showTypingIndicator() {
    const messagesDiv = document.getElementById('chat-messages');

    // Remove any existing typing indicator
    hideTypingIndicator();

    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typing-indicator';

    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;

    messagesDiv.appendChild(typingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// ========== Essay Assessment ==========
// Essay assessment state
let essayState = {
    assessmentId: null,
    question: null,
    topic: null,
    keyConcepts: []
};

// EasyMDE editor instance
let essayEditor = null;

function initAssessmentListeners() {
    // Tab navigation
    document.querySelectorAll('.assessment-tab').forEach(tab => {
        tab.addEventListener('click', () => switchAssessmentTab(tab.dataset.assessmentTab));
    });

    // Generate question button
    const generateBtn = document.getElementById('generate-essay-btn');
    if (generateBtn) generateBtn.addEventListener('click', generateEssayQuestion);

    // Submit essay button
    const submitBtn = document.getElementById('submit-essay-btn');
    if (submitBtn) submitBtn.addEventListener('click', submitEssayAnswer);

    // New question button
    const newQuestionBtn = document.getElementById('new-question-btn');
    if (newQuestionBtn) newQuestionBtn.addEventListener('click', showGenerateView);

    // Initialize EasyMDE editor for essay answer
    initEssayEditor();
}

function initEssayEditor() {
    const essayTextarea = document.getElementById('essay-answer');
    if (!essayTextarea || typeof EasyMDE === 'undefined') return;

    essayEditor = new EasyMDE({
        element: essayTextarea,
        placeholder: 'Write your essay answer here using Markdown formatting...\n\n**Bold** for emphasis\n*Italic* for subtle emphasis\n- Bullet points for lists\n1. Numbered lists for steps\n\n### Use headings to structure your answer',
        spellChecker: false,
        autosave: {
            enabled: false
        },
        toolbar: [
            'bold', 'italic', 'heading', '|',
            'unordered-list', 'ordered-list', '|',
            'preview', 'side-by-side', 'fullscreen', '|',
            'guide'
        ],
        status: ['words', 'lines'],
        minHeight: '300px',
        maxHeight: '600px',
        sideBySideFullscreen: false,
        shortcuts: {
            toggleBold: 'Cmd-B',
            toggleItalic: 'Cmd-I',
            toggleHeadingSmaller: 'Cmd-H',
            toggleUnorderedList: 'Cmd-L',
            toggleOrderedList: 'Cmd-Alt-L',
            togglePreview: 'Cmd-P',
            toggleSideBySide: 'F9',
            toggleFullScreen: 'F11'
        },
        previewRender: function(plainText) {
            // Use our existing formatMarkdown function for preview
            return formatMarkdown(plainText);
        }
    });

    // Update word count when editor content changes
    essayEditor.codemirror.on('change', () => {
        updateWordCount();
    });
}

function switchAssessmentTab(tabName) {
    // Update active tab
    document.querySelectorAll('.assessment-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.assessmentTab === tabName);
    });

    // Show corresponding content
    document.getElementById('new-essay-tab').style.display = tabName === 'new' ? 'block' : 'none';
    document.getElementById('essay-history-tab').style.display = tabName === 'history' ? 'block' : 'none';

    // Load history if switching to history tab
    if (tabName === 'history') {
        loadEssayHistory();
    }
}

function showGenerateView() {
    document.getElementById('generate-question-view').style.display = 'block';
    document.getElementById('essay-question-view').style.display = 'none';
    document.getElementById('essay-result').innerHTML = '';
    essayState = { assessmentId: null, question: null, topic: null, keyConcepts: [] };

    // Clear editor content
    if (essayEditor) {
        essayEditor.value('');
    }
}

function updateWordCount() {
    // Get content from EasyMDE editor or fallback to textarea
    const answer = essayEditor ? essayEditor.value().trim() : document.getElementById('essay-answer').value.trim();
    const wordCount = answer ? answer.split(/\s+/).filter(w => w.length > 0).length : 0;
    document.getElementById('essay-word-count').textContent = wordCount;
}

async function generateEssayQuestion() {
    const topic = document.getElementById('essay-topic-select').value;
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/assessment/essay/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': getUserId()
            },
            body: JSON.stringify({
                course_id: COURSE_ID,
                topic: topic
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Store state
        essayState.assessmentId = data.assessment_id;
        essayState.question = data.question;
        essayState.topic = data.topic;
        essayState.keyConcepts = data.key_concepts || [];

        // Display question
        document.getElementById('essay-topic-badge').textContent = data.topic;
        document.getElementById('essay-question-text').textContent = data.question;

        // Show key concepts if available
        const conceptsDiv = document.getElementById('essay-key-concepts');
        if (data.key_concepts && data.key_concepts.length > 0) {
            conceptsDiv.innerHTML = '<strong>Key concepts to address:</strong> ' +
                data.key_concepts.map(c => `<span class="concept-tag">${escapeHtml(c)}</span>`).join(' ');
            conceptsDiv.style.display = 'block';
        } else {
            conceptsDiv.style.display = 'none';
        }

        // Show guidance if available
        const guidanceDiv = document.getElementById('essay-guidance');
        if (data.guidance) {
            guidanceDiv.innerHTML = `<em>💡 ${escapeHtml(data.guidance)}</em>`;
            guidanceDiv.style.display = 'block';
        } else {
            guidanceDiv.style.display = 'none';
        }

        // Switch to question view
        document.getElementById('generate-question-view').style.display = 'none';
        document.getElementById('essay-question-view').style.display = 'block';

        // Clear editor content
        if (essayEditor) {
            essayEditor.value('');
        } else {
            document.getElementById('essay-answer').value = '';
        }

        document.getElementById('essay-result').innerHTML = '';
        updateWordCount();

    } catch (error) {
        console.error('Error generating question:', error);
        alert(`Error generating question: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function submitEssayAnswer() {
    // Get answer from EasyMDE editor or fallback to textarea
    const answer = (essayEditor ? essayEditor.value() : document.getElementById('essay-answer').value).trim();
    const resultDiv = document.getElementById('essay-result');

    if (!answer) {
        alert('Please write your essay answer before submitting.');
        return;
    }

    if (answer.length < 100) {
        alert('Your answer seems too short. Please write a more detailed response (at least 100 characters).');
        return;
    }

    if (!essayState.assessmentId) {
        alert('No active assessment. Please generate a new question.');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/assessment/essay/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': getUserId()
            },
            body: JSON.stringify({
                assessment_id: essayState.assessmentId,
                course_id: COURSE_ID,
                answer: answer  // This is now Markdown format
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Display results
        let strengthsHtml = '';
        if (data.strengths && data.strengths.length > 0) {
            strengthsHtml = `
                <div class="essay-strengths">
                    <h4>✅ Strengths</h4>
                    <ul>${data.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>
                </div>
            `;
        }

        let improvementsHtml = '';
        if (data.improvements && data.improvements.length > 0) {
            improvementsHtml = `
                <div class="essay-improvements">
                    <h4>⚠️ Areas for Improvement</h4>
                    <ul>${data.improvements.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
                </div>
            `;
        }

        resultDiv.innerHTML = `
            <div class="essay-evaluation">
                <div class="essay-grade">
                    <span class="grade-number">${data.grade}</span>
                    <span class="grade-label">/10</span>
                </div>
                ${strengthsHtml}
                ${improvementsHtml}
                <div class="essay-feedback">
                    <h4>📝 Detailed Feedback</h4>
                    ${formatMarkdown(data.feedback)}
                </div>
            </div>
        `;
        resultDiv.style.display = 'block';
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error submitting essay:', error);
        resultDiv.innerHTML = `<p class="error">Error: ${escapeHtml(error.message)}</p>`;
        resultDiv.style.display = 'block';
    } finally {
        hideLoading();
    }
}

async function loadEssayHistory() {
    const historyList = document.getElementById('essay-history-list');
    historyList.innerHTML = '<p class="loading-text">Loading...</p>';

    try {
        const response = await fetch(`${API_BASE}/api/assessment/essay/my-history?course_id=${COURSE_ID}`, {
            headers: { 'X-User-ID': getUserId() }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        if (!data.history || data.history.length === 0) {
            historyList.innerHTML = `
                <div class="empty-state">
                    <p>📝 No essay assessments yet.</p>
                    <p>Complete your first essay to see your history here!</p>
                </div>
            `;
            return;
        }

        historyList.innerHTML = data.history.map(item => `
            <div class="essay-history-item" onclick="viewEssayAttempt('${item.attemptId}')">
                <div class="history-item-header">
                    <span class="history-topic">${escapeHtml(item.topic)}</span>
                    <span class="history-grade grade-${item.grade >= 7 ? 'good' : item.grade >= 5 ? 'ok' : 'low'}">${item.grade}/10</span>
                </div>
                <p class="history-question">${escapeHtml(item.question.substring(0, 100))}...</p>
                <span class="history-date">${new Date(item.submittedAt).toLocaleDateString()}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading history:', error);
        historyList.innerHTML = `<p class="error">Error loading history: ${escapeHtml(error.message)}</p>`;
    }
}

async function viewEssayAttempt(attemptId) {
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/assessment/essay/attempt/${attemptId}`, {
            headers: { 'X-User-ID': getUserId() }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        const attempt = data.attempt;

        // Create modal or detailed view
        const modal = document.createElement('div');
        modal.className = 'essay-modal';
        modal.innerHTML = `
            <div class="essay-modal-content">
                <button class="modal-close" onclick="this.closest('.essay-modal').remove()">&times;</button>
                <h3>Essay Attempt - ${attempt.grade}/10</h3>
                <div class="attempt-details">
                    <h4>Your Answer:</h4>
                    <div class="attempt-answer">${formatMarkdown(attempt.answer)}</div>
                    <h4>Feedback:</h4>
                    <div class="attempt-feedback">${formatMarkdown(attempt.feedback)}</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

    } catch (error) {
        console.error('Error viewing attempt:', error);
        alert(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function getUserId() {
    // Get or create a persistent user ID
    let userId = localStorage.getItem('lls_user_id');
    if (!userId) {
        userId = 'user-' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('lls_user_id', userId);
    }
    return userId;
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
    const topicValue = topicSelect ? topicSelect.value : 'all';
    const difficulty = difficultySelect ? difficultySelect.value : 'medium';
    const num_questions = numQuestionsSelect ? parseInt(numQuestionsSelect.value) : 10;

    // Parse topic value - if it starts with "week-", extract week number
    let topic = topicValue;
    let week = null;
    if (topicValue.startsWith('week-')) {
        week = parseInt(topicValue.replace('week-', ''));
        // Get the topic name from the selected option text
        const selectedOption = topicSelect.options[topicSelect.selectedIndex];
        if (selectedOption) {
            // Extract topic name after "Week X: "
            const optionText = selectedOption.text;
            const colonIndex = optionText.indexOf(': ');
            topic = colonIndex > 0 ? optionText.substring(colonIndex + 2) : topicValue;
        }
    }

    isGeneratingQuiz = true;
    showLoading();

    try {
        // Build request body with optional week filter
        const requestBody = {
            course_id: COURSE_ID,
            topic: topic,
            num_questions: num_questions,
            difficulty: difficulty,
            allow_duplicate: false
        };

        // Add week filter if a specific week was selected
        if (week !== null) {
            requestBody.week = week;
        }

        // Use the new quiz persistence API
        const response = await fetch(`${API_BASE}/api/quizzes/courses/${COURSE_ID}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': getUserId()
            },
            body: JSON.stringify(requestBody)
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

// ========== Study Guide Management ==========
function initStudyListeners() {
    // Generate button
    const generateBtn = document.getElementById('generate-study-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateStudyGuide);
    }

    // Estimate tokens button
    const estimateBtn = document.getElementById('estimate-tokens-btn');
    if (estimateBtn) {
        estimateBtn.addEventListener('click', estimateStudyGuideTokens);
    }

    // Sub-tab navigation
    const subTabs = document.querySelectorAll('[data-study-tab]');
    subTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.studyTab;

            // Update active tab
            subTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show corresponding content
            document.getElementById('saved-guides-tab').style.display =
                tabName === 'saved-guides' ? 'block' : 'none';
            document.getElementById('new-guide-tab').style.display =
                tabName === 'new-guide' ? 'block' : 'none';

            // Clear result when switching tabs
            document.getElementById('study-result').style.display = 'none';
            // Hide debug panel when switching tabs
            document.getElementById('token-debug-panel').style.display = 'none';
        });
    });

    // Load saved guides on init
    loadSavedStudyGuides();
}

/**
 * Estimate tokens for the selected week(s) before generating
 */
async function estimateStudyGuideTokens() {
    const debugPanel = document.getElementById('token-debug-panel');
    const debugContent = document.getElementById('token-debug-content');
    const weekSelect = document.getElementById('study-week-select');
    const estimateBtn = document.getElementById('estimate-tokens-btn');

    // Show loading state
    estimateBtn.disabled = true;
    estimateBtn.textContent = '⏳ Estimating...';

    try {
        // Build query params
        let url = `${API_BASE}/api/study-guides/courses/${COURSE_ID}/estimate-tokens`;
        if (weekSelect && weekSelect.value) {
            url += `?weeks=${weekSelect.value}`;
        }

        const response = await fetch(url, { method: 'POST' });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Build debug HTML
        const statusClass = data.will_exceed_rate_limit ? 'debug-warning' : 'debug-success';
        const statusIcon = data.will_exceed_rate_limit ? '⚠️' : '✅';

        let materialsHtml = data.materials.map(m => `
            <tr>
                <td>${escapeHtml(m.title)}</td>
                <td>Week ${m.week || 'N/A'}</td>
                <td>${m.characters.toLocaleString()}</td>
                <td>${m.estimated_tokens.toLocaleString()}</td>
            </tr>
        `).join('');

        debugContent.innerHTML = `
            <div class="debug-summary ${statusClass}">
                <strong>${statusIcon} ${data.recommendation}</strong>
            </div>
            <div class="debug-stats">
                <div class="debug-stat">
                    <span class="debug-label">Materials:</span>
                    <span class="debug-value">${data.material_count}</span>
                </div>
                <div class="debug-stat">
                    <span class="debug-label">Total Characters:</span>
                    <span class="debug-value">${data.total_characters.toLocaleString()}</span>
                </div>
                <div class="debug-stat">
                    <span class="debug-label">Estimated Input Tokens:</span>
                    <span class="debug-value">${data.estimated_input_tokens.toLocaleString()}</span>
                </div>
                <div class="debug-stat">
                    <span class="debug-label">Rate Limit:</span>
                    <span class="debug-value">${data.rate_limit.toLocaleString()} tokens/min</span>
                </div>
            </div>
            <table class="debug-table">
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Week</th>
                        <th>Characters</th>
                        <th>Est. Tokens</th>
                    </tr>
                </thead>
                <tbody>
                    ${materialsHtml}
                </tbody>
            </table>
        `;

        // Show and open the panel
        debugPanel.style.display = 'block';
        debugPanel.open = true;

    } catch (error) {
        console.error('Error estimating tokens:', error);
        debugContent.innerHTML = `<div class="debug-error">❌ Error: ${escapeHtml(error.message)}</div>`;
        debugPanel.style.display = 'block';
        debugPanel.open = true;
    } finally {
        estimateBtn.disabled = false;
        estimateBtn.textContent = '📊 Estimate Tokens';
    }
}

/**
 * Load and display saved study guides for the current course
 */
async function loadSavedStudyGuides() {
    const listDiv = document.getElementById('study-guides-list');
    if (!listDiv || !COURSE_ID) {
        if (listDiv) {
            listDiv.innerHTML = '<p class="no-guides-message">Select a course to view saved study guides.</p>';
        }
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/study-guides/courses/${COURSE_ID}`);
        if (!response.ok) throw new Error('Failed to load study guides');

        const data = await response.json();

        if (data.guides && data.guides.length > 0) {
            listDiv.innerHTML = data.guides.map(guide => `
                <div class="study-guide-card">
                    <div class="guide-content" onclick="loadStudyGuide('${guide.id}')">
                        <h4>${escapeHtml(guide.title)}</h4>
                        <div class="guide-meta">
                            <span>📅 ${formatDate(guide.created_at)}</span>
                            <span>📝 ${guide.word_count || 0} words</span>
                            ${guide.week_numbers ? `<span>📚 Weeks: ${guide.week_numbers.join(', ')}</span>` : ''}
                        </div>
                    </div>
                    <div class="guide-actions">
                        <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); deleteStudyGuide('${guide.id}', '${escapeHtml(guide.title).replace(/'/g, "\\'")}')">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = `
                <div class="no-guides-message">
                    <p>No saved study guides yet.</p>
                    <p>Click "Generate New" to create your first study guide!</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading study guides:', error);
        listDiv.innerHTML = '<p class="error">Failed to load study guides.</p>';
    }
}

/**
 * Load and display a specific study guide
 */
async function loadStudyGuide(guideId) {
    const resultDiv = document.getElementById('study-result');
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/study-guides/courses/${COURSE_ID}/${guideId}`);
        if (!response.ok) throw new Error('Failed to load study guide');

        const guide = await response.json();

        resultDiv.innerHTML = formatMarkdown(guide.content);
        resultDiv.style.display = 'block';

        // Render any Mermaid diagrams
        await renderMermaidDiagrams(resultDiv);

        // Scroll to result
        resultDiv.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error loading study guide:', error);
        resultDiv.innerHTML = `<p class="error">Failed to load study guide: ${escapeHtml(error.message)}</p>`;
        resultDiv.style.display = 'block';
    } finally {
        hideLoading();
    }
}

/**
 * Generate a new study guide using the persistence API
 */
async function generateStudyGuide() {
    const resultDiv = document.getElementById('study-result');
    const weekSelect = document.getElementById('study-week-select');

    showLoading();

    try {
        // Build request
        const requestBody = {
            course_id: COURSE_ID
        };

        // Add week filter if selected
        if (weekSelect && weekSelect.value) {
            requestBody.weeks = [parseInt(weekSelect.value, 10)];
        }

        // Use new persistence API
        const response = await fetch(`${API_BASE}/api/study-guides/courses/${COURSE_ID}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        const guide = data.guide;

        // Display the generated content
        resultDiv.innerHTML = formatMarkdown(guide.content);
        resultDiv.style.display = 'block';

        // Render any Mermaid diagrams
        await renderMermaidDiagrams(resultDiv);

        // Refresh saved guides list
        await loadSavedStudyGuides();

        // Show success message if it was a new guide
        if (!data.is_duplicate) {
            console.log('Study guide saved:', guide.title);
        }

    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p class="error">${escapeHtml(error.message || 'Error generating study guide. Please try again.')}</p>`;
        resultDiv.style.display = 'block';
    } finally {
        hideLoading();
    }
}

/**
 * Format a date string for display
 */
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch (e) {
        return dateStr;
    }
}

/**
 * Delete a study guide with confirmation
 */
async function deleteStudyGuide(guideId, guideTitle) {
    // Confirm before deleting
    const confirmed = confirm(`Are you sure you want to delete "${guideTitle}"?\n\nThis action cannot be undone.`);
    if (!confirmed) return;

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/study-guides/courses/${COURSE_ID}/${guideId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to delete study guide');
        }

        // Clear the result display if showing the deleted guide
        const resultDiv = document.getElementById('study-result');
        resultDiv.style.display = 'none';
        resultDiv.innerHTML = '';

        // Refresh the list
        await loadSavedStudyGuides();

        console.log('Study guide deleted:', guideTitle);

    } catch (error) {
        console.error('Error deleting study guide:', error);
        alert(`Failed to delete study guide: ${error.message}`);
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

    // Load course weeks dynamically
    loadCourseWeeks();
}

/**
 * Fetch course weeks from API and render them in the dashboard
 */
async function loadCourseWeeks() {
    const weeksGrid = document.getElementById('weeks-grid');
    if (!weeksGrid) return;

    // Need course context to fetch weeks
    if (!COURSE_ID) {
        weeksGrid.innerHTML = '<p class="no-weeks-message">No course selected</p>';
        return;
    }

    try {
        // Fetch course with weeks from admin API
        const response = await fetch(`/api/admin/courses/${COURSE_ID}?include_weeks=true`);

        if (!response.ok) {
            throw new Error(`Failed to fetch course: ${response.status} ${response.statusText}`);
        }

        const course = await response.json();
        const weeks = course.weeks || [];

        if (weeks.length === 0) {
            weeksGrid.innerHTML = '<p class="no-weeks-message">No weeks defined for this course yet.</p>';
            return;
        }

        // Sort weeks by week number (with defensive validation)
        weeks.sort((a, b) => {
            const aNum = typeof a.weekNumber === 'number' ? a.weekNumber : 0;
            const bNum = typeof b.weekNumber === 'number' ? b.weekNumber : 0;
            return aNum - bNum;
        });

        // Render week cards
        weeksGrid.innerHTML = weeks.map(week => renderWeekCard(week)).join('');

        // Setup event delegation for week card clicks (only once)
        setupWeekCardEventDelegation(weeksGrid);

        // Update topics stat to show total weeks
        // TODO: Progress tracking will show completed/total when implemented
        const statTopics = document.getElementById('stat-topics');
        if (statTopics) {
            statTopics.textContent = `${weeks.length} weeks`;
        }

    } catch (error) {
        console.error('Error loading course weeks:', error);
        weeksGrid.innerHTML = '<p class="error-message">Failed to load course weeks. Please try refreshing.</p>';
    }
}

/**
 * Render a single week card
 * @param {Object} week - Week object from API
 * @param {number} week.weekNumber - Week number (1-based)
 * @param {string} [week.title] - Week title
 * @param {string} [week.topicDescription] - Description of the week's content
 * @param {string[]} [week.topics] - Array of topic strings
 * @returns {string} HTML string for the week card
 */
function renderWeekCard(week) {
    const weekNumber = week.weekNumber;
    const safeWeekNumber = escapeHtml(String(weekNumber || 0));
    const title = week.title || `Week ${weekNumber}`;
    const description = week.topicDescription || '';
    const topics = week.topics || [];

    // Get icon based on week number or title (icons are safe literals)
    const icon = getWeekIcon(week);

    // Build topics list (show first 3 topics, ensure each is a string)
    const topicsList = topics.slice(0, 3).map(t => `<li>${escapeHtml(String(t || ''))}</li>`).join('');
    const moreTopics = topics.length > 3 ? `<li class="more-topics">+${topics.length - 3} more...</li>` : '';

    return `
        <div class="topic-card week-card" data-week="${safeWeekNumber}" data-title="${escapeHtml(title)}">
            <h4>${icon} Week ${safeWeekNumber}: ${escapeHtml(title)}</h4>
            <p>${escapeHtml(description) || (topics.length > 0 ? '' : 'No description available')}</p>
            ${topics.length > 0 ? `<ul class="week-topics-list">${topicsList}${moreTopics}</ul>` : ''}
            <div class="topic-progress" data-placeholder="true">
                <div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div>
                <span class="progress-text">0% Complete</span>
            </div>
        </div>
    `;
}

/**
 * Get an appropriate icon for the week based on title keywords
 */
function getWeekIcon(week) {
    const title = (week.title || '').toLowerCase();

    if (title.includes('criminal')) return '⚖️';
    if (title.includes('constitution')) return '🏛️';
    if (title.includes('administrative') || title.includes('gala')) return '🏢';
    if (title.includes('private') || title.includes('contract') || title.includes('civil')) return '📜';
    if (title.includes('international') || title.includes('european')) return '🌍';
    if (title.includes('introduction') || title.includes('intro')) return '📚';
    if (title.includes('property')) return '🏠';
    if (title.includes('tort') || title.includes('liability')) return '⚠️';
    if (title.includes('review') || title.includes('exam')) return '📝';

    // Default icon based on week number (with validation)
    const icons = ['📖', '📗', '📘', '📙', '📕', '📓'];
    const weekNum = typeof week.weekNumber === 'number' && week.weekNumber > 0 ? week.weekNumber : 1;
    return icons[(weekNum - 1) % icons.length];
}

/**
 * Setup event delegation for week card clicks (prevents memory leaks)
 * Uses a data attribute on the element to ensure the listener is only attached once,
 * which is more robust than a global flag when dealing with DOM element lifecycle.
 */
function setupWeekCardEventDelegation(weeksGrid) {
    if (!weeksGrid || weeksGrid.dataset.delegationSetup) return;
    weeksGrid.dataset.delegationSetup = 'true';

    weeksGrid.addEventListener('click', (e) => {
        const card = e.target.closest('.week-card');
        if (!card) return;

        const weekNumber = card.dataset.week;
        const title = card.dataset.title;

        // Navigate to AI Tutor with week context
        const tutorTab = document.querySelector('.nav-tab[data-tab="tutor"]');
        if (tutorTab) tutorTab.click();

        // Set context to the week topic
        const contextSelect = document.getElementById('context-select');
        if (contextSelect && title) {
            // Try to find matching option or use the title
            const options = Array.from(contextSelect.options);
            const match = options.find(opt =>
                opt.value.toLowerCase().includes(title.toLowerCase()) ||
                title.toLowerCase().includes(opt.value.toLowerCase())
            );
            if (match) {
                contextSelect.value = match.value;
            }
        }

        // Pre-fill chat with week context
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.placeholder = `Ask about Week ${weekNumber}: ${title}...`;
        }
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
