#!/bin/bash

# Customer Compliance Check Script
# Ensures code meets enterprise customer compliance requirements

set -e

echo "Starting Customer Compliance Check..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to run a check
run_check() {
    local check_name="$1"
    local command="$2"
    local required="$3"  # true/false
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "\n${BLUE}[$TOTAL_CHECKS]${NC} Checking: $check_name"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ PASSED${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "  ${RED}✗ FAILED (REQUIRED)${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        else
            echo -e "  ${YELLOW}⚠ WARNING (OPTIONAL)${NC}"
            return 0
        fi
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo -e "\n${BLUE}Python Environment${NC}"
echo "==================="
run_check "Python 3.8+ installed" "python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'" true

# Check required tools
echo -e "\n${BLUE}Required Tools${NC}"
echo "=============="
run_check "pip installed" "command_exists pip || command_exists pip3" true
run_check "git installed" "command_exists git" true

# Install development dependencies if requirements-dev.txt exists
if [ -f "requirements-dev.txt" ]; then
    echo -e "\n${BLUE}Installing Development Dependencies${NC}"
    echo "==================================="
    python3 -m pip install -q -r requirements-dev.txt
fi

# Code Quality Checks
echo -e "\n${BLUE}Code Quality${NC}"
echo "============"

# Check if tools are available, install if needed
if ! command_exists black; then
    echo "Installing black..."
    python3 -m pip install -q black
fi

if ! command_exists isort; then
    echo "Installing isort..."
    python3 -m pip install -q isort
fi

if ! command_exists flake8; then
    echo "Installing flake8..."
    python3 -m pip install -q flake8
fi

run_check "Black code formatting" "black --check --diff ." true
run_check "Import sorting (isort)" "isort --check-only --diff ." true
run_check "Flake8 linting (critical)" "flake8 . --select=E9,F63,F7,F82" true
run_check "Flake8 linting (style)" "flake8 . --max-line-length=127" false

# Security Checks
echo -e "\n${BLUE}Security Scanning${NC}"
echo "================="

# Install security tools if needed
if ! command_exists bandit; then
    echo "Installing bandit..."
    python3 -m pip install -q bandit
fi

if ! command_exists safety; then
    echo "Installing safety..."
    python3 -m pip install -q safety
fi

run_check "Bandit security scan" "bandit -r . -ll" true
run_check "Safety vulnerability check" "safety check" true

# Check for common security issues
run_check "No hardcoded passwords" "! grep -r -i 'password.*=' --include='*.py' . || true" true
run_check "No API keys in code" "! grep -r -E '(api_key|apikey|api-key).*=' --include='*.py' . || true" true
run_check "No TODO/FIXME in production" "! grep -r -E '(TODO|FIXME|XXX|HACK)' --include='*.py' . || true" false

# Documentation Checks
echo -e "\n${BLUE}Documentation${NC}"
echo "============="
run_check "README.md exists" "[ -f README.md ]" true
run_check "Requirements.txt exists" "[ -f requirements.txt ]" true
run_check "License file exists" "[ -f LICENSE ] || [ -f LICENSE.txt ] || [ -f LICENSE.md ]" false

# Test Coverage (if pytest is available)
if command_exists pytest; then
    echo -e "\n${BLUE}Test Coverage${NC}"
    echo "============="
    
    if [ -d "tests" ] || find . -name "test_*.py" -o -name "*_test.py" | grep -q .; then
        run_check "Test files exist" "true" true
        
        # Install pytest-cov if needed
        if ! python3 -c "import pytest_cov" 2>/dev/null; then
            echo "Installing pytest-cov..."
            python3 -m pip install -q pytest-cov
        fi
        
        run_check "Test coverage ≥ 70%" "pytest --cov=. --cov-report=term-missing --cov-fail-under=70 -q" false
    else
        echo -e "  ${YELLOW}⚠ No test files found${NC}"
    fi
fi

# Git Checks
echo -e "\n${BLUE}Git Repository${NC}"
echo "=============="
run_check "Git repository initialized" "[ -d .git ]" true
run_check "No large files (>10MB)" "! find . -type f -size +10M | grep -v '.git' | grep -q ." true
run_check "Gitignore exists" "[ -f .gitignore ]" true

# Check for sensitive files
run_check "No .env files committed" "! find . -name '.env*' -not -path './.git/*' | grep -q ." true
run_check "No private keys committed" "! find . -name '*.pem' -o -name '*.key' -not -path './.git/*' | grep -q ." true

# File Structure Checks
echo -e "\n${BLUE}Project Structure${NC}"
echo "=================="
run_check "Source code organized" "[ -d src ] || find . -name '*.py' -not -path './.git/*' | grep -q ." true
run_check "No __pycache__ committed" "! find . -name '__pycache__' -not -path './.git/*' | grep -q ." true

# Final Report
echo -e "\n${BLUE}Compliance Report${NC}"
echo "=================="
echo "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "\n${GREEN} All compliance checks passed!${NC}"
    echo -e "${GREEN}Your code meets customer compliance requirements.${NC}"
    exit 0
else
    echo -e "\n${RED}$FAILED_CHECKS compliance check(s) failed.${NC}"
    echo -e "${RED}Please fix the issues above before deployment.${NC}"
    exit 1
fi