import numpy as np
from pinecone import Pinecone
from ..core.config import settings, AppMode
from .embeddings import embedding_service, EmbeddingServiceError
from .ner import extract_job_metadata
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


def embed_and_index(jobs: list[dict], batch_size: int = 32):
    """
    Takes scraped jobs, generates embeddings with NER metadata, and upserts them into Pinecone.
    
    This enhanced version:
    1. Extracts structured metadata using NER (skills, experience, salary, etc.)
    2. Generates semantic embeddings
    3. Stores both text and structured metadata in Pinecone
    
    Args:
        jobs: List of job dictionaries with 'text' and 'id' fields
        batch_size: Number of jobs to process per batch
    """
    if not jobs:
        logger.warning("⚠️ No jobs to index.")
        return

    logger.info(f"🚀 Starting to embed and index {len(jobs)} jobs with NER metadata extraction...")
    
    processed_jobs = 0
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        texts_to_embed = [job['text'] for job in batch]
        
        # Generate embeddings for the batch
        logger.debug(f"🔄 Generating embeddings for batch {i//batch_size + 1}")
        embeddings = [get_embedding(text) for text in texts_to_embed]

        vectors_to_upsert = []
        for job, embedding in zip(batch, embeddings):
            # Extract structured metadata using NER
            logger.debug(f"🔍 Extracting metadata for job {job.get('id', 'unknown')}")
            metadata = extract_job_metadata(job['text'])
            
            # Combine original job data with extracted metadata
            enhanced_metadata = {
                "text": job['text'],
                "title": job.get('title', ''),
                "company": job.get('company', ''),
                "location": job.get('location', ''),
                "url": job.get('url', ''),
                "source": job.get('source', ''),
                "posted_date": job.get('posted_date', ''),
                
                # NER extracted metadata
                "skills": metadata.get('skills', []),
                "experience_years": metadata.get('experience', {}).get('years'),
                "experience_level": metadata.get('experience', {}).get('level'),
                "salary_min": metadata.get('salary', {}).get('min'),
                "salary_max": metadata.get('salary', {}).get('max'),
                "salary_amount": metadata.get('salary', {}).get('amount'),
                "remote_work": metadata.get('remote_work', False),
                "extracted_locations": metadata.get('locations', []),
                "education": metadata.get('education', []),
                "benefits": metadata.get('benefits', []),
                
                # Metadata about the extraction
                "metadata_extracted": True,
                "skills_count": len(metadata.get('skills', [])),
                "has_salary_info": bool(metadata.get('salary')),
                "has_experience_info": bool(metadata.get('experience'))
            }
            
            vectors_to_upsert.append({
                "id": job['id'],
                "values": embedding,
                "metadata": enhanced_metadata
            })
            
            processed_jobs += 1
        
        # Upsert the batch to Pinecone
        try:
            index.upsert(vectors=vectors_to_upsert)
            logger.info(f"📦 Upserted batch {i//batch_size + 1}/{(len(jobs) + batch_size - 1)//batch_size} "
                       f"({len(batch)} jobs with metadata)")
        except Exception as e:
            logger.error(f"❌ Failed to upsert batch {i//batch_size + 1}: {e}")
            raise

    logger.info(f"🎉 Finished embedding and indexing {processed_jobs} jobs with structured metadata.")
    logger.info(f"✨ Enhanced search capabilities now available with NER-extracted filters!")