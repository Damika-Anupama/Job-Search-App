"""
Tests for Advanced Text Cleaning and Chunking functionality.

This module tests the text processing pipeline including HTML cleaning,
boilerplate removal, section identification, and intelligent chunking.
"""

import pytest
from src.job_search.ml.text_processing import (
    AdvancedTextProcessor, 
    process_job_text, 
    clean_job_text,
    TextChunk
)

class TestTextCleaning:
    """Test cases for text cleaning functionality"""
    
    def test_html_cleaning(self):
        """Test removal of HTML tags and entities"""
        processor = AdvancedTextProcessor()
        
        html_text = """
        <h1>Senior Python Developer</h1>
        <p>We are looking for a <strong>talented developer</strong> to join our team.</p>
        <ul>
            <li>5+ years experience</li>
            <li>Python &amp; Django knowledge</li>
        </ul>
        <br/><hr/>
        """
        
        cleaned = processor.clean_text(html_text)
        
        # Should remove HTML tags
        assert '<h1>' not in cleaned
        assert '<p>' not in cleaned
        assert '<ul>' not in cleaned
        assert '<li>' not in cleaned
        assert '<br/>' not in cleaned
        
        # Should preserve content
        assert 'Senior Python Developer' in cleaned
        assert 'talented developer' in cleaned
        assert '5+ years experience' in cleaned
        assert 'Python' in cleaned and 'Django' in cleaned
        
        # Should decode HTML entities
        assert '&amp;' not in cleaned
        assert '&' in cleaned or 'and' in cleaned
    
    def test_boilerplate_removal(self):
        """Test removal of common boilerplate text"""
        processor = AdvancedTextProcessor()
        
        boilerplate_text = """
        Senior Developer Position
        
        We are looking for a senior developer with Python experience.
        
        We are an equal opportunity employer and do not discriminate 
        based on race, gender, or age.
        
        Benefits include comprehensive health insurance, 401k matching,
        and flexible work arrangements.
        
        To apply, please send your resume to jobs@company.com.
        """
        
        cleaned = processor.clean_text(boilerplate_text)
        
        # Should preserve core job content
        assert 'Senior Developer Position' in cleaned
        assert 'Python experience' in cleaned
        
        # Should remove boilerplate (at least some of it)
        original_length = len(boilerplate_text)
        cleaned_length = len(cleaned)
        assert cleaned_length < original_length  # Some content was removed
    
    def test_whitespace_normalization(self):
        """Test normalization of excessive whitespace"""
        processor = AdvancedTextProcessor()
        
        messy_text = """
        
        
        Senior    Developer    Position
        
        
        
        We are looking for a developer.    
        
        
        Requirements:
        - 5+ years     experience
        - Python   knowledge
        
        
        """
        
        cleaned = processor.clean_text(messy_text)
        
        # Should normalize multiple spaces
        assert '    ' not in cleaned
        assert '   ' not in cleaned
        
        # Should reduce excessive newlines
        assert '\n\n\n' not in cleaned
        
        # Should preserve content structure
        assert 'Senior Developer Position' in cleaned
        assert 'Requirements:' in cleaned
        assert '5+ years' in cleaned

class TestSectionIdentification:
    """Test cases for section identification"""
    
    def test_section_identification(self):
        """Test identification of job description sections"""
        processor = AdvancedTextProcessor()
        
        sectioned_text = """
        Senior Python Developer
        
        We are a leading tech company looking for a senior developer.
        
        Responsibilities:
        - Develop Python applications
        - Work with Django framework
        - Collaborate with team
        
        Requirements:
        - 5+ years Python experience
        - Django knowledge required
        - Bachelor's degree preferred
        
        Benefits:
        - Health insurance
        - 401k matching
        - Flexible hours
        """
        
        sections = processor.identify_sections(sectioned_text)
        
        # Should identify main sections
        assert 'responsibilities' in sections
        assert 'requirements' in sections
        assert 'benefits' in sections
        
        # Should extract section content
        assert 'Develop Python applications' in sections.get('responsibilities', '')
        assert '5+ years Python experience' in sections.get('requirements', '')
        assert 'Health insurance' in sections.get('benefits', '')
    
    def test_section_headers_variations(self):
        """Test recognition of various section header formats"""
        processor = AdvancedTextProcessor()
        
        variations_text = """
        What you'll do:
        - Build applications
        
        What we're looking for:
        - Experience with Python
        
        What we offer:
        - Great benefits
        
        About us:
        - Tech company
        """
        
        sections = processor.identify_sections(variations_text)
        
        # Should recognize alternative section headers
        assert len(sections) >= 3  # Should find multiple sections
        
        # Content should be properly categorized
        found_content = ' '.join(sections.values()).lower()
        assert 'build applications' in found_content
        assert 'experience with python' in found_content
        assert 'great benefits' in found_content

