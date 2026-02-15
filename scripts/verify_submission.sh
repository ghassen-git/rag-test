#!/bin/bash

echo "🔍 Pre-Submission Verification Checklist"
echo "========================================"
echo ""

ERRORS=0

# Check files exist
echo "📁 Checking required files..."
FILES=(
    "docker-compose.yml"
    "requirements.txt"
    ".env.example"
    "README.md"
    "src"
    "tests"
)

for FILE in "${FILES[@]}"; do
    if [ -e "$FILE" ]; then
        echo "✅ $FILE exists"
    else
        echo "❌ $FILE missing!"
        ((ERRORS++))
    fi
done

echo ""

# Check architecture diagram
echo "🎨 Checking architecture diagram..."
if [ -e "architecture.png" ] || [ -e "architecture.pdf" ] || [ -e "docs/architecture.png" ]; then
    echo "✅ Architecture diagram found"
else
    echo "⚠️  Warning: Architecture diagram missing!"
fi

echo ""

# Run tests
echo "🧪 Running test suite..."
./scripts/run_all_tests.sh

if [ $? -ne 0 ]; then
    echo "❌ Tests failed!"
    ((ERRORS++))
fi

echo ""

# Check Docker Compose
echo "🐳 Checking Docker Compose..."
docker-compose config > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors!"
    ((ERRORS++))
fi

echo ""
echo "========================================"

if [ $ERRORS -eq 0 ]; then
    echo "🎉 READY FOR SUBMISSION!"
    echo "All checks passed. Good luck!"
else
    echo "⚠️  Found $ERRORS issues"
    echo "Please fix before submitting."
    exit 1
fi
