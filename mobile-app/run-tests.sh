#!/bin/bash

# iOS Medication App - Test Runner
# This script runs automated tests and provides instructions for manual testing

set -e

echo "=================================="
echo "iOS Medication App - Test Suite"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from mobile-app directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with AWS credentials"
    echo "See .env.example for template"
    exit 1
fi

echo "✅ Environment check passed"
echo ""

# Run automated tests
echo "Running automated E2E tests..."
echo "=================================="
node test-e2e.js

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All automated tests passed!"
    echo ""
    echo "=================================="
    echo "Next Steps: Manual Testing"
    echo "=================================="
    echo ""
    echo "1. Start the Expo app:"
    echo "   npm start"
    echo ""
    echo "2. Open iOS Simulator:"
    echo "   Press 'i' in the Expo terminal"
    echo ""
    echo "3. Follow the manual test guide:"
    echo "   See MANUAL_TEST_GUIDE.md"
    echo ""
    echo "4. Review test results:"
    echo "   See E2E_TEST_RESULTS.md"
    echo ""
    echo "=================================="
    echo "Current Database State"
    echo "=================================="
    echo ""
    echo "Slot 1: E2E Test Medicine (88 pills)"
    echo "Slot 2: Aspirin (29 pills)"
    echo "Slot 3: Prozac (15 pills)"
    echo ""
    echo "All slots: Bottles removed (in_holder=false)"
    echo ""
else
    echo ""
    echo "❌ Some automated tests failed"
    echo "Check the output above for details"
    exit 1
fi
