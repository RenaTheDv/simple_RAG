#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p data/raw data/processed data/vector_db

# Set Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment variables..."
    set -a
    source .env.example
    set +a
fi

# Run Streamlit app
echo "Starting Streamlit app..."
streamlit run src/web/streamlit_app.py 