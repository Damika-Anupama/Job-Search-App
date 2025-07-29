import requests
import numpy as np
from pinecone import Pinecone
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, HF_MODEL_DIMENSION, HF_INFERENCE_API, HF_TOKEN

def get_embedding(text: str) -> list[float]:
    """
    Generates a vector embedding for the given text using a Hugging Face Inference API.
    """
    if not HF_INFERENCE_API or not HF_TOKEN:
        # Fallback to mock if secrets aren't set
        print("Warning: Hugging Face credentials not set. Using MOCK embeddings.")
        return np.random.rand(HF_MODEL_DIMENSION).tolist()

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}
    
    try:
        response = requests.post(HF_INFERENCE_API, headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        result = response.json()
        # The actual embedding is often nested inside the response
        if isinstance(result, list) and isinstance(result[0], list):
            return result[0]
        else:
            raise ValueError(f"Unexpected API response format: {result}")
    except requests.RequestException as e:
        print(f"Error calling Hugging Face API: {e}")
        # Return a zero vector on failure to avoid crashing the whole process
        return [0.0] * HF_MODEL_DIMENSION


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
        print(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
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
        print(f"Index '{PINECONE_INDEX_NAME}' created successfully.")

    # 4. Return a handle to the specific index
    return pc.Index(PINECONE_INDEX_NAME)

# This line executes when the module is imported, initializing the index.
index = get_pinecone_index()
print(f"Successfully connected to Pinecone index '{PINECONE_INDEX_NAME}'.")
# --- End Pinecone Initialization ---


def embed_and_index(jobs: list[dict], batch_size: int = 32):
    """
    Takes scraped jobs, generates embeddings, and upserts them into Pinecone.
    """
    if not jobs:
        print("No jobs to index.")
        return

    print(f"Starting to embed and index {len(jobs)} jobs...")
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        texts_to_embed = [job['text'] for job in batch]
        
        embeddings = [get_embedding(text) for text in texts_to_embed]

        vectors_to_upsert = []
        for job, embedding in zip(batch, embeddings):
            vectors_to_upsert.append({
                "id": job['id'],
                "values": embedding,
                "metadata": {"text": job['text']}
            })
        
        # The rest of the code works as before, using the 'index' object.
        index.upsert(vectors=vectors_to_upsert)
        print(f"Upserted batch {i//batch_size + 1}/{(len(jobs) + batch_size - 1)//batch_size}")

    print("Finished embedding and indexing all jobs.")