"""
Unit Tests for Flashcard Viewer Component

Tests the FlashcardViewer JavaScript component functionality.
This uses pytest with selenium for browser automation testing.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


@pytest.fixture(scope="module")
def driver():
    """Setup Chrome WebDriver for testing."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode for CI
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture
def flashcard_page(driver):
    """Navigate to flashcards page before each test."""
    driver.get('http://localhost:8000/flashcards')
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard-sets')))
    return driver


class TestFlashcardSetSelection:
    """Test flashcard set selection functionality."""

    def test_flashcard_sets_display(self, flashcard_page):
        """Test that flashcard sets are displayed."""
        sets = flashcard_page.find_elements(By.CLASS_NAME, 'flashcard-set-card')
        assert len(sets) == 3, "Should display 3 flashcard sets"

    def test_set_has_title_and_description(self, flashcard_page):
        """Test that each set has title and description."""
        first_set = flashcard_page.find_element(By.CLASS_NAME, 'flashcard-set-card')
        title = first_set.find_element(By.TAG_NAME, 'h3')
        description = first_set.find_element(By.TAG_NAME, 'p')
        
        assert title.text != "", "Set should have a title"
        assert description.text != "", "Set should have a description"

    def test_start_studying_button(self, flashcard_page):
        """Test that clicking Start Studying loads the viewer."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()
        
        wait = WebDriverWait(flashcard_page, 10)
        viewer = wait.until(EC.presence_of_element_located((By.ID, 'flashcard-viewer')))
        
        assert viewer.is_displayed(), "Flashcard viewer should be displayed"


class TestFlashcardViewer:
    """Test flashcard viewer functionality."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()
        
        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))
        
        self.driver = flashcard_page

    def test_flashcard_displays(self):
        """Test that flashcard is displayed."""
        flashcard = self.driver.find_element(By.CLASS_NAME, 'flashcard')
        assert flashcard.is_displayed(), "Flashcard should be displayed"

    def test_card_has_front_content(self):
        """Test that card front has content."""
        front = self.driver.find_element(By.CLASS_NAME, 'flashcard-front')
        content = front.find_element(By.CLASS_NAME, 'card-content')
        
        assert content.text != "", "Card front should have content"

    def test_card_flip_on_click(self):
        """Test that card flips when clicked."""
        flashcard = self.driver.find_element(By.CLASS_NAME, 'flashcard')
        
        # Check initial state (not flipped)
        assert 'flipped' not in flashcard.get_attribute('class')
        
        # Click to flip
        flashcard.click()
        time.sleep(0.7)  # Wait for animation
        
        # Check flipped state
        assert 'flipped' in flashcard.get_attribute('class')

    def test_flip_button(self):
        """Test that flip button works."""
        btn_flip = self.driver.find_element(By.ID, 'btn-flip')
        flashcard = self.driver.find_element(By.CLASS_NAME, 'flashcard')
        
        # Click flip button
        btn_flip.click()
        time.sleep(0.7)
        
        assert 'flipped' in flashcard.get_attribute('class')

    def test_next_button(self):
        """Test that next button navigates to next card."""
        # Get initial card content
        front = self.driver.find_element(By.CLASS_NAME, 'flashcard-front')
        initial_content = front.find_element(By.CLASS_NAME, 'card-content').text
        
        # Click next
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        
        # Get new card content
        front = self.driver.find_element(By.CLASS_NAME, 'flashcard-front')
        new_content = front.find_element(By.CLASS_NAME, 'card-content').text
        
        assert initial_content != new_content, "Card content should change"

    def test_previous_button_disabled_at_start(self):
        """Test that previous button is disabled on first card."""
        btn_previous = self.driver.find_element(By.ID, 'btn-previous')
        assert btn_previous.get_attribute('disabled') is not None

    def test_previous_button_enabled_after_next(self):
        """Test that previous button is enabled after navigating forward."""
        # Navigate to next card
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        
        # Check previous button is enabled
        btn_previous = self.driver.find_element(By.ID, 'btn-previous')
        assert btn_previous.get_attribute('disabled') is None

    def test_progress_bar_updates(self):
        """Test that progress bar updates as user navigates."""
        progress_fill = self.driver.find_element(By.CLASS_NAME, 'progress-fill')
        initial_width = progress_fill.value_of_css_property('width')
        
        # Navigate to next card
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        
        new_width = progress_fill.value_of_css_property('width')
        assert new_width != initial_width, "Progress bar should update"

    def test_card_counter_updates(self):
        """Test that card counter updates."""
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 1 of' in progress_text.text
        
        # Navigate to next
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 2 of' in progress_text.text


