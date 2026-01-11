/**
 * Week Content Display System
 * Fetches week data from API and renders interactive week cards
 *
 * Cache Lifecycle:
 * - Populated: On initial page load via loadWeeks() and after successful API fetch
 * - Storage: In-memory (this.currentWeek, this.currentWeekTitle) - session-based
 * - Invalidated: When user switches courses or manually refreshes the page
 * - TTL: Session-based (cleared on page reload, no persistent storage)
 * - Refresh triggers: Course change, page reload, manual refresh
 */

class WeekContentManager {
    constructor() {
        this.weeksGrid = document.getElementById('weeks-grid');
        this.modal = document.getElementById('week-content-modal');
        this.currentWeek = null;
        this.currentWeekTitle = '';
        this.courseId = window.COURSE_CONTEXT?.courseId || window.COURSE_ID || 'LLS-2025-2026';
        // Cache weeks data to avoid additional API calls when viewing week details
        // Note: Cache persists for page session. Refresh page to reload updated course data.
        this.weeksData = {};
        this.allWeeks = [];
        this.currentPart = 'A'; // Default to Part A
        this.partSelector = document.getElementById('part-selector');

        this.init();
    }
    
    async init() {
        console.log('[WeekContentManager] Initializing...');
        console.log('[WeekContentManager] Course ID:', this.courseId);
        console.log('[WeekContentManager] Weeks grid element:', this.weeksGrid);

        if (!this.weeksGrid) {
            console.error('[WeekContentManager] weeks-grid element not found!');
            console.log('[WeekContentManager] Available elements:', {
                'weeks-section': document.getElementById('weeks-section'),
                'weeks-grid': document.getElementById('weeks-grid')
            });
            return;
        }

        console.log('[WeekContentManager] Loading weeks...');
        await this.loadWeeks();
    }
    
    async loadWeeks() {
        try {
            // Fetch weeks from public courses API (accessible to all authenticated users)
            const response = await fetch(`/api/courses/${this.courseId}?include_weeks=true`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[WeekContentManager] API error:', errorText);
                throw new Error(`Failed to load weeks: ${response.status}`);
            }

            const course = await response.json();
            const weeks = course.weeks || [];

            // Store all weeks
            this.allWeeks = weeks;

            // Cache weeks data for later use (avoids additional API calls)
            this.cacheWeeksData(weeks);

            // Check if course has parts (e.g., Criminal Law with Part A and Part B)
            const hasParts = weeks.some(w => w.part);
            if (hasParts) {
                this.initPartSelector();
            }

            this.renderWeeks(weeks);
        } catch (error) {
            console.error('[WeekContentManager] Error loading weeks:', error);
            // Fallback: render placeholder weeks
            this.renderFallbackWeeks();
        }
    }

    /**
     * Initialize part selector for courses with parts (e.g., Criminal Law)
     */
    initPartSelector() {
        if (!this.partSelector) {
            console.warn('[WeekContentManager] Part selector element not found');
            return;
        }

        // Show the part selector
        this.partSelector.style.display = 'block';

        // Add click handlers to part tabs
        const partTabs = this.partSelector.querySelectorAll('.part-tab');

        if (partTabs.length === 0) {
            console.error('[WeekContentManager] No part tabs found in part selector');
            return;
        }

        partTabs.forEach(tab => {
            // Validate tab has data-part attribute
            if (!tab.dataset.part) {
                console.error('[WeekContentManager] Part tab missing data-part attribute:', tab);
                return;
            }

            tab.addEventListener('click', (e) => {
                e.preventDefault();

                const selectedPart = tab.dataset.part;

                // Validate part value
                const validParts = ['A', 'B', 'mixed'];
                if (!validParts.includes(selectedPart)) {
                    console.error('[WeekContentManager] Invalid part selected:', selectedPart);
                    return;
                }

                console.log('[WeekContentManager] Part selected:', selectedPart);

                // Update active state and ARIA attributes
                partTabs.forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');

                // Update current part
                this.currentPart = selectedPart;

                // Filter and render weeks
                this.filterWeeksByPart();
            });
        });

        console.log('[WeekContentManager] Part selector initialized with', partTabs.length, 'tabs');
    }

