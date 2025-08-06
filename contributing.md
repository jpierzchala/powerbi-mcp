# Contributing to Power BI MCP Server

First off, thank you for considering contributing to Power BI MCP Server! It's people like you that make this tool better for everyone.

## Code of Conduct

By participating in this project, you are expected to uphold our values:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Include logs and error messages**
- **Describe the behavior you observed and expected**
- **Include your environment details** (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the proposed enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding style** used in the project
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass**
6. **Write a clear commit message**

## Development Setup

1. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/powerbi-mcp-server.git
   cd powerbi-mcp-server
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:
- Line length: 100 characters
- Use type hints for function parameters and returns
- Write docstrings for all public functions and classes

### Code Formatting

Use `black` for automatic code formatting:
```bash
black src/ tests/
```

### Linting

Use `flake8` for linting:
```bash
flake8 src/ tests/
```

### Type Checking

Use `mypy` for type checking:
```bash
mypy src/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_connector.py

# Run specific test
pytest tests/test_connector.py::test_connection
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source code structure
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies (Power BI, OpenAI)

Example test:
```python
import pytest
from unittest.mock import Mock, patch

def test_power_bi_connection():
    """Test successful Power BI connection"""
    with patch('pyadomd.Pyadomd') as mock_pyadomd:
        # Arrange
        mock_conn = Mock()
        mock_pyadomd.return_value.__enter__.return_value = mock_conn
        
        # Act
        connector = PowerBIConnector()
        result = connector.connect("endpoint", "tenant", "client", "secret", "dataset")
        
        # Assert
        assert result is True
        assert connector.connected is True
```

### Power BI DMV Query Limitations

When working with Power BI Dynamic Management Views (DMVs) through the `$SYSTEM.TMSCHEMA_*` tables, be aware of the following limitations imposed by the Data Mining parser:

- **No JOIN operations**: Cannot use INNER JOIN, LEFT JOIN, etc. between DMV tables
- **No GROUP BY**: Cannot aggregate data using GROUP BY clauses
- **No LIKE operator**: Cannot use pattern matching with LIKE
- **No CAST or CONVERT**: Cannot convert data types in queries
- **No IN clauses**: Cannot use `WHERE column IN (value1, value2, ...)`
- **Limited WHERE clauses**: Only basic equality and comparison operators are supported

**Example of valid DMV queries:**
```sql
-- Valid: Simple SELECT with WHERE
SELECT [Name], [Description] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = 'Sales'

-- Valid: SELECT all records
SELECT [FromTableID], [ToTableID] FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS
```

**Examples of invalid DMV queries:**
```sql
-- Invalid: JOIN not supported
SELECT t.[Name], r.[FromTableID] 
FROM $SYSTEM.TMSCHEMA_TABLES t 
JOIN $SYSTEM.TMSCHEMA_RELATIONSHIPS r ON t.[ID] = r.[FromTableID]

-- Invalid: GROUP BY not supported
SELECT [TableID], COUNT(*) FROM $SYSTEM.TMSCHEMA_COLUMNS GROUP BY [TableID]

-- Invalid: LIKE not supported
SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] LIKE 'Sales%'

-- Invalid: IN clause not supported
SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [ID] IN (1, 2, 3)
```

**Performance Optimization Strategies:**

Due to these limitations, relationship data retrieval requires multiple separate queries and post-processing in application code:

1. **Batch Fetching**: Get all tables, columns, and relationships in separate bulk queries
2. **In-Memory Mapping**: Build lookup dictionaries to map IDs to names
3. **Minimize Round Trips**: Fetch all required data upfront rather than making individual queries per table

This is why methods like `_get_all_relationships()` fetch all relationship data at once and then filter/map it in Python rather than using complex SQL queries.

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def execute_dax_query(self, dax_query: str) -> List[Dict[str, Any]]:
    """Execute a DAX query and return results.
    
    Args:
        dax_query: The DAX query to execute
        
    Returns:
        List of dictionaries containing query results
        
    Raises:
        ConnectionError: If not connected to Power BI
        QueryError: If the DAX query is invalid
    """
```

### README Updates

When adding new features, update the README:
- Add feature to the Features section
- Include usage examples
- Update configuration if needed

## Commit Messages

Use clear and meaningful commit messages:

- **feat**: New feature for the user
- **fix**: Bug fix for the user
- **docs**: Documentation only changes
- **style**: Formatting, missing semi-colons, etc
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **test**: Adding missing tests
- **chore**: Maintenance tasks

Examples:
```
feat: add support for calculated tables
fix: handle datetime serialization in DAX results
docs: update Power BI setup instructions
test: add tests for DataAnalyzer class
```

## Release Process

1. Update version in `src/server.py`
2. Update CHANGELOG.md
3. Create a pull request
4. After merge, create a GitHub release

## Getting Help

- Check the [documentation](docs/)
- Look at [existing issues](https://github.com/yourusername/powerbi-mcp-server/issues)
- Ask in discussions
- Contact maintainers

## Recognition

Contributors will be recognized in:
- The README.md file
- GitHub releases
- Project documentation

Thank you for contributing! 🎉
