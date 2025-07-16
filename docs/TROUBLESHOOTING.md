# Troubleshooting Guide

This guide helps you resolve common issues with the Power BI MCP Server.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Connection Problems](#connection-problems)
- [Authentication Errors](#authentication-errors)
- [Query Issues](#query-issues)
- [Performance Problems](#performance-problems)
- [Claude Desktop Integration](#claude-desktop-integration)

## Installation Issues

### ADOMD.NET Not Found

**Error:**
```
ImportError: Could not load ADOMD.NET library. Please install SSMS or ADOMD.NET client.
```

**Solutions:**

1. **Install SQL Server Management Studio (SSMS)**
   - Download from [Microsoft](https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms)
   - This includes ADOMD.NET libraries

2. **Install ADOMD.NET Separately**
   - Download from [NuGet](https://www.nuget.org/packages/Microsoft.AnalysisServices.AdomdClient.NetCore.retail.amd64/)
   - Extract and place in `C:\Program Files\Microsoft.NET\ADOMD.NET\`

3. **Check Installation Path**
   ```python
   # The server looks in these locations:
   C:\Program Files\Microsoft.NET\ADOMD.NET\160
   C:\Program Files\Microsoft.NET\ADOMD.NET\150
   C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\160
   C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\150
   ```
### Microsoft.Identity.Client Missing

**Error:**
```
FileNotFoundException: Could not load file or assembly 'Microsoft.Identity.Client, Version=4.6.0.0'
```

**Solutions:**
1. **Install Recent ADOMD.NET** - version 19.12 or newer bundles this library
2. **Verify `ADOMD_LIB_DIR`** - point it to the folder with `Microsoft.Identity.Client.dll`
3. **Restart the MCP server** after installation
4. **Use the provided Dockerfile** - the container now installs this library automatically


### MCP Framework Not Found

**Error:**
```
ModuleNotFoundError: No module named 'mcp'
```

**Solution:**
```bash
pip install mcp-framework
# NOT 'pip install mcp' - the package name is mcp-framework
```

### Python Version Error

**Error:**
```
SyntaxError: f-strings are not supported in Python 3.5
```

**Solution:**
- Upgrade to Python 3.8 or higher
- Check version: `python --version`

## Connection Problems

### XMLA Endpoint Not Enabled

**Error:**
```
Connection failed: The XMLA endpoint is not enabled for this workspace
```

**Solutions:**

1. **Enable XMLA in Power BI Admin Portal**
   - Go to Power BI Admin Portal → Capacity settings
   - Enable "XMLA Endpoint" to "Read Write"

2. **Check Workspace Type**
   - XMLA requires Premium capacity or PPU license
   - Shared capacity doesn't support XMLA

3. **Verify Endpoint URL Format**
   ```
   Correct: powerbi://api.powerbi.com/v1.0/myorg/WorkspaceName
   Wrong: https://api.powerbi.com/...
   ```

### Network Connectivity Issues

**Error:**
```
Connection failed: Unable to connect to the remote server
```

**Solutions:**

1. **Check Firewall**
   - Allow outbound HTTPS (443) to `*.powerbi.com`
   - Allow outbound to `*.analysis.windows.net`

2. **Proxy Configuration**
   ```python
   # Add to connection string if using proxy:
   f"Provider=MSOLAP;Data Source={endpoint};HTTPProxy=http://proxy:8080"
   ```

3. **Test Connectivity**
   ```bash
   nslookup api.powerbi.com
   ping api.powerbi.com
   ```

## Authentication Errors

### Invalid Service Principal

**Error:**
```
Connection failed: AADSTS700016: Application not found in the directory
```

**Solutions:**

1. **Verify Service Principal Details**
   - Tenant ID: Check in Azure Portal → Azure Active Directory
   - Client ID: From App Registration → Overview
   - Client Secret: May have expired, create new one

2. **Grant Power BI Permissions**
   - In Power BI workspace → Access → Add service principal
   - Grant at least "Viewer" permission

3. **Check Secret Expiration**
   ```bash
   # In Azure Portal → App Registration → Certificates & secrets
   # Create new secret if expired
   ```

### Dataset Not Found

**Error:**
```
Connection failed: The dataset 'YourDataset' was not found
```

**Solutions:**

1. **Exact Name Match**
   - Dataset names are case-sensitive
   - Use exact name from Power BI workspace

2. **Check Permissions**
   - Service principal needs access to specific dataset
   - Not just workspace access

## Query Issues

### Invalid DAX Syntax

**Error:**
```
DAX query failed: The syntax for 'EVALUATE' is incorrect
```

**Solutions:**

1. **Check Table/Column Names**
   ```dax
   # Correct - with proper syntax
   EVALUATE SUMMARIZE(Sales, Product[Category])
   
   # Wrong - missing table prefix
   EVALUATE SUMMARIZE(Sales, Category)
   ```

2. **Handle Special Characters**
   ```dax
   # For spaces in names
   EVALUATE 'Sales Table'
   
   # For special characters
   EVALUATE 'Sales-2024'
   ```

### HTML/XML Artifacts in DAX

**Error:**
```
DAX query failed: Unknown identifier '<oii>Rank</oii>'
```

**Solution:**
- This is fixed in the latest version
- Update to the optimized server code
- The `clean_dax_query()` function removes these artifacts

### Column Not Found

**Error:**
```
The column 'Sales[Rank]' does not exist
```

**Solutions:**

1. **List Available Columns**
   ```
   Show me the structure of the Sales table
   ```

2. **Check Column Names**
   - Use exact column names
   - Check for typos or case sensitivity

## Performance Problems

### Slow Connection (30+ seconds)

**Solutions:**

1. **Use Optimized Server**
   - Update to latest version with async operations
   - Tables load in background after connection

2. **Reduce Initial Table Load**
   ```python
   # In .env file
   INITIAL_TABLES_LIMIT=3  # Reduce from 5
   ```

3. **Check Network Latency**
   ```bash
   ping api.powerbi.com
   ```

### Query Timeouts

**Error:**
```
MCP error -32001: Request timed out
```

**Solutions:**

1. **Increase Timeout in Claude Desktop**
   ```json
   {
     "mcpServers": {
       "powerbi": {
         "timeout": 60000  // 60 seconds
       }
     }
   }
   ```

2. **Optimize DAX Queries**
   - Limit row count: `TOPN(1000, ...)`
   - Use filters early
   - Avoid complex calculations

### High Memory Usage

**Solutions:**

1. **Limit Sample Data**
   ```python
   # In .env
   MAX_SAMPLE_ROWS=5  # Reduce from 10
   ```

2. **Close Unused Connections**
   - Restart server periodically
   - Each connection holds memory

## Claude Desktop Integration

### Server Not Starting

**Error in Claude:**
```
Failed to start MCP server
```

**Solutions:**

1. **Check Path**
   ```json
   // Use absolute path with forward slashes
   "args": ["C:/Users/YourName/powerbi-mcp-server/src/server.py"]
   ```

2. **Test Server Directly**
   ```bash
   python src/server.py
   # Should show no output if working
   ```

3. **Check Python Path**
   ```json
   // Specify full Python path
   "command": "C:/Python39/python.exe"
   ```

### Environment Variables Not Loading

**Solution:**
```json
{
  "mcpServers": {
    "powerbi": {
      "env": {
        "PYTHONPATH": "C:/path/to/powerbi-mcp-server",
        "OPENAI_API_KEY": "sk-...",
        "PATH": "C:/path/to/python;C:/path/to/python/Scripts"
      }
    }
  }
}
```

### Tools Not Appearing

**Solutions:**

1. **Restart Claude Desktop**
   - Close completely (check system tray)
   - Reopen

2. **Check Logs**
   - Windows: `%APPDATA%\Claude\logs`
   - Look for MCP errors

3. **Verify Server Response**
   ```bash
   # Test server is returning tools
   python -c "from src.server import PowerBIMCPServer; print('OK')"
   ```

## Debug Mode

Enable detailed logging:

```python
# In .env
LOG_LEVEL=DEBUG
DEBUG_MODE=true
```

Check logs:
```bash
tail -f mcp-server-powerbi.log
```

## Getting More Help

1. **Check Logs First**
   - Server logs: `mcp-server-powerbi.log`
   - Claude logs: `%APPDATA%\Claude\logs`

2. **Create Detailed Issue**
   - Include error messages
   - Share relevant logs
   - Describe steps to reproduce

3. **Community Support**
   - GitHub Issues
   - Discussions section
   - Stack Overflow with tags: `power-bi`, `mcp`

## Common Quick Fixes

```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Clear Python cache
python -m pip cache purge

# Test imports
python -c "import mcp, pyadomd, openai, clr; print('All imports OK')"

# Validate .env file
python quickstart.py
```
