"""
Job card component for displaying job listings.
"""

import streamlit as st
import re
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

def extract_job_info(job_text: str) -> Dict[str, str]:
    """Extract structured information from job text"""
    lines = job_text.split('\n')
    
    # Try to extract company and location from first few lines
    company = ""
    location = ""
    title = ""
    
    # Look for patterns like "Company Name | Location" or "Title at Company"
    for line in lines[:3]:
        line = line.strip()
        if not line:
            continue
            
        # Pattern: "Title at Company" or "Title - Company"
        if " at " in line:
            parts = line.split(" at ", 1)
            if len(parts) == 2:
                title = parts[0].strip()
                company = parts[1].strip()
        elif " - " in line and not title:
            parts = line.split(" - ", 1)
            if len(parts) == 2:
                title = parts[0].strip()
                company = parts[1].strip()
        elif "|" in line:
            parts = line.split("|")
            if len(parts) >= 2:
                company = parts[0].strip()
                location = parts[1].strip()
        elif not title and line:
            title = line
    
    # Extract location patterns
    location_patterns = [
        r'(Remote|remote)',
        r'(San Francisco|SF|New York|NYC|Los Angeles|LA|Boston|Seattle|Austin|Denver|Chicago)',
        r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, State
        r'([A-Z][a-z]+,\s*[A-Z][a-z]+)',  # City, Country
    ]
    
    if not location:
        for pattern in location_patterns:
            match = re.search(pattern, job_text)
            if match:
                location = match.group(1)
                break
    
    return {
        "title": title or "Software Engineer",  # Default title
        "company": company or "Company",  # Default company
        "location": location or "Location not specified"
    }

def format_relevance_score(score: float) -> str:
    """Format relevance score as percentage with color"""
    percentage = int(score * 100)
    
    if percentage >= 90:
        return f"🎯 **{percentage}%** match"
    elif percentage >= 80:
        return f"🔥 **{percentage}%** match"
    elif percentage >= 70:
        return f"✨ **{percentage}%** match"
    elif percentage >= 60:
        return f"👍 **{percentage}%** match"
    else:
        return f"📊 **{percentage}%** match"

