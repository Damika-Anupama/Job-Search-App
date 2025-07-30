"""
Named Entity Recognition (NER) for Job Description Metadata Extraction.

This module extracts structured metadata from job descriptions including:
- Skills and technologies
- Experience levels
- Salary information
- Company names
- Locations
- Education requirements

Uses spaCy for NLP processing with custom patterns and rules.
"""

import re
import os
from typing import Dict, List, Set, Optional, Any
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Try to import spaCy, handle graceful fallback
try:
    import spacy
    from spacy.matcher import Matcher
    from spacy.lang.en import English
    SPACY_AVAILABLE = True
    logger.info("✅ spaCy NLP library loaded successfully")
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("⚠️ spaCy not available - NER extraction will be limited to regex patterns")

class JobMetadataExtractor:
    """
    Extracts structured metadata from job descriptions using NER and pattern matching.
    """
    
    def __init__(self):
        """Initialize the metadata extractor with spaCy model and custom patterns."""
        self.nlp = None
        self.matcher = None
        self._load_model()
        self._setup_skill_patterns()
        self._setup_experience_patterns()
        self._setup_salary_patterns()
        
    def _load_model(self):
        """Load spaCy English model if available."""
        if not SPACY_AVAILABLE:
            logger.warning("🚫 spaCy not available - using regex-only extraction")
            return
            
        try:
            # Try to load the English model
            self.nlp = spacy.load("en_core_web_sm")
            self.matcher = Matcher(self.nlp.vocab)
            logger.info("📚 Loaded spaCy en_core_web_sm model")
        except OSError:
            logger.warning("⚠️ en_core_web_sm model not found - attempting to use smaller model")
            try:
                # Fallback to basic English model
                self.nlp = English()
                self.matcher = Matcher(self.nlp.vocab)
                logger.info("📝 Using basic English tokenizer")
            except Exception as e:
                logger.error(f"❌ Failed to load any spaCy model: {e}")
                self.nlp = None
                self.matcher = None
                
    def _setup_skill_patterns(self):
        """Define patterns for technical skills and technologies."""
        if not self.matcher:
            return
            
        # Programming languages
        programming_languages = [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", 
            "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Julia",
            "Clojure", "F#", "Haskell", "Erlang", "Elixir", "Dart", "VB.NET"
        ]
        
        # Frameworks and libraries
        frameworks = [
            "React", "Angular", "Vue", "Django", "Flask", "FastAPI", "Express", "Node.js",
            "Spring", "Laravel", "Rails", "ASP.NET", "Flutter", "React Native", "Ionic",
            "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy", "OpenCV",
            "Docker", "Kubernetes", "Jenkins", "Terraform", "Ansible", "Chef", "Puppet"
        ]
        
        # Databases
        databases = [
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite", 
            "Oracle", "SQL Server", "Cassandra", "DynamoDB", "Firebase", "Neo4j",
            "InfluxDB", "MariaDB", "CouchDB", "Apache Kafka", "RabbitMQ"
        ]
        
        # Cloud platforms
        cloud_platforms = [
            "AWS", "Azure", "GCP", "Google Cloud", "Heroku", "DigitalOcean", "Linode",
            "IBM Cloud", "Oracle Cloud", "Alibaba Cloud", "Vercel", "Netlify"
        ]
        
        # Tools and technologies
        tools = [
            "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Slack", "VS Code", "IntelliJ",
            "Postman", "Figma", "Adobe", "Photoshop", "Sketch", "Tableau", "Power BI",
            "Grafana", "Prometheus", "New Relic", "DataDog", "Splunk", "ELK Stack"
        ]
        
        # Combine all skills
        all_skills = programming_languages + frameworks + databases + cloud_platforms + tools
        
        # Create patterns for each skill
        for skill in all_skills:
            pattern = [{"LOWER": skill.lower().replace(" ", "")}]  # Handle multi-word skills
            if skill.replace(" ", "") not in [p[0]["LOWER"] for p in [pattern]]:
                self.matcher.add(f"SKILL_{skill.upper().replace(' ', '_')}", [pattern])
        
        # Pattern for general skill mentions
        skill_patterns = [
            [{"LOWER": "experience"}, {"LOWER": "with"}, {"IS_ALPHA": True}],
            [{"LOWER": "knowledge"}, {"LOWER": "of"}, {"IS_ALPHA": True}],
            [{"LOWER": "proficient"}, {"LOWER": "in"}, {"IS_ALPHA": True}],
            [{"LOWER": "skilled"}, {"LOWER": "in"}, {"IS_ALPHA": True}],
        ]
        
        for i, pattern in enumerate(skill_patterns):
            self.matcher.add(f"SKILL_PATTERN_{i}", [pattern])
    
    def _setup_experience_patterns(self):
        """Define patterns for experience level extraction."""
        if not self.matcher:
            return
            
        experience_patterns = [
            # Years of experience
            [{"LIKE_NUM": True}, {"LOWER": {"IN": ["years", "year", "yrs", "yr"]}}, 
             {"LOWER": {"IN": ["experience", "exp"]}}],
            [{"LIKE_NUM": True}, {"TEXT": "+"}, {"LOWER": {"IN": ["years", "year", "yrs", "yr"]}}],
            
            # Experience levels
            [{"LOWER": {"IN": ["junior", "senior", "lead", "principal", "staff", "entry-level"]}}],
            [{"LOWER": "entry"}, {"LOWER": "level"}],
            [{"LOWER": {"IN": ["intern", "internship", "graduate", "trainee"]}}],
            [{"LOWER": "mid"}, {"LOWER": "level"}],
            [{"LOWER": {"IN": ["expert", "architect", "manager", "director", "head"]}}],
        ]
        
        for i, pattern in enumerate(experience_patterns):
            self.matcher.add(f"EXPERIENCE_{i}", [pattern])
    
    def _setup_salary_patterns(self):
        """Define patterns for salary extraction."""
        if not self.matcher:
            return
            
        salary_patterns = [
            # Dollar amounts
            [{"TEXT": "$"}, {"LIKE_NUM": True}],
            [{"TEXT": "$"}, {"LIKE_NUM": True}, {"LOWER": "k"}],
            [{"LIKE_NUM": True}, {"LOWER": "k"}],
            
            # Salary ranges
            [{"TEXT": "$"}, {"LIKE_NUM": True}, {"TEXT": "-"}, {"TEXT": "$"}, {"LIKE_NUM": True}],
            [{"LIKE_NUM": True}, {"TEXT": "-"}, {"LIKE_NUM": True}, {"LOWER": "k"}],
            
            # Annual/hourly indicators
            [{"LOWER": {"IN": ["salary", "compensation", "pay", "wage"]}}, 
             {"TEXT": ":"}, {"TEXT": "$"}, {"LIKE_NUM": True}],
        ]
        
        for i, pattern in enumerate(salary_patterns):
            self.matcher.add(f"SALARY_{i}", [pattern])
    
    def extract_skills_regex(self, text: str) -> List[str]:
        """Extract skills using regex patterns as fallback."""
        skills = set()
        
        # Common programming languages and technologies
        skill_patterns = {
            # Programming languages
            r'\b(?:Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b': 'programming',
            r'\b(?:React|Angular|Vue|Django|Flask|FastAPI|Express|Node\.js|Spring)\b': 'framework',
            r'\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|SQLite)\b': 'database',
            r'\b(?:AWS|Azure|GCP|Google Cloud|Docker|Kubernetes)\b': 'cloud',
            r'\b(?:Git|GitHub|GitLab|Jira|VS Code|Postman)\b': 'tool',
        }
        
        for pattern, category in skill_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(matches)
        
        return list(skills)
    
    def extract_experience_regex(self, text: str) -> Dict[str, Any]:
        """Extract experience information using regex."""
        experience_info = {}
        
        # Years of experience
        years_pattern = r'(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)'
        years_matches = re.findall(years_pattern, text, re.IGNORECASE)
        if years_matches:
            experience_info['years'] = int(years_matches[0])
        
        # Experience levels
        level_patterns = {
            'entry': r'\b(?:entry[\-\s]*level|junior|intern|graduate|trainee)\b',
            'mid': r'\b(?:mid[\-\s]*level|intermediate|regular)\b', 
            'senior': r'\b(?:senior|lead|principal|staff)\b',
            'executive': r'\b(?:manager|director|head|vp|cto|ceo)\b'
        }
        
        for level, pattern in level_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                experience_info['level'] = level
                break
        
        return experience_info
    
    def extract_salary_regex(self, text: str) -> Dict[str, Any]:
        """Extract salary information using regex."""
        salary_info = {}
        
        # Salary patterns with context to avoid false positives
        salary_patterns = [
            # Salary ranges with $ signs (most common format)
            r'\$(\d{1,3}(?:,\d{3})*)\s*[-–—]\s*\$(\d{1,3}(?:,\d{3})*)',
            r'salary[:\s]*\$(\d{1,3}(?:,\d{3})*)\s*[-–—]\s*\$(\d{1,3}(?:,\d{3})*)',
            
            # K format ranges
            r'(\d{2,3})k\s*[-–—]\s*(\d{2,3})k',
            
            # Single salary amounts with context
            r'salary[:\s]*\$(\d{1,3}(?:,\d{3})*)',
            r'compensation[:\s]*\$(\d{1,3}(?:,\d{3})*)',
            r'pay[:\s]*\$(\d{1,3}(?:,\d{3})*)',
            
            # Salary with 'k' suffix (avoiding 401k)
            r'salary[:\s]*(\d{2,3})k',
            r'(?<!401\s)(\d{2,3})k(?:\s|$)',  # Not preceded by "401 "
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match = matches[0]
                if isinstance(match, tuple) and len(match) == 2:  # Range
                    if 'k' in pattern.lower():
                        salary_info['min'] = int(match[0]) * 1000
                        salary_info['max'] = int(match[1]) * 1000
                    else:
                        salary_info['min'] = int(match[0].replace(',', ''))
                        salary_info['max'] = int(match[1].replace(',', ''))
                else:  # Single value
                    amount_str = match if isinstance(match, str) else match[0]
                    amount = int(amount_str.replace(',', ''))
                    if 'k' in pattern.lower():
                        amount *= 1000
                    # Only consider reasonable salary amounts (20k - 1M)
                    if 20000 <= amount <= 1000000:
                        salary_info['amount'] = amount
                break
        
        return salary_info
    
    def extract_metadata(self, job_text: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from job description text.
        
        Args:
            job_text: The job description text to analyze
            
        Returns:
            Dictionary containing extracted metadata
        """
        if not job_text:
            return {}
        
        metadata = {
            'skills': [],
            'experience': {},
            'salary': {},
            'locations': [],
            'education': [],
            'benefits': [],
            'company_size': None,
            'remote_work': False
        }
        
        try:
            # Use spaCy if available, otherwise fall back to regex
            if self.nlp and self.matcher:
                metadata.update(self._extract_with_spacy(job_text))
            else:
                metadata.update(self._extract_with_regex(job_text))
                
            # Additional regex-based extractions
            metadata['skills'].extend(self.extract_skills_regex(job_text))
            metadata['experience'].update(self.extract_experience_regex(job_text))
            metadata['salary'].update(self.extract_salary_regex(job_text))
            
            # Remove duplicates from skills
            metadata['skills'] = list(set(metadata['skills']))
            
            # Extract additional metadata
            metadata['remote_work'] = self._detect_remote_work(job_text)
            metadata['locations'].extend(self._extract_locations(job_text))
            metadata['education'].extend(self._extract_education(job_text))
            metadata['benefits'].extend(self._extract_benefits(job_text))
            
            logger.debug(f"🔍 Extracted metadata: {len(metadata['skills'])} skills, "
                        f"experience: {metadata['experience']}, remote: {metadata['remote_work']}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting metadata: {e}")
            
        return metadata
    
    def _extract_with_spacy(self, text: str) -> Dict[str, Any]:
        """Extract metadata using spaCy NLP model."""
        metadata = {'skills': [], 'experience': {}, 'salary': {}}
        
        try:
            doc = self.nlp(text)
            matches = self.matcher(doc)
            
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                span = doc[start:end]
                
                if label.startswith('SKILL'):
                    metadata['skills'].append(span.text)
                elif label.startswith('EXPERIENCE'):
                    # Process experience matches
                    if 'level' not in metadata['experience']:
                        metadata['experience']['level'] = span.text.lower()
                elif label.startswith('SALARY'):
                    # Process salary matches
                    metadata['salary']['raw'] = span.text
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ == 'ORG':
                    if 'companies' not in metadata:
                        metadata['companies'] = []
                    metadata['companies'].append(ent.text)
                elif ent.label_ in ['GPE', 'LOC']:  # Geographic entities
                    if 'locations' not in metadata:
                        metadata['locations'] = []
                    metadata['locations'].append(ent.text)
                    
        except Exception as e:
            logger.error(f"❌ Error in spaCy extraction: {e}")
            
        return metadata
    
    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Extract metadata using regex patterns only."""
        return {
            'skills': self.extract_skills_regex(text),
            'experience': self.extract_experience_regex(text),
            'salary': self.extract_salary_regex(text)
        }
    
    def _detect_remote_work(self, text: str) -> bool:
        """Detect if job supports remote work."""
        remote_keywords = [
            'remote', 'work from home', 'wfh', 'telecommute', 'distributed',
            'anywhere', 'location independent', 'home office', 'virtual'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in remote_keywords)
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract location information."""
        locations = []
        
        # Common location patterns
        location_patterns = [
            r'\b(?:New York|NYC|San Francisco|SF|Los Angeles|LA|Chicago|Boston|Seattle|Austin|Denver|Miami|Atlanta|Dallas|Phoenix|Portland|San Diego|Washington DC|DC)\b',
            r'\b(?:California|CA|New York|NY|Texas|TX|Florida|FL|Washington|WA|Illinois|IL|Massachusetts|MA|Colorado|CO|Oregon|OR)\b',
            r'\b(?:United States|USA|US|Canada|UK|United Kingdom|Germany|France|Netherlands|Australia|Singapore|India)\b'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            locations.extend(matches)
        
        return list(set(locations))
    
    def _extract_education(self, text: str) -> List[str]:
        """Extract education requirements."""
        education = []
        
        education_patterns = [
            r'\b(?:Bachelor|BA|BS|Master|MS|MA|PhD|Doctorate|Associate|AA|AS)\b',
            r'\b(?:degree|diploma|certification|certificate)\b',
            r'\b(?:Computer Science|CS|Engineering|Mathematics|Physics|Business|MBA)\b'
        ]
        
        for pattern in education_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            education.extend(matches)
        
        return list(set(education))
    
    def _extract_benefits(self, text: str) -> List[str]:
        """Extract job benefits and perks."""
        benefits = []
        
        benefit_keywords = [
            'health insurance', 'dental', 'vision', '401k', 'retirement',
            'vacation', 'pto', 'paid time off', 'flexible hours', 'gym',
            'stock options', 'equity', 'bonus', 'commission', 'healthcare',
            'life insurance', 'disability insurance', 'tuition reimbursement',
            'professional development', 'conference', 'training'
        ]
        
        text_lower = text.lower()
        for benefit in benefit_keywords:
            if benefit in text_lower:
                benefits.append(benefit)
        
        return benefits

# Global extractor instance
_extractor = None

def get_metadata_extractor() -> JobMetadataExtractor:
    """Get or create the global metadata extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = JobMetadataExtractor()
    return _extractor

def extract_job_metadata(job_text: str) -> Dict[str, Any]:
    """
    Convenience function to extract metadata from job text.
    
    Args:
        job_text: Job description text
        
    Returns:
        Dictionary containing extracted metadata
    """
    extractor = get_metadata_extractor()
    return extractor.extract_metadata(job_text)

# For testing the module
if __name__ == "__main__":
    # Test with sample job description
    sample_job = """
    Senior Python Developer - Remote
    
    We are looking for a Senior Python Developer with 5+ years of experience 
    to join our team. You'll work with Django, FastAPI, PostgreSQL, and AWS.
    
    Requirements:
    - Bachelor's degree in Computer Science
    - Experience with React and TypeScript
    - Knowledge of Docker and Kubernetes
    - $120,000 - $150,000 salary
    
    Benefits include health insurance, 401k, and flexible work hours.
    """
    
    logger.info("🧪 Testing NER metadata extraction")
    metadata = extract_job_metadata(sample_job)
    logger.info(f"📊 Extracted metadata: {metadata}")