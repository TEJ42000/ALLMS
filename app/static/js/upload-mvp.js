/**
 * Upload Manager for ALLMS MVP
 * 
 * Handles file upload, AI analysis, and integration with quiz/flashcard generation
 * 
 * Features:
 * - Drag & drop file upload
 * - Progress tracking
 * - AI analysis with Claude
 * - Integration with existing quiz/flashcard systems
 * 
 * Issue #200 - MVP Implementation
 */

class UploadManager {
    constructor() {
        this.dropzone = document.getElementById('upload-dropzone');
        this.fileInput = document.getElementById('file-input');
        this.progressDiv = document.getElementById('upload-progress');
        this.resultsDiv = document.getElementById('upload-results');
        this.analysisContent = document.getElementById('analysis-content');
        
        this.currentMaterialId = null;
        this.currentAnalysis = null;
        this.currentFilename = null;
        
        this.init();
    }
    
    init() {
        if (!this.dropzone) {
            console.warn('[UploadManager] Upload section not found');
            return;
        }
        
        console.log('[UploadManager] Initializing upload functionality');
        
        // Click to upload
        this.dropzone.addEventListener('click', () => {
            this.fileInput.click();
        });
        
        // File input change
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });
        
        // Drag and drop events
        this.dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropzone.classList.add('dragover');
        });
        
        this.dropzone.addEventListener('dragleave', () => {
            this.dropzone.classList.remove('dragover');
        });
        
        this.dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                this.handleFile(e.dataTransfer.files[0]);
            }
        });
        
        // Action buttons
        const quizBtn = document.getElementById('generate-quiz-btn');
        const flashcardsBtn = document.getElementById('generate-flashcards-btn');
        const anotherBtn = document.getElementById('upload-another-btn');
        
        if (quizBtn) quizBtn.addEventListener('click', () => this.generateQuiz());
        if (flashcardsBtn) flashcardsBtn.addEventListener('click', () => this.generateFlashcards());
        if (anotherBtn) anotherBtn.addEventListener('click', () => this.reset());

        // Load recent uploads
        this.loadRecentUploads();

        console.log('[UploadManager] Initialization complete');
    }
    
    async handleFile(file) {
        console.log('[UploadManager] Handling file:', file.name);
        
        const courseId = window.COURSE_CONTEXT?.courseId || 'LLS-2025-2026';
        
        // Show progress
        this.dropzone.style.display = 'none';
        this.progressDiv.style.display = 'block';
        this.resultsDiv.style.display = 'none';
        
        this.updateProgress(file.name, 'Uploading...');
        
        try {
            // Upload file
            const formData = new FormData();
            formData.append('file', file);
            formData.append('course_id', courseId);
            
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                const error = await uploadResponse.json();
                throw new Error(error.detail || 'Upload failed');
            }
            
            const uploadResult = await uploadResponse.json();
            
            if (uploadResult.status !== 'success') {
                throw new Error(uploadResult.message || 'Upload failed');
            }
            
            this.currentMaterialId = uploadResult.material_id;
            this.currentFilename = file.name;
            
            console.log('[UploadManager] Upload successful:', uploadResult.material_id);
            this.updateProgress(file.name, 'Analyzing with AI...');
            
            // Analyze file
            const analyzeResponse = await fetch(
                `/api/upload/${uploadResult.material_id}/analyze?course_id=${courseId}`,
                { method: 'POST' }
            );
            
            if (!analyzeResponse.ok) {
                const error = await analyzeResponse.json();
                throw new Error(error.detail || 'Analysis failed');
            }
            
            const analyzeResult = await analyzeResponse.json();
            
            if (analyzeResult.status !== 'success') {
                throw new Error(analyzeResult.message || 'Analysis failed');
            }
            
            this.currentAnalysis = analyzeResult;
            
            console.log('[UploadManager] Analysis complete:', analyzeResult.analysis);
            this.updateProgress(file.name, 'Complete!', 'complete');
            
            // Show results after short delay
            setTimeout(() => this.showResults(analyzeResult), 500);
            
        } catch (error) {
            console.error('[UploadManager] Error:', error);
            this.updateProgress(file.name, `Error: ${error.message}`, 'error');
            
            // Show error and allow retry
            setTimeout(() => {
                this.progressDiv.style.display = 'none';
                this.dropzone.style.display = 'block';
                if (typeof showNotification === 'function') {
                    showNotification(`Upload failed: ${error.message}`, 'error', 5000);
                }
            }, 2000);
        }
    }
    
    updateProgress(filename, status, statusClass = '') {
        const filenameEl = this.progressDiv.querySelector('.progress-filename');
        const statusEl = this.progressDiv.querySelector('.progress-status');
        
        if (filenameEl) filenameEl.textContent = filename;
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = 'progress-status ' + statusClass;
        }
    }
    
    showResults(result) {
        this.progressDiv.style.display = 'none';
        this.resultsDiv.style.display = 'block';
        
        const analysis = result.analysis;
        
        let html = `
            <div class="analysis-card">
                <h4>📄 ${this.escapeHtml(result.filename)}</h4>
                <p><strong>Type:</strong> ${this.escapeHtml(analysis.content_type || 'Unknown')}</p>
                <p><strong>Difficulty:</strong> ${this.escapeHtml(analysis.difficulty || 'Medium')}</p>
                <p><strong>Characters:</strong> ${(result.extraction?.char_count || 0).toLocaleString()}</p>
            </div>
        `;
        
        if (analysis.summary) {
            html += `
                <div class="analysis-card">
                    <h4>📝 Summary</h4>
                    <p>${this.escapeHtml(analysis.summary)}</p>
                </div>
            `;
        }
        
        if (analysis.main_topics?.length) {
            html += `
                <div class="analysis-card">
                    <h4>📚 Topics Covered</h4>
                    <div class="topic-tags">
                        ${analysis.main_topics.map(t => `<span class="topic-tag">${this.escapeHtml(t)}</span>`).join('')}
                    </div>
                </div>
            `;
        }
        
        if (analysis.key_concepts?.length) {
            html += `
                <div class="analysis-card">
                    <h4>💡 Key Concepts</h4>
                    <ul>
                        ${analysis.key_concepts.slice(0, 5).map(c => 
                            `<li><strong>${this.escapeHtml(c.term)}:</strong> ${this.escapeHtml(c.definition)}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (analysis.recommended_study_methods?.length) {
            html += `
                <div class="analysis-card">
                    <h4>🎯 Recommended Study Methods</h4>
                    <div class="topic-tags">
                        ${analysis.recommended_study_methods.map(m => `<span class="method-tag">${this.escapeHtml(m)}</span>`).join('')}
                    </div>
                </div>
            `;
        }
        
        this.analysisContent.innerHTML = html;
    }
    
    async generateQuiz() {
        if (!this.currentAnalysis) {
            console.warn('[UploadManager] No analysis available for quiz generation');
            if (typeof showNotification === 'function') {
                showNotification('Please analyze a file first before generating a quiz', 'warning');
            }
            return;
        }

        const analysis = this.currentAnalysis.analysis;
        const topic = analysis?.main_topics?.[0] || 'Uploaded Content';
        const difficulty = analysis?.difficulty_score > 7 ? 'hard' : (analysis?.difficulty_score > 4 ? 'medium' : 'easy');

        console.log('[UploadManager] Generating quiz for topic:', topic, 'difficulty:', difficulty);

        // Show loading notification
        if (typeof showNotification === 'function') {
            showNotification(`Generating quiz on "${topic}"...`, 'info', 3000);
        }

        try {
            // Call existing quiz generation API
            const response = await fetch(`${window.API_BASE || ''}/api/quizzes/courses/${this.courseId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': window.getUserId ? window.getUserId() : 'demo_user'
                },
                body: JSON.stringify({
                    course_id: this.courseId,
                    topic: topic,
                    num_questions: 10,
                    difficulty: difficulty,
                    allow_duplicate: false,
                    // Include analysis context for better question generation
                    context: {
                        key_concepts: analysis?.key_concepts || [],
                        learning_objectives: analysis?.learning_objectives || []
                    }
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Failed to generate quiz: ${response.status}`);
            }

            const data = await response.json();

            // Switch to quiz tab
            const quizTab = document.querySelector('[data-tab="quiz"]');
            if (quizTab) quizTab.click();

            // Trigger quiz display (call existing function if available)
            if (typeof window.displayQuiz === 'function') {
                window.displayQuiz(data.quiz);
            } else if (typeof window.resetQuizState === 'function') {
                window.resetQuizState(data.quiz);
            }

            // Show success notification
            if (typeof showNotification === 'function') {
                showNotification(`Quiz generated successfully! ${data.quiz.questions.length} questions ready.`, 'success');
            }

            console.log('[UploadManager] Quiz generated successfully:', data.quiz);

        } catch (error) {
            console.error('[UploadManager] Error generating quiz:', error);
            if (typeof showNotification === 'function') {
                showNotification(`Failed to generate quiz: ${error.message}`, 'error');
            }
        }
    }
    
    async generateFlashcards() {
        if (!this.currentAnalysis) {
            console.warn('[UploadManager] No analysis available for flashcard generation');
            if (typeof showNotification === 'function') {
                showNotification('Please analyze a file first before generating flashcards', 'warning');
            }
            return;
        }

        const analysis = this.currentAnalysis.analysis;
        const topic = analysis?.main_topics?.[0] || 'Uploaded Content';
        const numConcepts = analysis?.key_concepts?.length || 10;
        const numCards = Math.min(numConcepts * 2, 20); // 2 cards per concept, max 20

        console.log('[UploadManager] Generating flashcards for topic:', topic, 'num_cards:', numCards);

        // Show loading notification
        if (typeof showNotification === 'function') {
            showNotification(`Generating ${numCards} flashcards on "${topic}"...`, 'info', 3000);
        }

        try {
            // Call existing flashcard generation API
            const response = await fetch(`${window.API_BASE || ''}/api/files-content/flashcards`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    course_id: this.courseId,
                    topic: topic,
                    num_cards: numCards,
                    // Include analysis context for better flashcard generation
                    context: {
                        key_concepts: analysis?.key_concepts || [],
                        extracted_text: this.currentAnalysis.extracted_text?.substring(0, 5000) || ''
                    }
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Failed to generate flashcards: ${response.status}`);
            }

            const data = await response.json();

            if (!data.flashcards || data.flashcards.length === 0) {
                throw new Error('No flashcards generated');
            }

            // Switch to flashcards tab
            const flashcardsTab = document.querySelector('[data-tab="flashcards"]');
            if (flashcardsTab) flashcardsTab.click();

            // Transform and display flashcards (call existing function if available)
            if (typeof window.flashcards !== 'undefined') {
                window.flashcards = data.flashcards.map(card => ({
                    question: card.front || card.question || 'No question',
                    answer: card.back || card.answer || 'No answer',
                    category: 'upload',
                    known: false
                }));
                window.currentCardIndex = 0;

                if (typeof window.updateFlashcardDisplay === 'function') {
                    window.updateFlashcardDisplay();
                }
                if (typeof window.updateFlashcardStats === 'function') {
                    window.updateFlashcardStats();
                }
            }

            // Show success notification
            if (typeof showNotification === 'function') {
                showNotification(`${data.flashcards.length} flashcards generated successfully!`, 'success');
            }

            console.log('[UploadManager] Flashcards generated successfully:', data.flashcards.length);

        } catch (error) {
            console.error('[UploadManager] Error generating flashcards:', error);
            if (typeof showNotification === 'function') {
                showNotification(`Failed to generate flashcards: ${error.message}`, 'error');
            }
        }
    }
    
    reset() {
        console.log('[UploadManager] Resetting upload form');

        this.currentMaterialId = null;
        this.currentAnalysis = null;
        this.currentFilename = null;

        this.dropzone.style.display = 'block';
        this.progressDiv.style.display = 'none';
        this.resultsDiv.style.display = 'none';
        this.fileInput.value = '';

        // Reload recent uploads
        this.loadRecentUploads();
    }

    async loadRecentUploads() {
        console.log('[UploadManager] Loading recent uploads');

        const recentUploadsList = document.getElementById('recent-uploads-list');
        if (!recentUploadsList) return;

        const courseId = window.COURSE_CONTEXT?.courseId || 'LLS-2025-2026';

        try {
            const response = await fetch(`/api/upload/course/${courseId}?limit=5`);

            if (!response.ok) {
                throw new Error(`Failed to load uploads: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.materials || data.materials.length === 0) {
                recentUploadsList.innerHTML = '<p class="no-uploads">No uploads yet. Upload your first file above!</p>';
                return;
            }

            // File type icons
            const icons = {
                'pdf': '📕',
                'docx': '📘',
                'pptx': '📙',
                'txt': '📝',
                'md': '📝',
                'html': '🌐'
            };

            // Build HTML for recent uploads
            const uploadsHtml = data.materials.map(material => {
                const icon = icons[material.fileType] || '📄';
                const hasAnalysis = material.textExtracted && material.summaryGenerated;
                const statusIcon = hasAnalysis ? '✅' : '⏳';
                const statusText = hasAnalysis ? 'Analyzed' : 'Pending';

                // Format date
                let dateText = 'Recently';
                if (material.createdAt) {
                    const date = new Date(material.createdAt);
                    dateText = date.toLocaleDateString();
                }

                return `
                    <div class="recent-upload-item">
                        <div class="upload-item-info">
                            <span class="upload-item-icon">${icon}</span>
                            <div class="upload-item-details">
                                <div class="upload-item-name">${this.escapeHtml(material.filename)}</div>
                                <div class="upload-item-meta">${statusIcon} ${statusText} • ${dateText}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            recentUploadsList.innerHTML = uploadsHtml;

            console.log(`[UploadManager] Loaded ${data.materials.length} recent uploads`);

        } catch (error) {
            console.error('[UploadManager] Failed to load recent uploads:', error);
            recentUploadsList.innerHTML = '<p class="error-text">Failed to load recent uploads</p>';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[UploadManager] DOM ready, initializing...');
    window.uploadManager = new UploadManager();
});

