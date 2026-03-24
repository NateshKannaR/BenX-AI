"""
Modern Floating GUI with beautiful UI - Always-On Companion Mode
"""
import threading
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GUI_AVAILABLE = False
USE_CUSTOMTKINTER = False

try:
    import customtkinter as ctk
    GUI_AVAILABLE = True
    USE_CUSTOMTKINTER = True
except ImportError:
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox
        GUI_AVAILABLE = True
        USE_CUSTOMTKINTER = False
    except ImportError:
        GUI_AVAILABLE = False

# System tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    logger.warning("System tray not available. Install: pip install pystray pillow")

# Global hotkey support
try:
    import keyboard
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False
    logger.warning("Global hotkey not available. Install: pip install keyboard")


class FloatingGUI:
    """Modern floating GUI with beautiful design - Always-On Companion"""
    
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.voice_handler import VoiceHandler
        self.ai_engine = AIEngine()
        self.voice_handler = VoiceHandler()
        self.root = None
        self.processing = False
        self.tray_icon = None
        self.is_compact = False
        self.is_visible = True
        self.cpu_history = []
        self.gpu_history = []
        self.robot_photo = None
        self.setup_gui()
        self.setup_tray()
        self.setup_hotkey()
    
    def setup_gui(self):
        """Setup the floating GUI"""
        if not GUI_AVAILABLE:
            logger.warning("GUI not available")
            return
        
        if USE_CUSTOMTKINTER:
            self._setup_customtkinter_gui()
        else:
            self._setup_tkinter_gui()
    
    def _setup_customtkinter_gui(self):
        """Setup using customtkinter for modern look"""
        import tkinter as tk
        from jarvis_ai.config import Config
        ui_font = Config.FONT_FAMILY
        heading_font = getattr(Config, "HEADING_FONT_FAMILY", Config.FONT_FAMILY)

        # Configure customtkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("BenX - Advanced Assistant")

        # Floating window properties
        self.root.attributes('-topmost', False)
        self.root.attributes('-alpha', Config.WINDOW_OPACITY)

        width = Config.WINDOW_WIDTH
        height = Config.WINDOW_HEIGHT
        self.root.geometry(f"{width}x{height}")
        self.center_window()

        # Main container
        main_frame = ctk.CTkFrame(self.root, fg_color=Config.BG_COLOR)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header bar
        header_frame = ctk.CTkFrame(
            main_frame,
            fg_color=Config.GLASS_COLOR_DARK,
            height=56,
            corner_radius=14,
            border_width=1,
            border_color=Config.GLASS_BORDER
        )
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        logo = ctk.CTkLabel(
            header_frame,
            text="M",
            font=ctk.CTkFont(family=heading_font, size=18, weight="bold"),
            text_color=Config.ACCENT_COLOR
        )
        logo.pack(side="left", padx=(14, 10))

        nav_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        nav_frame.pack(side="left")

        tabs = ["Startside", "Scenario", "Overvaking", "Appsenter"]
        for idx, tab in enumerate(tabs):
            is_active = idx == 0
            tab_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
            tab_frame.pack(side="left", padx=10)

            tab_label = ctk.CTkLabel(
                tab_frame,
                text=tab,
                font=ctk.CTkFont(family=ui_font, size=12, weight="bold" if is_active else "normal"),
                text_color=Config.TEXT_COLOR if is_active else "#7b9db2"
            )
            tab_label.pack()

            underline = ctk.CTkFrame(
                tab_frame,
                fg_color=Config.ACCENT_COLOR if is_active else "transparent",
                height=2,
                width=64
            )
            underline.pack(pady=(4, 0))

        header_right = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_right.pack(side="right", padx=12)

        status_dot = tk.Canvas(header_right, width=10, height=10, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        status_dot.pack(side="right", padx=(6, 6))
        status_dot.create_oval(1, 1, 9, 9, fill=Config.ACCENT_COLOR_2, outline=Config.ACCENT_COLOR_2)

        self.status_label = ctk.CTkLabel(
            header_right,
            text="Ready",
            font=ctk.CTkFont(family=ui_font, size=11),
            text_color=Config.TEXT_COLOR
        )
        self.status_label.pack(side="right", padx=(6, 10))

        for icon in ["⚙", "≡", "✕"]:
            btn = ctk.CTkButton(
                header_right,
                text=icon,
                width=28,
                height=26,
                command=self.on_closing if icon == "✕" else None,
                fg_color="transparent",
                hover_color=Config.GLASS_COLOR,
                text_color=Config.TEXT_COLOR
            )
            btn.pack(side="right", padx=4)

        # Content layout
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.left_panel = ctk.CTkFrame(
            content_frame,
            fg_color=Config.GLASS_COLOR,
            width=300,
            corner_radius=14,
            border_width=1,
            border_color=Config.GLASS_BORDER
        )
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        left_title = ctk.CTkLabel(
            self.left_panel,
            text="GPU",
            font=ctk.CTkFont(family=heading_font, size=18, weight="bold"),
            text_color=Config.TEXT_COLOR
        )
        left_title.pack(pady=(14, 2))

        left_sub = ctk.CTkLabel(
            self.left_panel,
            text="Frekvens",
            font=ctk.CTkFont(family=ui_font, size=11),
            text_color="#89a5b7"
        )
        left_sub.pack(pady=(0, 6))

        self.gpu_canvas = tk.Canvas(self.left_panel, width=230, height=230, bg=Config.GLASS_COLOR, highlightthickness=0)
        self.gpu_canvas.pack(pady=(6, 10))
        self._draw_gpu_gauge(self.gpu_canvas, 0.35)

        gpu_hint = ctk.CTkLabel(
            self.left_panel,
            text="Diskret GPU er inaktiv",
            font=ctk.CTkFont(family=ui_font, size=10),
            text_color="#7ea0b7"
        )
        gpu_hint.pack(pady=(0, 8))

        stats_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        stats_frame.pack(fill="x", padx=16, pady=(4, 6))

        gpu_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        gpu_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(gpu_row, text="GPU Bruk", font=ctk.CTkFont(family=ui_font, size=11), text_color="#7ea0b7").pack(side="left")
        self.gpu_use_label = ctk.CTkLabel(gpu_row, text="--%", font=ctk.CTkFont(family=heading_font, size=11), text_color=Config.TEXT_COLOR)
        self.gpu_use_label.pack(side="right")

        self.gpu_hist_canvas = tk.Canvas(self.left_panel, width=240, height=60, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.gpu_hist_canvas.pack(padx=16, pady=(0, 10))
        self._draw_bar_chart(self.gpu_hist_canvas, [0] * 40, Config.ACCENT_COLOR)

        cpu_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cpu_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(cpu_row, text="CPU Bruk", font=ctk.CTkFont(family=ui_font, size=11), text_color="#7ea0b7").pack(side="left")
        self.cpu_use_label = ctk.CTkLabel(cpu_row, text="--%", font=ctk.CTkFont(family=heading_font, size=11), text_color=Config.TEXT_COLOR)
        self.cpu_use_label.pack(side="right")

        self.cpu_hist_canvas = tk.Canvas(self.left_panel, width=240, height=60, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.cpu_hist_canvas.pack(padx=16, pady=(0, 12))
        self._draw_bar_chart(self.cpu_hist_canvas, [0] * 40, Config.ACCENT_COLOR_2)

        center_panel = ctk.CTkFrame(content_frame, fg_color="transparent")
        center_panel.pack(side="left", fill="both", expand=True)

        center_header = ctk.CTkFrame(center_panel, fg_color="transparent")
        center_header.pack(fill="x", padx=16, pady=(12, 6))

        center_title = ctk.CTkFrame(center_header, fg_color="transparent")
        center_title.pack()

        ctk.CTkLabel(
            center_title,
            text="PREDATOR",
            font=ctk.CTkFont(family=heading_font, size=20, weight="bold"),
            text_color=Config.ACCENT_COLOR
        ).pack(side="left")
        ctk.CTkLabel(
            center_title,
            text="SENSE",
            font=ctk.CTkFont(family=heading_font, size=20, weight="bold"),
            text_color=Config.TEXT_COLOR
        ).pack(side="left", padx=(4, 0))

        mode_label = ctk.CTkLabel(
            center_panel,
            text="System Modus",
            font=ctk.CTkFont(family=ui_font, size=11),
            text_color="#8db2c8"
        )
        mode_label.pack()

        mode_value = ctk.CTkLabel(
            center_panel,
            text="Turbo",
            font=ctk.CTkFont(family=ui_font, size=16, weight="bold"),
            text_color=Config.ACCENT_COLOR_2
        )
        mode_value.pack(pady=(0, 6))

        center_body = ctk.CTkFrame(center_panel, fg_color="transparent")
        center_body.pack(fill="both", expand=True, padx=16, pady=(6, 10))

        hero_panel = ctk.CTkFrame(
            center_body,
            fg_color=Config.GLASS_COLOR_DARK,
            corner_radius=18,
            border_width=1,
            border_color=Config.GLASS_BORDER
        )
        hero_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))
        hero_panel.pack_propagate(False)

        self.hero_canvas = tk.Canvas(hero_panel, width=520, height=380, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.hero_canvas.pack(fill="both", expand=True, padx=14, pady=14)
        self._draw_hero_scene(self.hero_canvas)

        temp_panel = ctk.CTkFrame(
            center_body,
            fg_color=Config.GLASS_COLOR_DARK,
            corner_radius=18,
            border_width=1,
            border_color=Config.GLASS_BORDER,
            width=220
        )
        temp_panel.pack(side="left", fill="y")
        temp_panel.pack_propagate(False)

        temp_label = ctk.CTkLabel(
            temp_panel,
            text="TEMPERATURE",
            font=ctk.CTkFont(family=heading_font, size=10, weight="bold"),
            text_color="#7fb3c8"
        )
        temp_label.pack(pady=(10, 4))

        self.temp_gpu = tk.Canvas(temp_panel, width=170, height=170, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.temp_gpu.pack(pady=6)
        self._draw_ring(self.temp_gpu, 0.4, "GPU", accent_color=Config.ACCENT_COLOR, value_text="°C")

        self.temp_cpu = tk.Canvas(temp_panel, width=170, height=170, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.temp_cpu.pack(pady=6)
        self._draw_ring(self.temp_cpu, 0.35, "CPU", accent_color=Config.ACCENT_COLOR_2, value_text="°C")

        self.temp_sys = tk.Canvas(temp_panel, width=170, height=170, bg=Config.GLASS_COLOR_DARK, highlightthickness=0)
        self.temp_sys.pack(pady=6)
        self._draw_ring(self.temp_sys, 0.3, "System", accent_color=Config.ACCENT_COLOR_2, value_text="°C")

        self.chat_scroll = ctk.CTkScrollableFrame(center_panel, fg_color=Config.GLASS_COLOR, corner_radius=12, height=160, border_width=1, border_color=Config.GLASS_BORDER)
        self.chat_scroll.pack(fill="x", padx=16, pady=(0, 12))

        input_frame = ctk.CTkFrame(center_panel, fg_color=Config.GLASS_COLOR_DARK, corner_radius=12, border_width=1, border_color=Config.GLASS_BORDER)
        input_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask me anything or give me a command...",
            font=ctk.CTkFont(family=ui_font, size=12),
            height=38,
            fg_color=Config.GLASS_COLOR,
            border_color=Config.GLASS_HIGHLIGHT
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=10)
        self.input_entry.bind('<Return>', lambda e: self.process_input())
        self.input_entry.focus()

        self.send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            width=70,
            height=32,
            command=self.process_input,
            fg_color=Config.ACCENT_COLOR,
            hover_color="#1bc6bf",
            text_color=Config.BG_COLOR
        )
        self.send_button.pack(side="left", padx=6)

        self.voice_button = ctk.CTkButton(
            input_frame,
            text="Voice",
            width=60,
            height=32,
            command=self.voice_input,
            fg_color=Config.SUCCESS_COLOR if hasattr(self.voice_handler, 'recognizer') else Config.SECONDARY_COLOR,
            hover_color="#46c37f",
            text_color=Config.BG_COLOR
        )
        self.voice_button.pack(side="left", padx=6)

        self.right_panel = ctk.CTkFrame(
            content_frame,
            fg_color=Config.GLASS_COLOR,
            width=300,
            corner_radius=14,
            border_width=1,
            border_color=Config.GLASS_BORDER
        )
        self.right_panel.pack(side="left", fill="y", padx=(10, 0))
        self.right_panel.pack_propagate(False)

        widget_title = ctk.CTkLabel(
            self.right_panel,
            text="Widget",
            font=ctk.CTkFont(family=heading_font, size=12, weight="bold"),
            text_color=Config.TEXT_COLOR
        )
        widget_title.pack(pady=(12, 6))

        scenario_frame = ctk.CTkFrame(self.right_panel, fg_color=Config.GLASS_COLOR_DARK, corner_radius=10, border_width=1, border_color=Config.GLASS_BORDER)
        scenario_frame.pack(fill="x", padx=12, pady=(0, 10))
        scenario_label = ctk.CTkLabel(
            scenario_frame,
            text="Scenarioprofil",
            font=ctk.CTkFont(family=heading_font, size=10),
            text_color=Config.ACCENT_COLOR
        )
        scenario_label.pack(anchor="w", padx=10, pady=(8, 2))
        self.profile_menu = ctk.CTkOptionMenu(
            scenario_frame,
            values=["Daglig bruk", "Gaming", "Silent"],
            fg_color=Config.GLASS_COLOR,
            button_color=Config.ACCENT_COLOR,
            button_hover_color="#16a9bf",
            text_color=Config.TEXT_COLOR
        )
        self.profile_menu.pack(fill="x", padx=10, pady=(0, 8))

        self._scenario_row(scenario_frame, "Modus", "Turbo >")
        self._scenario_row(scenario_frame, "Vifte", "Maks. >")
        self._scenario_row(scenario_frame, "Effekt", "Bolge >")

        scenario_detail = ctk.CTkLabel(
            scenario_frame,
            text="Detaljer ->",
            font=ctk.CTkFont(family=ui_font, size=10),
            text_color="#7ea0b7"
        )
        scenario_detail.pack(anchor="e", padx=10, pady=(4, 8))

        monitoring_frame = ctk.CTkFrame(self.right_panel, fg_color=Config.GLASS_COLOR_DARK, corner_radius=10, border_width=1, border_color=Config.GLASS_BORDER)
        monitoring_frame.pack(fill="x", padx=12, pady=(0, 10))

        monitoring_header = ctk.CTkFrame(monitoring_frame, fg_color="transparent")
        monitoring_header.pack(fill="x", padx=10, pady=(8, 6))
        ctk.CTkLabel(
            monitoring_header,
            text="Overvaking",
            font=ctk.CTkFont(family=heading_font, size=10),
            text_color=Config.ACCENT_COLOR
        ).pack(side="left")
        ctk.CTkLabel(
            monitoring_header,
            text="🔧",
            font=ctk.CTkFont(family=ui_font, size=10),
            text_color="#7ea0b7"
        ).pack(side="right")

        grid_frame = ctk.CTkFrame(monitoring_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 4))

        self.mon_gpu_pct = self._monitor_box(grid_frame, "GPU %", "--", 0, 0)
        self.mon_gpu_temp = self._monitor_box(grid_frame, "GPU °C", "--", 0, 1)
        self.mon_cpu_pct = self._monitor_box(grid_frame, "CPU %", "--", 0, 2)
        self.mon_cpu_temp = self._monitor_box(grid_frame, "CPU °C", "--", 1, 0)
        self.mon_sys_temp = self._monitor_box(grid_frame, "System °C", "--", 1, 1)
        self.mon_ram_pct = self._monitor_box(grid_frame, "RAM %", "--", 1, 2)

        monitor_detail = ctk.CTkLabel(
            monitoring_frame,
            text="Detaljer ->",
            font=ctk.CTkFont(family=ui_font, size=10),
            text_color="#7ea0b7"
        )
        monitor_detail.pack(anchor="e", padx=10, pady=(4, 8))

        shortcuts_frame = ctk.CTkFrame(self.right_panel, fg_color=Config.GLASS_COLOR_DARK, corner_radius=10, border_width=1, border_color=Config.GLASS_BORDER)
        shortcuts_frame.pack(fill="x", padx=12, pady=(0, 10))
        shortcuts_title = ctk.CTkLabel(
            shortcuts_frame,
            text="App-snarvei",
            font=ctk.CTkFont(family=heading_font, size=10),
            text_color=Config.ACCENT_COLOR
        )
        shortcuts_title.pack(anchor="w", padx=10, pady=(8, 6))

        shortcuts_row = ctk.CTkFrame(shortcuts_frame, fg_color="transparent")
        shortcuts_row.pack(padx=10, pady=(0, 6))
        for label in ["K", "G", "X", "DTS"]:
            btn = ctk.CTkButton(
                shortcuts_row,
                text=label,
                width=44,
                height=36,
                fg_color=Config.GLASS_COLOR,
                hover_color=Config.GLASS_BORDER,
                text_color=Config.TEXT_COLOR
            )
            btn.pack(side="left", padx=4)

        shortcuts_detail = ctk.CTkLabel(
            shortcuts_frame,
            text="Detaljer ->",
            font=ctk.CTkFont(family=ui_font, size=10),
            text_color="#7ea0b7"
        )
        shortcuts_detail.pack(anchor="e", padx=10, pady=(2, 8))

        self.update_system_stats()

        # Welcome message
        self.add_message("BenX", "Hello! I'm BenX, your always-on AI companion. Press Ctrl+Space anytime to summon me!", "assistant")
        
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
    
    def _setup_tkinter_gui(self):
        """Fallback to standard tkinter"""
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox
        from jarvis_ai.config import Config
        
        self.root = tk.Tk()
        self.root.title("BenX - Advanced Assistant")
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.configure(bg=Config.BG_COLOR)
        self.root.attributes('-alpha', Config.WINDOW_OPACITY)
        self.center_window()
        
        # Header
        header = tk.Frame(self.root, bg=Config.THEME_COLOR, height=60)
        header.pack(fill=tk.X)
        
        title = tk.Label(header, text="🎯 BenX Assistant", font=("Arial", 18, "bold"),
                        bg=Config.THEME_COLOR, fg=Config.ACCENT_COLOR)
        title.pack(side=tk.LEFT, padx=15, pady=15)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg=Config.THEME_COLOR,
            fg=Config.TEXT_COLOR,
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_display.config(state=tk.DISABLED)
        
        # Input
        input_frame = tk.Frame(self.root, bg=Config.BG_COLOR)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.input_entry = tk.Entry(
            input_frame,
            font=("Arial", 12),
            bg=Config.THEME_COLOR,
            fg=Config.TEXT_COLOR,
            relief=tk.FLAT,
            insertbackground=Config.ACCENT_COLOR
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        self.input_entry.bind('<Return>', lambda e: self.process_input())
        
        send_btn = tk.Button(input_frame, text="Send", command=self.process_input,
                            bg=Config.ACCENT_COLOR, fg="white", relief=tk.FLAT, padx=20, pady=8)
        send_btn.pack(side=tk.RIGHT)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def add_message(self, sender: str, message: str, role: str = "user"):
        """Add message to chat"""
        if USE_CUSTOMTKINTER:
            from jarvis_ai.config import Config
            timestamp = datetime.now().strftime("%H:%M")
            is_user = role == "user" or sender == "You"
            bubble_color = Config.ACCENT_COLOR if is_user else Config.SECONDARY_COLOR
            text_color = "#0b0b0f" if is_user else Config.TEXT_COLOR

            bubble = ctk.CTkFrame(self.chat_scroll, fg_color=bubble_color, corner_radius=10)
            bubble.pack(fill="x", padx=8, pady=6, anchor="e" if is_user else "w")

            meta = ctk.CTkLabel(
                bubble,
                text=f"{sender} • {timestamp}",
                font=ctk.CTkFont(family=Config.FONT_FAMILY, size=10),
                text_color=text_color
            )
            meta.pack(anchor="w", padx=10, pady=(6, 0))

            content = ctk.CTkLabel(
                bubble,
                text=message,
                font=ctk.CTkFont(family=Config.FONT_FAMILY, size=12),
                text_color=text_color,
                wraplength=640,
                justify="left"
            )
            content.pack(anchor="w", padx=10, pady=(2, 8))

            self.chat_scroll.update_idletasks()
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        else:
            import tkinter as tk
            self.chat_display.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M")
            self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)

    def clear_chat(self):
        """Clear the chat display."""
        if USE_CUSTOMTKINTER:
            for child in self.chat_scroll.winfo_children():
                child.destroy()
        else:
            import tkinter as tk
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
    
    def update_status(self, status: str):
        """Update status label"""
        if hasattr(self, 'status_label'):
            if USE_CUSTOMTKINTER:
                self.status_label.configure(text=status)
            else:
                self.status_label.config(text=status)

    def update_system_stats(self):
        """Update system stats in the UI."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            gpu = max(0.0, min(100.0, cpu * 0.7))

            if hasattr(self, "gpu_use_label"):
                self.gpu_use_label.configure(text=f"{gpu:.0f}%")
            if hasattr(self, "cpu_use_label"):
                self.cpu_use_label.configure(text=f"{cpu:.0f}%")
            if hasattr(self, "mon_gpu_pct"):
                self.mon_gpu_pct.configure(text=f"{gpu:.0f}")
            if hasattr(self, "mon_gpu_temp"):
                self.mon_gpu_temp.configure(text="--")
            if hasattr(self, "mon_cpu_pct"):
                self.mon_cpu_pct.configure(text=f"{cpu:.0f}")
            if hasattr(self, "mon_cpu_temp"):
                self.mon_cpu_temp.configure(text="--")
            if hasattr(self, "mon_sys_temp"):
                self.mon_sys_temp.configure(text="--")
            if hasattr(self, "mon_ram_pct"):
                self.mon_ram_pct.configure(text=f"{mem.percent:.0f}")
            if hasattr(self, "gpu_canvas"):
                self._draw_gpu_gauge(self.gpu_canvas, gpu / 100.0)
            if hasattr(self, "ring_cpu"):
                self._draw_ring(self.ring_cpu, cpu / 100.0, "CPU", accent_color=Config.ACCENT_COLOR)
            if hasattr(self, "ring_mem"):
                self._draw_ring(self.ring_mem, mem.percent / 100.0, "System", accent_color=Config.ACCENT_COLOR_2)
            if hasattr(self, "temp_gpu"):
                self._draw_ring(self.temp_gpu, cpu / 100.0, "GPU", accent_color=Config.ACCENT_COLOR, value_text="°C")
            if hasattr(self, "temp_cpu"):
                self._draw_ring(self.temp_cpu, cpu / 100.0, "CPU", accent_color=Config.ACCENT_COLOR_2, value_text="°C")
            if hasattr(self, "temp_sys"):
                self._draw_ring(self.temp_sys, mem.percent / 100.0, "System", accent_color=Config.ACCENT_COLOR_2, value_text="°C")
            if hasattr(self, "gpu_hist_canvas"):
                self.gpu_history.append(gpu / 100.0)
                self.gpu_history = self.gpu_history[-40:]
                self._draw_bar_chart(self.gpu_hist_canvas, self.gpu_history, Config.ACCENT_COLOR)
            if hasattr(self, "cpu_hist_canvas"):
                self.cpu_history.append(cpu / 100.0)
                self.cpu_history = self.cpu_history[-40:]
                self._draw_bar_chart(self.cpu_hist_canvas, self.cpu_history, Config.ACCENT_COLOR_2)
        except Exception:
            pass

        if self.root:
            self.root.after(2000, self.update_system_stats)

    def _draw_ring(self, canvas, percent: float, label: str, accent_color: Optional[str] = None, value_text: Optional[str] = None):
        """Draw a neon ring gauge on a tkinter Canvas."""
        from jarvis_ai.config import Config
        percent = max(0.0, min(1.0, percent))
        canvas.delete("ring")
        size = min(int(canvas["width"]), int(canvas["height"]))
        pad = 10
        x0, y0, x1, y1 = pad, pad, size - pad, size - pad
        accent = accent_color or Config.ACCENT_COLOR
        canvas.create_oval(x0 - 4, y0 - 4, x1 + 4, y1 + 4, outline=Config.GLASS_BORDER, width=2, tags="ring")
        canvas.create_oval(x0, y0, x1, y1, outline=Config.GLASS_COLOR, width=10, tags="ring")
        extent = int(360 * percent)
        canvas.create_arc(
            x0, y0, x1, y1,
            start=90, extent=-extent,
            style="arc",
            outline=accent,
            width=10,
            tags="ring"
        )
        for angle in range(0, 360, 30):
            canvas.create_arc(
                x0 - 6, y0 - 6, x1 + 6, y1 + 6,
                start=angle, extent=2,
                style="arc",
                outline=Config.GLASS_BORDER,
                width=2,
                tags="ring"
            )
        center_text = value_text if value_text is not None else f"{int(percent * 100)}%"
        canvas.create_text(
            size // 2,
            size // 2 - 8,
            text=center_text,
            fill=Config.TEXT_COLOR,
            font=(Config.FONT_FAMILY, 12, "bold"),
            tags="ring"
        )
        canvas.create_text(
            size // 2,
            size // 2 + 12,
            text=label,
            fill=Config.TEXT_COLOR,
            font=(Config.FONT_FAMILY, 10),
            tags="ring"
        )

    def _draw_robot(self, canvas):
        """Draw a simple robot silhouette on a tkinter Canvas."""
        from jarvis_ai.config import Config
        canvas.delete("robot")
        width = int(canvas["width"])
        height = int(canvas["height"])
        cx = width // 2
        cy = height // 2 + 6

        glow = Config.ACCENT_COLOR
        body = "#0b1a22"
        outline = Config.ACCENT_COLOR
        eye = "#e6f1ff"

        # Head
        canvas.create_oval(cx - 26, cy - 70, cx + 26, cy - 18, fill=body, outline=outline, width=2, tags="robot")
        canvas.create_rectangle(cx - 6, cy - 85, cx + 6, cy - 70, fill=outline, outline=outline, tags="robot")
        canvas.create_oval(cx - 10, cy - 55, cx - 2, cy - 47, fill=eye, outline=eye, tags="robot")
        canvas.create_oval(cx + 2, cy - 55, cx + 10, cy - 47, fill=eye, outline=eye, tags="robot")

        # Torso
        canvas.create_rectangle(cx - 32, cy - 16, cx + 32, cy + 46, fill=body, outline=outline, width=2, tags="robot")
        canvas.create_rectangle(cx - 16, cy - 2, cx + 16, cy + 8, fill=glow, outline=glow, tags="robot")

        # Arms
        canvas.create_rectangle(cx - 52, cy - 6, cx - 32, cy + 10, fill=body, outline=outline, width=2, tags="robot")
        canvas.create_rectangle(cx + 32, cy - 6, cx + 52, cy + 10, fill=body, outline=outline, width=2, tags="robot")

        # Legs
        canvas.create_rectangle(cx - 22, cy + 46, cx - 2, cy + 78, fill=body, outline=outline, width=2, tags="robot")
        canvas.create_rectangle(cx + 2, cy + 46, cx + 22, cy + 78, fill=body, outline=outline, width=2, tags="robot")

    def _load_robot_image(self, max_size: int = 260):
        """Load the robot hero image if available."""
        if self.robot_photo is not None:
            return self.robot_photo

        try:
            from PIL import Image, ImageTk
        except Exception:
            return None

        asset_path = Path(__file__).resolve().parent / "assets" / "robot-hero.png"
        if not asset_path.exists():
            return None

        image = Image.open(asset_path)
        image.thumbnail((max_size, max_size))
        self.robot_photo = ImageTk.PhotoImage(image)
        return self.robot_photo

    def _draw_hero_scene(self, canvas):
        """Draw the hero glass frame and robot image."""
        from jarvis_ai.config import Config
        canvas.delete("hero")
        w = int(canvas["width"])
        h = int(canvas["height"])
        pad = 18

        canvas.create_rectangle(pad, pad, w - pad, h - pad, outline=Config.GLASS_BORDER, width=2, tags="hero")
        canvas.create_line(pad, pad + 30, pad + 40, pad + 30, fill=Config.ACCENT_COLOR, width=2, tags="hero")
        canvas.create_line(w - pad - 40, h - pad - 30, w - pad, h - pad - 30, fill=Config.ACCENT_COLOR_2, width=2, tags="hero")
        canvas.create_oval(w // 2 - 90, h - 60, w // 2 + 90, h - 30, outline=Config.ACCENT_COLOR, width=2, tags="hero")

        robot_img = self._load_robot_image(max_size=260)
        if robot_img:
            canvas.create_image(w // 2, h // 2 + 10, image=robot_img, tags="hero")
        else:
            self._draw_robot(canvas)

    def _draw_gpu_gauge(self, canvas, percent: float):
        """Draw the GPU gauge ring with tick marks."""
        from jarvis_ai.config import Config
        percent = max(0.0, min(1.0, percent))
        canvas.delete("gpu")
        size = min(int(canvas["width"]), int(canvas["height"]))
        pad = 12
        x0, y0, x1, y1 = pad, pad, size - pad, size - pad

        canvas.create_oval(x0, y0, x1, y1, outline=Config.GLASS_BORDER, width=2, tags="gpu")
        canvas.create_oval(x0 + 6, y0 + 6, x1 - 6, y1 - 6, outline=Config.ACCENT_COLOR, width=3, tags="gpu")

        extent = int(360 * percent)
        canvas.create_arc(
            x0 + 6, y0 + 6, x1 - 6, y1 - 6,
            start=90, extent=-extent,
            style="arc",
            outline=Config.ACCENT_COLOR,
            width=4,
            tags="gpu"
        )

        for i in range(24):
            angle = math.radians(i * 15 - 90)
            r1 = (size // 2) - 30
            r2 = r1 + 6
            cx = size // 2
            cy = size // 2
            x1t = cx + r1 * math.cos(angle)
            y1t = cy + r1 * math.sin(angle)
            x2t = cx + r2 * math.cos(angle)
            y2t = cy + r2 * math.sin(angle)
            canvas.create_line(x1t, y1t, x2t, y2t, fill=Config.GLASS_BORDER, width=1, tags="gpu")

        canvas.create_text(size // 2, size // 2 - 14, text="GPU", fill=Config.TEXT_COLOR, font=(Config.HEADING_FONT_FAMILY, 16, "bold"), tags="gpu")
        canvas.create_text(size // 2, size // 2 + 2, text="Frekvens", fill="#89a5b7", font=(Config.FONT_FAMILY, 10), tags="gpu")
        canvas.create_text(size // 2, size // 2 + 26, text="--", fill=Config.TEXT_COLOR, font=(Config.HEADING_FONT_FAMILY, 16, "bold"), tags="gpu")
        canvas.create_text(size // 2, size // 2 + 46, text="MHz", fill="#89a5b7", font=(Config.FONT_FAMILY, 9), tags="gpu")

    def _draw_bar_chart(self, canvas, values, color: str):
        """Draw a small bar chart for usage history."""
        from jarvis_ai.config import Config
        canvas.delete("bars")
        w = int(canvas["width"])
        h = int(canvas["height"])
        canvas.create_rectangle(2, 2, w - 2, h - 2, outline=Config.GLASS_BORDER, width=1, tags="bars")

        if not values:
            return

        bar_count = len(values)
        gap = 2
        bar_width = max(1, int((w - 10 - (bar_count - 1) * gap) / bar_count))
        x = 6
        for v in values:
            bar_h = max(2, int((h - 10) * max(0.0, min(1.0, v))))
            canvas.create_rectangle(x, h - 6 - bar_h, x + bar_width, h - 6, fill=color, outline="", tags="bars")
            x += bar_width + gap

    def _scenario_row(self, parent, label: str, value: str):
        """Create a scenario setting row."""
        from jarvis_ai.config import Config
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family=Config.FONT_FAMILY, size=10), text_color="#7ea0b7").pack(side="left")
        ctk.CTkLabel(row, text=value, font=ctk.CTkFont(family=Config.FONT_FAMILY, size=10), text_color=Config.TEXT_COLOR).pack(side="right")

    def _monitor_box(self, parent, label: str, value: str, row: int, col: int):
        """Create a monitoring stat box."""
        from jarvis_ai.config import Config
        box = ctk.CTkFrame(parent, fg_color=Config.GLASS_COLOR, corner_radius=8, border_width=1, border_color=Config.GLASS_BORDER)
        box.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        val = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(family=Config.HEADING_FONT_FAMILY, size=12, weight="bold"),
            text_color=Config.TEXT_COLOR
        )
        val.pack(pady=(6, 0))
        ctk.CTkLabel(
            box,
            text=label,
            font=ctk.CTkFont(family=Config.FONT_FAMILY, size=9),
            text_color="#7ea0b7"
        ).pack(pady=(0, 6))
        return val
    def _draw_hud_frame(self, canvas):
        """Draw a HUD-style frame behind the hero area."""
        from jarvis_ai.config import Config
        canvas.delete("hud")
        w = int(canvas["width"])
        h = int(canvas["height"])
        pad = 14
        canvas.create_rectangle(pad, pad, w - pad, h - pad, outline=Config.GLASS_BORDER, width=2, tags="hud")
        canvas.create_line(pad, pad + 24, pad + 30, pad + 24, fill=Config.ACCENT_COLOR, width=2, tags="hud")
        canvas.create_line(w - pad - 30, h - pad - 24, w - pad, h - pad - 24, fill=Config.ACCENT_COLOR_2, width=2, tags="hud")
        canvas.create_oval(w // 2 - 70, h - 40, w // 2 + 70, h - 16, outline=Config.ACCENT_COLOR, width=2, tags="hud")

    def _draw_sparkline(self, canvas):
        """Draw a static sparkline for the side panel."""
        from jarvis_ai.config import Config
        canvas.delete("spark")
        w = int(canvas["width"])
        h = int(canvas["height"])
        canvas.create_rectangle(6, 6, w - 6, h - 6, outline=Config.GLASS_BORDER, width=1, tags="spark")
        points = [(10, h - 18), (40, h - 24), (70, h - 36), (100, h - 30), (130, h - 42), (160, h - 28), (190, h - 38), (220, h - 26)]
        for i in range(len(points) - 1):
            canvas.create_line(*points[i], *points[i + 1], fill=Config.ACCENT_COLOR, width=2, tags="spark")
        canvas.create_text(14, 14, text="CPU Bruk", anchor="w", fill="#7ea0b7", font=(Config.FONT_FAMILY, 9), tags="spark")

    def _stat_box(self, parent, label: str, value: str, row: int, col: int):
        """Create a stat box in the monitoring panel."""
        from jarvis_ai.config import Config
        box = ctk.CTkFrame(parent, fg_color=Config.GLASS_COLOR_DARK, corner_radius=10, border_width=1, border_color=Config.GLASS_BORDER)
        box.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        label_widget = ctk.CTkLabel(
            box,
            text=label,
            font=ctk.CTkFont(family=Config.FONT_FAMILY, size=10),
            text_color="#8db2c8"
        )
        label_widget.pack(pady=(6, 2))
        value_widget = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(family=Config.FONT_FAMILY, size=16, weight="bold"),
            text_color=Config.TEXT_COLOR
        )
        value_widget.pack(pady=(0, 8))
        return value_widget

    def confirm_action(self, prompt: str) -> bool:
        """Ask for confirmation in the GUI thread and block for result."""
        if not self.root:
            return False

        response = {"value": False}
        event = threading.Event()

        def _ask():
            try:
                from tkinter import messagebox
                response["value"] = messagebox.askyesno("Confirm Action", prompt)
            finally:
                event.set()

        self.root.after(0, _ask)
        event.wait()
        return response["value"]
    
    def process_input(self):
        """Process user input"""
        if self.processing:
            return
        
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        # Clear input
        if USE_CUSTOMTKINTER:
            self.input_entry.delete(0, "end")
        else:
            self.input_entry.delete(0,"end")
        
        # Add user message
        self.add_message("You", user_input, "user")
        
        # Process in thread
        self.processing = True
        if hasattr(self, 'send_button'):
            if USE_CUSTOMTKINTER:
                self.send_button.configure(state="disabled")
            else:
                import tkinter as tk
                self.send_button.config(state=tk.DISABLED)
        self.update_status("Processing...")
        
        thread = threading.Thread(target=self._process_input_thread, args=(user_input,), daemon=True)
        thread.start()
    
    def _process_input_thread(self, user_input: str):
        """Process input in background"""
        try:
            self.jarvis.save_command(user_input)
            
            from jarvis_ai.executor import CommandExecutor
            
            self.update_status("Understanding...")
            json_cmd = self.ai_engine.interpret_command(
                user_input,
                conversation_context=self.ai_engine.conversation_history,
                learning_engine=self.ai_engine.learning_engine
            )
            
            result = CommandExecutor.execute(
                json_cmd,
                self.ai_engine,
                user_input,
                confirm_cb=self.confirm_action,
            )
            
            if result is None:
                self.update_status("Thinking...")
                response = self.ai_engine.chat(user_input)
                self.root.after(0, self._show_response, response, "assistant")
            else:
                self.root.after(0, self._show_response, result, "assistant")
        
        except Exception as e:
            logger.error(f"Processing error: {e}")
            self.root.after(0, self._show_response, f"❌ Error: {str(e)}", "assistant")
        finally:
            self.processing = False
            if hasattr(self, 'send_button'):
                self.root.after(0, lambda: self.send_button.configure(state="normal") if USE_CUSTOMTKINTER else self.send_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.update_status("Ready"))
    
    def _show_response(self, response: str, role: str):
        """Show response in GUI"""
        self.add_message("BenX", response, role)
        
        if hasattr(self.voice_handler, 'tts_engine') and len(response) < 500:
            self.voice_handler.speak(response)
    
    def voice_input(self):
        """Handle voice input"""
        self.update_status("Listening...")
        
        def _listen():
            text = self.voice_handler.listen()
            if text:
                if USE_CUSTOMTKINTER:
                    self.root.after(0, lambda: self.input_entry.insert(0, text))
                else:
                    self.root.after(0, lambda: self.input_entry.insert(0, text))
                self.root.after(0, lambda: self.process_input())
            self.root.after(0, lambda: self.update_status("Ready"))
        
        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
    
    def quick_action(self, command: str):
        """Execute quick action"""
        if USE_CUSTOMTKINTER:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, command)
        else:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, command)
        self.process_input()

    def prefill_input(self, text: str):
        """Prefill input without sending."""
        if not hasattr(self, "input_entry"):
            return
        if USE_CUSTOMTKINTER:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, text)
        else:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, text)
        self.input_entry.focus()
    
    def setup_tray(self):
        """Setup system tray icon"""
        if not TRAY_AVAILABLE:
            return
        
        def create_icon_image():
            # Create a simple icon
            img = Image.new('RGB', (64, 64), color='#89b4fa')
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill='#1e1e2e', outline='#89b4fa', width=3)
            draw.text((20, 20), "J", fill='#89b4fa')
            return img
        
        def show_window(icon, item):
            self.root.after(0, self.show_window)
        
        def hide_window(icon, item):
            self.root.after(0, self.hide_window)
        
        def quit_app(icon, item):
            self.root.after(0, self.quit_app)
            icon.stop()
        
        menu = pystray.Menu(
            pystray.MenuItem("Show BenX", show_window, default=True),
            pystray.MenuItem("Hide", hide_window),
            pystray.MenuItem("Compact Mode", lambda: self.root.after(0, self.toggle_compact_mode)),
            pystray.MenuItem("Quit", quit_app)
        )
        
        self.tray_icon = pystray.Icon("benx", create_icon_image(), "BenX Companion", menu)
        
        # Run tray in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def setup_hotkey(self):
        """Setup global hotkey (Ctrl+Space)"""
        if not HOTKEY_AVAILABLE:
            logger.warning("Global hotkey not available")
            return
        
        try:
            keyboard.add_hotkey('ctrl+space', self.toggle_window)
            logger.info("Global hotkey registered: Ctrl+Space")
        except Exception as e:
            logger.error(f"Failed to register hotkey: {e}")
    
    def toggle_window(self):
        """Toggle window visibility (for hotkey)"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def show_window(self):
        """Show the window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_visible = True
        if hasattr(self, 'input_entry'):
            self.input_entry.focus()
    
    def hide_window(self):
        """Hide the window"""
        self.root.withdraw()
        self.is_visible = False
    
    def minimize_to_tray(self):
        """Minimize to system tray instead of closing"""
        self.hide_window()
        if TRAY_AVAILABLE:
            self.add_message("System", "Minimized to tray. Press Ctrl+Space to restore.", "assistant")
    
    def toggle_compact_mode(self):
        """Toggle between full and compact mode"""
        from jarvis_ai.config import Config
        
        if self.is_compact:
            # Switch to full mode
            self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
            if hasattr(self, "left_panel"):
                self.left_panel.pack(side="left", fill="y", padx=(0, 10))
            if hasattr(self, "right_panel"):
                self.right_panel.pack(side="left", fill="y", padx=(10, 0))
            self.is_compact = False
        else:
            # Switch to compact mode
            self.root.geometry("400x200")
            if hasattr(self, "left_panel"):
                self.left_panel.pack_forget()
            if hasattr(self, "right_panel"):
                self.right_panel.pack_forget()
            self.is_compact = True
        
        self.center_window()
    
    def quit_app(self):
        """Completely quit the application"""
        if HOTKEY_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.destroy()
        self.jarvis.running = False
    
    def on_closing(self):
        """Handle window closing - minimize to tray by default"""
        self.minimize_to_tray()
    
    def run(self):
        """Run the GUI"""
        if self.root:
            self.root.mainloop()





