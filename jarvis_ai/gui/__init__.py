"""GUI Package"""

# DO NOT import jarvis_ui here - it uses tkinter which may conflict with GTK4
# Import only when needed

GUI_AVAILABLE = False

try:
    import tkinter as tk
    GUI_AVAILABLE = True
except ImportError:
    pass

__all__ = ['GUI_AVAILABLE']











