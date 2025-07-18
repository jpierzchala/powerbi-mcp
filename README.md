# Power BI MCP Server 🚀

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎥 Live Demo

![Power BI MCP Server Demo](PowerBI%20Mcp%20Demonstration.gif)

*Transform your Power BI experience - ask questions in natural language and get instant insights from your data.*

A Model Context Protocol (MCP) server that enables AI assistants to interact with Power BI datasets through natural language. Query your data, generate DAX, and get insights without leaving your AI assistant.

## ✨ Features

- 🔗 **Direct Power BI Connection** - Connect to any Power BI dataset via XMLA endpoints
- 💬 **Natural Language Queries** - Ask questions in plain English, get DAX queries and results
- 📊 **Automatic DAX Generation** - AI-powered DAX query generation using GPT-4o-mini
- 🔍 **Table Discovery** - Automatically explore tables, columns, and measures
- ⚡ **Optimized Performance** - Async operations and intelligent caching
- 🛡️ **Secure Authentication** - Service Principal authentication with Azure AD
- 📈 **Smart Suggestions** - Get relevant question suggestions based on your data

## 🎥 Demo

![Power BI MCP Demo](docs/images/demo.gif)

*Ask questions like "What are total sales by region?" and get instant insights from your Power BI data.*

## 🚀 Quick Start

### System Requirements & Platform Compatibility

| Platform | Python | .NET Runtime | ADOMD.NET | Status |
|----------|--------|--------------|-----------|--------|
| Windows  | 3.10+  | ✅ Built-in    | ✅ Available | ✅ Full Support |
| Linux    | 3.10+  | ✅ Available   | ⚠️ Docker only | ✅ Docker Support |
| macOS    | 3.10+  | ✅ Available   | ❌ Not available | ❌ Not supported |

**Note**: For Linux systems, use Docker to run the server with all dependencies included.

### Prerequisites

- Python 3.10 or higher (3.8+ may work but not officially supported)
- Windows with ADOMD.NET **or** Docker on Linux (container includes the runtime)
- SQL Server Management Studio (SSMS) or ADOMD.NET client libraries (Windows only)
- Power BI Pro/Premium with XMLA endpoint enabled
- Azure AD Service Principal with access to your Power BI dataset
- OpenAI API key (optional for natural language features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/powerbi-mcp-server.git
   cd powerbi-mcp-server
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Test the connection**
   ```bash
   python quickstart.py
   ```

### Configure with Claude Desktop

Add to your Claude Desktop configuration file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "python",
      "args": ["C:/path/to/powerbi-mcp-server/src/server.py"],
      "env": {
        "PYTHONPATH": "C:/path/to/powerbi-mcp-server",
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    }
  }
}
```

### Docker

Build the container image:
```bash
docker build -t powerbi-mcp .
```

Run the server:
```bash
docker run -it --rm -e OPENAI_API_KEY=<key> powerbi-mcp
```
The container listens on port `8000` by default. Override the host or port using
environment variables or command-line arguments:
```bash
docker run -it --rm -e OPENAI_API_KEY=<key> -p 7000:7000 powerbi-mcp \
  python src/server.py --host 0.0.0.0 --port 7000
```

The server exposes a Server-Sent Events endpoint at `/sse`. Clients should
connect to this endpoint and then POST JSON-RPC messages to the path provided in
the initial `endpoint` event (typically `/messages/`).

The container includes the .NET runtime required by `pythonnet` and `pyadomd`.
It sets `PYTHONNET_RUNTIME=coreclr` and `DOTNET_ROOT=/usr/share/dotnet` so the
.NET runtime is detected automatically. Environment variables mirror those in
`.env.example`; pass them with `-e VAR=value` or provide a `.env` file in the
build context.

## 📖 Usage

Once configured, you can interact with your Power BI data through Claude:

### Connect to Your Dataset
```
Connect to Power BI dataset at powerbi://api.powerbi.com/v1.0/myorg/YourWorkspace
```

### Explore Your Data
```
What tables are available?
Show me the structure of the Sales table
```

### Ask Questions
```
What are the total sales by product category?
Show me the trend of revenue over the last 12 months
Which store has the highest gross margin?
```

### Execute Custom DAX
```
Execute DAX: EVALUATE SUMMARIZE(Sales, Product[Category], "Total", SUM(Sales[Amount]))
```

## 🔧 Configuration

### Required Credentials

1. **Power BI XMLA Endpoint**
   - Format: `powerbi://api.powerbi.com/v1.0/myorg/WorkspaceName`
   - Enable in Power BI Admin Portal → Workspace Settings

2. **Azure AD Service Principal**
   - Create in Azure Portal → App Registrations
   - Grant access in Power BI Workspace → Access settings

