#!/bin/bash
# Build Lambda Layer using Poetry
# This script creates a Lambda layer from Poetry dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYER_DIR="$PROJECT_DIR/lambda_layer"
LAYER_ZIP="$PROJECT_DIR/lambda_layer.zip"

echo "🏗️  Building Lambda Layer with Poetry dependencies..."

# Clean up existing layer
rm -rf "$LAYER_DIR" "$LAYER_ZIP"

# Create layer directory structure
mkdir -p "$LAYER_DIR/python"

# Install dependencies to layer directory
cd "$PROJECT_DIR"
poetry export --without-dev --format=requirements.txt --output=requirements-lambda-export.txt

# Install to layer directory
pip install -r requirements-lambda-export.txt -t "$LAYER_DIR/python" --no-deps

# Create layer zip
cd "$LAYER_DIR"
zip -r "$LAYER_ZIP" . -q

# Clean up
rm -rf "$LAYER_DIR"
rm "$PROJECT_DIR/requirements-lambda-export.txt"

echo "✅ Lambda layer created: $LAYER_ZIP"
echo "📦 Layer size: $(du -h "$LAYER_ZIP" | cut -f1)"