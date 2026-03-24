#!/bin/bash
echo "=== BenX Window Properties Finder ==="
echo ""
echo "Instructions:"
echo "1. Keep this terminal open"
echo "2. Start BenX in another terminal: python benx.py"
echo "3. Click the □ button to open compact mode"
echo "4. Press Enter here to see window properties"
echo ""
read -p "Press Enter when BenX compact window is open..."

echo ""
echo "=== All BenX-related windows ==="
hyprctl clients | grep -B 2 -A 15 -i "benx"

echo ""
echo "=== Floating windows only ==="
hyprctl clients | grep -B 2 -A 15 "floating: 1" | grep -B 2 -A 15 -i "benx"
