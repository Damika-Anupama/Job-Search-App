#!/usr/bin/env python3
"""
Test runner script for Job Search Application

This script provides different test execution modes and ensures proper
environment setup for testing different application modes.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Info:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def install_test_dependencies():
    """Install test dependencies"""
    return run_command(
        "pip install -r requirements-dev.txt",
        "Installing test dependencies"
    )

def run_linting():
    """Run code linting"""
    success = True
    
    # Check if flake8 is available
    try:
        subprocess.run(["flake8", "--version"], capture_output=True, check=True)
        success &= run_command(
            "flake8 --max-line-length=100 --exclude=tests,venv,.venv,__pycache__ .",
            "Running flake8 linting"
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  flake8 not available, skipping linting")
    
    return success

def run_formatting_check():
    """Check code formatting with black"""
    try:
        subprocess.run(["black", "--version"], capture_output=True, check=True)
        return run_command(
            "black --check --diff .",
            "Checking code formatting with black"
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  black not available, skipping format check")
        return True

def run_unit_tests(mode=None, verbose=False):
    """Run unit tests"""
    cmd = "python -m pytest"
    
    if verbose:
        cmd += " -v -s"
    
    if mode:
        # Set environment variable for mode-specific testing
        os.environ['TEST_APP_MODE'] = mode
        description = f"Running unit tests for {mode} mode"
    else:
        description = "Running all unit tests"
    
    return run_command(cmd, description)

def run_coverage_report():
    """Generate coverage report"""
    return run_command(
        "python -m pytest --cov=. --cov-report=html --cov-report=term",
        "Generating coverage report"
    )

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "all"
    
    print("🚀 Job Search Application Test Runner")
    print(f"Working directory: {Path.cwd()}")
    
    if command == "install":
        install_test_dependencies()
    
    elif command == "lint":
        run_linting()
    
    elif command == "format":
        run_formatting_check()
    
    elif command == "unit":
        run_unit_tests(verbose=True)
    
    elif command == "lightweight":
        run_unit_tests(mode="lightweight", verbose=True)
    
    elif command == "full-ml":
        run_unit_tests(mode="full-ml", verbose=True)
    
    elif command == "cloud-ml":
        run_unit_tests(mode="cloud-ml", verbose=True)
    
    elif command == "coverage":
        run_coverage_report()
    
    elif command == "all":
        print("🎯 Running complete test suite...")
        success = True
        
        # Install dependencies
        success &= install_test_dependencies()
        
        # Run linting
        success &= run_linting()
        
        # Run formatting check
        success &= run_formatting_check()
        
        # Run tests for each mode
        for mode in ["lightweight", "full-ml", "cloud-ml"]:
            success &= run_unit_tests(mode=mode)
        
        # Generate coverage report
        success &= run_coverage_report()
        
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    
    else:
        print(f"""
Usage: python run_tests.py [command]

Commands:
  install     - Install test dependencies
  lint        - Run code linting
  format      - Check code formatting
  unit        - Run unit tests
  lightweight - Run tests for lightweight mode
  full-ml     - Run tests for full-ml mode  
  cloud-ml    - Run tests for cloud-ml mode
  coverage    - Generate coverage report
  all         - Run complete test suite (default)

Examples:
  python run_tests.py
  python run_tests.py unit
  python run_tests.py cloud-ml
  python run_tests.py coverage
        """)

if __name__ == "__main__":
    main()