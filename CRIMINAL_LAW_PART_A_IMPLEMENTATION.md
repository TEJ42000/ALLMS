# Criminal Law Part A Implementation
# Feature: Part A/B Selector for Criminal Law Course

**Date:** 2026-01-10  
**PR:** feature/criminal-law-part-a  
**Course:** CRIM-2025-2026  
**Status:** ✅ **COMPLETE**

---

## Executive Summary

Successfully implemented Criminal Law course (CRIM-2025-2026) with Part A (Substantive Criminal Law) and Part B (Criminal Procedure & Human Rights) structure. Added a Part A/B/Mixed selector to the UI allowing students to study each part separately or practice both together.

---

## Implementation Overview

### Course Structure

**Course ID:** CRIM-2025-2026  
**Total Points:** 40 (20 for Part A + 20 for Part B)  
**Total Weeks:** 12 (6 weeks Part A + 6 weeks Part B)

**Components:**
1. **Part A: Substantive Criminal Law** (20 points)
   - Foundations, offense structure, mens rea, defenses, inchoate offenses, participation

2. **Part B: Criminal Procedure & Human Rights** (20 points)
   - ECHR, fair trial rights, evidence, procedural safeguards

---

## Part A Content (Weeks 1-6)

### Week 1: Foundations of Criminal Law

**Topics:**
- Legality principle (nullum crimen sine lege)
- Lex praevia (no retroactive laws)
- Lex certa (legal certainty)
- Lex stricta (strict interpretation)
- Lex scripta (written law)
- Theories of punishment: retribution, deterrence, rehabilitation

**Key Concepts:**
- Legality Principle: No crime, no punishment without law
- Lex Praevia: Laws must exist before the act
- Retribution: Punishment as deserved suffering

**Key Frameworks:**
- Four aspects of legality principle
- Four theories of punishment

**Exam Tips:**
- Always check if legality principle is violated
- Distinguish between general and specific deterrence
- Know which theory Dutch law primarily follows

---

### Week 2: Offense Structure & Actus Reus

**Topics:**
- Tripartite framework (3 stages)
- Actus reus (guilty act)
- Voluntary act requirement
- Omissions liability
- Legal duty to act
- Causation: but-for test
- Causation: 8 attribution factors
- Intervening causes

**Key Concepts:**
- Tripartite Framework: (1) Actus reus, (2) Mens rea, (3) Absence of defenses
- Actus Reus: The guilty act - must be voluntary
- But-For Test: Factual causation test

**Key Frameworks:**
- Tripartite framework (3 stages)
- 8 attribution factors for legal causation
- Requirements for omissions liability

**Exam Tips:**
- Always apply tripartite framework systematically
- Check both factual (but-for) and legal causation
- Omissions require a legal duty to act

---

### Week 3: Mens Rea & Mental States

**Topics:**
- Mens rea (guilty mind)
- Dolus directus (direct intent)
- Dolus indirectus (indirect intent)
- Dolus eventualis (conditional intent)
- Negligence: objective standard
- Negligence: 2-stage test
- Strict liability offenses
- Transferred malice

**Key Concepts:**
- Dolus Directus: Direct intent - purpose to bring about result
- Dolus Eventualis: Conditional intent - foresees and accepts result
- Negligence: Failure to meet reasonable person standard (2-stage test)

**Key Frameworks:**
- Hierarchy of mens rea (dolus directus > indirectus > eventualis > negligence)
- 2-stage test for negligence
- Dolus eventualis test (foresight + acceptance)

**Exam Tips:**
- Distinguish dolus eventualis from negligence - key is acceptance
- Apply 2-stage negligence test systematically
- Check if offense requires specific mens rea

---

### Week 4: Defenses: Justifications & Excuses

**Topics:**
- Justifications vs excuses
- Self-defense (noodweer)
- 7 requirements for self-defense
- Proportionality in self-defense
- Necessity (noodtoestand)
- Duress (overmacht)
- Insanity defense
- Diminished responsibility

**Key Concepts:**
- Justification: Makes act lawful (e.g., self-defense)
- Excuse: Excuses the actor (e.g., insanity)
- Self-Defense: Justified force against unlawful attack (7 requirements)

**Key Frameworks:**
- 7 requirements for self-defense
- Justification vs excuse distinction
- Proportionality assessment