class TestKeyboardShortcuts:
    """Test keyboard shortcut functionality."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()
        
        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))
        
        self.driver = flashcard_page

    def test_space_key_flips_card(self):
        """Test that space key flips the card."""
        flashcard = self.driver.find_element(By.CLASS_NAME, 'flashcard')
        
        # Press space
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.SPACE).perform()
        time.sleep(0.7)
        
        assert 'flipped' in flashcard.get_attribute('class')

    def test_arrow_right_navigates_next(self):
        """Test that right arrow navigates to next card."""
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 1 of' in progress_text.text
        
        # Press right arrow
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ARROW_RIGHT).perform()
        time.sleep(0.3)
        
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 2 of' in progress_text.text

    def test_arrow_left_navigates_previous(self):
        """Test that left arrow navigates to previous card."""
        # First go to card 2
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        
        # Press left arrow
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ARROW_LEFT).perform()
        time.sleep(0.3)
        
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 1 of' in progress_text.text


class TestCardActions:
    """Test card action functionality (star, known, shuffle, restart)."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()
        
        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))
        
        self.driver = flashcard_page

    def test_star_button_toggles(self):
        """Test that star button toggles active state."""
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        
        # Check initial state
        assert 'active' not in btn_star.get_attribute('class')
        
        # Click to star
        btn_star.click()
        time.sleep(0.3)
        
        # Check active state
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        assert 'active' in btn_star.get_attribute('class')

    def test_known_button_toggles(self):
        """Test that known button toggles active state."""
        btn_know = self.driver.find_element(By.ID, 'btn-know')
        
        # Check initial state
        assert 'active' not in btn_know.get_attribute('class')
        
        # Click to mark as known
        btn_know.click()
        time.sleep(0.3)
        
        # Check active state
        btn_know = self.driver.find_element(By.ID, 'btn-know')
        assert 'active' in btn_know.get_attribute('class')

    def test_restart_button(self):
        """Test that restart button resets to first card."""
        # Navigate to card 3
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)
        btn_next.click()
        time.sleep(0.3)
        
        # Click restart
        btn_restart = self.driver.find_element(By.ID, 'btn-restart')
        btn_restart.click()
        time.sleep(0.3)
        
        # Check we're back at card 1
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card 1 of' in progress_text.text

    def test_shuffle_button_shows_confirmation(self):
        """Test that shuffle button shows confirmation dialog."""
        # Star a card first
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        btn_star.click()
        time.sleep(0.3)
        
        # Click shuffle - should show alert
        btn_shuffle = self.driver.find_element(By.ID, 'btn-shuffle')
        btn_shuffle.click()
        
        # Wait for alert
        wait = WebDriverWait(self.driver, 3)
        alert = wait.until(EC.alert_is_present())
        
        assert alert is not None, "Shuffle should show confirmation dialog"
        alert.dismiss()  # Cancel the shuffle


class TestStatistics:
    """Test statistics tracking."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()
        
        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))
        
        self.driver = flashcard_page

    def test_reviewed_count_increases(self):
        """Test that reviewed count increases when card is flipped."""
        # Get initial reviewed count
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        reviewed_stat = stats[0]
        initial_count = int(reviewed_stat.find_element(By.CLASS_NAME, 'stat-value').text)
        
        # Flip card
        flashcard = self.driver.find_element(By.CLASS_NAME, 'flashcard')
        flashcard.click()
        time.sleep(0.7)
        
        # Check reviewed count increased
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        reviewed_stat = stats[0]
        new_count = int(reviewed_stat.find_element(By.CLASS_NAME, 'stat-value').text)
        
        assert new_count == initial_count + 1

    def test_known_count_increases(self):
        """Test that known count increases when card is marked as known."""
        # Get initial known count
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        known_stat = stats[1]
        initial_count = int(known_stat.find_element(By.CLASS_NAME, 'stat-value').text)

        # Mark as known
        btn_know = self.driver.find_element(By.ID, 'btn-know')
        btn_know.click()
        time.sleep(0.3)

        # Check known count increased
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        known_stat = stats[1]
        new_count = int(known_stat.find_element(By.CLASS_NAME, 'stat-value').text)

        assert new_count == initial_count + 1


class TestMemoryLeaks:
    """Test memory leak prevention."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()

        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))

        self.driver = flashcard_page

    def test_navigation_cleanup(self):
        """Test that navigation properly cleans up event listeners."""
        # Navigate multiple times rapidly
        for _ in range(10):
            btn_next = self.driver.find_element(By.ID, 'btn-next')
            btn_next.click()
            time.sleep(0.1)

        # Check that we can still navigate (no errors from duplicate listeners)
        btn_previous = self.driver.find_element(By.ID, 'btn-previous')
        btn_previous.click()
        time.sleep(0.3)

        # Should still be functional
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card' in progress_text.text

    def test_rapid_keyboard_navigation(self):
        """Test that rapid keyboard navigation doesn't cause race conditions."""
        # Rapidly press arrow keys
        actions = ActionChains(self.driver)
        for _ in range(5):
            actions.send_keys(Keys.ARROW_RIGHT).perform()
            time.sleep(0.05)  # Very rapid

        time.sleep(0.5)  # Wait for all navigation to complete

        # Should still be functional
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        assert 'Card' in progress_text.text


