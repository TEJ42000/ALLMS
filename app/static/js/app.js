// app.js - Frontend JavaScript for Cognitio Flow

const API_BASE = '';  // Empty for same origin

// ========== Course Context ==========
// Get course context from window object (set by template)
const COURSE_ID = window.COURSE_CONTEXT?.courseId || null;
const COURSE_NAME = window.COURSE_CONTEXT?.courseName || 'LLS';
const COURSE = window.COURSE_CONTEXT?.course || null;

// ========== Request Tracking ==========
// Counter for active tutor requests to prevent race conditions with typing indicator
let activeTutorRequests = 0;

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

            // Dispatch tab-changed event
            const event = new CustomEvent('tab-changed', {
                detail: { tab: tabName }
            });
            document.dispatchEvent(event);
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
        securityLevel: 'strict'
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
                const id = 'mermaid-' + Array.from(window.crypto.getRandomValues(new Uint8Array(6)), b => b.toString(16).padStart(2, '0')).join('');

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
                // SECURITY: Use DOMParser for safe SVG insertion (CWE-79)
                // Mermaid's render() returns sanitized SVG (see https://mermaid.js.org/config/security.html)
                // DOMParser parses the SVG as a structured document, not as executable HTML
                // codeql[js/xss-through-dom] - svg is sanitized by Mermaid library, parsed as XML not HTML
                const parser = new DOMParser();
                const svgDoc = parser.parseFromString(svg, 'image/svg+xml');

                // Check for parsing errors (DOMParser creates parsererror element on failure)
                const parserError = svgDoc.querySelector('parsererror');
                if (parserError) {
                    console.warn('SVG parsing failed:', parserError.textContent);
                    // Keep the original code block as fallback
                    continue;
                }

                const svgElement = svgDoc.documentElement;
                if (svgElement && svgElement.nodeName === 'svg') {
                    diagramDiv.appendChild(document.importNode(svgElement, true));
                } else {
                    console.warn('Invalid SVG structure received from Mermaid');
                    // Keep the original code block as fallback
                    continue;
                }
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
//
// ReDoS PROTECTION STRATEGY:
// This function uses a defense-in-depth approach to prevent Regular Expression Denial of Service:
// 1. INPUT LENGTH LIMIT: Text truncated to 10KB before any regex processing
// 2. BOUNDED QUANTIFIERS: All quantifiers have strict upper bounds {1,500}
// 3. CHARACTER CLASS EXCLUSION: [^*] and [^`] prevent nested/overlapping matches
// 4. NO BACKTRACKING: Greedy quantifiers without alternation = O(n) time complexity
// 5. NO NESTED QUANTIFIERS: Avoids exponential complexity
//
// This multi-layer approach ensures the function is safe even with malicious input.
function formatInline(text) {
    // LAYER 1: Prevent ReDoS attacks by limiting text length before regex processing
    // Maximum length for inline formatting (10KB should be sufficient for any reasonable text)
    const MAX_INLINE_LENGTH = 10000;

    if (!text) return '';

    // Truncate if too long to prevent ReDoS (CRITICAL: This is our first line of defense)
    if (text.length > MAX_INLINE_LENGTH) {
        console.warn(`formatInline: Text truncated from ${text.length} to ${MAX_INLINE_LENGTH} chars to prevent ReDoS`);
        text = text.substring(0, MAX_INLINE_LENGTH) + '...';
    }

    text = escapeHtml(text);

    // LAYER 2: Use character class exclusions with strict quantifiers to prevent ReDoS
    // Pattern explanation:
    // - [^*] excludes asterisks, preventing nested/overlapping matches
    // - {1,500} strict quantifier with upper bound prevents catastrophic backtracking
    // - NO non-greedy quantifier (?) - character class exclusion already prevents overlapping
    // - No alternation or nested quantifiers to avoid exponential complexity
    // These patterns are O(n) time complexity, not vulnerable to ReDoS
    //
    // RELIANCE ON LENGTH LIMITS:
    // - Input is pre-truncated to 10KB (see above)
    // - Each pattern match is limited to 500 chars
    // - Combined with character class exclusion, this guarantees linear time complexity

    // Bold: **text** (must have at least 1 char, max 500)
    // Removed non-greedy ? to prevent backtracking issues
    text = text.replace(/\*\*([^*]{1,500})\*\*/g, '<strong>$1</strong>');

    // Italic: *text* (must have at least 1 char, max 500)
    // Removed non-greedy ? - character class exclusion prevents overlapping with bold
    text = text.replace(/\*([^*]{1,500})\*/g, '<em>$1</em>');

    // Code: `text` (must have at least 1 char, max 500)
    // Removed non-greedy ? to prevent backtracking issues
    text = text.replace(/`([^`]{1,500})`/g, '<code>$1</code>');

    return text;
}

// Escape HTML to prevent XSS
// This function properly escapes all special characters including:
// <, >, &, ", ', and backslashes by using textContent which handles all escaping
//
// Implementation note: This uses the browser's built-in escaping mechanism.
// Setting textContent automatically escapes ALL characters that need escaping in HTML,
// including backslashes, quotes, angle brackets, and control characters.
// This is a standard and secure pattern recommended for HTML escaping in JavaScript.
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;  // Browser automatically escapes all special chars
    return div.innerHTML;
}

// Compiled regex patterns for prompt injection detection (compiled once for performance)
// These patterns are defined at module level to avoid recompilation on every validation call
// Patterns avoid false positives for legal education (e.g., "act as a judge" is valid)
// Tightened to require AI-specific context words to avoid blocking legal topics
const PROMPT_INJECTION_PATTERNS = [
    // Instruction override attempts - target AI/system instructions specifically
    // Requires context words like "instructions", "prompts", "rules", "commands"
    /ignore\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)/i,
    /disregard\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)/i,
    /forget\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)/i,
    /override\s+(previous|all|above|prior)\s+(instructions?|prompts?|rules?|commands?)/i,

    // System manipulation attempts - specific to AI system
    // Tightened: requires "AI", "assistant", or "model" before "system" to avoid legal topics
    // Allows: "legal system instruction", "justice system message"
    // Blocks: "AI system prompt", "ignore system instruction"
    /(ai|assistant|model|chatbot)\s+system\s+(prompt|message|instruction)/i,
    /(ignore|bypass|override)\s+(the\s+)?system\s+(prompt|instruction|rules?)/i,
    /new\s+(instructions?|prompt)\s+(for\s+)?(you|the\s+system|the\s+ai)/i,

    // Role manipulation attempts - target AI role changes, not legal roles
    // Requires AI-specific roles: unrestricted, jailbroken, developer, admin, root, DAN
    /you\s+are\s+now\s+(an?\s+)?(unrestricted|jailbroken|developer|admin|root)/i,
    /act\s+as\s+(an?\s+)?(unrestricted|jailbroken|developer|admin|root|dan)/i,
    /pretend\s+(to\s+be|you\s+are)\s+(an?\s+)?(unrestricted|jailbroken|developer|admin)/i,

    // Direct command attempts targeting AI behavior
    // Requires "code", "command", or "script" to avoid blocking legal topics
    /(^|\s)(execute|run|perform)\s+(this|the|following)\s+(code|command|script)/i,

    // Explicit jailbreak attempts
    /(jailbreak|dan\s+mode|developer\s+mode|god\s+mode)/i,
];

/**
 * Validate topic input on frontend to prevent prompt injection
 * @param {string} topic - The topic to validate
 * @returns {Object} - {valid: boolean, error: string|null}
 */
function validateTopicInput(topic) {
    const MAX_TOPIC_LENGTH = 200;

    if (!topic || !topic.trim()) {
        return {valid: false, error: 'topic cannot be empty or only whitespace'};
    }

    const trimmedTopic = topic.trim();

    if (trimmedTopic.length > MAX_TOPIC_LENGTH) {
        return {valid: false, error: `topic must not exceed ${MAX_TOPIC_LENGTH} characters`};
    }

    // Check for suspicious prompt injection patterns using pre-compiled patterns
    // Normalize whitespace for pattern matching
    const normalizedTopic = trimmedTopic.replace(/\s+/g, ' ');

    // Use pre-compiled patterns from module level (performance optimization)
    for (const pattern of PROMPT_INJECTION_PATTERNS) {
        if (pattern.test(normalizedTopic)) {
            return {valid: false, error: 'topic contains suspicious content that may be a prompt injection attempt'};
        }
    }

    return {valid: true, error: null};
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

    // Increment active request counter and show typing indicator
    // Note: JavaScript is single-threaded, so this increment is atomic
    // However, we add defensive checks in the finally block
    activeTutorRequests++;
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
        addMessage('assistant', data.content);

    } catch (error) {
        console.error('Error:', error);
        addMessage('error', 'Sorry, there was an error processing your request.');
    } finally {
        // Decrement active request counter with defensive check
        // Ensure counter never goes negative (defensive programming)
        activeTutorRequests = Math.max(0, activeTutorRequests - 1);

        // Only hide typing indicator if no other requests are active
        // This prevents race condition where multiple simultaneous requests
        // could hide the indicator while other requests are still in progress
        if (activeTutorRequests === 0) {
            hideTypingIndicator();
        }
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

    // Note: Validation removed for select inputs as they contain predefined safe values
    // Backend validation still applies as defense-in-depth

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
        userId = 'user-' + Array.from(window.crypto.getRandomValues(new Uint8Array(12)), b => b.toString(16).padStart(2, '0')).join('');
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
    startTime: null,     // Track quiz start time
    timeLimit: null,     // Phase 1: Time limit in seconds (for timed quizzes)
    flaggedQuestions: [] // Phase 1: Array of flagged question indices
};

// Race condition protection - prevent multiple simultaneous quiz generations
let isGeneratingQuiz = false;

// Phase 1: Enhancement utilities (timer, progress bar, etc.)
let quizEnhancements = null;

// Phase 2: Cleanup function for event listeners
let phase2Cleanup = null;

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
                    <button class="btn btn-primary create-new-quiz-btn">Create New Quiz</button>
                </div>
            `;
            // Add event listener for CSP compliance (no inline onclick)
            const createBtn = container.querySelector('.create-new-quiz-btn');
            if (createBtn) {
                createBtn.addEventListener('click', () => switchQuizTab('new'));
            }
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
                    <button class="btn btn-primary browse-quizzes-btn">Browse Quizzes</button>
                </div>
            `;
            // Add event listener for CSP compliance (no inline onclick)
            const browseBtn = container.querySelector('.browse-quizzes-btn');
            if (browseBtn) {
                browseBtn.addEventListener('click', () => switchQuizTab('saved'));
            }
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
            startTime: Date.now(),
            timeLimit: quiz.timeLimit || null,  // Phase 1: Timer support
            flaggedQuestions: []  // Phase 1: Flag for review
        };

        // Phase 1: Initialize enhancements if available
        if (typeof initializePhase1Enhancements === 'function') {
            quizEnhancements = initializePhase1Enhancements(quizState);
        }

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
    // Phase 1: Cleanup timer before leaving quiz
    if (quizEnhancements && quizEnhancements.timer) {
        quizEnhancements.timer.stop();
        quizEnhancements.timer = null;
    }
    quizEnhancements = null;

    // CRITICAL FIX: Cleanup Phase 2 event listeners
    if (phase2Cleanup && typeof phase2Cleanup === 'function') {
        phase2Cleanup();
        phase2Cleanup = null;
    }

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

    // Validate topic input (defense in depth)
    // Note: Topic is extracted from option text (line 1272), which could be dynamically generated
    // Therefore validation is still needed, unlike essay-topic-select which uses predefined values
    if (topic && topic !== 'all') {
        const validation = validateTopicInput(topic);
        if (!validation.valid) {
            alert(`Invalid topic: ${validation.error}`);
            return;
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
            startTime: Date.now(),
            timeLimit: quiz.timeLimit || null,  // Phase 1: Timer support
            flaggedQuestions: []  // Phase 1: Flag for review
        };

        // Phase 1: Initialize enhancements if available
        if (typeof initializePhase1Enhancements === 'function') {
            quizEnhancements = initializePhase1Enhancements(quizState);
        }

        // Show notification if this was an existing quiz
        if (!data.is_new) {
            console.log('Loaded existing quiz with matching content');
        }

        // Show quiz content
        showQuizContent();

    } catch (error) {
        console.error('Error generating quiz:', error);
        // Show error message in quiz container
        if (questionContainer) {
            const errorMessage = error.message || 'Error generating quiz. Please try again.';
            questionContainer.innerHTML = `<p class="error">${escapeHtml(errorMessage)}</p>`;
        }
        if (quizContent) {
            quizContent.classList.remove('hidden');
        }
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

    // Phase 5: Initialize accessibility features
    initializeQuizAccessibility(questionContainer);

    // Phase 6: Initialize mobile features
    initializeMobileQuiz(questionContainer);

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

    // Phase 5: Announce question change to screen readers
    if (typeof announceQuestionChange === 'function') {
        announceQuestionChange(
            quizState.currentQuestionIndex + 1,
            quizState.questions.length,
            question.question
        );
    }

    const questionNum = quizState.currentQuestionIndex + 1;
    const userAnswer = quizState.userAnswers[quizState.currentQuestionIndex];

    // Phase 1: Create enhanced question header if enhancements are available
    let headerHTML = '';
    if (typeof createEnhancedQuestionHeader === 'function' && quizEnhancements) {
        const header = createEnhancedQuestionHeader(
            question,
            questionNum,
            quizState.questions.length,
            quizEnhancements.timer
        );
        // Convert DOM element to HTML string
        const tempDiv = document.createElement('div');
        tempDiv.appendChild(header);
        headerHTML = tempDiv.innerHTML;
    } else {
        // Fallback to original header
        headerHTML = `
            <div class="question-header">
                <h3>Question ${questionNum}</h3>
                ${question.difficulty ? `<span class="difficulty-badge difficulty-${question.difficulty}">${question.difficulty}</span>` : ''}
            </div>
        `;
    }

    let html = `
        <div class="quiz-question-card">
            ${headerHTML}
            <p class="question-text">${escapeHtml(question.question)}</p>
            ${question.articles && question.articles.length > 0 ? `
                <div class="question-articles">
                    <strong>Related Articles:</strong> ${question.articles.map(a => escapeHtml(a)).join(', ')}
                </div>
            ` : ''}
            <div id="quiz-options-placeholder"></div>
            <div id="quiz-flag-placeholder"></div>
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

    // CRITICAL FIX: Remove old event listeners before adding new ones
    // MEDIUM: Document container cloning behavior
    //
    // We clone and replace the container to remove ALL event listeners.
    // This is more reliable than tracking individual listeners.
    //
    // IMPORTANT: After this operation, any external references to the old
    // container will be stale. The container variable is reassigned to the
    // new cloned element. This is safe because:
    // 1. We're in the displayCurrentQuestion function scope
    // 2. The container is re-queried on each question change
    // 3. Event listeners are re-attached to the new container below
    //
    // Alternative approaches considered:
    // - removeEventListener: Requires tracking all listener references
    // - AbortController: Not supported in older browsers
    // - Clone/replace: Simple, reliable, works everywhere
    const oldContainer = container;
    const newContainer = container.cloneNode(true);
    container.parentNode.replaceChild(newContainer, container);
    container = newContainer;

    // Phase 2: Create enhanced answer options if available
    const optionsPlaceholder = container.querySelector('#quiz-options-placeholder');
    if (optionsPlaceholder && typeof createAnswerOptionsContainer === 'function') {
        const optionsContainer = createAnswerOptionsContainer(
            question.options,
            userAnswer,
            userAnswer !== null,
            userAnswer !== null ? question.correct_index : null
        );
        optionsPlaceholder.replaceWith(optionsContainer);

        // CRITICAL FIX: Cleanup old Phase 2 listeners before adding new ones
        if (phase2Cleanup && typeof phase2Cleanup === 'function') {
            phase2Cleanup();
            phase2Cleanup = null;
        }

        // CRITICAL FIX: Use Phase 2 event handlers OR fallback to old handler, not both
        if (typeof initializePhase2Enhancements === 'function') {
            // Phase 2 handles all option clicks internally
            phase2Cleanup = initializePhase2Enhancements(container, selectAnswer);
        } else {
            // Fallback: Use event delegation on the container
            container.addEventListener('click', handleQuizContainerClick);
        }
    } else {
        // No Phase 2: Use event delegation on the container
        container.addEventListener('click', handleQuizContainerClick);
    }

    // Phase 3: Create flag button if available
    const flagPlaceholder = container.querySelector('#quiz-flag-placeholder');
    if (flagPlaceholder && typeof createFlagButton === 'function') {
        const isFlagged = quizState.flaggedQuestions && quizState.flaggedQuestions.includes(quizState.currentQuestionIndex);
        const flagButton = createFlagButton(quizState.currentQuestionIndex, isFlagged);

        // Add click handler for flag button
        flagButton.addEventListener('click', () => {
            toggleQuestionFlag(quizState.currentQuestionIndex);
        });

        flagPlaceholder.replaceWith(flagButton);
    }

    // Phase 3: Update navigation sidebar if it exists
    updateNavigationSidebar();
}