**Exam Tips:**
- Always check all 7 requirements for self-defense
- Distinguish necessity (justification) from duress (excuse)
- Proportionality is key - excessive force defeats self-defense

---

### Week 5: Inchoate Offenses & Attempt

**Topics:**
- Attempt (poging)
- Subjectivist approach to attempt
- Objectivist approach to attempt
- Factual impossibility
- Legal impossibility
- Voluntary withdrawal
- Preparation vs attempt
- Abandonment

**Key Concepts:**
- Attempt: Trying to commit crime but failing (requires intent + substantial step)
- Factual Impossibility: Attempt fails due to facts (not a defense)
- Voluntary Withdrawal: Voluntary abandonment before completion

**Key Frameworks:**
- Subjectivist vs objectivist approaches
- Factual vs legal impossibility
- Requirements for voluntary withdrawal

**Exam Tips:**
- Distinguish preparation from attempt - look for substantial step
- Factual impossibility is NOT a defense
- Voluntary withdrawal must be truly voluntary

---

### Week 6: Participation & Complicity

**Topics:**
- Derivative liability
- Perpetration by means
- Instigation (uitlokking)
- Aiding and abetting (medeplichtigheid)
- Co-perpetration (medeplegen)
- Corporate criminal liability
- Vicarious liability
- Withdrawal from participation

**Key Concepts:**
- Derivative Liability: Accomplice's liability derives from principal's crime
- Co-Perpetration: Joint commission with shared intent (all are principals)
- Aiding and Abetting: Intentionally helping another (lesser liability)

**Key Frameworks:**
- Forms of participation (perpetrator, co-perpetrator, instigator, aider)
- Requirements for co-perpetration
- Corporate liability requirements

**Exam Tips:**
- Distinguish co-perpetration (equal) from aiding (lesser liability)
- Check accomplice has required mens rea
- Corporate liability requires act by natural person + attribution

---

## Part B Content (Weeks 7-12)

### Week 7: ECHR & Fair Trial Rights

**Topics:**
- ECHR Article 6 (fair trial)
- Engel criteria (3-part test)
- Autonomous interpretation
- Criminal charge definition
- Presumption of innocence
- Right to be informed
- Adequate time and facilities
- Legal assistance

**Key Concepts:**
- Engel Criteria: 3-part test for "criminal" proceedings
- Autonomous Interpretation: ECHR terms have independent meaning

**Key Frameworks:**
- Engel criteria (3-part test)
- Article 6 fair trial components

**Exam Tips:**
- Apply all 3 Engel criteria - any one can be sufficient
- Remember autonomous interpretation - domestic label not decisive

### Weeks 8-12: Criminal Procedure Topics

*Placeholder for future detailed content on Salduz, evidence, impartiality, Al-Khawaja test, etc.*

---

## UI Implementation

### Part Selector

**Location:** Weekly Content Section (below section description)

**Tabs:**
1. **Part A** (📖) - Substantive Criminal Law
2. **Part B** (⚖️) - Criminal Procedure & Human Rights
3. **Mixed** (🔀) - Combined practice (all weeks)

**Behavior:**
- Default: Part A selected
- Clicking a tab filters weeks to show only that part
- Mixed mode shows all weeks from both parts
- Active tab highlighted with gold gradient
- Smooth transitions between parts

**Responsive:**
- Mobile: Tabs stack vertically with smaller padding
- Desktop: Tabs display horizontally centered

---

## Files Created

### 1. `scripts/setup_criminal_law_course.py`

**Purpose:** Create Criminal Law course in Firestore with Part A and Part B structure

**Functions:**
- `create_criminal_law_course()` - Main setup function
- `create_part_a_weeks()` - Create Part A weeks 1-6
- `create_part_b_weeks()` - Create Part B weeks 7-12

**Usage:**
```bash
python scripts/setup_criminal_law_course.py
```

**Output:**
```
======================================================================
🎓 Setting up Criminal Law Course (CRIM-2025-2026)
======================================================================

✅ Created course: CRIM-2025-2026
   Name: Criminal Law
   Components: Part A (20 pts) + Part B (20 pts)

📚 Creating Part A weeks (Substantive Criminal Law)...
   ✅ Created 6 Part A weeks

📚 Creating Part B weeks (Criminal Procedure & Human Rights)...
   ✅ Created 6 Part B weeks

======================================================================
✅ Criminal Law course setup complete!
======================================================================

Course ID: CRIM-2025-2026
Total weeks: 12
Part A weeks: 6
Part B weeks: 6
```

