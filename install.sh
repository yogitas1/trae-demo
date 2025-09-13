#!/bin/bash
# AI Session Monitor Installation Script

set -e

echo "🤖 Conjurer - AI Session Monitor Installation"
echo "=================================="

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION found"

# Install required packages
echo "📦 Installing required Python packages..."
pip3 install psutil || {
    echo "❌ Failed to install psutil. Try: pip3 install --user psutil"
    exit 1
}

# Make the conjurer script executable
chmod +x conjurer.py

# Create output directory
mkdir -p ai_sessions

echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  Start monitoring: ./conjurer.py"
echo "  Custom output:    ./conjurer.py --output-dir /path/to/sessions"
echo "  Verbose mode:     ./conjurer.py --verbose"
echo ""
echo "📁 Session files will be saved to: ai_sessions/"
echo "🔧 Customize settings in: config.json"