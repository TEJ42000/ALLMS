// app.js - Frontend JavaScript for LLS Study Portal

const API_BASE = '';  // Empty for same origin

// ========== Tab Navigation ==========
document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
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
        });
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
    // Basic markdown formatting
    text = text.replace(/## (.*?)$/gm, '<h2>$1</h2>');
    text = text.replace(/### (.*?)$/gm, '<h3>$1</h3>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Lists
    text = text.replace(/^- (.*?)$/gm, '<li>$1</li>');
    text = text.replace(/^(\d+)\. (.*?)$/gm, '<li>$2</li>');
    
    // Emojis and special formatting
    text = text.replace(/✅/g, '<span class="emoji-check">✅</span>');
    text = text.replace(/❌/g, '<span class="emoji-cross">❌</span>');
    text = text.replace(/⚠️/g, '<span class="emoji-warning">⚠️</span>');
    text = text.replace(/💡/g, '<span class="emoji-tip">💡</span>');
    
    return text;
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

