"""
Docker Integration Tests

This module provides pytest integration for Docker build and container testing.
It wraps the automated test script (scripts/test-docker.sh) to allow running
Docker tests as part of the pytest test suite.

Usage:
    # Run all Docker tests
    pytest tests/test_docker_integration.py

    # Run only Docker tests (using marker)
    pytest -m docker

    # Skip slow tests (including Docker)
    pytest -m "not slow"

    # Run with verbose output
    pytest tests/test_docker_integration.py -v

Requirements:
    - Docker must be installed and running
    - Port 8080 must be available
    - ANTHROPIC_API_KEY environment variable (or will use test placeholder)

Note:
    These tests are marked as 'slow' and 'docker' because they:
    - Build a Docker image (can take 30-60 seconds)
    - Start and test a container
    - Run multiple endpoint tests
    Total execution time: ~2-3 minutes
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


# Get the repository root directory
REPO_ROOT = Path(__file__).parent.parent
TEST_SCRIPT = REPO_ROOT / "scripts" / "test-docker.sh"


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.integration
def test_docker_build_and_run():
    """
    Integration test for Docker build and container.
    
    This test runs the automated Docker test script which:
    1. Builds the Docker image
    2. Starts a container
    3. Tests all critical endpoints
    4. Verifies static files
    5. Checks logs for errors
    6. Tests clean shutdown
    
    The test passes if all Docker tests pass (exit code 0).
    """
    # Check if Docker is available
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")
    
    # Check if test script exists
    if not TEST_SCRIPT.exists():
        pytest.fail(f"Docker test script not found: {TEST_SCRIPT}")
    
    # Check if script is executable
    if not os.access(TEST_SCRIPT, os.X_OK):
        pytest.fail(f"Docker test script is not executable: {TEST_SCRIPT}")
    
    # Run the Docker test script
    result = subprocess.run(
        [str(TEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=300  # 5 minute timeout
    )
    
    # If the script failed, include its output in the assertion message
    if result.returncode != 0:
        error_msg = (
            f"Docker tests failed with exit code {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )
        pytest.fail(error_msg)
    
    # Test passed - optionally print summary
    print("\n" + "="*60)
    print("Docker Integration Tests - PASSED")
    print("="*60)
    if result.stdout:
        # Print last 20 lines of output (summary)
        lines = result.stdout.split('\n')
        summary_lines = lines[-20:] if len(lines) > 20 else lines
        print('\n'.join(summary_lines))


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.integration
def test_docker_image_exists():
    """
    Test that Docker image can be built successfully.
    
    This is a lighter test that only verifies the image builds,
    without running the full container test suite.
    """
    # Check if Docker is available
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")
    
    # Build the image
    result = subprocess.run(
        ["docker", "build", "-t", "lls-study-portal:test", "."],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180  # 3 minute timeout for build
    )
    
    assert result.returncode == 0, (
        f"Docker build failed:\n{result.stdout}\n{result.stderr}"
    )
    
    # Verify image exists
    result = subprocess.run(
        ["docker", "images", "-q", "lls-study-portal:test"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, "Failed to list Docker images"
    assert result.stdout.strip(), "Docker image not found after build"


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.integration
def test_dockerfile_syntax():
    """
    Test that Dockerfile has valid syntax.
    
    This is a quick smoke test that doesn't actually build the image,
    just validates the Dockerfile syntax.
    """
    dockerfile = REPO_ROOT / "Dockerfile"
    
    assert dockerfile.exists(), "Dockerfile not found"
    
    # Check if Docker is available
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not available or not running")
    
    # Validate Dockerfile syntax using docker build with --dry-run (if available)
    # Note: --dry-run is not available in all Docker versions, so we'll just
    # check that the file can be read and has basic structure
    
    content = dockerfile.read_text()
    
    # Basic syntax checks
    assert "FROM" in content, "Dockerfile missing FROM instruction"
    assert "WORKDIR" in content, "Dockerfile missing WORKDIR instruction"
    assert "COPY" in content or "ADD" in content, "Dockerfile missing COPY/ADD instruction"
    assert "CMD" in content or "ENTRYPOINT" in content, "Dockerfile missing CMD/ENTRYPOINT"
    
    # Check for health check (added in this PR)
    assert "HEALTHCHECK" in content, "Dockerfile missing HEALTHCHECK instruction"
    assert "curl" in content, "Dockerfile should use curl for health check"


if __name__ == "__main__":
    # Allow running this file directly with python
    sys.exit(pytest.main([__file__, "-v"]))

