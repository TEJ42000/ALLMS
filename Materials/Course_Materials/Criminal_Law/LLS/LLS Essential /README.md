# Law and Legal Skills (LLS) Course Materials
## International and European Law - University of Groningen (2025-2026)

---

## 📁 Repository Overview

This repository contains all course materials, study resources, and structured data for developing a comprehensive legal education application for the Law and Legal Skills (LLS) course.

**Total Size**: ~71MB  
**Academic Year**: 2025-2026  
**Institution**: University of Groningen  
**Program**: International and European Law (Bachelor's)

---

## 🚀 Quick Start for App Developers

### 1. **Read First**
- `COURSE_STRUCTURE_AND_APP_DEV_GUIDE.md` - Comprehensive development guide
- `course_data.json` - Structured JSON data for direct integration

### 2. **Understand the Structure**
```
LLS_Course_Materials/
├── Core_Materials/          # Primary textbooks (21MB)
├── Lectures/                # Weekly lecture materials (20MB)
├── Weekly_Readings/         # Assigned readings (24MB)
├── Case_Law/                # Legal case studies (5MB)
├── Mock_Exams/              # Practice exams + answers (1.3MB)
├── Study_Tools/             # Interactive study portal (270KB)
├── Skills_Reviews/          # Assessment materials (74KB)
├── COURSE_STRUCTURE_AND_APP_DEV_GUIDE.md
├── course_data.json
└── README.md (this file)
```

### 3. **Key Files for Integration**

#### Structured Data
- **course_data.json**: Complete course structure, decision models, concepts, citations
  - Import directly into your database
  - Contains all metadata for 6 weeks of content
  - Includes legal skills frameworks

#### Interactive Resources
- **Study_Tools/lls-study-portal-FINAL-WORKING.html**: Existing study portal
  - Can be embedded or adapted for your app
  - Contains quiz functionality and progress tracking

#### Primary Content Sources
- **Core_Materials/LLSReaderwithcoursecontentandquestions_20252026.pdf**: Official textbook
- **Core_Materials/ELSA_NOTES_.pdf**: Comprehensive study notes

---

## 📚 Course Structure at a Glance

### Assessment
- **Part A (Law)**: 100 points - Substantive legal knowledge
- **Part B (Legal Skills)**: 100 points - Legal analysis and research
- **Passing Threshold**: 110/200 points

### Weekly Topics
1. **Week 1**: Dutch Legal Systems & Constitutional Law
2. **Week 2**: Administrative Law (GALA framework)
3. **Week 3**: Criminal Law (8-question decision model)
4. **Week 4**: Private Law - Contract & Tort Law
5. **Week 5**: European Union Law
6. **Week 6**: International Law

---

## 🔑 Critical Requirements for Legal Apps

### ⚠️ ANTI-HALLUCINATION PROTOCOL
**All legal information MUST:**
1. ✅ Cite specific source (article number, case name, page reference)
2. ✅ Come from legal academic sources ONLY
3. ✅ Include verification links where possible
4. ✅ Distinguish between law and commentary
5. ❌ NEVER make up legal information
6. ❌ NEVER cite Wikipedia or general sources for legal analysis

### Citation Formats
```
Dutch Legislation:   Article 6:162 BW
ECtHR Cases:        Osmanoğlu v. Switzerland, App. No. 29086/12
Academic Sources:   [Author], [Title], [Publication] [Year], p. [page]
```

### Source Hierarchy (Priority Order)
1. **Primary Sources**: Statutes, Case law, Treaties (binding)
2. **Secondary Sources**: Textbooks, Law reviews (persuasive)
3. **Tertiary Sources**: Study guides (informational)

---

## 🎯 Key Features to Implement

### Essential Features
- [ ] **Source Citation Tracking**: Link every answer to authoritative source
- [ ] **Decision Model Workflows**: Guided legal analysis frameworks
  - Criminal Law 8-Question Model
  - Administrative Appeals Process
  - ECtHR Case Analysis 5-Question Framework
- [ ] **Progress Tracking**: Monitor completion by week/topic
- [ ] **Full-Text Search**: Across all materials with filters
- [ ] **Quiz Engine**: Practice questions with explanations

### Advanced Features
- [ ] **AI Tutor**: Question answering with mandatory citations
- [ ] **Flashcard System**: Spaced repetition for concepts
- [ ] **Offline Access**: Download materials for offline study
- [ ] **Collaboration Tools**: Study groups and shared notes

---

## 📊 Data Structures

### Course Schema
```json
{
  "course": {
    "id": "LLS-2025-2026",
    "totalPoints": 200,
    "passingThreshold": 110,
    "components": [...]
  },
  "weeks": [...],
  "legalSkills": {...},
  "materials": {...}
}
```

### Quiz Question Schema
```json
{
  "questionId": "unique-id",
  "topic": "administrative-law",
  "question": "...",
  "correctAnswer": "...",
  "sourceReference": {
    "document": "LLS Reader",
    "article": "Article 8:1 GALA"
  }
}
```

See `course_data.json` for complete structure.

---

## 🛠️ Technical Specifications

### File Handling
- **PDFs**: Use PDF.js or similar library for in-app viewing
- **HTML**: Can be embedded as iframe or adapted
- **Word Docs**: Convert to markdown/HTML for consistent display

### Performance
- **Total Size**: 71MB across 15 files
- **Optimization**: Implement lazy loading for large PDFs
- **Caching**: Cache frequently accessed materials locally
- **Search**: Pre-index content for fast queries

### Recommended Stack
```
Frontend:  React/Vue/Angular + TailwindCSS
Backend:   Node.js/Python + PostgreSQL/MongoDB
PDF:       PDF.js or react-pdf
Search:    ElasticSearch or Algolia
```

---

## 📖 Decision Models Reference

### 1. Criminal Law 8-Question Framework
```
1. What is X charged with?
2. What are the elements of the offense?
3. Has the actus reus been committed?
4. Was there mens rea?
5. Are there grounds for justification?
6. Are there grounds for excuse?
7. Can X be held criminally responsible?
8. What are procedural considerations?
```

### 2. Administrative Law Appeals
```
1. Is there a besluit (decision)?
2. Is appellant belanghebbende (interested party)?
3. Has bezwaar (objection) been filed? (6 weeks)
4. Has beroep (appeal) been filed? (6 weeks)
5. What is the standard of review?
```

### 3. ECtHR Case Analysis
```
1. Standing/Victim Status (Article 34 ECHR)
2. Jurisdiction (Article 1 ECHR)
3. Admissibility (exhaustion, 6-month rule, etc.)
4. Interference with Convention Right
5. Justification (prescribed by law, legitimate aim, necessary in democratic society)
```

**Critical Distinction**: Interference ≠ Violation

---

## 🔍 External Legal Databases

Integrate these for comprehensive legal research:

| Database | URL | Coverage |
|----------|-----|----------|
| EUR-Lex | https://eur-lex.europa.eu/ | EU law |
| HUDOC | https://hudoc.echr.coe.int/ | ECtHR cases |
| Rechtspraak.nl | https://www.rechtspraak.nl/ | Dutch courts |
| Wetten.nl | https://wetten.overheid.nl/ | Dutch legislation |

---

## 📝 Common Abbreviations

| Code | Full Name | Description |
|------|-----------|-------------|
| **BW** | Burgerlijk Wetboek | Dutch Civil Code |
| **Sr** | Wetboek van Strafrecht | Dutch Criminal Code |
| **GALA** | Algemene wet bestuursrecht | General Administrative Law Act |
| **ECHR** | European Convention on Human Rights | Human rights treaty |
| **ECtHR** | European Court of Human Rights | Strasbourg court |
| **TFEU** | Treaty on Functioning of EU | Primary EU law |
| **ICJ** | International Court of Justice | UN court |

---

## ✅ Quality Assurance Checklist

Before releasing any feature:
- [ ] All legal statements cite specific sources
- [ ] Citations include article/page numbers
- [ ] No conflation of different legal systems
- [ ] Clear distinction between law and commentary
- [ ] Accurate legal terminology
- [ ] No outdated information
- [ ] Tested with mock exam scenarios

---

## 📧 Support & Resources

### For Technical Issues
- Review `COURSE_STRUCTURE_AND_APP_DEV_GUIDE.md` for detailed guidance
- Check `course_data.json` for structured data
- Verify all sources in materials directories

### For Content Questions
**Remember**: 
- Prioritize legal academic sources over general knowledge
- Always cite authoritative sources
- Never hallucinate legal information
- When uncertain, flag for legal expert review

---

## 📄 License & Academic Integrity

**Purpose**: Educational study aid only  
**Usage**: All exam work must be student's own per university policies  
**Content**: Course materials © University of Groningen

---

## 🚧 Development Roadmap Suggestion

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up project structure
- [ ] Import course_data.json to database
- [ ] Implement PDF viewer
- [ ] Basic navigation and content display

### Phase 2: Core Features (Weeks 3-4)
- [ ] Quiz engine with source citations
- [ ] Decision model workflows
- [ ] Progress tracking
- [ ] Search functionality

### Phase 3: Advanced Features (Weeks 5-6)
- [ ] AI tutor with citation validation
- [ ] Flashcard system
- [ ] Collaboration tools
- [ ] Analytics dashboard

### Phase 4: Polish (Week 7)
- [ ] Offline mode
- [ ] Performance optimization
- [ ] User testing
- [ ] Documentation

---

## 📞 Quick Links

- **Main Guide**: `COURSE_STRUCTURE_AND_APP_DEV_GUIDE.md`
- **Structured Data**: `course_data.json`
- **Study Portal**: `Study_Tools/lls-study-portal-FINAL-WORKING.html`
- **Primary Textbook**: `Core_Materials/LLSReaderwithcoursecontentandquestions_20252026.pdf`

---

**Last Updated**: January 2026  
**Version**: Academic Year 2025-2026

---

*This repository supports development of a comprehensive legal education application while maintaining the highest standards of academic accuracy and proper legal citation.*
