# 📊 Structured Logging Guide

## 🎯 **Overview**

The Job Search Application uses enterprise-grade structured logging for better debugging, monitoring, and production operations. All print() statements have been replaced with proper logging.

## 🏗️ **Logging Architecture**

```
Logging System Architecture:
├── 📁 src/job_search/core/logging_config.py  # Central logging configuration
├── 📊 logs/                                  # Log files directory (auto-created)
│   ├── job_search.log                        # Main application logs
│   ├── errors.log                            # Error-level logs only
│   └── scraping.log                          # Background task logs
└── 🎨 Console Output                         # Colored, structured output
```

## ✨ **Key Features**

### **🎨 Colored Console Output**
- **Green** INFO messages for normal operations 
- **Yellow** WARNING messages for potential issues
- **Red** ERROR messages for failures
- **Cyan** DEBUG messages for detailed debugging
- **Magenta** CRITICAL messages for severe issues

### **📁 File-Based Logging**
- **Automatic Rotation**: 10MB files, 5 backups per log type
- **Separate Files**: Main, errors, and scraping logs isolated
- **Structured Format**: Timestamp, level, module, function, message

### **🏷️ Enhanced Context**
- **Module Information**: Shows which component generated the log
- **Function Names**: Exact function generating the message
- **Timestamps**: Precise timing for debugging sequences
- **Emojis**: Visual indicators for quick scanning

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Log level (default: INFO)
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

# Enable/disable file logging (default: true)
LOG_TO_FILE=true|false

# Log directory path (default: logs)
LOG_DIR=logs

# Environment-specific settings
CELERY_ENVIRONMENT=development|production|testing
```

### **Per-Service Configuration**
Each service can have independent log levels:
```bash
# Backend API detailed debugging
LOG_LEVEL=DEBUG docker-compose up backend

# Worker minimal logging
LOG_LEVEL=WARNING docker-compose up worker

# Production monitoring
LOG_LEVEL=INFO ENABLE_CELERY_MONITORING=true docker-compose up
```

## 📝 **Log Formats**

### **Console Format (Colored)**
```
[14:20:28] INFO | [core.logging]        | 🚀 Job Search API starting up
[14:20:28] INFO | [ml.embeddings]       | ✅ HuggingFace model loaded successfully
[14:20:29] ERROR| [scraping.tasks]      | ❌ Failed to scrape Remote OK: timeout
```

### **File Format (Detailed)**
```
[2025-07-30 14:20:28] INFO | job_search.core.logging | setup_logging | Logging initialized - Level: INFO, File logging: True
[2025-07-30 14:20:28] INFO | job_search.main         | create_app    | Creating FastAPI application in cloud-ml mode
[2025-07-30 14:20:29] ERROR| job_search.scraping.tasks | crawl_and_index | Failed to scrape Remote OK: Connection timeout
```

## 🛠️ **Usage Examples**

### **Basic Logging in Code**
```python
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("🔍 Detailed debugging information")
logger.info("✅ Normal operation completed")
logger.warning("⚠️ Potential issue detected")
logger.error("❌ Error occurred during processing")
logger.critical("🚨 Critical system failure")
```

### **Logging with Context**
```python
# Log with variables and context
logger.info(f"📰 Processing {len(jobs)} jobs from {source}")
logger.error(f"❌ Database connection failed: {error_msg}")

# Log function entry/exit
logger.debug("🔄 Starting job processing pipeline")
# ... processing logic ...
logger.debug("✅ Job processing pipeline completed")
```

### **Exception Logging**
```python
try:
    # risky operation
    result = process_jobs()
    logger.info(f"✅ Successfully processed {len(result)} jobs")
except Exception as e:
    logger.error(f"❌ Job processing failed: {e}")
    logger.debug("📋 Full traceback:", exc_info=True)
    raise
```

## 📊 **Monitoring & Analysis**

### **Real-Time Log Monitoring**
```bash
# Watch all logs
tail -f logs/job_search.log

# Watch only errors
tail -f logs/errors.log

# Watch background tasks
tail -f logs/scraping.log

# Filter by log level
grep "ERROR" logs/job_search.log

