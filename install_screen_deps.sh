#!/bin/bash
# Quick install script for BenX screen analysis dependencies

echo "🔧 Installing BenX Screen Analysis Dependencies..."
echo ""

# Install Python packages
echo "📦 Installing Python packages..."
pip install pyautogui pytesseract Pillow

# Check if tesseract is installed
if ! command -v tesseract &> /dev/null; then
    echo ""
    echo "📦 Installing tesseract-ocr system package..."
    
    # Detect package manager and install
    if command -v yay &> /dev/null; then
        yay -S tesseract tesseract-data-eng --noconfirm
    elif command -v pacman &> /dev/null; then
        sudo pacman -S tesseract tesseract-data-eng --noconfirm
    elif command -v apt &> /dev/null; then
        sudo apt install -y tesseract-ocr tesseract-ocr-eng
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y tesseract tesseract-langpack-eng
    else
        echo "⚠️  Could not detect package manager. Please install tesseract-ocr manually."
    fi
else
    echo "✅ tesseract-ocr already installed"
    
    # Check if English language data is installed
    if [ ! -f "/usr/share/tessdata/eng.traineddata" ]; then
        echo "📦 Installing English language data..."
        if command -v yay &> /dev/null; then
            yay -S tesseract-data-eng --noconfirm
        elif command -v pacman &> /dev/null; then
            sudo pacman -S tesseract-data-eng --noconfirm
        elif command -v apt &> /dev/null; then
            sudo apt install -y tesseract-ocr-eng
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y tesseract-langpack-eng
        fi
    else
        echo "✅ English language data already installed"
    fi
fi

echo ""
echo "✨ Installation complete! Try: python benx.py"
echo "   Then ask: 'what's on my screen'"
