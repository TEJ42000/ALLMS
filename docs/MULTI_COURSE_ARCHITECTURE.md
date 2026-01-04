# Multi-Course Support Architecture

## Overview

The LLS Study Portal now supports multiple courses with a course selection landing page and course-specific study portals. This document describes the architecture, implementation, and usage of the multi-course system.

## Architecture

### 1. Course Selection Flow

```
User visits / (root)
    ↓
Course Selection Landing Page
    ↓
User selects a course
    ↓
Redirects to /courses/{course_id}/study-portal
    ↓
Course-Specific Study Portal
```

### 2. URL Structure

| Route | Description | Template |
|-------|-------------|----------|
| `/` | Course selection landing page | `course_selection.html` |
| `/courses/{course_id}/study-portal` | Course-specific study portal | `index.html` (with course context) |

### 3. Course Context

Course context is passed from the backend to the frontend through:

1. **Template Variables**: Jinja2 templates receive `course_id`, `course_name`, and `course` object
2. **JavaScript Global**: `window.COURSE_CONTEXT` object contains course information
3. **Session Storage**: Selected course ID is stored in `sessionStorage`

## Components

### Backend Components

#### 1. Routes (`app/routes/pages.py`)

**`landing_page()`**
- Serves the course selection page at `/`
- No authentication required
- Displays all active courses

**`course_study_portal(course_id)`**
- Serves the study portal for a specific course
- Validates course exists and is active
- Passes course context to template
- Returns 404 if course not found

#### 2. Course Service Integration

The study portal integrates with the existing `CourseService` from issue #29:

```python
from app.services.course_service import get_course_service

service = get_course_service()
course = service.get_course(course_id, include_weeks=False)
```

### Frontend Components

#### 1. Course Selection Page

**Files:**
- `templates/course_selection.html`
- `app/static/css/course-selection.css`
- `app/static/js/course-selection.js`

**Features:**
- Fetches courses from `/api/admin/courses`
- Displays course cards with metadata
- Handles loading, error, and empty states
- Stores selected course in sessionStorage
- Navigates to course-specific portal

**Course Card Information:**
- Course name and ID
- Program and institution
- Academic year
- ECTS credits
- Week count
- Active/inactive status

#### 2. Course-Aware Study Portal

**Files:**
- `templates/index.html` (modified)
- `app/static/css/styles.css` (enhanced)
- `app/static/js/app.js` (enhanced)

**Enhancements:**
- Course badge in header showing current course
- "Change Course" link to return to selection page
- Course-specific welcome messages
- Course context in all API calls

#### 3. JavaScript Course Context

**Global Variables:**
```javascript
const COURSE_ID = window.COURSE_CONTEXT?.courseId || null;
const COURSE_NAME = window.COURSE_CONTEXT?.courseName || 'LLS';
const COURSE = window.COURSE_CONTEXT?.course || null;
```

**Helper Functions:**
```javascript
// Add course_id to API request parameters
function addCourseContext(params = {}) {
    if (COURSE_ID) {
        params.course_id = COURSE_ID;
    }
    return params;
}

// Build URL with query parameters
function buildUrl(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
            url.searchParams.append(key, params[key]);
        }
    });
    return url.toString();
}
```

**API Call Updates:**
All API calls now include course context:
```javascript
// Before
body: JSON.stringify({topic, num_questions})

// After
body: JSON.stringify(addCourseContext({topic, num_questions}))
```

## API Integration

### Course-Aware Endpoints

The following endpoints now accept optional `course_id` parameter:

| Endpoint | Method | Course Parameter |
|----------|--------|------------------|
| `/api/tutor/chat` | POST | `course_id` (optional) |
| `/api/assessment/assess` | POST | `course_id` (optional) |
| `/api/files-content/quiz` | POST | `course_id` (optional) |
| `/api/files-content/study-guide` | POST | `course_id` (optional) |
| `/api/files-content/flashcards` | POST | `course_id` (optional) |

When `course_id` is provided:
- System uses course-specific materials from Firestore
- Topics are loaded from course weeks
- Materials are filtered by course's `materialSubjects`

