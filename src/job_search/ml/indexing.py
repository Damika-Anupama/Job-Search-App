import numpy as np
from pinecone import Pinecone
from ..core.config import settings, AppMode
from .embeddings import embedding_service, EmbeddingServiceError
from .ner import extract_job_metadata
from .text_processing import process_job_text, TextChunk
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Configuration shortcuts
APP_MODE = settings.APP_MODE
PINECONE_API_KEY = settings.PINECONE_API_KEY
PINECONE_INDEX_NAME = settings.PINECONE_INDEX_NAME
HF_MODEL_DIMENSION = settings.HF_MODEL_DIMENSION

def get_embedding(text: str) -> list[float]:
    """
    Generates a vector embedding for the given text using the configured embedding service.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats representing the embedding
        
    Raises:
        EmbeddingServiceError: If embedding generation fails
    """
    if APP_MODE == AppMode.LIGHTWEIGHT:
        raise EmbeddingServiceError("Embeddings not supported in lightweight mode")
    
    try:
        # Use fallback for cloud-ml mode to maintain availability during indexing
        fallback = (APP_MODE == AppMode.CLOUD_ML)
        return embedding_service.get_embedding(text, fallback=fallback)
    except EmbeddingServiceError as e:
        logger.error(f"Embedding generation failed for text: {text[:100]}... Error: {e}")
        raise


