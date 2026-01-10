"""
Tests for homepage logo integration.

This test suite validates that the SVG logo is properly integrated
into the homepage navigation and footer, replacing the emoji character.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient


class TestHomepageLogo:
    """Test suite for homepage logo integration."""

    def test_logo_exists_in_navigation(self, client: TestClient):
        """Test that logo image exists in navigation bar."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find logo in navigation
        nav_logo = soup.select_one('.nav-brand img.brand-logo')
        assert nav_logo is not None, "Logo image not found in navigation"
        
        # Verify logo attributes
        assert nav_logo.get('src') == '/static/images/favicon.svg'
        assert nav_logo.get('alt') == 'Cognitio Flow Logo'
        assert 'brand-logo' in nav_logo.get('class', [])

    def test_logo_exists_in_footer(self, client: TestClient):
        """Test that logo image exists in footer."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find logo in footer
        footer_logo = soup.select_one('.footer-brand img.footer-logo')
        assert footer_logo is not None, "Logo image not found in footer"
        
        # Verify logo attributes
        assert footer_logo.get('src') == '/static/images/favicon.svg'
        assert footer_logo.get('alt') == 'Cognitio Flow Logo'
        assert 'footer-logo' in footer_logo.get('class', [])

    def test_no_emoji_in_navigation(self, client: TestClient):
        """Test that emoji character is not used in navigation."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        nav_brand = soup.select_one('.nav-brand')
        
        # Should not contain emoji as direct text
        assert '⚖️' not in nav_brand.get_text(), "Emoji should be replaced with SVG logo"

    def test_no_emoji_in_footer(self, client: TestClient):
        """Test that emoji character is not used in footer."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        footer_brand = soup.select_one('.footer-brand')
        
        # Should not contain emoji as direct text
        # Note: May appear in other parts of footer, but not in brand section
        footer_brand_header = soup.select_one('.footer-brand-header')
        if footer_brand_header:
            assert '⚖️' not in footer_brand_header.get_text(), "Emoji should be replaced with SVG logo"

    def test_brand_name_present(self, client: TestClient):
        """Test that brand name 'Cognitio Flow' is present."""
        response = client.get("/")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check navigation
        nav_brand_name = soup.select_one('.nav-brand .brand-name')
        assert nav_brand_name is not None
        assert 'Cognitio Flow' in nav_brand_name.get_text()

        # Check footer
        footer_brand_name = soup.select_one('.footer-brand .brand-name')
        assert footer_brand_name is not None
        assert 'Cognitio Flow' in footer_brand_name.get_text()

    def test_logo_accessibility(self, client: TestClient):
        """Test that logo has proper accessibility attributes."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check navigation logo
        nav_logo = soup.select_one('.nav-brand img.brand-logo')
        assert nav_logo.get('alt'), "Navigation logo missing alt text"
        assert len(nav_logo.get('alt')) > 0, "Navigation logo alt text is empty"
        
        # Check footer logo
        footer_logo = soup.select_one('.footer-brand img.footer-logo')
        assert footer_logo.get('alt'), "Footer logo missing alt text"
        assert len(footer_logo.get('alt')) > 0, "Footer logo alt text is empty"

    def test_css_classes_applied(self, client: TestClient):
        """Test that proper CSS classes are applied to logo elements."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Navigation logo should have brand-logo class
        nav_logo = soup.select_one('.nav-brand img')
        assert 'brand-logo' in nav_logo.get('class', [])
        
        # Footer logo should have footer-logo class
        footer_logo = soup.select_one('.footer-brand img')
        assert 'footer-logo' in footer_logo.get('class', [])

    def test_footer_brand_header_structure(self, client: TestClient):
        """Test that footer has proper brand header structure."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Footer should have brand header container
        footer_brand_header = soup.select_one('.footer-brand-header')
        assert footer_brand_header is not None, "Footer brand header container missing"
        
        # Should contain both logo and brand name
        logo = footer_brand_header.select_one('img.footer-logo')
        brand_name = footer_brand_header.select_one('.brand-name')
        
        assert logo is not None, "Logo missing from footer brand header"
        assert brand_name is not None, "Brand name missing from footer brand header"


