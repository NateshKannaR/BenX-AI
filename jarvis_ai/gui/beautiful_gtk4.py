"""
BenX Beautiful GTK4 UI - Exact replica of tkinter design
3-Panel Layout: System Info | Animated Logo | Chat
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio
import threading
import logging
import math
import json
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

GTK_AVAILABLE = True


class BeautifulBenXGTK4(Adw.ApplicationWindow):
    def __init__(self, jarvis_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jarvis = jarvis_instance
        
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.voice_handler import VoiceHandler
        from jarvis_ai.config import Config
        
        self.ai_engine = AIEngine()
        self.voice_handler = VoiceHandler()
        self.config = Config
        self.processing = False
        self.window_mode = 'full'
        self.rotation = 0
        self.activity_entries = []
        self.message_history = []  # Store all messages for syncing
        self.last_benx_message = ""
        self.pending_image_path = None  # Image to attach to next message
        self.setup_gui()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Create event controller for keyboard
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)
    
    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts"""
        # Ctrl+C to copy (if text is selected)
        if state & Gdk.ModifierType.CONTROL_MASK:
            if keyval == Gdk.KEY_c or keyval == Gdk.KEY_C:
                # Get focused widget
                focus = self.get_focus()
                if isinstance(focus, Gtk.Label) and focus.get_selectable():
                    # Copy selected text from label
                    text = focus.get_text()
                    if text:
                        self.copy_to_clipboard(text)
                        return True
        return False
    
    def setup_gui(self):
        self.set_title("BenX AI Assistant")
        self.set_default_size(1400, 800)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)
        
        # Top: BenX Title with window controls
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_box.set_margin_start(20)
        title_box.set_margin_end(20)
        title_box.set_margin_top(20)
        title_box.set_margin_bottom(10)
        title_box.add_css_class("topbar")
        main_box.append(title_box)

        title_copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_copy.set_hexpand(True)
        
        eyebrow = Gtk.Label(label="Adaptive Linux control interface", xalign=0)
        eyebrow.add_css_class("eyebrow-label")
        title_copy.append(eyebrow)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title_label = Gtk.Label(label="BenX", xalign=0)
        title_label.add_css_class("title-huge")
        title_row.append(title_label)

        title_copy.append(title_row)
        
        title_box.append(title_copy)
        
        # Window control buttons
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.add_css_class("window-controls")
        
        close_btn = self.create_window_dot_button("window-dot-red", lambda w: self.get_application().quit())
        controls_box.append(close_btn)
        
        minimize_btn = self.create_window_dot_button("window-dot-yellow", self.on_minimize_clicked)
        controls_box.append(minimize_btn)
        
        compact_btn = self.create_window_dot_button("window-dot-green", self.on_compact_clicked)
        controls_box.append(compact_btn)
        
        title_box.append(controls_box)
        
        # Content: 3 panels
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(20)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)
        main_box.append(content_box)
        
        # LEFT PANEL - System Info
        left_panel = self.create_left_panel()
        content_box.append(left_panel)
        
        # CENTER PANEL - Animated Logo
        center_panel = self.create_center_panel()
        content_box.append(center_panel)
        
        # RIGHT PANEL - Chat
        right_panel = self.create_right_panel()
        content_box.append(right_panel)
        
        # Apply CSS
        self.apply_css()
        
        # Start updates
        GLib.timeout_add(50, self.animate_logo)
        GLib.timeout_add_seconds(1, self.update_time)
        GLib.timeout_add_seconds(2, self.update_stats)
        
        self.add_chat_message("BenX", "Hello! I'm BenX, your AI assistant. How can I help you?")
        self.log_activity("✅ BenX started")
    
    def create_left_panel(self):
        frame = Gtk.Frame()
        frame.add_css_class("panel-frame")
        frame.set_size_request(240, -1)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        frame.set_child(box)

        # Time
        time_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        time_card.add_css_class("time-card")

        self.time_label = Gtk.Label(label="", xalign=0)
        self.time_label.add_css_class("time-label")
        time_card.append(self.time_label)

        self.date_label = Gtk.Label(label="", xalign=0)
        self.date_label.add_css_class("date-label")
        time_card.append(self.date_label)
        box.append(time_card)

        sep0 = Gtk.Separator()
        sep0.add_css_class("neon-separator")
        box.append(sep0)
        
        # System info header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header_box.add_css_class("panel-header-box")
        
        info = Gtk.Label(label="Live machine state and operator controls", xalign=0)
        info.add_css_class("panel-description")
        header_box.append(info)
        box.append(header_box)
        
        stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        stats_box.add_css_class("stats-stack")
        box.append(stats_box)
        
        self.cpu_label, self.cpu_bar = self.create_stat_card(stats_box, "CPU Load", "Monitors active processor usage", "accent-green")
        self.mem_label, self.mem_bar = self.create_stat_card(stats_box, "Memory", "Tracks used system memory", "accent-blue")
        self.disk_label, self.disk_bar = self.create_stat_card(stats_box, "Disk", "Shows root filesystem utilization", "accent-amber")
        self.battery_label, self.battery_bar = self.create_stat_card(stats_box, "Battery", "Current battery charge and state", "accent-green")
        
        return frame
    
    def create_center_panel(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_hexpand(True)
        box.set_vexpand(True)
        box.add_css_class("center-panel")
        
        # Drawing area for animated logo
        logo_frame = Gtk.Frame()
        logo_frame.add_css_class("logo-frame")
        logo_frame.set_vexpand(True)
        
        self.logo_area = Gtk.DrawingArea()
        self.logo_area.set_hexpand(True)
        self.logo_area.set_vexpand(True)
        self.logo_area.set_draw_func(self.draw_logo)
        logo_frame.set_child(self.logo_area)
        box.append(logo_frame)

        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        log_box.add_css_class("panel-header-box")

        log_kicker = Gtk.Label(label="Mission stream", xalign=0)
        log_kicker.add_css_class("panel-kicker-center")
        log_box.append(log_kicker)

        log_header = Gtk.Label(label="Activity Log", xalign=0)
        log_header.add_css_class("section-header")
        log_box.append(log_header)
        box.append(log_box)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add_css_class("log-scroll")
        scroll.set_min_content_height(140)
        scroll.set_size_request(-1, 140)

        self.activity_view = Gtk.TextView()
        self.activity_view.set_editable(False)
        self.activity_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.activity_view.add_css_class("activity-log")
        scroll.set_child(self.activity_view)
        box.append(scroll)
        
        return box
    
    def create_right_panel(self):
        frame = Gtk.Frame()
        frame.add_css_class("panel-frame")
        frame.set_size_request(450, -1)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        frame.set_child(box)
        
        # Chat header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header_box.add_css_class("panel-header-box")
        
        box.append(header_box)

        # Chat area
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add_css_class("chat-scroll")
        
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.chat_box.set_margin_start(10)
        self.chat_box.set_margin_end(10)
        self.chat_box.set_margin_top(10)
        self.chat_box.set_margin_bottom(10)
        scroll.set_child(self.chat_box)
        box.append(scroll)
        
        # Image indicator
        self.image_label = Gtk.Label(label="", xalign=0)
        self.image_label.add_css_class("helper-label")
        box.append(self.image_label)

        self.helper_label = Gtk.Label(label="", xalign=0)
        self.helper_label.add_css_class("helper-label")
        box.append(self.helper_label)

        # Input row: [+] [entry] [➤]
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        plus_btn = Gtk.Button(label="+")
        plus_btn.add_css_class("btn-plus")
        plus_btn.connect("clicked", self.on_attach_image_clicked)
        input_row.append(plus_btn)

        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Message BenX...")
        self.input_entry.add_css_class("chat-input")
        self.input_entry.set_hexpand(True)
        self.input_entry.connect("activate", self.on_send_clicked)
        input_row.append(self.input_entry)

        send_btn = Gtk.Button(label="➤")
        send_btn.add_css_class("btn-send-arrow")
        send_btn.connect("clicked", self.on_send_clicked)
        input_row.append(send_btn)

        box.append(input_row)
        
        return frame

    def create_stat_card(self, parent, title, description, accent_class):
        """Create a metric card for the diagnostics panel."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("stat-card")
        card.add_css_class(accent_class)
        
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        title_label = Gtk.Label(label=title, xalign=0)
        title_label.add_css_class("stat-title")
        title_label.set_hexpand(True)
        top.append(title_label)
        
        value_label = Gtk.Label(label="0%", xalign=1)
        value_label.add_css_class("stat-value")
        top.append(value_label)
        card.append(top)
        
        desc_label = Gtk.Label(label=description, xalign=0)
        desc_label.add_css_class("stat-description")
        card.append(desc_label)
        
        bar = Gtk.ProgressBar()
        bar.set_fraction(0.0)
        bar.set_show_text(False)
        bar.add_css_class("metric-bar")
        card.append(bar)
        
        parent.append(card)
        return value_label, bar

    def create_window_dot_button(self, dot_class, callback):
        """Create a mac-like traffic-light dot button."""
        button = Gtk.Button()
        button.set_has_frame(False)
        button.add_css_class("window-dot-btn")
        button.connect("clicked", callback)

        dot = Gtk.Box()
        dot.add_css_class("window-dot")
        dot.add_css_class(dot_class)
        dot.set_size_request(12, 12)
        button.set_child(dot)
        return button

    def create_copy_button(self, css_class, message, tooltip="Copy"):
        """Create a styled copy button with a symbolic icon."""
        button = Gtk.Button()
        button.add_css_class(css_class)
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda w: self.copy_to_clipboard(message))

        icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
        icon.set_pixel_size(16)
        button.set_child(icon)
        return button

    def set_processing_state(self, active, summary=None):
        """Reflect command processing state in the UI."""
        self.processing = active
        if hasattr(self, "helper_label") and summary:
            self.helper_label.set_text(summary)
        if hasattr(self, "input_entry"):
            self.input_entry.set_sensitive(not active)

    def _build_css(self) -> bytes:
        """Return the full CSS stylesheet as bytes."""
        return b"""
            /* Main window */
            window {
                background: radial-gradient(circle at top left, rgba(12, 38, 27, 0.12) 0%, transparent 20%),
                            linear-gradient(180deg, #020405 0%, #000000 100%);
                color: #ebfff7;
            }
            
            /* Title */
            .title-huge {
                font-size: 44pt;
                font-weight: bold;
                color: #f4fff9;
                font-family: 'Orbitron', monospace;
                letter-spacing: 0.08em;
            }

            .topbar {
                background: linear-gradient(180deg, rgba(3, 8, 10, 0.98) 0%, rgba(2, 5, 6, 0.94) 100%);
                border: 1px solid rgba(82, 255, 173, 0.22);
                border-radius: 26px;
                padding: 8px 14px;
                box-shadow: 0 18px 44px rgba(0, 0, 0, 0.35);
            }

            .eyebrow-label {
                font-size: 10pt;
                color: #8eb5ac;
                font-family: 'Share Tech Mono', monospace;
                letter-spacing: 0.24em;
                text-transform: uppercase;
            }

            .subtitle-label {
                font-size: 11pt;
                color: rgba(235, 255, 247, 0.72);
                font-family: 'Rajdhani', sans-serif;
            }

            .window-controls {
                padding: 0;
                background: transparent;
                border: none;
                border-radius: 18px;
                margin-right: 12px;
            }
            
            /* Window controls */
            .window-dot-btn {
                background: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                outline: none;
                padding: 0;
                min-width: 0;
                min-height: 0;
            }

            .window-dot {
                border-radius: 999px;
                border: 1px solid rgba(0, 0, 0, 0.18);
                min-width: 12px;
                min-height: 12px;
            }

            .window-dot-btn:hover,
            .window-dot-btn:active,
            .window-dot-btn:focus,
            .window-dot-btn:focus-visible {
                background: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                outline: none;
            }

            .window-dot-red {
                background-color: #ed6a5e;
            }

            .window-dot-yellow {
                background-color: #f5bd4f;
            }

            .window-dot-green {
                background-color: #61c454;
            }

            .window-dot-btn:hover .window-dot-red {
                background-color: #ff857a;
            }

            .window-dot-btn:hover .window-dot-yellow {
                background-color: #ffd46b;
            }

            .window-dot-btn:hover .window-dot-green {
                background-color: #7ad86c;
            }
            
            /* Panels */
            .panel-frame {
                background: linear-gradient(180deg, rgba(3, 8, 10, 0.98) 0%, rgba(2, 5, 6, 0.94) 100%);
                border: 1px solid rgba(82, 255, 173, 0.16);
                border-radius: 28px;
                box-shadow: 0 18px 44px rgba(0, 0, 0, 0.3);
            }
            
            /* Section headers */
            .section-header {
                font-size: 18pt;
                font-weight: bold;
                color: #f3fff8;
                font-family: 'Orbitron', monospace;
                letter-spacing: 0.05em;
            }

            .panel-header-box,
            .time-card,
            .stats-stack,
            .center-panel {
                background: transparent;
            }

            .panel-kicker,
            .panel-kicker-center {
                font-size: 10pt;
                color: #8eb5ac;
                font-family: 'Share Tech Mono', monospace;
                letter-spacing: 0.22em;
                text-transform: uppercase;
            }

            .panel-kicker-center {
                /* justify-content: center; */
            }

            .section-header-small {
                font-size: 11pt;
                font-weight: bold;
                color: #dffef1;
                font-family: 'Share Tech Mono', monospace;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            .command-deck {
                background: rgba(1, 4, 5, 0.9);
                border: 1px solid rgba(82, 255, 173, 0.08);
                border-radius: 18px;
                padding: 12px;
            }
            
            /* Stats */
            .stat-card {
                background: linear-gradient(180deg, rgba(2, 6, 8, 0.96) 0%, rgba(1, 4, 5, 0.9) 100%);
                border: 1px solid rgba(82, 255, 173, 0.08);
                border-radius: 18px;
                padding: 14px 16px;
            }

            .stat-title {
                font-size: 10pt;
                color: #8eb5ac;
                font-family: 'Share Tech Mono', monospace;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            .stat-value {
                font-size: 14pt;
                font-weight: bold;
                color: #ebfff7;
                font-family: 'Orbitron', monospace;
            }

            .stat-description {
                font-size: 10pt;
                color: rgba(235, 255, 247, 0.58);
                font-family: 'Rajdhani', sans-serif;
                margin-bottom: 4px;
            }

            .metric-bar trough {
                min-height: 8px;
                background: rgba(255, 255, 255, 0.06);
                border-radius: 999px;
            }

            .metric-bar trough slider {
                min-height: 0;
                min-width: 0;
                background: transparent;
                border: none;
                padding: 0;
                -gtk-outline-radius: 0;
            }

            .metric-bar progress {
                min-height: 8px;
                border-radius: 999px;
                background: linear-gradient(90deg, rgba(96, 255, 185, 0.45) 0%, #60ffb9 100%);
            }

            .accent-blue .metric-bar progress {
                background: linear-gradient(90deg, rgba(97, 216, 255, 0.45) 0%, #61d8ff 100%);
            }

            .accent-amber .metric-bar progress {
                background: linear-gradient(90deg, rgba(255, 196, 94, 0.4) 0%, #ffc45e 100%);
            }

            .accent-green .metric-bar progress {
                background: linear-gradient(90deg, rgba(96, 255, 185, 0.45) 0%, #60ffb9 100%);
            }
            
            /* Time */
            .time-label {
                font-size: 20pt;
                font-weight: bold;
                color: #f3fff8;
                font-family: 'Orbitron', monospace;
            }

            .date-label {
                font-size: 11pt;
                color: #8eb5ac;
                font-family: 'Share Tech Mono', monospace;
            }
            
            /* Separators */
            .neon-separator {
                background-color: rgba(96, 255, 185, 0.28);
                min-height: 1px;
            }
            
            /* Activity log */
            .activity-log {
                background: rgba(1, 4, 5, 0.9);
                color: #d9fff1;
                font-family: 'Share Tech Mono', monospace;
                font-size: 9pt;
                padding: 12px;
            }

            .activity-log text,
            .activity-log textview,
            .activity-log border,
            .activity-log viewport,
            .activity-log > text {
                background-color: rgba(1, 4, 5, 0.9);
                background-image: none;
                color: #d9fff1;
            }

            .activity-log text {
                background-color: rgba(1, 4, 5, 0.9);
                color: #d9fff1;
            }
            
            .log-scroll {
                background: rgba(1, 4, 5, 0.9);
                border: 1px solid rgba(82, 255, 173, 0.08);
                border-radius: 18px;
            }
            
            /* Chat */
            .chat-scroll {
                background: rgba(1, 4, 5, 0.94);
                border: 1px solid rgba(82, 255, 173, 0.08);
                border-radius: 20px;
            }
            
            .chat-message {
                background: linear-gradient(180deg, rgba(3, 8, 10, 0.96) 0%, rgba(2, 5, 6, 0.92) 100%);
                border: 1px solid rgba(82, 255, 173, 0.08);
                border-radius: 18px;
                padding: 10px 12px;
            }

            .chat-message-user {
                border-color: rgba(96, 255, 185, 0.14);
                background: linear-gradient(180deg, rgba(6, 18, 14, 0.96) 0%, rgba(3, 9, 8, 0.92) 100%);
            }

            .chat-message-assistant {
                border-color: rgba(82, 255, 173, 0.08);
            }
            
            .chat-sender {
                font-weight: bold;
                font-family: 'Share Tech Mono', monospace;
                font-size: 10pt;
            }
            
            .chat-text {
                font-family: 'Rajdhani', sans-serif;
                font-size: 10pt;
                color: #e4f8f0;
                line-height: 1.4;
            }
            
            /* Input */
            .chat-input {
                background: linear-gradient(180deg, rgba(2, 6, 8, 0.96) 0%, rgba(1, 4, 5, 0.94) 100%);
                color: #ebfff7;
                border: 2px solid rgba(82, 255, 173, 0.22);
                border-radius: 16px;
                padding: 12px 14px;
                font-family: 'Rajdhani', sans-serif;
                font-size: 12pt;
            }
            
            .chat-input:focus {
                border-color: rgba(82, 255, 173, 0.4);
                box-shadow: 0 0 0 3px rgba(82, 255, 173, 0.06);
            }

            /* Input row buttons */
            .btn-plus {
                background: rgba(5, 7, 13, 0.9);
                color: #60ffb9;
                border: 2px solid rgba(82, 255, 173, 0.3);
                border-radius: 14px;
                font-size: 18pt;
                font-weight: bold;
                min-width: 42px;
                min-height: 42px;
                padding: 0;
            }
            .btn-plus:hover {
                background: rgba(10, 30, 20, 0.95);
                border-color: #60ffb9;
                box-shadow: 0 0 12px rgba(96, 255, 185, 0.3);
            }

            .btn-send-arrow {
                background: linear-gradient(135deg, rgba(61, 214, 160, 0.95) 0%, rgba(82, 255, 173, 0.92) 100%);
                color: #02100b;
                border: none;
                border-radius: 14px;
                font-size: 16pt;
                font-weight: bold;
                min-width: 42px;
                min-height: 42px;
                padding: 0;
            }
            .btn-send-arrow:hover {
                box-shadow: 0 0 18px rgba(96, 255, 185, 0.45);
            }

            .compact-btn-plus {
                background: rgba(0, 15, 0, 0.9);
                color: #00ff41;
                border: 2px solid rgba(0, 255, 65, 0.4);
                border-radius: 10px;
                font-size: 16pt;
                font-weight: bold;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
            }
            .compact-btn-plus:hover {
                border-color: #00ff41;
                box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
            }

            .compact-btn-arrow {
                background: linear-gradient(135deg, rgba(0, 40, 0, 0.95) 0%, rgba(0, 60, 0, 0.8) 100%);
                color: #00ff41;
                border: 2px solid rgba(0, 255, 65, 0.5);
                border-radius: 10px;
                font-size: 14pt;
                font-weight: bold;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
            }
            .compact-btn-arrow:hover {
                border-color: #00ff41;
                box-shadow: 0 0 14px rgba(0, 255, 65, 0.4);
            }

            .compact-btn-mic {
                background: rgba(0, 10, 20, 0.9);
                color: #00cfff;
                border: 2px solid rgba(0, 200, 255, 0.4);
                border-radius: 10px;
                font-size: 14pt;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
            }
            .compact-btn-mic:hover {
                border-color: #00cfff;
                box-shadow: 0 0 12px rgba(0, 200, 255, 0.4);
            }
            .compact-btn-mic-active {
                background: rgba(180, 0, 0, 0.85);
                border-color: #ff4444;
                box-shadow: 0 0 16px rgba(255, 0, 0, 0.6);
            }

            .compact-btn-sysaudio {
                background: rgba(10, 0, 20, 0.9);
                color: #cc88ff;
                border: 2px solid rgba(180, 100, 255, 0.4);
                border-radius: 10px;
                font-size: 14pt;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
            }
            .compact-btn-sysaudio:hover {
                border-color: #cc88ff;
                box-shadow: 0 0 12px rgba(180, 100, 255, 0.4);
            }
            .compact-btn-sysaudio-active {
                background: rgba(0, 60, 0, 0.9);
                border-color: #00ff41;
                box-shadow: 0 0 16px rgba(0, 255, 65, 0.5);
            }
            
            /* Copy button */
            .copy-btn {
                background: rgba(5, 7, 13, 0.9);
                color: #60ffb9;
                border: 1px solid rgba(82, 255, 173, 0.18);
                border-radius: 12px;
                padding: 0;
                min-width: 34px;
                min-height: 34px;
            }
            .copy-btn:hover {
                background: rgba(10, 20, 17, 0.92);
                border-color: #60ffb9;
                box-shadow: 0 4px 12px rgba(0, 255, 65, 0.22);
            }

            .helper-label {
                font-size: 10pt;
                color: rgba(235, 255, 247, 0.62);
                font-family: 'Rajdhani', sans-serif;
            }

            .logo-frame {
                background: linear-gradient(180deg, rgba(1, 3, 4, 0.98) 0%, rgba(0, 0, 0, 1) 100%);
                border: 1px solid rgba(82, 255, 173, 0.1);
                border-radius: 30px;
                padding: 8px;
            }
            
            /* ================================================
               COMPACT WINDOW  (cw-*)
               ================================================ */
            .cw-root {
                background: linear-gradient(160deg, #0d1117 0%, #0a0e14 100%);
                border: 1px solid rgba(99, 179, 237, 0.18);
                border-radius: 18px;
                box-shadow: 0 24px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(99,179,237,0.06);
            }

            .cw-titlebar {
                background: transparent;
                border-radius: 18px 18px 0 0;
            }

            .cw-title {
                font-size: 12pt;
                font-weight: bold;
                color: #e2e8f0;
                font-family: 'Orbitron', monospace;
                letter-spacing: 0.12em;
            }

            .cw-wake-btn {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 0;
                min-width: 26px;
                min-height: 26px;
            }
            .cw-wake-btn image { color: #4a5568; -gtk-icon-size: 14px; }
            .cw-wake-btn:hover { background: rgba(246,173,85,0.12); border-color: rgba(246,173,85,0.3); }
            .cw-wake-btn:hover image { color: #f6ad55; }
            .cw-wake-btn-active {
                background: rgba(246,173,85,0.15);
                border-color: rgba(246,173,85,0.5);
                box-shadow: 0 0 10px rgba(246,173,85,0.3);
            }
            .cw-wake-btn-active image { color: #f6ad55; }

            .cw-status {
                font-size: 9pt;
                font-family: 'Share Tech Mono', monospace;
                letter-spacing: 0.1em;
                min-width: 52px;
            }

            .cw-sep {
                background-color: rgba(99, 179, 237, 0.1);
                min-height: 1px;
                margin: 0 10px;
            }

            .cw-chat-scroll {
                background: transparent;
                border: none;
            }

            .cw-attach-label {
                font-size: 9pt;
                color: #68d391;
                font-family: 'Share Tech Mono', monospace;
                min-height: 0;
            }

            /* Input bar */
            .cw-input-bar {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(99,179,237,0.14);
                border-radius: 14px;
                padding: 4px 6px;
            }

            .cw-entry {
                background: transparent;
                color: #e2e8f0;
                border: none;
                box-shadow: none;
                font-family: 'Rajdhani', sans-serif;
                font-size: 11pt;
                padding: 6px 8px;
                min-height: 0;
            }
            .cw-entry:focus {
                box-shadow: none;
                border: none;
                outline: none;
            }

            /* Icon buttons */
            .cw-btn-icon {
                background: rgba(255,255,255,0.05);
                color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 0;
                min-width: 34px;
                min-height: 34px;
            }
            .cw-btn-icon image {
                color: #94a3b8;
                -gtk-icon-size: 16px;
            }
            .cw-btn-icon:hover {
                background: rgba(99,179,237,0.12);
                border-color: rgba(99,179,237,0.3);
            }
            .cw-btn-icon:hover image {
                color: #63b3ed;
            }

            /* Active state - mic recording / sysaudio on */
            .cw-btn-active {
                background: rgba(239,68,68,0.18);
                border-color: rgba(239,68,68,0.5);
                box-shadow: 0 0 10px rgba(239,68,68,0.25);
            }
            .cw-btn-active image {
                color: #fc8181;
            }

            /* Sysaudio active overrides to green */
            .cw-btn-sysaudio-on {
                background: rgba(72,187,120,0.18);
                border-color: rgba(72,187,120,0.5);
                box-shadow: 0 0 10px rgba(72,187,120,0.25);
            }
            .cw-btn-sysaudio-on image {
                color: #68d391;
            }

            /* Send button */
            .cw-btn-send {
                background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%);
                color: #fff;
                border: none;
                border-radius: 10px;
                padding: 0;
                min-width: 34px;
                min-height: 34px;
            }
            .cw-btn-send image {
                color: #fff;
                -gtk-icon-size: 16px;
            }
            .cw-btn-send:hover {
                background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
                box-shadow: 0 0 12px rgba(66,153,225,0.4);
            }

            /* Chat messages */
            .cw-msg-benx {
                background: rgba(49,130,206,0.1);
                border: 1px solid rgba(49,130,206,0.2);
                border-radius: 0 12px 12px 12px;
                padding: 8px 12px;
            }
            .cw-msg-user {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px 0 12px 12px;
                padding: 8px 12px;
            }
            .cw-msg-system {
                background: rgba(72,187,120,0.08);
                border: 1px solid rgba(72,187,120,0.2);
                border-radius: 12px;
                padding: 6px 10px;
            }
            .cw-sender-benx {
                font-size: 9pt;
                font-family: 'Share Tech Mono', monospace;
                color: #63b3ed;
                font-weight: bold;
            }
            .cw-sender-user {
                font-size: 9pt;
                font-family: 'Share Tech Mono', monospace;
                color: #a0aec0;
                font-weight: bold;
            }
            .cw-sender-system {
                font-size: 9pt;
                font-family: 'Share Tech Mono', monospace;
                color: #68d391;
                font-weight: bold;
            }
            .cw-msg-text {
                font-family: 'Rajdhani', sans-serif;
                font-size: 10pt;
                color: #e2e8f0;
                line-height: 1.5;
            }
            .cw-copy-btn {
                background: transparent;
                color: #4a5568;
                border: none;
                border-radius: 6px;
                padding: 0;
                min-width: 22px;
                min-height: 22px;
            }
            .cw-copy-btn:hover {
                color: #63b3ed;
                background: rgba(99,179,237,0.1);
            }
            
            /* Notification bar */
            .notification-bar {
                background-color: #1a1a1a;
                border-radius: 5px;
            }
            
            .notification-logo {
                font-size: 14pt;
                font-weight: bold;
                color: #00ff41;
                font-family: 'Orbitron', monospace;
            }
            
            .notification-text {
                font-size: 11pt;
                font-weight: bold;
                color: #ffffff;
                font-family: 'Arial', sans-serif;
            }
        """

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(self._build_css())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def draw_logo(self, area, cr, width, height):
        """Draw animated logo with decorative circles"""
        cx, cy = width / 2, height / 2
        
        # Clear background
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.paint()

        # Subtle radial glow
        radial = cairo_radial = None
        try:
            import cairo
            cairo_radial = cairo.RadialGradient(cx, cy, 10, cx, cy, min(width, height) * 0.42)
            cairo_radial.add_color_stop_rgba(0, 0.08, 0.42, 0.28, 0.08)
            cairo_radial.add_color_stop_rgba(0.45, 0.02, 0.10, 0.06, 0.04)
            cairo_radial.add_color_stop_rgba(1, 0.0, 0.0, 0.0, 0.0)
            cr.set_source(cairo_radial)
            cr.arc(cx, cy, min(width, height) * 0.42, 0, 2 * math.pi)
            cr.fill()
        except ImportError as e:
            logger.debug("cairo not available for radial gradient: %s", e)
        
        # Try to load and draw logo image
        try:
            logo_path = Path(__file__).parent.parent.parent / "benx.jpg"
            if logo_path.exists() and not hasattr(self, '_logo_pixbuf'):
                self._logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo_path), 300, 300, True
                )

            if hasattr(self, '_logo_pixbuf'):
                Gdk.cairo_set_source_pixbuf(
                    cr, self._logo_pixbuf,
                    cx - 150, cy - 150
                )
                cr.paint()
        except (GLib.Error, OSError, ValueError) as e:
            logger.debug("Failed loading or painting logo image, using text fallback: %s", e)
            cr.set_source_rgb(0, 1, 0.25)
            cr.select_font_face("Orbitron", 0, 1)
            cr.set_font_size(32)
            text = "BenX"
            extents = cr.text_extents(text)
            cr.move_to(cx - extents.width/2, cy + extents.height/2)
            cr.show_text(text)
        except Exception as e:
            logger.exception("Unexpected draw_logo error:")
            cr.set_source_rgb(0, 1, 0.25)
            cr.select_font_face("Orbitron", 0, 1)
            cr.set_font_size(32)
            text = "BenX"
            extents = cr.text_extents(text)
            cr.move_to(cx - extents.width/2, cy + extents.height/2)
            cr.show_text(text)
        
        # Draw animated circles
        cr.set_line_width(2)
        cr.set_source_rgba(0.38, 1.0, 0.73, 0.85)
        
        for i, radius in enumerate([180, 150]):
            segments = 24
            for seg in range(segments):
                angle = math.radians((self.rotation + seg * 15 + i * 10) % 360)
                arc_len = math.radians(10)
                
                x1 = cx + radius * math.cos(angle)
                y1 = cy + radius * math.sin(angle)
                x2 = cx + radius * math.cos(angle + arc_len)
                y2 = cy + radius * math.sin(angle + arc_len)
                
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()

        # Draw crosshair lines
        cr.set_source_rgba(0.38, 0.85, 1.0, 0.18)
        cr.set_line_width(1)
        cr.move_to(cx - 230, cy)
        cr.line_to(cx + 230, cy)
        cr.stroke()
        cr.move_to(cx, cy - 230)
        cr.line_to(cx, cy + 230)
        cr.stroke()
        
        # Corner decorations
        corner_size = 30
        corners = [(30, 30), (width-30, 30), (30, height-30), (width-30, height-30)]
        
        for x, y in corners:
            if x < width/2 and y < height/2:
                cr.move_to(x, y+corner_size)
                cr.line_to(x, y)
                cr.line_to(x+corner_size, y)
            elif x > width/2 and y < height/2:
                cr.move_to(x-corner_size, y)
                cr.line_to(x, y)
                cr.line_to(x, y+corner_size)
            elif x < width/2 and y > height/2:
                cr.move_to(x, y-corner_size)
                cr.line_to(x, y)
                cr.line_to(x+corner_size, y)
            else:
                cr.move_to(x-corner_size, y)
                cr.line_to(x, y)
                cr.line_to(x, y-corner_size)
            cr.stroke()
    
    def animate_logo(self):
        """Animate the logo"""
        self.rotation = (self.rotation + 2) % 360
        self.logo_area.queue_draw()
        return True
    
    def update_time(self):
        """Update time display"""
        now = datetime.now(tz=timezone.utc).astimezone()
        self.time_label.set_text(now.strftime("%H:%M:%S"))
        self.date_label.set_text(now.strftime("%b %d, %Y"))
        return True
    
    def update_stats(self):
        """Update system stats"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            self.cpu_label.set_text(f"{cpu:.0f}%")
            self.mem_label.set_text(f"{mem:.0f}%")
            self.disk_label.set_text(f"{disk:.0f}%")
            self.cpu_bar.set_fraction(max(0.0, min(cpu / 100.0, 1.0)))
            self.mem_bar.set_fraction(max(0.0, min(mem / 100.0, 1.0)))
            self.disk_bar.set_fraction(max(0.0, min(disk / 100.0, 1.0)))
            
            # Battery
            try:
                battery = psutil.sensors_battery()
                if battery:
                    status = "Charging" if battery.power_plugged else "Discharging"
                    self.battery_label.set_text(f"{battery.percent:.0f}% ({status})")
                    self.battery_bar.set_fraction(max(0.0, min(battery.percent / 100.0, 1.0)))
                    
                    # Log warnings
                    if battery.percent < 20 and not battery.power_plugged:
                        if not hasattr(self, '_battery_warned'):
                            self.log_activity("⚠️ Low battery")
                            self._battery_warned = True
                    else:
                        self._battery_warned = False
            except AttributeError as e:
                logger.debug("Battery sensor unavailable: %s", e)
            else:
                if not psutil.sensors_battery():
                    self.battery_label.set_text("N/A")
                    self.battery_bar.set_fraction(0.0)
            
            # CPU/Memory warnings
            if cpu > 90 and not hasattr(self, '_cpu_warned'):
                self.log_activity("⚠️ High CPU usage")
                self._cpu_warned = True
            elif cpu < 80:
                self._cpu_warned = False
                
            if mem > 90 and not hasattr(self, '_mem_warned'):
                self.log_activity("⚠️ Low memory")
                self._mem_warned = True
            elif mem < 80:
                self._mem_warned = False
            
        except ImportError as e:
            logger.exception("psutil not available for stats update: %s", e)
        
        return True
    
    def add_chat_message(self, sender, message):
        """Add message to chat"""
        timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S")
        
        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        msg_box.set_margin_start(10)
        msg_box.set_margin_end(10)
        msg_box.set_margin_top(5)
        msg_box.set_margin_bottom(5)
        msg_box.add_css_class("chat-message")
        msg_box.add_css_class("chat-message-assistant" if sender == "BenX" else "chat-message-user")
        
        # Sender with copy button for BenX messages
        sender_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        color = '#00ff41' if sender == 'BenX' else '#00ffff'
        sender_label = Gtk.Label(label=f"[{timestamp}] {sender}:", xalign=0)
        sender_label.add_css_class("chat-sender")
        sender_label.set_markup(f"<span foreground='{color}'><b>[{timestamp}] {sender}:</b></span>")
        sender_label.set_hexpand(True)
        sender_box.append(sender_label)
        
        # Add copy button for BenX messages
        if sender == 'BenX':
            copy_btn = self.create_copy_button("copy-btn", message, "Copy to clipboard")
            sender_box.append(copy_btn)
        
        msg_box.append(sender_box)
        
        # Message
        msg_label = Gtk.Label(label=f"  {message}", xalign=0, wrap=True)
        msg_label.add_css_class("chat-text")
        msg_label.set_max_width_chars(50)
        msg_label.set_selectable(True)  # Make text selectable
        msg_box.append(msg_label)
        
        self.chat_box.append(msg_box)
        
        # Store message in history for syncing
        self.message_history.append({'sender': sender, 'message': message, 'timestamp': timestamp})
        if sender == 'BenX':
            self.last_benx_message = message
        
        # Auto-scroll
        GLib.idle_add(self._scroll_chat_to_bottom)
        
        # Log activity
        if sender == 'You':
            self.log_activity(f"Command: {message[:40]}..." if len(message) > 40 else f"Command: {message}")
        elif sender == 'BenX' and '✅' in message:
            self.log_activity(f"Success: {message[:40]}..." if len(message) > 40 else f"Success: {message}")
        elif sender == 'BenX' and '❌' in message:
            self.log_activity(f"Error: {message[:40]}..." if len(message) > 40 else f"Error: {message}")
    
    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        try:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(text)
            self.log_activity(f"📋 Copied to clipboard: {text[:30]}...")
        except Exception as e:
            self.log_activity(f"❌ Copy failed: {str(e)}")
    
    def _scroll_chat_to_bottom(self):
        """Scroll chat to bottom"""
        adj = self.chat_box.get_parent().get_vadjustment()
        if adj:
            adj.set_value(adj.get_upper())
    
    def log_activity(self, activity):
        """Add activity to log"""
        timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {activity}"
        self.activity_entries.append(entry)
        
        # Keep only last 50 entries
        if len(self.activity_entries) > 50:
            self.activity_entries.pop(0)
        
        # Update log display
        buffer = self.activity_view.get_buffer()
        buffer.set_text('\n'.join(self.activity_entries))
        
        # Auto-scroll to bottom
        mark = buffer.get_insert()
        self.activity_view.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)
    
    def on_attach_image_clicked(self, widget):
        """Open file chooser to select an image"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Image")
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Images")
        for pat in ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.webp"]:
            filter_images.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_images)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_image_chosen)

    def _on_image_chosen(self, dialog, result):
        """Callback when image file is chosen"""
        try:
            file = dialog.open_finish(result)
            if file:
                raw_path = Path(file.get_path()).resolve()
                # Restrict to user home to prevent path traversal
                home = Path.home().resolve()
                if not str(raw_path).startswith(str(home)):
                    self.log_activity("❌ Image path outside home directory rejected")
                    return
                self.pending_image_path = str(raw_path)
                name = raw_path.name
                self.image_label.set_markup(f"<span foreground='#60ffb9'>📎 {name}</span>")
                if hasattr(self, 'compact_image_label'):
                    self.compact_image_label.set_markup(f"<span foreground='#60ffb9'>📎 {name}</span>")
                self.log_activity(f"📎 Image attached: {name}")
        except Exception as e:
            if "dismissed" not in str(e).lower():
                logger.exception("Image select failed: %s", e)
                self.log_activity(f"❌ Image select failed: {e}")

    def _clear_image(self):
        """Clear attached image state"""
        self.pending_image_path = None
        self.image_label.set_text("")
        if hasattr(self, 'compact_image_label'):
            self.compact_image_label.set_text("")

    def on_send_clicked(self, widget):
        """Handle send button click"""
        text = self.input_entry.get_text().strip()
        if not text and not self.pending_image_path:
            return
        if not text:
            text = "What is in this image?"
        if self.processing:
            self.log_activity("ℹ️ BenX is already processing a request")
            return
        
        image_path = self.pending_image_path
        self.input_entry.set_text("")
        self._clear_image()

        display_text = f"{text} [📎 image attached]" if image_path else text
        self.add_chat_message("You", display_text)
        self.log_activity(f"Processing: {text[:30]}...")
        self.set_processing_state(True, f"Running request: {text[:60]}")
        
        # Process in thread
        threading.Thread(target=self.process_command, args=(text, image_path), daemon=True).start()
    
    def show_confirmation_dialog(self, message: str) -> bool:
        """Show confirmation dialog and return user's choice"""
        import threading
        result = [False]  # Use list to allow modification in nested function
        event = threading.Event()
        
        def show_dialog():
            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading("Confirmation Required")
            dialog.set_body(message)
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("ok", "Install")
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("ok")
            dialog.set_close_response("cancel")
            
            def on_response(dialog, response):
                result[0] = (response == "ok")
                event.set()
            
            dialog.connect("response", on_response)
            dialog.present()
        
        GLib.idle_add(show_dialog)
        event.wait(timeout=30)  # Wait up to 30 seconds for user response
        return result[0]
    
    def _run_agent_or_fallback(self, text: str) -> str:
        """Run agentic loop or fall back to single command. Returns response string."""
        from jarvis_ai.executor import CommandExecutor

        def on_step(msg):
            GLib.idle_add(self.log_activity, msg)
            if msg.startswith(("💭", "🔧", "⚙️", "👁️")):
                GLib.idle_add(self._add_agent_step_message, msg)

        agent_result = self.ai_engine.agent_run(
            text,
            confirm_cb=self.show_confirmation_dialog,
            on_step_cb=on_step
        )
        if agent_result is not None:
            return agent_result

        json_cmd = self.ai_engine.interpret_command(
            text,
            conversation_context=self.ai_engine.conversation_history,
            learning_engine=self.ai_engine.learning_engine
        )
        result = CommandExecutor.execute(
            json_cmd, self.ai_engine, text,
            confirm_cb=self.show_confirmation_dialog
        )
        return self.ai_engine.chat(text) if result is None else result

    def process_command(self, text, image_path=None):
        """Process command - tries agentic loop first, falls back to single command"""
        try:
            if image_path:
                response = self.ai_engine.chat(text, image_path=image_path)
            else:
                response = self._run_agent_or_fallback(text)
            GLib.idle_add(self.add_chat_message, "BenX", response)
            GLib.idle_add(self.set_processing_state, False, "Ready.")
        except Exception as e:
            GLib.idle_add(self.add_chat_message, "BenX", f"Error: {str(e)}")
            GLib.idle_add(self.set_processing_state, False, "Request failed.")

    def _add_agent_step_message(self, msg: str):
        """Add a small agent step indicator in the chat"""
        step_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        step_box.set_margin_start(20)
        step_box.set_margin_end(10)
        step_box.set_margin_top(2)
        step_box.set_margin_bottom(2)

        label = Gtk.Label(label=msg[:100], xalign=0)
        label.set_markup(f"<span foreground='#4a7a6a' size='small'>{msg[:100]}</span>")
        label.set_wrap(True)
        step_box.append(label)
        self.chat_box.append(step_box)
        GLib.idle_add(self._scroll_chat_to_bottom)
    
    def on_clear_clicked(self, widget):
        """Clear chat"""
        while True:
            child = self.chat_box.get_first_child()
            if child is None:
                break
            self.chat_box.remove(child)
        self.add_chat_message("BenX", "Chat cleared")
        self.log_activity("Chat cleared")
    
    def on_compact_clicked(self, widget):
        """Toggle compact mode"""
        if self.window_mode == 'full':
            self.enter_compact_mode()
        else:
            self.enter_full_mode()
    
    def on_minimize_clicked(self, widget):
        """Minimize to notification bar"""
        self.previous_mode = self.window_mode
        self.window_mode = 'minimized'
        
        if hasattr(self, 'compact_win') and self.compact_win:
            self.compact_win.close()
            self.compact_win = None
        else:
            self.set_visible(False)
        
        self.create_notification_bar()
        self.log_activity("Minimized (click notification to restore)")
    
    def enter_compact_mode(self):
        """Enter compact mode - redesigned clean UI"""
        self.window_mode = 'compact'
        self.set_visible(False)

        if hasattr(self, 'notification_win') and self.notification_win:
            self.notification_win.close()
            self.notification_win = None
        if hasattr(self, 'compact_win') and self.compact_win:
            self.compact_win.close()
            self.compact_win = None

        self.compact_win = Gtk.Window()
        self.compact_win.set_title("BenX-Compact")
        self.compact_win.set_default_size(420, 560)
        self.compact_win.set_decorated(False)
        self.compact_win.set_deletable(False)
        self.compact_win.set_modal(False)
        self.compact_win.set_application(self.get_application())

        # Root
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("cw-root")
        self.compact_win.set_child(root)

        # ── Title bar (draggable) ──────────────────────────────────────────
        title_handle = Gtk.WindowHandle()
        root.append(title_handle)

        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_bar.add_css_class("cw-titlebar")
        title_bar.set_margin_start(14)
        title_bar.set_margin_end(14)
        title_bar.set_margin_top(10)
        title_bar.set_margin_bottom(10)
        title_handle.set_child(title_bar)

        drag_click = Gtk.GestureClick()
        drag_click.set_button(1)
        drag_click.connect("pressed", self.on_compact_titlebar_pressed)
        title_bar.add_controller(drag_click)

        # Traffic lights
        dots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dots_box.append(self.create_window_dot_button("window-dot-red",   lambda w: self.get_application().quit()))
        dots_box.append(self.create_window_dot_button("window-dot-yellow", self.on_minimize_clicked))
        dots_box.append(self.create_window_dot_button("window-dot-green",  lambda w: self.enter_full_mode()))
        title_bar.append(dots_box)

        title_lbl = Gtk.Label(label="BenX", xalign=0)
        title_lbl.add_css_class("cw-title")
        title_lbl.set_hexpand(True)
        title_bar.append(title_lbl)

        # Status pill (shows mic/sysaudio/wake state)
        self.cw_status_lbl = Gtk.Label(label="", xalign=1)
        self.cw_status_lbl.add_css_class("cw-status")
        title_bar.append(self.cw_status_lbl)

        # Wake word toggle button in title bar
        self.cw_wake_btn = Gtk.Button()
        wake_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-muted-symbolic")
        wake_icon.set_pixel_size(14)
        self.cw_wake_btn.set_child(wake_icon)
        self.cw_wake_btn.add_css_class("cw-wake-btn")
        self.cw_wake_btn.set_tooltip_text("Enable wake word: say 'BenX' to activate")
        self.cw_wake_btn.connect("clicked", self.on_wake_word_toggle)
        title_bar.append(self.cw_wake_btn)

        # ── Divider ───────────────────────────────────────────────────────
        sep = Gtk.Separator()
        sep.add_css_class("cw-sep")
        root.append(sep)

        # ── Chat scroll ───────────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add_css_class("cw-chat-scroll")
        scroll.set_margin_start(10)
        scroll.set_margin_end(10)
        scroll.set_margin_top(8)
        scroll.set_margin_bottom(4)
        root.append(scroll)

        self.compact_chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.compact_chat_box.set_margin_start(4)
        self.compact_chat_box.set_margin_end(4)
        self.compact_chat_box.set_margin_top(4)
        self.compact_chat_box.set_margin_bottom(4)
        scroll.set_child(self.compact_chat_box)
        self.sync_messages_to_compact()

        # ── Image attachment label ────────────────────────────────────────
        self.compact_image_label = Gtk.Label(label="", xalign=0)
        self.compact_image_label.add_css_class("cw-attach-label")
        self.compact_image_label.set_margin_start(14)
        self.compact_image_label.set_margin_end(14)
        root.append(self.compact_image_label)

        # ── Input bar ─────────────────────────────────────────────────────
        input_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_bar.add_css_class("cw-input-bar")
        input_bar.set_margin_start(10)
        input_bar.set_margin_end(10)
        input_bar.set_margin_top(4)
        input_bar.set_margin_bottom(10)
        root.append(input_bar)

        # + attach
        plus_btn = Gtk.Button()
        plus_btn.set_child(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        plus_btn.add_css_class("cw-btn-icon")
        plus_btn.set_tooltip_text("Attach image")
        plus_btn.connect("clicked", self.on_attach_image_clicked)
        input_bar.append(plus_btn)

        # Text entry
        self.compact_input = Gtk.Entry()
        self.compact_input.set_placeholder_text("Ask BenX...")
        self.compact_input.add_css_class("cw-entry")
        self.compact_input.set_hexpand(True)
        self.compact_input.connect("activate", self.on_compact_send)
        input_bar.append(self.compact_input)

        # mic button
        self.compact_mic_btn = Gtk.Button()
        self.compact_mic_btn.set_child(Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic"))
        self.compact_mic_btn.add_css_class("cw-btn-icon")
        self.compact_mic_btn.set_tooltip_text("Speak to BenX")
        self.compact_mic_btn.connect("clicked", self.on_compact_mic_clicked)
        input_bar.append(self.compact_mic_btn)

        # system audio button
        self.compact_sysaudio_btn = Gtk.Button()
        self.compact_sysaudio_btn.set_child(Gtk.Image.new_from_icon_name("audio-speakers-symbolic"))
        self.compact_sysaudio_btn.add_css_class("cw-btn-icon")
        self.compact_sysaudio_btn.set_tooltip_text("Listen to system audio / calls")
        self.compact_sysaudio_btn.connect("clicked", self.on_compact_sysaudio_clicked)
        input_bar.append(self.compact_sysaudio_btn)

        # send button
        send_btn = Gtk.Button()
        send_btn.set_child(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        send_btn.add_css_class("cw-btn-send")
        send_btn.set_tooltip_text("Send")
        send_btn.connect("clicked", self.on_compact_send)
        input_bar.append(send_btn)

        self.compact_win.present()
        GLib.idle_add(self._set_compact_above)
        self.log_activity("Entered compact mode")
    
    def _set_compact_above(self):
        """Set compact window to stay on top"""
        if hasattr(self, 'compact_win') and self.compact_win:
            surface = self.compact_win.get_surface()
            if surface:
                try:
                    surface.set_keep_above(True)
                except AttributeError as e:
                    logger.debug("set_keep_above not supported: %s", e)
        return False
    
    def enter_full_mode(self):
        """Return to full mode"""
        self.window_mode = 'full'
        # Stop system audio monitor if running
        if getattr(self, '_sysaudio_active', False):
            self._sysaudio_active = False
            self.voice_handler.stop_system_audio_monitor()
        # Stop wake word engine if running
        if hasattr(self, '_wake_engine') and self._wake_engine and self._wake_engine.is_active():
            self._wake_engine.stop()
        
        # Close compact window
        if hasattr(self, 'compact_win') and self.compact_win:
            self.compact_win.close()
            self.compact_win = None
        
        # Close notification if exists
        if hasattr(self, 'notification_win') and self.notification_win:
            self.notification_win.close()
            self.notification_win = None
        
        # Show main window
        self.set_visible(True)
        self.present()
        self.log_activity("Entered full mode")
    
    def on_compact_mic_clicked(self, widget):
        if getattr(self, '_compact_listening', False):
            return
        self._compact_listening = True
        self.compact_mic_btn.add_css_class("cw-btn-active")
        self.compact_input.set_placeholder_text("Listening...")
        self.compact_input.set_sensitive(False)
        if hasattr(self, 'cw_status_lbl'):
            self.cw_status_lbl.set_markup("<span foreground='#ff5555'>● REC</span>")
        threading.Thread(target=self._compact_voice_listen, daemon=True).start()

    def _compact_voice_listen(self):
        """Listen in background, fill input and auto-send"""
        try:
            text = self.voice_handler.listen()
        except Exception:
            text = None
        finally:
            GLib.idle_add(self._compact_voice_done, text)

    def _compact_voice_done(self, text: str):
        self._compact_listening = False
        self.compact_mic_btn.remove_css_class("cw-btn-active")
        self.compact_input.set_sensitive(True)
        self.compact_input.set_placeholder_text("Ask BenX...")
        if hasattr(self, 'cw_status_lbl'):
            self.cw_status_lbl.set_text("")
        if text:
            self.compact_input.set_text(text)
            self.log_activity(f"🎤 Voice: {text[:40]}")
            self.on_compact_send(None)
        else:
            self.log_activity("❌ Voice: nothing heard")
            self.add_compact_message("BenX", "❌ Couldn't hear anything. Try again.")

    def on_compact_sysaudio_clicked(self, widget):
        if getattr(self, '_sysaudio_active', False):
            self._sysaudio_active = False
            self.voice_handler.stop_system_audio_monitor()
            self.compact_sysaudio_btn.remove_css_class("cw-btn-sysaudio-on")
            if hasattr(self, 'cw_status_lbl'):
                self.cw_status_lbl.set_text("")
            self.log_activity("🔇 System audio monitor stopped")
            self.add_compact_message("BenX", "🔇 Stopped listening to system audio.")
        else:
            self._sysaudio_active = True
            self.compact_sysaudio_btn.add_css_class("cw-btn-sysaudio-on")
            if hasattr(self, 'cw_status_lbl'):
                self.cw_status_lbl.set_markup("<span foreground='#68d391'>● SYS</span>")
            self.log_activity("🔊 System audio monitor started")
            self.add_compact_message("BenX", "🔊 Listening to system audio. I'll respond to anything I hear from your speakers.")
            self.voice_handler.start_system_audio_monitor(
                on_speech_cb=self._on_system_audio_speech,
                chunk_duration=8
            )

    def on_wake_word_toggle(self, widget):
        """Toggle wake word engine on/off"""
        if not hasattr(self, '_wake_engine') or self._wake_engine is None:
            from jarvis_ai.wake_word_engine import WakeWordEngine
            self._wake_engine = WakeWordEngine(on_wake_word=self._on_wake_word_detected)

        if self._wake_engine.is_active():
            self._wake_engine.stop()
            # Reset button icon
            wake_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-muted-symbolic")
            wake_icon.set_pixel_size(14)
            self.cw_wake_btn.set_child(wake_icon)
            self.cw_wake_btn.remove_css_class("cw-wake-btn-active")
            if hasattr(self, 'cw_status_lbl'):
                self.cw_status_lbl.set_text("")
            self.add_compact_message("BenX", "Wake word disabled.")
            self.log_activity("Wake word disabled")
        else:
            result = self._wake_engine.start()
            if result.startswith("✅"):
                wake_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
                wake_icon.set_pixel_size(14)
                self.cw_wake_btn.set_child(wake_icon)
                self.cw_wake_btn.add_css_class("cw-wake-btn-active")
                if hasattr(self, 'cw_status_lbl'):
                    self.cw_status_lbl.set_markup("<span foreground='#f6ad55'>&#9679; WAKE</span>")
                self.add_compact_message("BenX", "Wake word active. Say 'BenX' to give a command.")
                self.log_activity("Wake word enabled")
            else:
                self.add_compact_message("BenX", result)

    def _on_wake_word_detected(self, command: str):
        """Called from wake word thread when 'BenX' is heard"""
        GLib.idle_add(self._handle_wake_command, command)

    def _handle_wake_command(self, command: str):
        """Handle wake word trigger on main thread"""
        self.log_activity(f"Wake word triggered: '{command[:40]}'")

        if not command:
            # No command heard — show listening indicator and wait
            self.add_compact_message("BenX", "I heard you! What can I do for you?")
            if hasattr(self, 'cw_status_lbl'):
                self.cw_status_lbl.set_markup("<span foreground='#fc8181'>&#9679; REC</span>")
            # Record one more chunk
            threading.Thread(target=self._wake_record_followup, daemon=True).start()
            return

        # Show what was heard
        self.add_compact_message("You", command)
        if hasattr(self, 'cw_status_lbl'):
            self.cw_status_lbl.set_markup("<span foreground='#f6ad55'>&#9679; WAKE</span>")
        # Process through BenX
        threading.Thread(
            target=self.process_compact_command,
            args=(command,),
            daemon=True
        ).start()

    def _wake_record_followup(self):
        """Record follow-up command after wake word with no inline command"""
        from jarvis_ai.wake_word_engine import _get_mic_source, _record_wav, _transcribe_groq
        import os
        source = _get_mic_source()
        if not source:
            return
        wav = _record_wav(source, 6)
        if not wav:
            return
        text = _transcribe_groq(wav)
        try:
            os.remove(wav)
        except OSError as e:
            logger.debug("Failed to remove temp wav file: %s", e)
        if text and text.strip():
            GLib.idle_add(self._handle_wake_command, text.strip())
        """Called when system audio speech is detected."""
        if not getattr(self, '_sysaudio_active', False):
            return
        GLib.idle_add(self._handle_system_audio_text, text)

    def _handle_system_audio_text(self, text: str):
        """Handle transcribed system audio on main thread."""
        self.log_activity(f"🔊 Heard: {text[:50]}")
        self.add_compact_message("🔊 System", text)
        # Process through BenX AI
        threading.Thread(
            target=self.process_compact_command,
            args=(f"I heard this from system audio: {text}",),
            daemon=True
        ).start()

    def on_compact_send(self, widget):
        """Send message from compact mode"""
        text = self.compact_input.get_text().strip()
        image_path = self.pending_image_path
        if not text and not image_path:
            return
        if not text:
            text = "What is in this image?"
        
        self.compact_input.set_text("")
        self._clear_image()

        display_text = f"{text} [📎 image attached]" if image_path else text
        self.add_chat_message("You", display_text)
        self.add_compact_message("You", display_text)
        
        # Process in thread
        threading.Thread(target=self.process_compact_command, args=(text, image_path), daemon=True).start()
    
    def add_compact_message(self, sender, message):
        """Add message to compact chat with new cw-* styling"""
        if not hasattr(self, 'compact_chat_box'):
            return
        timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M")

        is_benx   = sender == "BenX"
        is_system = sender.startswith("🔊")

        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        msg_box.set_margin_start(4 if is_benx or is_system else 20)
        msg_box.set_margin_end(20 if is_benx or is_system else 4)
        msg_box.set_margin_top(3)
        msg_box.set_margin_bottom(3)
        if is_system:
            msg_box.add_css_class("cw-msg-system")
        elif is_benx:
            msg_box.add_css_class("cw-msg-benx")
        else:
            msg_box.add_css_class("cw-msg-user")

        # Sender row
        sender_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        sender_lbl = Gtk.Label(label=f"{sender}  {timestamp}", xalign=0)
        if is_system:
            sender_lbl.add_css_class("cw-sender-system")
        elif is_benx:
            sender_lbl.add_css_class("cw-sender-benx")
        else:
            sender_lbl.add_css_class("cw-sender-user")
        sender_lbl.set_hexpand(True)
        sender_row.append(sender_lbl)

        if is_benx:
            copy_btn = Gtk.Button()
            copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
            copy_icon.set_pixel_size(12)
            copy_btn.set_child(copy_icon)
            copy_btn.add_css_class("cw-copy-btn")
            copy_btn.connect("clicked", lambda w: self.copy_to_clipboard(message))
            sender_row.append(copy_btn)

        msg_box.append(sender_row)

        text_lbl = Gtk.Label(label=message, xalign=0, wrap=True)
        text_lbl.add_css_class("cw-msg-text")
        text_lbl.set_max_width_chars(42)
        text_lbl.set_selectable(True)
        msg_box.append(text_lbl)

        self.compact_chat_box.append(msg_box)
        GLib.idle_add(self._scroll_compact_to_bottom)
    
    def _scroll_compact_to_bottom(self):
        """Scroll compact chat to bottom"""
        if hasattr(self, 'compact_chat_box'):
            adj = self.compact_chat_box.get_parent().get_vadjustment()
            if adj:
                adj.set_value(adj.get_upper())
    
    def sync_messages_to_compact(self):
        """Sync all messages from full chat to compact chat"""
        if not hasattr(self, 'compact_chat_box'):
            return
        
        # Clear existing compact messages
        while True:
            child = self.compact_chat_box.get_first_child()
            if child is None:
                break
            self.compact_chat_box.remove(child)
        
        # Add all messages from history
        for msg_data in self.message_history:
            self._add_compact_message_from_data(msg_data)
        
        # Auto-scroll to bottom
        GLib.idle_add(self._scroll_compact_to_bottom)
    
    def _add_compact_message_from_data(self, msg_data):
        """Add a message to compact chat from stored data"""
        if not hasattr(self, 'compact_chat_box'):
            return
        sender  = msg_data['sender']
        message = msg_data['message']
        timestamp = msg_data['timestamp'][:5]  # HH:MM

        is_benx = sender == "BenX"
        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        msg_box.set_margin_start(4 if is_benx else 20)
        msg_box.set_margin_end(20 if is_benx else 4)
        msg_box.set_margin_top(3)
        msg_box.set_margin_bottom(3)
        msg_box.add_css_class("cw-msg-benx" if is_benx else "cw-msg-user")

        sender_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        sender_lbl = Gtk.Label(label=f"{sender}  {timestamp}", xalign=0)
        sender_lbl.add_css_class("cw-sender-benx" if is_benx else "cw-sender-user")
        sender_lbl.set_hexpand(True)
        sender_row.append(sender_lbl)
        if is_benx:
            copy_btn = Gtk.Button()
            copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
            copy_icon.set_pixel_size(12)
            copy_btn.set_child(copy_icon)
            copy_btn.add_css_class("cw-copy-btn")
            copy_btn.connect("clicked", lambda w: self.copy_to_clipboard(message))
            sender_row.append(copy_btn)
        msg_box.append(sender_row)

        text_lbl = Gtk.Label(label=message, xalign=0, wrap=True)
        text_lbl.add_css_class("cw-msg-text")
        text_lbl.set_max_width_chars(42)
        text_lbl.set_selectable(True)
        msg_box.append(text_lbl)
        self.compact_chat_box.append(msg_box)
    
    def process_compact_command(self, text, image_path=None):
        """Process command from compact mode"""
        try:
            if image_path:
                response = self.ai_engine.chat(text, image_path=image_path)
            else:
                response = self._run_agent_or_fallback(text)
            GLib.idle_add(self.add_chat_message, "BenX", response)
            GLib.idle_add(self.add_compact_message, "BenX", response)
        except Exception as e:
            GLib.idle_add(self.add_chat_message, "BenX", f"Error: {str(e)}")
            GLib.idle_add(self.add_compact_message, "BenX", f"Error: {str(e)}")
    
    def create_notification_bar(self):
        """Create floating notification bar"""
        if hasattr(self, 'notification_win') and self.notification_win:
            self.notification_win.close()
        
        self.notification_win = Gtk.Window()
        self.notification_win.set_title("BenX-Notification")
        self.notification_win.set_default_size(150, 40)
        self.notification_win.set_decorated(False)
        self.notification_win.set_deletable(False)
        self.notification_win.set_modal(False)
        
        # Set window class for Hyprland rules
        self.notification_win.set_application(self.get_application())
        
        # Make it float on top
        surface = self.notification_win.get_surface()
        if surface:
            surface.set_keep_above(True)
        
        # Main frame
        frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        frame.add_css_class("notification-bar")
        frame.set_margin_start(6)
        frame.set_margin_end(6)
        frame.set_margin_top(6)
        frame.set_margin_bottom(6)
        self.notification_win.set_child(frame)
        
        # Logo/Icon
        try:
            logo_path = Path(__file__).parent.parent.parent / "benx.jpg"
            if logo_path.exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(logo_path), 28, 28, True)
                logo = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                logo = Gtk.Label(label="B")
                logo.add_css_class("notification-logo")
        except (OSError, Exception) as e:
            logger.debug("Notification logo load failed: %s", e)
            logo = Gtk.Label(label="B")
            logo.add_css_class("notification-logo")
        
        frame.append(logo)
        
        # Text
        text_label = Gtk.Label(label="BenX")
        text_label.add_css_class("notification-text")
        text_label.set_hexpand(True)
        frame.append(text_label)
        
        # Click to restore
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", lambda g, n, x, y: self.restore_window())
        self.notification_win.add_controller(gesture)
        
        self.notification_win.present()
        
        # Set keep above after window is realized
        GLib.idle_add(self._set_notification_above)
        
        self.log_activity("Notification bar created")
    
    def _set_notification_above(self):
        """Set notification window to stay on top"""
        if hasattr(self, 'notification_win') and self.notification_win:
            surface = self.notification_win.get_surface()
            if surface:
                try:
                    surface.set_keep_above(True)
                except AttributeError as e:
                    logger.debug("set_keep_above not supported: %s", e)
        return False

    def on_compact_titlebar_pressed(self, gesture, n_press, x, y):
        """Begin native window dragging for the compact window"""
        if not hasattr(self, 'compact_win') or not self.compact_win:
            return

        surface = self.compact_win.get_surface()
        device = gesture.get_current_event_device()
        button = gesture.get_current_button()
        timestamp = gesture.get_current_event_time()

        if not surface or not device or not button:
            return

        try:
            surface.begin_move(device, button, x, y, timestamp)
        except AttributeError as e:
            logger.debug("begin_move not supported on this surface: %s", e)

    def restore_window(self):
        """Restore window from minimized state"""
        if hasattr(self, 'notification_win') and self.notification_win:
            self.notification_win.close()
            self.notification_win = None
        
        # Restore to previous mode
        previous = getattr(self, 'previous_mode', 'full')
        
        if previous == 'compact':
            self.enter_compact_mode()
        else:
            self.window_mode = 'full'
            self.set_visible(True)
            self.present()
        
        self.log_activity(f"Restored to {previous} mode")


class BeautifulBenXGTK4App(Adw.Application):
    def __init__(self, jarvis_instance):
        super().__init__(application_id='com.benx.beautiful')
        self.jarvis = jarvis_instance
        self.window = None
    
    def do_activate(self):
        if not self.window:
            self.window = BeautifulBenXGTK4(self.jarvis, application=self)
        self.window.present()
    
    def run_app(self):
        self.run(None)


def create_beautiful_gtk4_ui(jarvis_instance):
    """Create and run beautiful GTK4 UI"""
    app = BeautifulBenXGTK4App(jarvis_instance)
    return app