# Search for specific component
grep "ml.embeddings" logs/job_search.log
```

### **Docker Service Logs**
```bash
# All services combined
docker-compose -f docker/docker-compose-fullstack.yml logs -f

# Specific service
docker-compose -f docker/docker-compose-fullstack.yml logs -f backend
docker-compose -f docker/docker-compose-fullstack.yml logs -f worker
docker-compose -f docker/docker-compose-fullstack.yml logs -f scheduler

# Last N lines
docker-compose -f docker/docker-compose-fullstack.yml logs --tail=100 backend
```

### **Log Analysis Examples**
```bash
# Count error types
grep "ERROR" logs/job_search.log | cut -d'|' -f3 | sort | uniq -c

# Find slow operations (if timing included)
grep "completed in" logs/job_search.log | sort -k4 -n

# Monitor API requests
grep "POST\|GET\|PUT\|DELETE" logs/job_search.log

# Track background job execution
grep "🔄\|✅\|❌" logs/scraping.log
```

## 🚨 **Error Handling & Alerting**

### **Error Severity Levels**
- **WARNING**: Recoverable issues, system continues operating
- **ERROR**: Failed operations, but service remains available  
- **CRITICAL**: Severe failures requiring immediate attention

### **Common Error Patterns**
```python
# Network/API errors
logger.error(f"❌ Failed to connect to {service}: {error}")

# Data processing errors  
logger.error(f"💥 Failed to process job {job_id}: {error}")

# Configuration errors
logger.critical(f"🚨 Missing required config: {config_key}")

# Resource errors
logger.warning(f"⚠️ High memory usage: {memory_percent}%")
```

### **Integration with Monitoring Tools**
The structured logs can be easily integrated with:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Prometheus + Grafana** for metrics
- **Sentry** for error tracking
- **DataDog** for comprehensive monitoring

## 🔧 **Troubleshooting**

### **Log File Issues**
```bash
# Check log directory permissions
ls -la logs/

# Verify log rotation is working
ls -lh logs/job_search.log*

# Check disk space
df -h logs/
```

### **Missing Logs**
```bash
# Verify LOG_TO_FILE setting
echo $LOG_TO_FILE

# Check log level configuration
echo $LOG_LEVEL

# Manually test logging
python -c "from src.job_search.core.logging_config import setup_logging, get_logger; setup_logging(); logger = get_logger('test'); logger.info('Test message')"
```

### **Performance Impact**
- **File I/O**: Minimal impact with async logging
- **Console Output**: Slight overhead in development mode
- **Production**: Use INFO level or higher for optimal performance

## 🎯 **Best Practices**

### **Do's**
✅ Use appropriate log levels (DEBUG for debugging, INFO for flow, ERROR for failures)  
✅ Include context and variables in log messages  
✅ Use emojis for visual scanning and categorization  
✅ Log function entry/exit for complex operations  
✅ Include error details and potential causes  

### **Don'ts**
❌ Don't log sensitive information (passwords, API keys, personal data)  
❌ Don't use DEBUG level in production (performance impact)  
❌ Don't log in tight loops without rate limiting  
❌ Don't ignore log rotation (can fill disk space)  
❌ Don't use generic error messages without context  

### **Log Message Guidelines**
```python
# Good: Specific, contextual, actionable
logger.error(f"❌ Failed to save job {job_id} for user {user_id}: Database connection timeout")

# Bad: Generic, no context
logger.error("Error occurred")

# Good: Clear operation flow
logger.info(f"🔄 Starting ML search for query: '{query}' (max_results: {max_results})")

# Bad: Unclear purpose
logger.info("Processing request")
```

## 📈 **Performance Monitoring**

### **Key Metrics to Track**
- **Log Volume**: Messages per minute/hour
- **Error Rate**: ERROR/WARNING ratio to total logs
- **Response Times**: If included in log messages
- **Resource Usage**: Memory/CPU impact of logging

### **Log-Based Alerts**
Set up alerts for:
- High error rates (>5% ERROR messages)
- Critical errors (any CRITICAL level)
- Service unavailability patterns
- Background job failures

---

**💡 Tip**: Use the monitoring script for comprehensive health checks:
```bash
python scripts/monitor_services.py --continuous
```