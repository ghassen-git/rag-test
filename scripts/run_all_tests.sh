#!/bin/bash

echo "🧪 Running Complete RAG System Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Run core tests
echo "📋 Part 1: Core Requirements Tests"
echo "-----------------------------------"
pytest tests/core/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Core tests PASSED${NC}"
else
    echo -e "${RED}❌ Core tests FAILED${NC}"
    exit 1
fi

echo ""

# Run production tests
echo "🏭 Part 2: Production Quality Tests"
echo "------------------------------------"
pytest tests/production/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Production tests PASSED${NC}"
else
    echo -e "${RED}❌ Production tests FAILED${NC}"
    exit 1
fi

echo ""

# Run integration tests
echo "🔗 Part 3: Integration Tests"
echo "-----------------------------"
pytest tests/integration/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
echo "System is ready for submission."
echo "=========================================="