    /**
     * Filter weeks by selected part
     */
    filterWeeksByPart() {
        // Validate allWeeks is an array
        if (!Array.isArray(this.allWeeks)) {
            console.error('[WeekContentManager] allWeeks is not an array:', this.allWeeks);
            this.renderFallbackWeeks();
            this.announceFilterChange('Error loading weeks');
            return;
        }

        let filteredWeeks;
        let partName;

        if (this.currentPart === 'mixed') {
            // Show all weeks
            filteredWeeks = this.allWeeks;
            partName = 'all parts';
            console.log('[WeekContentManager] Showing all weeks (mixed mode):', filteredWeeks.length);
        } else {
            // Filter by part
            filteredWeeks = this.allWeeks.filter(w => w.part === this.currentPart);
            partName = `Part ${this.currentPart}`;
            console.log(`[WeekContentManager] Filtered to Part ${this.currentPart}:`, filteredWeeks.length, 'weeks');
        }

        // Validate we have weeks to show
        if (filteredWeeks.length === 0) {
            console.warn(`[WeekContentManager] No weeks found for part ${this.currentPart}`);
            this.announceFilterChange(`No weeks found for ${partName}`);
        } else {
            // Announce filter change to screen readers
            this.announceFilterChange(`Showing ${filteredWeeks.length} weeks from ${partName}`);
        }

        this.renderWeeks(filteredWeeks);
    }

    /**
     * Announce filter changes to screen readers via ARIA live region
     * @param {string} message - Message to announce
     */
    announceFilterChange(message) {
        const statusElement = document.getElementById('part-filter-status');
        if (statusElement) {
            statusElement.textContent = message;
            console.log('[WeekContentManager] ARIA announcement:', message);
        }
    }

    /**
     * Cache weeks data by week number for quick lookup
     * This allows showing week details without additional API calls
     */
    cacheWeeksData(weeks) {
        this.weeksData = {};
        weeks.forEach(week => {
            // Validate weekNumber is a positive integer before caching
            if (week.weekNumber && Number.isInteger(week.weekNumber) && week.weekNumber > 0) {
                this.weeksData[week.weekNumber] = week;
            }
        });
    }

    /**
     * Get cached week data by week number
     * @param {number} weekNumber - The week number to look up
     * @returns {Object|null} The cached week data or null if not found
     */
    getCachedWeekData(weekNumber) {
        return this.weeksData[weekNumber] || null;
    }

    renderWeeks(weeks) {
        console.log('[WeekContentManager] renderWeeks called with:', weeks);

        if (!weeks || weeks.length === 0) {
            console.warn('[WeekContentManager] No weeks to render, showing fallback');
            this.renderFallbackWeeks();
            return;
        }

        console.log('[WeekContentManager] Clearing grid and rendering', weeks.length, 'weeks');
        this.weeksGrid.innerHTML = '';

        // Sort by week number
        weeks.sort((a, b) => (a.weekNumber || 0) - (b.weekNumber || 0));

        // Safe logging with Array.isArray check
        if (Array.isArray(weeks)) {
            console.log('[WeekContentManager] Sorted weeks:', weeks.map(w => `Week ${w.weekNumber}`));
        }

        weeks.forEach((week, index) => {
            console.log(`[WeekContentManager] Creating card ${index + 1}/${weeks.length}:`, week);
            const card = this.createWeekCard(week);
            this.weeksGrid.appendChild(card);
        });

        console.log('[WeekContentManager] ✅ All week cards rendered successfully');
    }
    
    renderFallbackWeeks() {
        // Fallback data if API doesn't return weeks
        const fallbackWeeks = [
            { weekNumber: 1, title: 'Introduction & Legal Foundations', topics: ['Course Overview', 'Legal Systems', 'Sources of Law'] },
            { weekNumber: 2, title: 'Core Concepts', topics: ['Key Principles', 'Fundamental Rights', 'Legal Methods'] },
            { weekNumber: 3, title: 'Advanced Topics', topics: ['Case Analysis', 'Legal Reasoning', 'Application'] },
        ];
        
        this.weeksGrid.innerHTML = '';
        fallbackWeeks.forEach(week => {
            const card = this.createWeekCard(week);
            this.weeksGrid.appendChild(card);
        });
    }
    
