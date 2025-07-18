#!/bin/bash
# Pre-commit hook for code quality checks
# To install: ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit

set -e

echo "🔍 Running pre-commit checks..."

# Check if we're in the right directory
if [ ! -f "src/server.py" ]; then
    echo "❌ Error: Run from project root directory"
    exit 1
fi

# Check if required tools are installed
if ! command -v black &> /dev/null || ! command -v isort &> /dev/null || ! command -v flake8 &> /dev/null; then
    echo "📦 Installing required tools..."
    pip install black isort flake8
fi

# Run formatting checks
echo "🎨 Checking code formatting..."
if ! black --check --diff src/ tests/ --line-length=120; then
    echo "❌ Code formatting issues found. Run: black src/ tests/ --line-length=120"
    exit 1
fi

if ! isort --check-only --diff src/ tests/ --profile=black; then
    echo "❌ Import organization issues found. Run: isort src/ tests/ --profile=black"
    exit 1
fi

# Run linting
echo "🔍 Running linting checks..."
if ! flake8 src/ tests/ --config=.flake8; then
    echo "❌ Linting issues found. Fix them and try again."
    exit 1
fi

echo "✅ All pre-commit checks passed!"