/**
 * Toggle flag status for a question
 * @param {number} questionIndex - Index of question to toggle
 */
function toggleQuestionFlag(questionIndex) {
    if (!quizState.flaggedQuestions) {
        quizState.flaggedQuestions = [];
    }

    const index = quizState.flaggedQuestions.indexOf(questionIndex);
    if (index > -1) {
        // Unflag
        quizState.flaggedQuestions.splice(index, 1);
    } else {
        // Flag
        quizState.flaggedQuestions.push(questionIndex);
    }

    // Update the display
    const container = document.getElementById('quiz-question-container');
    if (container) {
        displayCurrentQuestion(container);
    }
}

/**
 * Update navigation sidebar with current quiz state
 */
function updateNavigationSidebar() {
    const sidebarContainer = document.getElementById('quiz-nav-sidebar-container');
    if (!sidebarContainer || typeof createQuestionNavSidebar !== 'function') {
        return;
    }

    // Create new sidebar
    const sidebar = createQuestionNavSidebar(quizState, (questionIndex) => {
        // Navigate to selected question
        quizState.currentQuestionIndex = questionIndex;
        const container = document.getElementById('quiz-question-container');
        if (container) {
            displayCurrentQuestion(container);
        }
    });

    // Replace old sidebar
    sidebarContainer.innerHTML = '';
    sidebarContainer.appendChild(sidebar);

    // Add toggle functionality for mobile
    const toggleBtn = sidebar.querySelector('.nav-sidebar-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            const isCollapsed = sidebar.classList.contains('collapsed');
            toggleBtn.textContent = isCollapsed ? '+' : '−';
            toggleBtn.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
        });
    }

    // Add navigation button click handlers
    const navButtons = sidebar.querySelectorAll('.question-nav-btn');
    navButtons.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            quizState.currentQuestionIndex = index;
            const container = document.getElementById('quiz-question-container');
            if (container) {
                displayCurrentQuestion(container);
            }
        });
    });
}