class TestTextChunking:
    """Test cases for text chunking strategies"""
    
    def test_overlapping_chunking(self):
        """Test creation of overlapping text chunks"""
        processor = AdvancedTextProcessor(max_chunk_size=50, overlap_size=10)
        
        long_text = " ".join([f"Word{i}" for i in range(200)])  # Create 200-word text
        job_id = "test_job_001"
        
        chunks = processor.create_chunks(long_text, job_id, strategy='overlapping')
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be within size limits
        for chunk in chunks:
            assert chunk.word_count <= 50
            assert chunk.word_count >= processor.min_chunk_size or chunk.word_count == len(long_text.split())
        
        # Should have proper metadata
        for chunk in chunks:
            assert chunk.parent_job_id == job_id
            assert chunk.chunk_type == 'segment'
            assert isinstance(chunk.chunk_index, int)
    
    def test_section_based_chunking(self):
        """Test section-based chunking strategy"""
        processor = AdvancedTextProcessor(max_chunk_size=100)
        
        sectioned_job = """
        Senior Python Developer
        
        Responsibilities:
        """ + " ".join([f"Responsibility{i}" for i in range(30)]) + """
        
        Requirements:
        """ + " ".join([f"Requirement{i}" for i in range(40)]) + """
        """
        
        job_id = "test_job_002"
        chunks = processor.create_chunks(sectioned_job, job_id, strategy='sections')
        
        # Should create section-based chunks
        chunk_types = [chunk.chunk_type for chunk in chunks]
        assert 'responsibilities' in chunk_types or 'responsibilities_part' in str(chunk_types)
        assert 'requirements' in chunk_types or 'requirements_part' in str(chunk_types)
        
        # Should include section headers
        for chunk in chunks:
            if chunk.chunk_type.startswith('responsibilities'):
                assert chunk.section_header == 'Responsibilities'
    
    def test_hybrid_chunking_strategy(self):
        """Test hybrid chunking strategy selection"""
        processor = AdvancedTextProcessor()
        
        # Text with clear sections should use section-based chunking
        sectioned_text = """
        Job Title
        
        Responsibilities:
        - Task 1
        - Task 2
        
        Requirements:
        - Skill 1
        - Skill 2
        """
        
        chunks = processor.create_chunks(sectioned_text, "job1", strategy='hybrid')
        chunk_types = [chunk.chunk_type for chunk in chunks]
        
        # Should identify this as sectioned content
        assert any('responsibilities' in chunk_type for chunk_type in chunk_types)
        
        # Text without clear sections should use overlapping chunking
        unsectioned_text = " ".join([f"Word{i}" for i in range(200)])
        chunks2 = processor.create_chunks(unsectioned_text, "job2", strategy='hybrid')
        chunk_types2 = [chunk.chunk_type for chunk in chunks2]
        
        # Should fall back to overlapping for unsectioned content
        assert 'segment' in chunk_types2 or 'full' in chunk_types2

class TestChunkQuality:
    """Test cases for chunk quality assessment"""
    
    def test_chunk_quality_scoring(self):
        """Test chunk quality score calculation"""
        processor = AdvancedTextProcessor()
        
        # High quality chunk (technical content, good length)
        high_quality = """
        We are looking for a senior Python developer with 5+ years of experience.
        Requirements include Django, PostgreSQL, AWS, and Docker knowledge.
        Responsibilities involve developing scalable web applications and APIs.
        """
        
        score_high = processor._calculate_chunk_quality(high_quality)
        
        # Low quality chunk (very short, no technical content)
        low_quality = "Apply now!"
        score_low = processor._calculate_chunk_quality(low_quality)
        
        # High quality should score better
        assert score_high > score_low
        assert 0.0 <= score_high <= 1.0
        assert 0.0 <= score_low <= 1.0
    
    def test_chunk_filtering(self):
        """Test filtering of low-quality chunks"""
        processor = AdvancedTextProcessor(min_chunk_size=20)
        
        # Create mixed quality chunks
        chunks = [
            TextChunk("High quality chunk with technical content and good length", 
                     "segment", 0, "job1", 10, confidence_score=0.8),
            TextChunk("Short", "segment", 1, "job1", 1, confidence_score=0.2),
            TextChunk("Another good chunk with requirements and responsibilities", 
                     "segment", 2, "job1", 8, confidence_score=0.7),
            TextChunk("Low quality chunk", "segment", 3, "job1", 3, confidence_score=0.1)
        ]
        
        filtered = processor._filter_chunks(chunks)
        
        # Should filter out low-quality and short chunks
        assert len(filtered) < len(chunks)
        
        # Remaining chunks should have reasonable quality
        for chunk in filtered:
            assert chunk.confidence_score >= 0.3
            assert chunk.word_count >= processor.min_chunk_size or chunk.word_count >= 8

