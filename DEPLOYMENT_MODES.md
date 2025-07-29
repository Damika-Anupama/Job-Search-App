# Job Search Application - Deployment Modes

This document explains the three distinct deployment modes available for the Job Search Application, addressing the issues with unclear mode distinctions and hidden fallback behavior.

## 🚀 Available Modes

### 1. Lightweight Mode (`APP_MODE=lightweight`)
**Purpose**: Fast, simple keyword-based search without ML dependencies

**Features**:
- ⚡ Simple keyword matching and filtering
- 📍 Location-based filtering
- 🛠️ Skills matching (required/preferred)
- 🚫 Keyword exclusions
- 💾 Redis caching
- 🚀 **Fast startup time** (~1-2 minutes build time)

**Use Cases**:
- Development environments
- Quick prototyping
- Resource-constrained environments
- When ML accuracy is not critical

**Dependencies**: Minimal (no PyTorch, no sentence-transformers)

### 2. Full ML Mode (`APP_MODE=full-ml`)
**Purpose**: Complete ML-powered search using local models

**Features**:
- 🧠 Local semantic search with sentence-transformers
- 🎯 Cross-encoder reranking for improved relevance
- 📊 Two-stage search: broad retrieval + precise reranking
- 🔍 Vector similarity matching via Pinecone
- 💾 Intelligent caching with ML-aware cache keys
- 🏠 **Fully offline** - no external ML API dependencies

**Use Cases**:
- Production environments
- When data privacy is critical
- Consistent performance regardless of external services
- Maximum search relevance

**Dependencies**: Full ML stack (PyTorch, sentence-transformers)
**Build Time**: ~10-15 minutes

### 3. Cloud ML Mode (`APP_MODE=cloud-ml`)
**Purpose**: HuggingFace Inference API with local fallback

**Features**:
- 🌐 HuggingFace Inference API for embeddings
- 🔄 Automatic fallback to local models when HF fails
- 📊 **Real-time health monitoring** - surfaces HF API issues
- 🎯 Cross-encoder reranking
- ⚡ Faster cold starts than full-ml mode
- 🔍 Detailed error reporting and health checks

**Use Cases**:
- Hybrid cloud-local deployments
- When you want to test HuggingFace performance
- Gradual migration from cloud to local ML
- Cost optimization (pay-per-use for embeddings)

**Dependencies**: Full ML stack (for fallback capability)
**Build Time**: ~5-8 minutes

## 🛠️ Configuration

### Environment Variables

```bash
# Required for all modes
APP_MODE=lightweight|full-ml|cloud-ml
REDIS_URL=redis://localhost:6379/0

# Required for ML modes (full-ml, cloud-ml)
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=job-search-index

# Required only for cloud-ml mode
HF_INFERENCE_API=https://api-inference.huggingface.co/models/your-model
HF_TOKEN=your-huggingface-token
```

### Mode Validation

The application validates configuration at startup:
- **Lightweight**: No additional credentials required
- **Full ML**: Requires `PINECONE_API_KEY`
- **Cloud ML**: Requires `PINECONE_API_KEY`, `HF_INFERENCE_API`, and `HF_TOKEN`

## 🐳 Docker Deployment

### Quick Start

```bash
# Lightweight Mode (fastest)
docker-compose -f docker-compose-lightweight.yml up

# Full ML Mode (default)
docker-compose up

# Cloud ML Mode  
docker-compose -f docker-compose-cloud.yml up
```

### Manual Docker Build

```bash
# Lightweight
docker build -f Dockerfile-lightweight -t job-search:lightweight .

# Full ML
docker build -f Dockerfile -t job-search:full-ml .

# Cloud ML
docker build -f Dockerfile-cloud -t job-search:cloud-ml .
```

## 🔍 Health Monitoring

### Health Check Endpoints

```bash
# Basic health check
GET /health

# Embedding service specific health
GET /health/embedding

# Example responses show real HF inference status
```

### Cloud ML Health Response Example

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
        "hf_api_status": "timeout",
        "local_fallback": "available"
      }
    },
    "pinecone": {"status": "healthy", "total_vectors": 15000}
  }
}
```

## 🧪 Testing

### Run Tests for All Modes

```bash
# Install test dependencies
python run_tests.py install

# Run complete test suite
python run_tests.py all

# Test specific modes
python run_tests.py lightweight
python run_tests.py full-ml
python run_tests.py cloud-ml

# Coverage report
python run_tests.py coverage
```

### Manual Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run pytest
pytest -v

# With coverage
pytest --cov=. --cov-report=html
```

## 🎯 Key Improvements

### 1. Clear Mode Distinction
- No more ambiguous "fast" vs "full" modes
- Each mode has distinct capabilities and use cases
- Mode is visible in API title and health endpoints

### 2. Proper Error Handling
- **No more silent fallbacks** that mask issues
- HuggingFace API failures are properly surfaced
- Health checks show real-time component status
- Embedding service errors bubble up to users

### 3. Mode-Specific Optimization
- Lightweight mode skips ML entirely (no PyTorch loading)
- Cloud ML mode doesn't use fallback in search (surfaces real HF issues)
- Full ML mode is purely offline with no external dependencies

### 4. Comprehensive Testing
- Unit tests for each mode
- Component isolation and mocking
- Health check validation
- Error scenario testing

## 🔄 Migration Guide

### From Previous Setup

1. **Set explicit mode**:
   ```bash
   export APP_MODE=full-ml  # or lightweight/cloud-ml
   ```

2. **Update Docker usage**:
   ```bash
   # Old way
   docker-compose up
   
   # New way (explicit mode)
   docker-compose -f docker-compose-lightweight.yml up  # Fast
   docker-compose up                                    # Full ML
   docker-compose -f docker-compose-cloud.yml up       # Cloud ML
   ```

3. **Monitor health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/health/embedding
   ```

### Performance Expectations

| Mode | Build Time | Startup Time | Search Quality | External Deps |
|------|------------|--------------|----------------|---------------|
| Lightweight | 1-2 min | ~5 sec | Basic | None |
| Full ML | 10-15 min | ~30 sec | High | None |
| Cloud ML | 5-8 min | ~15 sec | High* | HuggingFace |

*Cloud ML quality depends on HuggingFace API availability

## 🐛 Troubleshooting

### Common Issues

1. **"Vector search not available"**
   - Check `PINECONE_API_KEY` is set
   - Verify Pinecone index exists
   - Check `/health` endpoint

2. **"Embedding service unavailable"**
   - In cloud-ml mode: Check HuggingFace credentials
   - Check `/health/embedding` for detailed status
   - Try switching to full-ml mode for local-only operation

3. **Silent search failures**
   - This should no longer happen - all errors now surface properly
   - Check application logs for embedding service errors
   - Use health endpoints to diagnose issues

### Performance Testing

To truly test the differences between modes:

1. **Turn off HuggingFace VM** (to test cloud-ml error handling)
2. **Monitor `/health/embedding`** endpoint
3. **Compare search response times** between modes
4. **Check cache behavior** with different mode-specific cache keys

## 📊 Monitoring

### Key Metrics to Track

- **Health endpoint status** (`/health`)
- **Embedding service availability** (`/health/embedding`)
- **Search response times** by mode
- **Cache hit rates** (mode-specific cache keys)
- **HuggingFace API success rates** (cloud-ml mode)

This new architecture ensures you can clearly see the performance differences between modes and properly handle external service failures!