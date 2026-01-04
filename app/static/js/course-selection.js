/**
 * Course Selection Page JavaScript
 * Handles loading and displaying available courses
 */

// API Base URL
const API_BASE = '/api/admin/courses';

// DOM Elements
let coursesGrid;
let loadingIndicator;
let errorMessage;
let noCoursesMessage;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    coursesGrid = document.getElementById('courses-grid');
    loadingIndicator = document.getElementById('loading-indicator');
    errorMessage = document.getElementById('error-message');
    noCoursesMessage = document.getElementById('no-courses-message');

    loadCourses();
});

/**
 * Load courses from the API
 */
async function loadCourses() {
    try {
        showLoading();
        hideError();
        hideNoCourses();

        const response = await fetch(API_BASE);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const courses = await response.json();
        
        hideLoading();

        if (courses.length === 0) {
            showNoCourses();
        } else {
            displayCourses(courses);
        }
    } catch (error) {
        console.error('Error loading courses:', error);
        hideLoading();
        showError();
    }
}

/**
 * Display courses in the grid
 */
function displayCourses(courses) {
    coursesGrid.innerHTML = '';

    courses.forEach(course => {
        const courseCard = createCourseCard(course);
        coursesGrid.appendChild(courseCard);
    });
}

/**
 * Create a course card element
 */
function createCourseCard(course) {
    const card = document.createElement('div');
    card.className = 'course-card';
    card.onclick = () => selectCourse(course.id);

    // Determine course icon based on name
    const icon = getCourseIcon(course.name);

    // Format academic year
    const academicYear = course.academicYear || 'N/A';

    // Calculate stats
    const weekCount = course.weekCount || 0;
    const ects = course.ects || 0;

    card.innerHTML = `
        <div class="course-card-header">
            <div class="course-icon">${icon}</div>
            <span class="course-status ${course.active ? 'active' : 'inactive'}">
                ${course.active ? '✓ Active' : '⏸ Inactive'}
            </span>
        </div>
        
        <h3 class="course-name">${escapeHtml(course.name)}</h3>
        <div class="course-id">ID: ${escapeHtml(course.id)}</div>
        
        <div class="course-meta">
            ${course.program ? `
                <div class="course-meta-item">
                    <span>📚</span>
                    <span><strong>Program:</strong> ${escapeHtml(course.program)}</span>
                </div>
            ` : ''}
            ${course.institution ? `
                <div class="course-meta-item">
                    <span>🏛️</span>
                    <span><strong>Institution:</strong> ${escapeHtml(course.institution)}</span>
                </div>
            ` : ''}
            <div class="course-meta-item">
                <span>📅</span>
                <span><strong>Academic Year:</strong> ${escapeHtml(academicYear)}</span>
            </div>
        </div>
        
        ${course.description ? `
            <p class="course-description">${escapeHtml(course.description)}</p>
        ` : ''}
        
        <div class="course-stats">
            <div class="course-stat">
                <div class="course-stat-value">${weekCount}</div>
                <div class="course-stat-label">Weeks</div>
            </div>
            <div class="course-stat">
                <div class="course-stat-value">${ects}</div>
                <div class="course-stat-label">ECTS</div>
            </div>
        </div>
        
        <div class="course-action">
            <button class="select-course-btn" onclick="event.stopPropagation(); selectCourse('${escapeHtml(course.id)}')">
                Enter Course →
            </button>
        </div>
    `;

    return card;
}

/**
 * Get appropriate icon for course based on name
 */
function getCourseIcon(courseName) {
    const name = courseName.toLowerCase();
    
    if (name.includes('law') || name.includes('legal')) {
        return '⚖️';
    } else if (name.includes('business') || name.includes('management')) {
        return '💼';
    } else if (name.includes('science') || name.includes('research')) {
        return '🔬';
    } else if (name.includes('art') || name.includes('design')) {
        return '🎨';
    } else if (name.includes('engineering')) {
        return '⚙️';
    } else if (name.includes('medicine') || name.includes('health')) {
        return '🏥';
    } else {
        return '📚';
    }
}

/**
 * Select a course and navigate to the study portal
 */
function selectCourse(courseId) {
    // Store selected course in session storage
    sessionStorage.setItem('selectedCourse', courseId);
    
    // Navigate to course-specific study portal
    window.location.href = `/courses/${encodeURIComponent(courseId)}/study-portal`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show loading indicator
 */
function showLoading() {
    loadingIndicator.style.display = 'block';
    coursesGrid.style.display = 'none';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    loadingIndicator.style.display = 'none';
    coursesGrid.style.display = 'grid';
}

/**
 * Show error message
 */
function showError() {
    errorMessage.style.display = 'block';
    coursesGrid.style.display = 'none';
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.style.display = 'none';
}

/**
 * Show no courses message
 */
function showNoCourses() {
    noCoursesMessage.style.display = 'block';
    coursesGrid.style.display = 'none';
}

/**
 * Hide no courses message
 */
function hideNoCourses() {
    noCoursesMessage.style.display = 'none';
}

