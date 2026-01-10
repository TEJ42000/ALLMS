# Essay Assessment Comprehensive Practice Options
# Feature: All Weeks (Mixed) and Part A/B Grouped Options

**Date:** 2026-01-10  
**Branch:** feature/criminal-law-part-a  
**Status:** ✅ **COMPLETE**

---

## Executive Summary

Added comprehensive practice options to the Essay Assessment topic selector, allowing students to generate essay questions that draw from multiple weeks/topics. This enables realistic exam preparation with questions that integrate knowledge across the entire course or specific parts.

---

## Feature Overview

### New Options in Essay Topic Selector

**Before:**
- Only individual week topics (Week 1, Week 2, ..., Week 12)
- No way to practice comprehensive questions

**After:**
- **📚 Comprehensive Practice** (optgroup)
  - **All Weeks (Mixed)** - Entire course
  - **Part A (Weeks 1-6)** - Substantive Criminal Law
  - **Part B (Weeks 7-12)** - Criminal Procedure
- **📅 Individual Weeks** (optgroup)
  - Week 1-12 individual topics

---

## Comprehensive Practice Options

### 1. All Weeks (Mixed) - Entire Course

**Value:** `all-weeks`

**Description:** Generate comprehensive essay questions that draw from ANY content across the entire Criminal Law course (both Part A and Part B).

**Use Case:**
- Final exam preparation
- Testing connections between substantive and procedural law
- Comprehensive understanding assessment
- Realistic exam practice (exams often mix topics)

**Example Questions:**
- "Analyze a scenario involving both mens rea issues (Part A) and fair trial rights (Part B)"
- "Compare the role of intent in substantive criminal law with the presumption of innocence in criminal procedure"
- "Apply the tripartite framework and ECHR Article 6 to evaluate a complex criminal case"

---

### 2. Part A (Weeks 1-6) - Substantive Criminal Law

**Value:** `part-a`

**Description:** Generate essay questions focused on Part A topics, potentially integrating multiple substantive law concepts.

**Topics Covered:**
- Week 1: Foundations (legality principle, theories of punishment)
- Week 2: Offense Structure (tripartite framework, actus reus, causation)
- Week 3: Mens Rea (dolus directus/indirectus/eventualis, negligence)
- Week 4: Defenses (justifications vs excuses, self-defense, necessity)
- Week 5: Inchoate Offenses (attempt, impossibility, withdrawal)
- Week 6: Participation (derivative liability, co-perpetration, aiding)

**Use Case:**
- Part A exam preparation
- Focused practice on substantive law
- Integration of multiple substantive concepts
- Understanding connections within Part A

**Example Questions:**
- "Analyze a scenario involving both mens rea and defenses"
- "Compare dolus eventualis with voluntary withdrawal from attempt"
- "Apply the tripartite framework to a case involving co-perpetration and self-defense"

---

### 3. Part B (Weeks 7-12) - Criminal Procedure

**Value:** `part-b`

**Description:** Generate essay questions focused on Part B topics, potentially integrating multiple procedural law concepts.

**Topics Covered:**
- Week 7: ECHR & Fair Trial Rights (Engel criteria, autonomous interpretation)
- Weeks 8-12: Criminal procedure topics (Salduz, evidence, impartiality, etc.)

**Use Case:**
- Part B exam preparation
- Focused practice on procedural law
- Integration of multiple procedural concepts
- Understanding connections within Part B

**Example Questions:**
- "Analyze a scenario involving both Salduz rights and evidence admissibility"
- "Compare the Engel criteria with the Al-Khawaja test"
- "Apply ECHR Article 6 to evaluate procedural fairness in a complex case"

---

## Implementation Details

### Frontend Changes

**File:** `templates/index.html`

