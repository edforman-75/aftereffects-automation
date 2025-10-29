#!/bin/bash

# Test Runner Script for After Effects Automation
# Runs the complete test suite with coverage reporting

set -e  # Exit on error

echo "========================================="
echo "After Effects Automation - Test Suite"
echo "========================================="
echo ""

# Set PYTHONPATH to project root
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):$PYTHONPATH"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing dependencies..."
    pip3 install --break-system-packages -r requirements-dev.txt
fi

# Run tests with different verbosity levels based on argument
case "$1" in
    "quick")
        echo "Running quick tests (unit tests only)..."
        pytest tests/unit/ -v --tb=short
        ;;
    "integration")
        echo "Running integration tests..."
        pytest tests/integration/ -v --tb=short
        ;;
    "coverage")
        echo "Running all tests with coverage report..."
        pytest tests/ -v --cov=services --cov=core --cov-report=html --cov-report=term-missing
        echo ""
        echo "========================================="
        echo "Coverage report generated"
        echo "========================================="
        echo "HTML report: htmlcov/index.html"
        echo "Open with: open htmlcov/index.html (Mac) or xdg-open htmlcov/index.html (Linux)"
        ;;
    "verbose")
        echo "Running all tests with verbose output..."
        pytest tests/ -vv --tb=long
        ;;
    "markers")
        echo "Listing available test markers..."
        pytest --markers
        ;;
    "unit")
        echo "Running unit tests with coverage..."
        pytest tests/unit/ -v --cov=services --cov=core --cov-report=term-missing
        ;;
    *)
        echo "Running full test suite with coverage..."
        pytest tests/ -v --cov=services --cov=core --cov-report=html --cov-report=term-missing
        echo ""
        echo "========================================="
        echo "Test Results Summary"
        echo "========================================="
        echo ""
        echo "Coverage report: htmlcov/index.html"
        echo ""
        echo "Usage:"
        echo "  ./run_tests.sh              - Run all tests with coverage"
        echo "  ./run_tests.sh quick        - Run unit tests only (fast)"
        echo "  ./run_tests.sh integration  - Run integration tests only"
        echo "  ./run_tests.sh unit         - Run unit tests with coverage"
        echo "  ./run_tests.sh coverage     - Run all tests with detailed coverage"
        echo "  ./run_tests.sh verbose      - Run all tests with verbose output"
        echo "  ./run_tests.sh markers      - List available test markers"
        ;;
esac

exit 0