class TestEndToEndProcessing:
    """End-to-end tests for complete processing pipeline"""
    
    def test_complete_job_processing(self):
        """Test complete job processing pipeline"""
        sample_job = {
            'id': 'test_job_complete',
            'text': """
            <h1>Senior Python Developer - Remote</h1>
            
            <p>We are a leading technology company looking for an excellent opportunity!</p>
            
            <h2>Responsibilities:</h2>
            <ul>
                <li>Develop Python applications using Django</li>
                <li>Work with PostgreSQL and Redis databases</li>
                <li>Deploy applications on AWS infrastructure</li>
                <li>Collaborate with cross-functional teams</li>
            </ul>
            
            <h2>Requirements:</h2>
            <ul>
                <li>5+ years of Python development experience</li>
                <li>Strong knowledge of Django framework</li>
                <li>Experience with PostgreSQL and Redis</li>
                <li>AWS and Docker experience preferred</li>
                <li>Bachelor's degree in Computer Science</li>
            </ul>
            
            <h2>Benefits:</h2>
            <p>We offer comprehensive benefits including health insurance, 
            401k matching, and flexible work arrangements.</p>
            
            <p>We are an equal opportunity employer and do not discriminate.</p>
            <p>To apply, please send your resume to jobs@company.com</p>
            """,
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'location': 'Remote',
            'url': 'https://example.com/job'
        }
        
        chunks = process_job_text(sample_job, chunking_strategy='hybrid')
        
        # Should create multiple chunks
        assert len(chunks) > 0
        
        # Should have cleaned text (no HTML)
        for chunk in chunks:
            assert '<h1>' not in chunk.text
            assert '<ul>' not in chunk.text
            assert '<li>' not in chunk.text
        
        # Should preserve important content
        all_text = ' '.join(chunk.text for chunk in chunks)
        assert 'Python' in all_text
        assert 'Django' in all_text
        assert '5+ years' in all_text
        
        # Should have proper metadata
        for chunk in chunks:
            assert chunk.parent_job_id == 'test_job_complete'
            assert hasattr(chunk, 'original_title')
            assert chunk.original_title == 'Senior Python Developer'
            assert chunk.original_company == 'TechCorp'
    
    def test_processing_statistics(self):
        """Test processing statistics generation"""
        processor = AdvancedTextProcessor()
        
        sample_job = {
            'id': 'stats_test',
            'text': """
            Senior Developer Position
            
            Responsibilities:
            - Develop applications
            - Test software
            
            Requirements:
            - 3 years experience
            - Python knowledge
            """
        }
        
        chunks = processor.process_job_description(sample_job)
        stats = processor.get_processing_stats(chunks)
        
        # Should provide comprehensive statistics
        assert 'total_chunks' in stats
        assert 'chunk_types' in stats
        assert 'avg_words_per_chunk' in stats
        assert 'avg_quality_score' in stats
        
        assert stats['total_chunks'] == len(chunks)
        assert stats['avg_quality_score'] >= 0.0
        assert stats['avg_words_per_chunk'] > 0

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_empty_input_handling(self):
        """Test handling of empty or invalid input"""
        processor = AdvancedTextProcessor()
        
        # Empty string
        chunks = processor.process_job_description({'id': 'empty', 'text': ''})
        assert chunks == []
        
        # None text
        chunks = processor.process_job_description({'id': 'none', 'text': None})
        assert chunks == []
        
        # Very short text
        chunks = processor.process_job_description({'id': 'short', 'text': 'Job'})
        assert len(chunks) == 0  # Too short to create valid chunks
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML"""
        processor = AdvancedTextProcessor()
        
        malformed_html = """
        <h1>Job Title<h1>  <!-- Unclosed tag -->
        <p>Description with <strong>bold text
        <ul>
            <li>Item 1
            <li>Item 2</li>
        """
        
        cleaned = processor.clean_text(malformed_html)
        
        # Should handle malformed HTML gracefully
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
        assert 'Job Title' in cleaned
        assert 'Description' in cleaned

if __name__ == "__main__":
    # Run a simple test
    print("Testing text processing pipeline...")
    
    sample_job = {
        'id': 'test_manual',
        'text': """
        <h1>Senior Python Developer - Remote</h1>
        
        We are looking for a senior developer with Django experience.
        
        <h2>Requirements:</h2>
        <ul>
            <li>5+ years Python experience</li>
            <li>Django and PostgreSQL knowledge</li>
        </ul>
        
        <p>We are an equal opportunity employer.</p>
        """
    }
    
    chunks = process_job_text(sample_job)
    
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: {chunk.chunk_type} ({chunk.word_count} words)")
        print(f"    Text: {chunk.text[:100]}...")
        print(f"    Quality: {chunk.confidence_score:.2f}")
    
    print("✅ Text processing test completed!")