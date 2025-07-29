"""
🚀 AI Job Discovery Platform - Streamlit Frontend

A modern, enterprise-grade frontend for the AI-powered job search platform.
"""

import streamlit as st
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import our custom components and utilities
import sys
import os

# Ensure current directory is in path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config.settings import settings
from utils.api_client import api_client, handle_api_error, run_with_spinner, APIException
from components.job_card import render_job_card, render_saved_job_card

# Page configuration
st.set_page_config(
    page_title=settings.PAGE_TITLE,
    page_icon=settings.PAGE_ICON,
    layout=settings.LAYOUT,
    initial_sidebar_state=settings.INITIAL_SIDEBAR_STATE
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.375rem;
        margin: 1rem 0;
    }
    
    .warning-message {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.375rem;
        margin: 1rem 0;
    }
    
    .sidebar-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #17a2b8;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        border: none;
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if 'saved_jobs' not in st.session_state:
        st.session_state.saved_jobs = []
    
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    if 'last_search_results' not in st.session_state:
        st.session_state.last_search_results = []
    
    if 'backend_health' not in st.session_state:
        st.session_state.backend_health = None

def check_backend_health():
    """Check backend health and update session state"""
    try:
        health_response = api_client.get_health()
        if health_response and health_response['success']:
            st.session_state.backend_health = health_response['data']
            return True
    except:
        st.session_state.backend_health = None
        return False
    return False

def render_header():
    """Render the main application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🚀 AI Job Discovery Platform</h1>
        <p>Find your perfect job with intelligent ML-powered search across multiple job boards</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the sidebar with navigation and info"""
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        
        # Navigation
        page = st.radio(
            "Choose a page:",
            ["🔍 Job Search", "📊 Saved Jobs", "📈 Analytics", "⚙️ Settings & Admin"],
            index=0
        )
        
        st.divider()
        
        # Backend status
        st.markdown("## 🔌 System Status")
        
        if st.button("🔄 Check Backend Health", help="Check if backend is running"):
            with st.spinner("Checking backend..."):
                check_backend_health()
        
        if st.session_state.backend_health:
            health = st.session_state.backend_health
            status = health.get('status', 'unknown')
            
            if status == 'healthy':
                st.success(f"✅ Backend: {status.title()}")
            elif status == 'degraded':
                st.warning(f"⚠️ Backend: {status.title()}")
            else:
                st.error(f"❌ Backend: {status.title()}")
            
            # Component status
            components = health.get('components', {})
            for comp_name, comp_data in components.items():
                comp_status = comp_data.get('status', 'unknown')
                if comp_status == 'healthy':
                    st.text(f"✅ {comp_name.title()}")
                else:
                    st.text(f"❌ {comp_name.title()}")
        else:
            st.error("❌ Backend: Unavailable")
            st.caption("Make sure the backend is running at http://localhost:8000")
        
        st.divider()
        
        # User info
        st.markdown("## 👤 User Info")
        st.caption(f"User ID: `{st.session_state.user_id[:8]}...`")
        st.caption(f"Saved Jobs: {len(st.session_state.saved_jobs)}")
        
        # Quick stats
        if st.session_state.saved_jobs:
            status_counts = {}
            for job in st.session_state.saved_jobs:
                status = job.get('status', 'saved')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            st.markdown("### 📊 Quick Stats")
            for status, count in status_counts.items():
                st.caption(f"{status.title()}: {count}")
        
        return page

