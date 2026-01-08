#!/usr/bin/env python3
"""
Quick Integration Test - Upload → Quiz/Flashcard

Tests the newly implemented integration between upload analysis
and quiz/flashcard generation.

Usage:
    python test_integration_quick.py
"""

import requests
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
COURSE_ID = "LLS-2025-2026"
TEST_USER_ID = "test_user_123"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def create_test_pdf():
    """Create a simple test PDF with text content."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = Path("test_contract_law.pdf")
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 12)
        
        # Add content about contract law
        y = 750
        content = [
            "Contract Law - Formation",
            "",
            "A contract is a legally binding agreement between two or more parties.",
            "",
            "Essential Elements:",
            "1. Offer - A clear proposal made by one party to another",
            "2. Acceptance - Unqualified agreement to the terms of the offer",
            "3. Consideration - Something of value exchanged between parties",
            "4. Intention to create legal relations",
            "5. Capacity - Parties must have legal capacity to contract",
            "",
            "Offer and Acceptance:",
            "An offer must be communicated to the offeree and can be accepted",
            "by conduct or express words. Acceptance must mirror the offer",
            "(mirror image rule).",
            "",
            "Consideration:",
            "Consideration is the price paid for a promise. It must be sufficient",
            "but need not be adequate. Past consideration is generally not valid.",
        ]
        
        for line in content:
            c.drawString(50, y, line)
            y -= 20
        
        c.save()
        print_success(f"Created test PDF: {pdf_path}")
        return pdf_path
        
    except ImportError:
        print_warning("reportlab not installed, using text file instead")
        # Create a text file as fallback
        txt_path = Path("test_contract_law.txt")
        with open(txt_path, 'w') as f:
            f.write("""Contract Law - Formation

A contract is a legally binding agreement between two or more parties.

Essential Elements:
1. Offer - A clear proposal made by one party to another
2. Acceptance - Unqualified agreement to the terms of the offer
3. Consideration - Something of value exchanged between parties
4. Intention to create legal relations
5. Capacity - Parties must have legal capacity to contract

Offer and Acceptance:
An offer must be communicated to the offeree and can be accepted
by conduct or express words. Acceptance must mirror the offer
(mirror image rule).

