#!/bin/bash
# Setup script for BenX AI

echo "=========================================="
echo "BenX AI - Setup Script"
echo "=========================================="
echo ""

# Check if API key is already set
if [ -n "$GROQ_API_KEY" ] || [ -n "$GROQ_KEY" ]; then
    echo "✅ API key already configured in environment"
else
    echo "⚠️  No API key found in environment"
    echo ""
    echo "To set up your Groq API key:"
    echo "1. Get a free API key from: https://console.groq.com/keys"
    echo "2. Run one of these commands:"
    echo ""
    echo "   # Temporary (current session only):"
    echo "   export GROQ_API_KEY='your_key_here'"
    echo ""
    echo "   # Permanent (add to ~/.bashrc or ~/.zshrc):"
    echo "   echo 'export GROQ_API_KEY=\"your_key_here\"' >> ~/.bashrc"
    echo "   source ~/.bashrc"
    echo ""
    read -p "Do you want to set it now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Groq API key: " api_key
        export GROQ_API_KEY="$api_key"
        echo "✅ API key set for this session"
        echo ""
        echo "To make it permanent, add this to your ~/.bashrc:"
        echo "export GROQ_API_KEY=\"$api_key\""
    fi
fi

echo ""
echo "=========================================="
echo "Running BenX AI..."
echo "=========================================="
echo ""

python3 benx.py "$@"