**Changes:**
```html
<select id="essay-topic-select" class="form-select">
    <!-- Comprehensive Practice Options -->
    <optgroup label="📚 Comprehensive Practice">
        <option value="all-weeks">All Weeks (Mixed) - Entire Course</option>
        <option value="part-a">Part A (Weeks 1-6) - Substantive Criminal Law</option>
        <option value="part-b">Part B (Weeks 7-12) - Criminal Procedure</option>
    </optgroup>
    
    <!-- Individual Week Topics -->
    <optgroup label="📅 Individual Weeks">
        {% for topic in topics %}
        <option value="{{ topic.name }}">Week {{ topic.weekNumber }}: {{ topic.name }}</option>
        {% endfor %}
    </optgroup>
</select>
```

**Benefits:**
- Clear visual hierarchy with optgroups
- Emoji icons for quick recognition
- Grouped organization (comprehensive vs individual)
- Better UX for topic selection

---

### Backend Changes

**File:** `app/services/anthropic_client.py`

**Function:** `generate_essay_question()`

**Changes:**

```python
async def generate_essay_question(
    topic: str,
    course_context: Optional[str] = None,
    user_context: Optional[UserContext] = None,
) -> Dict:
    # Handle special topic values for comprehensive practice
    if topic == "all-weeks":
        user_message = """Generate a comprehensive essay question that draws from ANY content across the entire Criminal Law course (both Part A: Substantive Criminal Law and Part B: Criminal Procedure).

The question should:
- Integrate concepts from multiple weeks
- Test understanding of connections between different topics
- Be suitable for comprehensive exam practice
- Challenge students to synthesize knowledge from the full course"""
    
    elif topic == "part-a":
        user_message = """Generate an essay question focused on Part A: Substantive Criminal Law (Weeks 1-6).

The question should cover topics from:
- Week 1: Foundations (legality principle, theories of punishment)
- Week 2: Offense Structure (tripartite framework, actus reus, causation)
- Week 3: Mens Rea (dolus directus/indirectus/eventualis, negligence)
- Week 4: Defenses (justifications vs excuses, self-defense, necessity)
- Week 5: Inchoate Offenses (attempt, impossibility, withdrawal)
- Week 6: Participation (derivative liability, co-perpetration, aiding)

The question may integrate multiple topics from Part A."""
    
    elif topic == "part-b":
        user_message = """Generate an essay question focused on Part B: Criminal Procedure & Human Rights (Weeks 7-12).

The question should cover topics from:
- Week 7: ECHR & Fair Trial Rights (Engel criteria, autonomous interpretation)
- Weeks 8-12: Criminal procedure topics (Salduz, evidence, impartiality, etc.)

The question may integrate multiple topics from Part B."""
    
    else:
        # Standard single-topic question
        user_message = f"Generate an essay question for the topic: {topic}"
```

**Benefits:**
- Explicit instructions for comprehensive questions
- AI understands to integrate multiple topics
- Realistic exam-style questions
- Flexible question generation

---

### System Prompt Updates

**File:** `app/services/anthropic_client.py`

**Constant:** `ESSAY_QUESTION_SYSTEM_PROMPT`

**Changes:**
- Updated to mention Criminal Law course (CRIM-2025-2026)
- Added guidance for comprehensive questions
- Emphasized integration of multiple topics
- Added "Comprehensive" question type

**Key Addition:**
```
FOR COMPREHENSIVE QUESTIONS:
- Draw from multiple weeks/topics
- Test connections between different concepts
- Create realistic scenarios that require synthesizing knowledge
- Challenge students to apply multiple frameworks/tests
```

---

### CSS Styling

**File:** `app/static/css/styles.css`

**Changes:**
```css
/* Optgroup styling for essay topic selector */
.form-select optgroup {
    font-weight: 700;
    font-style: normal;
    color: var(--gold);
    background: rgba(212, 175, 55, 0.1);
    padding: 8px 0;
}

.form-select option {
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.3);
    color: var(--text-primary);
}

.form-select option:hover {
    background: rgba(212, 175, 55, 0.2);
}
```

