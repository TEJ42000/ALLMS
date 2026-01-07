#!/bin/bash
# Docker Build and Container Test Script for LLS Study Portal
# This script automates the testing process outlined in Issue #8

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="lls-study-portal"
IMAGE_TAG="test"
CONTAINER_NAME="lls-study-portal-test"
PORT=8080
TEST_ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-sk-ant-test-key-placeholder}"
STARTUP_WAIT="${STARTUP_WAIT:-5}"  # Configurable startup wait time in seconds

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Function to cleanup
cleanup() {
    print_header "Cleaning Up"
    
    # Stop and remove container if it exists
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        print_info "Stopping container..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        print_info "Removing container..."
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        print_success "Container cleaned up"
    fi
    
    # Optionally remove image (commented out by default)
    # if docker images | grep -q "$IMAGE_NAME.*$IMAGE_TAG"; then
    #     print_info "Removing image..."
    #     docker rmi $IMAGE_NAME:$IMAGE_TAG 2>/dev/null || true
    # fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Function to wait for container to be healthy
wait_for_healthy() {
    local max_attempts=30
    local attempt=1
    
    print_info "Waiting for container to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "none")

        if [ "$health_status" = "healthy" ]; then
            print_success "Container is healthy!"
            return 0
        elif [ "$health_status" = "unhealthy" ]; then
            print_error "Container is unhealthy!"
            docker logs "$CONTAINER_NAME" --tail 50
            return 1
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_warning "Health check timeout - container may not have HEALTHCHECK configured"
    print_info "Checking if container is running..."

    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container is running (health check not available)"
        return 0
    else
        print_error "Container is not running"
        return 1
    fi
}

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local path=$2
    local expected_status=$3
    local description=$4
    local data=$5
    
    print_info "Testing: $description"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:$PORT$path" 2>/dev/null || echo "000")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:$PORT$path" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "000")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "$expected_status" ]; then
        print_success "$description - Status: $status_code"
        return 0
    else
        print_error "$description - Expected: $expected_status, Got: $status_code"
        return 1
    fi
}

# Main test execution
main() {
    print_header "Docker Build and Container Test"
    print_info "Image: $IMAGE_NAME:$IMAGE_TAG"
    print_info "Container: $CONTAINER_NAME"
    print_info "Port: $PORT"
    
    # Step 1: Build Docker image
    print_header "Step 1: Building Docker Image"
    print_info "Running: docker build -t $IMAGE_NAME:$IMAGE_TAG ."
    
    if docker build -t $IMAGE_NAME:$IMAGE_TAG . ; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
    
    # Verify image exists
    if docker images | grep -q "$IMAGE_NAME.*$IMAGE_TAG"; then
        print_success "Image verified in docker images list"
        docker images | grep "$IMAGE_NAME.*$IMAGE_TAG"
    else
        print_error "Image not found after build"
        exit 1
    fi
    
    # Step 2: Run container
    print_header "Step 2: Running Container"
    print_info "Starting container with environment variables..."
    
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$PORT":8080 \
        -e ANTHROPIC_API_KEY="$TEST_ANTHROPIC_KEY" \
        -e AUTH_ENABLED=false \
        -e ENV=development \
        "$IMAGE_NAME:$IMAGE_TAG"

    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container started successfully"
    else
        print_error "Container failed to start"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    
    # Wait for container to be ready
    print_header "Step 3: Waiting for Application to Start"
    print_info "Waiting ${STARTUP_WAIT}s for container to initialize..."
    sleep "$STARTUP_WAIT"
    
    # Check container logs
    print_info "Container logs:"
    docker logs "$CONTAINER_NAME" --tail 20
    
    # Wait for health check
    if ! wait_for_healthy; then
        print_error "Container failed health check"
        exit 1
    fi
    
    # Step 3: Test endpoints
    print_header "Step 4: Testing Endpoints"
    
    test_count=0
    pass_count=0
    
    # Test 1: Health endpoint
    ((test_count++))
    if test_endpoint "GET" "/health" "200" "Health check endpoint"; then
        ((pass_count++))
    fi
    
    # Test 2: Main page
    ((test_count++))
    if test_endpoint "GET" "/" "200" "Main landing page"; then
        ((pass_count++))
    fi
    
    # Test 3: API docs
    ((test_count++))
    if test_endpoint "GET" "/api/docs" "200" "Swagger UI documentation"; then
        ((pass_count++))
    fi
    
    # Test 4: Static files (check if CSS loads)
    ((test_count++))
    print_info "Testing: Static CSS file"
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/static/css/styles.css" | grep -q "200"; then
        print_success "Static CSS file - Status: 200"
        ((pass_count++))
    else
        print_error "Static CSS file failed to load"
    fi
    
    # Test 5: AI Tutor endpoint (should fail without proper auth, but endpoint should exist)
    ((test_count++))
    test_data='{"message":"Test question","conversation_history":[]}'
    if test_endpoint "POST" "/api/tutor/chat" "200" "AI Tutor chat endpoint" "$test_data"; then
        ((pass_count++))
    fi
    
    # Step 4: Check container logs for errors
    print_header "Step 5: Checking Container Logs"
    print_info "Checking for errors in logs..."

    if docker logs "$CONTAINER_NAME" 2>&1 | grep -iE "ERROR:|Exception:|Failed to" | grep -v "ANTHROPIC_API_KEY" | grep -v "0 errors"; then
        print_warning "Found some errors in logs (see above)"
    else
        print_success "No critical errors found in logs"
    fi

    # Step 5: Test container stop
    print_header "Step 6: Testing Container Shutdown"
    print_info "Stopping container..."

    if docker stop "$CONTAINER_NAME"; then
        print_success "Container stopped cleanly"
    else
        print_error "Container failed to stop cleanly"
    fi
    
    # Final summary
    print_header "Test Summary"
    echo -e "${BLUE}Total Tests: $test_count${NC}"
    echo -e "${GREEN}Passed: $pass_count${NC}"
    echo -e "${RED}Failed: $((test_count - pass_count))${NC}"
    
    if [ $pass_count -eq $test_count ]; then
        print_success "All tests passed! ✨"
        echo -e "\n${GREEN}Docker build and container are working correctly!${NC}\n"
        exit 0
    else
        print_error "Some tests failed"
        echo -e "\n${RED}Please review the failures above${NC}\n"
        exit 1
    fi
}

# Run main function
main

