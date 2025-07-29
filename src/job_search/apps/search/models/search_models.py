"""
Domain models for the search functionality.

These models represent the core business entities and value objects
for the search domain, with proper validation and business rules.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class SearchType(str, Enum):
    """Types of search operations"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    SIMILAR_JOBS = "similar_jobs"


class SalaryRange(BaseModel):
    """Salary range specification"""
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    period: str = Field(default="yearly", pattern=r"^(hourly|daily|weekly|monthly|yearly)$")
    
    @validator('max_amount')
    def max_greater_than_min(cls, v, values):
        if v is not None and values.get('min_amount') is not None:
            if v < values['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v


class LocationFilter(BaseModel):
    """Location-based filtering"""
    cities: List[str] = Field(default=[], description="Specific cities")
    states: List[str] = Field(default=[], description="States/provinces")
    countries: List[str] = Field(default=[], description="Countries")
    remote_ok: bool = Field(default=False, description="Include remote positions")
    hybrid_ok: bool = Field(default=False, description="Include hybrid positions")
    radius_km: Optional[int] = Field(None, ge=1, le=500, description="Search radius in km")
    
    @validator('cities', 'states', 'countries')
    def normalize_locations(cls, v):
        return [location.strip().lower() for location in v if location.strip()]


class ExperienceLevel(str, Enum):
    """Job experience levels"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"


class CompanySize(str, Enum):
    """Company size categories"""
    STARTUP = "startup"          # 1-50 employees
    SMALL = "small"              # 51-200 employees
    MEDIUM = "medium"            # 201-1000 employees
    LARGE = "large"              # 1001-5000 employees
    ENTERPRISE = "enterprise"    # 5000+ employees


class SearchQuery(BaseModel):
    """
    Comprehensive search query with all filtering options.
    
    This is the main value object that encapsulates all search parameters
    and business rules for job searching.
    """
    
    # Core search parameters
    text: str = Field(..., min_length=1, max_length=500, description="Main search query")
    search_type: SearchType = Field(default=SearchType.SEMANTIC, description="Type of search to perform")
    
    # Result parameters
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    candidate_pool_size: Optional[int] = Field(default=100, ge=10, le=1000, description="Size of candidate pool for reranking")
    
    # Filtering parameters
    locations: List[str] = Field(default=[], description="Location filters (cities, 'remote', etc.)")
    location_filter: Optional[LocationFilter] = Field(None, description="Advanced location filtering")
    
    required_skills: List[str] = Field(default=[], max_items=10, description="Skills that must be present")
    preferred_skills: List[str] = Field(default=[], max_items=20, description="Skills that boost relevance")
    exclude_keywords: List[str] = Field(default=[], max_items=10, description="Keywords to exclude")
    
    # Experience and compensation
    experience_levels: List[ExperienceLevel] = Field(default=[], description="Desired experience levels")
    salary_range: Optional[SalaryRange] = Field(None, description="Salary requirements")
    
    # Company preferences
    company_sizes: List[CompanySize] = Field(default=[], description="Preferred company sizes")
    company_names: List[str] = Field(default=[], max_items=20, description="Specific companies")
    exclude_companies: List[str] = Field(default=[], max_items=50, description="Companies to exclude")
    
    # Job type preferences
    job_types: List[str] = Field(default=[], description="Full-time, part-time, contract, etc.")
    remote_preference: Optional[bool] = Field(None, description="Remote work preference")
    
    # ML and ranking preferences
    enable_reranking: bool = Field(default=True, description="Enable ML reranking")
    personalization_enabled: bool = Field(default=True, description="Enable personalized results")
    diversity_boost: float = Field(default=0.1, ge=0.0, le=1.0, description="Boost result diversity")
    
    # Technical parameters
    namespace: Optional[str] = Field(None, description="Vector database namespace")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    
    # Temporal filters
    posted_after: Optional[datetime] = Field(None, description="Only jobs posted after this date")
    posted_before: Optional[datetime] = Field(None, description="Only jobs posted before this date")
    
    @validator('text')
    def validate_query_text(cls, v):
        """Ensure query text is meaningful"""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError('Query text cannot be empty')
        # Remove excessive whitespace
        return ' '.join(cleaned.split())
    
    @validator('required_skills', 'preferred_skills', 'exclude_keywords')
    def normalize_skills(cls, v):
        """Normalize skill names"""
        return [skill.strip().lower() for skill in v if skill.strip()]
    
    @validator('posted_after', 'posted_before')
    def validate_date_range(cls, v, values, field):
        """Ensure date range makes sense"""
        if field.name == 'posted_before' and v is not None:
            posted_after = values.get('posted_after')
            if posted_after is not None and v < posted_after:
                raise ValueError('posted_before must be after posted_after')
        return v


class CompanyInfo(BaseModel):
    """Company information"""
    name: str
    size: Optional[CompanySize] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    review_count: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2030)


class UserInteraction(BaseModel):
    """User interaction with a job"""
    action: str  # viewed, saved, applied, clicked, etc.
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default={})


class JobDocument(BaseModel):
    """
    Rich job document with all enriched information.
    
    This represents a job posting with all the metadata,
    scores, and user-specific information attached.
    """
    
    # Core job information
    id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    description: str = Field(..., description="Full job description")
    
    # Location information
    location: Optional[str] = Field(None, description="Job location")
    is_remote: bool = Field(default=False, description="Remote work allowed")
    is_hybrid: bool = Field(default=False, description="Hybrid work model")
    
    # Job details
    job_type: Optional[str] = Field(None, description="Full-time, part-time, etc.")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Required experience level")
    skills_required: List[str] = Field(default=[], description="Required skills")
    skills_preferred: List[str] = Field(default=[], description="Preferred skills")
    
    # Compensation
    salary_min: Optional[Decimal] = Field(None, description="Minimum salary")
    salary_max: Optional[Decimal] = Field(None, description="Maximum salary")
    salary_currency: str = Field(default="USD", description="Salary currency")
    
    # Metadata
    posted_date: Optional[datetime] = Field(None, description="When job was posted")
    source: str = Field(..., description="Data source (linkedin, indeed, etc.)")
    source_url: Optional[str] = Field(None, description="Original job posting URL")
    
    # Search relevance
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall relevance score")
    vector_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Vector similarity score")
    rerank_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Reranking score")
    
    # User-specific data (populated if user context available)
    is_saved: bool = Field(default=False, description="User has saved this job")
    application_status: Optional[str] = Field(None, description="User's application status")
    user_interactions: List[UserInteraction] = Field(default=[], description="User interaction history")
    
    # Enriched data
    company_info: Optional[CompanyInfo] = Field(None, description="Enriched company information")
    similar_jobs_count: int = Field(default=0, description="Number of similar jobs available")
    
    @classmethod
    def from_search_result(cls, search_result: Dict[str, Any]) -> 'JobDocument':
        """Create JobDocument from raw search result"""
        metadata = search_result.get('metadata', {})
        
        return cls(
            id=search_result.get('id', ''),
            title=metadata.get('title', ''),
            company_name=metadata.get('company', ''),
            description=metadata.get('text', ''),
            location=metadata.get('location'),
            source=metadata.get('source', 'unknown'),
            source_url=metadata.get('url'),
            posted_date=metadata.get('posted_date'),
            relevance_score=search_result.get('score', 0.0),
            vector_score=search_result.get('score', 0.0),
            skills_required=metadata.get('skills_required', []),
            job_type=metadata.get('job_type'),
            is_remote=metadata.get('remote', False),
            salary_min=metadata.get('salary_min'),
            salary_max=metadata.get('salary_max')
        )


class SearchResult(BaseModel):
    """
    Complete search result with metadata and statistics.
    """
    
    jobs: List[JobDocument] = Field(..., description="List of matching jobs")
    total_found: int = Field(..., ge=0, description="Total jobs found (before pagination)")
    query: SearchQuery = Field(..., description="Original search query")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default={}, description="Search execution metadata")
    processing_time_ms: Optional[int] = Field(None, description="Search processing time")
    cached: bool = Field(default=False, description="Result served from cache")
    
    # Statistics
    search_stats: Dict[str, Any] = Field(default={}, description="Search statistics")
    
    # Faceted search results (for future use)
    facets: Dict[str, List[Dict[str, Any]]] = Field(default={}, description="Faceted search results")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create from dictionary (for cache retrieval)"""
        return cls(**data)
    
    @property
    def has_more_results(self) -> bool:
        """Check if there are more results available"""
        return len(self.jobs) < self.total_found
    
    @property
    def average_relevance_score(self) -> float:
        """Calculate average relevance score"""
        if not self.jobs:
            return 0.0
        return sum(job.relevance_score for job in self.jobs) / len(self.jobs)