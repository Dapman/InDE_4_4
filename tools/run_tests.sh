#!/bin/bash
# InDE Build Harness - Test Runner
# Runs all tests with proper Python path configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "InDE v3.5.x Test Runner"
echo "============================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Set Python path
export PYTHONPATH="$PROJECT_DIR/app:$PROJECT_DIR:$PYTHONPATH"

# Change to project directory
cd "$PROJECT_DIR"

# Check for pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Install with: pip install pytest${NC}"
    exit 1
fi

# Parse arguments
VERBOSE=""
COVERAGE=""
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        --coverage)
            COVERAGE="--cov=app --cov-report=term-missing"
            shift
            ;;
        -k)
            SPECIFIC_TEST="-k $2"
            shift 2
            ;;
        *)
            SPECIFIC_TEST="$1"
            shift
            ;;
    esac
done

echo "Project directory: $PROJECT_DIR"
echo "Python path includes: app/"
echo ""

# Run tests in order
TOTAL_PASSED=0
TOTAL_FAILED=0

run_test_suite() {
    local suite_name=$1
    local test_path=$2

    if [ -f "$test_path" ] || [ -d "$test_path" ]; then
        echo -e "${YELLOW}[$suite_name]${NC}"
        echo "Running: pytest $test_path $VERBOSE $COVERAGE $SPECIFIC_TEST"

        if pytest "$test_path" $VERBOSE $COVERAGE $SPECIFIC_TEST; then
            echo -e "${GREEN}PASSED${NC}"
            ((TOTAL_PASSED++))
        else
            echo -e "${RED}FAILED${NC}"
            ((TOTAL_FAILED++))
        fi
        echo ""
    else
        echo -e "${YELLOW}[$suite_name]${NC} - Skipped (not found: $test_path)"
        echo ""
    fi
}

# Run test suites
run_test_suite "v3.4 Session 1" "tests/test_v34_session1.py"
run_test_suite "v3.4 Session 2" "tests/test_v34_session2.py"
run_test_suite "Build Verification" "app/tests/test_build_verification.py"
run_test_suite "Backward Compatibility" "app/tests/test_backward_compat.py"
run_test_suite "Events v3.2" "app/tests/test_events_v32.py"
run_test_suite "IKF Tests" "app/tests/test_ikf.py"
run_test_suite "Intelligence Tests" "app/tests/test_intelligence.py"
run_test_suite "Portfolio Tests" "app/tests/test_portfolio.py"
run_test_suite "TIM Tests" "app/tests/test_tim.py"
run_test_suite "SILR Enrichment" "app/tests/test_silr_enrichment.py"
run_test_suite "Teams v3.3" "app/tests/test_v33_teams.py"
run_test_suite "IKF Service" "ikf-service/tests/"

# Summary
echo "============================================================"
echo "Test Summary"
echo "============================================================"
echo -e "Passed: ${GREEN}$TOTAL_PASSED${NC}"
echo -e "Failed: ${RED}$TOTAL_FAILED${NC}"
echo ""

if [ $TOTAL_FAILED -gt 0 ]; then
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
