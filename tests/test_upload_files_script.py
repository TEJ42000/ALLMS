"""Tests for upload_files_script.py."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from upload_files_script import discover_materials, TIER_PRIORITIES, SUPPORTED_EXTENSIONS


class TestDiscoverMaterials:
    """Tests for discover_materials() function."""

    def test_discover_materials_basic_structure(self):
        """Test basic file discovery from three-tier structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create three-tier structure
            syllabus_dir = materials_dir / "Syllabus" / "Criminal_Law"
            syllabus_dir.mkdir(parents=True)
            (syllabus_dir / "syllabus.pdf").write_text("test")
            
            course_dir = materials_dir / "Course_Materials" / "Criminal_Law" / "Part_A"
            course_dir.mkdir(parents=True)
            (course_dir / "lecture.pdf").write_text("test")
            
            supp_dir = materials_dir / "Supplementary_Sources" / "Case_Law" / "ECHR"
            supp_dir.mkdir(parents=True)
            (supp_dir / "case.pdf").write_text("test")
            
            # Discover files
            result = discover_materials(str(materials_dir))
            
            # Should find 3 files
            assert len(result) == 3
            
            # Check tier assignments
            syllabus_keys = [k for k, v in result.items() if v["tier"] == "Syllabus"]
            assert len(syllabus_keys) == 1
            
            course_keys = [k for k, v in result.items() if v["tier"] == "Course_Materials"]
            assert len(course_keys) == 1
            
            supp_keys = [k for k, v in result.items() if v["tier"] == "Supplementary_Sources"]
            assert len(supp_keys) == 1

    def test_discover_materials_tier_priorities(self):
        """Test that tier priorities are correctly assigned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create files in each tier
            for tier_name, priority in TIER_PRIORITIES.items():
                tier_dir = materials_dir / tier_name / "Subject"
                tier_dir.mkdir(parents=True)
                (tier_dir / f"{tier_name.lower()}.pdf").write_text("test")
            
            result = discover_materials(str(materials_dir))
            
            # Check priorities
            for key, info in result.items():
                tier = info["tier"]
                assert info["tier_priority"] == TIER_PRIORITIES[tier]

    def test_discover_materials_supported_extensions(self):
        """Test that only supported file extensions are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            tier_dir = materials_dir / "Syllabus" / "Subject"
            tier_dir.mkdir(parents=True)
            
            # Create files with various extensions
            (tier_dir / "file.pdf").write_text("test")
            (tier_dir / "file.docx").write_text("test")
            (tier_dir / "file.md").write_text("test")
            (tier_dir / "file.txt").write_text("test")
            (tier_dir / "file.jpg").write_text("test")  # Not supported
            (tier_dir / "file.exe").write_text("test")  # Not supported
            
            result = discover_materials(str(materials_dir))
            
            # Should only find supported extensions
            assert len(result) == 4
            
            # Check that unsupported extensions are not included
            for info in result.values():
                ext = Path(info["filename"]).suffix.lower()
                assert ext in SUPPORTED_EXTENSIONS

    def test_discover_materials_case_insensitive_tier_names(self):
        """Test case-insensitive tier name handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create directory with wrong case
            tier_dir = materials_dir / "syllabus" / "Subject"  # lowercase
            tier_dir.mkdir(parents=True)
            (tier_dir / "file.pdf").write_text("test")
            
            # Should still discover the file and normalize tier name
            with patch('upload_files_script.logger') as mock_logger:
                result = discover_materials(str(materials_dir))
                
                # Should log a warning about case
                mock_logger.warning.assert_called()
                warning_call = str(mock_logger.warning.call_args)
                assert "case matters" in warning_call.lower()
            
            # Should find the file with normalized tier name
            assert len(result) == 1
            for info in result.values():
                assert info["tier"] == "Syllabus"  # Normalized

    def test_discover_materials_unique_keys_across_tiers(self):
        """Test that files with same name in different tiers get unique keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)

            # Create files with same name in different tiers
            dir1 = materials_dir / "Syllabus" / "Subject"
            dir1.mkdir(parents=True)
            (dir1 / "file.pdf").write_text("test1")

            dir2 = materials_dir / "Course_Materials" / "Subject"
            dir2.mkdir(parents=True)
            (dir2 / "file.pdf").write_text("test2")

            result = discover_materials(str(materials_dir))

            # Should find both files
            assert len(result) == 2

            # Keys should be different (tier name makes them different)
            keys = list(result.keys())
            assert keys[0] != keys[1]

            # One should have "syllabus" and one should have "course_materials"
            assert any("syllabus" in key for key in keys)
            assert any("course_materials" in key for key in keys)

    def test_discover_materials_metadata(self):
        """Test that file metadata is correctly captured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create a file
            tier_dir = materials_dir / "Syllabus" / "Criminal_Law" / "Part_A"
            tier_dir.mkdir(parents=True)
            test_file = tier_dir / "test_file.pdf"
            test_file.write_text("test content")
            
            result = discover_materials(str(materials_dir))
            
            assert len(result) == 1
            key = list(result.keys())[0]
            info = result[key]
            
            # Check metadata
            assert "path" in info
            assert "filename" in info
            assert info["filename"] == "test_file.pdf"
            assert "tier" in info
            assert info["tier"] == "Syllabus"
            assert "tier_priority" in info
            assert info["tier_priority"] == 1
            assert "subject" in info
            assert info["subject"] == "Criminal_Law"
            assert "category" in info
            assert info["category"] == "Part_A"
            assert "size_bytes" in info
            assert info["size_bytes"] > 0

    def test_discover_materials_nonexistent_directory(self):
        """Test handling of nonexistent materials directory."""
        result = discover_materials("/nonexistent/path")
        
        # Should return empty dict
        assert result == {}

    def test_discover_materials_empty_directory(self):
        """Test handling of empty materials directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = discover_materials(tmpdir)
            
            # Should return empty dict
            assert result == {}

    def test_discover_materials_skips_non_tier_directories(self):
        """Test that non-tier directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create a valid tier directory
            tier_dir = materials_dir / "Syllabus" / "Subject"
            tier_dir.mkdir(parents=True)
            (tier_dir / "file.pdf").write_text("test")
            
            # Create a non-tier directory
            other_dir = materials_dir / "OtherStuff" / "Subject"
            other_dir.mkdir(parents=True)
            (other_dir / "file.pdf").write_text("test")
            
            with patch('upload_files_script.logger') as mock_logger:
                result = discover_materials(str(materials_dir))
                
                # Should log debug message about skipping
                mock_logger.debug.assert_called()
            
            # Should only find file in tier directory
            assert len(result) == 1
            for info in result.values():
                assert info["tier"] in TIER_PRIORITIES

    def test_discover_materials_key_generation(self):
        """Test that file keys are generated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_dir = Path(tmpdir)
            
            # Create a file with specific path
            tier_dir = materials_dir / "Course_Materials" / "Criminal_Law" / "Part_A_Substantive"
            tier_dir.mkdir(parents=True)
            (tier_dir / "Week 3 Lecture.pdf").write_text("test")
            
            result = discover_materials(str(materials_dir))
            
            assert len(result) == 1
            key = list(result.keys())[0]
            
            # Key should be: course_materials_criminal_law_part_a_substantive_week_3_lecture
            assert "course_materials" in key
            assert "criminal_law" in key
            assert "part_a_substantive" in key
            assert "week_3_lecture" in key
            # Should not contain spaces or hyphens
            assert " " not in key
            assert "-" not in key

