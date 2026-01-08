# Testing Setup Guide

**Date:** 2026-01-08  
**Component:** Flashcards UI Testing  
**Status:** HIGH - Required for CI/CD

---

## Overview

This document describes the testing setup for the Flashcards UI Component, including Selenium/ChromeDriver dependencies and CI/CD configuration.

---

## Dependencies

### Python Packages

```bash
# Install testing dependencies
pip install pytest==7.4.3
pip install selenium==4.15.2
pip install pytest-selenium==4.0.1
pip install webdriver-manager==4.0.1
```

### System Dependencies

#### ChromeDriver

**Option 1: Automatic (Recommended)**
```python
# Using webdriver-manager (already in tests)
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
```

**Option 2: Manual Installation**

**macOS:**
```bash
brew install chromedriver
```

**Linux (Ubuntu/Debian):**
```bash
# Install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f

# Install ChromeDriver
sudo apt-get install chromium-chromedriver
```

**Windows:**
1. Download ChromeDriver from https://chromedriver.chromium.org/
2. Add to PATH or place in project directory

---

## CI/CD Configuration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Run Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install Chrome
      run: |
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
        sudo apt-get update
        sudo apt-get install -y google-chrome-stable
    
    - name: Install ChromeDriver
      run: |
        sudo apt-get install -y chromium-chromedriver
        sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest selenium pytest-selenium webdriver-manager
    
    - name: Run unit tests
      run: |
        pytest tests/test_flashcard_route.py -v
    
    - name: Start application
      run: |
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        sleep 5
    
    - name: Run E2E tests
      run: |
        pytest tests/test_flashcard_viewer.py -v --headless
```

---

## Running Tests Locally

### Unit Tests Only

```bash
# Fast - no browser required
pytest tests/test_flashcard_route.py -v
```

### E2E Tests (Selenium)

```bash
# Start the application first
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, run E2E tests
pytest tests/test_flashcard_viewer.py -v
```

### All Tests

```bash
# Start application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Run all tests
pytest tests/ -v

# Stop application
pkill -f uvicorn
```

---

## Test Configuration

### pytest.ini

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
markers =
    unit: Unit tests (no browser required)
    e2e: End-to-end tests (requires browser)
    slow: Slow tests (may take >5 seconds)
```

### Running Specific Test Types

```bash
# Unit tests only
pytest -m unit

# E2E tests only
pytest -m e2e

# Skip slow tests
pytest -m "not slow"
```

---

## Headless Mode

For CI/CD, tests run in headless mode (no visible browser).

### Enable Headless in Tests

```python
@pytest.fixture(scope="module")
def driver():
    """Setup Chrome WebDriver for testing."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()
```

---

## Troubleshooting

### ChromeDriver Version Mismatch

**Error:** "This version of ChromeDriver only supports Chrome version X"

**Solution:**
```bash
# Use webdriver-manager to auto-download correct version
pip install webdriver-manager

# Or manually download matching version
# Check Chrome version: chrome://version
# Download from: https://chromedriver.chromium.org/downloads
```

### Connection Refused

**Error:** "selenium.common.exceptions.WebDriverException: Message: unknown error: net::ERR_CONNECTION_REFUSED"

**Solution:**
```bash
# Ensure application is running
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check if port 8000 is available
lsof -i :8000
```

### Timeout Errors

**Error:** "selenium.common.exceptions.TimeoutException"

**Solution:**
```python
# Increase wait time
wait = WebDriverWait(driver, 30)  # Increase from 10 to 30 seconds

# Or use explicit waits
from selenium.webdriver.support import expected_conditions as EC
wait.until(EC.presence_of_element_located((By.ID, 'element-id')))
```

### Headless Mode Issues

**Error:** Tests pass locally but fail in CI

**Solution:**
```python
# Add more headless-specific options
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-extensions')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
```

---

## Docker Setup (Optional)

### Dockerfile for Testing

```dockerfile
FROM python:3.10-slim

# Install Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable chromium-chromedriver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pytest selenium pytest-selenium webdriver-manager

# Copy application
WORKDIR /app
COPY . .

# Run tests
CMD ["pytest", "tests/", "-v"]
```

### Run Tests in Docker

```bash
# Build image
docker build -t flashcards-tests .

# Run tests
docker run --rm flashcards-tests
```

---

## Performance Optimization

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto  # Auto-detect CPU cores
pytest tests/ -n 4     # Use 4 workers
```

### Test Fixtures Optimization

```python
# Use module-scoped fixtures for expensive setup
@pytest.fixture(scope="module")
def driver():
    # Setup once per module
    driver = webdriver.Chrome()
    yield driver
    driver.quit()
```

---

## Continuous Integration Best Practices

1. **Cache Dependencies**
   - Cache pip packages
   - Cache ChromeDriver downloads

2. **Fail Fast**
   - Run unit tests before E2E tests
   - Stop on first failure in CI

3. **Retry Flaky Tests**
   ```bash
   pip install pytest-rerunfailures
   pytest --reruns 3 --reruns-delay 1
   ```

4. **Generate Reports**
   ```bash
   pip install pytest-html
   pytest --html=report.html --self-contained-html
   ```

---

## Required Files

### requirements-test.txt

```
pytest==7.4.3
selenium==4.15.2
pytest-selenium==4.0.1
webdriver-manager==4.0.1
pytest-xdist==3.5.0
pytest-rerunfailures==12.0
pytest-html==4.1.1
```

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

---

**Status:** Documentation Complete  
**Last Updated:** 2026-01-08  
**Maintained By:** Development Team

