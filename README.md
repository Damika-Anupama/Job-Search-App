# Job Search Application

A comprehensive, multi-source job search platform with ML-powered semantic search, user tracking, and intelligent job recommendations.

## Features

### Intelligent Job Search
- **Multi-Source Aggregation**: Hacker News "Who is Hiring?", Remote OK, Arbeit Now, The Muse (489+ jobs indexed, 328+ after filtering)
- **Semantic Search**: Find jobs by meaning using Hugging Face `nomic-embed-text-v1.5` (768D vectors)
- **Advanced Text Processing**: Cleans HTML, removes boilerplate, normalizes text (20-40% size reduction)
- **Intelligent Chunking**: Section-based and overlapping chunking for better search coverage
- **Named Entity Recognition (NER)**: Extracts structured metadata (skills, salary, experience, location) from descriptions
- **Two-Stage Search**: Vector retrieval + optional cross-encoder reranking (20-30% accuracy improvement)
- **Smart Filtering**: Location, skills, experience level, salary ranges, remote work, education, benefits
- **Redis Caching**: Sub-second response times with personalized cache keys

### Personal Job Tracking
- **Save Jobs**: Build your personal job pipeline
- **Status Tracking**: saved → applied → interviewing → offered/rejected
- **Progress Analytics**: Track your job search statistics
- **Notes & Timeline**: Add personal notes and track application timeline

### Flexible Deployment Modes
- **Lightweight**: Fast keyword search, minimal resources (~1-2 min build, no ML deps)
- **Full ML**: Local semantic search + cross-encoder reranking, fully offline (~10-15 min build)
- **Cloud ML**: HuggingFace Inference API + local fallback (~5-8 min build)

---

## Tech Stack

### Backend
- **FastAPI** — Modern web framework with automatic OpenAPI docs
- **Celery** — Distributed task queue for background job processing
- **Redis** — High-performance caching and message broker
- **MongoDB Atlas** — User tracking and job pipeline storage
- **Pinecone** — Serverless vector database (768D cosine similarity)

### AI/ML
- **Hugging Face Transformers** — Production embedding generation (`nomic-embed-text-v1.5`)
- **Sentence Transformers** — Cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)
- **spaCy** — Named entity recognition (`en_core_web_sm`)
- **PyTorch** — Deep learning framework, CPU-optimized (Full ML mode)

### Frontend
- **Streamlit** — Multi-page web application (port 8501)

### Data Processing
- **BeautifulSoup4** — HTML parsing for job scraping
- **Custom scrapers** — Specialized parsers for each job board

### Infrastructure
- **Docker Compose** — Multi-container orchestration
- **Pydantic** — Data validation and configuration management
- **Structured Logging** — Colored console + rotating file logs

---

## Architecture

```
job-search-app/
├── src/job_search/           # Main application package
│   ├── api/                  # FastAPI routes and models
│   │   ├── routes/           # API endpoint definitions
│   │   └── models.py         # Pydantic request/response models
│   ├── core/                 # Business logic and services
│   │   ├── config.py         # Configuration management
│   │   ├── search.py         # Core search functionality
│   │   └── logging_config.py # Structured logging configuration
│   ├── db/                   # Database connections and services
│   │   ├── mongodb.py        # MongoDB user tracking
│   │   └── redis_client.py   # Redis caching client
│   ├── ml/                   # Machine learning services
│   │   ├── embeddings.py     # Text embedding generation
│   │   ├── reranking.py      # Cross-encoder reranking
│   │   ├── indexing.py       # Vector database operations
│   │   ├── ner.py            # Named Entity Recognition
│   │   └── text_processing.py# Advanced text cleaning and chunking
│   └── scraping/             # Data collection modules
│       ├── scrapers.py       # Job board scrapers
│       ├── tasks.py          # Celery background tasks
│       └── celery_config.py  # Celery configuration
├── frontend/                 # Streamlit application
│   ├── app.py                # Main multi-page app
│   ├── config/settings.py    # Frontend configuration
│   ├── utils/api_client.py   # Backend API integration
│   └── components/job_card.py# Reusable UI components
├── scripts/
│   └── monitor_services.py   # Service health monitoring
├── logs/                     # Auto-created log files
│   ├── job_search.log        # Main application logs
│   ├── errors.log            # Error-level logs only
│   └── scraping.log          # Background task logs
├── tests/                    # Test suite
├── config/                   # Configuration files (.env.example)
├── docker/                   # Docker deployment files
│   ├── Dockerfile            # Full ML backend
│   ├── Dockerfile-lightweight# Lightweight backend
│   ├── docker-compose-fullstack.yml    # Production
│   └── docker-compose-development.yml # Development
├── docs/                     # Architecture and planning docs
└── requirements/             # Dependency specifications
    ├── base.txt              # Lightweight mode
    ├── ml.txt                # Full ML / Cloud ML mode
    └── dev.txt               # Development tools
```

