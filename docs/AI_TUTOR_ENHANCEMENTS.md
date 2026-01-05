# AI Tutor Enhancements - Course-Aware Mode

## Overview

This document describes the enhancements made to the AI Tutor system to support the new multi-course architecture and data restructuring. The AI tutor now operates in two modes:

1. **Legacy Mode**: Uses hardcoded default topics (backward compatible)
2. **Course-Aware Mode**: Uses course-specific materials from Firestore

## Changes Summary

### Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `app/routes/ai_tutor.py` | Enhanced all endpoints | Added course-aware functionality |
| `app/models/schemas.py` | Added `course_id` field | Support course context in responses |
| `tests/test_ai_tutor.py` | Added 6 new tests | Test course-aware functionality |

### New Features

1. **Course-Aware Chat** (`POST /api/tutor/chat`)
   - Accepts optional `course_id` query parameter
   - Enhances context with course-specific topics
   - Returns `course_id` in response when provided

2. **Course-Specific Topics** (`GET /api/tutor/topics`)
   - Already supported `course_id` parameter
   - Returns topics from Firestore when course_id provided
   - Falls back to default topics for backward compatibility

3. **Course-Specific Examples** (`GET /api/tutor/examples`)
   - NEW: Accepts optional `course_id` query parameter
   - Generates examples based on course topics
   - Falls back to default examples

4. **Course Information** (`GET /api/tutor/course-info`)
   - NEW endpoint for comprehensive course details
   - Returns topics, weeks, materials count
   - Helps AI tutor provide course-specific assistance

---

## API Endpoints

### 1. POST /api/tutor/chat

**Enhanced with course-aware mode**

#### Legacy Mode (Backward Compatible)
```bash
POST /api/tutor/chat
Content-Type: application/json

{
  "message": "Explain Art. 6:74 DCC",
  "context": "Private Law"
}
```

#### Course-Aware Mode (NEW)
```bash
POST /api/tutor/chat?course_id=LLS-2025-2026
Content-Type: application/json

{
  "message": "Explain Art. 6:74 DCC",
  "context": "Private Law"
}
```

**Response:**
```json
{
  "content": "## Article 6:74 DCC - Damages\n\n...",
  "status": "success",
  "timestamp": "2026-01-05T10:00:00",
  "course_id": "LLS-2025-2026"
}
```

**Enhancements:**
- Context is enhanced with course topics when `course_id` provided
- Response includes `course_id` field
- Maintains backward compatibility

---

### 2. GET /api/tutor/topics

**Already supported course-aware mode** (no changes needed)

#### Legacy Mode
```bash
GET /api/tutor/topics
```

#### Course-Aware Mode
```bash
GET /api/tutor/topics?course_id=LLS-2025-2026
```

**Response:**
```json
{
  "topics": [
    {
      "id": "constitutional_law",
      "name": "Constitutional Law",
      "description": "Week 1: Introduction",
      "week": 1
    }
  ],
  "course_id": "LLS-2025-2026",
  "status": "success"
}
```

---

### 3. GET /api/tutor/examples

**Enhanced with course-aware mode**

#### Legacy Mode
```bash
GET /api/tutor/examples
```

#### Course-Aware Mode (NEW)
```bash
GET /api/tutor/examples?course_id=LLS-2025-2026
```

**Response (Course-Aware):**
```json
{
  "examples": [
    {
      "topic": "Constitutional Law",
      "week": 1,
      "questions": [
        "Explain the key concepts from Constitutional Law",
        "What are the main legal principles in Constitutional Law?",
        "Can you provide an example case for Constitutional Law?"
      ]
    }
  ],
  "course_id": "LLS-2025-2026",
  "status": "success"
}
```

**Enhancements:**
- Generates examples based on course topics
- Includes week numbers
- Falls back to default examples if course not found

---

### 4. GET /api/tutor/course-info (NEW)

**Comprehensive course information for AI tutor context**

```bash
GET /api/tutor/course-info?course_id=LLS-2025-2026
```

**Response:**
```json
{
  "course_id": "LLS-2025-2026",
  "name": "Law & Legal Skills",
  "description": "LLS Course 2025-2026",
  "topics": [
    {
      "id": "constitutional_law",
      "name": "Constitutional Law",
      "description": "Week 1: Introduction",
      "week": 1
    }
  ],
  "weeks": [
    {
      "number": 1,
      "title": "Introduction to Law",
      "topics": ["Constitutional Law"],
      "materials_count": 5
    }
  ],
  "materials_count": 45,
  "active": true,
  "status": "success"
}
```

**Use Cases:**
- Frontend can display course context
- AI tutor can access comprehensive course structure
- Helps users understand available materials

---

## Integration with Data Structure

### How It Works

1. **FilesAPIService Integration**
   - `get_course_topics(course_id)` retrieves topics from Firestore
   - Topics are extracted from week data
   - Normalized topic IDs for consistency

2. **CourseService Integration**
   - `get_course(course_id, include_weeks=True)` retrieves full course data
   - Single Firestore read for efficiency
   - Includes weeks, topics, and materials

