# 🎯 Quiz System Manual Testing Guide

## ✅ Environment Setup Complete

The quiz system has been successfully merged into the main branch and is ready for manual testing!

**Merged PR**: #53 - Comprehensive Interactive Quiz System  
**Commit**: e37a7a6  
**Status**: ✅ All 14 tests passing

---

## 🚀 Starting the Application

### 1. Start the Development Server

```bash
cd /Users/matejmonteleone/PycharmProjects/LLMRMS
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🧪 Manual Testing Checklist

### Test 1: Quiz Generation

**Steps**:
1. Navigate to the main page (http://localhost:8000)
2. Scroll down to the **"Quiz Generator"** section
3. Select a topic from the dropdown (e.g., "Private Law", "Criminal Law", "All Topics")
4. Select a difficulty level (Easy, Medium, or Hard)
5. Click the **"Start Quiz"** button

**Expected Results**:
- ✅ Loading indicator appears
- ✅ Quiz generates with 10 questions
- ✅ First question displays with A/B/C/D options
- ✅ Progress indicator shows "1 / 10"
- ✅ Score shows "0"

---

### Test 2: Answer Selection

**Steps**:
1. Read the first question
2. Click on one of the answer options (A, B, C, or D)

**Expected Results**:
- ✅ Selected option highlights with gold border
- ✅ Immediate feedback appears (green box for correct, red box for incorrect)
- ✅ Explanation text displays (if available)
- ✅ If incorrect, correct answer is shown
- ✅ Score updates if answer is correct
- ✅ Option buttons become disabled (can't change answer)
- ✅ "Next" button becomes enabled

---

### Test 3: Question Navigation

**Steps**:
1. After answering the first question, click **"Next"** button
2. Answer the second question
3. Click **"Previous"** button to go back to question 1
4. Try clicking "Previous" on question 1

**Expected Results**:
- ✅ Navigation works smoothly between questions
- ✅ Previous answers are preserved
- ✅ Feedback is still visible for answered questions
- ✅ "Previous" button is disabled on first question
- ✅ Progress indicator updates correctly (e.g., "2 / 10")
- ✅ Can review previous answers without changing them

---

### Test 4: Visual Feedback

**Steps**:
1. Answer a question correctly
2. Answer a question incorrectly
3. Observe the visual feedback

**Expected Results**:

**Correct Answer**:
- ✅ Green feedback box with checkmark (✓)
- ✅ "Correct!" message
- ✅ Explanation text (if available)
- ✅ Score increments

**Incorrect Answer**:
- ✅ Red feedback box with X (✗)
- ✅ "Incorrect" message
- ✅ Shows correct answer with letter (e.g., "Correct answer: B) ...")
- ✅ Explanation text (if available)
- ✅ Score remains unchanged

---

### Test 5: Difficulty Badges

**Steps**:
1. Observe the difficulty badge on each question

**Expected Results**:
- ✅ Easy questions: Green badge
- ✅ Medium questions: Yellow/gold badge
- ✅ Hard questions: Red badge
- ✅ Badge displays in top-right of question card

---

### Test 6: Complete Quiz

**Steps**:
1. Answer all 10 questions
2. On the last question, click **"Finish Quiz"** button

**Expected Results**:
- ✅ Results screen appears
- ✅ Large circular score display shows percentage
- ✅ Score fraction displayed (e.g., "7/10")
- ✅ Performance message based on score:
  - 90%+: "Excellent! You have mastered this material!" (Green)
  - 70-89%: "Good job! You have a solid understanding." (Gold)
  - 50-69%: "Not bad, but there's room for improvement." (Yellow)
  - <50%: "Keep studying! Review the material and try again." (Red)

---

### Test 7: Results Screen - Question Review

**Steps**:
1. On the results screen, scroll down to "Question Review"
2. Examine each question summary

**Expected Results**:
- ✅ All 10 questions listed
- ✅ Each question shows:
  - Question number (Q1, Q2, etc.)
  - Checkmark (✓) for correct or X (✗) for incorrect
  - Question text
  - Your answer
  - Correct answer (if you got it wrong)
- ✅ Correct answers have green left border
- ✅ Incorrect answers have red left border
- ✅ Hover effect on question cards

---

### Test 8: Post-Quiz Actions

**Steps**:
1. On the results screen, click **"Review Answers"** button
2. Navigate through questions to review
3. Return to results screen
4. Click **"Take Another Quiz"** button

**Expected Results**:

**Review Answers**:
- ✅ Returns to question 1
- ✅ All answers preserved
- ✅ Feedback still visible
- ✅ Can navigate through all questions
- ✅ Buttons remain disabled (can't change answers)

**Take Another Quiz**:
- ✅ Returns to quiz generator section
- ✅ Quiz content hidden
- ✅ Topic and difficulty selectors reset
- ✅ Can generate a new quiz

---

### Test 9: Responsive Design

**Steps**:
1. Resize browser window to different widths
2. Test on mobile device (or use browser dev tools)

**Expected Results**:
- ✅ Layout adapts to screen size
- ✅ Buttons remain accessible
- ✅ Text remains readable
- ✅ No horizontal scrolling
- ✅ Touch-friendly button sizes on mobile

---

### Test 10: Styling and Animations

**Steps**:
1. Observe the visual design throughout the quiz
2. Hover over answer options
3. Watch transitions between questions

**Expected Results**:
- ✅ Professional card-based layout
- ✅ Smooth hover effects on answer buttons
- ✅ Answer buttons shift slightly on hover (translateX)
- ✅ Circular score display with gradient background
- ✅ Color-coded feedback (green/red)
- ✅ Smooth transitions between states
- ✅ Consistent gold/navy color scheme

---

## 🐛 Known Issues to Watch For

### Potential Issues:
1. **Quiz Generation Fails**: Check browser console for API errors
2. **No Questions Display**: Verify course materials are loaded
3. **Styling Issues**: Clear browser cache and reload
4. **Navigation Bugs**: Check browser console for JavaScript errors

### Debugging:
```bash
# Check server logs
# Look for errors in terminal where uvicorn is running

