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

### Prerequisites

- Python 3.8 or higher
- Windows OS (required for ADOMD.NET)
- SQL Server Management Studio (SSMS) or ADOMD.NET client libraries
- Power BI Pro/Premium with XMLA endpoint enabled
- Azure AD Service Principal with access to your Power BI dataset
- OpenAI API key

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

3. **OpenAI API Key**
   - Get from [OpenAI Platform](https://platform.openai.com)
   - Model used: `gpt-4o-mini` (200x cheaper than GPT-4)

### Environment Variables

Create a `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # Optional: defaults to gpt-4o-mini

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

Run the test suite:
```bash
python -m pytest tests/
```

Test specific functionality:
```bash
python tests/test_connection.py
python tests/test_dax_generation.py
```

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

## 🐛 Troubleshooting

### Common Issues

1. **ADOMD.NET not found**
   - Install SQL Server Management Studio (SSMS)
   - Or download [ADOMD.NET](https://docs.microsoft.com/en-us/analysis-services/client-libraries)

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
