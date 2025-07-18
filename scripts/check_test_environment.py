#!/usr/bin/env python3
"""
Script to check if the test environment is properly set up.
This runs before tests to ensure dependencies are available.
"""

import sys
import os
import platform
import subprocess

def check_python_version():
    """Check if Python version is supported"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("⚠️  WARNING: Python 3.10+ is recommended for best compatibility")
        return False
    
    print("✅ Python version is supported")
    return True

def check_dotnet_runtime():
    """Check if .NET runtime is available"""
    try:
        result = subprocess.run(['dotnet', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ .NET runtime available: {result.stdout.strip()}")
            return True
        else:
            print("❌ .NET runtime not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ .NET runtime not found")
        return False

def check_pyadomd():
    """Check if pyadomd can be imported"""
    try:
        # Try to import pyadomd in a safe way
        import sys
        import os
        
        # On Linux, we need to set the runtime before importing
        if sys.platform.startswith('linux'):
            try:
                import pythonnet
                # Try to set a compatible runtime
                pythonnet.set_runtime("coreclr")
            except Exception:
                # If we can't set coreclr, try mono
                try:
                    import pythonnet
                    pythonnet.set_runtime("mono")
                except Exception:
                    print("⚠️  No compatible .NET runtime found")
                    print("   pyadomd functionality will be disabled")
                    return False
        
        import pyadomd
        print("✅ pyadomd can be imported")
        return True
    except ImportError as e:
        print(f"⚠️  pyadomd import failed: {e}")
        print("   This is expected on non-Windows systems or without ADOMD.NET")
        return False
    except Exception as e:
        print(f"⚠️  pyadomd check failed: {e}")
        print("   This is expected on systems without proper .NET runtime")
        return False

def check_pythonnet():
    """Check if pythonnet can be imported"""
    try:
        import pythonnet
        print("✅ pythonnet can be imported")
        return True
    except ImportError as e:
        print(f"❌ pythonnet import failed: {e}")
        return False

def check_test_dependencies():
    """Check if test dependencies are available"""
    required_packages = ['pytest', 'pytest-asyncio', 'pytest-cov']
    all_good = True
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} is not available")
            all_good = False
    
    return all_good

def main():
    """Main function to run all checks"""
    print("🔍 Checking test environment...")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print()
    
    checks = [
        ("Python version", check_python_version),
        (".NET runtime", check_dotnet_runtime),
        ("pythonnet", check_pythonnet),
        ("pyadomd", check_pyadomd),
        ("Test dependencies", check_test_dependencies),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"Checking {name}...")
        result = check_func()
        results.append((name, result))
        print()
    
    print("📊 Environment Check Summary:")
    print("=" * 40)
    
    critical_failures = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
        
        # Only pythonnet and test dependencies are critical
        if not result and name in ["pythonnet", "Test dependencies"]:
            critical_failures += 1
    
    print()
    
    if critical_failures > 0:
        print(f"❌ {critical_failures} critical checks failed")
        print("   Tests may not run properly")
        return 1
    else:
        print("✅ Environment check passed!")
        print("   Tests should run successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())
