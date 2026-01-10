/**
 * LLS Admin Portal - Course Management JavaScript
 */
const API_BASE = '/api/admin/courses';
let currentCourse = null;
let currentWeek = null;
let courses = [];

const elements = {
    coursesView: document.getElementById('courses-view'),
    courseDetailView: document.getElementById('course-detail-view'),
    weekEditorView: document.getElementById('week-editor-view'),
    coursesList: document.getElementById('courses-list'),
    weeksList: document.getElementById('weeks-list'),
    loading: document.getElementById('loading'),
    toast: document.getElementById('toast'),
    tabs: {
        courses: document.querySelector('[data-view="courses"]'),
        courseDetail: document.getElementById('course-detail-tab'),
        weekEditor: document.getElementById('week-editor-tab')
    }
};

function showLoading() { elements.loading.classList.remove('hidden'); }
function hideLoading() { elements.loading.classList.add('hidden'); }

// Helper to format file size
function formatFileSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Display materials statistics
function displayMaterialsStats(stats) {
    const statsContainer = document.getElementById('materials-stats');
    if (!statsContainer) return;

    const textPending = stats.text_pending || 0;
    const summaryPending = stats.summary_pending || 0;

    statsContainer.innerHTML = `
        <div class="stats-bar">
            <span class="stat-item">📁 Total: ${stats.total}</span>
            <span class="stat-item">📤 Uploaded: ${stats.by_source?.uploaded || 0}</span>
            <span class="stat-item">🔍 Scanned: ${stats.by_source?.scanned || 0}</span>
            <span class="stat-item ${textPending > 0 ? 'pending' : 'complete'}">
                📝 Text: ${stats.text_extracted}/${stats.total}
            </span>
            <span class="stat-item ${summaryPending > 0 ? 'pending' : 'complete'}">
                ✨ Summaries: ${stats.summary_generated}/${stats.total}
            </span>
            ${textPending > 0 || summaryPending > 0 ? `
                <button class="btn-action batch-process-btn" onclick="batchProcessMaterials()">
                    🔄 Process All (${textPending + summaryPending} pending)
                </button>
            ` : ''}
        </div>
    `;
    statsContainer.classList.remove('hidden');
}

