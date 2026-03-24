#!/bin/bash
# Setup BenX windows to be excluded from screen recording

HYPR_CONFIG="$HOME/.config/hypr/hyprland.conf"

echo "Setting up BenX screen recording exclusion for Hyprland..."

# Add window rules to Hyprland config
if [ -f "$HYPR_CONFIG" ]; then
    # Check if rules already exist
    if ! grep -q "BenX-Compact" "$HYPR_CONFIG"; then
        echo "" >> "$HYPR_CONFIG"
        echo "# BenX - Exclude from screen recording" >> "$HYPR_CONFIG"
        echo "windowrulev2 = noscreenshot, title:^(BenX-Compact)$" >> "$HYPR_CONFIG"
        echo "windowrulev2 = noscreenshot, title:^(BenX-Notification)$" >> "$HYPR_CONFIG"
        echo "✅ Added window rules to $HYPR_CONFIG"
        echo "⚠️  Please reload Hyprland config: hyprctl reload"
    else
        echo "✅ Rules already exist in $HYPR_CONFIG"
    fi
else
    echo "❌ Hyprland config not found at $HYPR_CONFIG"
    echo "Please add these lines manually to your Hyprland config:"
    echo ""
    echo "windowrulev2 = noscreenshot, title:^(BenX-Compact)$"
    echo "windowrulev2 = noscreenshot, title:^(BenX-Notification)$"
fi

echo ""
echo "For OBS Studio, you can also:"
echo "1. Right-click on the window in OBS"
echo "2. Select 'Filters'"
echo "3. Add 'Window Capture' filter"
echo "4. Exclude windows with 'BenX' in the title"
