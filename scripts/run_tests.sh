#!/bin/bash

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Header
echo ""
echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}        Prior Authorization API - Test Suite Runner${NC}"
echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if server is running
check_server() {
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Server not detected. Starting server...${NC}"
        echo -e "${YELLOW}Please run 'uv run fastapi dev' in another terminal${NC}"
        return 1
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BOLD}${PURPLE}────────────────────────────────────────────────────────────────${NC}"
    echo -e "${BOLD}${PURPLE}  $1${NC}"
    echo -e "${BOLD}${PURPLE}────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

# Function to print test header
print_test() {
    echo -e "${BOLD}${BLUE}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 1. Integration Tests
print_section "1️⃣  Integration Tests (pytest)"
print_test "Running pytest with detailed output..."
echo ""
uv run pytest tests/test_answers.py -v -s
PYTEST_EXIT=$?

if [ $PYTEST_EXIT -eq 0 ]; then
    print_success "Integration tests passed!"
else
    print_error "Integration tests failed with exit code $PYTEST_EXIT"
fi

# 2. Evaluation Pipeline
print_section "2️⃣  Evaluation Pipeline (Pydantic AI)"
print_test "Running 9 test cases with LLM-as-Judge evaluation..."
echo ""
uv run python tests/eval_pydantic_ai.py
EVAL_EXIT=$?

if [ $EVAL_EXIT -eq 0 ]; then
    print_success "Evaluation pipeline completed!"
else
    print_error "Evaluation pipeline failed with exit code $EVAL_EXIT"
fi

# 3. API Examples (if server is running)
print_section "3️⃣  API Examples (Live Server)"

if check_server; then
    echo ""
    
    # Simple Example
    print_test "Testing Simple Example..."
    curl -s -X POST "http://localhost:8000/answers" \
        -H "Content-Type: application/json" \
        -d '{
            "patient": {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1970-01-01",
                "gender": "Male",
                "prescription": {
                    "medication": "Zepbound",
                    "dosage": "5 mg",
                    "frequency": "once weekly",
                    "duration": "ongoing"
                },
                "visit_notes": ["Patient has BMI of 35 kg/m²."]
            },
            "question_set": {
                "name": "Simple Test",
                "questions": [
                    {
                        "type": "text",
                        "key": "bmi",
                        "content": "What is the patient'\''s BMI?"
                    }
                ]
            }
        }' | python -m json.tool
    
    if [ $? -eq 0 ]; then
        print_success "Simple example test passed!"
    else
        print_error "Simple example test failed!"
    fi
    
    echo ""
    
    # Actor-Critic Demo
    print_test "Testing Actor-Critic Demo (ambiguous data)..."
    curl -s -X POST "http://localhost:8000/answers" \
        -H "Content-Type: application/json" \
        -d @sample_data/actor_critic_example.json | python -m json.tool
    
    if [ $? -eq 0 ]; then
        print_success "Actor-Critic demo test passed!"
        echo -e "${YELLOW}Look for '[Refined via Actor-Critic]' in the reasoning above!${NC}"
    else
        print_error "Actor-Critic demo test failed!"
    fi
    
    echo ""
    
    # Detailed Example
    print_test "Testing Detailed Example..."
    curl -s -X POST "http://localhost:8000/answers" \
        -H "Content-Type: application/json" \
        -d @sample_data/example_request.json | python -m json.tool | head -n 50
    
    if [ $? -eq 0 ]; then
        print_success "Detailed example test passed!"
        echo -e "${YELLOW}(Output truncated for readability)${NC}"
    else
        print_error "Detailed example test failed!"
    fi
else
    print_error "Skipping live server tests - server not running"
fi

# 4. Code Quality
print_section "4️⃣  Code Quality (Linting & Formatting)"
print_test "Running pre-commit checks..."
echo ""
uv run pre-commit run --all-files
LINT_EXIT=$?

if [ $LINT_EXIT -eq 0 ]; then
    print_success "All linting checks passed!"
else
    print_error "Linting checks failed with exit code $LINT_EXIT"
fi

# Summary
print_section "📊 Test Summary"

TOTAL_TESTS=4
PASSED_TESTS=0

[ $PYTEST_EXIT -eq 0 ] && ((PASSED_TESTS++)) && echo -e "${GREEN}✓ Integration Tests${NC}" || echo -e "${RED}✗ Integration Tests${NC}"
[ $EVAL_EXIT -eq 0 ] && ((PASSED_TESTS++)) && echo -e "${GREEN}✓ Evaluation Pipeline${NC}" || echo -e "${RED}✗ Evaluation Pipeline${NC}"
check_server > /dev/null 2>&1 && ((PASSED_TESTS++)) && echo -e "${GREEN}✓ API Examples${NC}" || echo -e "${YELLOW}⊘ API Examples (Skipped - Server Not Running)${NC}"
[ $LINT_EXIT -eq 0 ] && ((PASSED_TESTS++)) && echo -e "${GREEN}✓ Code Quality${NC}" || echo -e "${RED}✗ Code Quality${NC}"

echo ""
echo -e "${BOLD}Result: $PASSED_TESTS/$TOTAL_TESTS test suites passed${NC}"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${BOLD}${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${BOLD}${YELLOW}⚠️  Some tests failed or were skipped${NC}"
    exit 1
fi

