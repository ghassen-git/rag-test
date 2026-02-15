#!/bin/bash

# Setup script for RAG system

set -e

echo "🚀 Setting up Real-Time RAG System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - MATHPIX_APP_ID"
    echo "   - MATHPIX_APP_KEY"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Build and start services
echo "🐳 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to initialize (this may take 2-3 minutes)..."
sleep 30

# Check service health
echo ""
echo "🔍 Checking service health..."

# Check PostgreSQL
echo -n "PostgreSQL: "
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✓ Ready"
else
    echo "⚠️  Not ready yet"
fi

# Check MongoDB
echo -n "MongoDB: "
if docker-compose exec -T mongo mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "✓ Ready"
else
    echo "⚠️  Not ready yet"
fi

# Check Kafka
echo -n "Kafka: "
if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo "✓ Ready"
else
    echo "⚠️  Not ready yet"
fi

# Check Milvus
echo -n "Milvus: "
if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
    echo "✓ Ready"
else
    echo "⚠️  Not ready yet"
fi

# Wait a bit more for app to start
echo ""
echo "⏳ Waiting for application to start..."
sleep 30

# Check application health
echo -n "RAG Application: "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Ready"
else
    echo "⚠️  Not ready yet (may need more time)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Service URLs:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/health"
echo "   - Metrics: http://localhost:8000/metrics"
echo ""
echo "🧪 Test the system:"
echo '   curl -X POST http://localhost:8000/query \\'
echo '     -H "Content-Type: application/json" \\'
echo '     -d '"'"'{"question": "What is 1984 about?", "top_k": 5}'"'"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f rag-app"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