Consideration:
Consideration is the price paid for a promise. It must be sufficient
but need not be adequate. Past consideration is generally not valid.
""")
        print_success(f"Created test file: {txt_path}")
        return txt_path

def test_upload_file(file_path):
    """Test file upload."""
    print_info("Testing file upload...")

    url = f"{BASE_URL}/api/upload"

    # Add CSRF headers for local testing
    headers = {
        'Origin': 'http://localhost:8000',
        'Referer': 'http://localhost:8000/'
    }

    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/pdf')}
        data = {
            'course_id': COURSE_ID,
            'title': 'Contract Law - Formation'
        }

        response = requests.post(url, files=files, data=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        material_id = result.get('material_id')
        print_success(f"Upload successful! Material ID: {material_id}")
        return material_id
    else:
        print_error(f"Upload failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

def test_analyze_file(material_id):
    """Test file analysis."""
    print_info("Testing file analysis...")

    url = f"{BASE_URL}/api/upload/{material_id}/analyze"
    params = {'course_id': COURSE_ID}
    headers = {
        'Origin': 'http://localhost:8000',
        'Referer': 'http://localhost:8000/'
    }

    response = requests.post(url, params=params, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        analysis = result.get('analysis', {})
        
        print_success("Analysis successful!")
        print_info(f"  Topics: {analysis.get('main_topics', [])}")
        print_info(f"  Difficulty: {analysis.get('difficulty_score', 'N/A')}")
        print_info(f"  Key Concepts: {len(analysis.get('key_concepts', []))}")
        
        return result
    else:
        print_error(f"Analysis failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

def test_generate_quiz(analysis_data):
    """Test quiz generation from analysis."""
    print_info("Testing quiz generation...")
    
    url = f"{BASE_URL}/api/quizzes/courses/{COURSE_ID}"
    
    analysis = analysis_data.get('analysis', {})
    topic = analysis.get('main_topics', ['Contract Law'])[0]
    difficulty_score = analysis.get('difficulty_score', 5)
    difficulty = 'hard' if difficulty_score > 7 else ('medium' if difficulty_score > 4 else 'easy')
    
    payload = {
        'course_id': COURSE_ID,
        'topic': topic,
        'num_questions': 10,
        'difficulty': difficulty,
        'allow_duplicate': False,
        'context': {
            'key_concepts': analysis.get('key_concepts', []),
            'learning_objectives': analysis.get('learning_objectives', [])
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-User-ID': TEST_USER_ID
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        quiz = result.get('quiz', {})
        questions = quiz.get('questions', [])
        
        print_success(f"Quiz generated! {len(questions)} questions")
        if questions:
            print_info(f"  First question: {questions[0].get('question', '')[:60]}...")
        
        return result
    else:
        print_error(f"Quiz generation failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

def test_generate_flashcards(analysis_data):
    """Test flashcard generation from analysis."""
    print_info("Testing flashcard generation...")
    
    url = f"{BASE_URL}/api/files-content/flashcards"
    
    analysis = analysis_data.get('analysis', {})
    topic = analysis.get('main_topics', ['Contract Law'])[0]
    num_concepts = len(analysis.get('key_concepts', []))
    num_cards = min(num_concepts * 2, 20)
    
    payload = {
        'course_id': COURSE_ID,
        'topic': topic,
        'num_cards': num_cards,
        'context': {
            'key_concepts': analysis.get('key_concepts', []),
            'extracted_text': analysis_data.get('extracted_text', '')[:5000]
        }
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        flashcards = result.get('flashcards', [])
        
        print_success(f"Flashcards generated! {len(flashcards)} cards")
        if flashcards:
            first_card = flashcards[0]
            print_info(f"  First card front: {first_card.get('front', '')[:60]}...")
        
        return result
    else:
        print_error(f"Flashcard generation failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

def main():
    """Run integration tests."""
    print("\n" + "="*60)
    print("  Upload → Quiz/Flashcard Integration Test")
    print("="*60 + "\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        print_success("Server is running")
    except requests.exceptions.ConnectionError:
        print_error("Server is not running!")
        print_info("Start the server with: uvicorn app.main:app --reload")
        return
    
    # Create test file
    test_file = create_test_pdf()
    
    try:
        # Test 1: Upload
        print("\n" + "-"*60)
        print("Test 1: File Upload")
        print("-"*60)
        material_id = test_upload_file(test_file)
        if not material_id:
            print_error("Upload test failed. Stopping.")
            return
        
        # Wait a bit for processing
        time.sleep(2)
        
        # Test 2: Analysis
        print("\n" + "-"*60)
        print("Test 2: Content Analysis")
        print("-"*60)
        analysis_data = test_analyze_file(material_id)
        if not analysis_data:
            print_error("Analysis test failed. Stopping.")
            return
        
        # Wait a bit
        time.sleep(2)
        
        # Test 3: Quiz Generation
        print("\n" + "-"*60)
        print("Test 3: Quiz Generation")
        print("-"*60)
        quiz_result = test_generate_quiz(analysis_data)
        
        # Test 4: Flashcard Generation
        print("\n" + "-"*60)
        print("Test 4: Flashcard Generation")
        print("-"*60)
        flashcard_result = test_generate_flashcards(analysis_data)
        
        # Summary
        print("\n" + "="*60)
        print("  Test Summary")
        print("="*60)
        
        tests_passed = 0
        tests_total = 4
        
        if material_id:
            print_success("Upload: PASS")
            tests_passed += 1
        else:
            print_error("Upload: FAIL")
        
        if analysis_data:
            print_success("Analysis: PASS")
            tests_passed += 1
        else:
            print_error("Analysis: FAIL")
        
        if quiz_result:
            print_success("Quiz Generation: PASS")
            tests_passed += 1
        else:
            print_error("Quiz Generation: FAIL")
        
        if flashcard_result:
            print_success("Flashcard Generation: PASS")
            tests_passed += 1
        else:
            print_error("Flashcard Generation: FAIL")
        
        print(f"\nResults: {tests_passed}/{tests_total} tests passed")
        
        if tests_passed == tests_total:
            print_success("\n🎉 All tests passed! Integration is working correctly.")
            print_info("\nNext steps:")
            print_info("  1. Test in browser UI")
            print_info("  2. Create demo course")
            print_info("  3. Upload sample materials")
        else:
            print_warning(f"\n⚠️  {tests_total - tests_passed} test(s) failed. Review errors above.")
        
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
            print_info(f"\nCleaned up test file: {test_file}")

if __name__ == "__main__":
    main()

