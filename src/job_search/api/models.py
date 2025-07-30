"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Search API Models
class SearchRequest(BaseModel):
    """Enhanced request model for job search with NER-based filtering"""
    query: str = Field(
        ..., 
        description="Search query to find relevant job postings",
        examples=[
            "python developer remote",
            "machine learning AI engineer",
            "frontend react javascript"
        ]
    )
    locations: List[str] = Field(
        default=[],
        description="Filter jobs by location (OR logic)",
        examples=[["remote"], ["san francisco", "new york"]]
    )
    required_skills: List[str] = Field(
        default=[],
        description="Skills that MUST be present (AND logic)",
        examples=[["python"], ["react"]]
    )
    preferred_skills: List[str] = Field(
        default=[],
        description="Skills that boost relevance (OR logic)",
        examples=[["docker", "redis"], ["postgresql", "mongodb"]]
    )
    exclude_keywords: List[str] = Field(
        default=[],
        description="Keywords to exclude from results",
        examples=[["internship", "unpaid"], ["on-site"]]
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return (1-50)"
    )
    
    # NER-based metadata filters
    experience_level: Optional[str] = Field(
        default=None,
        description="Filter by experience level: entry, mid, senior, executive",
        examples=["senior", "entry"]
    )
    min_experience_years: Optional[int] = Field(
        default=None,
        ge=0,
        le=30,
        description="Minimum years of experience required"
    )
    max_experience_years: Optional[int] = Field(
        default=None,
        ge=0,
        le=30,
        description="Maximum years of experience required"
    )
    min_salary: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum salary requirement (annual USD)"
    )
    max_salary: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum salary range (annual USD)"
    )
    remote_only: Optional[bool] = Field(
        default=None,
        description="Filter for remote work opportunities only"
    )
    has_salary_info: Optional[bool] = Field(
        default=None,
        description="Filter for jobs that include salary information"
    )
    required_education: List[str] = Field(
        default=[],
        description="Required education levels or degrees",
        examples=[["bachelor", "master"], ["computer science"]]
    )
    required_benefits: List[str] = Field(
        default=[],
        description="Required benefits or perks",
        examples=[["health insurance", "401k"], ["remote work"]]
    )

class JobResult(BaseModel):
    """Enhanced individual job search result with NER metadata"""
    id: str = Field(description="Unique job posting identifier")
    score: float = Field(description="Final relevance score")
    text: str = Field(description="Complete job posting text")
    vector_score: float = Field(default=0.0, description="Vector similarity score")
    cross_score: float = Field(default=0.0, description="Cross-encoder score")
    
    # Basic job information
    title: Optional[str] = Field(default=None, description="Job title")
    company: Optional[str] = Field(default=None, description="Company name")
    location: Optional[str] = Field(default=None, description="Job location")
    url: Optional[str] = Field(default=None, description="Job posting URL")
    source: Optional[str] = Field(default=None, description="Job board source")
    posted_date: Optional[str] = Field(default=None, description="Date job was posted")
    
    # NER-extracted metadata
    extracted_skills: List[str] = Field(default=[], description="Skills extracted from job description")
    experience_years: Optional[int] = Field(default=None, description="Required years of experience")
    experience_level: Optional[str] = Field(default=None, description="Experience level (entry/mid/senior/executive)")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary (USD)")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary (USD)")
    salary_amount: Optional[int] = Field(default=None, description="Single salary amount (USD)")
    remote_work: Optional[bool] = Field(default=False, description="Supports remote work")
    extracted_locations: List[str] = Field(default=[], description="Locations extracted from description")
    education_requirements: List[str] = Field(default=[], description="Education requirements")
    benefits: List[str] = Field(default=[], description="Job benefits and perks")
    
    # Metadata quality indicators
    skills_count: int = Field(default=0, description="Number of skills extracted")
    has_salary_info: bool = Field(default=False, description="Whether salary information was found")
    has_experience_info: bool = Field(default=False, description="Whether experience info was found")

class SearchResponse(BaseModel):
    """Response model for job search"""
    source: str = Field(description="Data source: 'cache' or 'pinecone'")
    results: List[JobResult] = Field(description="List of relevant job postings")
    total_found: int = Field(description="Total jobs found before pagination")
    filters_applied: Dict[str, Any] = Field(description="Applied filters summary")
    reranked: bool = Field(default=False, description="Whether results were reranked")
    candidates_retrieved: int = Field(default=0, description="Candidates for reranking")

# User Tracking Models
class SaveJobRequest(BaseModel):
    """Request to save a job for user tracking"""
    job_id: str = Field(description="Unique identifier of the job to save")
    job_data: Dict[str, Any] = Field(description="Complete job data")

class UpdateJobStatusRequest(BaseModel):
    """Request to update job application status"""
    status: str = Field(
        description="New status for the job",
        examples=["saved", "applied", "interviewing", "offered", "rejected", "withdrawn"]
    )
    notes: Optional[str] = Field(default="", description="Optional notes about the status change")

class SavedJob(BaseModel):
    """Model for a saved job"""
    job_id: str = Field(description="Unique identifier of the saved job")
    saved_at: datetime = Field(description="When the job was saved")
    status: str = Field(description="Current status of the job application")
    notes: str = Field(description="User notes about this job")
    job_data: Dict[str, Any] = Field(description="Complete job information")
    application_date: Optional[datetime] = Field(default=None, description="Date when applied")
    interview_dates: List[datetime] = Field(default=[], description="List of interview dates")
    updated_at: datetime = Field(description="Last time this job was updated")

class SavedJobsResponse(BaseModel):
    """Response containing user's saved jobs"""
    user_id: str = Field(description="User identifier")
    total_saved: int = Field(description="Total number of saved jobs")
    jobs: List[SavedJob] = Field(description="List of saved jobs")
    statistics: Dict[str, Any] = Field(description="Job application statistics")

class UserStatsResponse(BaseModel):
    """Response containing user statistics"""
    user_id: str = Field(description="User identifier")
    total_jobs: int = Field(description="Total number of saved jobs")
    by_status: Dict[str, int] = Field(description="Count of jobs by status")
    recent_activity: int = Field(description="Jobs updated in last 7 days")

# Health Check Models
class ComponentHealth(BaseModel):
    """Health status of a system component"""
    status: str = Field(description="Component status: healthy, unhealthy, degraded")
    message: Optional[str] = Field(default=None, description="Additional status information")

class HealthResponse(BaseModel):
    """System health check response"""
    status: str = Field(description="Overall system status")
    mode: str = Field(description="Current application mode")
    components: Dict[str, ComponentHealth] = Field(description="Individual component health")