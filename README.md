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
│   │   └── search.py        # Core search functionality
│   ├── db/                  # Database connections and services
│   │   ├── mongodb.py       # MongoDB user tracking
│   │   └── redis_client.py  # Redis caching client
│   ├── ml/                  # Machine learning services
│   │   ├── embeddings.py    # Text embedding generation
│   │   ├── reranking.py     # Cross-encoder reranking
│   │   └── indexing.py      # Vector database operations
│   └── scraping/            # Data collection modules
│       ├── scrapers.py      # Job board scrapers
│       └── tasks.py         # Celery background tasks
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

### 3. **Docker Deployment**

```bash
# Lightweight mode
docker-compose -f docker/docker-compose-lightweight.yml up

# Full ML mode  
docker-compose -f docker/docker-compose.yml up

# Cloud ML mode
docker-compose -f docker/docker-compose-cloud.yml up
```

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

## 📊 Monitoring

### Health Checks
- **Overall**: `GET /health`
- **Embedding Service**: `GET /health/embedding`
- **Components**: Individual service status

### Metrics
- Search response times
- Cache hit rates  
- User activity statistics
- ML model performance

## 🚀 Production Deployment

### Docker Swarm
```bash
docker stack deploy -c docker/docker-compose-production.yml job-search
```

### Kubernetes
```bash
kubectl apply -f k8s/
```

### Performance Recommendations
- **Lightweight**: 512MB RAM, 1 CPU core
- **Full ML**: 4GB RAM, 2 CPU cores
- **Cloud ML**: 2GB RAM, 1-2 CPU cores

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