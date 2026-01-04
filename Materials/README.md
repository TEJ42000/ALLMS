# Materials Directory - Three-Tier Organization System

This directory contains all course materials organized using a **three-tier system** that clearly separates materials by their authority level and purpose.

## 📚 Directory Structure

```
Materials/
├── Syllabus/                      # Tier 1: Official Course Syllabi
├── Course_Materials/              # Tier 2: Primary Learning Materials
└── Supplementary_Sources/         # Tier 3: External & Supplementary Materials
```

---

## 🎯 Tier 1: Syllabus/

**Purpose:** Official course syllabi and foundational documents

**Authority Level:** ⭐⭐⭐ Highest (Official university-provided content)

**Contents:**
- Official course syllabi provided directly by professors
- Course objectives and learning outcomes
- Assessment criteria and exam information
- Grading rubrics and course policies
- Core building blocks that define course context

**Structure:**
```
Syllabus/
├── Criminal_Law/
│   ├── Part_A_Syllabus_2025-2026.docx
│   ├── Part_B_Syllabus_2025-2026.pdf
│   └── Course_Outline.pdf
├── Administrative_Law/
└── International_Law/
```

**When to use:**
- Understanding course requirements and objectives
- Checking exam format and assessment criteria
- Verifying official course policies
- AI system prioritizes these files for authoritative answers

---

## 📖 Tier 2: Course_Materials/

**Purpose:** Primary learning materials and student resources

**Authority Level:** ⭐⭐ Medium (Mix of official and student-compiled content)

**Contents:**
- Official university-provided content (PDFs, PowerPoints, lecture slides)
- Student-compiled study materials and notes
- Third-party student resources (study guides, summaries)
- Working group materials and practice questions
- Lecture transcripts and recordings
- Organized by subject/course and week where applicable

**Structure:**
```
Course_Materials/
├── Criminal_Law/
│   ├── Part_A_Substantive/
│   │   ├── Week_01/
│   │   ├── Week_02/
│   │   └── Lecture_Slides/
│   ├── Part_B_Procedural/
│   │   ├── Week_01/
│   │   └── Lecture_Slides/
│   ├── Working_Groups/
│   ├── Study_Notes/
│   ├── Study_Guides/
│   └── Exam_Materials/
├── Administrative_Law/
└── International_Law/
```

**When to use:**
- Daily study and exam preparation
- Understanding lecture content
- Practice questions and working group exercises
- Creating study summaries
- Most frequently accessed materials

---

## 🌐 Tier 3: Supplementary_Sources/

**Purpose:** External and supplementary reference materials

**Authority Level:** ⭐ Lower (External resources for additional context)

**Contents:**
- External websites and online resources
- Additional explanatory materials when core content is insufficient
- Reference materials and case law databases
- Links to external legal databases (EUR-Lex, HUDOC, etc.)
- Third-party study aids and commercial outlines
- Comparative law resources

**Structure:**
```
Supplementary_Sources/
├── Case_Law/
│   ├── ECHR/
│   ├── CJEU/
│   └── National_Courts/
├── External_Links.md
├── Legal_Databases.md
└── Additional_Reading/
```

**When to use:**
- Deep diving into specific case law
- Finding additional explanations for complex topics
- Accessing external legal databases
- Comparative law research
- When core materials need supplementation

---

## 🤖 AI System Integration

The three-tier system enables the AI tutor to prioritize sources appropriately:

1. **Tier 1 (Syllabus)** - Highest priority for course requirements and official policies
2. **Tier 2 (Course_Materials)** - Primary source for content generation and study materials
3. **Tier 3 (Supplementary_Sources)** - Used for additional context and case law references

When generating content (quizzes, study guides, flashcards), the AI system:
- Prioritizes Tier 1 files for authoritative information
- Uses Tier 2 files as the main content source
- References Tier 3 files for supplementary examples and case law

---

## 📤 Uploading Materials

To upload materials to the Anthropic Files API:

```bash
python scripts/upload_files_script.py
```

This script:
- Automatically discovers all files in the three-tier structure
- Uploads them to Anthropic's Files API
- Generates `file_ids.json` with tier metadata
- Enables tier-based prioritization in the AI system

**Supported file types:** `.pdf`, `.docx`, `.md`, `.txt`

---

## ➕ Adding New Materials

### Adding to Tier 1 (Syllabus)
1. Place official syllabus files in `Syllabus/[Subject]/`
2. Use descriptive names: `[Subject]_Syllabus_[Year].pdf`
3. Run upload script to make available to AI system

### Adding to Tier 2 (Course_Materials)
1. Organize by subject: `Course_Materials/[Subject]/`
2. Use subcategories: `Part_A_Substantive/`, `Study_Notes/`, etc.
3. Consider organizing by week if applicable
4. Run upload script after adding files

### Adding to Tier 3 (Supplementary_Sources)
1. Place in appropriate category: `Case_Law/`, `Additional_Reading/`, etc.
2. Organize by source type (ECHR, CJEU, etc.)
3. Consider creating index files for external links
4. Run upload script to include in AI system

---

## 📋 Best Practices

### File Naming
- Use descriptive names: `Criminal_Law_Part_A_Week_3_Lecture.pdf`
- Avoid special characters: use underscores instead of spaces
- Include year/semester when relevant: `Syllabus_2025-2026.pdf`
- Be consistent within each tier

### Organization
- Keep related materials together in the same subdirectory
- Use week-based organization for lecture materials
- Separate official content from student notes
- Create README files in subdirectories for complex structures

### Maintenance
- Regularly update materials at the start of each semester
- Archive old materials rather than deleting them
- Run upload script after significant changes
- Verify file_ids.json is updated correctly

---

## 🔍 Finding Materials

### By Subject
All materials for a subject are grouped together:
- `Syllabus/Criminal_Law/` - Official syllabi
- `Course_Materials/Criminal_Law/` - All course materials
- `Supplementary_Sources/Case_Law/` - Related case law

### By Type
Materials are organized by type within each subject:
- Lecture slides → `Course_Materials/[Subject]/Part_A_Substantive/`
- Study notes → `Course_Materials/[Subject]/Study_Notes/`
- Working groups → `Course_Materials/[Subject]/Working_Groups/`
- Exam materials → `Course_Materials/[Subject]/Exam_Materials/`

### By Week
Week-specific materials are in weekly subdirectories:
- `Course_Materials/Criminal_Law/Part_A_Substantive/Week_01/`
- `Course_Materials/Criminal_Law/Part_B_Procedural/Week_02/`

---

## 📊 Benefits of This Structure

### For Students
- **Clear hierarchy** - Easy to understand which materials are authoritative
- **Better navigation** - Logical organization by content type and purpose
- **Faster access** - Quickly locate the right type of resource

### For Developers
- **Maintainability** - Clear structure makes adding new materials straightforward
- **Scalability** - Easy to add new courses without restructuring
- **AI prioritization** - System can prioritize Tier 1 over Tier 3

### For the AI System
- **Source authority** - Can weight responses based on material tier
- **Better context** - Understands relationship between different material types
- **Improved accuracy** - Prioritizes official course content over supplementary materials

---

## 📞 Support

For questions about the materials structure:
- Check the README in each tier directory
- Review `FILE_INDEX.md` in Study_Guides for detailed file listings
- Contact course administrators for official materials

---

**Last Updated:** January 2026
**Structure Version:** 1.0 (Three-Tier System)

