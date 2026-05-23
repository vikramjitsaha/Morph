#!/usr/bin/env bash
# setup.sh — One-shot setup for Morph
# Usage: chmod +x setup.sh && ./setup.sh

set -e

PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🤖  Morph Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python version
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "  Python version: $PY_VERSION"

REQUIRED_MAJOR=3
REQUIRED_MINOR=10
ACTUAL_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
ACTUAL_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")

if [ "$ACTUAL_MAJOR" -lt "$REQUIRED_MAJOR" ] || [ "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]; then
    echo "  ❌ Python $REQUIRED_MAJOR.$REQUIRED_MINOR+ required (got $PY_VERSION)"
    exit 1
fi
echo "  ✅ Python version OK"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "  Creating virtual environment in $VENV_DIR …"
    $PYTHON -m venv "$VENV_DIR"
    echo "  ✅ Virtual environment created"
else
    echo "  ✅ Virtual environment already exists"
fi

# Activate
source "$VENV_DIR/bin/activate" 2>/dev/null || source "$VENV_DIR/Scripts/activate" 2>/dev/null

# Upgrade pip
echo ""
echo "  Upgrading pip …"
pip install --upgrade pip --quiet

# Install dependencies
echo "  Installing dependencies …"
pip install -r requirements.txt --quiet
echo "  ✅ Dependencies installed"

# Copy .env.example → .env (if not exists)
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "  ✅ Created .env from .env.example"
    echo ""
    echo "  ⚠️  IMPORTANT: Edit .env and set your LLM credentials:"
    echo "     • For OpenRouter: set OPENROUTER_API_KEY"
    echo "     • For Ollama:     set LLM_PROVIDER=ollama (and ensure Ollama is running)"
else
    echo "  ✅ .env already exists (skipped)"
fi

# Create output directory
mkdir -p output
echo "  ✅ Created output/ directory"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your LLM provider credentials"
echo "    2. Activate venv:  source .venv/bin/activate"
echo "    3. Run with sample: python main.py sample_requirements.md"
echo "    4. Or your own:    python main.py your_requirements.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
