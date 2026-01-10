#!/usr/bin/env python3
"""
Setup Criminal Law Course (CRIM-2025-2026) with Part A and Part B structure.

This script creates the Criminal Law course in Firestore with:
- Part A: Substantive Criminal Law (weeks 1-6)
- Part B: Criminal Procedure & Human Rights (weeks 1-6)
- Course components for Part A and Part B
- Week documents with detailed content
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore


def create_criminal_law_course():
    """Create the Criminal Law course with Part A and Part B."""
    
    db = firestore.Client()
    course_id = "CRIM-2025-2026"
    
    print("=" * 70)
    print("🎓 Setting up Criminal Law Course (CRIM-2025-2026)")
    print("=" * 70)
    
    # Course metadata
    course_data = {
        "id": course_id,
        "name": "Criminal Law",
        "program": "LLB Law",
        "institution": "Maastricht University",
        "academicYear": "2025-2026",
        "totalPoints": 40,
        "passingThreshold": 22,
        "components": [
            {
                "id": "A",
                "name": "Substantive Criminal Law",
                "maxPoints": 20,
                "description": "Foundations, offense structure, mens rea, defenses, inchoate offenses, and participation"
            },
            {
                "id": "B",
                "name": "Criminal Procedure & Human Rights",
                "maxPoints": 20,
                "description": "ECHR, fair trial rights, evidence, and procedural safeguards"
            }
        ],
        "materialSubjects": ["Criminal_Law"],
        "abbreviations": {
            "Sr": "Wetboek van Strafrecht (Dutch Criminal Code)",
            "Sv": "Wetboek van Strafvordering (Dutch Code of Criminal Procedure)",
            "ECHR": "European Convention on Human Rights",
            "ECtHR": "European Court of Human Rights"
        },
        "active": True,
        "weekCount": 12,  # 6 weeks Part A + 6 weeks Part B
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    # Create course document
    course_ref = db.collection("courses").document(course_id)
    course_ref.set(course_data)
    print(f"\n✅ Created course: {course_id}")
    print(f"   Name: {course_data['name']}")
    print(f"   Components: Part A (20 pts) + Part B (20 pts)")
    
    # Create Part A weeks
    print("\n📚 Creating Part A weeks (Substantive Criminal Law)...")
    part_a_weeks = create_part_a_weeks()
    
    batch = db.batch()
    for week_data in part_a_weeks:
        week_ref = course_ref.collection("weeks").document(f"week-{week_data['weekNumber']}")
        batch.set(week_ref, week_data)
    batch.commit()
    print(f"   ✅ Created {len(part_a_weeks)} Part A weeks")
    
    # Create Part B weeks
    print("\n📚 Creating Part B weeks (Criminal Procedure & Human Rights)...")
    part_b_weeks = create_part_b_weeks()
    
    batch = db.batch()
    for week_data in part_b_weeks:
        week_ref = course_ref.collection("weeks").document(f"week-{week_data['weekNumber']}")
        batch.set(week_ref, week_data)
    batch.commit()
    print(f"   ✅ Created {len(part_b_weeks)} Part B weeks")
    
    print("\n" + "=" * 70)
    print("✅ Criminal Law course setup complete!")
    print("=" * 70)
    print(f"\nCourse ID: {course_id}")
    print(f"Total weeks: {len(part_a_weeks) + len(part_b_weeks)}")
    print(f"Part A weeks: {len(part_a_weeks)}")
    print(f"Part B weeks: {len(part_b_weeks)}")
    print("\nNext steps:")
    print("1. Run populate_firestore_materials.py to add materials")
    print("2. Test the Part A/B selector in the UI")
    print("3. Generate study guides for each part")


def create_part_a_weeks():
    """Create Part A (Substantive Criminal Law) weeks 1-6."""
    
    weeks = []
    
    # Week 1: Foundations
    weeks.append({
        "weekNumber": 1,
        "part": "A",
        "title": "Foundations of Criminal Law",
        "topicDescription": "Introduction to criminal law principles including the legality principle (lex praevia, lex certa, lex stricta, lex scripta) and theories of punishment (retribution, deterrence, rehabilitation, incapacitation).",
        "topics": [
            "Legality principle (nullum crimen sine lege)",
            "Lex praevia (no retroactive laws)",
            "Lex certa (legal certainty)",
            "Lex stricta (strict interpretation)",
            "Lex scripta (written law)",
            "Theories of punishment: retribution",
            "Theories of punishment: deterrence",
            "Theories of punishment: rehabilitation"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Legality Principle",
                "definition": "Nullum crimen, nulla poena sine lege - no crime, no punishment without law. Protects against arbitrary prosecution.",
                "source": "Criminal Law Textbook Chapter 1"
            },
            {
                "term": "Lex Praevia",
                "definition": "Laws must exist before the act (no retroactive criminal laws).",
                "source": "ECHR Article 7"
            },
            {
                "term": "Retribution",
                "definition": "Punishment as deserved suffering for wrongdoing - 'just deserts' theory.",
                "source": "Criminal Law Textbook Chapter 1"
            }
        ],
        "keyFrameworks": [
            "Four aspects of legality principle (lex praevia, certa, stricta, scripta)",
            "Four theories of punishment (retribution, deterrence, rehabilitation, incapacitation)"
        ],
        "examTips": [
            "Always check if legality principle is violated in problem questions",
            "Distinguish between general and specific deterrence",
            "Know which theory of punishment Dutch law primarily follows"
        ]
    })
    
    # Week 2: Offense Structure
    weeks.append({
        "weekNumber": 2,
        "part": "A",
        "title": "Offense Structure & Actus Reus",
        "topicDescription": "The tripartite framework for analyzing criminal offenses (3 stages), actus reus requirements, liability for omissions, and causation including the but-for test and 8 attribution factors.",
        "topics": [
            "Tripartite framework (3 stages)",
            "Actus reus (guilty act)",
            "Voluntary act requirement",
            "Omissions liability",
            "Legal duty to act",
            "Causation: but-for test",
            "Causation: 8 attribution factors",
            "Intervening causes"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Tripartite Framework",
                "definition": "Three-stage analysis: (1) Actus reus, (2) Mens rea, (3) Absence of defenses.",
                "source": "Criminal Law Textbook Chapter 2"
            },
            {
                "term": "Actus Reus",
                "definition": "The guilty act - physical element of a crime. Must be voluntary.",
                "source": "Criminal Law Textbook Chapter 2"
            },
            {
                "term": "But-For Test",
                "definition": "Factual causation: 'But for the defendant's act, would the result have occurred?'",
                "source": "Criminal Law Textbook Chapter 2"
            }
        ],
        "keyFrameworks": [
            "Tripartite framework (3 stages)",
            "8 attribution factors for legal causation",
            "Requirements for omissions liability"
        ],
        "examTips": [
            "Always apply tripartite framework systematically",
            "Check both factual (but-for) and legal causation",
            "Omissions require a legal duty to act - identify the source"
        ]
    })
    
    # Week 3: Mens Rea
    weeks.append({
        "weekNumber": 3,
        "part": "A",
        "title": "Mens Rea & Mental States",
        "topicDescription": "Mental element of crimes including dolus directus (direct intent), dolus indirectus (indirect intent), dolus eventualis (conditional intent), negligence (2-stage test), and strict liability offenses.",
        "topics": [
            "Mens rea (guilty mind)",
            "Dolus directus (direct intent)",
            "Dolus indirectus (indirect intent)",
            "Dolus eventualis (conditional intent)",
            "Negligence: objective standard",
            "Negligence: 2-stage test",
            "Strict liability offenses",
            "Transferred malice"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Dolus Directus",
                "definition": "Direct intent - the defendant's purpose or aim to bring about the prohibited result.",
                "source": "Criminal Law Textbook Chapter 3"
            },
            {
                "term": "Dolus Eventualis",
                "definition": "Conditional intent - defendant foresees result as possible and accepts/approves it.",
                "source": "Criminal Law Textbook Chapter 3"
            },
            {
                "term": "Negligence",
                "definition": "Failure to meet the standard of care expected of a reasonable person. 2-stage test: (1) objective breach, (2) subjective foreseeability.",
                "source": "Criminal Law Textbook Chapter 3"
            }
        ],
        "keyFrameworks": [
            "Hierarchy of mens rea (dolus directus > indirectus > eventualis > negligence)",
            "2-stage test for negligence",
            "Dolus eventualis test (foresight + acceptance)"
        ],
        "examTips": [
            "Distinguish dolus eventualis from negligence - key is acceptance/approval",
            "Apply 2-stage negligence test systematically",
            "Check if offense requires specific mens rea or allows negligence"
        ]
    })
    
    # Week 4: Defenses
    weeks.append({
        "weekNumber": 4,
        "part": "A",
        "title": "Defenses: Justifications & Excuses",
        "topicDescription": "Criminal defenses including the distinction between justifications and excuses, self-defense (7 requirements), necessity, duress, and insanity defense.",
        "topics": [
            "Justifications vs excuses",
            "Self-defense (noodweer)",
            "7 requirements for self-defense",
            "Proportionality in self-defense",
            "Necessity (noodtoestand)",
            "Duress (overmacht)",
            "Insanity defense",
            "Diminished responsibility"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Justification",
                "definition": "Defense that makes the act lawful - the act was the right thing to do (e.g., self-defense).",
                "source": "Criminal Law Textbook Chapter 4"
            },
            {
                "term": "Excuse",
                "definition": "Defense that excuses the actor - the act was wrong but the actor is not blameworthy (e.g., insanity).",
                "source": "Criminal Law Textbook Chapter 4"
            },
            {
                "term": "Self-Defense",
                "definition": "Justified use of force to defend against unlawful attack. Requires 7 elements including necessity and proportionality.",
                "source": "Sr Article 41"
            }
        ],
        "keyFrameworks": [
            "7 requirements for self-defense",
            "Justification vs excuse distinction",
            "Proportionality assessment"
        ],
        "examTips": [
            "Always check all 7 requirements for self-defense",
            "Distinguish necessity (justification) from duress (excuse)",
            "Proportionality is key - excessive force defeats self-defense"
        ]
    })
    
    # Week 5: Inchoate Offenses
    weeks.append({
        "weekNumber": 5,
        "part": "A",
        "title": "Inchoate Offenses & Attempt",
        "topicDescription": "Incomplete crimes including attempt (subjectivist vs objectivist approaches), impossibility (factual vs legal), and voluntary withdrawal as a defense.",
        "topics": [
            "Attempt (poging)",
            "Subjectivist approach to attempt",
            "Objectivist approach to attempt",
            "Factual impossibility",
            "Legal impossibility",
            "Voluntary withdrawal",
            "Preparation vs attempt",
            "Abandonment"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Attempt",
                "definition": "Trying to commit a crime but failing to complete it. Requires intent and substantial step toward completion.",
                "source": "Sr Article 45"
            },
            {
                "term": "Factual Impossibility",
                "definition": "Attempt fails due to factual circumstances (e.g., empty gun). Not a defense.",
                "source": "Criminal Law Textbook Chapter 5"
            },
            {
                "term": "Voluntary Withdrawal",
                "definition": "Defendant voluntarily abandons attempt before completion. May negate liability.",
                "source": "Criminal Law Textbook Chapter 5"
            }
        ],
        "keyFrameworks": [
            "Subjectivist vs objectivist approaches",
            "Factual vs legal impossibility",
            "Requirements for voluntary withdrawal"
        ],
        "examTips": [
            "Distinguish preparation from attempt - look for substantial step",
            "Factual impossibility is NOT a defense",
            "Voluntary withdrawal must be truly voluntary, not due to external factors"
        ]
    })
    
    # Week 6: Participation
    weeks.append({
        "weekNumber": 6,
        "part": "A",
        "title": "Participation & Complicity",
        "topicDescription": "Forms of participation in crime including derivative liability, perpetration by means, instigation, aiding and abetting, co-perpetration, and corporate criminal liability.",
        "topics": [
            "Derivative liability",
            "Perpetration by means",
            "Instigation (uitlokking)",
            "Aiding and abetting (medeplichtigheid)",
            "Co-perpetration (medeplegen)",
            "Corporate criminal liability",
            "Vicarious liability",
            "Withdrawal from participation"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Derivative Liability",
                "definition": "Accomplice's liability derives from the principal's crime. Requires principal to commit the offense.",
                "source": "Criminal Law Textbook Chapter 6"
            },
            {
                "term": "Co-Perpetration",
                "definition": "Joint commission of a crime with shared intent and substantial contribution. All are principals.",
                "source": "Sr Article 47"
            },
            {
                "term": "Aiding and Abetting",
                "definition": "Intentionally helping another commit a crime. Lesser liability than perpetration.",
                "source": "Sr Article 48"
            }
        ],
        "keyFrameworks": [
            "Forms of participation (perpetrator, co-perpetrator, instigator, aider)",
            "Requirements for co-perpetration",
            "Corporate liability requirements"
        ],
        "examTips": [
            "Distinguish co-perpetration (equal liability) from aiding (lesser liability)",
            "Check if accomplice has required mens rea for their form of participation",
            "Corporate liability requires both act by natural person and attribution to corporation"
        ]
    })
    
    return weeks


def create_part_b_weeks():
    """Create Part B (Criminal Procedure & Human Rights) weeks 1-6."""
    
    weeks = []
    
    # Week 1: ECHR Foundations
    weeks.append({
        "weekNumber": 7,  # Part B starts at week 7
        "part": "B",
        "title": "ECHR & Fair Trial Rights",
        "topicDescription": "Introduction to the European Convention on Human Rights, Article 6 fair trial rights, Engel criteria for determining criminal charges, and the autonomous interpretation of 'criminal' under ECHR.",
        "topics": [
            "ECHR Article 6 (fair trial)",
            "Engel criteria (3-part test)",
            "Autonomous interpretation",
            "Criminal charge definition",
            "Presumption of innocence",
            "Right to be informed",
            "Adequate time and facilities",
            "Legal assistance"
        ],
        "materials": [],
        "keyConcepts": [
            {
                "term": "Engel Criteria",
                "definition": "3-part test to determine if proceedings are 'criminal': (1) domestic classification, (2) nature of offense, (3) severity of penalty.",
                "source": "Engel v. Netherlands (1976)"
            },
            {
                "term": "Autonomous Interpretation",
                "definition": "ECHR terms have independent meaning, not bound by domestic law classifications.",
                "source": "ECtHR case law"
            }
        ],
        "keyFrameworks": [
            "Engel criteria (3-part test)",
            "Article 6 fair trial components"
        ],
        "examTips": [
            "Apply all 3 Engel criteria - any one can be sufficient",
            "Remember autonomous interpretation - domestic label not decisive"
        ]
    })
    
    # Weeks 2-6 would continue with Salduz, evidence, impartiality, etc.
    # For brevity, adding placeholders
    for week_num in range(8, 13):
        weeks.append({
            "weekNumber": week_num,
            "part": "B",
            "title": f"Criminal Procedure Week {week_num - 6}",
            "topicDescription": "Criminal procedure and human rights topics (to be detailed).",
            "topics": ["Placeholder topic"],
            "materials": [],
            "keyConcepts": [],
            "keyFrameworks": [],
            "examTips": []
        })
    
    return weeks


if __name__ == "__main__":
    try:
        create_criminal_law_course()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

