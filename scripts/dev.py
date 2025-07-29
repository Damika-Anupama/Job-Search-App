#!/usr/bin/env python3
"""
Development helper script for easy testing and running.
"""

import subprocess
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_tests():
    """Run the test suite"""
    print("🧪 Running tests...")
    return subprocess.run([sys.executable, "-m", "pytest", "tests/"], cwd=project_root)

def run_app():
    """Run the application in development mode"""
    print("🚀 Starting application...")
    return subprocess.run([sys.executable, "app.py"], cwd=project_root)

def check_health():
    """Check if the application is healthy"""
    print("🏥 Checking application health...")
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Application is {health_data['status']}")
            print(f"🔧 Mode: {health_data['mode']}")
            for component, status in health_data['components'].items():
                emoji = "✅" if status['status'] == 'healthy' else "❌"
                print(f"{emoji} {component}: {status['status']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to application (is it running?)")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def install_deps(mode="base"):
    """Install dependencies for specified mode"""
    print(f"📦 Installing {mode} dependencies...")
    req_file = project_root / "requirements" / f"{mode}.txt"
    if req_file.exists():
        return subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    else:
        print(f"❌ Requirements file not found: {req_file}")
        return 1

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("""
🚀 Job Search App Development Helper

Usage:
  python scripts/dev.py [command]

Commands:
  run      - Start the application
  test     - Run tests
  health   - Check application health
  install  - Install dependencies (base|ml|dev)

Examples:
  python scripts/dev.py run
  python scripts/dev.py test
  python scripts/dev.py install ml
        """)
        return

    command = sys.argv[1]
    
    if command == "run":
        run_app()
    elif command == "test":
        run_tests()
    elif command == "health":
        check_health()
    elif command == "install":
        mode = sys.argv[2] if len(sys.argv) > 2 else "base"
        install_deps(mode)
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()