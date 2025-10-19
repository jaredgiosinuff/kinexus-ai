#!/bin/bash
# Build Lambda Layer using Poetry
# This script creates a Lambda layer from Poetry dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYER_DIR="$PROJECT_DIR/lambda_layer"
LAYER_ZIP="$PROJECT_DIR/lambda_layer.zip"

echo "🏗️  Building Lambda Layer..."

# Clean up existing layer
rm -rf "$LAYER_DIR" "$LAYER_ZIP"

# Create layer directory structure
mkdir -p "$LAYER_DIR/python"

cd "$PROJECT_DIR"

# Choose requirements source: prefer curated requirements-lambda.txt, otherwise export via Poetry
REQ_FILE="requirements-lambda.txt"
USED_EXPORT=false
if [ -f "$REQ_FILE" ]; then
  echo "📄 Using curated $REQ_FILE"
else
  echo "📦 No $REQ_FILE found; exporting from Poetry (requires poetry-plugin-export)"
  poetry export --without dev --format=requirements.txt --output=requirements-lambda-export.txt
  REQ_FILE="requirements-lambda-export.txt"
  USED_EXPORT=true
fi

# Install to layer directory WITH dependencies (removed --no-deps to include all dependencies)
pip install -r "$REQ_FILE" -t "$LAYER_DIR/python" --no-cache-dir

# Prune non-runtime files to reduce size
find "$LAYER_DIR/python" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$LAYER_DIR/python" -type f -name "*.pyc" -delete
find "$LAYER_DIR/python" -type d \( -name tests -o -name test -o -name docs -o -name examples \) -prune -exec rm -rf {} +

# Create layer zip
cd "$LAYER_DIR"
zip -r "$LAYER_ZIP" . -q

# Clean up
rm -rf "$LAYER_DIR"
if [ "$USED_EXPORT" = true ]; then
  rm -f "$PROJECT_DIR/requirements-lambda-export.txt"
fi

echo "✅ Lambda layer created: $LAYER_ZIP"
echo "📦 Layer size: $(du -h "$LAYER_ZIP" | cut -f1)"