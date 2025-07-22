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

### **CRITICAL: Full Test Suite Validation**
**🚨 MANDATORY: Before completing any task, ALL tests must pass. No exceptions.**

1. **Final Validation is REQUIRED:**
   ```bash
   # Complete test suite - ALL must pass
   pytest -v
   ```

2. **Never skip failing tests** - If tests fail, they must be fixed, not removed
   - Failing tests indicate broken functionality
   - Only remove tests with explicit approval from user/operator
   - Document reason for any test removal in commit message

3. **Test Execution Order** (layered approach):
   ```bash
   # 1. Unit tests (fast, isolated, mocked)
   pytest tests/unit/ -v
   
   # 2. Local tests (require server startup)
   pytest tests/local/ -v
   
   # 3. Integration tests (require external services)
   pytest tests/integration/ -v
   ```

### **Test Development Guidelines**
- Always run `pytest -q` after changes
- For every new or modified feature, add or update tests to cover the change
- **Maintain test isolation** - tests must not depend on each other
- **Use appropriate test markers:**
  - `@pytest.mark.unit` for unit tests
  - `@pytest.mark.local` for local server tests  
  - `@pytest.mark.integration` for integration tests

### **When Tests Fail**
1. **DO NOT COMMIT** until all tests pass
2. **DO NOT DELETE** failing tests without approval
3. **Investigate and fix** the root cause
4. If unsure about test removal, ask: "Should I remove test X because of reason Y?"

### **Code Quality Integration**
- **Run formatting checks as part of testing workflow:**
  ```bash
  # Full local validation (same as CI)
  black --check --diff src/ tests/ --line-length=120
  isort --check-only --diff src/ tests/ --profile=black
  flake8 src/ tests/ --config=.flake8
  
  # Run all test layers
  pytest tests/unit/ -v --tb=short
  pytest tests/local/ -v --tb=short  
  pytest tests/integration/ -v --tb=short
  ```

## Why This Matters
- GitHub Actions will fail if code is not properly formatted
- Consistent formatting improves code readability and maintainability
- Automated checks prevent style issues from reaching production
- Following these steps ensures CI/CD pipeline success

## Quick Validation Commands
```bash
# Code quality and unit tests (fast)
black src/ tests/ --line-length=120 && isort src/ tests/ --profile=black && flake8 src/ tests/ --config=.flake8 && pytest tests/unit/ -v && echo "✅ Code quality and unit tests passed!"

# Full validation including all test layers (comprehensive)
black src/ tests/ --line-length=120 && isort src/ tests/ --profile=black && flake8 src/ tests/ --config=.flake8 && pytest -v && echo "🎉 ALL TESTS PASSED - Ready to commit!"
```