def render_job_card(job: Dict[str, Any], user_id: str, show_save_button: bool = True, 
                   saved_jobs: Optional[list] = None, key_prefix: str = "job") -> Optional[str]:
    """
    Render a job card with all information and actions.
    
    Args:
        job: Job data from API
        user_id: Current user ID
        show_save_button: Whether to show save button
        saved_jobs: List of saved jobs to check against
        key_prefix: Prefix for Streamlit keys
        
    Returns:
        Action taken ('save', 'similar', None)
    """
    
    # Extract job information
    job_info = extract_job_info(job.get('text', ''))
    job_id = job.get('id', str(uuid.uuid4()))
    score = job.get('score', 0.0)
    
    # Check if job is already saved
    is_saved = False
    if saved_jobs:
        is_saved = any(saved_job.get('job_id') == job_id for saved_job in saved_jobs)
    
    # Create card container with styling
    with st.container():
        # Add custom CSS for card styling
        st.markdown("""
        <style>
        .job-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .job-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        .job-title {
            color: #2c3e50;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .job-company {
            color: #34495e;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .job-location {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .relevance-score {
            font-size: 1.1em;
            margin-bottom: 15px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Card header with job info
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f'<div class="job-title">{job_info["title"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="job-company">🏢 {job_info["company"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="job-location">📍 {job_info["location"]}</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="relevance-score">{format_relevance_score(score)}</div>', 
                       unsafe_allow_html=True)
        
        with col3:
            # Action buttons
            if show_save_button and not is_saved:
                if st.button("💾 Save", key=f"{key_prefix}_save_{job_id}", 
                           help="Save this job to your tracking list"):
                    return "save"
            elif is_saved:
                st.success("✅ Saved")
            
            if st.button("🔍 Similar", key=f"{key_prefix}_similar_{job_id}",
                        help="Find similar jobs"):
                return "similar"
        
        # Job description in expandable section
        with st.expander("📄 View Full Description", expanded=False):
            # Clean up the job text for better display
            job_text = job.get('text', '').strip()
            
            # Split into paragraphs and clean up
            paragraphs = [p.strip() for p in job_text.split('\n') if p.strip()]
            
            # Display first paragraph as summary
            if paragraphs:
                st.markdown("**Summary:**")
                st.write(paragraphs[0])
                
                if len(paragraphs) > 1:
                    st.markdown("**Full Description:**")
                    for paragraph in paragraphs[1:]:
                        st.write(paragraph)
        
        # Additional metadata if available
        metadata_cols = st.columns(4)
        
        with metadata_cols[0]:
            if 'vector_score' in job:
                st.caption(f"🎯 Vector: {job['vector_score']:.2f}")
        
        with metadata_cols[1]:
            if 'cross_score' in job:
                st.caption(f"🔄 Rerank: {job['cross_score']:.2f}")
        
        with metadata_cols[2]:
            if 'source' in job.get('metadata', {}):
                st.caption(f"📊 From: {job['metadata']['source']}")
        
        with metadata_cols[3]:
            st.caption(f"🆔 ID: {job_id[:8]}...")
        
        st.divider()
    
    return None

def render_saved_job_card(job: Dict[str, Any], user_id: str, key_prefix: str = "saved") -> Optional[Dict[str, Any]]:
    """
    Render a saved job card with status tracking.
    
    Args:
        job: Saved job data
        user_id: Current user ID
        key_prefix: Prefix for Streamlit keys
        
    Returns:
        Dictionary with action info if any action taken
    """
    from ..config.settings import settings
    
    job_data = job.get('job_data', {})
    job_id = job.get('job_id', '')
    current_status = job.get('status', 'saved')
    notes = job.get('notes', '')
    saved_at = job.get('saved_at', '')
    
    # Extract job information
    job_info = extract_job_info(job_data.get('text', ''))
    
    with st.container():
        # Header with job info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {job_info['title']}")
            st.markdown(f"**🏢 {job_info['company']}** | 📍 {job_info['location']}")
            
            if saved_at:
                try:
                    saved_date = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                    st.caption(f"💾 Saved on {saved_date.strftime('%B %d, %Y')}")
                except:
                    st.caption(f"💾 Saved: {saved_at}")
        
        with col2:
            score = job_data.get('score', 0.0)
            st.markdown(format_relevance_score(score))
        
        # Status tracking
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            new_status = st.selectbox(
                "Application Status:",
                options=settings.JOB_STATUS_OPTIONS,
                index=settings.JOB_STATUS_OPTIONS.index(f"📌 {current_status.title()}") 
                      if f"📌 {current_status.title()}" in settings.JOB_STATUS_OPTIONS 
                      else 0,
                key=f"{key_prefix}_status_{job_id}"
            )
        
        with col2:
            new_notes = st.text_input(
                "Notes:",
                value=notes,
                key=f"{key_prefix}_notes_{job_id}",
                placeholder="Add notes about this application..."
            )
        
        with col3:
            if st.button("🗑️ Remove", key=f"{key_prefix}_remove_{job_id}",
                        help="Remove from saved jobs"):
                return {"action": "remove", "job_id": job_id}
            
            if st.button("💾 Update", key=f"{key_prefix}_update_{job_id}",
                        help="Update status and notes"):
                # Extract status without emoji
                clean_status = new_status.split(" ", 1)[1].lower() if " " in new_status else new_status.lower()
                return {
                    "action": "update",
                    "job_id": job_id,
                    "status": clean_status,
                    "notes": new_notes
                }
        
        # Job description in expander
        with st.expander("📄 View Full Description"):
            st.write(job_data.get('text', 'No description available'))
        
        # Metadata
        if job_data.get('vector_score') or job_data.get('cross_score'):
            col1, col2, col3 = st.columns(3)
            with col1:
                if 'vector_score' in job_data:
                    st.caption(f"🎯 Vector Score: {job_data['vector_score']:.2f}")
            with col2:
                if 'cross_score' in job_data:
                    st.caption(f"🔄 Rerank Score: {job_data['cross_score']:.2f}")
            with col3:
                st.caption(f"🆔 {job_id[:12]}...")
        
        st.divider()
    
    return None