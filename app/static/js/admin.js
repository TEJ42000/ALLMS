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
        // API returns a list directly, not an object with courses property
        courses = Array.isArray(data) ? data : (data.courses || []);
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
        const response = await fetch(url, {
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
        const response = await fetch(`${API_BASE}/${currentCourse.id}/scan-materials`, {
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

    // Fetch uploaded materials if not provided
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

    // Helper to format file size
    const formatSize = (bytes) => {
        if (!bytes) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    // Convert uploaded materials to the scanned format and merge by category
    if (uploadedMaterials && uploadedMaterials.length > 0) {
        uploadedMaterials.forEach(um => {
            // Strip 'Materials/' prefix from storagePath for preview API compatibility
            let filePath = um.storagePath || '';
            if (filePath.startsWith('Materials/')) {
                filePath = filePath.substring('Materials/'.length);
            }

            const converted = {
                title: um.title || um.filename,
                file: filePath,
                size: formatSize(um.fileSize),
                week: um.weekNumber,
                isUploaded: true,  // Mark as uploaded for styling
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

    // Helper to render a material item with uploaded badges
    const renderMaterialItem = (m, weekHint = null) => {
        const uploadedBadge = m.isUploaded ? '<span class="material-badge badge-uploaded">📤 Uploaded</span>' : '';
        const summaryBadge = m.summaryGenerated ? '<span class="material-badge badge-summary">✨ AI Summary</span>' : '';
        const textBadge = m.textExtracted ? '<span class="material-badge badge-extracted">✓ Text</span>' : '';
        const badges = [uploadedBadge, summaryBadge, textBadge].filter(b => b).join(' ');

        return `
            <li class="${m.isUploaded ? 'uploaded-item' : ''}">
                <div class="material-item-content">
                    <span class="material-title">${m.title}</span>
                    <span class="material-meta">${getWeekDisplay(m.file, weekHint || m.week)} · ${m.size || m.court || ''}</span>
                    ${badges ? `<div class="material-badges">${badges}</div>` : ''}
                    ${m.summary ? `<div class="material-summary-inline" title="${m.summary.replace(/"/g, '&quot;')}">📝 ${m.summary.substring(0, 100)}${m.summary.length > 100 ? '...' : ''}</div>` : ''}
                </div>
                ${previewBtn(m.file, m.title)}
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
        const response = await fetch(`${API_BASE}/${currentCourse.id}/sync-week-materials`, {
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
        const response = await fetch(`${API_BASE}/${currentCourse.id}/weeks/${weekData.weekNumber}`, {
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
        ectsPoints: parseInt(document.getElementById('course-points').value) || null,
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
            <h3>${course.name || 'Untitled Course'}</h3>
            <div class="course-id">${course.id}</div>
            <div class="course-meta">
                ${course.institution || ''} ${course.academicYear ? '• ' + course.academicYear : ''}
                ${course.ectsPoints ? '• ' + course.ectsPoints + ' ECTS' : ''}
            </div>
            <span class="course-status ${(course.active ?? course.isActive) ? 'active' : 'inactive'}">
                ${(course.active ?? course.isActive) ? '● Active' : '○ Inactive'}
            </span>
        </div>
    `).join('');
    document.querySelectorAll('.course-card').forEach(card => {
        card.addEventListener('click', () => fetchCourse(card.dataset.courseId));
    });
}

function renderCourseForm() {
    if (!currentCourse) return;
    document.getElementById('course-id').value = currentCourse.id || '';
    document.getElementById('course-name').value = currentCourse.name || '';
    document.getElementById('course-program').value = currentCourse.program || '';
    document.getElementById('course-institution').value = currentCourse.institution || '';
    document.getElementById('course-year').value = currentCourse.academicYear || '';
    document.getElementById('course-points').value = currentCourse.ectsPoints || '';
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
        const response = await fetch(`${API_BASE}/syllabi/extract`, {
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

        const response = await fetch(API_BASE, {
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

            await fetch(`${API_BASE}/${courseId}/weeks/${weekNumber}`, {
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
    document.getElementById('back-to-list-btn').addEventListener('click', () => { showView('courses'); fetchCourses(); });
    document.getElementById('add-week-btn').addEventListener('click', addNewWeek);
    document.getElementById('add-component-btn').addEventListener('click', addComponent);
    document.getElementById('add-abbreviation-btn').addEventListener('click', addAbbreviation);
    document.getElementById('scan-materials-btn').addEventListener('click', scanMaterials);
    document.getElementById('sync-week-materials-btn').addEventListener('click', syncWeekMaterials);
    document.getElementById('import-syllabus-btn').addEventListener('click', openSyllabusModal);

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

