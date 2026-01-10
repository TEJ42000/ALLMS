/**
 * Cognitio Flow Homepage JavaScript
 * Handles course loading and interactions for the premium homepage
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
    console.log('[Homepage] Initializing...');
    
    coursesGrid = document.getElementById('courses-grid');
    loadingIndicator = document.getElementById('loading-indicator');
    errorMessage = document.getElementById('error-message');
    noCoursesMessage = document.getElementById('no-courses-message');
    
    // Smooth scroll for anchor links
    initSmoothScroll();
    
    // Load courses
    loadCourses();
});

/**
 * Initialize smooth scrolling for anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Load courses from the API
 */
async function loadCourses() {
    try {
        console.log('[Homepage] Loading courses from API...');
        showLoading();
        hideError();
        hideNoCourses();

        const response = await fetch(API_BASE);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('[Homepage] API response:', data);

        // Handle paginated response format: {items: [...], total: N, ...}
        // Also support legacy array format for backwards compatibility
        const courses = Array.isArray(data) ? data : (data.items || []);
        console.log('[Homepage] Courses found:', courses.length);

        hideLoading();

        if (courses.length === 0) {
            showNoCourses();
        } else {
            displayCourses(courses);
        }
    } catch (error) {
        console.error('[Homepage] Error loading courses:', error);
        hideLoading();
        showError();
    }
}

/**
 * Display courses in the grid
 */
function displayCourses(courses) {
    console.log('[Homepage] Displaying', courses.length, 'courses');
    coursesGrid.innerHTML = '';

    courses.forEach((course, index) => {
        console.log(`[Homepage] Creating card ${index + 1}:`, course);
        const courseCard = createCourseCard(course);
        coursesGrid.appendChild(courseCard);
    });
    
    console.log('[Homepage] ✅ All course cards rendered');
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
    const materialCount = course.materialCount || 0;

    // Determine status
    const isActive = course.isActive !== false;
    const statusClass = isActive ? 'active' : 'inactive';
    const statusText = isActive ? 'Active' : 'Inactive';

    card.innerHTML = `
        <div class="course-header">
            <div class="course-icon">${icon}</div>
            <span class="course-status ${statusClass}">${statusText}</span>
        </div>
        
        <h3 class="course-name">${escapeHtml(course.name)}</h3>
        <div class="course-id">${escapeHtml(course.id)}</div>
        
        <div class="course-meta">
            <div class="course-meta-item">
                <span class="meta-label">Academic Year</span>
                <span class="meta-value">${escapeHtml(academicYear)}</span>
            </div>
            <div class="course-meta-item">
                <span class="meta-label">ECTS Credits</span>
                <span class="meta-value">${ects}</span>
            </div>
            ${course.program ? `
                <div class="course-meta-item">
                    <span class="meta-label">Program</span>
                    <span class="meta-value">${escapeHtml(course.program)}</span>
                </div>
            ` : ''}
            ${course.institution ? `
                <div class="course-meta-item">
                    <span class="meta-label">Institution</span>
                    <span class="meta-value">${escapeHtml(course.institution)}</span>
                </div>
            ` : ''}
        </div>
        
        <div class="course-stats">
            <div class="stat-item">
                <span class="stat-icon">📅</span>
                <span class="stat-value">${weekCount}</span> weeks
            </div>
            <div class="stat-item">
                <span class="stat-icon">📚</span>
                <span class="stat-value">${materialCount}</span> materials
            </div>
        </div>
        
        <div class="course-cta">
            <button class="select-course-btn">
                Enter Study Portal →
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
    
    if (name.includes('criminal') || name.includes('crime')) {
        return '⚖️';
    } else if (name.includes('legal') || name.includes('law')) {
        return '📜';
    } else if (name.includes('history')) {
        return '📖';
    } else if (name.includes('constitutional') || name.includes('constitution')) {
        return '🏛️';
    } else if (name.includes('international')) {
        return '🌍';
    } else if (name.includes('contract')) {
        return '📝';
    } else if (name.includes('property')) {
        return '🏠';
    } else if (name.includes('tort')) {
        return '⚠️';
    } else {
        return '⚖️'; // Default legal icon
    }
}

/**
 * Select a course and navigate to the study portal
 */
function selectCourse(courseId) {
    console.log('[Homepage] Course selected:', courseId);
    
    // Store selected course in session storage
    sessionStorage.setItem('selectedCourse', courseId);
    
    // Navigate to course-specific study portal
    window.location.href = `/courses/${encodeURIComponent(courseId)}/study-portal`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Show loading indicator
 */
function showLoading() {
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    if (coursesGrid) {
        coursesGrid.style.display = 'none';
    }
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
    if (coursesGrid) {
        coursesGrid.style.display = 'grid';
    }
}

/**
 * Show error message
 */
function showError() {
    if (errorMessage) {
        errorMessage.style.display = 'block';
    }
    if (coursesGrid) {
        coursesGrid.style.display = 'none';
    }
}

/**
 * Hide error message
 */
function hideError() {
    if (errorMessage) {
        errorMessage.style.display = 'none';
    }
}

/**
 * Show no courses message
 */
function showNoCourses() {
    if (noCoursesMessage) {
        noCoursesMessage.style.display = 'block';
    }
    if (coursesGrid) {
        coursesGrid.style.display = 'none';
    }
}

/**
 * Hide no courses message
 */
function hideNoCourses() {
    if (noCoursesMessage) {
        noCoursesMessage.style.display = 'none';
    }
}

// Add scroll animations
window.addEventListener('scroll', () => {
    const features = document.querySelectorAll('.feature-card');
    const courses = document.querySelectorAll('.course-card');
    
    [...features, ...courses].forEach(element => {
        const rect = element.getBoundingClientRect();
        const isVisible = rect.top < window.innerHeight - 100;
        
        if (isVisible && !element.classList.contains('animated')) {
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            
            setTimeout(() => {
                element.style.transition = 'all 0.6s ease';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
                element.classList.add('animated');
            }, 100);
        }
    });
});

console.log('[Homepage] Script loaded successfully');

