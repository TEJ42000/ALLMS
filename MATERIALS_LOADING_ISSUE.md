# Materials Not Loading - Issue & Solution

**Date:** 2026-01-08  
**Issue:** Course materials not appearing for different weeks  
**Status:** ⚠️ IDENTIFIED - Needs Firestore population

---

## 🔍 Root Cause

### The Problem

**Materials exist locally but not in Firestore:**
- ✅ 94 materials found in local `Materials/` directory
- ❌ Materials NOT in Firestore `courses/{course_id}/materials` collection
- ❌ Website queries Firestore, finds nothing, shows empty

**Why this happened:**
- Materials are stored locally in `Materials/` directory
- System expects materials metadata in Firestore
- No automatic sync between local files and Firestore
- Materials need to be manually populated into Firestore

---

## 📊 What We Found

### Local Materials (94 files)

```
Criminal-Law---Part--2025-2026: 50 materials
  - Syllabus PDFs
  - Lecture slides
  - Working group materials
  - Study notes
  
LLS-2025-2026: 19 materials
  - Syllabus
  - Course materials
  - Study notes
  
Legal-History-2025-2026: 25 materials
  - Syllabus
  - Lecture notes
  - Study materials
```

### Firestore Status

**Current state:**
- `courses/{course_id}/materials` collection: EMPTY
- `courses/{course_id}/uploadedMaterials` collection: May have user uploads

**What's needed:**
- Populate `materials` collection with local file metadata
- Include: filename, storagePath, weekNumber, tier, category

---

## ✅ Solution

### Step 1: Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

**This is required to:**
- Access Firestore from local scripts
- Write materials metadata to Firestore

### Step 2: Run Population Script

```bash
cd /Users/matejmonteleone/PycharmProjects/LLMRMS
python scripts/populate_firestore_materials.py
```

**What this does:**
1. Scans `Materials/` directory
2. Discovers all PDFs, DOCX, TXT, MD, HTML files
3. Extracts metadata (filename, week, tier, category)
4. Creates Firestore documents in `courses/{course_id}/materials`
5. Materials appear in website immediately

### Step 3: Verify Materials Appear

1. Visit: https://lls-study-portal-sarfwmfd3q-ez.a.run.app
2. Select a course (Criminal Law, LLS, or Legal History)
3. Check different weeks
4. Materials should now appear

---

## 📋 Script Details

### What Gets Populated

**For each material:**
```json
{
  "id": "uuid",
  "filename": "Criminal_Law_Week_5.pdf",
  "title": "Criminal Law Week 5",
  "storagePath": "Course_Materials/Criminal_Law/Week_5/Criminal_Law_Week_5.pdf",
  "weekNumber": 5,
  "tier": "course_materials",
  "category": "Week_5",
  "source": "local",
  "uploadedAt": "2026-01-08T23:00:00Z",
  "textExtracted": false,
  "summaryGenerated": false
}
```

### Week Number Detection

**Script automatically detects week numbers from:**
- Filename: `Week_5_Lecture.pdf` → Week 5
- Directory: `Week_6/materials.pdf` → Week 6
- Default: Week 1 if no week found

### Tier Mapping

```
Syllabus/              → tier: "syllabus"
Course_Materials/      → tier: "course_materials"
Supplementary_Sources/ → tier: "supplementary"
```

---

## 🔧 Alternative: Manual Upload via UI

**If you don't want to run the script:**

1. Visit the website
2. Go to Upload tab
3. Upload each PDF manually
4. System will create Firestore entries automatically

**Pros:**
- No script needed
- No authentication needed
- Works immediately

**Cons:**
- Tedious (94 files to upload)
- Time-consuming (~30-60 minutes)
- Loses original directory structure

---

## 📊 Expected Results

### After Population

**Criminal Law course:**
- Week 1: Syllabus, course outline
- Week 4: Lecture slides, working group materials
- Week 5: Participation materials, working groups
- Week 6: Liability criteria, working groups
- Exam materials: Mock exams, practice questions

**LLS course:**
- Week 1: Syllabus, course structure
- Various weeks: Study notes, materials

**Legal History course:**
- Week 1: Syllabus
- Various weeks: Lecture notes, study materials

---

## 🚨 Current Workaround

**Until Firestore is populated:**

**Users can:**
1. Upload their own materials via Upload tab
2. Materials will be stored in `uploadedMaterials` collection
3. These will appear in the UI
4. Can generate quizzes/flashcards from uploads

**This works but:**
- Users have to upload everything themselves
- Loses the pre-existing 94 materials
- Not ideal for demo/production

---

## 📝 Summary

### Issue
- Materials exist locally (94 files)
- Not in Firestore
- Website shows empty

### Solution
```bash
# 1. Authenticate
gcloud auth application-default login

# 2. Populate Firestore
python scripts/populate_firestore_materials.py

# 3. Verify on website
# Visit https://lls-study-portal-sarfwmfd3q-ez.a.run.app
```

### Result
- All 94 materials appear in website
- Organized by week
- Ready for quiz/flashcard generation

---

## 🎯 Next Steps

**Immediate:**
1. Run `gcloud auth application-default login`
2. Run `python scripts/populate_firestore_materials.py`
3. Verify materials appear on website

**Optional:**
4. Extract text from materials (for better quiz generation)
5. Generate summaries (for study guides)
6. Link materials to specific weeks in course structure

---

## 📞 Need Help?

**If authentication fails:**
```bash
# Make sure you're logged in
gcloud auth list

# Re-authenticate if needed
gcloud auth login
gcloud auth application-default login
```

**If script fails:**
- Check error message
- Verify Firestore database exists
- Verify project ID is correct (vigilant-axis-483119-r8)

**If materials still don't appear:**
- Check Firestore console
- Verify documents were created
- Check browser console for errors

---

**Ready to fix?** Run the authentication command and then the population script!