def render_search_page():
    """Render the main job search page"""
    st.markdown("## 🔍 Smart Job Search")
    st.markdown("Search across multiple job boards with AI-powered semantic matching")
    
    # Search form
    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            query = st.text_input(
                "🎯 What job are you looking for?",
                placeholder=settings.SEARCH_PLACEHOLDER,
                help="Use natural language - our AI understands context and meaning",
                max_chars=settings.MAX_SEARCH_QUERY_LENGTH
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            search_clicked = st.form_submit_button("🚀 Search Jobs", use_container_width=True)
        
        # Advanced filters in expander
        with st.expander("🎛️ Advanced Filters (Optional)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                locations = st.multiselect(
                    "📍 Locations",
                    ["remote", "san francisco", "new york", "london", "berlin", "toronto", "seattle", "austin"],
                    help="Select preferred locations"
                )
                
                required_skills = st.multiselect(
                    "⚡ Required Skills",
                    ["python", "javascript", "react", "node.js", "java", "go", "rust", "machine learning"],
                    help="Skills that MUST be present"
                )
            
            with col2:
                preferred_skills = st.multiselect(
                    "✨ Preferred Skills",
                    ["docker", "kubernetes", "aws", "gcp", "postgresql", "mongodb", "redis", "tensorflow"],
                    help="Skills that boost relevance"
                )
                
                exclude_keywords = st.multiselect(
                    "🚫 Exclude Keywords",
                    ["internship", "unpaid", "contract", "part-time", "on-site"],
                    help="Keywords to exclude from results"
                )
            
            with col3:
                max_results = st.slider(
                    "📊 Max Results",
                    min_value=5,
                    max_value=50,
                    value=settings.DEFAULT_MAX_RESULTS,
                    help="Maximum number of jobs to return"
                )
                
                enable_reranking = st.checkbox(
                    "🧠 Enable ML Reranking",
                    value=True,
                    help="Use advanced ML to improve result relevance"
                )
    
    # Process search
    if search_clicked and query.strip():
        # Build search filters
        filters = {
            "locations": locations,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "exclude_keywords": exclude_keywords,
            "max_results": max_results,
            "enable_reranking": enable_reranking
        }
        
        # Perform search
        search_response = handle_api_error(
            run_with_spinner,
            api_client.search_jobs,
            query,
            **filters,
            spinner_text=f"🔍 Searching for '{query}'..."
        )
        
        if search_response and search_response['success']:
            search_data = search_response['data']
            # Handle different response formats from test backend
            results = search_data.get('jobs', search_data.get('results', []))
            
            # Update session state
            st.session_state.last_search_results = results
            st.session_state.search_history.append({
                "query": query,
                "timestamp": datetime.now(),
                "results_count": len(results)
            })
            
            # Display results summary
            total_found = search_data.get('total_results', search_data.get('total_found', len(results)))
            reranked = search_data.get('reranked', False)
            source = search_data.get('source', 'unknown')
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Results Found", len(results))
            with col2:
                st.metric("🎯 Total Available", total_found)
            with col3:
                st.metric("🧠 ML Reranked", "Yes" if reranked else "No")
            with col4:
                st.metric("⚡ Source", source.title())
            
            if results:
                st.success(f"✅ Found {len(results)} jobs matching your criteria!")
                
                # Display jobs
                st.markdown("---")
                st.markdown("## 📋 Job Results")
                
                for i, job in enumerate(results):
                    action = render_job_card(
                        job, 
                        st.session_state.user_id, 
                        show_save_button=True,
                        saved_jobs=st.session_state.saved_jobs,
                        key_prefix=f"search_{i}"
                    )
                    
                    if action == "save":
                        # Save job via API
                        save_response = handle_api_error(
                            api_client.save_job,
                            st.session_state.user_id,
                            job.get('id', str(uuid.uuid4())),
                            job
                        )
                        
                        if save_response and save_response['success']:
                            st.success("💾 Job saved successfully!")
                            # Refresh saved jobs
                            refresh_saved_jobs()
                            st.rerun()
                        
                    elif action == "similar":
                        # Find similar jobs (could be implemented)
                        st.info("🔍 Similar job search feature coming soon!")
            
            else:
                st.warning("🤔 No jobs found matching your criteria. Try adjusting your search terms or filters.")
    
    elif search_clicked and not query.strip():
        st.error("⚠️ Please enter a search query to find jobs.")
    
    # Show recent search history
    if st.session_state.search_history:
        with st.expander("🕒 Recent Searches"):
            for i, search in enumerate(reversed(st.session_state.search_history[-5:])):  # Last 5 searches
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"'{search['query']}'")
                with col2:
                    st.caption(f"{search['results_count']} results")
                with col3:
                    st.caption(search['timestamp'].strftime("%H:%M"))

def refresh_saved_jobs():
    """Refresh saved jobs from backend"""
    response = handle_api_error(
        api_client.get_saved_jobs,
        st.session_state.user_id
    )
    
    if response and response['success']:
        saved_jobs_data = response['data']
        st.session_state.saved_jobs = saved_jobs_data.get('jobs', [])

