#!/bin/bash

# =============================================================================
# Automated Trading Bot - Virtual Environment Activation Script
# =============================================================================

echo "🚀 Activating Automated Trading Bot Environment"
echo "================================================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "📁 Project directory: $PROJECT_DIR"

# Change to project directory
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "trading_bot_env" ]; then
    echo "❌ Virtual environment not found!"
    echo "📋 Creating virtual environment..."
    python3 -m venv trading_bot_env
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment created successfully!"
    else
        echo "❌ Failed to create virtual environment!"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source trading_bot_env/bin/activate

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated successfully!"
    echo ""
    echo "📊 Environment Information:"
    echo "   🐍 Python version: $(python --version)"
    echo "   📦 Installed packages: $(pip list | wc -l) packages"
    echo "   📁 Working directory: $(pwd)"
    echo ""
    echo "🎯 Quick Commands:"
    echo "   📋 Install minimal: pip install -r requirements-minimal.txt"
    echo "   🕷️  Install scraping: pip install -r requirements-scraping.txt"
    echo "   🏗️  Install full: pip install -r requirements.txt"
    echo "   🧪 Install dev: pip install -r requirements-dev.txt"
    echo "   🔍 Test setup: python -c \"import pandas, numpy; print('✅ Setup OK')\""
    echo ""
    echo "🚀 Ready to trade! Happy coding!"
else
    echo "❌ Failed to activate virtual environment!"
    exit 1
fi