When `course_id` is NOT provided:
- System returns an error or redirects to course selection
- All features require course context

## Session Management

### Course Selection Persistence

```javascript
// Store selected course
sessionStorage.setItem('selectedCourse', courseId);

// Retrieve selected course
const courseId = sessionStorage.getItem('selectedCourse');
```

### Navigation Flow

1. User selects course → stored in sessionStorage
2. User navigates within portal → course context maintained via URL
3. User clicks "Change Course" → returns to `/` (selection page)
4. User closes browser → sessionStorage cleared

## Migration from Single-Course Setup

### For Existing Users

Users transitioning from the old single-course setup should:
1. Visit the root URL (`/`) to see the course selection page
2. Select their course (e.g., "LLS-2025-2026")
3. Bookmark the course-specific URL for quick access: `/courses/{course_id}/study-portal`

### API Compatibility

All API endpoints now require `course_id` parameter for course-specific functionality:
- Endpoints gracefully handle missing `course_id` by returning appropriate errors
- Frontend automatically includes `course_id` when in course context

## Styling

### Course Selection Page

**Theme:**
- Navy blue and gold color scheme (consistent with main portal)
- Glassmorphism effects
- Smooth animations and transitions

**Responsive Design:**
- Grid layout adapts to screen size
- Mobile-friendly course cards
- Touch-friendly buttons

### Study Portal Enhancements

**Course Badge:**
- Displays in header next to title
- Shows course ID
- Includes "Change Course" link with rotate animation

**Header Layout:**
- Flexbox layout for responsive design
- Wraps on smaller screens
- Maintains visual hierarchy

## Testing

### Manual Testing Checklist

- [ ] Course selection page loads and displays courses
- [ ] Course cards show correct metadata
- [ ] Clicking course navigates to study portal
- [ ] Course badge appears in portal header
- [ ] "Change Course" link returns to selection page
- [ ] API calls include course_id parameter
- [ ] Session storage persists course selection
- [ ] Error handling for invalid course IDs
- [ ] Loading states display correctly

### Test Scenarios

1. **New User Flow:**
   - Visit `/` → See course selection
   - Select course → Navigate to portal
   - Use features → Course context maintained

2. **Returning User Flow:**
   - Visit `/courses/{course_id}/study-portal` directly
   - Course context loaded from URL
   - All features work with course context

3. **Course Switching:**
   - In portal, click "Change Course"
   - Return to selection page
   - Select different course
   - New course context applied

## Future Enhancements

### Planned Features

1. **User Preferences:**
   - Remember last selected course per user
   - Store in database instead of sessionStorage

2. **Course Dashboard:**
   - Course-specific progress tracking
   - Week-by-week completion status
   - Course-specific statistics

3. **Week Navigation:**
   - Week selector in portal
   - Filter materials by week
   - Week-specific quizzes and study guides

4. **Authentication:**
   - User accounts
   - Course enrollment
   - Progress persistence

5. **Admin Features:**
   - Course activation/deactivation from UI
   - Course cloning
   - Bulk material upload per course

## Troubleshooting

### Common Issues

**Issue:** Course selection page shows no courses
- **Solution:** Check Firestore connection and course data
- **Check:** `/api/admin/courses` endpoint returns data

**Issue:** Course context not passed to API
- **Solution:** Verify `window.COURSE_CONTEXT` is set
- **Check:** View page source for course context script

**Issue:** 404 error when accessing course portal
- **Solution:** Verify course ID exists in Firestore
- **Check:** Course is marked as active

**Issue:** API calls failing without course_id
- **Solution:** Ensure you're accessing portal through course-specific URL
- **Check:** URL should be `/courses/{course_id}/study-portal`

## Related Documentation

- [Issue #29: Course Management System](https://github.com/TEJ42000/ALLMS/issues/29)
- [Course Data Models](../app/models/course_models.py)
- [Course Service](../app/services/course_service.py)
- [Admin API Documentation](../app/routes/admin_courses.py)

## Support

For questions or issues:
1. Check this documentation
2. Review issue #29 for course management details
3. Check API documentation at `/api/docs`
4. Contact development team