// Batch process materials (extract text and generate summaries)
async function batchProcessMaterials() {
    if (!currentCourse?.id) {
        showToast('No course selected', 'error');
        return;
    }

    if (!confirm('This will extract text and generate AI summaries for all pending materials. This may take several minutes and use API credits. Continue?')) {
        return;
    }

    try {
        showLoading();
        showToast('Processing materials... This may take a while.', 'info');

        const response = await secureFetch(`${API_BASE}/${currentCourse.id}/unified-materials/batch-process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                process_text: true,
                process_summary: true
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Batch processing failed');
        }

        const result = await response.json();
        showToast(`Processed ${result.processed} materials (${result.errors} errors)`, result.errors > 0 ? 'warning' : 'success');

        // Refresh the materials list
        await renderCourseMaterialsList(currentCourse.materials);

    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function showToast(message, type = 'info') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type}`;
    elements.toast.classList.remove('hidden');
    setTimeout(() => elements.toast.classList.add('hidden'), 3000);
}

function showView(viewName) {
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    if (viewName === 'courses') {
        elements.coursesView.classList.add('active');
        elements.tabs.courses.classList.add('active');
        elements.tabs.courseDetail.style.display = 'none';
        elements.tabs.weekEditor.style.display = 'none';
    } else if (viewName === 'course-detail') {
        elements.courseDetailView.classList.add('active');
        elements.tabs.courseDetail.style.display = 'inline-block';
        elements.tabs.courseDetail.classList.add('active');
    } else if (viewName === 'week-editor') {
        elements.weekEditorView.classList.add('active');
        elements.tabs.weekEditor.style.display = 'inline-block';
        elements.tabs.weekEditor.classList.add('active');
    }
}

async function fetchCourses() {
    showLoading();
    try {
        const response = await fetch(API_BASE);
        if (!response.ok) throw new Error('Failed to fetch courses');
        const data = await response.json();
        // Handle paginated response format: {items: [...], total: N, ...}
        // Also support legacy array format for backwards compatibility
        courses = Array.isArray(data) ? data : (data.items || data.courses || []);
        renderCoursesList();
    } catch (error) {
        showToast('Error loading courses: ' + error.message, 'error');
    } finally { hideLoading(); }
}

async function fetchCourse(courseId) {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/${courseId}?include_weeks=true`);
        if (!response.ok) throw new Error('Course not found');
        currentCourse = await response.json();
        renderCourseForm();
        renderWeeksList();
        renderCourseMaterialsList(currentCourse.materials);
        showView('course-detail');

        // Initialize upload functionality for this course
        if (typeof initUpload === 'function') {
            initUpload(courseId);
        }
    } catch (error) {
        showToast('Error loading course: ' + error.message, 'error');
    } finally { hideLoading(); }
}

async function saveCourse() {
    const courseData = getCourseFormData();
    if (!courseData.id) { showToast('Course ID is required', 'error'); return; }
    showLoading();
    try {
        const isNew = !currentCourse || currentCourse.id !== courseData.id;
        const method = isNew ? 'POST' : 'PATCH';
        const url = isNew ? API_BASE : `${API_BASE}/${courseData.id}`;
        const response = await secureFetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(courseData)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save course');
        }
        currentCourse = await response.json();
        showToast('Course saved successfully!', 'success');
        fetchCourses();
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally { hideLoading(); }
}

async function scanMaterials() {
    if (!currentCourse?.id) {
        showToast('Save the course first', 'error');
        return;
    }

    const useAI = document.getElementById('use-ai-titles')?.checked || false;
    showLoading();

    try {
        const response = await secureFetch(`${API_BASE}/${currentCourse.id}/scan-materials`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ use_ai_titles: useAI })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to scan materials');
        }

        const result = await response.json();
        showToast(result.message, 'success');

        // Refresh course data to get updated materials and render list
        await fetchCourse(currentCourse.id);
        renderCourseMaterialsList(currentCourse.materials);
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function renderCourseMaterialsList(materials, uploadedMaterials = null) {
    const container = document.getElementById('course-materials-list');
    if (!container) return;  // Guard for when not on course detail view

    // Try to use unified materials API first
    let unifiedMaterials = null;
    if (currentCourse?.id) {
        try {
            const response = await fetch(`/api/admin/courses/${currentCourse.id}/unified-materials?include_stats=true`);
            if (response.ok) {
                const data = await response.json();
                unifiedMaterials = data.materials || [];

                // Display stats if available
                if (data.stats) {
                    displayMaterialsStats(data.stats);
                }
            }
        } catch (e) {
            console.warn('Failed to fetch unified materials, falling back to legacy:', e);
        }
    }

    // If we got unified materials, convert them to the expected format
    if (unifiedMaterials && unifiedMaterials.length > 0) {
        // Convert unified materials to the legacy format for display
        materials = materials || {};
        uploadedMaterials = [];  // Clear - we'll use unified materials

        unifiedMaterials.forEach(um => {
            const converted = {
                title: um.title || um.filename,
                file: um.storagePath,
                size: formatFileSize(um.fileSize),
                week: um.weekNumber,
                isUploaded: um.source === 'uploaded',
                materialId: um.id,
                summary: um.summary,
                summaryGenerated: um.summaryGenerated,
                textExtracted: um.textExtracted,
                source: um.source
            };

            // Map category to the appropriate array
            const category = um.category?.toLowerCase();
            if (category === 'textbook') {
                if (!materials.coreTextbooks) materials.coreTextbooks = [];
                materials.coreTextbooks.push(converted);
            } else if (category === 'lecture') {
                if (!materials.lectures) materials.lectures = [];
                materials.lectures.push(converted);
            } else if (category === 'reading') {
                if (!materials.readings) materials.readings = [];
                materials.readings.push(converted);
            } else if (category === 'case') {
                if (!materials.caseStudies) materials.caseStudies = [];
                materials.caseStudies.push(converted);
            } else if (category === 'exam') {
                if (!materials.mockExams) materials.mockExams = [];
                materials.mockExams.push(converted);
            } else {
                if (!materials.other) materials.other = [];
                materials.other.push(converted);
            }
        });
    } else {
        // Fall back to legacy approach: fetch uploaded materials separately
        if (uploadedMaterials === null && currentCourse?.id) {
            try {
                const response = await fetch(`/api/admin/courses/${currentCourse.id}/materials/uploads`);
                if (response.ok) {
                    const data = await response.json();
                    uploadedMaterials = data.materials || [];
                } else {
                    uploadedMaterials = [];
                }
            } catch (e) {
                uploadedMaterials = [];
            }
        }
    }

    if (!materials && (!uploadedMaterials || uploadedMaterials.length === 0)) {
        container.innerHTML = '<p class="empty-state">No materials loaded. Click "Scan Folders" to discover materials or "Upload Files" to add new materials.</p>';
        return;
    }

    // Initialize materials object if null
    if (!materials) {
        materials = {};
    }

    // Build a map of file -> weeks that reference it
    const fileToWeeks = {};
    (currentCourse?.weeks || []).forEach(week => {
        (week.materials || []).forEach(m => {
            if (!fileToWeeks[m.file]) fileToWeeks[m.file] = [];
            fileToWeeks[m.file].push(week.weekNumber);
        });
    });

    // Helper to get week display for a material
    const getWeekDisplay = (file, hintWeek) => {
        const linkedWeeks = fileToWeeks[file] || [];
        if (linkedWeeks.length > 0) {
            return `Weeks: ${linkedWeeks.sort((a,b) => a-b).join(', ')}`;
        } else if (hintWeek) {
            return `Week ${hintWeek} (hint)`;
        } else {
            return 'Course-wide';
        }
    };

    // Helper to create preview button
    const previewBtn = (file, title) => {
        if (!file) return '';
        // Escape backslashes first, then single quotes for safe HTML attribute embedding
        const escapedFile = file.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const escapedTitle = (title || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        return `<button class="preview-btn" onclick="event.stopPropagation(); openPreviewModal('${escapedFile}', '${escapedTitle}')">👁️ Preview</button>`;
    };

    // Helper to create extraction status badge
    const extractionBadge = (file) => {
        if (!file) return '';
        const status = extractionCache.get(file);
        if (!status) {
            return '<span class="extraction-status-badge not-extracted">Not Checked</span>';
        }

        if (status.error) {
            return `<span class="extraction-status-badge failed" onclick="event.stopPropagation(); showToast('Error: ${status.error}', 'error')">Failed</span>`;
        }

        if (status.extracted) {
            const escapedFile = file.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            return `<span class="extraction-status-badge extracted" onclick="event.stopPropagation(); openTextPreviewModal('${escapedFile}')">
                Extracted
                <span class="extraction-metadata">${formatNumber(status.charCount)} chars</span>
            </span>`;
        }

        return '<span class="extraction-status-badge not-extracted">Not Extracted</span>';
    };

    // Helper to format file size
    const formatSize = (bytes) => {
        if (!bytes) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    // Build a set of uploaded file paths for deduplication
    const uploadedFilePaths = new Set();
    const uploadedMaterialIds = {};

    // Convert uploaded materials to the scanned format and merge by category
    if (uploadedMaterials && uploadedMaterials.length > 0) {
        uploadedMaterials.forEach(um => {
            // Strip 'Materials/' prefix from storagePath for preview API compatibility
            let filePath = um.storagePath || '';
            if (filePath.startsWith('Materials/')) {
                filePath = filePath.substring('Materials/'.length);
            }

            // Track uploaded paths for deduplication
            uploadedFilePaths.add(filePath);
            uploadedFilePaths.add(um.filename);  // Also track by filename
            uploadedMaterialIds[filePath] = um.id;

            const converted = {
                title: um.title || um.filename,
                file: filePath,
                size: formatSize(um.fileSize),
                week: um.weekNumber,
                isUploaded: true,  // Mark as uploaded for styling
                materialId: um.id,  // Store ID for delete functionality
                summary: um.summary,
                summaryGenerated: um.summaryGenerated,
                textExtracted: um.textExtracted,
                uploadedAt: um.uploadedAt
            };

            // Map category to the appropriate array
            const category = um.category?.toLowerCase();
            if (category === 'lecture') {
                if (!materials.lectures) materials.lectures = [];
                materials.lectures.push(converted);
            } else if (category === 'reading') {
                if (!materials.readings) materials.readings = [];
                materials.readings.push(converted);
            } else if (category === 'case') {
                if (!materials.caseStudies) materials.caseStudies = [];
                materials.caseStudies.push(converted);
            } else if (um.tier === 'syllabus') {
                // Syllabus goes to coreTextbooks
                if (!materials.coreTextbooks) materials.coreTextbooks = [];
                materials.coreTextbooks.push(converted);
            } else {
                // Default to 'other' for supplementary or uncategorized
                if (!materials.other) materials.other = [];
                materials.other.push(converted);
            }
        });
    }

    // Deduplicate: remove scanned materials that match uploaded materials
    const deduplicateArray = (arr) => {
        if (!arr) return arr;
        return arr.filter(m => {
            if (m.isUploaded) return true;  // Keep uploaded materials
            const filename = m.file ? m.file.split('/').pop() : '';
            return !uploadedFilePaths.has(m.file) && !uploadedFilePaths.has(filename);
        });
    };

    materials.coreTextbooks = deduplicateArray(materials.coreTextbooks);
    materials.lectures = deduplicateArray(materials.lectures);
    materials.readings = deduplicateArray(materials.readings);
    materials.caseStudies = deduplicateArray(materials.caseStudies);
    materials.mockExams = deduplicateArray(materials.mockExams);
    materials.other = deduplicateArray(materials.other);

    // Helper to render a material item with uploaded badges, extraction status, and delete button
    const renderMaterialItem = (m, weekHint = null) => {
        const uploadedBadge = m.isUploaded ? '<span class="material-badge badge-uploaded">📤 Uploaded</span>' : '';
        const summaryBadge = m.summaryGenerated ? '<span class="material-badge badge-summary">✨ AI Summary</span>' : '';
        const textBadge = m.textExtracted ? '<span class="material-badge badge-extracted">✓ Text</span>' : '';
        const badges = [uploadedBadge, summaryBadge, textBadge].filter(b => b).join(' ');

        // Delete button only for uploaded materials
        const deleteBtn = m.isUploaded && m.materialId
            ? `<button class="delete-btn" onclick="event.stopPropagation(); deleteMaterial('${m.materialId}')" title="Delete">🗑️</button>`
            : '';

        return `
            <li class="${m.isUploaded ? 'uploaded-item' : ''}">
                <div class="material-item-content">
                    <span class="material-title">${m.title}</span>
                    <span class="material-meta">${getWeekDisplay(m.file, weekHint || m.week)} · ${m.size || m.court || ''}</span>
                    ${badges ? `<div class="material-badges">${badges}</div>` : ''}
                    ${m.summary ? `<div class="material-summary-inline" title="${m.summary.replace(/"/g, '&quot;')}">📝 ${m.summary.substring(0, 100)}${m.summary.length > 100 ? '...' : ''}</div>` : ''}
                </div>
                <div class="material-actions-inline">
                    ${extractionBadge(m.file)}
                    ${previewBtn(m.file, m.title)}
                    ${deleteBtn}
                </div>
            </li>
        `;
    };

    const sections = [];

    // Core Textbooks
    if (materials.coreTextbooks?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📚 Core Textbooks (${materials.coreTextbooks.length})</h4>
                <ul class="materials-items">
                    ${materials.coreTextbooks.map(t => renderMaterialItem(t)).join('')}
                </ul>
            </div>
        `);
    }

    // Lectures
    if (materials.lectures?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>🎓 Lectures (${materials.lectures.length})</h4>
                <ul class="materials-items">
                    ${materials.lectures.map(l => renderMaterialItem(l, l.week)).join('')}
                </ul>
            </div>
        `);
    }

    // Readings
    if (materials.readings?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📖 Readings (${materials.readings.length})</h4>
                <ul class="materials-items">
                    ${materials.readings.map(r => renderMaterialItem(r, r.week)).join('')}
                </ul>
            </div>
        `);
    }

    // Case Studies
    if (materials.caseStudies?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>⚖️ Case Studies (${materials.caseStudies.length})</h4>
                <ul class="materials-items">
                    ${materials.caseStudies.map(c => renderMaterialItem(c)).join('')}
                </ul>
            </div>
        `);
    }

    // Mock Exams
    if (materials.mockExams?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📝 Mock Exams (${materials.mockExams.length})</h4>
                <ul class="materials-items">
                    ${materials.mockExams.map(e => renderMaterialItem(e)).join('')}
                </ul>
            </div>
        `);
    }

    // Other / Supplementary
    if (materials.other?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📄 Other / Supplementary (${materials.other.length})</h4>
                <ul class="materials-items">
                    ${materials.other.map(o => renderMaterialItem(o)).join('')}
                </ul>
            </div>
        `);
    }

    if (sections.length === 0) {
        container.innerHTML = '<p class="empty-state">No materials found. Click "Scan Folders" to discover materials or "Upload Files" to add new materials.</p>';
    } else {
        container.innerHTML = sections.join('');
    }
}

async function syncWeekMaterials() {
    if (!currentCourse?.id) {
        showToast('Save the course first', 'error');
        return;
    }

    showLoading();
    try {
        const response = await secureFetch(`${API_BASE}/${currentCourse.id}/sync-week-materials`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to sync materials');
        }

        const result = await response.json();
        showToast(result.message, 'success');

        // Refresh course data
        await fetchCourse(currentCourse.id);
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function saveWeek() {
    if (!currentCourse) { showToast('No course selected', 'error'); return; }
    const weekData = getWeekFormData();
    if (!weekData.weekNumber) { showToast('Week number is required', 'error'); return; }
    showLoading();
    try {
        const response = await secureFetch(`${API_BASE}/${currentCourse.id}/weeks/${weekData.weekNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(weekData)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save week');
        }
        showToast('Week saved successfully!', 'success');
        fetchCourse(currentCourse.id);
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally { hideLoading(); }
}

