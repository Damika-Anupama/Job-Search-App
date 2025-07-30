"""
Tests for Named Entity Recognition (NER) metadata extraction.

This module tests the NER functionality for extracting structured metadata
from job descriptions including skills, experience, salary, and other entities.
"""

import pytest
from src.job_search.ml.ner import extract_job_metadata, JobMetadataExtractor

class TestNERExtraction:
    """Test cases for NER metadata extraction"""
    
    def test_skill_extraction(self):
        """Test extraction of technical skills from job descriptions"""
        job_text = """
        Senior Python Developer position at TechCorp. We are looking for someone 
        with experience in Python, Django, FastAPI, PostgreSQL, and AWS. 
        Knowledge of React and TypeScript is a plus. Experience with Docker 
        and Kubernetes preferred.
        """
        
        metadata = extract_job_metadata(job_text)
        
        # Check that skills were extracted
        assert 'skills' in metadata
        skills = [skill.lower() for skill in metadata['skills']]
        
        # Should extract major technologies mentioned
        expected_skills = ['python', 'django', 'fastapi', 'postgresql', 'aws', 'react', 'typescript', 'docker', 'kubernetes']
        found_skills = [skill for skill in expected_skills if skill in skills]
        
        # Should find at least half of the expected skills
        assert len(found_skills) >= len(expected_skills) // 2, f"Expected skills: {expected_skills}, Found: {skills}"
    
    def test_experience_extraction(self):
        """Test extraction of experience requirements"""
        job_text = """
        We are seeking a Senior Software Engineer with 5+ years of experience 
        in full-stack development. This is a senior-level position requiring 
        extensive experience in web technologies.
        """
        
        metadata = extract_job_metadata(job_text)
        
        # Check experience information
        assert 'experience' in metadata
        experience = metadata['experience']
        
        # Should detect experience years or level
        assert experience.get('years') == 5 or experience.get('level') == 'senior'
    
    def test_salary_extraction(self):
        """Test extraction of salary information"""
        test_cases = [
            ("Salary: $120,000", {'amount': 120000}),
            ("$100k - $150k annually", {'min': 100000, 'max': 150000}),
            ("Compensation range: $80,000 - $120,000", {'min': 80000, 'max': 120000}),
            ("120k salary", {'amount': 120000})
        ]
        
        for job_text, expected in test_cases:
            metadata = extract_job_metadata(job_text)
            salary = metadata.get('salary', {})
            
            # Check if any expected salary info was found
            found_match = False
            for key, value in expected.items():
                if salary.get(key) == value:
                    found_match = True
                    break
            
            assert found_match, f"Expected {expected} in salary data {salary} for text: {job_text}"
    
    def test_remote_work_detection(self):
        """Test detection of remote work opportunities"""
        remote_texts = [
            "This is a remote position with flexible hours",
            "Work from home opportunity available",
            "Remote work, anywhere in the US",
            "100% remote, distributed team"
        ]
        
        non_remote_texts = [
            "On-site position in San Francisco",
            "Office-based role in New York",
            "In-person collaboration required"
        ]
        
        for text in remote_texts:
            metadata = extract_job_metadata(text)
            assert metadata.get('remote_work', False), f"Should detect remote work in: {text}"
        
        for text in non_remote_texts:
            metadata = extract_job_metadata(text)
            assert not metadata.get('remote_work', False), f"Should not detect remote work in: {text}"
    
    def test_location_extraction(self):
        """Test extraction of job locations"""
        job_text = """
        Software Engineer position in San Francisco, CA. We also have 
        offices in New York and Austin. Remote work available for 
        candidates in the United States.
        """
        
        metadata = extract_job_metadata(job_text)
        locations = [loc.lower() for loc in metadata.get('locations', [])]
        
        # Should extract some location information
        expected_locations = ['san francisco', 'new york', 'austin', 'united states', 'ca']
        found_locations = [loc for loc in expected_locations if any(loc in location for location in locations)]
        
        assert len(found_locations) > 0, f"Expected to find locations, got: {locations}"
    
    def test_education_extraction(self):
        """Test extraction of education requirements"""
        job_text = """
        Requirements: Bachelor's degree in Computer Science or related field.
        Master's degree preferred. PhD candidates welcome.
        """
        
        metadata = extract_job_metadata(job_text)
        education = [edu.lower() for edu in metadata.get('education', [])]
        
        # Should extract education-related terms
        expected_terms = ['bachelor', 'master', 'phd', 'computer science', 'degree']
        found_terms = [term for term in expected_terms if any(term in edu for edu in education)]
        
        assert len(found_terms) > 0, f"Expected education terms, got: {education}"
    
    def test_benefits_extraction(self):
        """Test extraction of job benefits"""
        job_text = """
        Great benefits package including health insurance, dental coverage,
        401k matching, flexible PTO, and gym membership. Stock options available.
        """
        
        metadata = extract_job_metadata(job_text)
        benefits = [benefit.lower() for benefit in metadata.get('benefits', [])]
        
        # Should extract some benefits
        expected_benefits = ['health insurance', 'dental', '401k', 'pto', 'gym', 'stock options']
        found_benefits = [benefit for benefit in expected_benefits if any(benefit in b for b in benefits)]
        
        assert len(found_benefits) > 0, f"Expected benefits, got: {benefits}"
    
    def test_empty_input(self):
        """Test handling of empty or invalid input"""
        # Empty string
        metadata = extract_job_metadata("")
        assert isinstance(metadata, dict)
        
        # None input
        metadata = extract_job_metadata(None)
        assert isinstance(metadata, dict)
        
        # Very short text
        metadata = extract_job_metadata("Job")
        assert isinstance(metadata, dict)
    
    def test_comprehensive_job_description(self):
        """Test extraction from a comprehensive job description"""
        job_text = """
        Senior Python Developer - Remote
        
        TechCorp is seeking a Senior Python Developer with 5+ years of experience
        to join our distributed team. This is a remote position with competitive
        salary range of $120,000 - $150,000.
        
        Requirements:
        - Bachelor's degree in Computer Science or related field
        - 5+ years of Python development experience
        - Experience with Django, FastAPI, PostgreSQL
        - Knowledge of AWS, Docker, Kubernetes
        - Strong React and TypeScript skills preferred
        
        Benefits:
        - Health insurance and dental coverage
        - 401k with company matching
        - Flexible PTO policy
        - $1000 learning stipend
        - Remote work with flexible hours
        
        This is a senior-level position with opportunities for growth.
        """
        
        metadata = extract_job_metadata(job_text)
        
        # Verify multiple categories were extracted
        assert len(metadata.get('skills', [])) >= 3, "Should extract multiple skills"
        assert metadata.get('experience', {}).get('years') == 5, "Should extract experience years"
        assert metadata.get('experience', {}).get('level') == 'senior', "Should extract experience level"
        assert metadata.get('salary', {}).get('min') == 120000, "Should extract minimum salary"
        assert metadata.get('salary', {}).get('max') == 150000, "Should extract maximum salary"
        assert metadata.get('remote_work') == True, "Should detect remote work"
        assert len(metadata.get('education', [])) >= 1, "Should extract education requirements"
        assert len(metadata.get('benefits', [])) >= 2, "Should extract multiple benefits"