**Benefits:**
- Gold-colored optgroup labels (matches theme)
- Clear visual separation between groups
- Better hover states for options
- Improved readability

---

## User Experience

### Workflow

1. **Navigate to Assessment Section**
   - Click "Assessment" tab in navigation

2. **Select Comprehensive Practice Option**
   - Open "Select Topic" dropdown
   - See two optgroups:
     - 📚 Comprehensive Practice
     - 📅 Individual Weeks

3. **Choose Practice Mode**
   - **All Weeks (Mixed):** For final exam prep
   - **Part A (Weeks 1-6):** For Part A exam prep
   - **Part B (Weeks 7-12):** For Part B exam prep
   - **Individual Week:** For focused topic practice

4. **Generate Question**
   - Click "Generate Question"
   - AI generates appropriate question based on selection
   - For comprehensive options, question integrates multiple topics

5. **Write Answer**
   - Answer the essay question (3-7 paragraphs)
   - Submit for AI evaluation

6. **Receive Feedback**
   - Get grade (1-10) and detailed feedback
   - Review strengths and areas for improvement

---

## Benefits

### For Students

✅ **Realistic Exam Practice**
- Exams often mix topics from multiple weeks
- Comprehensive questions prepare for real exam format
- Practice synthesizing knowledge

✅ **Flexible Study Modes**
- Full course practice (all-weeks)
- Part-specific practice (part-a, part-b)
- Topic-specific practice (individual weeks)

✅ **Better Exam Preparation**
- Test understanding of connections between topics
- Identify gaps in comprehensive knowledge
- Build confidence for final exams

✅ **Progressive Learning**
- Start with individual topics
- Progress to part-specific practice
- Culminate with full course practice

---

### For Instructors

✅ **Comprehensive Assessment**
- Test integration of knowledge
- Evaluate synthesis skills
- Assess connections between topics

✅ **Realistic Question Generation**
- AI generates exam-style questions
- Questions integrate multiple concepts
- Suitable for final exam preparation

---

## Testing

### Manual Testing Checklist

- [x] Dropdown shows optgroups correctly
- [x] "All Weeks (Mixed)" option appears first
- [x] Part A and Part B options appear
- [x] Individual weeks grouped separately
- [x] Selecting "all-weeks" generates comprehensive question
- [x] Selecting "part-a" generates Part A question
- [x] Selecting "part-b" generates Part B question
- [x] Individual week selection still works
- [x] CSS styling applied correctly
- [x] Optgroups visually distinct
- [x] No JavaScript errors

---

## Future Enhancements

### Potential Improvements

1. **Custom Topic Combinations**
   - Allow students to select specific weeks to combine
   - E.g., "Weeks 2, 3, and 5 only"

2. **Difficulty Levels**
   - Easy: Single topic
   - Medium: 2-3 topics
   - Hard: 4+ topics or full course

3. **Question Type Selection**
   - Case analysis
   - Comparative
   - Application
   - Critical analysis
   - Problem questions

4. **Saved Practice Sets**
   - Save favorite topic combinations
   - Track progress on comprehensive practice
   - Review past comprehensive questions

---

## Files Changed

**Modified (3 files, +74 lines):**
1. `templates/index.html` (+12 lines)
   - Added optgroups to essay topic selector
   - Added comprehensive practice options

2. `app/services/anthropic_client.py` (+49 lines)
   - Updated `generate_essay_question()` to handle special values
   - Enhanced system prompt for comprehensive questions

3. `app/static/css/styles.css` (+13 lines)
   - Added optgroup styling
   - Improved option hover states

**Total:** +74 lines added

---

## Related Features

- **Part A/B Selector in Weekly Content:** Complements this feature
- **Criminal Law Course Structure:** Enables part-specific practice
- **Essay Assessment System:** Core feature being enhanced

---

**Status:** ✅ **COMPLETE**  
**Ready for:** Testing and deployment  
**Complements:** PR #262 (Criminal Law Part A implementation)

