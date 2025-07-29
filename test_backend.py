#!/usr/bin/env python3
"""
Test script to verify backend functionality before frontend integration.
"""

import sys
import os
import requests
import time
import subprocess
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_old_backend():
    """Test the old main.py backend"""
    print("Testing old backend (main_old.py)...")
    
    try:
        # Use the old main.py which should work
        process = subprocess.Popen([
            sys.executable, "main_old.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for startup
        time.sleep(3)
        
        # Test basic endpoints
        try:
            # Test root endpoint
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("SUCCESS: Root endpoint working")
                
                # Test health endpoint  
                health_response = requests.get("http://localhost:8000/health", timeout=5)
                if health_response.status_code == 200:
                    print("SUCCESS: Health endpoint working")
                    health_data = health_response.json()
                    print(f"   Status: {health_data.get('status', 'unknown')}")
                    print(f"   Mode: {health_data.get('mode', 'unknown')}")
                    
                    # Test search endpoint with simple query
                    search_data = {"query": "python developer"}
                    search_response = requests.post("http://localhost:8000/search", 
                                                  json=search_data, timeout=10)
                    
                    if search_response.status_code == 200:
                        print("SUCCESS: Search endpoint working")
                        search_result = search_response.json()
                        print(f"   Results: {len(search_result.get('results', []))}")
                        print(f"   Source: {search_result.get('source', 'unknown')}")
                        return True
                    else:
                        print(f"ERROR: Search endpoint failed: {search_response.status_code}")
                        print(f"   Response: {search_response.text}")
                else:
                    print(f"ERROR: Health endpoint failed: {health_response.status_code}")
            else:
                print(f"ERROR: Root endpoint failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to backend")
        except requests.exceptions.Timeout:
            print("❌ Backend request timed out")
        except Exception as e:
            print(f"❌ Error testing backend: {e}")
        
        finally:
            # Clean up process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
    
    return False

def install_frontend_deps():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    
    try:
        frontend_req = Path(__file__).parent / "frontend" / "requirements.txt"
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(frontend_req)
        ], check=True)
        print("✅ Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install frontend deps: {e}")
        return False

def test_frontend():
    """Test frontend startup"""
    print("🌐 Testing frontend startup...")
    
    try:
        frontend_app = Path(__file__).parent / "frontend" / "app.py"
        
        # Start streamlit in background
        process = subprocess.Popen([
            "streamlit", "run", str(frontend_app),
            "--server.port", "8501",
            "--server.headless", "true"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(5)
        
        try:
            # Test if streamlit is running
            response = requests.get("http://localhost:8501", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend started successfully")
                print("🌐 Frontend available at: http://localhost:8501")
                return True
            else:
                print(f"❌ Frontend responded with: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to frontend")
        except Exception as e:
            print(f"❌ Error testing frontend: {e}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
    except FileNotFoundError:
        print("❌ Streamlit not found. Installing frontend dependencies...")
        if install_frontend_deps():
            return test_frontend()
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
    
    return False

def main():
    """Main test function"""
    print("🚀 Job Search Platform Integration Test")
    print("=" * 50)
    
    # Test backend first
    backend_works = test_old_backend()
    
    if backend_works:
        print("\n✅ Backend is working! Now testing frontend...")
        
        # Test frontend
        frontend_works = test_frontend()
        
        if frontend_works:
            print("\n🎉 SUCCESS: Both backend and frontend are working!")
            print("\n📋 Next Steps:")
            print("1. Start backend: python main_old.py")
            print("2. Start frontend: cd frontend && python run.py")
            print("3. Visit http://localhost:8501 to use the app")
        else:
            print("\n⚠️ Backend works but frontend has issues")
    else:
        print("\n❌ Backend is not working. Please fix backend issues first.")
        print("\n💡 Troubleshooting:")
        print("1. Make sure Redis is running: docker-compose up redis -d")
        print("2. Check if all dependencies are installed")
        print("3. Verify .env configuration")

if __name__ == "__main__":
    main()