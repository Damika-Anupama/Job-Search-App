# Current Codebase Issues and Remediation Suggestions

## Test Suite Failures
- **Outdated module references**: The existing pytest suite imports legacy module names (e.g., `config`, `embedding_service`, `indexing`, `mongodb_service`) that no longer exist in the refactored package layout, causing import errors before any assertions run. 【F:tests/test_config.py†L4-L83】【F:tests/test_embedding_service.py†L1-L35】【F:tests/test_indexing.py†L1-L24】【F:tests/test_main.py†L1-L13】【F:tests/test_mongodb.py†L1-L13】【402208†L1-L39】
  - **Remediation**: Rewrite tests to import from the current `job_search` package (e.g., `job_search.core.config.Settings`), add fixture-based dependency setup, and remove reliance on deprecated top-level modules. Provide shims only if backward compatibility is required.

## Configuration Loading Risks
- **Eager validation with hard failures**: `Settings.validate()` raises `ValueError` during module import when required ML credentials are absent, even in development contexts where users may want lightweight mode defaults. This causes the app to crash before it can start or fallback gracefully. 【F:src/job_search/core/config.py†L63-L78】
  - **Remediation**: Perform mode-aware validation lazily (e.g., during startup), default to `lightweight` when ML credentials are missing, and surface actionable error messages via health endpoints instead of import-time exceptions.

## Connection Side Effects at Import Time
- **Redis connection attempted on import**: Instantiating `RedisClient` at module scope tries to connect immediately and logs errors if Redis is unavailable, complicating local development and unit testing. 【F:src/job_search/db/redis_client.py†L12-L69】
  - **Remediation**: Use lazy initialization or dependency injection via FastAPI lifespans; allow an in-memory mock cache for tests; surface connection health via explicit checks rather than implicit side effects.

## Search Implementation Gaps
- **Mock-only search paths**: Lightweight mode and the ML fallback return static mock job data instead of querying real indexes or scraped sources, so the API does not reflect the advertised multi-source search behavior. 【F:src/job_search/core/search.py†L50-L165】
  - **Remediation**: Wire search to actual scraped datasets or vector indexes; gate mock behavior behind explicit demo flags; add integration tests that validate end-to-end retrieval and filtering logic.

## Developer Experience Gaps
- **Environment defaults can block startup**: Because configuration and connection objects initialize eagerly, missing Redis, Pinecone, or Hugging Face settings halt the app before routers load, preventing partial functionality (e.g., health endpoints) in constrained environments. 【F:src/job_search/core/config.py†L63-L78】【F:src/job_search/db/redis_client.py†L12-L69】
  - **Remediation**: Defer external service initialization to startup events, provide clear degraded-mode fallbacks, and document minimal environment settings for development and CI.
