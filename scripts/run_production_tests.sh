#!/bin/bash

echo "🏭 Running Production Quality Tests"
echo "====================================="
echo ""

pytest tests/production/ -v --tb=short

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All production tests PASSED!"
else
    echo ""
    echo "❌ Some production tests FAILED"
    exit 1
fi
