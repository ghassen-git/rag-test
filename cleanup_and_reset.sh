#!/bin/bash

# Cleanup Script - Remove all mock data and reset the system
# This prepares the system for indexing your own data

set -e

echo "🧹 RAG System Cleanup and Reset"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  WARNING: This will delete all existing data!${NC}"
echo "This includes:"
echo "  - PostgreSQL books database"
echo "  - MongoDB reviews collection"
echo "  - Milvus vector collections"
echo "  - Kafka topics and offsets"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Step 1: Stop all services
echo "1️⃣  Stopping all services..."
docker-compose down
echo -e "${GREEN}✅${NC} Services stopped"

# Step 2: Remove volumes (this deletes all data)
echo ""
echo "2️⃣  Removing Docker volumes (all data will be deleted)..."
docker volume rm $(docker volume ls -q | grep rag) 2>/dev/null || true
echo -e "${GREEN}✅${NC} Volumes removed"

# Step 3: Clean up local data directories (optional)
echo ""
echo "3️⃣  Cleaning local data directories..."
read -p "Remove sample books from data/sample_books? (yes/no): " remove_samples

if [ "$remove_samples" == "yes" ]; then
    rm -f data/sample_books/*.pdf 2>/dev/null || true
    rm -f data/sample_books/*.txt 2>/dev/null || true
    echo -e "${GREEN}✅${NC} Sample books removed"
else
    echo "Sample books kept"
fi

# Step 4: Create fresh data directory structure
echo ""
echo "4️⃣  Creating fresh data directory structure..."
mkdir -p data/your_books
mkdir -p data/processed
mkdir -p logs
echo -e "${GREEN}✅${NC} Directories created"

# Step 5: Restart services with clean state
echo ""
echo "5️⃣  Starting services with clean state..."
docker-compose up -d
echo -e "${GREEN}✅${NC} Services starting..."

echo ""
echo "6️⃣  Waiting for services to initialize (60 seconds)..."
sleep 60

# Step 7: Verify services are healthy
echo ""
echo "7️⃣  Verifying service health..."

# Check PostgreSQL
if docker exec rag-postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} PostgreSQL is ready"
else
    echo -e "${RED}❌${NC} PostgreSQL is not ready"
fi

# Check MongoDB
if docker exec rag-mongo mongosh --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} MongoDB is ready"
else
    echo -e "${RED}❌${NC} MongoDB is not ready"
fi

# Check Milvus
if curl -s http://localhost:9091/healthz >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} Milvus is ready"
else
    echo -e "${RED}❌${NC} Milvus is not ready"
fi

# Check API
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} API is ready"
else
    echo -e "${YELLOW}⚠️${NC}  API not ready yet (may need more time)"
fi

echo ""
echo "================================"
echo "🎉 Cleanup Complete!"
echo "================================"
echo ""
echo "Your system is now clean and ready for your own data."
echo ""
echo "Next steps:"
echo "1. Place your PDF files in: data/your_books/"
echo "2. Run: python index_your_data.py"
echo "3. Or use the API to add books: curl -X POST http://localhost:8000/add_book"
echo ""
echo "For detailed instructions, see: DATA_INGESTION_GUIDE.md"
