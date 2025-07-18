# Agent Instructions

When modifying code in this repository:

## Environment Setup
- Recreate the environment described in the `Dockerfile` (install the .NET runtime and ADOMD.NET library) so tests mimic the container as closely as possible.

## Code Quality Requirements
- **ALWAYS run code formatting before committing changes:**
  ```bash
  # Auto-format code with black
  black src/ tests/ --line-length=120
  
  # Organize imports with isort
  isort src/ tests/ --profile=black
  
  # Check for linting issues
  flake8 src/ tests/ --config=.flake8
  ```

## Testing Requirements
- Always run `pytest -q` after changes.
- For every new or modified feature, add or update tests to cover the change.
- **Run formatting checks as part of testing workflow:**
  ```bash
  # Full local validation (same as CI)
  black --check --diff src/ tests/ --line-length=120
  isort --check-only --diff src/ tests/ --profile=black
  flake8 src/ tests/ --config=.flake8
  pytest tests/ -k "not test_integration" -v
  ```

## Why This Matters
- GitHub Actions will fail if code is not properly formatted
- Consistent formatting improves code readability and maintainability
- Automated checks prevent style issues from reaching production
- Following these steps ensures CI/CD pipeline success

## Quick Validation Command
```bash
# One-liner to check everything locally
black src/ tests/ --line-length=120 && isort src/ tests/ --profile=black && flake8 src/ tests/ --config=.flake8 && echo "✅ Code quality checks passed!"
```
