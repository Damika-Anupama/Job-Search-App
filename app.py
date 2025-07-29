#!/usr/bin/env python3
"""
Clean application entry point.

This is the main entry point for the Job Search application.
It imports the properly structured FastAPI app from the src package.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from job_search.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)