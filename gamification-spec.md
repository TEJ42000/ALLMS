Specification: Law Student Engagement & Mastery Ecosystem1. Executive SummaryThis document defines a behavioral framework for a law student web application. It transitions the experience from a static resource to a dynamic "Mastery Journey" designed for Gen Z (born 2004–2010). The strategy focuses on immediate gratification, flexible consistency, and high-stakes simulation during the critical Week 7 study period.2. Feature 1: The "Juris Doctor" XP EconomyGoal: Provide instant visual feedback for every micro-action, turning "dry" study into measurable progress.Task Valuation TablePoints (XP) are awarded immediately upon task completion to satisfy the Gen Z need for real-time validation.ComponentActionXP AwardedFlash Cards10 cards reviewed correctly5 XPStudy GuidesCompletion of a weekly topic guide15 XPQuizzesEasy Difficulty (Pass)10 XPQuizzesHard Difficulty (Pass)25 XPEvaluationsAI Grade 1–620 XPEvaluationsAI Grade 7–1050 XPLevel ProgressionStudents progress through career-themed titles:Levels 1-10: Junior ClerkLevels 11-25: Summer AssociateLevels 26-50: Junior PartnerLevel 50+: Senior Partner / Juris DoctorSimplified Firestore Model:JSON// 'user_stats' collection -> {userId} document
{
  "total_xp": 4500,
  "current_level": 12,
  "level_title": "Summer Associate",
  "xp_to_next_level": 500
}
3. Feature 2: The "Counselor’s Creed" Streak SystemGoal: Leverage "Loss Avoidance" to form daily habits without causing anxiety.1The 4:00 AM Reset: To accommodate Gen Z nocturnal study patterns, the "day" ends at 4:00 AM, allowing late-night sessions to count for the current day.Consistency Bonus: Completing at least one task in all 4 categories (Flashcards, Quiz, Evaluation, Guide) in a single week awards a "Full Disclosure" XP multiplier for the following week.Streak Freeze: A consumable item earned every 500 XP that automatically protects the streak if a student misses a day.Simplified Firestore Model:JSON// 'user_stats' collection -> {userId} document
{
  "streak": {
    "current_count": 14,
    "last_activity_date": Timestamp(...),
    "freezes_available": 1,
    "next_reset": Timestamp(...) 
  }
}
4. Feature 3: Behavioral & Achievement BadgesGoal: Reward specific study habits and academic excellence through visual "Status Symbols."3Creative Badge Categories🦉 Night Owl: Complete aHard Quiz or AI Evaluation between 11:00 PM and 3:00 AM.☀️ Early Riser: Complete a Study Guide before 8:00 AM.🎩 Hat Trick: Pass 3 separate Hard Quizzes in a row with 100% accuracy.5🔥 Combo King: Flip 20 Flashcards in a row without marking one as "Incorrect."6⚖️ Legal Scholar: Achieve an AI Grade of 9 or 10 on three consecutive Evaluations.📖 Deep Diver: Spend 45+ minutes interacting with a single Study Guide without navigating away.Simplified Firestore Model:JSON// 'user_achievements' subcollection under {userId}
{
  "badge_id": "night_owl",
  "tier": "gold", // bronze, silver, gold
  "earned_at": Timestamp(...),
  "times_earned": 3
}
5. Feature 4: The "Week 7" Boss Prep QuestGoal: Frame the final study week as a "Quest" to maximize intensity before the exam.7Quest Framing: During Week 7, the UI transforms into "Boss Prep Mode." The dashboard displays a "Exam Readiness" progress bar that fills as students complete guides and quizzes.7The Boss Battle: The final practice exam is framed as a "Boss Battle." Students who pass with a score of 7+ on the first attempt earn the exclusive "Trial Ready" badge.9Double XP Weekend: Week 7 Saturday and Sunday are "Double XP" days for hard quizzes and AI evaluations to encourage the final push.106. UI/UX Visual GuidelinesProgress Bars: Use color-transitioning bars (Red $\rightarrow$ Yellow $\rightarrow$ Green) for both XP levels and Week 7 exam readiness.AI Feedback Loops: When the AI gives a 1-10 grade, use "Glow & Grow" feedback—highlighting strengths with a "glow" effect and areas for improvement with a "grow" icon to keep feedback constructive.Confetti Triggers: Trigger micro-animations (confetti or sparkles) immediately when a "Hat Trick" or "Combo King" is achieved to provide the dopamine hit Gen Z expects.Brag Buttons: At the end of Week 7, provide a shareable "Study Report Card" graphic for students to post to social circles (Clans/Discord), fostering social influence.3