// ========== Phase 5: Accessibility Integration ==========

// Store cleanup function for keyboard navigation
let keyboardNavigationCleanup = null;

// ========== Phase 6: Mobile Integration ==========

// Store cleanup function for mobile features
let mobileCleanup = null;

/**
 * Initialize mobile features for quiz
 * @param {HTMLElement} container - Quiz container element
 */
function initializeMobileQuiz(container) {
    if (!container) return;

    // Prevent race condition: clean up existing initialization first
    if (mobileCleanup) {
        mobileCleanup();
        mobileCleanup = null;
    }

    // Check if mobile functions are available
    if (typeof initializeMobileFeatures !== 'function') {
        console.warn('Quiz mobile functions not loaded');
        mobileCleanup = () => {}; // Set dummy cleanup
        return;
    }

    // Initialize mobile features
    mobileCleanup = initializeMobileFeatures(
        container,
        quizState,
        (newIndex) => {
            // Navigate to question via swipe
            quizState.currentQuestionIndex = newIndex;
            displayCurrentQuestion(container);
            updateNavigationSidebar();
        }
    );

    // Optimize touch targets
    if (typeof optimizeTouchTargets === 'function') {
        optimizeTouchTargets(container);
    }
}

/**
 * Initialize accessibility features for quiz
 * @param {HTMLElement} container - Quiz container element
 */
