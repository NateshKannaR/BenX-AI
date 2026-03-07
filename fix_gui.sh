#!/bin/bash

echo "🔧 Fixing GUI for Jarvis..."
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Installing tk package..."
    pacman -S --noconfirm tk
else
    echo "Installing tk package (requires sudo)..."
    sudo pacman -S --noconfirm tk
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ tk package installed successfully!"
    echo "🎯 Now run: python3 jarvis.py"
else
    echo ""
    echo "❌ Failed to install tk package"
    echo "   Try manually: sudo pacman -S tk"
fi