3. **OpenAI API Key** *(optional)*
   - Needed only for natural language features
   - Endpoints that rely on GPT models are hidden if this key is not set
   - Get from [OpenAI Platform](https://platform.openai.com)
   - Model used: `gpt-4o-mini` (200x cheaper than GPT-4)

### Environment Variables

Create a `.env` file (OpenAI settings are optional):

```env
# OpenAI Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # Defaults to gpt-4o-mini

# Optional: Default Power BI Credentials
# These values are used when the `connect_powerbi` action does not supply
# tenant_id, client_id or client_secret.
DEFAULT_TENANT_ID=your_tenant_id
DEFAULT_CLIENT_ID=your_client_id
DEFAULT_CLIENT_SECRET=your_client_secret

# Logging
LOG_LEVEL=INFO
```

## 🏗️ Architecture

```
powerbi-mcp-server/
├── src/
│   └── server.py          # Main MCP server implementation
├── docs/                  # Documentation
├── examples/              # Example queries and use cases
├── tests/                 # Test suite
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── quickstart.py        # Quick test script
└── README.md           # This file
```

### Key Components

1. **PowerBIConnector** - Handles XMLA connections and DAX execution
2. **DataAnalyzer** - AI-powered query generation and interpretation
3. **PowerBIMCPServer** - MCP protocol implementation

## 🔐 Security Best Practices

- **Never commit credentials** - Use `.env` files and keep them in `.gitignore`
- **Use Service Principals** - Avoid personal credentials
- **Minimal permissions** - Grant only necessary access to datasets
- **Rotate secrets regularly** - Update Service Principal secrets periodically
- **Use secure connections** - Always use HTTPS/TLS

## 🧪 Testing

### Unit Tests

Run the standard test suite:
```bash
python -m pytest tests/
```

Test specific functionality:
```bash
python tests/test_connector.py
python tests/test_server_process.py
```

### Integration Tests

Real integration tests with Power BI datasets are available but disabled by default. These tests connect to actual Power BI services and may consume API quota.

**Enable Integration Tests:**

1. **Configure test environment**
   ```bash
   cp .env.example .env
   # Edit .env file and set:
   ENABLE_INTEGRATION_TESTS=true
   ```

2. **Set test dataset configuration**
   ```env
   # Test Power BI Dataset Configuration
   TEST_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/YourTestWorkspace
   TEST_TENANT_ID=your_tenant_id
   TEST_CLIENT_ID=your_client_id  
   TEST_CLIENT_SECRET=your_client_secret
   TEST_INITIAL_CATALOG=YourTestDatasetName
   
   # Optional: Expected test data for validation
   TEST_EXPECTED_TABLE=Sales
   TEST_EXPECTED_COLUMN=Amount
   TEST_DAX_QUERY=EVALUATE TOPN(1, Sales)
   TEST_MIN_TABLES_COUNT=1
   ```

3. **Run integration tests**
   ```bash
   # Interactive runner with safety checks
   python run_integration_tests.py
   
   # Or directly with pytest
   python -m pytest tests/test_integration.py -v
   
   # Run with auto-confirmation (CI/CD)
   python run_integration_tests.py --yes
   ```

**Integration Test Coverage:**
- ✅ Power BI dataset connection
- ✅ Table discovery and schema retrieval
- ✅ DAX query execution
- ✅ Sample data retrieval
- ✅ MCP tool interface testing
- ✅ Natural language query generation (with OpenAI)
- ✅ AI-powered suggestions (with OpenAI)

**⚠️ Warning:** Integration tests connect to real Power BI datasets and may consume:
- XMLA endpoint usage quota
- OpenAI API tokens
- Network bandwidth

Only run integration tests in dedicated test environments.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📊 Performance

- **Connection time**: 2-3 seconds
- **Query execution**: 1-5 seconds depending on complexity
- **Token usage**: ~500-2000 tokens per query with GPT-4o-mini
- **Cost**: ~$0.02-0.06 per day for typical usage

## 🧪 Testing

### Running Tests

```bash
# Check environment compatibility
python scripts/check_test_environment.py

# Run unit tests
python -m pytest tests/ -k "not test_integration" -v

# Run integration tests (requires .env configuration)
python -m pytest tests/test_integration.py -v
```

### Test Environment Requirements

- Python 3.10+ (recommended)
- All dependencies from requirements.txt
- For integration tests: valid Power BI connection credentials

### Platform-Specific Testing

- **Windows**: Full test suite supported
- **Linux**: Unit tests only (use Docker for integration tests)
- **macOS**: Unit tests only (limited support)

## 🐛 Troubleshooting

### Common Issues

1. **ADOMD.NET not found**
   - For Windows, install SQL Server Management Studio (SSMS)
   - On Linux, use the provided Docker image which bundles the cross-platform ADOMD.NET runtime

2. **Connection fails**
   - Verify XMLA endpoint is enabled in Power BI
   - Check Service Principal has workspace access
   - Ensure dataset name matches exactly

3. **Timeout errors**
   - Increase timeout in Claude Desktop config
   - Check network connectivity to Power BI

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for the MCP specification
- [Microsoft](https://microsoft.com) for Power BI and ADOMD.NET
- [OpenAI](https://openai.com) for GPT models
- The MCP community for inspiration and support

## 📬 Support

- 📧 Email: sulaimanahmed013@gmail.com
- 💬 Issues: [GitHub Issues](https://github.com/sulaiman013/powerbi-mcp-server/issues)
- 📚 Docs: [Full Documentation](https://github.com/sulaiman013/powerbi-mcp-server/wiki)