def render_saved_jobs_page():
    """Render the saved jobs page"""
    st.markdown("## 📊 Your Saved Jobs")
    st.markdown("Track your job applications and manage your pipeline")
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh", help="Refresh saved jobs from server"):
            with st.spinner("Refreshing saved jobs..."):
                refresh_saved_jobs()
                st.rerun()
    
    with col2:
        # Filter by status
        status_filter = st.selectbox(
            "Filter by Status:",
            ["All"] + [status.split(" ", 1)[1] for status in settings.JOB_STATUS_OPTIONS],
            index=0
        )
    
    # Load saved jobs if not already loaded
    if not st.session_state.saved_jobs:
        refresh_saved_jobs()
    
    saved_jobs = st.session_state.saved_jobs
    
    # Filter jobs by status
    if status_filter != "All":
        saved_jobs = [job for job in saved_jobs if job.get('status', '').lower() == status_filter.lower()]
    
    if saved_jobs:
        # Show statistics
        st.markdown("### 📈 Pipeline Overview")
        
        status_counts = {}
        for job in st.session_state.saved_jobs:
            status = job.get('status', 'saved').title()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Display metrics
        cols = st.columns(len(status_counts))
        for i, (status, count) in enumerate(status_counts.items()):
            with cols[i]:
                st.metric(f"📊 {status}", count)
        
        st.markdown("---")
        st.markdown(f"### 📋 Your Jobs ({len(saved_jobs)} shown)")
        
        # Display saved jobs
        for i, job in enumerate(saved_jobs):
            action_data = render_saved_job_card(
                job,
                st.session_state.user_id,
                key_prefix=f"saved_{i}"
            )
            
            if action_data:
                if action_data['action'] == 'remove':
                    # Remove job
                    remove_response = handle_api_error(
                        api_client.remove_saved_job,
                        st.session_state.user_id,
                        action_data['job_id']
                    )
                    
                    if remove_response and remove_response['success']:
                        st.success("🗑️ Job removed successfully!")
                        refresh_saved_jobs()
                        st.rerun()
                
                elif action_data['action'] == 'update':
                    # Update job status
                    update_response = handle_api_error(
                        api_client.update_job_status,
                        st.session_state.user_id,
                        action_data['job_id'],
                        action_data['status'],
                        action_data['notes']
                    )
                    
                    if update_response and update_response['success']:
                        st.success("💾 Job status updated successfully!")
                        refresh_saved_jobs()
                        st.rerun()
    
    else:
        if status_filter == "All":
            st.info("📝 No saved jobs yet. Go to the Job Search page to find and save interesting opportunities!")
        else:
            st.info(f"📝 No jobs with status '{status_filter}' found.")
        
        # Quick link to search
        if st.button("🔍 Go to Job Search", use_container_width=True):
            st.switch_page("🔍 Job Search")

def render_analytics_page():
    """Render analytics and insights page"""
    st.markdown("## 📈 Analytics & Insights")
    st.markdown("Track your job search progress and get insights")
    
    # Get user stats
    stats_response = handle_api_error(
        api_client.get_user_stats,
        st.session_state.user_id
    )
    
    if stats_response and stats_response['success']:
        stats = stats_response['data']
        
        # Overview metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Jobs Saved", stats.get('total_jobs', 0))
        with col2:
            st.metric("🔥 Recent Activity", stats.get('recent_activity', 0))
        with col3:
            total_applied = sum(count for status, count in stats.get('by_status', {}).items() 
                             if status in ['applied', 'interviewing', 'offered'])
            st.metric("📝 Applications Active", total_applied)
        
        # Status breakdown
        st.markdown("### 📊 Application Pipeline")
        by_status = stats.get('by_status', {})
        
        if by_status:
            # Create columns for each status
            status_cols = st.columns(len(by_status))
            for i, (status, count) in enumerate(by_status.items()):
                with status_cols[i]:
                    st.metric(f"📈 {status.title()}", count)
            
            # Simple chart (you could use plotly for more advanced charts)
            st.markdown("### 📈 Status Distribution")
            chart_data = {status.title(): count for status, count in by_status.items()}
            st.bar_chart(chart_data)
        else:
            st.info("📊 No application data available yet. Save some jobs to see analytics!")
    
    else:
        st.error("❌ Unable to load analytics data")
    
    # Search history analytics
    if st.session_state.search_history:
        st.markdown("### 🔍 Search Activity")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🔍 Total Searches", len(st.session_state.search_history))
        with col2:
            total_results = sum(search['results_count'] for search in st.session_state.search_history)
            st.metric("📊 Total Results Found", total_results)
        
        # Recent searches
        st.markdown("### 🕒 Recent Search Queries")
        for search in reversed(st.session_state.search_history[-10:]):
            with st.expander(f"'{search['query']}' - {search['results_count']} results"):
                st.write(f"**Time:** {search['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Results:** {search['results_count']} jobs found")

