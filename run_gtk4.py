#!/usr/bin/env python3
"""
BenX GTK4 Launcher - Shortcut to benx.py

This ensures GTK4 is loaded first, then runs benx.py
"""

# MUST be first - load GTK4 before anything else
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

# Now safe to import everything else
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🎯 Starting BenX with GTK4 UI (Native Wayland)...")
    
    # Now import and run
    from benx import main
    main()
