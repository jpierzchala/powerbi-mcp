# Windows Setup Guide for Power BI MCP Integration Tests

This guide helps you set up integration tests on Windows systems.

## Prerequisites

- Windows 10/11
- Python 3.8+
- .NET 8.0+ Runtime
- Power BI Pro/Premium account
- Azure AD tenant with Service Principal

## Step-by-Step Setup

### 1. Install Required Software

#### Install .NET Runtime
```powershell
# Download and install .NET 8.0 Runtime from Microsoft
# Or use winget:
winget install Microsoft.DotNet.Runtime.8
```

#### Install SQL Server Management Studio (SSMS)
SSMS includes ADOMD.NET libraries required for Power BI connectivity:

1. Download SSMS from [Microsoft](https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms)
2. Install with default options
3. Restart your computer after installation

### 2. Setup Python Environment

```powershell
# Clone the repository
git clone https://github.com/jpierzchala/powerbi-mcp.git
cd powerbi-mcp

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify ADOMD.NET Installation

```powershell
# Test if ADOMD.NET is available
python -c "
import sys
sys.path.insert(0, 'src')
try:
    from server import PowerBIConnector
    connector = PowerBIConnector()
    connector._check_pyadomd()
    print('✅ ADOMD.NET is available')
except Exception as e:
    print(f'❌ ADOMD.NET issue: {e}')
"
```

**If you get an error about System.Configuration.ConfigurationManager:**

#### Option A: Install via NuGet (Advanced)
```powershell
# Create a temporary .NET project to install dependencies
mkdir temp-deps
cd temp-deps
dotnet new console
dotnet add package System.Configuration.ConfigurationManager
dotnet add package Microsoft.AnalysisServices.AdomdClient.NetCore.retail.amd64
dotnet restore

# Copy the packages to your Python environment
# (This is complex - Option B recommended)
```

#### Option B: Use Docker (Easier)
```powershell
# Build Docker image (includes all dependencies)
docker build -t powerbi-mcp .

# Test with Docker
docker run --rm powerbi-mcp python -c "from src.server import PowerBIConnector; print('✅ ADOMD.NET works in Docker')"
```

### 4. Configure Azure AD Service Principal

#### Create Service Principal
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Name: `PowerBI-MCP-Integration-Tests`
5. Click **Register**

#### Get Credentials
1. **Tenant ID**: Azure AD → Overview → Tenant ID
2. **Client ID**: Your app registration → Overview → Application (client) ID
3. **Client Secret**: Your app registration → Certificates & secrets → New client secret

#### Grant Power BI Access
1. Go to [Power BI Portal](https://app.powerbi.com)
2. Open your test workspace
3. Click **Settings** → **Access**
4. Add your Service Principal as **Member** or **Admin**

### 5. Enable XMLA Endpoint

#### For Premium Workspaces
1. Power BI Admin Portal → Tenant settings
2. Enable **XMLA Endpoint** → **Read Write**
3. Apply to specific security groups or entire organization

#### For Pro Workspaces
1. Workspace Settings → **Advanced**
2. Enable **XMLA Endpoint** (if available)

### 6. Create Test Dataset

Create a simple dataset for testing:

#### Option A: Upload Sample Data
1. Create `test-data.csv`:
   ```csv
   Date,Product,Category,Amount,Quantity
   2024-01-01,Product A,Electronics,1000,10
   2024-01-02,Product B,Clothing,750,15
   2024-01-03,Product C,Electronics,1200,8
   ```

2. Upload to Power BI and publish to your test workspace

#### Option B: Use Existing Dataset
- Ensure it has at least one table with data
- Note the exact table and column names

### 7. Configure Environment

Create `.env` file in project root:

```bash
# Enable integration tests
ENABLE_INTEGRATION_TESTS=true

# Power BI Test Configuration
TEST_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/YourTestWorkspace
TEST_TENANT_ID=your-tenant-id-here
TEST_CLIENT_ID=your-client-id-here
TEST_CLIENT_SECRET=your-client-secret-here
TEST_INITIAL_CATALOG=YourTestDatasetName

# Test Validation (adjust to your dataset)
TEST_EXPECTED_TABLE=Table1
TEST_EXPECTED_COLUMN=Amount
TEST_DAX_QUERY=EVALUATE TOPN(1, Table1)
TEST_MIN_TABLES_COUNT=1

