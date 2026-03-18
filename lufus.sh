#!/usr/bin/env bash

set -euo pipefail

VENV_DIR=".venv"

echo "Setting up virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip (optional but recommended)
pip install --upgrade pip

# Install Briefcase if not installed
if ! pip show briefcase > /dev/null 2>&1; then
    echo "Installing Briefcase..."
    pip install briefcase
fi

echo "Running app..."

# Run the app
briefcase dev
