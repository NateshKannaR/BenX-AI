#!/bin/bash

echo "🎯 Installing Jarvis Enhanced Dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Install Python packages
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt

# Check for system dependencies
echo "🔍 Checking system dependencies..."

# Check for portaudio (for voice features)
if ! command -v pkg-config &> /dev/null || ! pkg-config --exists portaudio-2.0; then
    echo "⚠️  PortAudio not found. Voice features may not work."
    echo "   Install with: sudo pacman -S portaudio (Arch) or sudo apt-get install portaudio19-dev (Ubuntu/Debian)"
fi

# Check for tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  tkinter not found. GUI features will be disabled."
    echo "   Install with: sudo pacman -S tk (Arch) or sudo apt-get install python3-tk (Ubuntu/Debian)"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 Run Jarvis with: python3 jarvis.py"
echo "📖 See README.md for more information"
