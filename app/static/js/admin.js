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
        courses = data.courses || [];
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
    const rows = document.querySelectorAll('#topics-list .item-row');
    return Array.from(rows).map(row => ({
        name: row.querySelector('.topic-name')?.value.trim() || '',
        description: row.querySelector('.topic-desc')?.value.trim() || ''
    })).filter(t => t.name);
}

function collectMaterials() {
    const rows = document.querySelectorAll('#materials-list .item-row');
    return Array.from(rows).map(row => ({
        title: row.querySelector('.mat-title')?.value.trim() || '',
        file: row.querySelector('.mat-file')?.value.trim() || '',
        pages: row.querySelector('.mat-pages')?.value.trim() || ''
    })).filter(m => m.title || m.file);
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
            <span class="course-status ${course.isActive ? 'active' : 'inactive'}">
                ${course.isActive ? '● Active' : '○ Inactive'}
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
    document.getElementById('course-active').checked = currentCourse.isActive !== false;
    document.getElementById('course-id').disabled = true;
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
    const topics = currentWeek?.topics || [];
    document.getElementById('topics-list').innerHTML = topics.map((t, i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${t.name || ''}" placeholder="Topic name" class="topic-name">
            <input type="text" value="${t.description || ''}" placeholder="Description" class="topic-desc">
            <button type="button" class="btn-remove" onclick="removeTopic(${i})">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No topics</p>';
}

function renderMaterialsList() {
    const materials = currentWeek?.materials || [];
    document.getElementById('materials-list').innerHTML = materials.map((m, i) => `
        <div class="item-row" data-idx="${i}">
            <input type="text" value="${m.title || ''}" placeholder="Material title" class="mat-title">
            <input type="text" value="${m.file || ''}" placeholder="Filename" class="mat-file">
            <input type="text" value="${m.pages || ''}" placeholder="Pages" class="mat-pages">
            <button type="button" class="btn-remove" onclick="removeMaterial(${i})">✕</button>
        </div>
    `).join('') || '<p class="empty-state">No materials</p>';
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
    currentWeek.topics.push({ name: '', description: '' });
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

    // Week actions
    document.getElementById('save-week-btn').addEventListener('click', saveWeek);
    document.getElementById('back-to-course-btn').addEventListener('click', () => showView('course-detail'));
    document.getElementById('add-topic-btn').addEventListener('click', addTopic);
    document.getElementById('add-material-btn').addEventListener('click', addMaterial);
    document.getElementById('add-concept-btn').addEventListener('click', addConcept);

    // Load specific course if provided
    if (window.initialCourseId) {
        fetchCourse(window.initialCourseId);
    }
});