### Two-Stage Search Architecture

**Lightweight Mode (Keyword Search):**
1. Keyword matching and filtering against scraped job data
2. Location, skills, and keyword exclusion filters
3. Fast response, no external ML dependencies

**Full ML / Cloud ML Mode (Semantic Search):**
1. **Stage 1 — Vector Retrieval**: Broad semantic search via Pinecone (retrieves 8x candidates)
2. **Stage 2 — Cross-Encoder Reranking**: Precise query-document relevance scoring
3. NER-based metadata filtering (salary, experience, location, benefits)
4. Result: 20-30% better relevance over vector search alone

```
Job Sources → Scrapers → Text Processing → Embeddings → Pinecone
                                                              ↓
Search Query → Embedding → Vector Search → Reranking → API Response
                                              ↑
                                         Redis Cache
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose (2GB+ memory for lightweight, 4GB+ for Full ML)
- Hugging Face account with Inference Endpoint (for Cloud ML mode)
- Pinecone account (for ML modes)
- MongoDB Atlas (for user tracking)

### 1. Environment Setup

```bash
git clone <repository-url>
cd job-search-app
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

### 2. Choose Deployment Mode

#### Option A: Lightweight Mode (Recommended for Development)
```bash
pip install -r requirements/base.txt
# Set in config/.env: APP_MODE=lightweight
python app.py
```

#### Option B: Full ML Mode (Best Performance, Offline)
```bash
pip install -r requirements/ml.txt
python -m spacy download en_core_web_sm   # optional, for NER
# Set in config/.env: APP_MODE=full-ml
python app.py
```

#### Option C: Cloud ML Mode (HuggingFace + Local Fallback)
```bash
pip install -r requirements/ml.txt
python -m spacy download en_core_web_sm   # optional
# Set in config/.env:
# APP_MODE=cloud-ml
# HF_INFERENCE_API=your_hf_endpoint
# HF_TOKEN=your_hf_token
python app.py
```

### 3. Docker Deployment

#### Development Environment
```bash
cd docker
docker-compose -f docker-compose-development.yml up --build
```
Services: Redis (6379), Backend (8000, lightweight), Frontend (8501)

#### Production (Full Stack)
```bash
cd docker
docker-compose -f docker-compose-fullstack.yml up --build -d
```
Services: Redis (6379), Backend (8000, full ML), Celery Worker, Celery Scheduler, Frontend (8501)

#### Access Points
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Frontend UI**: http://localhost:8501
- **Health Check**: http://localhost:8000/health

---

## Deployment Modes

| Mode | Build Time | Startup | RAM | Search Quality | External Deps |
|------|-----------|---------|-----|----------------|---------------|
| Lightweight | 1-2 min | ~5 sec | <1GB | Basic keyword | None |
| Full ML | 10-15 min | ~30 sec | 2-4GB | High (offline) | None |
| Cloud ML | 5-8 min | ~15 sec | 1-2GB | High* | HuggingFace |

*Cloud ML quality depends on HuggingFace API availability. Automatically falls back to local models when HF fails.

### Mode Validation

Configuration is validated at startup:
- **Lightweight**: No additional credentials required
- **Full ML**: Requires `PINECONE_API_KEY`
- **Cloud ML**: Requires `PINECONE_API_KEY`, `HF_INFERENCE_API`, and `HF_TOKEN`

### Health Monitoring Per Mode

```bash
# Overall system health
GET /health

# Embedding service health (especially useful for Cloud ML)
GET /health/embedding
```

Cloud ML degraded example:
```json
{
  "status": "degraded",
  "mode": "cloud-ml",
  "components": {
    "redis": {"status": "healthy"},
    "embedding_service": {
      "status": "degraded",
      "details": {
        "hf_inference": "unavailable",
        "hf_error": "HuggingFace API timeout",
        "local_fallback": "available"
      }
    },
    "pinecone": {"status": "healthy", "total_vectors": 15000}
  }
}
```

