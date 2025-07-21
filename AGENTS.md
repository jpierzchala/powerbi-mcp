# Agent Instructions

When modifying code in this repository:

## Environment Consistency Requirements

This repository supports three distinct environments that must be kept consistent:

### 1. **Local Development Environment (Windows)**
- Windows with Visual Studio Code
- SSMS/ADOMD.NET libraries
- `.env` file for configuration
- Manual package installation

### 2. **Docker Environment (Linux)**
- Linux container with Python 3.11-slim
- Uses `install_dotnet_adomd.sh --system`
- Environment variables via `docker-entrypoint.sh`
- Systemwide .NET installation (`/usr/share/dotnet`)

### 3. **Copilot Agent Environment (Linux)**
- Linux container/codespace
- Uses `install_dotnet_adomd.sh --user`
- Environment variables via secrets (no .env file)
- User-local .NET installation (`$HOME/.local/dotnet`)

### **Consistency Rules:**
- **All environments must use the same `install_dotnet_adomd.sh` script** (with appropriate `--system` or `--user` flag)
- **All environments must use `pip install -r requirements.txt`** for Python dependencies
- **All environments must support the same core functionality** (MCP server, Power BI connectivity, testing)
- **When adding new dependencies:** Update `requirements.txt` and verify compatibility across all environments
- **When modifying installation scripts:** Test in Docker environment first, then update copilot-setup-steps.yml
- **Environment-specific differences are acceptable only for:**
  - Installation paths (system vs user)
  - Configuration delivery method (.env vs secrets)
  - Platform-specific workarounds

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
- **MANDATORY: Run integration tests to verify functionality actually works:**
  ```bash
  # Run integration tests with real Power BI connection
  python run_integration_tests.py --yes
  ```
- **Run formatting checks as part of testing workflow:**
  ```bash
  # Full local validation (same as CI)
  black --check --diff src/ tests/ --line-length=120
  isort --check-only --diff src/ tests/ --profile=black
  flake8 src/ tests/ --config=.flake8
  pytest tests/ -k "not test_integration" -v
  ```

## Integration Testing Requirements
- **CRITICAL: You MUST run integration tests before submitting any changes**
- Unit tests are not sufficient - they only test mocked functionality
- Integration tests verify that your changes work with real Power BI datasets
- If you implement features that depend on ADOMD.NET or Power BI APIs:
  1. First run unit tests to verify basic logic
  2. **Then ALWAYS run integration tests** to ensure real-world functionality
  3. If integration tests fail, fix the issues before submitting
  4. Integration test failures indicate your implementation has real bugs
- **Never submit changes without running integration tests first**

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
