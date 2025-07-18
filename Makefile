# Power BI MCP Server - Make commands
.PHONY: help test test-unit test-integration install clean lint format format-check quality-check

# Default target
help:
	@echo "Power BI MCP Server - Available Commands:"
	@echo ""
	@echo "  install           Install dependencies"
	@echo "  test             Run all tests (unit only by default)"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests (requires configuration)"
	@echo "  lint             Run code linting"
	@echo "  format           Format code with black and isort"
	@echo "  format-check     Check if code is properly formatted"
	@echo "  quality-check    Run all quality checks (format, lint, test)"
	@echo "  clean            Clean cache and temporary files"
	@echo "  run              Run the server in development mode"
	@echo ""
	@echo "Integration Tests:"
	@echo "  1. Copy .env.example to .env"
	@echo "  2. Set ENABLE_INTEGRATION_TESTS=true"
	@echo "  3. Configure TEST_* variables"
	@echo "  4. Run: make test-integration"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install flake8 black isort

# Run unit tests only
test-unit:
	python -m pytest tests/ -k "not test_integration" -v

# Run all tests (unit + integration if enabled)
test:
	python -m pytest tests/ -v

# Run integration tests with interactive confirmation
test-integration:
	python run_integration_tests.py

# Run integration tests without confirmation (for CI/CD)
test-integration-ci:
	python run_integration_tests.py --yes

# Run code linting
lint:
	flake8 src/ tests/ --config=.flake8

# Format code automatically
format:
	black src/ tests/ --line-length=120
	isort src/ tests/ --profile=black

# Check if code is properly formatted (CI-style check)
format-check:
	black --check --diff src/ tests/ --line-length=120
	isort --check-only --diff src/ tests/ --profile=black

# Run all quality checks (same as CI pipeline)
quality-check: format-check lint
	@echo "✅ All quality checks passed!"

# Complete validation (format, lint, test)
validate: format-check lint test-unit
	@echo "✅ Full validation completed successfully!"

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Run the server in development mode
run:
	python src/server.py

# Quick connection test
quickstart:
	python quickstart.py

# Check integration test configuration
check-integration-config:
	@echo "Integration Test Configuration Status:"
	@echo "====================================="
	@python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ENABLE_INTEGRATION_TESTS:', os.getenv('ENABLE_INTEGRATION_TESTS', 'false')); print('TEST_XMLA_ENDPOINT:', 'Configured' if os.getenv('TEST_XMLA_ENDPOINT') else 'Not configured'); print('TEST_TENANT_ID:', 'Configured' if os.getenv('TEST_TENANT_ID') else 'Not configured'); print('OPENAI_API_KEY:', 'Configured' if os.getenv('OPENAI_API_KEY') else 'Not configured')"
