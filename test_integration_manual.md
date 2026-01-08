# Manual Integration Test - Upload → Quiz/Flashcard

## Test Environment

**Date:** 2026-01-08  
**Branch:** main (with integration merged)  
**Features:** Upload → Quiz, Upload → Flashcard

---

## Prerequisites

- [ ] Application running locally or deployed
- [ ] User authenticated (@mgms.eu domain)
- [ ] Course selected (e.g., LLS-2025-2026)
- [ ] Sample PDF file ready for upload

---

## Test 1: Upload → Quiz Integration

### Steps

1. **Navigate to Upload Tab**
   - [ ] Click "Upload" tab in navigation
   - [ ] Verify upload interface loads

2. **Upload a PDF File**
   - [ ] Drag & drop a PDF (or click to browse)
   - [ ] File: Any PDF with text content (lecture notes, article, etc.)
   - [ ] Verify upload progress shows
   - [ ] Wait for upload to complete

3. **Wait for Analysis**
   - [ ] Verify "Analyzing..." message appears
   - [ ] Wait for analysis to complete (may take 10-30 seconds)
   - [ ] Verify analysis results display:
     - Main topics
     - Key concepts
     - Difficulty score
     - Recommended study methods

4. **Generate Quiz**
   - [ ] Click "Generate Quiz" button
   - [ ] Verify loading notification appears
   - [ ] Wait for quiz generation (may take 10-20 seconds)
   - [ ] Verify automatic switch to "Quiz" tab
   - [ ] Verify quiz appears with questions

5. **Verify Quiz Content**
   - [ ] Check quiz has 10 questions
   - [ ] Check questions relate to uploaded content
   - [ ] Check difficulty matches analysis (easy/medium/hard)
   - [ ] Try answering a question
   - [ ] Verify feedback works

### Expected Results

✅ **Success Criteria:**
- Upload completes without errors
- Analysis shows relevant topics and concepts
- "Generate Quiz" button triggers quiz generation
- Quiz appears in Quiz tab
- Quiz contains 10 questions related to content
- Questions are answerable

❌ **Failure Indicators:**
- Upload fails
- Analysis doesn't complete
- "Generate Quiz" shows error
- Quiz doesn't appear
- Quiz is empty or has errors

### Actual Results

**Upload Status:** _______________  
**Analysis Status:** _______________  
**Quiz Generation Status:** _______________  
**Quiz Display Status:** _______________  

**Notes:**
```
[Write any observations, errors, or issues here]
```

---

## Test 2: Upload → Flashcard Integration

### Steps

1. **Use Same Uploaded File**
   - [ ] Return to Upload tab
   - [ ] Verify analysis results still visible
   - [ ] (Or upload a new file and wait for analysis)

2. **Generate Flashcards**
   - [ ] Click "Generate Flashcards" button
   - [ ] Verify loading notification appears
   - [ ] Wait for flashcard generation (may take 10-20 seconds)
   - [ ] Verify automatic switch to "Flashcards" tab
   - [ ] Verify flashcards appear

3. **Verify Flashcard Content**
   - [ ] Check flashcards are displayed
   - [ ] Check number of flashcards (should be 10-20)
   - [ ] Click to flip a flashcard
   - [ ] Verify front shows question/term
   - [ ] Verify back shows answer/definition
   - [ ] Navigate through multiple cards

4. **Test Flashcard Features**
   - [ ] Click "Next" button
   - [ ] Click "Previous" button
   - [ ] Mark a card as "Known"
   - [ ] Verify stats update

### Expected Results

✅ **Success Criteria:**
- "Generate Flashcards" button triggers generation
- Flashcards appear in Flashcards tab
- Flashcards contain 10-20 cards
- Cards relate to uploaded content
- Flip animation works
- Navigation works

❌ **Failure Indicators:**
- "Generate Flashcards" shows error
- Flashcards don't appear
- Flashcards are empty
- Can't flip cards
- Navigation broken

### Actual Results

**Flashcard Generation Status:** _______________  
**Flashcard Display Status:** _______________  
**Number of Cards:** _______________  
**Navigation Status:** _______________  

**Notes:**
```
[Write any observations, errors, or issues here]
```

---

## Test 3: Error Handling

### Test 3.1: Generate Without Analysis

1. **Reset Upload Tab**
   - [ ] Refresh page or clear upload
   - [ ] Verify no analysis results visible

2. **Try to Generate Quiz**
   - [ ] Click "Generate Quiz" button
   - [ ] Verify warning notification appears
   - [ ] Message should say: "Please analyze a file first"

3. **Try to Generate Flashcards**
   - [ ] Click "Generate Flashcards" button
   - [ ] Verify warning notification appears
   - [ ] Message should say: "Please analyze a file first"

### Expected Results

✅ **Success Criteria:**
- Warning notifications appear
- No errors thrown
- User-friendly messages

### Test 3.2: Network Error Simulation

1. **Disconnect Network** (optional)
   - [ ] Turn off WiFi or disconnect network
   - [ ] Try to generate quiz
   - [ ] Verify error notification appears
   - [ ] Reconnect network

### Expected Results

✅ **Success Criteria:**
- Error notification appears
- Error message is user-friendly
- No application crash

---

## Test 4: End-to-End User Flow

### Complete User Journey

1. **Start Fresh**
   - [ ] Navigate to Upload tab
   - [ ] Upload a new PDF file

2. **Analyze Content**
   - [ ] Wait for analysis to complete
   - [ ] Review analysis results

3. **Generate Quiz**
   - [ ] Click "Generate Quiz"
   - [ ] Take the quiz
   - [ ] Submit answers
   - [ ] Review results

4. **Generate Flashcards**
   - [ ] Return to Upload tab
   - [ ] Click "Generate Flashcards"
   - [ ] Study flashcards
   - [ ] Mark some as known

5. **Check Progress**
   - [ ] Navigate to Dashboard
   - [ ] Verify stats updated
   - [ ] Check for new badges (if applicable)

### Expected Results

✅ **Success Criteria:**
- Complete flow works without errors
- All features integrate seamlessly
- Stats update correctly
- User experience is smooth

---

## Browser Compatibility (Optional)

Test in multiple browsers:

- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

---

## Performance Metrics

**Upload Time:** _____ seconds  
**Analysis Time:** _____ seconds  
**Quiz Generation Time:** _____ seconds  
**Flashcard Generation Time:** _____ seconds  

**Total Time (Upload → Quiz):** _____ seconds  
**Total Time (Upload → Flashcards):** _____ seconds  

---

## Issues Found

### Critical Issues
```
[List any critical bugs that prevent functionality]
```

### Minor Issues
```
[List any minor bugs or UX issues]
```

### Suggestions
```
[List any improvements or enhancements]
```

---

## Test Summary

**Date Tested:** _______________  
**Tester:** _______________  
**Environment:** _______________  

**Overall Status:** ⬜ PASS / ⬜ FAIL / ⬜ PARTIAL

**Recommendation:**
```
[Proceed to next phase / Fix issues / Need more testing]
```

---

## Next Steps

If tests pass:
- [ ] Proceed with creating demo course
- [ ] Upload sample materials
- [ ] Generate sample content

If tests fail:
- [ ] Document issues in GitHub
- [ ] Fix critical bugs
- [ ] Re-test

---

## Quick Test Checklist

**5-Minute Smoke Test:**
- [ ] Upload PDF
- [ ] Wait for analysis
- [ ] Click "Generate Quiz"
- [ ] Verify quiz appears
- [ ] Click "Generate Flashcards"
- [ ] Verify flashcards appear

**Result:** ⬜ PASS / ⬜ FAIL

