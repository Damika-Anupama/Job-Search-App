# 🚀 Job Search Application

A comprehensive, multi-source job search platform with ML-powered semantic search, user tracking, and intelligent job recommendations.

## ✨ Features

### 🔍 **Intelligent Job Search**
- **Multi-Source Aggregation**: Hacker News "Who is Hiring?", Remote OK, Arbeit Now, The Muse
- **Semantic Search**: Find jobs by meaning, not just keywords
- **Smart Filtering**: Location, skills, experience level, salary requirements
- **Cross-Encoder Reranking**: Advanced relevance scoring for better results

### 👤 **Personal Job Tracking**
- **Save Jobs**: Build your personal job pipeline
- **Status Tracking**: saved → applied → interviewing → offered/rejected
- **Progress Analytics**: Track your job search statistics
- **Notes & Timeline**: Add personal notes and track application timeline

### 🧠 **Flexible Deployment Modes**
- **Lightweight**: Fast keyword search, minimal resources (< 1GB RAM)
- **Full ML**: Local embeddings + reranking (2-4GB RAM)  
- **Cloud ML**: HuggingFace Inference + local fallback (1-2GB RAM)

## 🏗️ Architecture

```
job-search-app/
├── src/job_search/           # Main application package
│   ├── api/                  # FastAPI routes and models
│   │   ├── routes/          # API endpoint definitions
│   │   └── models.py        # Pydantic request/response models
│   ├── core/                # Business logic and services
│   │   ├── config.py        # Configuration management
│   │   ├── search.py        # Core search functionality
│   │   └── logging_config.py # Structured logging configuration
│   ├── db/                  # Database connections and services
│   │   ├── mongodb.py       # MongoDB user tracking
│   │   └── redis_client.py  # Redis caching client
│   ├── ml/                  # Machine learning services
│   │   ├── embeddings.py    # Text embedding generation
│   │   ├── reranking.py     # Cross-encoder reranking
│   │   └── indexing.py      # Vector database operations
│   └── scraping/            # Data collection modules
│       ├── scrapers.py      # Job board scrapers
│       ├── tasks.py         # Celery background tasks
│       └── celery_config.py # Production Celery configuration
├── scripts/                 # Utility scripts
│   └── monitor_services.py  # Service monitoring and health checks
├── logs/                    # Application logs (auto-created)
│   ├── job_search.log       # Main application logs
│   ├── errors.log           # Error-level logs only
│   └── scraping.log         # Background task logs
├── tests/                   # Test suite
├── config/                  # Configuration files
├── docker/                  # Docker deployment files
├── docs/                    # Documentation
└── requirements/            # Dependency specifications
```

## 🚀 Quick Start

### 1. **Environment Setup**

```bash
# Clone the repository
git clone <repository-url>
cd job-search-app

# Copy environment configuration
cp config/.env.example config/.env
# Edit config/.env with your API keys
```

### 2. **Choose Your Deployment Mode**

#### **Option A: Lightweight Mode (Recommended for Development)**
```bash
# Install lightweight dependencies
pip install -r requirements/base.txt

# Set mode in config/.env
APP_MODE=lightweight

# Run the application
python app.py
```

#### **Option B: Full ML Mode (Best Performance)**
```bash
# Install ML dependencies
pip install -r requirements/ml.txt

# Set mode in config/.env  
APP_MODE=full-ml

# Run the application
python app.py
```

#### **Option C: Cloud ML Mode (Balanced)**
```bash
# Install ML dependencies
pip install -r requirements/ml.txt

# Configure HuggingFace credentials in config/.env
HF_INFERENCE_API=your_hf_endpoint
HF_TOKEN=your_hf_token
APP_MODE=cloud-ml

# Run the application
python app.py
```

### 3. **Docker Deployment (Recommended)**

```bash
# Full-stack deployment with all services
docker-compose -f docker/docker-compose-fullstack.yml up -d

# View services status
docker-compose -f docker/docker-compose-fullstack.yml ps

# View logs
docker-compose -f docker/docker-compose-fullstack.yml logs -f
```

**Services Included:**
- 🔗 **Backend API** (port 8000) - FastAPI application
- 🖥️ **Frontend** (port 8501) - Streamlit interface  
- 📦 **Redis Cache** (port 6379) - High-performance caching
- ⚙️ **Celery Worker** - Background job processing
- ⏰ **Celery Scheduler** - Periodic task scheduling
- 📊 **Structured Logging** - All services log to `logs/` directory

## 📚 API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Key Endpoints

