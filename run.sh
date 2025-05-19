#!/bin/bash
# Run script for Linux/WSL environment

# Check if python3-pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip for Python 3..."
    sudo apt-get update && sudo apt-get install -y python3-pip
fi

# Install dependencies from requirements.txt
pip3 install -r requirements.txt

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Run the FastAPI server
python3 -m uvicorn app.main:app --reload