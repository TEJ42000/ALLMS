// app.js - Frontend JavaScript for LLS Study Portal

const API_BASE = '';  // Empty for same origin

// ========== Tab Navigation ==========
document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const navTabs = document.getElementById('nav-tabs');

    // Mobile menu toggle
    if (mobileMenuBtn && navTabs) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenuBtn.classList.toggle('active');
            navTabs.classList.toggle('active');
        });
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show corresponding content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabName}-tab`) {
                    content.classList.add('active');
                }
            });

            // Close mobile menu after selecting a tab
            if (mobileMenuBtn && navTabs) {
                mobileMenuBtn.classList.remove('active');
                navTabs.classList.remove('active');
            }
        });
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
        if (mobileMenuBtn && navTabs &&
            !mobileMenuBtn.contains(e.target) &&
            !navTabs.contains(e.target)) {
            mobileMenuBtn.classList.remove('active');
            navTabs.classList.remove('active');
        }
    });

    // Initialize event listeners
    initTutorListeners();
    initAssessmentListeners();
    initQuizListeners();
    initStudyListeners();
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
    document.getElementById('generate-quiz-btn').addEventListener('click', generateQuiz);
}

async function generateQuiz() {
    const topic = document.getElementById('quiz-topic').value;
    const num_questions = parseInt(document.getElementById('quiz-count').value);
    const resultDiv = document.getElementById('quiz-result');
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/files-content/quiz`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({topic, num_questions, difficulty: 'medium'})
        });
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        const data = await response.json();
        displayQuiz(data.quiz);
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<p class="error">Error generating quiz. Please try again.</p>';
    } finally {
        hideLoading();
    }
}

function displayQuiz(quiz) {
    // Quiz display implementation
    const resultDiv = document.getElementById('quiz-result');
    resultDiv.innerHTML = '<p>Quiz generated! (Display implementation pending)</p>';
    resultDiv.style.display = 'block';
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