function getCourseFormData() {
    return {
        id: document.getElementById('course-id').value.trim(),
        name: document.getElementById('course-name').value.trim(),
        program: document.getElementById('course-program').value.trim(),
        institution: document.getElementById('course-institution').value.trim(),
        academicYear: document.getElementById('course-year').value.trim(),
        totalPoints: parseInt(document.getElementById('course-points').value) || null,
        materialSubjects: document.getElementById('course-subjects').value.split(',').map(s => s.trim()).filter(Boolean),
        components: collectComponents(),
        abbreviations: collectAbbreviations(),
        isActive: document.getElementById('course-active').checked
    };
}

function getWeekFormData() {
    return {
        weekNumber: parseInt(document.getElementById('week-number').value) || null,
        title: document.getElementById('week-title').value.trim(),
        description: document.getElementById('week-description').value.trim(),
        topics: collectTopics(),
        materials: collectMaterials(),
        keyConcepts: collectConcepts()
    };
}

function collectTopics() {
    // Topics are List[str] - simple strings, not objects
    const rows = document.querySelectorAll('#topics-list .item-row');
    return Array.from(rows).map(row =>
        row.querySelector('.topic-text')?.value.trim() || ''
    ).filter(t => t);
}

function collectComponents() {
    const rows = document.querySelectorAll('#components-list .item-row');
    return Array.from(rows).map(row => ({
        id: row.querySelector('.comp-id')?.value.trim() || '',
        name: row.querySelector('.comp-name')?.value.trim() || '',
        maxPoints: parseInt(row.querySelector('.comp-points')?.value) || 0,
        description: row.querySelector('.comp-desc')?.value.trim() || ''
    })).filter(c => c.id && c.name);
}

function collectAbbreviations() {
    const rows = document.querySelectorAll('#abbreviations-list .item-row');
    const abbrevs = {};
    rows.forEach(row => {
        const key = row.querySelector('.abbrev-key')?.value.trim() || '';
        const value = row.querySelector('.abbrev-value')?.value.trim() || '';
        if (key && value) abbrevs[key] = value;
    });
    return abbrevs;
}

function collectMaterials() {
    // Materials are now stored directly in currentWeek.materials
    // They're added via the picker, not via form inputs
    return (currentWeek?.materials || []).filter(m => m.file || m.title);
}

function collectConcepts() {
    const rows = document.querySelectorAll('#concepts-list .item-row');
    return Array.from(rows).map(row => ({
        term: row.querySelector('.concept-term')?.value.trim() || '',
        definition: row.querySelector('.concept-def')?.value.trim() || ''
    })).filter(c => c.term);
}

function renderCoursesList() {
    if (courses.length === 0) {
        elements.coursesList.innerHTML = '<p class="empty-state">No courses found. Create your first course!</p>';
        return;
    }
    elements.coursesList.innerHTML = courses.map(course => `
        <div class="course-card" data-course-id="${course.id}">
            <div class="course-card-header">
                <h3>${course.name || 'Untitled Course'}</h3>
                <button class="btn-icon btn-delete" data-course-id="${course.id}" data-course-name="${course.name || 'Untitled Course'}" title="Delete course permanently">
                    🗑️
                </button>
            </div>
            <div class="course-id">${course.id}</div>
            <div class="course-meta">
                ${course.institution || ''} ${course.academicYear ? '• ' + course.academicYear : ''}
                ${course.totalPoints ? '• ' + course.totalPoints + ' ECTS' : ''}
            </div>
            <span class="course-status ${(course.active ?? course.isActive) ? 'active' : 'inactive'}">
                ${(course.active ?? course.isActive) ? '● Active' : '○ Inactive'}
            </span>
        </div>
    `).join('');

    // Add click handlers for course cards (excluding delete button)
    document.querySelectorAll('.course-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't open course if clicking delete button
            if (e.target.closest('.btn-delete')) return;
            fetchCourse(card.dataset.courseId);
        });
    });

    // Add click handlers for delete buttons
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent card click
            const courseId = btn.dataset.courseId;
            const courseName = btn.dataset.courseName;
            confirmDeleteCourse(courseId, courseName);
        });
    });
}

function renderCourseForm() {
    if (!currentCourse) return;
    document.getElementById('course-id').value = currentCourse.id || '';
    document.getElementById('course-name').value = currentCourse.name || '';
    document.getElementById('course-program').value = currentCourse.program || '';
    document.getElementById('course-institution').value = currentCourse.institution || '';
    document.getElementById('course-year').value = currentCourse.academicYear || '';
    document.getElementById('course-points').value = currentCourse.totalPoints || '';
    document.getElementById('course-subjects').value = (currentCourse.materialSubjects || []).join(', ');
    document.getElementById('course-active').checked = (currentCourse.active ?? currentCourse.isActive) !== false;
    document.getElementById('course-id').disabled = true;
    renderComponentsList();
    renderAbbreviationsList();
}

