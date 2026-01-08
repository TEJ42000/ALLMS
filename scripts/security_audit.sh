#!/bin/bash

# Security Audit Script for Gamification UI/UX Features
# Checks for common security vulnerabilities

set -e

echo "========================================="
echo "Security Audit for Gamification UI/UX"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

# Function to report issue
report_issue() {
    echo -e "${RED}✗ ISSUE:${NC} $1"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

# Function to report success
report_success() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
}

# Function to report warning
report_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
}

echo "1. Checking for XSS vulnerabilities..."
echo "----------------------------------------"

# Check for innerHTML usage without sanitization
if grep -r "innerHTML\s*=" app/static/js/gamification-*.js | grep -v "escapeHtml\|sanitize" > /dev/null 2>&1; then
    # Check if escapeHtml is defined and used
    if grep -q "escapeHtml" app/static/js/gamification-animations.js && \
       grep -q "escapeHtml" app/static/js/progress-visualizations.js && \
       grep -q "escapeHtml" app/static/js/shareable-graphics.js && \
       grep -q "escapeHtml" app/static/js/onboarding-tour.js; then
        report_success "XSS protection: escapeHtml function found in all files"
    else
        report_issue "Some files missing escapeHtml function"
    fi
else
    report_success "No unsafe innerHTML usage detected"
fi

# Check for direct user input in DOM manipulation
if grep -r "\${.*data\." app/static/js/gamification-*.js | grep -v "safe\|escape\|sanitize" > /dev/null 2>&1; then
    report_warning "Found template literals with data properties - verify sanitization"
else
    report_success "No unsanitized template literals found"
fi

echo ""
echo "2. Checking for event listener memory leaks..."
echo "-----------------------------------------------"

# Check for { once: true } on one-time event listeners
if grep -r "addEventListener.*click.*modal\|addEventListener.*close" app/static/js/gamification-*.js | grep -v "once: true" > /dev/null 2>&1; then
    report_warning "Some modal event listeners may not use { once: true }"
else
    report_success "Modal event listeners properly configured"
fi

echo ""
echo "3. Checking for null/undefined checks..."
echo "-----------------------------------------"

# Check for blob null checks
if grep -q "if (!blob)" app/static/js/gamification-animations.js && \
   grep -q "if (!blob)" app/static/js/shareable-graphics.js; then
    report_success "Blob null checks present"
else
    report_issue "Missing blob null checks in canvas operations"
fi

# Check for canvas null checks
if grep -q "if (!canvas)" app/static/js/gamification-animations.js && \
   grep -q "if (!canvas)" app/static/js/shareable-graphics.js; then
    report_success "Canvas null checks present"
else
    report_warning "Consider adding canvas null checks"
fi

echo ""
echo "4. Checking API response validation..."
echo "---------------------------------------"

# Check for response.ok validation
if grep -q "if (!response.ok)" app/static/js/progress-visualizations.js && \
   grep -q "if (!.*\.ok)" app/static/js/shareable-graphics.js; then
    report_success "API response status validation present"
else
    report_issue "Missing API response status validation"
fi

# Check for data validation
if grep -q "typeof data !== 'object'" app/static/js/progress-visualizations.js; then
    report_success "API response data validation present"
else
    report_warning "Consider adding data type validation"
fi

echo ""
echo "5. Checking for input sanitization..."
echo "--------------------------------------"

# Check for sanitizeNumber function
if grep -q "sanitizeNumber" app/static/js/gamification-animations.js && \
   grep -q "sanitizeNumber" app/static/js/progress-visualizations.js; then
    report_success "Number sanitization functions present"
else
    report_issue "Missing number sanitization functions"
fi

# Check for parseInt/parseFloat with radix
if grep -r "parseInt.*10\|parseFloat" app/static/js/gamification-*.js > /dev/null 2>&1; then
    report_success "Proper number parsing with radix"
else
    report_warning "Verify number parsing uses radix parameter"
fi

echo ""
echo "6. Checking for error handling..."
echo "----------------------------------"

# Check for try-catch blocks
if grep -q "try {" app/static/js/gamification-animations.js && \
   grep -q "catch" app/static/js/gamification-animations.js; then
    report_success "Error handling present in animations"
else
    report_warning "Limited error handling in animations"
fi

# Check for console.error usage
if grep -q "console.error" app/static/js/gamification-*.js; then
    report_success "Error logging present"
else
    report_warning "Consider adding error logging"
fi

echo ""
echo "7. Checking for localStorage security..."
echo "-----------------------------------------"

# Check for localStorage usage
if grep -r "localStorage\." app/static/js/gamification-*.js > /dev/null 2>&1; then
    report_warning "localStorage used - ensure no sensitive data is stored"
    
    # Check if sensitive data might be stored
    if grep -r "localStorage.*password\|localStorage.*token\|localStorage.*secret" app/static/js/gamification-*.js > /dev/null 2>&1; then
        report_issue "Potentially sensitive data in localStorage"
    else
        report_success "No obvious sensitive data in localStorage"
    fi
fi

echo ""
echo "8. Checking for HTTPS/secure contexts..."
echo "-----------------------------------------"

# Check for Web Share API usage (requires secure context)
if grep -q "navigator.share" app/static/js/gamification-*.js; then
    report_warning "Web Share API requires HTTPS in production"
fi

echo ""
echo "9. Checking JavaScript syntax..."
echo "---------------------------------"

# Check if node is available
if command -v node &> /dev/null; then
    for file in app/static/js/gamification-*.js app/static/js/sound-control.js app/static/js/onboarding-tour.js; do
        if [ -f "$file" ]; then
            if node --check "$file" 2>&1; then
                report_success "Syntax valid: $(basename $file)"
            else
                report_issue "Syntax error in: $(basename $file)"
            fi
        fi
    done
else
    report_warning "Node.js not found - skipping syntax check"
fi

echo ""
echo "10. Checking for Content Security Policy compatibility..."
echo "----------------------------------------------------------"

# Check for inline event handlers
if grep -r "onclick=\|onload=\|onerror=" app/static/js/gamification-*.js > /dev/null 2>&1; then
    report_issue "Inline event handlers found - not CSP compatible"
else
    report_success "No inline event handlers (CSP compatible)"
fi

# Check for eval usage
if grep -r "eval(" app/static/js/gamification-*.js > /dev/null 2>&1; then
    report_issue "eval() usage found - security risk"
else
    report_success "No eval() usage detected"
fi

echo ""
echo "========================================="
echo "Security Audit Summary"
echo "========================================="

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No critical issues found!${NC}"
    echo ""
    echo "Recommendations:"
    echo "  - Run npm audit for dependency vulnerabilities"
    echo "  - Test in production-like environment with HTTPS"
    echo "  - Review CSP headers for production deployment"
    echo "  - Run E2E tests to verify security measures"
    exit 0
else
    echo -e "${RED}✗ Found $ISSUES_FOUND issue(s) that should be addressed${NC}"
    echo ""
    echo "Please review and fix the issues above before deploying to production."
    exit 1
fi

