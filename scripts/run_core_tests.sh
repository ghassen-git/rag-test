#!/bin/bash

echo "📋 Running Core Requirements Tests"
echo "===================================="
echo ""

pytest tests/core/ -v --tb=short

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All core tests PASSED!"
else
    echo ""
    echo "❌ Some core tests FAILED"
    exit 1
fi