class TestNumericValidation:
    """Test numeric value validation."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()

        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))

        self.driver = flashcard_page

    def test_progress_percentage_valid(self):
        """Test that progress percentage is between 0 and 100."""
        progress_fill = self.driver.find_element(By.CLASS_NAME, 'progress-fill')
        width = progress_fill.value_of_css_property('width')

        # Extract numeric value
        parent_width = self.driver.find_element(By.CLASS_NAME, 'progress-bar').size['width']
        fill_width = progress_fill.size['width']
        percentage = (fill_width / parent_width) * 100 if parent_width > 0 else 0

        assert 0 <= percentage <= 100, f"Progress percentage {percentage} out of range"

    def test_stat_values_non_negative(self):
        """Test that all stat values are non-negative."""
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat-value')

        for stat in stats:
            value = int(stat.text.replace('%', ''))
            assert value >= 0, f"Stat value {value} is negative"

    def test_card_counter_valid(self):
        """Test that card counter shows valid numbers."""
        progress_text = self.driver.find_element(By.CLASS_NAME, 'progress-text')
        text = progress_text.text

        # Extract numbers from "Card X of Y"
        import re
        match = re.search(r'Card (\d+) of (\d+)', text)
        assert match, "Card counter format invalid"

        current = int(match.group(1))
        total = int(match.group(2))

        assert current >= 1, "Current card number should be at least 1"
        assert current <= total, "Current card number should not exceed total"
        assert total >= 1, "Total cards should be at least 1"


class TestStarredCardsValidation:
    """Test starred cards index validation."""

    @pytest.fixture(autouse=True)
    def setup_viewer(self, flashcard_page):
        """Start a flashcard set before each test."""
        btn_study = flashcard_page.find_element(By.CLASS_NAME, 'btn-study')
        btn_study.click()

        wait = WebDriverWait(flashcard_page, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'flashcard')))

        self.driver = flashcard_page

    def test_starred_cards_persist_after_navigation(self):
        """Test that starred cards remain valid after navigation."""
        # Star first card
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        btn_star.click()
        time.sleep(0.3)

        # Navigate to next card
        btn_next = self.driver.find_element(By.ID, 'btn-next')
        btn_next.click()
        time.sleep(0.3)

        # Star second card
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        btn_star.click()
        time.sleep(0.3)

        # Check starred count
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        starred_stat = stats[2]
        starred_count = int(starred_stat.find_element(By.CLASS_NAME, 'stat-value').text)

        assert starred_count == 2, "Should have 2 starred cards"

    def test_shuffle_clears_starred_cards(self):
        """Test that shuffle clears starred cards to prevent index corruption."""
        # Star a card
        btn_star = self.driver.find_element(By.ID, 'btn-star')
        btn_star.click()
        time.sleep(0.3)

        # Click shuffle and accept confirmation
        btn_shuffle = self.driver.find_element(By.ID, 'btn-shuffle')
        btn_shuffle.click()

        # Accept alert
        wait = WebDriverWait(self.driver, 3)
        alert = wait.until(EC.alert_is_present())
        alert.accept()
        time.sleep(0.5)

        # Check starred count is 0
        stats = self.driver.find_elements(By.CLASS_NAME, 'stat')
        starred_stat = stats[2]
        starred_count = int(starred_stat.find_element(By.CLASS_NAME, 'stat-value').text)

        assert starred_count == 0, "Starred cards should be cleared after shuffle"

