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

            this.renderWeeks(weeks);
        } catch (error) {
            console.error('[WeekContentManager] Error loading weeks:', error);
            // Fallback: render placeholder weeks
            this.renderFallbackWeeks();
        }
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
        console.log('[WeekContentManager] Sorted weeks:', weeks.map(w => `Week ${w.weekNumber}`));

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
            <span class="week-label">Week ${week.weekNumber}</span>
            <h3>${this.escapeHtml(week.title || `Week ${week.weekNumber}`)}</h3>
            <p class="week-description">${this.escapeHtml(description)}</p>

            ${topics.length > 0 ? `
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

        // Show loading state
        const modalBody = document.getElementById('week-modal-body');
        if (modalBody) {
            modalBody.innerHTML = '<div class="loading-placeholder">📚 Loading study notes...</div>';
        }

        // Show modal
        this.modal.classList.add('show');

        // Show floating AI tutor button
        this.showFloatingAIButton();

        try {
            // Fetch week details from admin API
            const response = await fetch(`/api/admin/courses/${this.courseId}/weeks/${weekNumber}`);

            if (response.ok) {
                const weekData = await response.json();
                modalBody.innerHTML = this.formatStudyNotes(weekData);
            } else {
                // Fallback: show basic info
                modalBody.innerHTML = this.getPlaceholderStudyNotes(weekNumber, weekTitle);
            }
        } catch (error) {
            console.error('[WeekContentManager] Error loading week content:', error);
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
                const conceptText = typeof concept === 'string' ? concept : (concept.name || concept);
                const conceptDesc = typeof concept === 'object' ? concept.description : '';
                html += `
                    <div class="concept-box">
                        <div class="concept-header">
                            <span class="concept-badge">Concept ${idx + 1}</span>
                            <span class="concept-title">${this.escapeHtml(conceptText)}</span>
                        </div>
                        ${conceptDesc ? `<div class="concept-description">${this.escapeHtml(conceptDesc)}</div>` : ''}
                    </div>
                `;
            });
            html += `
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

        // Exam Tips with special styling
        if (data.examTips) {
            html += `
                <div class="notes-section notes-tips">
                    <div class="notes-section-header">
                        <span class="notes-icon">⭐</span>
                        <h3>Exam Tips</h3>
                    </div>
                    <div class="notes-section-content">
                        <div class="exam-tips-box">
                            ${this.escapeHtml(data.examTips)}
                        </div>
                    </div>
                </div>
            `;
        }

        html += '</div>';

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

