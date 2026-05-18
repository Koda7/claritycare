#!/bin/bash
set -e

echo "=================================================="
echo "  Oscar Medical Guidelines Pipeline"
echo "=================================================="

# Check for .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example and add your OpenAI key:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load env vars
export $(grep -v '^#' .env | xargs)

# Detect python command
PYTHON=${PYTHON:-$(command -v python3 || command -v python)}
PIP=${PIP:-$(command -v pip3 || command -v pip)}

# Ensure Python deps are installed
echo ""
echo "[1/5] Installing Python dependencies..."
$PIP install -r backend/requirements.txt -q

# Initialize database
echo ""
echo "[2/5] Initializing database..."
cd backend
$PYTHON database.py

# Run discovery
echo ""
echo "[3/5] Discovering PDFs..."
$PYTHON -m scraper.discover

# Run downloads
echo ""
echo "[4/5] Downloading PDFs..."
$PYTHON -m scraper.download

# Run structuring pipeline (at least 10)
echo ""
echo "[5/5] Running LLM structuring pipeline..."
$PYTHON -m pipeline.structure --limit 15

cd ..

echo ""
echo "=================================================="
echo "  Pipeline complete!"
echo "=================================================="
echo ""
echo "To start the API server:"
echo "  cd backend && uvicorn main:app --reload"
echo ""
echo "To start the frontend (in another terminal):"
echo "  cd frontend && npm install && npm run dev"
echo ""