class TestNERWithoutSpaCy:
    """Test NER functionality when spaCy is not available (regex-only mode)"""
    
    def test_regex_skill_extraction(self):
        """Test skill extraction using regex patterns only"""
        extractor = JobMetadataExtractor()
        # Simulate spaCy not being available
        extractor.nlp = None
        extractor.matcher = None
        
        job_text = "Python developer with Django and PostgreSQL experience"
        skills = extractor.extract_skills_regex(job_text)
        
        # Should find some skills even with regex only
        skills_lower = [skill.lower() for skill in skills]
        assert 'python' in skills_lower or 'django' in skills_lower or 'postgresql' in skills_lower
    
    def test_regex_experience_extraction(self):
        """Test experience extraction using regex patterns only"""
        extractor = JobMetadataExtractor()
        
        job_text = "Looking for a senior developer with 8 years of experience"
        experience = extractor.extract_experience_regex(job_text)
        
        assert experience.get('years') == 8 or experience.get('level') == 'senior'
    
    def test_regex_salary_extraction(self):
        """Test salary extraction using regex patterns only"""
        extractor = JobMetadataExtractor()
        
        test_cases = [
            ("Salary $100,000", 100000),
            ("$80k annually", 80000),
            ("150k compensation", 150000)
        ]
        
        for job_text, expected_amount in test_cases:
            salary = extractor.extract_salary_regex(job_text)
            assert salary.get('amount') == expected_amount, f"Expected {expected_amount}, got {salary}"

if __name__ == "__main__":
    # Run a simple test
    print("Testing NER extraction...")
    
    sample_job = """
    Senior Python Developer - Remote
    
    We are looking for a Senior Python Developer with 5+ years of experience 
    to join our team. You'll work with Django, FastAPI, PostgreSQL, and AWS.
    Salary: $120,000 - $150,000
    
    Requirements:
    - Bachelor's degree in Computer Science
    - Experience with React and TypeScript
    - Knowledge of Docker and Kubernetes
    
    Benefits include health insurance, 401k, and flexible work hours.
    """
    
    metadata = extract_job_metadata(sample_job)
    print(f"Extracted metadata: {metadata}")
    print("✅ NER extraction test completed!")