# --- Pinecone Initialization (New Object-Oriented Way) ---
def get_pinecone_index():
    """Initializes and returns a Pinecone index object."""
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY is not set in the environment.")

    # 1. Create an instance of the Pinecone class
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # 2. Check if the index exists
    existing_indexes = [index.name for index in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing_indexes:
        logger.info(f"🔍 Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
        # 3. Create the index if it doesn't exist
        from pinecone import ServerlessSpec
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=HF_MODEL_DIMENSION,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        logger.info(f"✅ Index '{settings.PINECONE_INDEX_NAME}' created successfully.")

    # 4. Return a handle to the specific index
    return pc.Index(PINECONE_INDEX_NAME)

# This line executes when the module is imported, initializing the index.
index = get_pinecone_index()
logger.info(f"✅ Successfully connected to Pinecone index '{settings.PINECONE_INDEX_NAME}'.")
# --- End Pinecone Initialization ---


def embed_and_index(jobs: list[dict], batch_size: int = 16, chunking_strategy: str = 'hybrid'):
    """
    Advanced job processing pipeline with text cleaning, chunking, NER, and embedding.
    
    This enhanced version:
    1. Cleans job descriptions (removes HTML, boilerplate, normalizes text)
    2. Intelligently chunks long job descriptions into focused segments
    3. Extracts structured metadata using NER (skills, experience, salary, etc.)
    4. Generates high-quality semantic embeddings for each chunk
    5. Stores chunks with rich metadata in Pinecone for precise search
    
    Args:
        jobs: List of job dictionaries with 'text' and 'id' fields
        batch_size: Number of job chunks to process per batch (reduced for chunking)
        chunking_strategy: Text chunking strategy ('sections', 'overlapping', 'hybrid')
    """
    if not jobs:
        logger.warning("⚠️ No jobs to index.")
        return

    logger.info(f"🚀 Starting advanced processing pipeline for {len(jobs)} jobs...")
    logger.info(f"📝 Using '{chunking_strategy}' chunking strategy with batch size {batch_size}")
    
    # Step 1: Process all jobs into chunks with cleaning and NER
    all_chunks = []
    total_chunks = 0
    processing_stats = {
        'jobs_processed': 0,
        'chunks_created': 0,
        'text_cleaned': 0,
        'sections_identified': 0,
        'metadata_extracted': 0
    }
    
    for job in jobs:
        try:
            logger.debug(f"🔄 Processing job {job.get('id', 'unknown')}")
            
            # Process job into cleaned, chunked segments
            chunks = process_job_text(job, chunking_strategy)
            
            if chunks:
                # Extract NER metadata for each chunk (or reuse for all chunks from same job)
                logger.debug(f"🔍 Extracting NER metadata for {len(chunks)} chunks")
                base_metadata = extract_job_metadata(job.get('text', ''))
                
                for chunk in chunks:
                    chunk.ner_metadata = base_metadata
                
                all_chunks.extend(chunks)
                total_chunks += len(chunks)
                processing_stats['sections_identified'] += len(set(c.chunk_type for c in chunks))
            
            processing_stats['jobs_processed'] += 1
            processing_stats['chunks_created'] += len(chunks) if chunks else 0
            processing_stats['text_cleaned'] += 1
            processing_stats['metadata_extracted'] += 1
            
        except Exception as e:
            logger.error(f"❌ Failed to process job {job.get('id', 'unknown')}: {e}")
            continue
    
    if not all_chunks:
        logger.warning("⚠️ No chunks created from jobs. Check job text content.")
        return
    
    logger.info(f"📊 Processing completed: {processing_stats}")
    logger.info(f"📄 Created {total_chunks} chunks from {len(jobs)} jobs (avg: {total_chunks/len(jobs):.1f} chunks/job)")
    
    # Step 2: Generate embeddings and index chunks in batches
    processed_chunks = 0
    vectors_batch = []
    
    for i, chunk in enumerate(all_chunks):
        try:
            # Generate embedding for the cleaned chunk text
            logger.debug(f"🔄 Generating embedding for chunk {i+1}/{len(all_chunks)}")
            embedding = get_embedding(chunk.text)
            
            # Create comprehensive metadata for the chunk
            chunk_metadata = {
                # Original job information
                "text": chunk.text,
                "title": getattr(chunk, 'original_title', ''),
                "company": getattr(chunk, 'original_company', ''),
                "location": getattr(chunk, 'original_location', ''),
                "url": getattr(chunk, 'original_url', ''),
                "source": getattr(chunk, 'original_source', ''),
                
                # Chunk-specific metadata
                "chunk_type": chunk.chunk_type,
                "chunk_index": chunk.chunk_index,
                "parent_job_id": chunk.parent_job_id,
                "word_count": chunk.word_count,
                "confidence_score": chunk.confidence_score,
                "section_header": chunk.section_header,
                
                # NER extracted metadata (from original job)
                "skills": getattr(chunk, 'ner_metadata', {}).get('skills', []),
                "experience_years": getattr(chunk, 'ner_metadata', {}).get('experience', {}).get('years'),
                "experience_level": getattr(chunk, 'ner_metadata', {}).get('experience', {}).get('level'),
                "salary_min": getattr(chunk, 'ner_metadata', {}).get('salary', {}).get('min'),
                "salary_max": getattr(chunk, 'ner_metadata', {}).get('salary', {}).get('max'),
                "salary_amount": getattr(chunk, 'ner_metadata', {}).get('salary', {}).get('amount'),
                "remote_work": getattr(chunk, 'ner_metadata', {}).get('remote_work', False),
                "extracted_locations": getattr(chunk, 'ner_metadata', {}).get('locations', []),
                "education": getattr(chunk, 'ner_metadata', {}).get('education', []),
                "benefits": getattr(chunk, 'ner_metadata', {}).get('benefits', []),
                
                # Processing metadata
                "is_chunk": True,
                "chunking_strategy": chunking_strategy,
                "metadata_extracted": True,
                "skills_count": len(getattr(chunk, 'ner_metadata', {}).get('skills', [])),
                "has_salary_info": bool(getattr(chunk, 'ner_metadata', {}).get('salary')),
                "has_experience_info": bool(getattr(chunk, 'ner_metadata', {}).get('experience')),
                "processing_quality": chunk.confidence_score
            }
            
            # Create unique ID for chunk
            chunk_id = f"{chunk.parent_job_id}_chunk_{chunk.chunk_index}"
            
            vector_data = {
                "id": chunk_id,
                "values": embedding,
                "metadata": chunk_metadata
            }
            
            vectors_batch.append(vector_data)
            processed_chunks += 1
            
            # Upsert batch when it reaches batch_size
            if len(vectors_batch) >= batch_size:
                try:
                    index.upsert(vectors=vectors_batch)
                    logger.info(f"📦 Upserted batch of {len(vectors_batch)} chunks "
                               f"({processed_chunks}/{len(all_chunks)} total)")
                    vectors_batch = []
                except Exception as e:
                    logger.error(f"❌ Failed to upsert chunk batch: {e}")
                    raise
            
        except Exception as e:
            logger.error(f"❌ Failed to process chunk {i+1}: {e}")
            continue
    
    # Upsert final batch
    if vectors_batch:
        try:
            index.upsert(vectors=vectors_batch)
            logger.info(f"📦 Upserted final batch of {len(vectors_batch)} chunks")
        except Exception as e:
            logger.error(f"❌ Failed to upsert final batch: {e}")
            raise
    
    # Final statistics
    avg_quality = sum(c.confidence_score for c in all_chunks) / len(all_chunks)
    logger.info(f"🎉 Indexing completed successfully!")
    logger.info(f"📊 Final stats: {processed_chunks} chunks indexed, avg quality: {avg_quality:.2f}")
    logger.info(f"✨ Enhanced search now available with:")
    logger.info(f"   🧹 Cleaned text (removed boilerplate and HTML)")
    logger.info(f"   📄 Intelligent chunking ({chunking_strategy} strategy)")
    logger.info(f"   🔍 NER metadata extraction")
    logger.info(f"   🎯 High-precision semantic search")