---

## Files Modified

### 1. `templates/index.html`

**Changes:**
- Added Part Selector HTML structure
- Added part tabs (Part A, Part B, Mixed)
- Positioned above week grid

**Lines:** 181-200

---

### 2. `app/static/css/styles.css`

**Changes:**
- Added `.part-selector` styles
- Added `.part-tabs` flex layout
- Added `.part-tab` button styles
- Added hover and active states
- Added emoji icons for each part
- Added responsive styles for mobile

**Lines:** 4129-4178

---

### 3. `app/static/js/weeks.js`

**Changes:**
- Added `currentPart` property (default: 'A')
- Added `allWeeks` array to store all weeks
- Added `partSelector` reference
- Added `initPartSelector()` method
- Added `filterWeeksByPart()` method
- Modified `loadWeeks()` to detect parts and initialize selector
- Modified `createWeekCard()` to show part in week label

**Key Methods:**

```javascript
initPartSelector() {
    // Show part selector
    // Add click handlers to tabs
    // Update active state on click
    // Filter weeks by selected part
}

filterWeeksByPart() {
    // Filter weeks by currentPart
    // Show all weeks if 'mixed'
    // Re-render filtered weeks
}
```

---

## Firestore Structure

### Course Document

```
courses/
  CRIM-2025-2026/
    id: "CRIM-2025-2026"
    name: "Criminal Law"
    program: "LLB Law"
    institution: "Maastricht University"
    academicYear: "2025-2026"
    totalPoints: 40
    passingThreshold: 22
    components: [
      {
        id: "A",
        name: "Substantive Criminal Law",
        maxPoints: 20,
        description: "Foundations, offense structure, mens rea..."
      },
      {
        id: "B",
        name: "Criminal Procedure & Human Rights",
        maxPoints: 20,
        description: "ECHR, fair trial rights, evidence..."
      }
    ]
    materialSubjects: ["Criminal_Law"]
    abbreviations: {
      Sr: "Wetboek van Strafrecht",
      Sv: "Wetboek van Strafvordering",
      ECHR: "European Convention on Human Rights",
      ECtHR: "European Court of Human Rights"
    }
    active: true
    weekCount: 12
```

### Week Documents

```
courses/
  CRIM-2025-2026/
    weeks/
      week-1/
        weekNumber: 1
        part: "A"
        title: "Foundations of Criminal Law"
        topicDescription: "Introduction to criminal law principles..."
        topics: [...]
        materials: []
        keyConcepts: [...]
        keyFrameworks: [...]
        examTips: [...]
      
      week-7/
        weekNumber: 7
        part: "B"
        title: "ECHR & Fair Trial Rights"
        topicDescription: "Introduction to ECHR..."
        topics: [...]
        materials: []
        keyConcepts: [...]
        keyFrameworks: [...]
        examTips: [...]
```

---

## Testing

### Manual Testing Checklist

- [x] Course created in Firestore
- [x] 12 weeks created (6 Part A + 6 Part B)
- [x] Part selector appears in UI
- [x] Part A tab shows weeks 1-6
- [x] Part B tab shows weeks 7-12
- [x] Mixed tab shows all 12 weeks
- [x] Week cards show part label
- [x] Active tab highlighted correctly
- [x] Smooth transitions between parts
- [x] Responsive on mobile

---

## Next Steps

### Immediate
1. ✅ Run `python scripts/setup_criminal_law_course.py`
2. ✅ Verify course in Firestore
3. ✅ Test Part A/B selector in UI
4. ⏳ Add materials for Criminal Law course
5. ⏳ Test study guide generation for each part

### Future Enhancements
1. Add detailed Part B content (weeks 8-12)
2. Add practice questions for each week
3. Add flashcards for key concepts
4. Add mock exam with mixed Part A/B questions
5. Add progress tracking per part

---

**Status:** ✅ **COMPLETE**  
**Course:** CRIM-2025-2026 created with 12 weeks  
**UI:** Part A/B/Mixed selector implemented  
**Ready for:** Materials upload and testing