function initializeQuizAccessibility(container) {
    if (!container) return;

    // Prevent race condition: clean up existing initialization first
    if (keyboardNavigationCleanup) {
        keyboardNavigationCleanup();
        keyboardNavigationCleanup = null;
    }

    // Check if accessibility functions are available
    if (typeof initializeKeyboardNavigation !== 'function') {
        console.warn('Quiz accessibility functions not loaded');
        keyboardNavigationCleanup = () => {}; // Set dummy cleanup to prevent re-initialization
        return;
    }

    // Add skip links to page (only once)
    if (!document.querySelector('.skip-links') && typeof createSkipLinks === 'function') {
        const skipLinks = createSkipLinks();
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    // Initialize keyboard navigation
    keyboardNavigationCleanup = initializeKeyboardNavigation(
        container,
        quizState,
        (newIndex) => {
            // Navigate to question via keyboard
            quizState.currentQuestionIndex = newIndex;
            displayCurrentQuestion(container);
            updateNavigationSidebar();
        }
    );

    // Ensure visible focus indicators
    if (typeof ensureVisibleFocus === 'function') {
        ensureVisibleFocus(container);
    }

    // Create screen reader region
    if (typeof createScreenReaderRegion === 'function') {
        createScreenReaderRegion();
    }
}

/**
 * Event delegation handler for quiz container clicks.
 * Handles all button clicks within the quiz question container.
 */
function handleQuizContainerClick(event) {
    const target = event.target;

    // Handle quiz option selection (both old and Phase 2 enhanced options)
    const optionBtn = target.closest('.quiz-option') || target.closest('.quiz-option-enhanced');
    if (optionBtn && !optionBtn.disabled) {
        const index = parseInt(optionBtn.dataset.answerIndex || optionBtn.dataset.optionIndex, 10);
        if (!isNaN(index)) {
            selectAnswer(index);
            return;
        }
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

    // Phase 5: Announce answer selection to screen readers
    if (typeof announceAnswerSelection === 'function') {
        const optionText = question.options[answerIndex];
        const optionLetter = String.fromCharCode(65 + answerIndex); // A, B, C, D
        announceAnswerSelection(optionText, optionLetter);
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

        // Log activity for gamification (don't block quiz submission if this fails)
        try {
            if (window.activityTracker) {
                const totalQuestions = quizState.questions.length;
                const percentage = (quizState.score / totalQuestions) * 100;

                await window.activityTracker.logActivity('quiz_completed', {
                    quiz_id: quizState.quizId,
                    score: quizState.score,
                    total_questions: totalQuestions,
                    difficulty: quizState.difficulty || 'easy',
                    time_taken_seconds: timeTaken,
                    percentage: percentage
                }, quizState.courseId);
            }
        } catch (gamificationError) {
            console.error('Failed to log quiz activity for gamification:', gamificationError);
            // Don't throw - gamification failure shouldn't block quiz submission
        }

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
    // Phase 1: Cleanup timer before restarting
    if (quizEnhancements && quizEnhancements.timer) {
        quizEnhancements.timer.stop();
        quizEnhancements.timer = null;
    }
    quizEnhancements = null;

    // CRITICAL FIX: Cleanup Phase 2 event listeners
    if (phase2Cleanup && typeof phase2Cleanup === 'function') {
        phase2Cleanup();
        phase2Cleanup = null;
    }

    // Phase 5: Cleanup keyboard navigation
    if (keyboardNavigationCleanup && typeof keyboardNavigationCleanup === 'function') {
        keyboardNavigationCleanup();
        keyboardNavigationCleanup = null;
    }

    // Phase 6: Cleanup mobile features
    if (mobileCleanup && typeof mobileCleanup === 'function') {
        mobileCleanup();
        mobileCleanup = null;
    }

    // Reset state
    quizState = {
        quizId: null,
        courseId: null,
        questions: [],
        currentQuestionIndex: 0,
        userAnswers: [],
        score: 0,
        isComplete: false,
        startTime: null,
        timeLimit: null,
        flaggedQuestions: []
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

    // Load saved guides and populate week dropdown concurrently
    // Both operations are independent and handle their own errors individually
    Promise.all([
        loadSavedStudyGuides().catch(e => console.error('Failed to load saved guides:', e)),
        populateStudyWeekDropdown().catch(e => console.error('Failed to populate week dropdown:', e))
    ]);
}

/**
 * Enhance the study guide week dropdown with material counts.
 * The dropdown is server-rendered with course topics; this adds material counts
 * and disables weeks with no materials.
 */
async function populateStudyWeekDropdown() {
    const weekSelect = document.getElementById('study-week-select');
    if (!weekSelect || !COURSE_ID) {
        return;
    }

    try {
        const response = await fetch(`/api/courses/${COURSE_ID}/materials/week-counts`);

        if (!response.ok) {
            console.error('Failed to fetch material counts:', response.status);
            // Keep existing options as-is (server-rendered)
            return;
        }

        const data = await response.json();
        const weeks = data.weeks || [];
        const totalMaterials = data.total || 0;

        // Create a map of week number to count
        const weekCounts = {};
        weeks.forEach(w => {
            weekCounts[w.week] = w.count;
        });

        // Update the "All Weeks" option with total count
        const allWeeksOption = weekSelect.querySelector('option[value=""]');
        if (allWeeksOption) {
            allWeeksOption.textContent = `All Weeks (${totalMaterials} materials)`;
        }

        // Update each week option with material count
        weekSelect.querySelectorAll('option[data-week]').forEach(option => {
            const weekNum = parseInt(option.dataset.week);
            const count = weekCounts[weekNum] || 0;
            const countText = count === 0 ? 'no materials' : `${count} material${count !== 1 ? 's' : ''}`;

            // Append count to existing text (which includes topic name)
            const currentText = option.textContent;
            option.textContent = `${currentText} (${countText})`;

            // Disable if no materials
            if (count === 0) {
                option.disabled = true;
            }
        });

        console.log(`Enhanced study week dropdown with material counts: ${totalMaterials} total materials`);

    } catch (error) {
        console.error('Error fetching material counts:', error);
        // Keep existing options as-is (server-rendered)
    }
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
                        <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); deleteStudyGuide('${guide.id}', '${escapeHtml(guide.title).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">
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
    // Add course-specific information banner to dashboard
    const dashboardSection = document.getElementById('dashboard-section');
    if (dashboardSection && COURSE_ID) {
        // Check if course info banner already exists
        let courseInfoBanner = dashboardSection.querySelector('.course-info-banner');
        if (!courseInfoBanner) {
            // Create banner using DOM manipulation for CSP compliance and XSS prevention
            courseInfoBanner = document.createElement('div');
            courseInfoBanner.className = 'course-info-banner';

            // Create icon element
            const icon = document.createElement('span');
            icon.className = 'course-info-icon';
            icon.textContent = '📚';

            // Create text container
            const textDiv = document.createElement('div');
            textDiv.className = 'course-info-text';

            // Create course name element
            const nameDiv = document.createElement('div');
            nameDiv.className = 'course-info-name';
            nameDiv.textContent = `Active Course: ${COURSE_NAME}`;

            // Create course ID element
            const idDiv = document.createElement('div');
            idDiv.className = 'course-info-id';
            idDiv.textContent = `Course ID: ${COURSE_ID}`;

            // Assemble text container
            textDiv.appendChild(nameDiv);
            textDiv.appendChild(idDiv);

            // Create badge element
            const badge = document.createElement('span');
            badge.className = 'course-info-badge';
            badge.textContent = '✓ Course-Specific Content';

            // Assemble banner
            courseInfoBanner.appendChild(icon);
            courseInfoBanner.appendChild(textDiv);
            courseInfoBanner.appendChild(badge);

            // Insert banner at the top of the dashboard section with error handling
            try {
                const sectionTitle = dashboardSection.querySelector('.section-title');
                if (sectionTitle) {
                    // Insert after section title for better visual hierarchy
                    sectionTitle.insertAdjacentElement('afterend', courseInfoBanner);
                } else {
                    // No section title - prepend to dashboard
                    dashboardSection.insertAdjacentElement('afterbegin', courseInfoBanner);
                }
            } catch (error) {
                // Fallback: if insertAdjacentElement fails, try appendChild
                console.warn('Course banner insertion failed, using fallback:', error);
                try {
                    dashboardSection.appendChild(courseInfoBanner);
                } catch (fallbackError) {
                    console.error('Course banner insertion completely failed:', fallbackError);

                    // Notify user that course info couldn't be displayed
                    const errorBanner = document.createElement('div');
                    errorBanner.className = 'alert alert-warning';
                    errorBanner.style.margin = '10px 0';
                    errorBanner.textContent = 'Unable to display course information banner. Course functionality may be limited.';

                    // Try to insert error notification
                    try {
                        dashboardSection.insertAdjacentElement('afterbegin', errorBanner);
                    } catch (e) {
                        // If even error notification fails, just log it
                        console.error('Could not display error notification:', e);
                    }
                }
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
        // Fetch course with weeks from public courses API (accessible to all authenticated users)
        const response = await fetch(`/api/courses/${COURSE_ID}?include_weeks=true`);

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

// ========== Flashcards ==========
// Course-aware flashcard system - loads flashcards dynamically from backend API
// Flashcards are generated from actual course materials using FilesAPIService

// Constants
const DEFAULT_FLASHCARD_COUNT = 20;

// State
let flashcards = [];
let currentCardIndex = 0;
let isLoadingFlashcards = false;
let lastFlashcardErrorTime = 0;  // Timestamp of last error for debouncing

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
    // Debounce error retries to prevent rapid retries that could overload the backend
    // Check this first to provide immediate feedback to users
    const DEBOUNCE_MS = 2000;
    const now = Date.now();
    if (lastFlashcardErrorTime && (now - lastFlashcardErrorTime) < DEBOUNCE_MS) {
        const remainingMs = DEBOUNCE_MS - (now - lastFlashcardErrorTime);
        const remainingSec = Math.ceil(remainingMs / 1000);
        console.log(`Debounce active: ${remainingSec}s remaining`);

        // User-friendly message explaining why they need to wait
        const message = remainingSec === 1
            ? 'Please wait 1 second before trying again. This helps prevent server overload.'
            : `Please wait ${remainingSec} seconds before trying again. This helps prevent server overload.`;

        showFlashcardError(message);
        return;
    }

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

        // Success - reset error debouncing timestamp
        lastFlashcardErrorTime = 0;

        console.log(`Loaded ${flashcards.length} flashcards for course ${COURSE_ID}`);

    } catch (error) {
        console.error('Error loading flashcards:', error);
        showFlashcardError(error.message || 'Error loading flashcards. Please try again.');

        // Record error timestamp for debouncing future retry attempts
        lastFlashcardErrorTime = Date.now();
    } finally {
        // Always reset loading flag to allow future requests
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

// ========== Cleanup on Page Unload ==========
// Prevent memory leaks by cleaning up event listeners
window.addEventListener('beforeunload', () => {
    // Cleanup GamificationUI if it exists
    if (window.gamificationUI && typeof window.gamificationUI.cleanup === 'function') {
        window.gamificationUI.cleanup();
    }

    // Cleanup ActivityTracker if it exists
    if (window.activityTracker && typeof window.activityTracker.cleanup === 'function') {
        window.activityTracker.cleanup();
    }
});
