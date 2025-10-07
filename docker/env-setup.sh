#!/bin/sh

# Environment Setup Script for Frontend Container
# This script injects runtime environment variables into the React app

set -e

# Function to replace environment variables in built files
replace_env_vars() {
    local file="$1"

    # Replace API base URL
    if [ -n "$VITE_API_BASE_URL" ]; then
        sed -i "s|VITE_API_BASE_URL_PLACEHOLDER|$VITE_API_BASE_URL|g" "$file"
    fi

    # Replace WebSocket base URL
    if [ -n "$VITE_WS_BASE_URL" ]; then
        sed -i "s|VITE_WS_BASE_URL_PLACEHOLDER|$VITE_WS_BASE_URL|g" "$file"
    fi

    # Replace other environment variables as needed
    if [ -n "$VITE_APP_VERSION" ]; then
        sed -i "s|VITE_APP_VERSION_PLACEHOLDER|$VITE_APP_VERSION|g" "$file"
    fi
}

# Create runtime configuration file
create_runtime_config() {
    cat > /usr/share/nginx/html/runtime-config.js << EOF
window.__RUNTIME_CONFIG__ = {
    API_BASE_URL: '${VITE_API_BASE_URL:-http://localhost:8000/api}',
    WS_BASE_URL: '${VITE_WS_BASE_URL:-ws://localhost:8000/api/ws}',
    APP_VERSION: '${VITE_APP_VERSION:-1.0.0}',
    ENVIRONMENT: '${ENVIRONMENT:-production}'
};
EOF
}

echo "Setting up environment variables for frontend..."

# Find all JavaScript files in the build directory
find /usr/share/nginx/html -name "*.js" -type f | while read -r file; do
    echo "Processing: $file"
    replace_env_vars "$file"
done

# Find all CSS files in the build directory
find /usr/share/nginx/html -name "*.css" -type f | while read -r file; do
    echo "Processing: $file"
    replace_env_vars "$file"
done

# Create runtime configuration
create_runtime_config

echo "Environment setup completed successfully"