3. **Context Enhancement**
   - When `course_id` provided, AI tutor context is enhanced
   - Includes course name and topic list
   - Helps AI provide more relevant responses

### Data Flow

```
User Request (with course_id)
    ↓
AI Tutor Endpoint
    ↓
FilesAPIService.get_course_topics(course_id)
    ↓
CourseService.get_course(course_id)
    ↓
Firestore (courses/{course_id})
    ↓
Enhanced Context → Anthropic API
    ↓
Response (with course_id)
```

---

## Backward Compatibility

### Legacy Mode Support

All endpoints maintain full backward compatibility:

1. **No `course_id` parameter**: Uses default topics
2. **Invalid `course_id`**: Falls back to defaults (with warning)
3. **Firestore unavailable**: Uses hardcoded defaults

### Default Topics

```python
DEFAULT_TOPICS = [
    {"id": "constitutional", "name": "Constitutional Law", ...},
    {"id": "administrative", "name": "Administrative Law", ...},
    {"id": "criminal", "name": "Criminal Law", ...},
    {"id": "private", "name": "Private Law", ...},
    {"id": "international", "name": "International Law", ...}
]
```

---

## Testing

### Test Coverage

**18 tests total** (all passing ✅):

1. **Legacy Mode Tests** (12 tests)
   - Chat endpoint functionality
   - Topics retrieval
   - Examples retrieval
   - Error handling

2. **Course-Aware Mode Tests** (6 new tests)
   - Chat with course_id
   - Topics with course_id
   - Examples with course_id
   - Course info endpoint
   - Invalid course handling
   - Error scenarios

### Running Tests

```bash
# Run all AI tutor tests
python3 -m pytest tests/test_ai_tutor.py -v

# Run only course-aware tests
python3 -m pytest tests/test_ai_tutor.py::TestCourseAwareMode -v
```

---

## Migration Guide

### For Frontend Developers

**No breaking changes!** All existing code continues to work.

**To use course-aware mode:**

```javascript
// Legacy mode (still works)
const response = await fetch('/api/tutor/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: 'Explain Art. 6:74 DCC',
    context: 'Private Law'
  })
});

// Course-aware mode (NEW)
const courseId = 'LLS-2025-2026';
const response = await fetch(`/api/tutor/chat?course_id=${courseId}`, {
  method: 'POST',
  body: JSON.stringify({
    message: 'Explain Art. 6:74 DCC',
    context: 'Private Law'
  })
});

// Check if course-aware mode was used
const data = await response.json();
if (data.course_id) {
  console.log('Course-aware response:', data.course_id);
}
```

### For Backend Developers

**No changes required** for existing integrations.

**To leverage course-aware features:**

```python
from app.services.files_api_service import get_files_api_service

service = get_files_api_service()

# Get course topics
topics = service.get_course_topics('LLS-2025-2026')

# Get course materials
materials = service.get_topic_files_for_course(
    course_id='LLS-2025-2026',
    week_numbers=[1, 2, 3]
)
```

---

## Performance Considerations

### Optimizations

1. **Single Firestore Read**
   - `get_course(course_id, include_weeks=True)` fetches all data at once
   - Reduces Firestore read operations
   - Improves response time

2. **Lazy Loading**
   - CourseService is lazy-loaded to avoid circular imports
   - Services are singletons (cached)

3. **Fallback Strategy**
   - Quick fallback to defaults on errors
   - No blocking on Firestore unavailability

### Caching Recommendations

Consider implementing caching for:
- Course topics (TTL: 1 hour)
- Course info (TTL: 1 hour)
- Default topics (permanent)

---

## Error Handling

### Error Scenarios

1. **Course Not Found**
   - Returns 404 with clear error message
   - Falls back to defaults for non-critical endpoints

2. **Firestore Unavailable**
   - Logs warning
   - Falls back to default topics
   - Continues operation

3. **Invalid Course ID**
   - Returns 404 for course-info endpoint
   - Falls back to defaults for other endpoints

### Example Error Response

```json
{
  "detail": "Course not found: INVALID-ID"
}
```

---

## Future Enhancements

### Potential Improvements

1. **Material-Aware Chat**
   - Include specific materials in AI context
   - Reference course materials in responses

2. **Week-Specific Context**
   - Filter topics by week number
   - Provide week-specific examples

3. **Skill Framework Integration**
   - Include legal skills in context
   - Provide skill-specific guidance

4. **Caching Layer**
   - Cache course topics and info
   - Reduce Firestore reads

---

## Summary

The AI Tutor enhancements successfully integrate with the new multi-course architecture while maintaining full backward compatibility. The system now supports:

✅ Course-aware chat with enhanced context  
✅ Course-specific topics from Firestore  
✅ Course-specific examples generation  
✅ Comprehensive course information endpoint  
✅ Full backward compatibility with legacy mode  
✅ Comprehensive test coverage (18 tests)  
✅ Graceful error handling and fallbacks  

**No breaking changes** - all existing integrations continue to work seamlessly.

