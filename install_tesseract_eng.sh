#!/bin/bash
# Install Tesseract English Language Data

echo "🔧 Installing Tesseract English Language Data..."
echo ""

# Check if already installed
if [ -f "/usr/share/tessdata/eng.traineddata" ]; then
    echo "✅ English language data already installed!"
    exit 0
fi

# Detect package manager and install
if command -v yay &> /dev/null; then
    echo "📦 Installing with yay..."
    yay -S tesseract-data-eng --noconfirm
elif command -v pacman &> /dev/null; then
    echo "📦 Installing with pacman..."
    sudo pacman -S tesseract-data-eng --noconfirm
elif command -v apt &> /dev/null; then
    echo "📦 Installing with apt..."
    sudo apt install -y tesseract-ocr-eng
elif command -v dnf &> /dev/null; then
    echo "📦 Installing with dnf..."
    sudo dnf install -y tesseract-langpack-eng
else
    echo "⚠️  Could not detect package manager."
    echo ""
    echo "Please install manually:"
    echo "  Arch: sudo pacman -S tesseract-data-eng"
    echo "  Ubuntu: sudo apt install tesseract-ocr-eng"
    echo "  Fedora: sudo dnf install tesseract-langpack-eng"
    exit 1
fi

echo ""
echo "✅ Installation complete!"
echo "   Tesseract can now recognize English text."