function renderComponentsList() {
    const components = currentCourse?.components || [];
    document.getElementById('components-list').innerHTML = components.map((c, i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${c.id || ''}" placeholder="ID (e.g., part-a)" class="comp-id" style="width:100px">
            <input type="text" value="${c.name || ''}" placeholder="Name (e.g., Law)" class="comp-name">
            <input type="number" value="${c.maxPoints || ''}" placeholder="Points" class="comp-points" style="width:80px">
            <input type="text" value="${c.description || ''}" placeholder="Description" class="comp-desc">
            <button type="button" class="btn-remove" onclick="removeComponent(${i})">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No components defined</p>';
}

function renderAbbreviationsList() {
    const abbrevs = currentCourse?.abbreviations || {};
    const entries = Object.entries(abbrevs);
    document.getElementById('abbreviations-list').innerHTML = entries.map(([key, value], i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${key}" placeholder="Abbreviation (e.g., GALA)" class="abbrev-key" style="width:120px">
            <input type="text" value="${value}" placeholder="Full name" class="abbrev-value">
            <button type="button" class="btn-remove" onclick="removeAbbreviation('${key}')">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No abbreviations defined</p>';
}

function renderWeeksList() {
    const weeks = currentCourse?.weeks || [];
    if (weeks.length === 0) {
        elements.weeksList.innerHTML = '<p class="empty-state">No weeks configured. Click "Add Week" to create one.</p>';
        return;
    }
    elements.weeksList.innerHTML = weeks.sort((a, b) => a.weekNumber - b.weekNumber).map(week => `
        <div class="week-card" data-week="${week.weekNumber}">
            <div class="week-number">Week ${week.weekNumber}</div>
            <div class="week-title">${week.title || 'Untitled'}</div>
            <div class="week-stats">
                ${(week.topics || []).length} topics •
                ${(week.materials || []).length} materials •
                ${(week.keyConcepts || []).length} concepts
            </div>
        </div>
    `).join('');
    document.querySelectorAll('.week-card').forEach(card => {
        card.addEventListener('click', () => editWeek(parseInt(card.dataset.week)));
    });
}

function renderWeekForm() {
    if (!currentWeek) return;
    document.getElementById('week-number').value = currentWeek.weekNumber || '';
    document.getElementById('week-title').value = currentWeek.title || '';
    document.getElementById('week-description').value = currentWeek.description || '';
    renderTopicsList();
    renderMaterialsList();
    renderConceptsList();
}

function renderTopicsList() {
    // Topics are List[str] - simple strings, not objects
    const topics = currentWeek?.topics || [];
    document.getElementById('topics-list').innerHTML = topics.map((topic, i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${typeof topic === 'string' ? topic : (topic.name || '')}" placeholder="Topic name" class="topic-text">
            <button type="button" class="btn-remove" onclick="removeTopic(${i})">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No topics</p>';
}

function renderWeekMaterialsList() {
    const materials = currentWeek?.materials || [];
    const container = document.getElementById('week-materials-list');

    if (materials.length === 0) {
        container.innerHTML = '<p class="empty-state">No materials linked to this week</p>';
    } else {
        container.innerHTML = materials.map((m, i) => {
            // Escape backslashes first, then single quotes for safe HTML attribute embedding
            const escapedFile = (m.file || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const escapedTitle = (m.title || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const previewBtn = m.file
                ? `<button type="button" class="preview-btn" onclick="event.stopPropagation(); openPreviewModal('${escapedFile}', '${escapedTitle}')">👁️</button>`
                : '';
            return `
            <div class="week-material-row" data-idx="${i}">
                <span class="material-type-badge">${m.type || 'other'}</span>
                <span class="material-info">
                    <strong>${m.title || m.file || 'Untitled'}</strong>
                    ${m.chapters ? `<small>Chapters: ${m.chapters.join(', ')}</small>` : ''}
                </span>
                ${previewBtn}
                <button type="button" class="btn-remove" onclick="removeWeekMaterial(${i})">✕</button>
            </div>
        `}).join('');
    }

    // Also populate the material picker dropdown
    populateMaterialPicker();
}

function populateMaterialPicker() {
    const select = document.getElementById('material-picker-select');
    const courseMaterials = currentCourse?.materials || {};
    const currentWeekMaterials = currentWeek?.materials || [];

    // Get files already linked to this week
    const linkedFiles = new Set(currentWeekMaterials.map(m => m.file));

    let options = '<option value="">-- Select a material to add --</option>';

    // Add textbooks
    (courseMaterials.coreTextbooks || []).forEach(t => {
        if (!linkedFiles.has(t.file)) {
            options += `<option value="textbook|${t.file}|${t.title}">📚 ${t.title}</option>`;
        }
    });

    // Add lectures
    (courseMaterials.lectures || []).forEach(l => {
        if (!linkedFiles.has(l.file)) {
            const weekInfo = l.week ? ` (Week ${l.week})` : '';
            options += `<option value="lecture|${l.file}|${l.title}">🎓 ${l.title}${weekInfo}</option>`;
        }
    });

    // Add readings
    (courseMaterials.readings || []).forEach(r => {
        if (!linkedFiles.has(r.file)) {
            const weekInfo = r.week ? ` (Week ${r.week})` : '';
            options += `<option value="reading|${r.file}|${r.title}">📖 ${r.title}${weekInfo}</option>`;
        }
    });

    // Add case studies
    (courseMaterials.caseStudies || []).forEach(c => {
        if (!linkedFiles.has(c.file)) {
            options += `<option value="case|${c.file}|${c.title}">⚖️ ${c.title}</option>`;
        }
    });

    // Add exams
    (courseMaterials.mockExams || []).forEach(e => {
        if (!linkedFiles.has(e.file)) {
            options += `<option value="exam|${e.file}|${e.title}">📝 ${e.title}</option>`;
        }
    });

    // Add other
    (courseMaterials.other || []).forEach(o => {
        if (!linkedFiles.has(o.file)) {
            options += `<option value="other|${o.file}|${o.title}">📄 ${o.title}</option>`;
        }
    });

    select.innerHTML = options;
}

function addSelectedMaterial() {
    const select = document.getElementById('material-picker-select');
    const value = select.value;

    if (!value) {
        showToast('Select a material first', 'error');
        return;
    }

    const [type, file, title] = value.split('|');

    if (!currentWeek) currentWeek = { materials: [] };
    if (!currentWeek.materials) currentWeek.materials = [];

    currentWeek.materials.push({ type, file, title });
    renderWeekMaterialsList();
    showToast(`Added: ${title}`, 'success');
}

function addCustomMaterial() {
    if (!currentWeek) currentWeek = { materials: [] };
    if (!currentWeek.materials) currentWeek.materials = [];

    // Add an empty custom material
    currentWeek.materials.push({ type: 'other', file: '', title: 'Custom Material' });
    renderWeekMaterialsList();
}

function removeWeekMaterial(idx) {
    if (currentWeek?.materials) {
        currentWeek.materials.splice(idx, 1);
        renderWeekMaterialsList();
    }
}

// Keep old function name for compatibility
function renderMaterialsList() {
    renderWeekMaterialsList();
}

function addMaterial() {
    addCustomMaterial();
}

function removeMaterial(idx) {
    removeWeekMaterial(idx);
}

function renderConceptsList() {
    const concepts = currentWeek?.keyConcepts || [];
    document.getElementById('concepts-list').innerHTML = concepts.map((c, i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${c.term || ''}" placeholder="Term" class="concept-term">
            <input type="text" value="${c.definition || ''}" placeholder="Definition" class="concept-def">
            <button type="button" class="btn-remove" onclick="removeConcept(${i})">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No key concepts</p>';
}

// ========== Week Editor Functions ==========
function editWeek(weekNumber) {
    const weeks = currentCourse?.weeks || [];
    currentWeek = weeks.find(w => w.weekNumber === weekNumber) || { weekNumber, topics: [], materials: [], keyConcepts: [] };
    renderWeekForm();
    showView('week-editor');
}

function createNewCourse() {
    currentCourse = null;
    document.getElementById('course-id').value = '';
    document.getElementById('course-id').disabled = false;
    document.getElementById('course-name').value = '';
    document.getElementById('course-program').value = '';
    document.getElementById('course-institution').value = '';
    document.getElementById('course-year').value = '';
    document.getElementById('course-points').value = '';
    document.getElementById('course-subjects').value = '';
    document.getElementById('course-active').checked = true;
    document.getElementById('components-list').innerHTML = '<p class="empty-state">Save the course first to add components.</p>';
    document.getElementById('abbreviations-list').innerHTML = '<p class="empty-state">Save the course first to add abbreviations.</p>';
    elements.weeksList.innerHTML = '<p class="empty-state">Save the course first to add weeks.</p>';
    showView('course-detail');
}

function addNewWeek() {
    const weeks = currentCourse?.weeks || [];
    const nextNumber = weeks.length > 0 ? Math.max(...weeks.map(w => w.weekNumber)) + 1 : 1;
    currentWeek = { weekNumber: nextNumber, title: '', description: '', topics: [], materials: [], keyConcepts: [] };
    renderWeekForm();
    showView('week-editor');
}

// Item add/remove functions
function addTopic() {
    if (!currentWeek) currentWeek = { topics: [] };
    if (!currentWeek.topics) currentWeek.topics = [];
    currentWeek.topics.push('');  // Topics are simple strings
    renderTopicsList();
}

function removeTopic(idx) {
    if (currentWeek?.topics) {
        currentWeek.topics.splice(idx, 1);
        renderTopicsList();
    }
}

function addMaterial() {
    if (!currentWeek) currentWeek = { materials: [] };
    if (!currentWeek.materials) currentWeek.materials = [];
    currentWeek.materials.push({ title: '', file: '', pages: '' });
    renderMaterialsList();
}

function removeMaterial(idx) {
    if (currentWeek?.materials) {
        currentWeek.materials.splice(idx, 1);
        renderMaterialsList();
    }
}

function addConcept() {
    if (!currentWeek) currentWeek = { keyConcepts: [] };
    if (!currentWeek.keyConcepts) currentWeek.keyConcepts = [];
    currentWeek.keyConcepts.push({ term: '', definition: '' });
    renderConceptsList();
}

function removeConcept(idx) {
    if (currentWeek?.keyConcepts) {
        currentWeek.keyConcepts.splice(idx, 1);
        renderConceptsList();
    }
}

// Course component/abbreviation add/remove functions
function addComponent() {
    if (!currentCourse) { showToast('Save the course first', 'error'); return; }
    if (!currentCourse.components) currentCourse.components = [];
    currentCourse.components.push({ id: '', name: '', maxPoints: 0, description: '' });
    renderComponentsList();
}

function removeComponent(idx) {
    if (currentCourse?.components) {
        currentCourse.components.splice(idx, 1);
        renderComponentsList();
    }
}

function addAbbreviation() {
    if (!currentCourse) { showToast('Save the course first', 'error'); return; }
    if (!currentCourse.abbreviations) currentCourse.abbreviations = {};
    // Add a placeholder that will be replaced when saved
    const placeholder = `NEW_${Date.now()}`;
    currentCourse.abbreviations[placeholder] = '';
    renderAbbreviationsList();
}

function removeAbbreviation(key) {
    if (currentCourse?.abbreviations && key in currentCourse.abbreviations) {
        delete currentCourse.abbreviations[key];
        renderAbbreviationsList();
    }
}

// ========== Syllabus Import ==========
let selectedSyllabus = null;
let extractedSyllabusData = null;

async function openSyllabusModal() {
    document.getElementById('syllabus-modal').classList.remove('hidden');
    document.getElementById('syllabus-step-1').classList.remove('hidden');
    document.getElementById('syllabus-step-2').classList.add('hidden');
    document.getElementById('syllabus-back-btn').classList.add('hidden');
    document.getElementById('syllabus-extract-btn').classList.add('hidden');
    document.getElementById('syllabus-import-btn').classList.add('hidden');
    selectedSyllabus = null;
    extractedSyllabusData = null;

    // Scan for syllabi folders
    try {
        const response = await fetch(`${API_BASE}/syllabi/scan`);
        if (!response.ok) throw new Error('Failed to scan syllabi');
        const data = await response.json();
        renderSyllabiFolders(data.folders);
    } catch (error) {
        document.getElementById('syllabi-list').innerHTML =
            `<p class="error">Error scanning syllabi: ${error.message}</p>`;
    }
}

function closeSyllabusModal() {
    document.getElementById('syllabus-modal').classList.add('hidden');
}

function renderSyllabiFolders(folders) {
    const container = document.getElementById('syllabi-list');
    if (!folders || folders.length === 0) {
        container.innerHTML = '<p class="empty-state">No syllabus folders found in Materials/Syllabus/</p>';
        return;
    }

    container.innerHTML = folders.map(f => `
        <div class="syllabus-item" onclick="selectSyllabusFolder('${f.path}', '${f.subject}', this)">
            <div class="syllabus-info">
                <strong>📁 ${f.subject}</strong>
                <small>${f.files.length} file(s) | ${f.total_pages} total pages</small>
                <div class="syllabus-files">
                    ${f.files.map(file => `<span class="file-tag">📄 ${file.filename}</span>`).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

function selectSyllabusFolder(path, subject, element) {
    // Remove previous selection
    document.querySelectorAll('.syllabus-item').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    selectedSyllabus = { path, subject };
    document.getElementById('syllabus-extract-btn').classList.remove('hidden');
}

async function extractSyllabusData() {
    if (!selectedSyllabus) {
        showToast('Please select a syllabus first', 'error');
        return;
    }

    showLoading();
    try {
        const response = await secureFetch(`${API_BASE}/syllabi/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ syllabus_path: selectedSyllabus.path })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to extract data');
        }

        const result = await response.json();
        extractedSyllabusData = result.extracted_data;

        // Show step 2
        document.getElementById('syllabus-step-1').classList.add('hidden');
        document.getElementById('syllabus-step-2').classList.remove('hidden');
        document.getElementById('syllabus-extract-btn').classList.add('hidden');
        document.getElementById('syllabus-back-btn').classList.remove('hidden');
        document.getElementById('syllabus-import-btn').classList.remove('hidden');

        // Populate form
        document.getElementById('extracted-name').value = extractedSyllabusData.courseName || '';
        document.getElementById('extracted-code').value = extractedSyllabusData.courseCode || '';
        document.getElementById('extracted-year').value = extractedSyllabusData.academicYear || '';
        document.getElementById('extracted-program').value = extractedSyllabusData.program || '';
        document.getElementById('extracted-institution').value = extractedSyllabusData.institution || '';
        document.getElementById('extracted-points').value = extractedSyllabusData.totalPoints || '';
        document.getElementById('extracted-threshold').value = extractedSyllabusData.passingThreshold || '';
        document.getElementById('extracted-subjects').value = (extractedSyllabusData.materialSubjects || []).join(', ');

        // Show weeks preview
        const weeks = extractedSyllabusData.weeks || [];
        document.getElementById('extracted-weeks-count').textContent = weeks.length;
        document.getElementById('extracted-weeks-preview').innerHTML = weeks.map(w => `
            <div class="week-preview-item">
                <strong>Week ${w.weekNumber}: ${w.title || 'Untitled'}</strong>
                ${w.topics ? `<br><small>Topics: ${w.topics.join(', ')}</small>` : ''}
            </div>
        `).join('') || '<p class="empty-state">No weeks extracted</p>';

        showToast('Data extracted successfully!', 'success');
    } catch (error) {
        showToast('Error extracting data: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function syllabusStepBack() {
    document.getElementById('syllabus-step-1').classList.remove('hidden');
    document.getElementById('syllabus-step-2').classList.add('hidden');
    document.getElementById('syllabus-back-btn').classList.add('hidden');
    document.getElementById('syllabus-import-btn').classList.add('hidden');
    if (selectedSyllabus) {
        document.getElementById('syllabus-extract-btn').classList.remove('hidden');
    }
}

async function importSyllabusData() {
    // Get edited values from form
    const courseName = document.getElementById('extracted-name').value;
    const courseCode = document.getElementById('extracted-code').value;
    const academicYear = document.getElementById('extracted-year').value;

    if (!courseName || !academicYear) {
        showToast('Course name and academic year are required', 'error');
        return;
    }

    // Generate course ID from code or name
    const courseId = courseCode
        ? `${courseCode.replace(/[^a-zA-Z0-9]/g, '')}-${academicYear}`
        : `${courseName.replace(/[^a-zA-Z0-9]/g, '-').substring(0, 20)}-${academicYear}`;

    // Parse material subjects from comma-separated input
    const subjectsInput = document.getElementById('extracted-subjects').value;
    const materialSubjects = subjectsInput
        ? subjectsInput.split(',').map(s => s.trim()).filter(s => s)
        : [];

    showLoading();
    try {
        // Build syllabus data for storage
        const syllabusData = {
            sourceFolder: extractedSyllabusData.sourceFolder || '',
            sourceFiles: extractedSyllabusData.sourceFiles || [],
            rawText: extractedSyllabusData.rawText || '',
            sections: extractedSyllabusData.sections || [],
            courseDescription: extractedSyllabusData.courseDescription || null,
            learningObjectives: extractedSyllabusData.learningObjectives || [],
            prerequisites: extractedSyllabusData.prerequisites || null,
            teachingMethods: extractedSyllabusData.teachingMethods || null,
            assessmentInfo: extractedSyllabusData.assessmentInfo || null,
            assessments: extractedSyllabusData.assessments || [],
            lecturers: extractedSyllabusData.lecturers || [],
            officeHours: null,
            attendancePolicy: extractedSyllabusData.attendancePolicy || null,
            academicIntegrity: extractedSyllabusData.academicIntegrity || null,
            additionalNotes: extractedSyllabusData.additionalNotes || null
        };

        // Create course
        const courseData = {
            id: courseId,
            name: courseName,
            program: document.getElementById('extracted-program').value || null,
            institution: document.getElementById('extracted-institution').value || null,
            academicYear: academicYear,
            totalPoints: parseInt(document.getElementById('extracted-points').value) || null,
            passingThreshold: parseInt(document.getElementById('extracted-threshold').value) || null,
            components: extractedSyllabusData.components || [],
            materialSubjects: materialSubjects,
            syllabus: syllabusData
        };

        const response = await secureFetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(courseData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create course');
        }

        // Create weeks if extracted (using PUT upsert endpoint)
        const weeks = extractedSyllabusData.weeks || [];
        for (const week of weeks) {
            const weekNumber = week.weekNumber;
            if (!weekNumber) continue;

            const weekData = {
                weekNumber: weekNumber,
                title: week.title || `Week ${weekNumber}`,
                topics: week.topics || [],
                materials: [],
                keyConcepts: []
            };

            await secureFetch(`${API_BASE}/${courseId}/weeks/${weekNumber}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(weekData)
            });
        }

        showToast(`Course "${courseName}" created with ${weeks.length} weeks!`, 'success');
        closeSyllabusModal();
        fetchCourses();

    } catch (error) {
        showToast('Error importing course: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ========== Material Preview ==========
let slideViewerState = {
    filePath: null,
    currentPage: 1,
    totalPages: 0,
    slides: []
};

async function openPreviewModal(filePath, title) {
    // First, check the file type using the info endpoint
    const infoUrl = `${API_BASE}/materials/info/${encodeURIComponent(filePath).replace(/%2F/g, '/')}`;

    try {
        const response = await fetch(infoUrl);
        if (!response.ok) {
            throw new Error('Failed to get file info');
        }

        const info = await response.json();

        if (info.file_type === 'slide_archive') {
            // Open slide viewer
            openSlideViewer(filePath, title, info);
        } else if (info.file_type === 'pdf') {
            // Open PDF in new tab
            const previewUrl = `${API_BASE}/materials/preview/${encodeURIComponent(filePath).replace(/%2F/g, '/')}`;
            window.open(previewUrl, '_blank');
        } else {
            // Unknown type - offer download
            alert(`This file type (${info.file_type}) cannot be previewed. It may be corrupted or in an unsupported format.`);
        }
    } catch (error) {
        console.error('Preview error:', error);
        // Fallback: try opening as PDF
        const previewUrl = `${API_BASE}/materials/preview/${encodeURIComponent(filePath).replace(/%2F/g, '/')}`;
        window.open(previewUrl, '_blank');
    }
}

function openSlideViewer(filePath, title, info) {
    slideViewerState = {
        filePath: filePath,
        currentPage: 1,
        totalPages: info.num_pages || 0,
        slides: info.slides || []
    };

    // Create or get the slide viewer modal
    let modal = document.getElementById('slide-viewer-modal');
    if (!modal) {
        modal = createSlideViewerModal();
        document.body.appendChild(modal);
    }

    // Update title
    document.getElementById('slide-viewer-title').textContent = title || filePath.split('/').pop();
    document.getElementById('slide-page-info').textContent = `Page 1 of ${slideViewerState.totalPages}`;

    // Load first slide
    loadSlide(1);

    // Show modal
    modal.classList.remove('hidden');
}

function createSlideViewerModal() {
    const modal = document.createElement('div');
    modal.id = 'slide-viewer-modal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content slide-viewer-content">
            <div class="modal-header">
                <h3 id="slide-viewer-title">Slide Viewer</h3>
                <button class="close-btn" onclick="closeSlideViewer()">&times;</button>
            </div>
            <div class="slide-viewer-body">
                <div class="slide-container">
                    <img id="slide-image" src="" alt="Slide" />
                    <div id="slide-loading" class="slide-loading">Loading...</div>
                </div>
                <div class="slide-text-panel" id="slide-text-panel">
                    <h4>Slide Text</h4>
                    <pre id="slide-text-content"></pre>
                </div>
            </div>
            <div class="slide-controls">
                <button class="btn" onclick="prevSlide()" id="prev-slide-btn">◀ Previous</button>
                <span id="slide-page-info">Page 1 of 1</span>
                <button class="btn" onclick="nextSlide()" id="next-slide-btn">Next ▶</button>
                <button class="btn btn-secondary" onclick="toggleSlideText()" id="toggle-text-btn">Show Text</button>
            </div>
        </div>
    `;
    return modal;
}

async function loadSlide(pageNumber) {
    const { filePath, totalPages } = slideViewerState;
    if (pageNumber < 1 || pageNumber > totalPages) return;

    slideViewerState.currentPage = pageNumber;

    // Update UI
    document.getElementById('slide-page-info').textContent = `Page ${pageNumber} of ${totalPages}`;
    document.getElementById('prev-slide-btn').disabled = pageNumber <= 1;
    document.getElementById('next-slide-btn').disabled = pageNumber >= totalPages;

    // Show loading
    const loadingEl = document.getElementById('slide-loading');
    const imageEl = document.getElementById('slide-image');
    loadingEl.style.display = 'block';
    imageEl.style.opacity = '0.5';

    // Load image
    const imageUrl = `${API_BASE}/materials/slide/${encodeURIComponent(filePath).replace(/%2F/g, '/')}/page/${pageNumber}`;
    imageEl.onload = () => {
        loadingEl.style.display = 'none';
        imageEl.style.opacity = '1';
    };
    imageEl.onerror = () => {
        loadingEl.textContent = 'Failed to load slide';
        imageEl.style.opacity = '0.5';
    };
    imageEl.src = imageUrl;

    // Load text
    try {
        const textUrl = `${API_BASE}/materials/slide/${encodeURIComponent(filePath).replace(/%2F/g, '/')}/text?page=${pageNumber}`;
        const response = await fetch(textUrl);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('slide-text-content').textContent = data.text || '(No text on this slide)';
        }
    } catch (e) {
        document.getElementById('slide-text-content').textContent = '(Could not load text)';
    }
}

function prevSlide() {
    if (slideViewerState.currentPage > 1) {
        loadSlide(slideViewerState.currentPage - 1);
    }
}

function nextSlide() {
    if (slideViewerState.currentPage < slideViewerState.totalPages) {
        loadSlide(slideViewerState.currentPage + 1);
    }
}

function toggleSlideText() {
    const panel = document.getElementById('slide-text-panel');
    const btn = document.getElementById('toggle-text-btn');
    if (panel.classList.contains('visible')) {
        panel.classList.remove('visible');
        btn.textContent = 'Show Text';
    } else {
        panel.classList.add('visible');
        btn.textContent = 'Hide Text';
    }
}

function closeSlideViewer() {
    const modal = document.getElementById('slide-viewer-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function closePreviewModal() {
    closeSlideViewer();
    const modal = document.getElementById('preview-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// ========== Delete Material ==========
async function deleteMaterial(materialId) {
    if (!currentCourse?.id) {
        showToast('No course selected', 'error');
        return;
    }

    if (!confirm('Are you sure you want to delete this material? This action cannot be undone.')) {
        return;
    }

    try {
        showLoading();

        // Try unified endpoint first, fall back to legacy
        let response = await secureFetch(`${API_BASE}/${currentCourse.id}/unified-materials/${materialId}?delete_file=true`, {
            method: 'DELETE'
        });

        // If unified endpoint fails with 404, try legacy endpoint
        if (response.status === 404) {
            response = await secureFetch(`${API_BASE}/${currentCourse.id}/materials/uploads/${materialId}`, {
                method: 'DELETE'
            });
        }

        if (!response.ok && response.status !== 204) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete material');
        }

        showToast('Material deleted successfully', 'success');

        // Refresh the materials list
        await renderCourseMaterialsList(currentCourse?.materials);
    } catch (error) {
        console.error('Delete error:', error);
        showToast(`Failed to delete: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ========== Text Extraction Status UI ==========

// Configuration constants
const EXTRACTION_CONFIG = {
    // UI Display
    PREVIEW_CHAR_LIMIT: 500,              // Characters to show in preview before "Show More"
    ACTIVITY_LOG_LIMIT: 10,               // Number of recent activities to display
    PROGRESS_HIDE_DELAY: 3000,            // Milliseconds to wait before hiding progress (3 seconds)

    // Performance
    DEBOUNCE_DELAY: 500,                  // Milliseconds to debounce refresh button (0.5 seconds)
    MAX_CONCURRENT_EXTRACTIONS: 3,        // Maximum parallel extraction operations

    // Time calculations (in seconds)
    SECONDS_PER_MINUTE: 60,
    SECONDS_PER_HOUR: 3600,
    SECONDS_PER_DAY: 86400,
    SECONDS_PER_WEEK: 604800,

    // Number formatting
    THOUSAND: 1000,
    MILLION: 1000000
};

let extractionCache = new Map(); // Cache extraction status for files
let extractionInProgress = false;
let extractionAbortController = null;
let refreshDebounceTimer = null;  // Timer for debouncing refresh

/**
 * Debounced wrapper for refreshExtractionDashboard
 * Prevents rapid-fire API requests when users click refresh multiple times
 */
function refreshExtractionDashboard() {
    // Clear existing timer
    if (refreshDebounceTimer) {
        clearTimeout(refreshDebounceTimer);
    }

    // Set new timer
    refreshDebounceTimer = setTimeout(() => {
        refreshExtractionDashboardImmediate();
    }, EXTRACTION_CONFIG.DEBOUNCE_DELAY);
}

/**
 * Immediate refresh without debouncing (for internal use)
 */
async function refreshExtractionDashboardImmediate() {
    if (!currentCourse?.materials) {
        showToast('No materials loaded', 'error');
        return;
    }

    showLoading();
    try {
        // Get all file paths from materials
        const filePaths = getAllMaterialFilePaths(currentCourse.materials);

        // Fetch extraction status for all files
        const statusPromises = filePaths.map(path => getExtractionStatus(path));
        const statuses = await Promise.all(statusPromises);

        // Calculate metrics
        const metrics = calculateExtractionMetrics(statuses);

        // Update dashboard
        updateExtractionDashboard(metrics);

        // Update badges in materials list
        renderCourseMaterialsList(currentCourse.materials);

    } catch (error) {
        showToast('Error refreshing extraction stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function getAllMaterialFilePaths(materials) {
    const paths = [];
    if (materials.coreTextbooks) paths.push(...materials.coreTextbooks.map(m => m.file).filter(Boolean));
    if (materials.lectures) paths.push(...materials.lectures.map(m => m.file).filter(Boolean));
    if (materials.caseStudies) paths.push(...materials.caseStudies.map(m => m.file).filter(Boolean));
    if (materials.mockExams) paths.push(...materials.mockExams.map(m => m.file).filter(Boolean));
    if (materials.readings) paths.push(...materials.readings.map(m => m.file).filter(Boolean));
    return [...new Set(paths)]; // Remove duplicates
}

async function getExtractionStatus(filePath) {
    // Check cache first
    if (extractionCache.has(filePath)) {
        return extractionCache.get(filePath);
    }

    try {
        const response = await fetch(`/api/admin/cache/file/${encodeURIComponent(filePath)}`);
        if (response.ok) {
            const data = await response.json();
            const status = {
                path: filePath,
                extracted: data.cached,
                charCount: data.text_length || 0,
                fileType: data.file_type || 'unknown',
                extractionDate: data.cached_at || null,
                error: null
            };
            extractionCache.set(filePath, status);
            return status;
        } else if (response.status === 404) {
            const status = {
                path: filePath,
                extracted: false,
                charCount: 0,
                fileType: 'unknown',
                extractionDate: null,
                error: null
            };
            extractionCache.set(filePath, status);
            return status;
        } else {
            throw new Error('Failed to fetch status');
        }
    } catch (error) {
        return {
            path: filePath,
            extracted: false,
            charCount: 0,
            fileType: 'unknown',
            extractionDate: null,
            error: error.message
        };
    }
}

function calculateExtractionMetrics(statuses) {
    const total = statuses.length;
    const extracted = statuses.filter(s => s.extracted).length;
    const failed = statuses.filter(s => s.error).length;
    const totalChars = statuses.reduce((sum, s) => sum + s.charCount, 0);

    // Group by file type
    const byType = {};
    statuses.forEach(s => {
        if (!byType[s.fileType]) {
            byType[s.fileType] = { total: 0, extracted: 0 };
        }
        byType[s.fileType].total++;
        if (s.extracted) byType[s.fileType].extracted++;
    });

    return {
        total,
        extracted,
        failed,
        pending: total - extracted - failed,
        coverage: total > 0 ? Math.round((extracted / total) * 100) : 0,
        totalChars,
        byType
    };
}

function updateExtractionDashboard(metrics) {
    document.getElementById('extraction-coverage').textContent = `${metrics.coverage}%`;
    document.getElementById('extraction-total-files').textContent = metrics.total;
    document.getElementById('extraction-extracted').textContent = metrics.extracted;
    document.getElementById('extraction-failed').textContent = metrics.failed;
    document.getElementById('extraction-total-chars').textContent = formatNumber(metrics.totalChars);

    // Update by-type breakdown
    const typeContainer = document.getElementById('extraction-by-type');
    if (Object.keys(metrics.byType).length === 0) {
        typeContainer.innerHTML = '<p class="empty-state">No files found</p>';
    } else {
        typeContainer.innerHTML = Object.entries(metrics.byType)
            .map(([type, stats]) => `
                <div class="type-stat">
                    <span class="type-stat-label">${type.toUpperCase()}</span>
                    <span class="type-stat-value">${stats.extracted}/${stats.total}</span>
                </div>
            `).join('');
    }

    // Update activity log
    updateActivityLog();
}

function updateActivityLog() {
    const activityContainer = document.getElementById('extraction-activity-log');

    // Get recent extraction activities from cache
    const activities = [];
    extractionCache.forEach((status, filePath) => {
        if (status.extracted && status.extractionDate) {
            activities.push({
                file: filePath.split('/').pop(),
                date: new Date(status.extractionDate),
                chars: status.charCount
            });
        }
    });

    // Sort by date descending and take last N activities
    activities.sort((a, b) => b.date - a.date);
    const recentActivities = activities.slice(0, EXTRACTION_CONFIG.ACTIVITY_LOG_LIMIT);

    if (recentActivities.length === 0) {
        activityContainer.innerHTML = '<p class="empty-state">No recent activity</p>';
    } else {
        activityContainer.innerHTML = recentActivities.map(activity => {
            const timeAgo = getTimeAgo(activity.date);
            return `
                <div class="activity-item">
                    <div class="activity-item-time">${timeAgo}</div>
                    <div class="activity-item-text">Extracted ${activity.file} (${formatNumber(activity.chars)} chars)</div>
                </div>
            `;
        }).join('');
    }
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < EXTRACTION_CONFIG.SECONDS_PER_MINUTE) return 'Just now';
    if (seconds < EXTRACTION_CONFIG.SECONDS_PER_HOUR) return `${Math.floor(seconds / EXTRACTION_CONFIG.SECONDS_PER_MINUTE)} minutes ago`;
    if (seconds < EXTRACTION_CONFIG.SECONDS_PER_DAY) return `${Math.floor(seconds / EXTRACTION_CONFIG.SECONDS_PER_HOUR)} hours ago`;
    if (seconds < EXTRACTION_CONFIG.SECONDS_PER_WEEK) return `${Math.floor(seconds / EXTRACTION_CONFIG.SECONDS_PER_DAY)} days ago`;

    return date.toLocaleDateString();
}

function formatNumber(num) {
    if (num >= EXTRACTION_CONFIG.MILLION) return (num / EXTRACTION_CONFIG.MILLION).toFixed(1) + 'M';
    if (num >= EXTRACTION_CONFIG.THOUSAND) return (num / EXTRACTION_CONFIG.THOUSAND).toFixed(1) + 'K';
    return num.toString();
}

/**
 * Extract all materials with concurrent processing (max 3 at a time)
 * This significantly improves performance over sequential processing
 */
async function extractAllMaterials() {
    if (!currentCourse?.materials) {
        showToast('No materials loaded', 'error');
        return;
    }

    if (extractionInProgress) {
        showToast('Extraction already in progress', 'warning');
        return;
    }

    const filePaths = getAllMaterialFilePaths(currentCourse.materials);
    if (filePaths.length === 0) {
        showToast('No materials to extract', 'warning');
        return;
    }

    extractionInProgress = true;
    extractionAbortController = new AbortController();

    // Show progress container
    const progressContainer = document.getElementById('extraction-progress-container');
    progressContainer.style.display = 'block';

    const progressBar = document.getElementById('extraction-progress-bar');
    const progressText = document.getElementById('extraction-progress-text');
    const progressStats = document.getElementById('extraction-progress-stats');
    const errorsContainer = document.getElementById('extraction-errors-summary');

    let processed = 0;
    let errors = [];
    let currentlyProcessing = [];

    try {
        // Process files with concurrency limiting
        await processConcurrentExtractions(
            filePaths,
            async (filePath) => {
                // Update UI with currently processing files
                currentlyProcessing.push(filePath.split('/').pop());
                if (currentlyProcessing.length > EXTRACTION_CONFIG.MAX_CONCURRENT_EXTRACTIONS) {
                    currentlyProcessing.shift();
                }
                progressText.textContent = `Processing: ${currentlyProcessing.join(', ')}`;
                progressStats.textContent = `${processed} / ${filePaths.length} files`;

                try {
                    await extractSingleFile(filePath);
                    processed++;
                } catch (error) {
                    errors.push({ file: filePath, error: error.message });
                    processed++;
                }

                // Update progress bar
                const progress = Math.round((processed / filePaths.length) * 100);
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress}%`;

                // Remove from currently processing
                const idx = currentlyProcessing.indexOf(filePath.split('/').pop());
                if (idx > -1) currentlyProcessing.splice(idx, 1);
            },
            EXTRACTION_CONFIG.MAX_CONCURRENT_EXTRACTIONS,
            extractionAbortController.signal
        );

        // Show results
        if (errors.length > 0) {
            errorsContainer.style.display = 'block';
            document.getElementById('download-error-report-btn').onclick = () => downloadErrorReport(errors);
            showToast(`Extraction complete with ${errors.length} errors`, 'warning');
        } else {
            showToast('All files extracted successfully!', 'success');
        }

        // Refresh dashboard
        await refreshExtractionDashboardImmediate();

    } catch (error) {
        if (error.name === 'AbortError') {
            showToast('Extraction cancelled', 'warning');
        } else {
            showToast('Extraction failed: ' + error.message, 'error');
        }
    } finally {
        extractionInProgress = false;
        extractionAbortController = null;

        // Hide progress after configured delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
            errorsContainer.style.display = 'none';
        }, EXTRACTION_CONFIG.PROGRESS_HIDE_DELAY);
    }
}

/**
 * Process items concurrently with a maximum concurrency limit
 * @param {Array} items - Array of items to process
 * @param {Function} processor - Async function to process each item
 * @param {number} maxConcurrent - Maximum number of concurrent operations
 * @param {AbortSignal} signal - Optional abort signal
 */
async function processConcurrentExtractions(items, processor, maxConcurrent, signal) {
    const results = [];
    const executing = [];

    for (const item of items) {
        // Check if aborted
        if (signal?.aborted) {
            throw new DOMException('Aborted', 'AbortError');
        }

        // Create promise for this item
        const promise = processor(item).then(result => {
            // Remove from executing array when done
            executing.splice(executing.indexOf(promise), 1);
            return result;
        });

        results.push(promise);
        executing.push(promise);

        // If we've reached max concurrency, wait for one to finish
        if (executing.length >= maxConcurrent) {
            await Promise.race(executing);
        }
    }

    // Wait for all remaining promises to complete
    return Promise.all(results);
}

async function extractSingleFile(filePath) {
    // Use the correct endpoint for individual file extraction
    const response = await secureFetch(`/api/admin/cache/file/${encodeURIComponent(filePath)}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Extraction failed' }));
        throw new Error(error.detail || 'Extraction failed');
    }

    // Clear cache for this file to force refresh
    extractionCache.delete(filePath);

    return await response.json();
}

/**
 * Sanitize CSV cell value to prevent formula injection attacks
 * @param {string} value - The value to sanitize
 * @returns {string} - Sanitized value safe for CSV
 */
function sanitizeCSVValue(value) {
    if (!value) return '';

    const str = String(value);

    // Check if value starts with dangerous characters that could trigger formula execution
    // Dangerous prefixes: = + - @ \t \r (equals, plus, minus, at-sign, tab, carriage return)
    const dangerousChars = ['=', '+', '-', '@', '\t', '\r'];

    if (dangerousChars.some(char => str.startsWith(char))) {
        // Prefix with single quote to prevent formula injection
        // Also escape any existing quotes
        return "'" + str.replace(/"/g, '""');
    }

    // Escape double quotes by doubling them (CSV standard)
    return str.replace(/"/g, '""');
}

/**
 * Download error report as CSV file with proper sanitization
 * @param {Array} errors - Array of error objects with file and error properties
 */
function downloadErrorReport(errors) {
    // Sanitize all values to prevent CSV injection attacks
    const csvRows = errors.map(e => {
        const sanitizedFile = sanitizeCSVValue(e.file);
        const sanitizedError = sanitizeCSVValue(e.error);
        return `"${sanitizedFile}","${sanitizedError}"`;
    });

    const csv = 'File,Error\n' + csvRows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `extraction-errors-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

async function openTextPreviewModal(filePath) {
    const modal = document.getElementById('text-preview-modal');
    modal.classList.remove('hidden');

    // Show loading
    document.getElementById('preview-text-container').innerHTML = '<p class="empty-state">Loading...</p>';

    try {
        const response = await fetch(`/api/admin/cache/file/${encodeURIComponent(filePath)}`);
        if (!response.ok) throw new Error('Failed to load extracted text');

        const data = await response.json();

        // Update metadata
        document.getElementById('preview-file-path').textContent = filePath;
        document.getElementById('preview-file-type').textContent = data.file_type || 'unknown';
        document.getElementById('preview-extraction-date').textContent = data.cached_at ? new Date(data.cached_at).toLocaleString() : 'N/A';
        document.getElementById('preview-char-count').textContent = formatNumber(data.text_length || 0);
        document.getElementById('preview-page-count').textContent = data.metadata?.num_pages || 'N/A';
        document.getElementById('preview-extraction-method').textContent = data.file_type || 'N/A';

        // Show text (first N chars by default)
        const text = data.text || 'No text extracted';
        const previewContainer = document.getElementById('preview-text-container');
        previewContainer.textContent = text.substring(0, EXTRACTION_CONFIG.PREVIEW_CHAR_LIMIT);
        previewContainer.classList.add('collapsed');

        // Setup buttons
        document.getElementById('copy-text-btn').onclick = () => {
            navigator.clipboard.writeText(data.text || '');
            showToast('Text copied to clipboard!', 'success');
        };

        document.getElementById('show-full-text-btn').onclick = () => {
            if (previewContainer.classList.contains('collapsed')) {
                previewContainer.textContent = text;
                previewContainer.classList.remove('collapsed');
                document.getElementById('show-full-text-btn').textContent = '📖 Show Less';
            } else {
                previewContainer.textContent = text.substring(0, EXTRACTION_CONFIG.PREVIEW_CHAR_LIMIT);
                previewContainer.classList.add('collapsed');
                document.getElementById('show-full-text-btn').textContent = '📖 Show Full Text';
            }
        };

    } catch (error) {
        document.getElementById('preview-text-container').innerHTML = `<p class="error-text">Error: ${error.message}</p>`;
    }
}

function closeTextPreviewModal() {
    document.getElementById('text-preview-modal').classList.add('hidden');
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('text-preview-modal');
    if (modal && e.target === modal) {
        closeTextPreviewModal();
    }
});

// ========== Event Listeners ==========
document.addEventListener('DOMContentLoaded', () => {
    fetchCourses();

    // Tab navigation
    elements.tabs.courses.addEventListener('click', () => showView('courses'));
    elements.tabs.courseDetail.addEventListener('click', () => showView('course-detail'));
    elements.tabs.weekEditor.addEventListener('click', () => showView('week-editor'));

    // Course actions
    document.getElementById('create-course-btn').addEventListener('click', createNewCourse);
    document.getElementById('save-course-btn').addEventListener('click', saveCourse);
    document.getElementById('delete-course-detail-btn').addEventListener('click', () => {
        if (currentCourse) {
            confirmDeleteCourse(currentCourse.id, currentCourse.name);
        }
    });
    document.getElementById('back-to-list-btn').addEventListener('click', () => { showView('courses'); fetchCourses(); });
    document.getElementById('add-week-btn').addEventListener('click', addNewWeek);
    document.getElementById('add-component-btn').addEventListener('click', addComponent);
    document.getElementById('add-abbreviation-btn').addEventListener('click', addAbbreviation);
    document.getElementById('scan-materials-btn').addEventListener('click', scanMaterials);
    document.getElementById('sync-week-materials-btn').addEventListener('click', syncWeekMaterials);
    document.getElementById('import-syllabus-btn').addEventListener('click', openSyllabusModal);

    // Extraction actions
    document.getElementById('extract-all-btn').addEventListener('click', extractAllMaterials);
    document.getElementById('refresh-extraction-stats-btn').addEventListener('click', refreshExtractionDashboard);
    document.getElementById('cancel-extraction-btn').addEventListener('click', () => {
        if (extractionAbortController) {
            extractionAbortController.abort();
            showToast('Cancelling extraction...', 'info');
        }
    });

    // Week actions
    document.getElementById('save-week-btn').addEventListener('click', saveWeek);
    document.getElementById('back-to-course-btn').addEventListener('click', () => showView('course-detail'));
    document.getElementById('add-topic-btn').addEventListener('click', addTopic);
    document.getElementById('add-selected-material-btn').addEventListener('click', addSelectedMaterial);
    document.getElementById('add-custom-material-btn').addEventListener('click', addCustomMaterial);
    document.getElementById('add-concept-btn').addEventListener('click', addConcept);

    // Load specific course if provided
    if (window.initialCourseId) {
        fetchCourse(window.initialCourseId);
    }
});

// ========== Course Deletion ==========

/**
 * Show confirmation dialog before deleting a course.
 *
 * @param {string} courseId - Course ID to delete
 * @param {string} courseName - Course name for display
 */
function confirmDeleteCourse(courseId, courseName) {
    const message = `Are you sure you want to delete "${courseName}"?\n\n` +
                   `This will permanently delete:\n` +
                   `• All course weeks and materials\n` +
                   `• All student data and progress\n` +
                   `• All associated files\n\n` +
                   `⚠️ THIS ACTION CANNOT BE UNDONE!\n\n` +
                   `Type the course ID "${courseId}" to confirm:`;

    const confirmation = prompt(message);

    if (confirmation === courseId) {
        deleteCourse(courseId, courseName);
    } else if (confirmation !== null) {
        // User entered something but it didn't match
        alert('Course ID did not match. Deletion cancelled.');
    }
    // If confirmation is null, user clicked Cancel - do nothing
}

/**
 * Delete a course permanently.
 *
 * @param {string} courseId - Course ID to delete
 * @param {string} courseName - Course name for display
 */
async function deleteCourse(courseId, courseName) {
    try {
        showLoading();

        // Ask if they want to delete files too
        const deleteFiles = confirm(
            `Do you also want to delete the files from the Materials/${courseId}/ folder?\n\n` +
            `Click OK to delete files, or Cancel to keep them.`
        );

        const response = await secureFetch(`/api/admin/courses/${courseId}/permanent?delete_files=${deleteFiles}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to delete course: ${response.status}`);
        }

        hideLoading();
        alert(`✅ Course "${courseName}" has been permanently deleted.`);

        // Navigate back to course list and refresh
        showView('courses');
        fetchCourses();

    } catch (error) {
        hideLoading();
        console.error('Error deleting course:', error);
        alert(`❌ Failed to delete course: ${error.message}`);
    }
}

