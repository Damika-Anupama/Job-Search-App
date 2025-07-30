"""
Advanced Text Cleaning and Chunking for Job Descriptions.

This module provides sophisticated text processing to improve embedding quality by:
1. Removing boilerplate text and noise from job descriptions
2. Cleaning HTML remnants and normalizing text
3. Intelligently chunking long job descriptions into focused segments
4. Creating overlapping chunks for better semantic coverage

The goal is to extract the core signal from job descriptions while removing
marketing jargon, legal boilerplate, and other noise that can dilute embeddings.
"""

import re
import html
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ..core.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class TextChunk:
    """Represents a processed text chunk from a job description."""
    text: str
    chunk_type: str  # 'title', 'summary', 'requirements', 'responsibilities', 'benefits', 'full'
    chunk_index: int  # Position in the document
    parent_job_id: str
    word_count: int
    overlap_start: int = 0
    overlap_end: int = 0
    confidence_score: float = 1.0  # Quality score for the chunk
    section_header: Optional[str] = None

class AdvancedTextProcessor:
    """
    Advanced text processor for cleaning and chunking job descriptions.
    """
    
    def __init__(self, 
                 max_chunk_size: int = 512,
                 overlap_size: int = 50,
                 min_chunk_size: int = 100):
        """
        Initialize the text processor.
        
        Args:
            max_chunk_size: Maximum words per chunk
            overlap_size: Number of words to overlap between chunks
            min_chunk_size: Minimum words for a valid chunk
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        # Compile regex patterns for better performance
        self._compile_patterns()
        
        logger.info(f"✅ Text processor initialized - max_chunk: {max_chunk_size}, "
                   f"overlap: {overlap_size}, min_chunk: {min_chunk_size}")
    
    def _compile_patterns(self):
        """Compile regex patterns for text cleaning."""
        
        # HTML and formatting patterns
        self.html_pattern = re.compile(r'<[^>]+>')
        self.html_entities = re.compile(r'&[a-zA-Z0-9#]+;')
        self.multiple_spaces = re.compile(r'\s+')
        self.line_breaks = re.compile(r'\n+')
        
        # Boilerplate removal patterns (more conservative)
        self.boilerplate_patterns = [
            # Equal opportunity statements (full sentences)
            re.compile(r'(?i)\b.*equal\s+opportunity\s+employer.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*we\s+do\s+not\s+discriminate.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*committed\s+to\s+diversity.*?\.', re.MULTILINE),
            
            # Application instructions (full sentences)
            re.compile(r'(?i)\b.*to\s+apply.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*send\s+your\s+resume.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*please\s+submit.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*apply\s+online.*?\.', re.MULTILINE),
            
            # Legal and compliance (full sentences)
            re.compile(r'(?i)\b.*drug[-\s]free\s+workplace.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*background\s+check.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*right\s+to\s+work.*?\.', re.MULTILINE),
            
            # Only remove very specific generic phrases
            re.compile(r'(?i)\b.*great\s+opportunity\s+to\s+join.*?\.', re.MULTILINE),
            re.compile(r'(?i)\b.*excellent\s+opportunity\s+to\s+join.*?\.', re.MULTILINE),
        ]
        
        # Section header patterns
        self.section_headers = {
            'responsibilities': re.compile(r'(?i)^(responsibilities|duties|what\s+you.ll\s+do|your\s+role|job\s+description)[\s\:]*$', re.MULTILINE),
            'requirements': re.compile(r'(?i)^(requirements|qualifications|what\s+we.re\s+looking\s+for|must\s+have|preferred|skills)[\s\:]*$', re.MULTILINE),
            'benefits': re.compile(r'(?i)^(benefits|perks|what\s+we\s+offer|compensation|package)[\s\:]*$', re.MULTILINE),
            'about': re.compile(r'(?i)^(about\s+us|about\s+the\s+company|company|overview)[\s\:]*$', re.MULTILINE),
            'location': re.compile(r'(?i)^(location|where|office)[\s\:]*$', re.MULTILINE)
        }
        
        # Content quality patterns
        self.low_quality_patterns = [
            re.compile(r'^.{0,20}$'),  # Very short lines
            re.compile(r'^\s*[-•\*]\s*$'),  # Empty bullet points
            re.compile(r'^\s*\d+\.\s*$'),  # Empty numbered lists
            re.compile(r'^\s*[:\-\=]{3,}\s*$'),  # Separator lines
        ]
    
    def clean_text(self, text: str) -> str:
        """
        Clean job description text by removing HTML, boilerplate, and normalizing.
        
        Args:
            text: Raw job description text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        original_length = len(text)
        
        # 1. HTML cleaning
        text = self.html_pattern.sub(' ', text)
        text = html.unescape(text)  # Convert HTML entities
        text = self.html_entities.sub(' ', text)
        
        # 2. Remove boilerplate text
        removed_patterns = 0
        for pattern in self.boilerplate_patterns:
            matches = pattern.findall(text)
            if matches:
                text = pattern.sub('', text)
                removed_patterns += len(matches)
        
        # 3. Normalize whitespace
        text = self.line_breaks.sub('\n', text)
        text = self.multiple_spaces.sub(' ', text)
        
        # 4. Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)  # Multiple exclamations
        text = re.sub(r'[?]{2,}', '?', text)  # Multiple questions
        text = re.sub(r'[\.]{3,}', '...', text)  # Multiple dots
        
        # 5. Clean up formatting artifacts
        text = re.sub(r'\s*\n\s*\n\s*', '\n\n', text)  # Multiple newlines
        text = re.sub(r'^\s+|\s+$', '', text)  # Leading/trailing whitespace
        
        cleaned_length = len(text)
        reduction_pct = ((original_length - cleaned_length) / original_length) * 100 if original_length > 0 else 0
        
        logger.debug(f"🧹 Text cleaned: {original_length} → {cleaned_length} chars "
                    f"({reduction_pct:.1f}% reduction, {removed_patterns} patterns removed)")
        
        return text
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        """
        Identify and extract different sections from job description.
        
        Args:
            text: Cleaned job description text
            
        Returns:
            Dictionary mapping section types to their content
        """
        sections = {}
        lines = text.split('\n')
        current_section = 'summary'
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a section header
            section_found = None
            for section_type, pattern in self.section_headers.items():
                if pattern.search(line):
                    section_found = section_type
                    break
            
            if section_found:
                # Save previous section if it has content
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                # Add line to current section
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        logger.debug(f"📋 Identified {len(sections)} sections: {list(sections.keys())}")
        return sections
    
    def create_chunks(self, text: str, job_id: str, strategy: str = 'hybrid') -> List[TextChunk]:
        """
        Create chunks from job description using specified strategy.
        
        Args:
            text: Cleaned job description text
            job_id: Unique identifier for the job
            strategy: Chunking strategy ('sections', 'overlapping', 'hybrid')
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        
        if strategy == 'sections':
            chunks = self._create_section_chunks(text, job_id)
        elif strategy == 'overlapping':
            chunks = self._create_overlapping_chunks(text, job_id)
        elif strategy == 'hybrid':
            # Use section-based chunking if sections found, otherwise overlapping
            sections = self.identify_sections(text)
            if len(sections) > 1:
                chunks = self._create_section_chunks(text, job_id)
            else:
                chunks = self._create_overlapping_chunks(text, job_id)
        
        # Filter out low-quality chunks
        chunks = self._filter_chunks(chunks)
        
        logger.info(f"📄 Created {len(chunks)} chunks for job {job_id} using {strategy} strategy")
        return chunks
    
    def _create_section_chunks(self, text: str, job_id: str) -> List[TextChunk]:
        """Create chunks based on identified sections."""
        chunks = []
        sections = self.identify_sections(text)
        
        for i, (section_type, section_content) in enumerate(sections.items()):
            if not section_content:
                continue
                
            words = section_content.split()
            word_count = len(words)
            
            if word_count < self.min_chunk_size:
                # Merge small sections with the next one
                continue
            
            if word_count <= self.max_chunk_size:
                # Section fits in one chunk
                chunk = TextChunk(
                    text=section_content,
                    chunk_type=section_type,
                    chunk_index=i,
                    parent_job_id=job_id,
                    word_count=word_count,
                    section_header=section_type.title(),
                    confidence_score=self._calculate_chunk_quality(section_content)
                )
                chunks.append(chunk)
            else:
                # Split large section into overlapping chunks
                sub_chunks = self._split_long_section(section_content, section_type, job_id, i)
                chunks.extend(sub_chunks)
        
        # Always create a full-text chunk for fallback
        full_text_words = text.split()
        if len(full_text_words) >= self.min_chunk_size:
            full_chunk = TextChunk(
                text=text,
                chunk_type='full',
                chunk_index=len(chunks),
                parent_job_id=job_id,
                word_count=len(full_text_words),
                confidence_score=0.8  # Lower score for full text
            )
            chunks.append(full_chunk)
        
        return chunks
    
    def _create_overlapping_chunks(self, text: str, job_id: str) -> List[TextChunk]:
        """Create overlapping chunks from text."""
        chunks = []
        words = text.split()
        
        if len(words) <= self.max_chunk_size:
            # Single chunk
            chunk = TextChunk(
                text=text,
                chunk_type='full',
                chunk_index=0,
                parent_job_id=job_id,
                word_count=len(words),
                confidence_score=self._calculate_chunk_quality(text)
            )
            return [chunk]
        
        # Create overlapping chunks
        start = 0
        chunk_index = 0
        
        while start < len(words):
            end = min(start + self.max_chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            # Calculate overlap
            overlap_start = max(0, start - self.overlap_size) if start > 0 else 0
            overlap_end = min(end + self.overlap_size, len(words)) if end < len(words) else end
            
            chunk = TextChunk(
                text=chunk_text,
                chunk_type='segment',
                chunk_index=chunk_index,
                parent_job_id=job_id,
                word_count=len(chunk_words),
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                confidence_score=self._calculate_chunk_quality(chunk_text)
            )
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start += self.max_chunk_size - self.overlap_size
            chunk_index += 1
        
        return chunks
    
    def _split_long_section(self, text: str, section_type: str, job_id: str, base_index: int) -> List[TextChunk]:
        """Split a long section into overlapping chunks."""
        chunks = []
        words = text.split()
        start = 0
        sub_index = 0
        
        while start < len(words):
            end = min(start + self.max_chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunk = TextChunk(
                text=chunk_text,
                chunk_type=f"{section_type}_part",
                chunk_index=base_index * 100 + sub_index,  # Unique indexing
                parent_job_id=job_id,
                word_count=len(chunk_words),
                section_header=section_type.title(),
                confidence_score=self._calculate_chunk_quality(chunk_text)
            )
            chunks.append(chunk)
            
            start += self.max_chunk_size - self.overlap_size
            sub_index += 1
        
        return chunks
    
    def _calculate_chunk_quality(self, text: str) -> float:
        """Calculate quality score for a chunk (0.0 to 1.0)."""
        if not text:
            return 0.0
        
        score = 1.0
        
        # Penalize very short text
        words = text.split()
        if len(words) < 20:
            score *= 0.5
        
        # Penalize low-quality patterns
        for pattern in self.low_quality_patterns:
            if pattern.search(text):
                score *= 0.7
                break
        
        # Reward technical content
        technical_keywords = ['experience', 'required', 'skills', 'responsibilities', 'qualifications']
        tech_count = sum(1 for keyword in technical_keywords if keyword.lower() in text.lower())
        score += tech_count * 0.1
        
        # Reward structured content (bullet points, lists)
        if re.search(r'[•\-\*]\s+', text) or re.search(r'\d+\.\s+', text):
            score += 0.1
        
        return min(1.0, score)
    
    def _filter_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Filter out low-quality chunks."""
        filtered = []
        
        for chunk in chunks:
            # Skip chunks that are too short
            if chunk.word_count < self.min_chunk_size:
                continue
            
            # Skip very low-quality chunks
            if chunk.confidence_score < 0.3:
                continue
            
            # Skip chunks with mostly boilerplate
            boilerplate_ratio = self._calculate_boilerplate_ratio(chunk.text)
            if boilerplate_ratio > 0.7:
                continue
            
            filtered.append(chunk)
        
        logger.debug(f"🔍 Filtered {len(chunks)} → {len(filtered)} chunks")
        return filtered
    
    def _calculate_boilerplate_ratio(self, text: str) -> float:
        """Calculate ratio of boilerplate content in text."""
        if not text:
            return 1.0
        
        original_length = len(text)
        cleaned = text
        
        # Remove matches from boilerplate patterns
        for pattern in self.boilerplate_patterns:
            cleaned = pattern.sub('', cleaned)
        
        removed_length = original_length - len(cleaned)
        return removed_length / original_length if original_length > 0 else 0.0
    
    def process_job_description(self, job_data: Dict[str, Any], 
                              chunking_strategy: str = 'hybrid') -> List[TextChunk]:
        """
        Complete processing pipeline for a job description.
        
        Args:
            job_data: Job data dictionary with 'text' and 'id' fields
            chunking_strategy: Strategy for chunking ('sections', 'overlapping', 'hybrid')
            
        Returns:
            List of processed TextChunk objects
        """
        job_id = job_data.get('id', 'unknown')
        raw_text = job_data.get('text', '')
        
        if not raw_text:
            logger.warning(f"⚠️ No text found for job {job_id}")
            return []
        
        logger.info(f"🔄 Processing job {job_id} - {len(raw_text)} chars, strategy: {chunking_strategy}")
        
        # 1. Clean the text
        cleaned_text = self.clean_text(raw_text)
        
        if not cleaned_text:
            logger.warning(f"⚠️ No content remaining after cleaning for job {job_id}")
            return []
        
        # 2. Create chunks
        chunks = self.create_chunks(cleaned_text, job_id, chunking_strategy)
        
        # 3. Add original job metadata to chunks
        for chunk in chunks:
            # Preserve original job metadata in chunk
            chunk.original_title = job_data.get('title', '')
            chunk.original_company = job_data.get('company', '')
            chunk.original_location = job_data.get('location', '')
            chunk.original_url = job_data.get('url', '')
            chunk.original_source = job_data.get('source', '')
        
        logger.info(f"✅ Processed job {job_id} → {len(chunks)} chunks")
        return chunks
    
    def get_processing_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about processed chunks."""
        if not chunks:
            return {}
        
        chunk_types = {}
        word_counts = []
        quality_scores = []
        
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            word_counts.append(chunk.word_count)
            quality_scores.append(chunk.confidence_score)
        
        return {
            'total_chunks': len(chunks),
            'chunk_types': chunk_types,
            'avg_words_per_chunk': sum(word_counts) / len(word_counts),
            'avg_quality_score': sum(quality_scores) / len(quality_scores),
            'min_words': min(word_counts),
            'max_words': max(word_counts),
            'total_words': sum(word_counts)
        }

# Global processor instance
_processor = None

def get_text_processor() -> AdvancedTextProcessor:
    """Get or create the global text processor instance."""
    global _processor
    if _processor is None:
        _processor = AdvancedTextProcessor()
    return _processor

def process_job_text(job_data: Dict[str, Any], 
                    chunking_strategy: str = 'hybrid') -> List[TextChunk]:
    """
    Convenience function to process job description text.
    
    Args:
        job_data: Job data dictionary
        chunking_strategy: Chunking strategy to use
        
    Returns:
        List of processed TextChunk objects
    """
    processor = get_text_processor()
    return processor.process_job_description(job_data, chunking_strategy)

def clean_job_text(text: str) -> str:
    """
    Convenience function to clean job description text.
    
    Args:
        text: Raw job description text
        
    Returns:
        Cleaned text
    """
    processor = get_text_processor()
    return processor.clean_text(text)

# For testing the module
if __name__ == "__main__":
    # Test with sample job description
    sample_job = {
        'id': 'test_job_001',
        'text': """
        <h1>Senior Python Developer - Remote</h1>
        
        <p>We are a leading technology company looking for an excellent opportunity 
        to join our fast-growing team!</p>
        
        <h2>Responsibilities:</h2>
        <ul>
            <li>Develop and maintain Python applications</li>
            <li>Work with Django and FastAPI frameworks</li>
            <li>Collaborate with cross-functional teams</li>
            <li>Write clean, maintainable code</li>
        </ul>
        
        <h2>Requirements:</h2>
        <ul>
            <li>5+ years of Python experience</li>
            <li>Experience with PostgreSQL and Redis</li>
            <li>Knowledge of AWS and Docker</li>
            <li>Bachelor's degree preferred</li>
        </ul>
        
        <h2>Benefits:</h2>
        <p>Comprehensive benefits package including health insurance, 401k, 
        and flexible work arrangements.</p>
        
        <p>We are an equal opportunity employer and do not discriminate based on 
        race, gender, age, or any other protected characteristic.</p>
        
        <p>To apply, please send your resume to jobs@company.com</p>
        """,
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'Remote'
    }
    
    logger.info("🧪 Testing text processing pipeline")
    chunks = process_job_text(sample_job)
    
    processor = get_text_processor()
    stats = processor.get_processing_stats(chunks)
    
    logger.info(f"📊 Processing stats: {stats}")
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Chunk {i+1}: {chunk.chunk_type} ({chunk.word_count} words, "
                   f"quality: {chunk.confidence_score:.2f})")
        logger.info(f"  Text: {chunk.text[:100]}...")
    
    logger.info("✅ Text processing test completed!")