#!/usr/bin/env python3
"""
Frontend runner script for development and testing.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install frontend requirements"""
    print("📦 Installing frontend requirements...")
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def run_streamlit():
    """Run the Streamlit application"""
    print("🚀 Starting Streamlit frontend...")
    app_file = Path(__file__).parent / "app.py"
    
    try:
        subprocess.run([
            "streamlit", "run", str(app_file),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--theme.base", "light",
            "--theme.primaryColor", "#667eea"
        ])
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped by user")
    except FileNotFoundError:
        print("❌ Streamlit not found. Installing...")
        if install_requirements():
            run_streamlit()
    except Exception as e:
        print(f"❌ Error running frontend: {e}")

def main():
    """Main entry point"""
    print("🎯 Job Search Frontend Launcher")
    print("=" * 40)
    
    # Check if requirements are installed
    try:
        import streamlit
        print("✅ Streamlit is available")
    except ImportError:
        print("📦 Streamlit not installed, installing requirements...")
        if not install_requirements():
            sys.exit(1)
    
    # Set environment variables for development
    os.environ.setdefault("BACKEND_BASE_URL", "http://localhost:8000")
    
    print(f"🔗 Backend URL: {os.environ.get('BACKEND_BASE_URL')}")
    print(f"🌐 Frontend will be available at: http://localhost:8501")
    print("\n💡 Make sure your backend is running at http://localhost:8000")
    print("   You can start it with: python app.py")
    print("\n🚀 Starting frontend...")
    
    run_streamlit()

if __name__ == "__main__":
    main()