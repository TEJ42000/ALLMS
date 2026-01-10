"""Unit tests for Criminal Law course setup script."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone


class TestCriminalLawSetup:
    """Tests for setup_criminal_law_course.py functions."""

    @patch('scripts.setup_criminal_law_course.firestore.Client')
    def test_create_course_success(self, mock_firestore):
        """Test successful course creation."""
        from scripts.setup_criminal_law_course import create_criminal_law_course
        
        # Mock Firestore client
        mock_db = MagicMock()
        mock_firestore.return_value = mock_db
        
        # Mock course doesn't exist
        mock_course_ref = MagicMock()
        mock_course_doc = MagicMock()
        mock_course_doc.exists = False
        mock_course_ref.get.return_value = mock_course_doc
        mock_db.collection.return_value.document.return_value = mock_course_ref
        
        # Run function
        create_criminal_law_course(force=False)
        
        # Verify course was created
        assert mock_course_ref.set.called
        course_data = mock_course_ref.set.call_args[0][0]
        assert course_data['id'] == 'CRIM-2025-2026'
        assert course_data['name'] == 'Criminal Law'
        assert course_data['totalPoints'] == 40
        assert len(course_data['components']) == 2

    @patch('scripts.setup_criminal_law_course.firestore.Client')
    def test_create_course_duplicate_without_force(self, mock_firestore):
        """Test that duplicate course creation fails without --force."""
        from scripts.setup_criminal_law_course import create_criminal_law_course

        # Mock Firestore client
        mock_db = MagicMock()
        mock_firestore.return_value = mock_db

        # Mock course already exists
        mock_course_ref = MagicMock()
        mock_course_doc = MagicMock()
        mock_course_doc.exists = True
        mock_course_ref.get.return_value = mock_course_doc
        mock_db.collection.return_value.document.return_value = mock_course_ref

        # Should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            create_criminal_law_course(force=False)

    def test_create_course_invalid_force_type(self):
        """Test that invalid force parameter type raises TypeError."""
        from scripts.setup_criminal_law_course import create_criminal_law_course

        # Should raise TypeError for non-boolean values
        with pytest.raises(TypeError, match="force parameter must be a boolean"):
            create_criminal_law_course(force="true")

        with pytest.raises(TypeError, match="force parameter must be a boolean"):
            create_criminal_law_course(force=1)

        with pytest.raises(TypeError, match="force parameter must be a boolean"):
            create_criminal_law_course(force=None)

    @patch('scripts.setup_criminal_law_course.firestore.Client')
    def test_create_course_duplicate_with_force(self, mock_firestore):
        """Test that duplicate course creation succeeds with --force."""
        from scripts.setup_criminal_law_course import create_criminal_law_course
        
        # Mock Firestore client
        mock_db = MagicMock()
        mock_firestore.return_value = mock_db
        
        # Mock course already exists
        mock_course_ref = MagicMock()
        mock_course_doc = MagicMock()
        mock_course_doc.exists = True
        mock_course_ref.get.return_value = mock_course_doc
        
        # Mock existing weeks
        mock_weeks_ref = MagicMock()
        mock_week1 = MagicMock()
        mock_week1.reference = MagicMock()
        mock_weeks_ref.stream.return_value = [mock_week1]
        mock_course_ref.collection.return_value = mock_weeks_ref
        
        mock_db.collection.return_value.document.return_value = mock_course_ref
        
        # Should succeed with force=True
        create_criminal_law_course(force=True)
        
        # Verify old weeks were deleted
        assert mock_db.batch.called

    def test_create_part_a_weeks(self):
        """Test Part A weeks creation."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        
        # Should create 6 weeks
        assert len(weeks) == 6
        
        # Check week 1
        week1 = weeks[0]
        assert week1['weekNumber'] == 1
        assert week1['part'] == 'A'
        assert week1['title'] == 'Foundations of Criminal Law'
        # Use substring matching since topics have detailed names (e.g., 'Legality principle (nullum crimen...)')
        assert any('Legality principle' in t for t in week1['topics'])
        assert len(week1['keyConcepts']) > 0
        assert len(week1['keyFrameworks']) > 0
        assert len(week1['examTips']) > 0
        
        # Check all weeks have required fields
        for week in weeks:
            assert 'weekNumber' in week
            assert 'part' in week
            assert week['part'] == 'A'
            assert 'title' in week
            assert 'topicDescription' in week
            assert 'topics' in week
            assert isinstance(week['topics'], list)
            assert 'materials' in week
            assert 'keyConcepts' in week
            assert 'keyFrameworks' in week
            assert 'examTips' in week

    def test_create_part_b_weeks(self):
        """Test Part B weeks creation."""
        from scripts.setup_criminal_law_course import create_part_b_weeks
        
        weeks = create_part_b_weeks()
        
        # Should create 6 weeks (7-12)
        assert len(weeks) == 6
        
        # Check week 7 (first Part B week)
        week7 = weeks[0]
        assert week7['weekNumber'] == 7
        assert week7['part'] == 'B'
        assert week7['title'] == 'ECHR & Fair Trial Rights'
        # Use substring matching since topics have detailed names (e.g., 'Engel criteria (3-part test)')
        assert any('Engel criteria' in t for t in week7['topics'])
        
        # Check all weeks have part B
        for week in weeks:
            assert week['part'] == 'B'
            assert week['weekNumber'] >= 7
            assert week['weekNumber'] <= 12

    def test_part_a_week_numbers_sequential(self):
        """Test that Part A week numbers are sequential 1-6."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        week_numbers = [w['weekNumber'] for w in weeks]
        
        assert week_numbers == [1, 2, 3, 4, 5, 6]

    def test_part_b_week_numbers_sequential(self):
        """Test that Part B week numbers are sequential 7-12."""
        from scripts.setup_criminal_law_course import create_part_b_weeks
        
        weeks = create_part_b_weeks()
        week_numbers = [w['weekNumber'] for w in weeks]
        
        assert week_numbers == [7, 8, 9, 10, 11, 12]

    def test_week_content_structure(self):
        """Test that week content has proper structure."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        
        # Check week 1 key concepts structure
        week1 = weeks[0]
        for concept in week1['keyConcepts']:
            assert 'term' in concept
            assert 'definition' in concept
            assert 'source' in concept
            assert isinstance(concept['term'], str)
            assert isinstance(concept['definition'], str)
            assert len(concept['definition']) > 0

    def test_no_duplicate_week_numbers(self):
        """Test that there are no duplicate week numbers."""
        from scripts.setup_criminal_law_course import create_part_a_weeks, create_part_b_weeks
        
        part_a = create_part_a_weeks()
        part_b = create_part_b_weeks()
        
        all_weeks = part_a + part_b
        week_numbers = [w['weekNumber'] for w in all_weeks]
        
        # Should have 12 unique week numbers
        assert len(week_numbers) == 12
        assert len(set(week_numbers)) == 12

    def test_topics_not_empty(self):
        """Test that all weeks have at least one topic."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        
        for week in weeks:
            assert len(week['topics']) > 0, f"Week {week['weekNumber']} has no topics"

    def test_exam_tips_not_empty(self):
        """Test that all weeks have exam tips."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        
        for week in weeks:
            assert len(week['examTips']) > 0, f"Week {week['weekNumber']} has no exam tips"

    def test_key_frameworks_not_empty(self):
        """Test that all weeks have key frameworks."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        
        for week in weeks:
            assert len(week['keyFrameworks']) > 0, f"Week {week['weekNumber']} has no key frameworks"


class TestWeekContentValidation:
    """Tests for week content validation."""

    def test_week_1_legality_principle_content(self):
        """Test Week 1 has comprehensive legality principle content."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        week1 = weeks[0]
        
        # Check for key legality principle topics
        topics_str = ' '.join(week1['topics']).lower()
        assert 'lex praevia' in topics_str
        assert 'lex certa' in topics_str
        assert 'lex stricta' in topics_str
        assert 'lex scripta' in topics_str

    def test_week_2_tripartite_framework(self):
        """Test Week 2 includes tripartite framework."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        week2 = weeks[1]
        
        topics_str = ' '.join(week2['topics']).lower()
        assert 'tripartite' in topics_str
        assert 'actus reus' in topics_str
        assert 'causation' in topics_str

    def test_week_3_mens_rea_types(self):
        """Test Week 3 covers all mens rea types."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        week3 = weeks[2]
        
        topics_str = ' '.join(week3['topics']).lower()
        assert 'dolus directus' in topics_str
        assert 'dolus indirectus' in topics_str
        assert 'dolus eventualis' in topics_str
        assert 'negligence' in topics_str

    def test_week_4_defenses(self):
        """Test Week 4 covers defenses comprehensively."""
        from scripts.setup_criminal_law_course import create_part_a_weeks
        
        weeks = create_part_a_weeks()
        week4 = weeks[3]
        
        topics_str = ' '.join(week4['topics']).lower()
        assert 'self-defense' in topics_str or 'noodweer' in topics_str
        assert 'necessity' in topics_str or 'noodtoestand' in topics_str
        assert 'duress' in topics_str or 'overmacht' in topics_str

    def test_week_7_echr_content(self):
        """Test Week 7 has ECHR and Engel criteria."""
        from scripts.setup_criminal_law_course import create_part_b_weeks
        
        weeks = create_part_b_weeks()
        week7 = weeks[0]
        
        topics_str = ' '.join(week7['topics']).lower()
        assert 'echr' in topics_str or 'european convention' in topics_str
        assert 'engel' in topics_str

