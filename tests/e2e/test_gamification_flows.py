"""
End-to-End Tests for Gamification UI/UX Flows

Tests critical user flows including:
- Level up animation flow
- Badge earning flow
- XP gain flow
- Onboarding tour flow
- Shareable graphics generation flow
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time


class TestGamificationE2E:
    """End-to-end tests for gamification UI/UX features."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture(autouse=True)
    def setup(self, driver):
        """Navigate to the application before each test."""
        driver.get('http://localhost:8000')  # Adjust URL as needed
        # Clear localStorage to reset state
        driver.execute_script("localStorage.clear();")
        time.sleep(1)
    
    def test_level_up_animation_flow(self, driver):
        """Test level up animation displays correctly."""
        # Trigger level up event via JavaScript
        driver.execute_script("""
            document.dispatchEvent(new CustomEvent('gamification:levelup', {
                detail: {
                    newLevel: 5,
                    newLevelTitle: 'Summer Associate',
                    xpGained: 100
                }
            }));
        """)
        
        # Wait for modal to appear
        try:
            modal = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'level-up-modal'))
            )
            
            # Verify modal is visible
            assert modal.is_displayed(), "Level up modal should be visible"
            
            # Verify content is sanitized (no script tags)
            modal_html = modal.get_attribute('innerHTML')
            assert '<script>' not in modal_html.lower(), "Modal should not contain script tags"
            
            # Verify level number is displayed
            level_element = driver.find_element(By.CLASS_NAME, 'level-up-level')
            assert 'Level 5' in level_element.text, "Level number should be displayed"
            
            # Verify level title is displayed
            rank_element = driver.find_element(By.CLASS_NAME, 'level-up-rank')
            assert 'Summer Associate' in rank_element.text, "Level title should be displayed"
            
            # Click close button
            close_button = driver.find_element(By.CLASS_NAME, 'level-up-close')
            close_button.click()
            
            # Wait for modal to disappear
            WebDriverWait(driver, 3).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'level-up-modal'))
            )
            
        except TimeoutException:
            pytest.fail("Level up modal did not appear within timeout")
    
    def test_xss_prevention_in_level_up(self, driver):
        """Test that XSS attempts are prevented in level up animation."""
        # Attempt XSS via level title
        driver.execute_script("""
            document.dispatchEvent(new CustomEvent('gamification:levelup', {
                detail: {
                    newLevel: 5,
                    newLevelTitle: '<script>alert("XSS")</script>',
                    xpGained: 100
                }
            }));
        """)
        
        # Wait for modal
        try:
            modal = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'level-up-modal'))
            )
            
            # Verify script tag is escaped
            rank_element = driver.find_element(By.CLASS_NAME, 'level-up-rank')
            rank_html = rank_element.get_attribute('innerHTML')
            
            # Should contain escaped HTML, not actual script tag
            assert '&lt;script&gt;' in rank_html or '&lt;' in rank_html, \
                "Script tags should be escaped"
            assert '<script>' not in rank_html, "Script tags should not be executable"
            
        except TimeoutException:
            pytest.fail("Level up modal did not appear")
    
    def test_badge_earned_animation_flow(self, driver):
        """Test badge earned animation displays correctly."""
        driver.execute_script("""
            document.dispatchEvent(new CustomEvent('gamification:badgeearned', {
                detail: {
                    badgeName: 'Night Owl',
                    badgeIcon: '🦉',
                    badgeTier: 'Bronze',
                    badgeDescription: 'Complete a quiz late at night'
                }
            }));
        """)
        
        try:
            modal = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'badge-earned-modal'))
            )
            
            assert modal.is_displayed(), "Badge modal should be visible"
            
            # Verify badge name
            name_element = driver.find_element(By.CLASS_NAME, 'badge-earned-name')
            assert 'Night Owl' in name_element.text
            
            # Verify tier
            tier_element = driver.find_element(By.CLASS_NAME, 'badge-earned-tier')
            assert 'Bronze' in tier_element.text
            assert 'bronze' in tier_element.get_attribute('class')
            
            # Verify share button exists
            share_button = driver.find_element(By.CLASS_NAME, 'badge-earned-share')
            assert share_button.is_displayed()
            
        except TimeoutException:
            pytest.fail("Badge modal did not appear")
    
    def test_xp_gain_animation_flow(self, driver):
        """Test XP gain animation displays correctly."""
        driver.execute_script("""
            document.dispatchEvent(new CustomEvent('gamification:xpgain', {
                detail: {
                    xpGained: 25,
                    activityType: 'quiz_hard_passed'
                }
            }));
        """)
        
        try:
            indicator = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'xp-gain-indicator'))
            )
            
            # Verify XP amount is displayed
            amount_element = driver.find_element(By.CLASS_NAME, 'xp-gain-amount')
            assert '+25 XP' in amount_element.text
            
        except TimeoutException:
            pytest.fail("XP gain indicator did not appear")
    
    def test_onboarding_tour_flow(self, driver):
        """Test onboarding tour displays and navigates correctly."""
        # Clear onboarding completion flag
        driver.execute_script("localStorage.removeItem('onboarding_completed');")
        driver.execute_script("localStorage.setItem('visit_count', '0');")
        
        # Trigger tour manually
        driver.execute_script("if (window.onboardingTour) window.onboardingTour.start();")
        
        try:
            # Wait for overlay
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'onboarding-overlay'))
            )
            assert 'active' in overlay.get_attribute('class')
            
            # Wait for tooltip
            tooltip = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'onboarding-tooltip'))
            )
            
            # Verify first step content
            title = driver.find_element(By.CLASS_NAME, 'onboarding-tooltip-title')
            assert 'XP' in title.text or 'Level' in title.text
            
            # Click Next button
            next_button = driver.find_element(By.CLASS_NAME, 'onboarding-btn-next')
            next_button.click()
            
            time.sleep(0.5)
            
            # Verify we moved to next step
            progress = driver.find_element(By.CLASS_NAME, 'onboarding-progress')
            assert 'Step 2' in progress.text
            
            # Click Skip button
            skip_button = driver.find_element(By.CLASS_NAME, 'onboarding-btn-skip')
            skip_button.click()
            
            # Handle confirmation dialog
            alert = driver.switch_to.alert
            alert.accept()
            
            # Verify tour is closed
            WebDriverWait(driver, 3).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'onboarding-overlay'))
            )
            
        except TimeoutException:
            pytest.fail("Onboarding tour did not appear or navigate correctly")
    
    def test_sound_control_toggle(self, driver):
        """Test sound control toggle works correctly."""
        try:
            # Wait for sound control to appear
            control = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'sound-control'))
            )
            
            # Get initial state
            initial_icon = driver.find_element(By.CLASS_NAME, 'sound-control-icon').text
            
            # Click to toggle
            control.click()
            
            time.sleep(0.5)
            
            # Verify icon changed
            new_icon = driver.find_element(By.CLASS_NAME, 'sound-control-icon').text
            assert initial_icon != new_icon, "Sound icon should change on toggle"
            
            # Verify localStorage was updated
            sound_enabled = driver.execute_script("return localStorage.getItem('gamification_sound');")
            assert sound_enabled in ['true', 'false'], "Sound preference should be saved"
            
        except TimeoutException:
            pytest.fail("Sound control did not appear")
    
    def test_keyboard_navigation(self, driver):
        """Test keyboard navigation works for accessibility."""
        # Trigger level up modal
        driver.execute_script("""
            document.dispatchEvent(new CustomEvent('gamification:levelup', {
                detail: { newLevel: 5, newLevelTitle: 'Test', xpGained: 100 }
            }));
        """)
        
        try:
            # Wait for modal
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'level-up-modal'))
            )
            
            # Find close button
            close_button = driver.find_element(By.CLASS_NAME, 'level-up-close')
            
            # Tab to button and press Enter
            close_button.send_keys(Keys.RETURN)
            
            # Verify modal closes
            WebDriverWait(driver, 3).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'level-up-modal'))
            )
            
        except TimeoutException:
            pytest.fail("Keyboard navigation did not work")
    
    def test_api_error_handling(self, driver):
        """Test that API errors are handled gracefully."""
        # Mock API to return error
        driver.execute_script("""
            window.fetch = function() {
                return Promise.resolve({
                    ok: false,
                    status: 500,
                    json: () => Promise.resolve({})
                });
            };
        """)
        
        # Trigger update that calls API
        driver.execute_script("""
            if (window.progressVisualizations) {
                window.progressVisualizations.updateHeaderCircularProgress();
            }
        """)
        
        # Wait a moment for error handling
        time.sleep(1)
        
        # Verify no uncaught errors (page should still be functional)
        logs = driver.get_log('browser')
        critical_errors = [log for log in logs if log['level'] == 'SEVERE' and 'Uncaught' in log['message']]
        
        assert len(critical_errors) == 0, "Should handle API errors gracefully without uncaught exceptions"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