# Optional: OpenAI for AI features
OPENAI_API_KEY=your-openai-key-here
```

### 8. Run Integration Tests

```powershell
# Interactive mode (recommended for first run)
python run_integration_tests.py

# Direct pytest execution
python -m pytest tests/test_integration.py -v

# Run specific test categories
python -m pytest tests/test_integration.py::TestPowerBIIntegration -v
```

## Troubleshooting

### Common Issues

#### Issue: "Could not load file or assembly System.Configuration.ConfigurationManager"

**Solution 1 - Use Docker:**
```powershell
docker build -t powerbi-mcp .
docker run --rm \
  -e ENABLE_INTEGRATION_TESTS=true \
  -e TEST_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/YourTestWorkspace \
  -e TEST_TENANT_ID=your-tenant-id \
  -e TEST_CLIENT_ID=your-client-id \
  -e TEST_CLIENT_SECRET=your-client-secret \
  -e TEST_INITIAL_CATALOG=YourTestDatasetName \
  -e TEST_EXPECTED_TABLE=Table1 \
  -e TEST_EXPECTED_COLUMN=Amount \
  -e OPENAI_API_KEY=your-openai-key \
  powerbi-mcp python run_integration_tests.py --yes
```

**Note**: Docker containers do not use `.env` files. Pass all configuration via environment variables as shown above.

**Solution 2 - Install Framework ADOMD.NET:**
1. Download and install [SQL Server 2022 Feature Pack](https://www.microsoft.com/en-us/download/details.aspx?id=104781)
2. Install `Microsoft® SQL Server® 2022 Analysis Management Objects`
3. Install `Microsoft® SQL Server® 2022 ADOMD.NET`

#### Issue: "Authentication failed"

**Check:**
1. Credentials are correct (no extra spaces)
2. Service Principal has workspace access
3. XMLA endpoint is enabled
4. Try connecting with Power BI Desktop first to verify endpoint

#### Issue: "Dataset not found"

**Check:**
1. Dataset name is exact match (case-sensitive)
2. Dataset is published (not just saved)
3. Workspace name in XMLA endpoint is correct
4. Service Principal has access to the workspace

#### Issue: "Tests are skipped"

This usually means:
- `ENABLE_INTEGRATION_TESTS` is not set to `true`
- Required environment variables are missing
- ADOMD.NET dependencies are not available

### Advanced Diagnostics

#### Check .NET Installation
```powershell
dotnet --list-runtimes
# Should show Microsoft.NETCore.App 8.0.x
```

#### Check Python Environment
```powershell
python --version
pip list | findstr -E "(pytest|dotenv|openai|pyadomd|pythonnet)"
```

#### Test Power BI Connection
```powershell
# Quick connection test
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Check configuration
print('XMLA Endpoint:', os.getenv('TEST_XMLA_ENDPOINT', 'Not configured'))
print('Dataset:', os.getenv('TEST_INITIAL_CATALOG', 'Not configured'))
print('Integration tests:', os.getenv('ENABLE_INTEGRATION_TESTS', 'false'))
"
```

## Performance Tips

### Optimize Test Execution
1. **Use small test datasets** (< 1000 rows)
2. **Limit number of tables** in test workspace
3. **Use simple DAX queries** for validation
4. **Run tests during off-peak hours**

### CI/CD Considerations
- **Don't run integration tests on every commit**
- **Use dedicated test workspace** 
- **Set up Service Principal with minimal permissions**
- **Consider cost implications** of frequent API calls

## Next Steps

Once setup is complete:

1. **Validate basic connectivity:**
   ```powershell
   python run_integration_tests.py
   ```

2. **Run full test suite:**
   ```powershell
   python -m pytest tests/ -v
   ```

3. **Set up automated testing** (optional)
4. **Configure CI/CD pipelines** (optional)

## Support

If you encounter issues:

1. Check [Troubleshooting Guide](TROUBLESHOOTING_INTEGRATION.md)
2. Review [GitHub Issues](https://github.com/jpierzchala/powerbi-mcp/issues)
3. Create new issue with:
   - Full error message
   - Environment details (`python --version`, `dotnet --version`)
   - Your configuration (without secrets)

## Security Notes

- **Never commit `.env` file** to version control
- **Use dedicated Service Principal** for testing
- **Rotate secrets regularly**
- **Limit Service Principal permissions** to test workspace only
- **Monitor API usage** to avoid unexpected charges
