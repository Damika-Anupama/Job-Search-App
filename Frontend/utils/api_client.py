"""
API client for communicating with the FastAPI backend.
"""

import aiohttp
import asyncio
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
import json
import time
import sys
import os

# Add the parent directory to sys.path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config.settings import settings

class APIClient:
    """Async API client for backend communication"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = settings.API_TIMEOUT
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            session = await self._get_session()
            async with session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    data = {"message": await response.text()}
                
                if response.status >= 400:
                    raise APIException(
                        message=data.get("detail", f"HTTP {response.status}"),
                        status_code=response.status,
                        response_data=data
                    )
                
                return {
                    "status_code": response.status,
                    "data": data,
                    "success": True
                }
        
        except aiohttp.ClientError as e:
            raise APIException(
                message=f"Network error: {str(e)}",
                status_code=0,
                response_data={}
            )
        except Exception as e:
            raise APIException(
                message=f"Unexpected error: {str(e)}",
                status_code=0,
                response_data={}
            )
    
    async def search_jobs(self, query: str, **filters) -> Dict[str, Any]:
        """Search for jobs"""
        search_request = {
            "query": query,
            "max_results": filters.get("max_results", settings.DEFAULT_MAX_RESULTS),
            **filters
        }
        
        return await self._make_request(
            "POST", 
            settings.ENDPOINTS["search"],
            json=search_request
        )
    
    async def trigger_indexing(self) -> Dict[str, Any]:
        """Trigger background job indexing"""
        return await self._make_request(
            "POST",
            settings.ENDPOINTS["trigger_indexing"]
        )
    
    async def get_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return await self._make_request("GET", settings.ENDPOINTS["health"])
    
    async def save_job(self, user_id: str, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a job for user tracking"""
        return await self._make_request(
            "POST",
            settings.get_api_url("save_job", user_id=user_id),
            json={"job_id": job_id, "job_data": job_data}
        )
    
    async def get_saved_jobs(self, user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Get user's saved jobs"""
        params = {"status": status} if status else {}
        return await self._make_request(
            "GET",
            settings.get_api_url("get_saved_jobs", user_id=user_id),
            params=params
        )
    
    async def update_job_status(self, user_id: str, job_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """Update job application status"""
        return await self._make_request(
            "PUT",
            settings.get_api_url("update_job_status", user_id=user_id, job_id=job_id),
            json={"status": status, "notes": notes}
        )
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        return await self._make_request(
            "GET",
            settings.get_api_url("user_stats", user_id=user_id)
        )
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

class SyncAPIClient:
    """Synchronous API client for Streamlit"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = settings.API_TIMEOUT
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make synchronous HTTP request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            
            # Try to parse JSON, fallback to text
            try:
                data = response.json()
            except:
                data = {"message": response.text}
            
            if response.status_code >= 400:
                raise APIException(
                    message=data.get("detail", f"HTTP {response.status_code}"),
                    status_code=response.status_code,
                    response_data=data
                )
            
            return {
                "status_code": response.status_code,
                "data": data,
                "success": True
            }
        
        except requests.exceptions.RequestException as e:
            raise APIException(
                message=f"Network error: {str(e)}",
                status_code=0,
                response_data={}
            )
        except Exception as e:
            raise APIException(
                message=f"Unexpected error: {str(e)}",
                status_code=0,
                response_data={}
            )
    
    def search_jobs(self, query: str, **filters) -> Dict[str, Any]:
        """Search for jobs"""
        search_request = {
            "query": query,
            "max_results": filters.get("max_results", settings.DEFAULT_MAX_RESULTS),
            **filters
        }
        
        return self._make_request(
            "POST", 
            settings.ENDPOINTS["search"],
            json=search_request
        )
    
    def trigger_indexing(self) -> Dict[str, Any]:
        """Trigger background job indexing"""
        return self._make_request(
            "POST",
            settings.ENDPOINTS["trigger_indexing"]
        )
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return self._make_request("GET", settings.ENDPOINTS["health"])
    
    def save_job(self, user_id: str, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a job for user tracking"""
        return self._make_request(
            "POST",
            settings.get_api_url("save_job", user_id=user_id),
            json={"job_id": job_id, "job_data": job_data}
        )
    
    def get_saved_jobs(self, user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Get user's saved jobs"""
        params = {"status": status} if status else {}
        return self._make_request(
            "GET",
            settings.get_api_url("get_saved_jobs", user_id=user_id),
            params=params
        )
    
    def update_job_status(self, user_id: str, job_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """Update job application status"""
        return self._make_request(
            "PUT",
            settings.get_api_url("update_job_status", user_id=user_id, job_id=job_id),
            json={"status": status, "notes": notes}
        )
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        return self._make_request(
            "GET",
            settings.get_api_url("user_stats", user_id=user_id)
        )
    
    def remove_saved_job(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Remove a saved job"""
        return self._make_request(
            "DELETE",
            settings.get_api_url("remove_saved_job", user_id=user_id, job_id=job_id)
        )

class APIException(Exception):
    """Custom exception for API errors"""
    
    def __init__(self, message: str, status_code: int, response_data: Dict[str, Any]):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
    
    def __str__(self):
        return f"API Error ({self.status_code}): {self.message}"

# Global API client instance
api_client = SyncAPIClient()

# Helper functions for Streamlit
def run_with_spinner(func, *args, spinner_text="Processing...", **kwargs):
    """Run function with Streamlit spinner"""
    with st.spinner(spinner_text):
        return func(*args, **kwargs)

def handle_api_error(func, *args, **kwargs):
    """Handle API errors gracefully in Streamlit"""
    try:
        return func(*args, **kwargs)
    except APIException as e:
        if e.status_code == 0:
            st.error(f"🔌 **Connection Error**: {e.message}")
            st.error("❓ **Troubleshooting**: Make sure the backend server is running at `http://localhost:8000`")
        elif e.status_code >= 500:
            st.error(f"🔧 **Server Error**: {e.message}")
            st.error("💡 **Try**: Refresh the page or contact support if the issue persists")
        elif e.status_code >= 400:
            st.warning(f"⚠️ **Request Error**: {e.message}")
        else:
            st.error(f"❌ **Unexpected Error**: {e.message}")
        return None
    except Exception as e:
        st.error(f"💥 **Unexpected Error**: {str(e)}")
        return None