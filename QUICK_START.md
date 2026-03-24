# BenX Quick Start Guide

## Running BenX

### Start BenX with GTK4 UI
```bash
cd ~/Downloads/Ben
source venv/bin/activate
python benx.py
```

### Start in CLI Mode (No GUI)
```bash
python benx.py --no-gui
```

## What Was Fixed

**Problem:** `Namespace Gtk is already loaded with version 3.0`

**Solution:** 
- Changed `benx.py` to use GTK4 instead of tkinter
- GTK4 is now loaded FIRST before any other imports
- Removed conflicting imports from `jarvis_ai/gui/__init__.py`

## Features

### GTK4 UI Features
- ✅ Native Wayland support
- ✅ Screen recording exclusion (privacy)
- ✅ 3-panel layout (System Info | Logo | Chat)
- ✅ Real-time system monitoring
- ✅ Activity logging
- ✅ Voice input support
- ✅ Compact mode (floating chat window)
- ✅ Minimize to notification bar

### UI Modes
1. **Full Mode** - Complete 3-panel interface
2. **Compact Mode** - Floating chat window only (click □ button)
3. **Minimized** - Small notification bar (click ─ button)

## Troubleshooting

### If GTK4 error still occurs:
```bash
# Kill any running Python processes
pkill -9 python

# Restart your terminal
# Then try again
source venv/bin/activate
python benx.py
```

### Check GTK4 installation:
```bash
python -c "import gi; gi.require_version('Gtk', '4.0'); print('GTK4 OK')"
```

### Install GTK4 if missing:
```bash
# Arch Linux
sudo pacman -S gtk4 libadwaita python-gobject

# Ubuntu/Debian
sudo apt install libgtk-4-1 libadwaita-1-0 python3-gi
```

## File Structure
```
Ben/
├── benx.py              # Main entry (GTK4 UI)
├── benx_gtk4.py         # Alternative launcher
├── jarvis.py            # Old version (tkinter)
├── jarvis_ai/
│   ├── gui/
│   │   ├── benx_gtk4.py # GTK4 UI implementation
│   │   └── jarvis_ui.py # Old tkinter UI (not used)
│   ├── ai_engine.py
│   ├── executor.py
│   └── config.py
└── venv/                # Virtual environment
```

## Commands You Can Use

### System Control
- "volume 80" / "increase volume" / "decrease volume"
- "brightness 50" / "brighter" / "dimmer"
- "battery status"
- "system info"

### Applications
- "open chrome"
- "open terminal"
- "list running apps"

### Files
- "list files in Downloads"
- "create file test.txt"
- "search for python files"

### Chat
- "what's the weather?"
- "tell me a joke"
- "explain quantum computing"

## Next Steps

1. ✅ GTK4 is now working
2. Test the UI features (compact mode, minimize, etc.)
3. Try voice input (click VOICE button)
4. Explore system monitoring in left panel
5. Check activity log for command history

Enjoy BenX! 🎯