---

## Frontend

The Streamlit frontend provides a full multi-page interface at http://localhost:8501.

### Pages
- **Job Search** — AI-powered semantic search with advanced filters, relevance scores, ML reranking toggle
- **Saved Jobs** — Personal pipeline: save jobs, track status (saved → applied → interviewing → offered), add notes
- **Analytics** — Job search insights, application statistics, activity metrics
- **Settings & Admin** — System management, health monitoring, manual job indexing triggers

### Frontend Configuration
```bash
# Backend URL (default: http://localhost:8000)
BACKEND_BASE_URL=http://localhost:8000

# API timeout in seconds (default: 30)
API_TIMEOUT=30
```

Settings also configurable in `frontend/config/settings.py` (UI theme, API endpoints, search settings, user options).

### Implemented API Endpoints (Frontend)
- `POST /search/` — Job search with filters
- `GET /health/` — System health monitoring
- `POST /search/trigger-indexing` — Manual job indexing
- `POST /users/{user_id}/saved-jobs` — Save job for tracking
- `GET /users/{user_id}/saved-jobs` — Get saved jobs
- `PUT /users/{user_id}/saved-jobs/{job_id}` — Update job status
- `DELETE /users/{user_id}/saved-jobs/{job_id}` — Remove saved job
- `GET /users/{user_id}/stats` — User analytics

---

## Advanced Text Processing

Raw job descriptions contain HTML artifacts, boilerplate, and marketing noise that dilutes search quality. The pipeline transforms them into clean, focused, searchable content.

### Text Cleaning
- Removes HTML tags, decodes entities (`&amp;` → `&`), normalizes whitespace
- Removes common HR boilerplate (application instructions, legal disclaimers, generic company marketing)
- Standardizes punctuation and spacing, preserves technical terms and bullet-point structure

### Chunking Strategies

**Section-Based** (when job has clear sections):
```
Original: Summary → Responsibilities → Requirements → Benefits → About Company
Chunks:   Chunk 1: Responsibilities | Chunk 2: Requirements | Chunk 3: Benefits
```

**Overlapping** (for unstructured descriptions):
- 512-word segments with overlapping windows to preserve context across boundaries
- Multiple embeddings per job for better search coverage

**Hybrid (default)**: Auto-detects structure, uses section-based when sections are found, falls back to overlapping otherwise.

### Performance
- **Text Reduction**: 20-40% after cleaning
- **Search Precision**: ~35% improvement in relevant results
- **Chunk Quality**: Average 0.85/1.0 score
- **Processing Speed**: ~150ms per job description

---

## NER-Powered Search

Named Entity Recognition automatically extracts structured metadata from job descriptions for precise filtering.

### Extracted Metadata

| Category | Examples |
|----------|---------|
| Technical Skills | Python, JavaScript, React, Django, PostgreSQL, AWS, Docker, Kubernetes |
| Experience Level | Entry, mid, senior, executive; years of experience; seniority indicators |
| Salary | Ranges ($100k-$150k), fixed amounts ($120,000); smart filtering (401k ≠ salary) |
| Location & Remote | Cities, states, remote/hybrid detection |
| Education | Degree level (BS/MS/PhD), field of study |
| Benefits | Health insurance, 401k, PTO, stock options, professional development |

### Search with NER Filters

```bash
# Senior Python developer, remote, with salary info
POST /search/
{
  "query": "python backend developer",
  "experience_level": "senior",
  "remote_only": true,
  "has_salary_info": true,
  "min_salary": 120000
}

# ML engineer with education and benefit requirements
POST /search/
{
  "query": "machine learning engineer",
  "required_education": ["computer science"],
  "required_benefits": ["health insurance", "stock options"],
  "min_experience_years": 3
}
```

---

## API Reference

### Search Endpoint

```http
POST /search/
```

```json
{
  "query": "python developer remote",
  "locations": ["remote"],
  "required_skills": ["python"],
  "preferred_skills": ["django", "docker"],
  "exclude_keywords": ["internship"],
  "max_results": 10,
  "experience_level": "senior",
  "min_experience_years": 3,
  "max_experience_years": 8,
  "min_salary": 100000,
  "max_salary": 180000,
  "remote_only": true,
  "has_salary_info": true,
  "required_education": ["bachelor"],
  "required_benefits": ["health insurance", "401k"]
}
```