    createWeekCard(week) {
        const card = document.createElement('div');
        card.className = 'week-card';
        card.dataset.weekNumber = week.weekNumber;

        const progress = week.progress || 0;
        const topics = week.topics || week.keyTopics || [];
        const description = week.description || week.summary || this.generateDescription(week);

        // Make entire card clickable
        card.style.cursor = 'pointer';
        card.onclick = () => this.openWeekStudyNotes(week.weekNumber, week.title || `Week ${week.weekNumber}`);

        card.innerHTML = `
            <span class="week-label">Week ${week.weekNumber}${week.part ? ` - Part ${week.part}` : ''}</span>
            <h3>${this.escapeHtml(week.title || `Week ${week.weekNumber}`)}</h3>
            <p class="week-description">${this.escapeHtml(description)}</p>

            ${topics.length > 0 && Array.isArray(topics) ? `
                <div class="week-topics">
                    ${topics.slice(0, 4).map(t => `<span class="topic-tag">${this.escapeHtml(typeof t === 'string' ? t : t.name || t)}</span>`).join('')}
                    ${topics.length > 4 ? `<span class="topic-tag">+${topics.length - 4} more</span>` : ''}
                </div>
            ` : ''}

            <div class="week-progress-bar">
                <div class="week-progress-fill" style="width: ${progress}%"></div>
            </div>

            <div class="week-card-footer">
                <span class="week-card-hint">📖 Click to view study notes</span>
            </div>
        `;

        return card;
    }
    
    generateDescription(week) {
        const topics = week.topics || [];
        if (topics.length > 0) {
            return `Study materials and resources covering ${topics.slice(0, 2).join(', ')}${topics.length > 2 ? ' and more' : ''}.`;
        }
        return 'Study materials and resources for this week.';
    }
    
    async openWeekStudyNotes(weekNumber, weekTitle) {
        // Validate weekNumber to prevent cache corruption and API errors
        if (!Number.isInteger(weekNumber) || weekNumber < 1 || weekNumber > 52) {
            console.error('[WeekContentManager] Invalid weekNumber:', weekNumber);
            throw new TypeError(`weekNumber must be an integer between 1 and 52, got: ${weekNumber}`);
        }

        this.currentWeek = weekNumber;
        this.currentWeekTitle = weekTitle || `Week ${weekNumber}`;

        if (!this.modal) {
            console.error('[WeekContentManager] Modal element not found');
            return;
        }

        // Update modal title
        const modalTitle = document.getElementById('week-modal-title');
        if (modalTitle) {
            modalTitle.innerHTML = `
                <div class="week-notes-header">
                    <span class="week-notes-number">Week ${weekNumber}</span>
                    <span class="week-notes-title">${this.escapeHtml(weekTitle)}</span>
                </div>
            `;
        }

        const modalBody = document.getElementById('week-modal-body');

        // Show modal
        this.modal.classList.add('show');

        // Show floating AI tutor button
        this.showFloatingAIButton();

        // Use cached week data (already fetched during loadWeeks) instead of making another API call
        // This is more efficient and works for non-admin users
        const weekData = this.getCachedWeekData(weekNumber);

        if (weekData) {
            modalBody.innerHTML = this.formatStudyNotes(weekData);
        } else {
            // Fallback: show placeholder if week data not in cache
            console.warn('[WeekContentManager] Week data not found in cache for week:', weekNumber);
            modalBody.innerHTML = this.getPlaceholderStudyNotes(weekNumber, weekTitle);
        }
    }
    
