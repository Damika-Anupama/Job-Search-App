# AI-Powered Semantic Job Search Agent

**Built for the Redis AI Challenge 2025**

This project is a backend application for an intelligent job discovery agent. It's designed to save time for skilled professionals (e.g., software engineers) by automatically aggregating fresh job postings from across the internet and enabling powerful, meaning-based "semantic" search.

Instead of manually checking multiple job boards for new listings, this system:
1.  **Automatically scrapes** recent job postings from sources like Hacker News "Who is Hiring?" threads.
2.  **Generates vector embeddings** for each job to capture its semantic meaning (currently using mock embeddings for testing).
3.  **Indexes** these jobs in a vector database (Pinecone).
4.  **Provides a fast API** for users to search for jobs based on what they *mean*, not just keywords they type.
5.  **Leverages Redis** for high-speed caching and as a robust backbone for background task management.

---

## 🚀 Core Features

-   **Automated Web Scraping:** Background worker scrapes Hacker News "Who is Hiring?" threads using BeautifulSoup
-   **Semantic Search API:** FastAPI endpoint (`/search`) that finds jobs based on vector similarity
-   **Redis-Powered Caching:** Search results cached in Redis for lightning-fast repeat queries
-   **Asynchronous Task Queue:** Celery workers handle heavy tasks (scraping, indexing) in the background
-   **Vector Database Integration:** Pinecone stores job embeddings for similarity search
-   **Containerized Environment:** Full Docker Compose setup for easy deployment
-   **Real-time Job Data:** Automatically indexes 200+ job postings from latest HN hiring threads

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Web Scraping:** BeautifulSoup4, Requests
- **Vector Database:** Pinecone (with ServerlessSpec)
- **Caching & Message Broker:** Redis
- **Task Queue:** Celery
- **Containerization:** Docker, Docker Compose
- **API Documentation:** Swagger/OpenAPI

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Pinecone API key

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Job-Search-App
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   
3. **Configure your `.env` file:**
   ```env
   PINECONE_API_KEY=your_pinecone_api_key_here
   PINECONE_INDEX_NAME=job-search-app
   HF_MODEL_DIMENSION=384
   REDIS_URL=redis://redis:6379/0
   HN_HIRING_URL=https://news.ycombinator.com/item?id=42575537
   ```

4. **Start the application:**
   ```bash
   docker-compose up --build
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs

---

## 📋 API Usage

### Search Jobs
**Endpoint:** `POST /search`

**Request:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python developer remote"}'
```

**Response:**
```json
{
  "source": "pinecone",
  "results": [
    {
      "id": "hn_42581481",
      "score": 0.784331143,
      "text": "CloudTrucks| Senior Front-End Engineer | SF | On-site..."
    }
  ]
}
```

### Example Queries
- `"python developer remote"`
- `"machine learning AI startup"`
- `"frontend react javascript"`
- `"rust backend systems"`

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│      Redis      │────│  Celery Worker  │
│   (Port 8000)   │    │   (Caching &    │    │   (Background   │
│                 │    │  Message Broker)│    │     Tasks)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              Cache Results              Scrape & Index
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Search API    │    │   Redis Cache   │    │ Hacker News API │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         │                                              │
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│ Pinecone Vector │                          │ BeautifulSoup   │
│    Database     │                          │   Web Scraper   │
└─────────────────┘                          └─────────────────┘
```

---

## 📊 Current Status

✅ **Working Features:**
- Docker containerization
- Hacker News job scraping (279+ jobs indexed)
- Pinecone vector database integration
- Redis caching system
- Celery background workers
- Semantic search API
- Swagger documentation

🔄 **Mock Implementation:**
- Vector embeddings (using random vectors for testing)

🚀 **Future Enhancements:**
- Real AI embeddings (Hugging Face, OpenAI)
- Multiple job sources (LinkedIn, Indeed, etc.)
- Job filtering and sorting
- User authentication
- Email notifications for new relevant jobs

---

## 🐛 Troubleshooting

### Common Issues

1. **Pinecone API Error:**
   - Ensure your `PINECONE_API_KEY` is set correctly in `.env`
   - Verify your Pinecone account has sufficient quota

2. **Container Build Issues:**
   - Run `docker-compose down` then `docker-compose up --build`
   - Clear Docker cache: `docker system prune -a`

3. **No Search Results:**
   - Wait for initial job indexing (check worker logs)
   - Verify Celery worker is running: `docker-compose logs worker`

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.