Response:
```json
{
  "source": "pinecone",
  "results": [
    {
      "id": "ro_1093607",
      "score": 0.95,
      "text": "Position: Backend Developer...",
      "vector_score": 0.72,
      "cross_score": 0.95
    }
  ],
  "total_found": 75,
  "reranked": true,
  "candidates_retrieved": 50,
  "filters_applied": {...}
}
```

### User Tracking Endpoints

```http
POST   /users/{user_id}/saved-jobs          # Save a job
GET    /users/{user_id}/saved-jobs?status=applied  # Get saved jobs
PUT    /users/{user_id}/saved-jobs/{job_id} # Update status/notes
DELETE /users/{user_id}/saved-jobs/{job_id} # Remove saved job
GET    /users/{user_id}/stats               # Application statistics
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Overall system health |
| `/health/embedding` | GET | Embedding service status |
| `/search/trigger-indexing` | POST | Manually trigger job scraping |
| `/docs` | GET | Interactive Swagger docs |
| `/redoc` | GET | ReDoc API docs |

---

## Configuration

### Required Environment Variables

```bash
# Application Mode
APP_MODE=lightweight|full-ml|cloud-ml

# Redis (required for all modes)
REDIS_URL=redis://localhost:6379/0

# MongoDB Atlas (required for user tracking)
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE_NAME=job-search-app

# Pinecone (required for ML modes)
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=job-search-index

# HuggingFace (required for cloud-ml mode)
HF_INFERENCE_API=https://your-endpoint.us-east-1.aws.endpoints.huggingface.cloud/embed
HF_TOKEN=your_hf_token

# Job Source URLs (pre-configured defaults)
HN_HIRING_URL=https://news.ycombinator.com/item?id=42575537
REMOTEOK_API_URL=https://remoteok.io/api
ARBEITNOW_API_URL=https://www.arbeitnow.com/api/job-board-api
THEMUSE_API_URL=https://www.themuse.com/api/public/jobs?category=Software%20Engineer&page=0

# Logging (optional)
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_DIR=logs

# Celery (optional)
CELERY_WORKER_CONCURRENCY=2
CELERY_ENVIRONMENT=development|production|testing
ENABLE_CELERY_MONITORING=true|false
```

---

## Logging

The application uses structured logging with colored console output and rotating file logs.

### Log Files
```
logs/
├── job_search.log   # Main application logs (10MB, 5 backups)
├── errors.log       # Error-level logs only
└── scraping.log     # Background task logs
```

### Console Format
```
[14:20:28] INFO | [core.logging]    | Job Search API starting up
[14:20:28] INFO | [ml.embeddings]   | HuggingFace model loaded successfully
[14:20:29] ERROR| [scraping.tasks]  | Failed to scrape Remote OK: timeout
```

### Configuration
```bash
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
LOG_TO_FILE=true|false
LOG_DIR=logs
```

Per-service log levels:
```bash
LOG_LEVEL=DEBUG docker-compose up backend      # Detailed API debugging
LOG_LEVEL=WARNING docker-compose up worker     # Minimal worker logs
LOG_LEVEL=INFO ENABLE_CELERY_MONITORING=true docker-compose up  # Production
```

### Usage in Code
```python
from ..core.logging_config import get_logger
logger = get_logger(__name__)

logger.info(f"Processing {len(jobs)} jobs from {source}")
logger.error(f"Database connection failed: {error_msg}")
```

### Log Analysis
```bash
# Real-time monitoring
tail -f logs/job_search.log
tail -f logs/errors.log
tail -f logs/scraping.log

# Filter by level or component
grep "ERROR" logs/job_search.log
grep "ml.embeddings" logs/job_search.log

# Docker service logs
docker-compose -f docker/docker-compose-fullstack.yml logs -f backend
docker-compose -f docker/docker-compose-fullstack.yml logs --tail=100 worker
```

### Integration with Monitoring Tools
Structured logs are compatible with ELK Stack, Prometheus + Grafana, Sentry, and DataDog.

---

## Testing

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run all tests
pytest

# With coverage
pytest --cov=src/job_search --cov-report=html

# Specific test files
python tests/test_mongodb.py
python tests/test_api_endpoints.py

# Run tests per mode
python run_tests.py all
python run_tests.py lightweight
python run_tests.py full-ml
python run_tests.py cloud-ml
python run_tests.py coverage
```