    formatStudyNotes(data) {
        let html = '<div class="study-notes-content">';

        // Overview section with icon
        if (data.description) {
            html += `
                <div class="notes-section notes-overview">
                    <div class="notes-section-header">
                        <span class="notes-icon">📋</span>
                        <h3>Overview</h3>
                    </div>
                    <div class="notes-section-content">
                        <p class="notes-description">${this.escapeHtml(data.description)}</p>
                    </div>
                </div>
            `;
        }

        // Learning Objectives with checkboxes
        if (data.learningObjectives?.length) {
            html += `
                <div class="notes-section notes-objectives">
                    <div class="notes-section-header">
                        <span class="notes-icon">🎯</span>
                        <h3>Learning Objectives</h3>
                    </div>
                    <div class="notes-section-content">
                        <ul class="objectives-list">
            `;
            data.learningObjectives.forEach((obj, idx) => {
                html += `
                    <li class="objective-item">
                        <span class="objective-number">${idx + 1}</span>
                        <span class="objective-text">${this.escapeHtml(obj)}</span>
                    </li>
                `;
            });
            html += `
                        </ul>
                    </div>
                </div>
            `;
        }

        // Key Topics with visual cards
        if (data.topics?.length) {
            html += `
                <div class="notes-section notes-topics">
                    <div class="notes-section-header">
                        <span class="notes-icon">📚</span>
                        <h3>Key Topics</h3>
                    </div>
                    <div class="notes-section-content">
                        <div class="topics-grid">
            `;
            data.topics.forEach(topic => {
                const topicText = typeof topic === 'string' ? topic : (topic.name || topic);
                const topicDesc = typeof topic === 'object' ? topic.description : '';
                html += `
                    <div class="topic-card-note">
                        <div class="topic-card-title">${this.escapeHtml(topicText)}</div>
                        ${topicDesc ? `<div class="topic-card-desc">${this.escapeHtml(topicDesc)}</div>` : ''}
                    </div>
                `;
            });
            html += `
                        </div>
                    </div>
                </div>
            `;
        }

        // Key Concepts with highlight boxes
        if (data.keyConcepts?.length) {
            html += `
                <div class="notes-section notes-concepts">
                    <div class="notes-section-header">
                        <span class="notes-icon">💡</span>
                        <h3>Key Concepts</h3>
                    </div>
                    <div class="notes-section-content">
            `;
            data.keyConcepts.forEach((concept, idx) => {
                // FIX BUG #1: Handle both string and object formats
                let conceptText, conceptDesc, conceptSource;
                if (typeof concept === 'string') {
                    conceptText = concept;
                    conceptDesc = '';
                    conceptSource = '';
                } else if (typeof concept === 'object') {
                    // Support multiple object formats
                    conceptText = concept.term || concept.name || concept.title || '[Unnamed Concept]';
                    conceptDesc = concept.definition || concept.description || '';
                    conceptSource = concept.source || '';
                }

                html += `
                    <div class="concept-box">
                        <div class="concept-header">
                            <span class="concept-badge">Concept ${idx + 1}</span>
                            <span class="concept-title">${this.escapeHtml(conceptText)}</span>
                        </div>
                        ${conceptDesc ? `<div class="concept-description">${this.escapeHtml(conceptDesc)}</div>` : ''}
                        ${conceptSource ? `<div class="concept-source"><em>Source: ${this.escapeHtml(conceptSource)}</em></div>` : ''}
                    </div>
                `;
            });
            html += `
                    </div>
                </div>
            `;
        }

        // FIX BUG #2: Add Key Cases section
        if (data.keyCases?.length) {
            html += `
                <div class="notes-section notes-cases">
                    <div class="notes-section-header">
                        <span class="notes-icon">⚖️</span>
                        <h3>Key Cases</h3>
                    </div>
                    <div class="notes-section-content">
            `;
            data.keyCases.forEach((caseItem, idx) => {
                let caseName, caseDesc, caseYear;
                if (typeof caseItem === 'string') {
                    caseName = caseItem;
                    caseDesc = '';
                    caseYear = '';
                } else if (typeof caseItem === 'object') {
                    caseName = caseItem.name || caseItem.title || '[Unnamed Case]';
                    caseDesc = caseItem.description || caseItem.holding || '';
                    caseYear = caseItem.year || '';
                }

                html += `
                    <div class="case-card">
                        <div class="case-header">
                            <span class="case-number">${idx + 1}</span>
                            <span class="case-name">${this.escapeHtml(caseName)}</span>
                            ${caseYear ? `<span class="case-year">(${this.escapeHtml(caseYear)})</span>` : ''}
                        </div>
                        ${caseDesc ? `<div class="case-description">${this.escapeHtml(caseDesc)}</div>` : ''}
                    </div>
                `;
            });
            html += `
                    </div>
                </div>
            `;
        }

        // FIX BUG #2: Add Key Frameworks section
        if (data.keyFrameworks?.length) {
            html += `
                <div class="notes-section notes-frameworks">
                    <div class="notes-section-header">
                        <span class="notes-icon">🔧</span>
                        <h3>Key Frameworks</h3>
                    </div>
                    <div class="notes-section-content">
                        <ul class="frameworks-list">
            `;
            data.keyFrameworks.forEach((framework, idx) => {
                const frameworkText = typeof framework === 'string' ? framework : (framework.name || framework.title || framework);
                const frameworkDesc = typeof framework === 'object' ? (framework.description || '') : '';

                html += `
                    <li class="framework-item">
                        <div class="framework-header">
                            <span class="framework-number">${idx + 1}</span>
                            <span class="framework-text">${this.escapeHtml(frameworkText)}</span>
                        </div>
                        ${frameworkDesc ? `<div class="framework-description">${this.escapeHtml(frameworkDesc)}</div>` : ''}
                    </li>
                `;
            });
            html += `
                        </ul>
                    </div>
                </div>
            `;
        }

        // Materials with file icons
        if (data.materials?.length) {
            html += `
                <div class="notes-section notes-materials">
                    <div class="notes-section-header">
                        <span class="notes-icon">📄</span>
                        <h3>Study Materials</h3>
                    </div>
                    <div class="notes-section-content">
                        <ul class="materials-list">
            `;
            data.materials.forEach(mat => {
                const matTitle = typeof mat === 'string' ? mat : (mat.title || mat.filename || mat);
                const matType = this.getFileIcon(matTitle);
                html += `
                    <li class="material-item">
                        <span class="material-icon">${matType}</span>
                        <span class="material-name">${this.escapeHtml(matTitle)}</span>
                    </li>
                `;
            });
            html += `
                        </ul>
                    </div>
                </div>
            `;
        }

        // Exam Tips with special styling - handle both string and array
        if (data.examTips) {
            html += `
                <div class="notes-section notes-tips">
                    <div class="notes-section-header">
                        <span class="notes-icon">⭐</span>
                        <h3>Exam Tips</h3>
                    </div>
                    <div class="notes-section-content">
            `;

            if (Array.isArray(data.examTips)) {
                html += '<ul class="exam-tips-list">';
                data.examTips.forEach((tip, idx) => {
                    const tipText = typeof tip === 'string' ? tip : (tip.text || tip.tip || tip);
                    html += `
                        <li class="exam-tip-item">
                            <span class="tip-number">💡</span>
                            <span class="tip-text">${this.escapeHtml(tipText)}</span>
                        </li>
                    `;
                });
                html += '</ul>';
            } else {
                html += `<div class="exam-tips-box">${this.escapeHtml(data.examTips)}</div>`;
            }

            html += `
                    </div>
                </div>
            `;
        }

        html += '</div>'; // Close study-notes-content

        // FIX BUG #3: Add action buttons at the bottom
        html += `
            <div class="modal-actions">
                <button class="btn-action btn-quiz" onclick="weekContentManager.generateQuizForWeek()">
                    <span class="btn-icon">📝</span>
                    <span class="btn-text">Generate Quiz</span>
                </button>
                <button class="btn-action btn-flashcards" onclick="weekContentManager.generateFlashcardsForWeek()">
                    <span class="btn-icon">🗂️</span>
                    <span class="btn-text">Generate Flashcards</span>
                </button>
                <button class="btn-action btn-tutor" onclick="weekContentManager.askAITutorAboutWeek()">
                    <span class="btn-icon">🤖</span>
                    <span class="btn-text">Ask AI Tutor</span>
                </button>
            </div>
        `;

        return html || this.getPlaceholderStudyNotes(data.weekNumber || this.currentWeek, data.title || this.currentWeekTitle);
    }

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': '📕',
            'docx': '📘',
            'doc': '📘',
            'pptx': '📊',
            'ppt': '📊',
            'txt': '📝',
            'md': '📝',
            'html': '🌐'
        };
        return icons[ext] || '📄';
    }
    
    getPlaceholderStudyNotes(weekNumber, weekTitle) {
        return `
            <div class="study-notes-content">
                <div class="notes-section notes-overview">
                    <div class="notes-section-header">
                        <span class="notes-icon">📚</span>
                        <h3>${this.escapeHtml(weekTitle || `Week ${weekNumber}`)}</h3>
                    </div>
                    <div class="notes-section-content">
                        <p class="notes-description">Study notes for this week are being prepared.</p>
                        <div class="placeholder-actions">
                            <p>In the meantime, you can:</p>
                            <ul class="objectives-list">
                                <li class="objective-item">
                                    <span class="objective-number">1</span>
                                    <span class="objective-text">Ask the AI Tutor questions about this week's topics</span>
                                </li>
                                <li class="objective-item">
                                    <span class="objective-number">2</span>
                                    <span class="objective-text">Generate a quiz to test your knowledge</span>
                                </li>
                                <li class="objective-item">
                                    <span class="objective-number">3</span>
                                    <span class="objective-text">Create flashcards for key concepts</span>
                                </li>
                                <li class="objective-item">
                                    <span class="objective-number">4</span>
                                    <span class="objective-text">Upload your own materials for analysis</span>
                                </li>
                            </ul>
                        </div>
                        <div class="exam-tips-box">
                            💡 <strong>Tip:</strong> Click the floating professor button to ask the AI Tutor about this week's material.
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    showFloatingAIButton() {
        // Remove existing button if any
        const existing = document.getElementById('floating-ai-tutor');
        if (existing) existing.remove();

        // Create floating button
        const button = document.createElement('button');
        button.id = 'floating-ai-tutor';
        button.className = 'floating-ai-button';
        button.innerHTML = '👨‍🏫';
        button.title = 'Ask AI Tutor about this week';
        button.onclick = () => this.openAITutorFromNotes();

        // Add to modal
        if (this.modal) {
            this.modal.appendChild(button);
        }
    }

    hideFloatingAIButton() {
        const button = document.getElementById('floating-ai-tutor');
        if (button) button.remove();
    }

    openAITutorFromNotes() {
        // Close modal
        this.closeModal();

        // Navigate to AI tutor
        this.openAITutor(this.currentWeek, this.currentWeekTitle);
    }
    
    openAITutor(weekNumber, weekTitle) {
        // Validate weekNumber if provided
        if (weekNumber !== null && weekNumber !== undefined) {
            if (!Number.isInteger(weekNumber) || weekNumber < 1 || weekNumber > 52) {
                console.error('[WeekContentManager] Invalid weekNumber:', weekNumber);
                throw new TypeError(`weekNumber must be an integer between 1 and 52, got: ${weekNumber}`);
            }
        }

        // Close week modal if open
        this.closeModal();

        // Switch to AI Tutor tab
        const tutorTab = document.querySelector('[data-tab="tutor"]');
        if (tutorTab) {
            tutorTab.click();

            // Wait for tab to switch, then pre-fill context
            setTimeout(() => {
                const chatInput = document.getElementById('chat-input');
                if (chatInput) {
                    const title = weekTitle || `Week ${weekNumber}`;
                    chatInput.value = `I'd like to learn about ${title}. Can you give me an overview of the key concepts?`;
                    chatInput.focus();
                }
            }, 100);
        }
    }
    
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('show');
        }
        this.hideFloatingAIButton();
    }
    
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    // FIX BUG #3: Action button methods
    generateQuizForWeek() {
        console.log('[WeekContentManager] Generating quiz for week:', this.currentWeek);

        // Close modal
        this.closeModal();

        // Switch to Quiz tab
        if (typeof switchTab === 'function') {
            switchTab('quiz');
        }

        // Set week number in quiz form
        setTimeout(() => {
            const weekSelect = document.getElementById('quiz-week');
            if (weekSelect) {
                weekSelect.value = this.currentWeek;
            }

            // Auto-populate topic with week title
            const topicInput = document.getElementById('quiz-topic');
            if (topicInput && this.currentWeekTitle) {
                topicInput.value = this.currentWeekTitle;
            }

            // Show notification
            if (typeof showNotification === 'function') {
                showNotification(`Ready to generate quiz for ${this.currentWeekTitle}`, 'success', 3000);
            }
        }, 300);
    }

    generateFlashcardsForWeek() {
        console.log('[WeekContentManager] Generating flashcards for week:', this.currentWeek);

        // Close modal
        this.closeModal();

        // Switch to Flashcards tab
        if (typeof switchTab === 'function') {
            switchTab('flashcards');
        }

        // Set week number and topic
        setTimeout(() => {
            const weekSelect = document.getElementById('flashcard-week');
            if (weekSelect) {
                weekSelect.value = this.currentWeek;
            }

            const topicInput = document.getElementById('flashcard-topic');
            if (topicInput && this.currentWeekTitle) {
                topicInput.value = this.currentWeekTitle;
            }

            // Show notification
            if (typeof showNotification === 'function') {
                showNotification(`Ready to generate flashcards for ${this.currentWeekTitle}`, 'success', 3000);
            }
        }, 300);
    }

    askAITutorAboutWeek() {
        console.log('[WeekContentManager] Opening AI Tutor for week:', this.currentWeek);

        // Close modal
        this.closeModal();

        // Switch to AI Tutor tab
        if (typeof switchTab === 'function') {
            switchTab('tutor');
        }

        // Pre-fill tutor input with week context
        setTimeout(() => {
            const tutorInput = document.getElementById('tutor-input');
            if (tutorInput) {
                tutorInput.value = `I have questions about ${this.currentWeekTitle}`;
                tutorInput.focus();
            }

            // Show notification
            if (typeof showNotification === 'function') {
                showNotification(`AI Tutor ready to help with ${this.currentWeekTitle}`, 'success', 3000);
            }
        }, 300);
    }
}

// Global functions for modal buttons
function closeWeekModal() {
    if (window.weekContentManager) {
        window.weekContentManager.closeModal();
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.weekContentManager = new WeekContentManager();
});

