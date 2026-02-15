# Test Execution Guide

## 🎯 Quick Reference

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for services (30 seconds)
sleep 30

# 3. Run all tests
./scripts/run_all_tests.sh

# 4. Pre-submission check
./scripts/verify_submission.sh
```

## 📋 Test Execution Flow

```
┌─────────────────────────────────────────┐
│  1. Start Docker Services               │
│     docker-compose up -d                │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  2. Wait for Services Ready             │
│     - PostgreSQL (port 5432)            │
│     - MongoDB (port 27017)              │
│     - Milvus (port 19530)               │
│     - Kafka/Debezium (port 8083)        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  3. Run Test Suite                      │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Part A: Core Requirements       │   │
│  │ - PostgreSQL CDC (7 tests)      │   │
│  │ - MongoDB CDC (4 tests)         │   │
│  │ - OCR Pipeline (4 tests)        │   │
│  │ - Vectorization (6 tests)       │   │
│  │ - Multi-Agent (6 tests)         │   │
│  │ - MCP Server (6 tests)          │   │
│  │ - RAG Strategy (5 tests)        │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Part B: Production Quality      │   │
│  │ - Initial Load (4 tests)        │   │
│  │ - Data Quality (6 tests)        │   │
│  │ - Embedding Quality (3 tests)   │   │
│  │ - Security (6 tests)            │   │
│  │ - Connectivity (6 tests)        │   │
│  │ - Concurrent Load (2 tests)     │   │
│  │ - Chunking Quality (3 tests)    │   │
│  │ - Documentation (5 tests)       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Part C: Integration             │   │
│  │ - End-to-End (1 test)           │   │
│  └─────────────────────────────────┘   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  4. Results Summary                     │
│     ✅ 58 tests passed                  │
│     ⏱️  4-6 minutes total               │
└─────────────────────────────────────────┘
```

## 🔍 Individual Test Categories

### Core Requirements Tests
```bash
# Run all core tests
./scripts/run_core_tests.sh

# Or run individually
pytest tests/core/test_postgres_cdc.py -v
pytest tests/core/test_mongodb_cdc.py -v
pytest tests/core/test_ocr_pipeline.py -v
pytest tests/core/test_vectorization.py -v
pytest tests/core/test_agents.py -v
pytest tests/core/test_mcp_server.py -v
pytest tests/core/test_rag_strategy.py -v
```

### Production Quality Tests
```bash
# Run all production tests
./scripts/run_production_tests.sh

# Or run individually
pytest tests/production/test_initial_load.py -v
pytest tests/production/test_data_quality.py -v
pytest tests/production/test_embedding_quality.py -v
pytest tests/production/test_security.py -v
pytest tests/production/test_connectivity.py -v
pytest tests/production/test_concurrent_load.py -v
pytest tests/production/test_chunking_quality.py -v
pytest tests/production/test_documentation.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_end_to_end.py -v
```

## 🎨 Test Output Examples

### Successful Test
```
tests/core/test_postgres_cdc.py::TestPostgresCDC::test_debezium_connector_registered 
✅ Debezium PostgreSQL connector registered
PASSED
```

### Skipped Test
```
tests/core/test_agents.py::TestMultiAgentSystem::test_search_agent_semantic_search 
SKIPPED (Search Agent not implemented)
```

### Failed Test
```
tests/core/test_postgres_cdc.py::TestPostgresCDC::test_cdc_captures_insert 
❌ CDC latency too high: 5.23s
FAILED
```

## 🐛 Debugging Failed Tests

### 1. Check Service Status
```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
postgres            Up                  0.0.0.0:5432->5432/tcp
mongodb             Up                  0.0.0.0:27017->27017/tcp
milvus              Up                  0.0.0.0:19530->19530/tcp
kafka               Up                  0.0.0.0:9092->9092/tcp
```

### 2. Check Service Logs
```bash
docker-compose logs postgres
docker-compose logs mongodb
docker-compose logs milvus
docker-compose logs kafka
```

### 3. Run Single Test with Verbose Output
```bash
pytest tests/core/test_postgres_cdc.py::TestPostgresCDC::test_cdc_captures_insert -vv -s
```

### 4. Check Environment Variables
```bash
cat .env | grep -v "^#" | grep -v "^$"
```

## 📊 Test Metrics

### Performance Benchmarks
| Test Category | Expected Time | Max Time |
|--------------|---------------|----------|
| PostgreSQL CDC | 30s | 60s |
| MongoDB CDC | 20s | 40s |
| OCR Pipeline | 45s | 90s |
| Vectorization | 40s | 80s |
| Multi-Agent | 30s | 60s |
| MCP Server | 20s | 40s |
| RAG Strategy | 45s | 90s |
| Production Tests | 60s | 120s |
| Integration | 30s | 60s |

### Success Criteria
- ✅ All 58 tests pass
- ✅ Total time < 10 minutes
- ✅ No service connection errors
- ✅ No credential leaks detected
- ✅ All data quality checks pass

## 🔄 Continuous Testing

### Watch Mode (Development)
```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw tests/
```

### Pre-Commit Hook
```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
./scripts/run_all_tests.sh
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## 📈 Coverage Report

Generate coverage report:
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## 🎯 Test Selection

### Run by Marker
```bash
# Run only core tests
pytest -m core

# Run only production tests
pytest -m production

# Run only integration tests
pytest -m integration
```

### Run by Pattern
```bash
# Run all CDC tests
pytest -k "cdc"

# Run all security tests
pytest -k "security"

# Run all quality tests
pytest -k "quality"
```

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Connection refused | Start services: `docker-compose up -d` |
| Service not ready | Wait longer: `sleep 60` |
| API key error | Check `.env` file has valid keys |
| Timeout error | Increase timeout in `pytest.ini` |
| Import error | Install dependencies: `pip install -r requirements.txt` |
| Permission denied | Make scripts executable: `chmod +x scripts/*.sh` |

## ✅ Pre-Submission Checklist

Before running final verification:

- [ ] All services are running
- [ ] .env file is configured
- [ ] All dependencies installed
- [ ] No uncommitted changes
- [ ] Architecture diagram exists
- [ ] README is complete

Then run:
```bash
./scripts/verify_submission.sh
```

## 📞 Support

For issues:
1. Check this guide
2. Review `README_TESTING.md`
3. Check service logs
4. Verify environment variables
5. Review test output carefully