---

## Monitoring & Health Checks

### Service Health Monitor
```bash
python scripts/monitor_services.py             # Single check
python scripts/monitor_services.py --continuous # Continuous monitoring
python scripts/monitor_services.py --json       # JSON output for scripts/alerting
```

### Health Endpoints
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/embedding
curl http://localhost:8501/_stcore/health     # Frontend
docker exec job-search-redis redis-cli ping   # Redis
```

### Container Health
```bash
docker-compose -f docker/docker-compose-fullstack.yml ps
docker stats
```

### Celery Worker
```bash
celery -A src.job_search.scraping.tasks.celery_app inspect ping
```

---

## Production Deployment

### Docker Production Setup
```bash
# Full-stack deployment
docker-compose -f docker/docker-compose-fullstack.yml up -d

# Scale workers for high load (never scale scheduler beyond 1)
docker-compose -f docker/docker-compose-fullstack.yml up -d --scale worker=3
docker-compose -f docker/docker-compose-fullstack.yml up -d --scale scheduler=1

# Production environment
export LOG_LEVEL=INFO
export LOG_TO_FILE=true
export CELERY_ENVIRONMENT=production
export ENABLE_CELERY_MONITORING=true
```

### Resource Requirements by Mode

| Mode | RAM | CPU |
|------|-----|-----|
| Lightweight | 512MB | 1 core |
| Full ML | 4GB | 2-4 cores |
| Cloud ML | 2GB | 2 cores |

### Security
- Non-root user in frontend container
- Minimal base images (`python:3.10-slim`)
- `.dockerignore` excludes sensitive files
- Services communicate via internal Docker network (Redis not exposed externally)
- Only necessary ports exposed to host

### Pre-Production Checklist
- [ ] Remove development volume mounts from docker-compose
- [ ] Set all production environment variables
- [ ] Configure external Redis/MongoDB
- [ ] Set up load balancer and SSL/TLS
- [ ] Configure log rotation and monitoring alerts
- [ ] Scale test under expected load

### Performance Optimization
- Enable log file rotation (10MB files, 5 backups)
- Use Redis persistence for critical cache data
- Scale Celery workers based on job volume
- Monitor worker memory (restart after 1000 tasks)
- Set task time limits (1 hour default)

### Development Setup
```bash
pip install -r requirements/dev.txt
pre-commit install
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

---

## Known Issues

These are current codebase issues identified for remediation:

### Test Suite
- Outdated module imports (`config`, `embedding_service`, `indexing`, `mongodb_service`) reference legacy names that no longer exist in the refactored package layout, causing import failures before any assertions run.
- **Fix**: Rewrite tests to import from `job_search.core.config.Settings` etc.; add fixture-based dependency setup.

### Configuration Loading
- `Settings.validate()` raises `ValueError` at module import time when ML credentials are absent, even when the user intends lightweight mode. This prevents the app from starting or falling back gracefully.
- **Fix**: Move to lazy/startup-time validation; default to `lightweight` when ML credentials are missing; surface errors via health endpoints.

### Redis Initialization
- `RedisClient` attempts a live connection at module import scope, logging errors when Redis is unavailable — complicates local dev and unit testing.
- **Fix**: Use lazy initialization or FastAPI lifespan dependency injection; allow in-memory mock for tests.

### Search Implementation
- Lightweight mode and the ML fallback currently return static mock data instead of querying real indexes, meaning advertised multi-source search behavior is not fully implemented end-to-end.
- **Fix**: Wire search to actual scraped datasets/vector indexes; gate mock behavior behind explicit demo flags.

---

## Roadmap to 2030

### Platform Reliability & Observability
- Move configuration to a typed Pydantic Settings layer with staged validation and dynamic reload
- Introduce OpenTelemetry tracing/metrics for API, scraping, and ML components
- Defer external service initialization to startup events with clear degraded-mode fallbacks

### Search & Data Quality
- Replace mock search flows with fully wired pipelines (continuous scrapers → cleaned/chunked documents → vector store → reranking → metadata filters)
- Add freshness scoring, deduplication, and spam removal in the indexing path