class TestLogoCSS:
    """Test suite for logo CSS styling."""

    def test_homepage_css_loaded(self, client: TestClient):
        """Test that homepage.css is loaded."""
        response = client.get("/")
        assert response.status_code == 200
        assert '/static/css/homepage.css' in response.text

    def test_logo_css_exists(self):
        """Test that logo CSS classes exist in stylesheet."""
        import os
        css_path = os.path.join('app', 'static', 'css', 'homepage.css')
        
        assert os.path.exists(css_path), "homepage.css file not found"
        
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for logo CSS classes
        assert '.brand-logo' in css_content, "brand-logo class not found in CSS"
        assert '.footer-logo' in css_content, "footer-logo class not found in CSS"
        assert '.footer-brand-header' in css_content, "footer-brand-header class not found in CSS"

    def test_logo_sizing_css(self):
        """Test that logo sizing is defined in CSS."""
        import os
        css_path = os.path.join('app', 'static', 'css', 'homepage.css')
        
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for width/height definitions
        assert 'width: 40px' in css_content or 'width:40px' in css_content, \
            "Navigation logo width not defined"
        assert 'width: 48px' in css_content or 'width:48px' in css_content, \
            "Footer logo width not defined"

    def test_responsive_logo_css(self):
        """Test that responsive logo sizing exists."""
        import os
        css_path = os.path.join('app', 'static', 'css', 'homepage.css')
        
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for mobile responsive sizing
        assert '@media' in css_content, "No media queries found"
        assert 'max-width: 768px' in css_content, "Mobile breakpoint not found"


class TestLogoFile:
    """Test suite for logo SVG file."""

    def test_favicon_svg_exists(self):
        """Test that favicon.svg file exists."""
        import os
        logo_path = os.path.join('app', 'static', 'images', 'favicon.svg')
        assert os.path.exists(logo_path), "favicon.svg file not found"

    def test_favicon_svg_valid(self):
        """Test that favicon.svg is valid SVG."""
        import os
        logo_path = os.path.join('app', 'static', 'images', 'favicon.svg')
        
        with open(logo_path, 'r') as f:
            svg_content = f.read()
        
        # Basic SVG validation
        assert '<svg' in svg_content, "Not a valid SVG file"
        assert 'xmlns' in svg_content, "Missing SVG namespace"
        assert 'viewBox' in svg_content, "Missing viewBox attribute"
        assert '</svg>' in svg_content, "SVG not properly closed"

    def test_favicon_svg_accessible(self, client: TestClient):
        """Test that favicon.svg is accessible via HTTP."""
        response = client.get("/static/images/favicon.svg")
        assert response.status_code == 200
        assert 'image/svg+xml' in response.headers.get('content-type', '').lower() or \
               'text/xml' in response.headers.get('content-type', '').lower() or \
               response.headers.get('content-type', '').lower() == ''


class TestBackwardCompatibility:
    """Test suite for backward compatibility."""

    def test_homepage_still_loads(self, client: TestClient):
        """Test that homepage still loads successfully."""
        response = client.get("/")
        assert response.status_code == 200

    def test_navigation_structure_intact(self, client: TestClient):
        """Test that navigation structure is intact."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Navigation should exist
        nav = soup.select_one('.homepage-nav')
        assert nav is not None
        
        # Nav container should exist
        nav_container = soup.select_one('.nav-container')
        assert nav_container is not None
        
        # Nav brand should exist
        nav_brand = soup.select_one('.nav-brand')
        assert nav_brand is not None

    def test_footer_structure_intact(self, client: TestClient):
        """Test that footer structure is intact."""
        response = client.get("/")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Footer should exist
        footer = soup.select_one('.homepage-footer')
        assert footer is not None
        
        # Footer container should exist
        footer_container = soup.select_one('.footer-container')
        assert footer_container is not None
        
        # Footer brand should exist
        footer_brand = soup.select_one('.footer-brand')
        assert footer_brand is not None

