#!/usr/bin/env python3
"""
Power BI MCP Server - Quick Start Script
This script helps you test your setup and verify everything is working correctly.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Print welcome header"""
    print(f"\n{Colors.BOLD}Power BI MCP Server - Quick Start{Colors.END}")
    print("=" * 50)

def check_python_version():
    """Check if Python version is 3.8+"""
    print(f"\n{Colors.BLUE}Checking Python version...{Colors.END}")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"{Colors.GREEN}✓ Python {version.major}.{version.minor}.{version.micro} is supported{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}✗ Python {version.major}.{version.minor} is not supported. Please use Python 3.8+{Colors.END}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print(f"\n{Colors.BLUE}Checking dependencies...{Colors.END}")
    
    required_packages = {
        'mcp': 'mcp-framework',
        'pyadomd': 'pyadomd',
        'openai': 'openai',
        'dotenv': 'python-dotenv',
        'clr': 'pythonnet'
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            if import_name == 'dotenv':
                import dotenv
            elif import_name == 'clr':
                import clr
            else:
                __import__(import_name)
            print(f"{Colors.GREEN}✓ {package_name} is installed{Colors.END}")
        except ImportError:
            print(f"{Colors.RED}✗ {package_name} is not installed{Colors.END}")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n{Colors.YELLOW}To install missing packages, run:{Colors.END}")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_adomd():
    """Check if ADOMD.NET is available"""
    print(f"\n{Colors.BLUE}Checking ADOMD.NET...{Colors.END}")
    
    try:
        import clr
        adomd_paths = [
            r"C:\Program Files\Microsoft.NET\ADOMD.NET\160",
            r"C:\Program Files\Microsoft.NET\ADOMD.NET\150",
            r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\160",
            r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\150"
        ]
        
        adomd_found = False
        for path in adomd_paths:
            if os.path.exists(path):
                try:
                    sys.path.append(path)
                    clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
                    adomd_found = True
                    print(f"{Colors.GREEN}✓ ADOMD.NET found at: {path}{Colors.END}")
                    break
                except:
                    continue
        
        if not adomd_found:
            print(f"{Colors.RED}✗ ADOMD.NET not found{Colors.END}")
            print(f"{Colors.YELLOW}Please install SQL Server Management Studio (SSMS) or ADOMD.NET client{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}✗ Error checking ADOMD.NET: {str(e)}{Colors.END}")
        return False
    
    return True

def check_environment():
    """Check environment variables"""
    print(f"\n{Colors.BLUE}Checking environment variables...{Colors.END}")
    
    # Load .env file
    load_dotenv()
    
    # Check OpenAI API key (optional)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        print(f"{Colors.GREEN}✓ OpenAI API key found{Colors.END}")
    else:
        print(f"{Colors.YELLOW}ℹ OpenAI API key not set - natural language features will be disabled{Colors.END}")
    
    # Check optional Power BI credentials used as fallback
    tenant_id = os.getenv("DEFAULT_TENANT_ID")
    if tenant_id:
        print(f"{Colors.GREEN}✓ Default Power BI credentials found (fallback){Colors.END}")
    else:
        print(f"{Colors.YELLOW}ℹ Default Power BI credentials not set (optional){Colors.END}")
    
    return True

def test_power_bi_connection():
    """Test Power BI connection"""
    print(f"\n{Colors.BLUE}Testing Power BI connection...{Colors.END}")
    
    try:
        from server import PowerBIConnector
        
        print(f"{Colors.YELLOW}Enter your Power BI connection details:{Colors.END}")
        print("(Press Enter to skip this test)")
        
        xmla_endpoint = input("XMLA Endpoint: ").strip()
        if not xmla_endpoint:
            print(f"{Colors.YELLOW}Skipping Power BI connection test{Colors.END}")
            return True
        
        tenant_id = input("Tenant ID: ").strip() or os.getenv("DEFAULT_TENANT_ID", "")
        client_id = input("Client ID: ").strip() or os.getenv("DEFAULT_CLIENT_ID", "")
        client_secret = input("Client Secret: ").strip() or os.getenv("DEFAULT_CLIENT_SECRET", "")
        dataset_name = input("Dataset Name: ").strip()
        
        if not all([tenant_id, client_id, client_secret, dataset_name]):
            print(f"{Colors.RED}✗ Missing required credentials{Colors.END}")
            return False
        
        print(f"\n{Colors.YELLOW}Connecting to Power BI...{Colors.END}")
        
        connector = PowerBIConnector()
        connector.connect(xmla_endpoint, tenant_id, client_id, client_secret, dataset_name)
        
        print(f"{Colors.GREEN}✓ Successfully connected to '{dataset_name}'{Colors.END}")
        
        # Discover tables
        tables = connector.discover_tables()
        print(f"{Colors.GREEN}✓ Found {len(tables)} tables:{Colors.END}")
        for table in tables[:5]:
            print(f"  - {table}")
        if len(tables) > 5:
            print(f"  ... and {len(tables) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}✗ Connection failed: {str(e)}{Colors.END}")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if not os.path.exists('.env') and os.path.exists('.env.example'):
        print(f"\n{Colors.YELLOW}Creating .env file from template...{Colors.END}")
        with open('.env.example', 'r') as src, open('.env', 'w') as dst:
            dst.write(src.read())
        print(f"{Colors.GREEN}✓ Created .env file. Please edit it with your credentials.{Colors.END}")
        return False
    return True

def main():
    """Run all checks"""
    print_header()
    
    # Create .env if needed
    env_exists = create_env_file()
    
    # Run all checks
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("ADOMD.NET", check_adomd),
        ("Environment", check_environment),
    ]
    
    all_passed = True
    results = {}
    
    for name, check_func in checks:
        results[name] = check_func()
        all_passed = all_passed and results[name]
    
    # Optional Power BI test
    if all_passed:
        test_power_bi_connection()
    
    # Summary
    print(f"\n{Colors.BOLD}Summary:{Colors.END}")
    print("=" * 50)
    
    for name, passed in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"{name}: {status}")
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Your Power BI MCP Server is ready to use!{Colors.END}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print("1. Run the server: python src/server.py")
        print("2. Configure Claude Desktop with the settings in README.md")
        print("3. Start chatting with your Power BI data!")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Some checks failed. Please fix the issues above.{Colors.END}")
        if not env_exists:
            print(f"\n{Colors.YELLOW}Don't forget to edit .env with your API keys!{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelled by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.END}")
        sys.exit(1)
