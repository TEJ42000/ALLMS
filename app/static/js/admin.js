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
        renderMaterialsList(currentCourse.materials);
        showView('course-detail');
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
        renderMaterialsList(currentCourse.materials);
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderMaterialsList(materials) {
    const container = document.getElementById('materials-list');
    if (!materials) {
        container.innerHTML = '<p class="empty-state">No materials loaded. Click "Scan Folders" to discover materials.</p>';
        return;
    }

    const sections = [];

    // Core Textbooks
    if (materials.coreTextbooks?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📚 Core Textbooks (${materials.coreTextbooks.length})</h4>
                <ul class="materials-items">
                    ${materials.coreTextbooks.map(t => `
                        <li>
                            <span class="material-title">${t.title}</span>
                            <span class="material-meta">${t.size || ''} · ${t.type || 'textbook'}</span>
                        </li>
                    `).join('')}
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
                    ${materials.lectures.map(l => `
                        <li>
                            <span class="material-title">${l.title}</span>
                            <span class="material-meta">${l.week ? 'Week ' + l.week : 'No week'} · ${l.size || ''}</span>
                        </li>
                    `).join('')}
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
                    ${materials.readings.map(r => `
                        <li>
                            <span class="material-title">${r.title}</span>
                            <span class="material-meta">${r.week ? 'Week ' + r.week : 'No week'} · ${r.size || ''}</span>
                        </li>
                    `).join('')}
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
                    ${materials.caseStudies.map(c => `
                        <li>
                            <span class="material-title">${c.title}</span>
                            <span class="material-meta">${c.court || ''}</span>
                        </li>
                    `).join('')}
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
                    ${materials.mockExams.map(e => `
                        <li>
                            <span class="material-title">${e.title}</span>
                            <span class="material-meta">${e.size || ''}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `);
    }

    // Other
    if (materials.other?.length) {
        sections.push(`
            <div class="materials-category">
                <h4>📄 Other (${materials.other.length})</h4>
                <ul class="materials-items">
                    ${materials.other.map(o => `
                        <li>
                            <span class="material-title">${o.title}</span>
                            <span class="material-meta">${o.category || ''} · ${o.size || ''}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `);
    }

    if (sections.length === 0) {
        container.innerHTML = '<p class="empty-state">No materials found. Click "Scan Folders" to discover materials.</p>';
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
        container.innerHTML = materials.map((m, i) => `
            <div class="week-material-row" data-idx="${i}">
                <span class="material-type-badge">${m.type || 'other'}</span>
                <span class="material-info">
                    <strong>${m.title || m.file || 'Untitled'}</strong>
                    ${m.chapters ? `<small>Chapters: ${m.chapters.join(', ')}</small>` : ''}
                </span>
                <button type="button" class="btn-remove" onclick="removeWeekMaterial(${i})">✕</button>
            </div>
        `).join('');
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

