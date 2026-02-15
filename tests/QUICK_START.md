# Quick Start Guide - Testing

## Prerequisites

1. All services must be running:
```bash
docker-compose up -d
```

2. Wait for services to be ready (~30 seconds)

3. Ensure .env file is configured with valid API keys

## Run Tests

### Option 1: Run Everything (Recommended)
```bash
./scripts/run_all_tests.sh
```

### Option 2: Run by Category
```bash
# Core requirements only
./scripts/run_core_tests.sh

# Production quality only
./scripts/run_production_tests.sh

# Integration tests only
pytest tests/integration/ -v
```

### Option 3: Run Specific Test File
```bash
pytest tests/core/test_postgres_cdc.py -v
pytest tests/production/test_security.py -v
```

## Pre-Submission Verification

Before submitting your project:
```bash
./scripts/verify_submission.sh
```

This will:
- ✅ Check all required files exist
- ✅ Run complete test suite
- ✅ Validate docker-compose.yml
- ✅ Verify documentation

## Expected Results

All 58 tests should pass:
- 38 core requirement tests
- 20 production quality tests

Total runtime: 4-6 minutes

## Common Issues

### "Connection refused"
**Solution:** Start services with `docker-compose up -d`

### "Service not ready"
**Solution:** Wait 30-60 seconds after starting services

### "API key not found"
**Solution:** Check your .env file has valid credentials

### Tests timeout
**Solution:** Increase timeout in `tests/conftest.py`

## Test Output

Successful test output looks like:
```
✅ PostgreSQL ready
✅ MongoDB ready
✅ Milvus ready

tests/core/test_postgres_cdc.py::TestPostgresCDC::test_debezium_connector_registered PASSED
tests/core/test_postgres_cdc.py::TestPostgresCDC::test_postgres_connector_status PASSED
...

========================================
🎉 ALL TESTS PASSED!
System is ready for submission.
========================================
```

## Need Help?

See full documentation in `README_TESTING.md`
