/**
 * Week Content Display System
 * Fetches week data from API and renders interactive week cards
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
        if (!this.weeksGrid) {
            console.warn('[WeekContentManager] weeks-grid element not found');
            return;
        }
        await this.loadWeeks();
    }
    
    async loadWeeks() {
        try {
            console.log('[WeekContentManager] Loading weeks for course:', this.courseId);
            
            // Fetch weeks from existing admin API
            const response = await fetch(`/api/admin/courses/${this.courseId}?include_weeks=true`);
            if (!response.ok) throw new Error(`Failed to load weeks: ${response.status}`);
            
            const course = await response.json();
            const weeks = course.weeks || [];
            
            console.log('[WeekContentManager] Loaded', weeks.length, 'weeks');
            this.renderWeeks(weeks);
        } catch (error) {
            console.error('[WeekContentManager] Error loading weeks:', error);
            // Fallback: render placeholder weeks
            this.renderFallbackWeeks();
        }
    }
    
    renderWeeks(weeks) {
        if (!weeks || weeks.length === 0) {
            this.renderFallbackWeeks();
            return;
        }
        
        this.weeksGrid.innerHTML = '';
        
        // Sort by week number
        weeks.sort((a, b) => (a.weekNumber || 0) - (b.weekNumber || 0));
        
        weeks.forEach(week => {
            const card = this.createWeekCard(week);
            this.weeksGrid.appendChild(card);
        });
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
            
            <div class="week-card-actions">
                <button class="btn-study" onclick="weekContentManager.openWeekContent(${week.weekNumber}, '${this.escapeHtml(week.title || '')}')">
                    📖 Study
                </button>
                <button class="btn-ask-ai" onclick="weekContentManager.openAITutor(${week.weekNumber}, '${this.escapeHtml(week.title || '')}')">
                    🤖 Ask AI
                </button>
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
    
    async openWeekContent(weekNumber, weekTitle) {
        this.currentWeek = weekNumber;
        this.currentWeekTitle = weekTitle || `Week ${weekNumber}`;
        
        if (!this.modal) {
            console.error('[WeekContentManager] Modal element not found');
            return;
        }
        
        // Update modal title
        const modalTitle = document.getElementById('week-modal-title');
        if (modalTitle) {
            modalTitle.textContent = this.currentWeekTitle;
        }
        
        // Show loading state
        const modalBody = document.getElementById('week-modal-body');
        if (modalBody) {
            modalBody.innerHTML = '<div class="loading-placeholder">Loading content...</div>';
        }
        
        // Show modal
        this.modal.classList.add('show');
        
        try {
            // Fetch week details from admin API
            const response = await fetch(`/api/admin/courses/${this.courseId}/weeks/${weekNumber}`);
            
            if (response.ok) {
                const weekData = await response.json();
                modalBody.innerHTML = this.formatWeekContent(weekData);
            } else {
                // Fallback: show basic info
                modalBody.innerHTML = this.getPlaceholderContent(weekNumber, weekTitle);
            }
        } catch (error) {
            console.error('[WeekContentManager] Error loading week content:', error);
            modalBody.innerHTML = this.getPlaceholderContent(weekNumber, weekTitle);
        }
    }
    
    formatWeekContent(data) {
        let html = '';
        
        if (data.title) {
            html += `<h3>📋 ${this.escapeHtml(data.title)}</h3>`;
        }
        
        if (data.description) {
            html += `<p>${this.escapeHtml(data.description)}</p>`;
        }
        
        if (data.learningObjectives?.length) {
            html += `<h3>🎯 Learning Objectives</h3><ul>`;
            data.learningObjectives.forEach(obj => {
                html += `<li>${this.escapeHtml(obj)}</li>`;
            });
            html += `</ul>`;
        }
        
        if (data.topics?.length) {
            html += `<h3>📚 Key Topics</h3><ul>`;
            data.topics.forEach(topic => {
                const topicText = typeof topic === 'string' ? topic : (topic.name || topic);
                html += `<li><strong>${this.escapeHtml(topicText)}</strong></li>`;
            });
            html += `</ul>`;
        }
        
        if (data.keyConcepts?.length) {
            html += `<h3>💡 Key Concepts</h3>`;
            data.keyConcepts.forEach(concept => {
                const conceptText = typeof concept === 'string' ? concept : (concept.name || concept);
                html += `<div class="key-concept"><p>${this.escapeHtml(conceptText)}</p></div>`;
            });
        }
        
        if (data.materials?.length) {
            html += `<h3>📄 Materials</h3><ul>`;
            data.materials.forEach(mat => {
                const matTitle = typeof mat === 'string' ? mat : (mat.title || mat.filename || mat);
                html += `<li>${this.escapeHtml(matTitle)}</li>`;
            });
            html += `</ul>`;
        }
        
        if (data.examTips) {
            html += `<h3>💡 Exam Tips</h3><div class="key-concept">${this.escapeHtml(data.examTips)}</div>`;
        }
        
        return html || this.getPlaceholderContent(data.weekNumber || this.currentWeek, data.title || this.currentWeekTitle);
    }
    
    getPlaceholderContent(weekNumber, weekTitle) {
        return `
            <h3>📚 ${this.escapeHtml(weekTitle || `Week ${weekNumber}`)}</h3>
            <p>Content for this week is being prepared. In the meantime, you can:</p>
            <ul>
                <li>Ask the AI Tutor questions about this week's topics</li>
                <li>Generate a quiz to test your knowledge</li>
                <li>Create flashcards for key concepts</li>
                <li>Upload your own materials for analysis</li>
            </ul>
            <div class="key-concept">
                <p>💡 <strong>Tip:</strong> Click "Ask AI About This" below to start a tutoring session focused on this week's material.</p>
            </div>
        `;
    }
    
    openAITutor(weekNumber, weekTitle) {
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

function openAITutorFromModal() {
    if (window.weekContentManager && window.weekContentManager.currentWeek) {
        window.weekContentManager.openAITutor(
            window.weekContentManager.currentWeek,
            window.weekContentManager.currentWeekTitle
        );
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.weekContentManager = new WeekContentManager();
});

