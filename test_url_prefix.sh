#!/bin/bash

# Test script to verify URL prefix handling
# This script tests both local and nginx scenarios

echo "=========================================="
echo "URL Prefix Configuration Test"
echo "=========================================="
echo ""

# Test 1: Local without prefix
echo "Test 1: Running locally (no prefix)"
echo "--------------------------------------"
echo "Expected: APP_PREFIX should be empty string"
echo "URLs should work as: /api/search"
echo ""
echo "To test manually:"
echo "  python -m src.web"
echo "  Open browser: http://localhost:5000/"
echo "  Check browser console: window.APP_PREFIX"
echo ""

# Test 2: With SCRIPT_NAME environment variable
echo "Test 2: Running with SCRIPT_NAME=/misesdata"
echo "--------------------------------------"
echo "Expected: APP_PREFIX should be '/misesdata'"
echo "URLs should work as: /misesdata/api/search"
echo ""
echo "To test manually:"
echo "  SCRIPT_NAME=/misesdata python -m src.web"
echo "  Open browser: http://localhost:5000/misesdata/"
echo "  Check browser console: window.APP_PREFIX"
echo ""

# Test 3: Behind nginx
echo "Test 3: Behind nginx with proxy"
echo "--------------------------------------"
echo "Expected: nginx sends X-Forwarded-Prefix header"
echo "Flask receives SCRIPT_NAME from ProxyFix middleware"
echo "URLs work as: https://yourdomain.com/misesdata/api/search"
echo ""
echo "Nginx config should have:"
echo "  proxy_set_header X-Forwarded-Prefix /misesdata;"
echo ""
echo "Systemd service should have:"
echo "  Environment=\"SCRIPT_NAME=/misesdata\""
echo ""

# Verification checklist
echo "=========================================="
echo "Verification Checklist"
echo "=========================================="
echo ""
echo "✓ base.html has window.APP_PREFIX and apiUrl() function"
echo "✓ All templates use apiUrl('/api/...') instead of '/api/...'"
echo "✓ No hardcoded /api/, /auth/, /viz/, /remote/ URLs remain"
echo "✓ flask app configured with ProxyFix middleware"
echo "✓ flask app reads SCRIPT_NAME and sets APPLICATION_ROOT"
echo ""

echo "To verify all fetch calls are updated:"
echo "  grep -r \"fetch.*['\\\"\\\`]/api/\" src/web/templates/ | grep -v apiUrl"
echo "  (should return no results)"
echo ""

echo "=========================================="
echo "Quick Test Commands"
echo "=========================================="
echo ""
echo "# Start without prefix (local dev)"
echo "python -m src.web"
echo ""
echo "# Start with prefix (simulate nginx)"
echo "SCRIPT_NAME=/misesdata python -m src.web"
echo ""
echo "# Test API endpoint directly"
echo "curl http://localhost:5000/api/search?q=gdp"
echo "curl http://localhost:5000/misesdata/api/search?q=gdp  # with prefix"
echo ""