def render_settings_page():
    """Render settings and admin page"""
    st.markdown("## ⚙️ Settings & Admin Tools")
    st.markdown("Manage application settings and backend operations")
    
    # System health section
    st.markdown("### 🔌 System Health")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Check System Health", use_container_width=True):
            with st.spinner("Checking system health..."):
                check_backend_health()
    
    with col2:
        if st.button("🔄 Trigger Job Indexing", use_container_width=True):
            indexing_response = handle_api_error(
                run_with_spinner,
                api_client.trigger_indexing,
                spinner_text="🔄 Triggering background job indexing..."
            )
            
            if indexing_response and indexing_response['success']:
                st.success("✅ Job indexing task has been triggered!")
                st.info("ℹ️ The indexing process runs in the background and may take several minutes.")
    
    # Display current health status
    if st.session_state.backend_health:
        health = st.session_state.backend_health
        
        st.markdown("#### 📊 Current Status")
        status = health.get('status', 'unknown')
        if status == 'healthy':
            st.success(f"✅ Overall System Status: {status.upper()}")
        else:
            st.warning(f"⚠️ Overall System Status: {status.upper()}")
        
        # Component details
        components = health.get('components', {})
        if components:
            st.markdown("#### 🔧 Component Status")
            
            for comp_name, comp_data in components.items():
                comp_status = comp_data.get('status', 'unknown')
                
                with st.expander(f"{comp_name.title()} - {comp_status.upper()}"):
                    st.json(comp_data)
    
    # User settings
    st.markdown("### 👤 User Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("User ID", value=st.session_state.user_id, disabled=True)
        
        if st.button("🔄 Generate New User ID", help="Generate a new user ID (will lose saved jobs)"):
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.saved_jobs = []
            st.success("✅ New User ID generated!")
            st.rerun()
    
    with col2:
        # Data management
        st.markdown("#### 🗂️ Data Management")
        
        if st.button("🗑️ Clear Search History"):
            st.session_state.search_history = []
            st.success("✅ Search history cleared!")
        
        if st.button("🔄 Refresh All Data"):
            with st.spinner("Refreshing all data..."):
                refresh_saved_jobs()
                check_backend_health()
            st.success("✅ All data refreshed!")
    
    # Application info
    st.markdown("### ℹ️ Application Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Frontend Version:** 1.0.0  
        **Backend URL:** {settings.BACKEND_BASE_URL}  
        **Session Started:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """)
    
    with col2:
        st.info(f"""
        **User ID:** `{st.session_state.user_id}`  
        **Saved Jobs:** {len(st.session_state.saved_jobs)}  
        **Search History:** {len(st.session_state.search_history)} queries
        """)

def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()
    
    # Check backend health on startup
    if st.session_state.backend_health is None:
        check_backend_health()
    
    # Render header
    render_header()
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Render the selected page
    if selected_page == "🔍 Job Search":
        render_search_page()
    elif selected_page == "📊 Saved Jobs":
        render_saved_jobs_page()
    elif selected_page == "📈 Analytics":
        render_analytics_page()
    elif selected_page == "⚙️ Settings & Admin":
        render_settings_page()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🚀 AI Job Discovery Platform | Built with ❤️ using Streamlit & FastAPI</p>
        <p>💡 <em>Powered by enterprise-grade ML and semantic search technology</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()