# Check browser console
# Open Developer Tools (F12) and check Console tab
```

---

## 📊 Test Results Template

Use this template to record your test results:

```
Date: ___________
Tester: ___________
Browser: ___________
OS: ___________

Test 1 - Quiz Generation:           [ ] Pass  [ ] Fail
Test 2 - Answer Selection:          [ ] Pass  [ ] Fail
Test 3 - Question Navigation:       [ ] Pass  [ ] Fail
Test 4 - Visual Feedback:           [ ] Pass  [ ] Fail
Test 5 - Difficulty Badges:         [ ] Pass  [ ] Fail
Test 6 - Complete Quiz:             [ ] Pass  [ ] Fail
Test 7 - Question Review:           [ ] Pass  [ ] Fail
Test 8 - Post-Quiz Actions:         [ ] Pass  [ ] Fail
Test 9 - Responsive Design:         [ ] Pass  [ ] Fail
Test 10 - Styling/Animations:       [ ] Pass  [ ] Fail

Overall Result:                     [ ] Pass  [ ] Fail

Notes:
_____________________________________________
_____________________________________________
_____________________________________________
```

---

## 🎨 Visual Features to Verify

### Question Display:
- [ ] Clean card layout with rounded corners
- [ ] Clear question text (1.2em font size)
- [ ] A/B/C/D options with circular letter badges
- [ ] Hover effects on answer buttons
- [ ] Difficulty badge in top-right

### Feedback Display:
- [ ] Green box for correct answers
- [ ] Red box for incorrect answers
- [ ] Clear explanation text
- [ ] Correct answer shown when wrong

### Results Screen:
- [ ] Large circular score (200px diameter)
- [ ] Percentage in large text (3em)
- [ ] Fraction below percentage
- [ ] Performance message
- [ ] Color-coded border (green/gold/yellow/red)
- [ ] Detailed question review list
- [ ] Action buttons (Review/Take Another)

---

## 🔧 Troubleshooting

### Issue: Quiz doesn't generate
**Solution**: 
- Check if course materials are loaded
- Verify API endpoint is accessible
- Check browser console for errors

### Issue: Styling looks broken
**Solution**:
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Verify CSS file is loaded (check Network tab)
- Check for CSS conflicts

### Issue: Navigation doesn't work
**Solution**:
- Check browser console for JavaScript errors
- Verify all quiz functions are loaded
- Try refreshing the page

---

## ✅ Success Criteria

The quiz system is working correctly if:
- ✅ Quiz generates with 10 questions
- ✅ All answer options are clickable
- ✅ Immediate feedback appears after selection
- ✅ Navigation works in both directions
- ✅ Score tracks correctly
- ✅ Results screen displays properly
- ✅ Review and restart functions work
- ✅ Styling is professional and polished
- ✅ No JavaScript errors in console
- ✅ Responsive on different screen sizes

---

## 📝 Additional Notes

- The quiz system uses the existing `/api/files-content/quiz` endpoint
- Questions are generated using AI based on course materials
- State management is handled client-side with `quizState` object
- All styling follows the existing gold/navy color scheme
- The system is fully backward compatible with existing code

---

**Happy Testing!** 🎉

If you encounter any issues, check the browser console and server logs for error messages.