#### 🔍 **Search Jobs**
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
  "max_results": 10
}
```

#### 👤 **User Tracking**
```http
# Save a job
POST /users/{user_id}/saved-jobs

# Get saved jobs
GET /users/{user_id}/saved-jobs?status=applied

# Update job status
PUT /users/{user_id}/saved-jobs/{job_id}

# Get statistics
GET /users/{user_id}/stats
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Application Mode
APP_MODE=lightweight|full-ml|cloud-ml

# Redis (required)
REDIS_URL=redis://localhost:6379/0

# MongoDB Atlas (required for user tracking)
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE_NAME=job-search-app

# Pinecone (required for ML modes)
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=job-search-index

# HuggingFace (required for cloud-ml mode)
HF_INFERENCE_API=your_hf_endpoint
HF_TOKEN=your_hf_token

# Logging Configuration (optional)
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
LOG_TO_FILE=true|false
LOG_DIR=logs

# Celery Configuration (optional)
CELERY_WORKER_CONCURRENCY=2
CELERY_ENVIRONMENT=development|production|testing
CELERY_SECURE=true|false
ENABLE_CELERY_MONITORING=true|false
```

## 🧪 Testing

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src/job_search --cov-report=html

# Test specific functionality
python tests/test_mongodb.py
python tests/test_api_endpoints.py
```

## 📊 Monitoring & Logging

### 📋 Service Health Monitoring
```bash
# Run comprehensive health check
python scripts/monitor_services.py

# Continuous monitoring (Ctrl+C to stop)
python scripts/monitor_services.py --continuous

# JSON output for scripts/alerting
python scripts/monitor_services.py --json
```

### 🔍 Health Check Endpoints
- **Overall System**: `GET /health`
- **Individual Services**: Docker health checks for all containers
- **Celery Worker**: `celery -A src.job_search.scraping.tasks.celery_app inspect ping`
- **Celery Scheduler**: Process monitoring in scheduler container

### 📁 Structured Logging
```bash
# View logs in real-time
tail -f logs/job_search.log

# View only errors
tail -f logs/errors.log

# View background task logs
tail -f logs/scraping.log

# View all Docker service logs
docker-compose -f docker/docker-compose-fullstack.yml logs -f
```

**Log Levels Available:**
- `DEBUG` - Detailed debugging information
- `INFO` - General application flow (default)
- `WARNING` - Potential issues or important notices
- `ERROR` - Error conditions that need attention

### 📈 Metrics & Performance
- ⚡ Search response times and cache hit rates
- 👥 User activity and job application statistics  
- 🧠 ML model performance and inference times
- 🔄 Background task execution and success rates
- 📊 Service health and availability metrics

## 🚀 Production Deployment

### 🐳 Docker Production Setup
```bash
# Production deployment with separated services
docker-compose -f docker/docker-compose-fullstack.yml up -d

# Scale workers for high load
docker-compose -f docker/docker-compose-fullstack.yml up -d --scale worker=3

# Enable production logging and monitoring
export LOG_LEVEL=INFO
export LOG_TO_FILE=true
export CELERY_ENVIRONMENT=production
export ENABLE_CELERY_MONITORING=true
```

### 📊 Service Architecture (Production)
- **Backend API** - Main FastAPI application
- **Frontend** - Streamlit user interface
- **Redis Cache** - High-performance data caching
- **Celery Worker(s)** - Background job processing (scalable)
- **Celery Beat Scheduler** - Periodic task scheduling (single instance)
- **Log Aggregation** - Centralized logging to `logs/` directory

### ⚡ Performance Recommendations

**Resource Requirements by Mode:**
- **Lightweight Mode**: 512MB RAM, 1 CPU core
- **Full ML Mode**: 4GB RAM, 2-4 CPU cores  
- **Cloud ML Mode**: 2GB RAM, 2 CPU cores

**Production Optimizations:**
- Enable log file rotation (10MB files, 5 backups)
- Use Redis persistence for critical cache data
- Scale Celery workers based on job volume
- Monitor worker memory usage (restart after 1000 tasks)
- Set appropriate task time limits (1 hour default)

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src/ tests/
isort src/ tests/

# Run linting
flake8 src/ tests/
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **Sentence Transformers** for semantic search capabilities
- **MongoDB Atlas** for user data persistence
- **Pinecone** for vector database services
- **HuggingFace** for ML model hosting

---

**📧 Support**: Open an issue or contact the development team
**🌟 Star**: If this project helps you, consider giving it a star!