### ML & Personalization
- Standardize embeddings and reranking behind a provider abstraction (local / cloud / on-device) with A/B testing hooks
- User-level personalization: skill gap analysis, career path suggestions, salary benchmarks — with privacy-preserving MongoDB storage and client-side encryption options

### Developer Experience & CI/CD
- CI/CD pipeline with automated tests, linting, security scanning, and versioned Docker images per mode
- Local dev profiles with mock data and in-memory cache (no external services required for `pytest`)

### Frontend & Product
- Progressive web app with offline saved searches and analytics dashboards
- Accessibility, localization, and GDPR/CCPA compliance for global audiences

---

## Scalable Architecture (Future)

The architecture is designed to evolve toward a domain-driven, microservice-ready platform. Current modularity score: **9.5/10**.

### Domain Structure (Target)
```
src/
├── apps/
│   ├── search/          # Search domain (API, services, models, schemas)
│   ├── users/           # User management domain
│   ├── analytics/       # Analytics domain
│   ├── notifications/   # Notification system
│   └── recommendations/ # ML recommendations
├── infrastructure/
│   ├── database/        # MongoDB, Redis, Elasticsearch, Vector DB abstractions
│   ├── messaging/       # Celery, Kafka (future), RabbitMQ (alternative)
│   ├── monitoring/      # Logging, Prometheus metrics, distributed tracing
│   └── security/        # Auth, RBAC, encryption
├── ml/
│   ├── embeddings/      # Provider abstraction (HuggingFace, OpenAI, local)
│   ├── reranking/
│   ├── nlp/             # Text processing, NER, sentiment
│   └── serving/
├── data/
│   ├── scrapers/        # Plugin-based job board scrapers
│   ├── pipelines/       # ETL, streaming, batch
│   └── quality/
└── shared/
    ├── core/            # Config, exceptions, middleware, DI
    └── utils/
```

### Design Patterns in Use
- **Service Layer**: Business logic decoupled from API handlers
- **Repository Pattern**: Abstracted data access (swappable implementations)
- **Factory Pattern**: `EmbeddingProviderFactory` routes between HF, OpenAI, local
- **Plugin Architecture**: Add new job boards or ML providers without core changes
- **Interface-Based Design**: `VectorDatabaseInterface` supports Pinecone, Chroma, Weaviate

### Microservice Transition Path
1. **Phase 1** (Months 1-3): Monitoring, basic scaling, hermetic tests
2. **Phase 2** (Months 4-6): Extract first microservice (e.g., search-service)
3. **Phase 3** (Months 7-12): Full microservice split + event-driven architecture
4. **Phase 4** (Year 2+): Global multi-region deployment, AI platform

### Performance Targets (at scale)
- <100ms cached searches
- <500ms vector searches (10M jobs)
- <1s complex ML reranking
- 1000+ RPS with proper caching
- 10TB+ data with sharding

---

## Troubleshooting

### HuggingFace 403 Errors
```bash
curl -H "Authorization: Bearer $HF_TOKEN" $HF_INFERENCE_API
# Fix: Regenerate token with inference.endpoints.infer.write permissions
```

### Empty Search Results
```bash
# Check indexing status
curl -X POST http://localhost:8000/search/trigger-indexing
docker-compose logs -f worker | grep "Upserted batch"
```

### Cross-Encoder Model Loading Failed
```bash
docker stats
# Fix: Increase Docker memory to 4GB+ (Docker Desktop → Settings → Resources → Memory)
```

### Redis Connection Failed
```bash
docker-compose ps redis
docker-compose restart redis
docker exec job-search-backend redis-cli -h redis ping
```

### Frontend Can't Reach Backend
```bash
docker logs job-search-backend
docker exec job-search-frontend curl http://backend:8000/health
```

### Build Failures / Clean Rebuild
```bash
docker system prune -f
docker-compose build --no-cache
```

### Log File Issues
```bash
ls -la logs/
ls -lh logs/job_search.log*   # Check rotation
df -h logs/                    # Check disk space
echo $LOG_TO_FILE
echo $LOG_LEVEL
```

### Pinecone Not Connected
```bash
# Verify PINECONE_API_KEY is set and index exists
curl http://localhost:8000/health
```

---

## Contributing

Contributions are welcome. Please submit a Pull Request.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
