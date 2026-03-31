"""
BenX GTK4 UI - Native Wayland support with screen recording exclusion
"""
import sys

# CRITICAL: Prevent any GTK3 imports
if 'gi.repository.Gtk' in sys.modules:
    raise RuntimeError("GTK already loaded. Cannot load GTK4. Please restart.")

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

GTK_AVAILABLE = True


class BenXGTK4(Adw.ApplicationWindow):
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
        self.compact_win = None
        self.notification_win = None
        
        self.setup_gui()
    
    def setup_gui(self):
        self.set_title("BenX AI Assistant")
        self.set_default_size(1400, 800)
        
        # Get native surface and set layer to top
        surface = self.get_surface()
        if surface:
            from gi.repository import Gdk
            surface.set_keep_above(True)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="BenX", css_classes=["title"]))
        
        # Window control buttons
        compact_btn = Gtk.Button(label="□")
        compact_btn.connect("clicked", self.on_compact_clicked)
        header.pack_end(compact_btn)
        
        minimize_btn = Gtk.Button(label="─")
        minimize_btn.connect("clicked", self.on_minimize_clicked)
        header.pack_end(minimize_btn)
        
        main_box.append(header)
        
        # Content area with 3 panels
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)
        main_box.append(content_box)
        
        # LEFT PANEL - System Info
        left_panel = self.create_left_panel()
        content_box.append(left_panel)
        
        # CENTER PANEL - Logo
        center_panel = self.create_center_panel()
        content_box.append(center_panel)
        
        # RIGHT PANEL - Chat
        right_panel = self.create_right_panel()
        content_box.append(right_panel)
        
        # Apply CSS
        self.apply_css()
        
        # Start updates
        GLib.timeout_add_seconds(1, self.update_time)
        GLib.timeout_add_seconds(2, self.update_stats)
        
        self.add_chat_message("BenX", "Hello! I'm BenX, your AI assistant. How can I help you?")
    
    def create_left_panel(self):
        frame = Gtk.Frame()
        frame.set_size_request(350, -1)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        frame.set_child(box)
        
        # System info labels
        box.append(Gtk.Label(label="◢ SYSTEM INFO", css_classes=["heading"]))
        
        self.cpu_label = Gtk.Label(label="CPU: 0%", xalign=0)
        box.append(self.cpu_label)
        
        self.mem_label = Gtk.Label(label="Memory: 0%", xalign=0)
        box.append(self.mem_label)
        
        self.disk_label = Gtk.Label(label="Disk: 0%", xalign=0)
        box.append(self.disk_label)
        
        self.battery_label = Gtk.Label(label="Battery: N/A", xalign=0)
        box.append(self.battery_label)
        
        box.append(Gtk.Separator())
        
        self.time_label = Gtk.Label(label="", css_classes=["time"])
        box.append(self.time_label)
        
        box.append(Gtk.Separator())
        
        # Activity log
        box.append(Gtk.Label(label="◢ ACTIVITY LOG", css_classes=["heading"]))
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.activity_view = Gtk.TextView()
        self.activity_view.set_editable(False)
        self.activity_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll.set_child(self.activity_view)
        box.append(scroll)
        
        return frame
    
    def create_center_panel(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_hexpand(True)
        box.set_vexpand(True)
        
        label = Gtk.Label(label="BenX", css_classes=["logo"])
        box.append(label)
        
        return box
    
    def create_right_panel(self):
        frame = Gtk.Frame()
        frame.set_size_request(450, -1)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        frame.set_child(box)
        
        box.append(Gtk.Label(label="◢ CHAT", css_classes=["heading"]))
        
        # Chat area
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.set_child(self.chat_box)
        box.append(scroll)
        
        # Input
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Type your message...")
        self.input_entry.connect("activate", self.on_send_clicked)
        box.append(self.input_entry)
        
        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        send_btn = Gtk.Button(label="SEND")
        send_btn.connect("clicked", self.on_send_clicked)
        btn_box.append(send_btn)
        
        voice_btn = Gtk.Button(label="VOICE")
        voice_btn.connect("clicked", self.on_voice_clicked)
        btn_box.append(voice_btn)
        
        clear_btn = Gtk.Button(label="CLEAR")
        clear_btn.connect("clicked", self.on_clear_clicked)
        btn_box.append(clear_btn)
        
        box.append(btn_box)
        
        return frame
    
    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: #000000;
                color: #00ff41;
            }
            .heading {
                font-weight: bold;
                font-size: 14pt;
                color: #00ff41;
            }
            .time {
                font-size: 16pt;
                font-weight: bold;
                color: #00ff41;
            }
            .logo {
                font-size: 48pt;
                font-weight: bold;
                color: #00ff41;
            }
            frame {
                background-color: #001a00;
                border: 2px solid #00ff41;
            }
            entry {
                background-color: #000a00;
                color: #00ff41;
                border: 1px solid #00ff41;
            }
            button {
                background-color: #000000;
                color: #00ff41;
                border: 2px solid #00ff41;
                padding: 8px 20px;
            }
            button:hover {
                background-color: #001a00;
            }
            textview {
                background-color: #000a00;
                color: #00ff41;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def add_chat_message(self, sender, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        msg_box.set_margin_start(10)
        msg_box.set_margin_end(10)
        msg_box.set_margin_top(5)
        msg_box.set_margin_bottom(5)
        
        header = Gtk.Label(label=f"[{timestamp}] {sender}:", xalign=0)
        header.set_markup(f"<b>[{timestamp}] {sender}:</b>")
        msg_box.append(header)
        
        content = Gtk.Label(label=f"  {message}", xalign=0, wrap=True)
        content.set_max_width_chars(50)
        msg_box.append(content)
        
        self.chat_box.append(msg_box)
    
    def log_activity(self, activity):
        timestamp = datetime.now().strftime("%H:%M:%S")
        buffer = self.activity_view.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, f"[{timestamp}] {activity}\n")
    
    def update_time(self):
        self.time_label.set_text(datetime.now().strftime("%H:%M:%S"))
        return True
    
    def update_stats(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            self.cpu_label.set_text(f"CPU: {cpu:.0f}%")
            self.mem_label.set_text(f"Memory: {mem:.0f}%")
            self.disk_label.set_text(f"Disk: {disk:.0f}%")
            
            try:
                battery = psutil.sensors_battery()
                if battery:
                    status = "Charging" if battery.power_plugged else "Discharging"
                    self.battery_label.set_text(f"Battery: {battery.percent:.0f}% ({status})")
            except Exception:
                pass
        except Exception:
            pass
        return True
    
    def on_send_clicked(self, widget):
        text = self.input_entry.get_text().strip()
        if not text:
            return
        
        self.input_entry.set_text("")
        self.add_chat_message("You", text)
        self.log_activity(f"Command: {text}")
        
        # Process in thread
        threading.Thread(target=self.process_command, args=(text,), daemon=True).start()
    
    def process_command(self, text):
        try:
            from jarvis_ai.executor import CommandExecutor
            
            json_cmd = self.ai_engine.interpret_command(text, conversation_context=self.ai_engine.conversation_history, learning_engine=self.ai_engine.learning_engine)
            result = CommandExecutor.execute(json_cmd, self.ai_engine, text)
            
            if result is None:
                response = self.ai_engine.chat(text)
            else:
                response = result
            
            GLib.idle_add(self.add_chat_message, "BenX", response)
        except Exception as e:
            GLib.idle_add(self.add_chat_message, "BenX", f"Error: {str(e)}")
    
    def on_voice_clicked(self, widget):
        self.log_activity("🎤 Voice input activated")
        threading.Thread(target=self.voice_input, daemon=True).start()
    
    def voice_input(self):
        text = self.voice_handler.listen()
        if text:
            GLib.idle_add(self.input_entry.set_text, text)
            GLib.idle_add(self.on_send_clicked, None)
    
    def on_clear_clicked(self, widget):
        while True:
            child = self.chat_box.get_first_child()
            if child is None:
                break
            self.chat_box.remove(child)
        self.add_chat_message("BenX", "Chat cleared")
    
    def on_compact_clicked(self, widget):
        if self.window_mode == 'full':
            self.enter_compact_mode()
        else:
            self.enter_full_mode()
    
    def enter_compact_mode(self):
        self.window_mode = 'compact'
        self.set_visible(False)
        
        # Create compact window
        self.compact_win = Gtk.Window()
        self.compact_win.set_title("BenX-Compact")
        self.compact_win.set_default_size(400, 500)
        self.compact_win.set_decorated(False)
        
        surface = self.compact_win.get_surface()
        if surface:
            surface.set_keep_above(True)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        self.compact_win.set_child(box)
        
        # Title bar
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_box.append(Gtk.Label(label="BenX Chat"))
        
        expand_btn = Gtk.Button(label="▢")
        expand_btn.connect("clicked", lambda w: self.enter_full_mode())
        title_box.append(expand_btn)
        
        minimize_btn = Gtk.Button(label="─")
        minimize_btn.connect("clicked", self.on_minimize_clicked)
        title_box.append(minimize_btn)
        
        box.append(title_box)
        
        # Chat
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.compact_chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.set_child(self.compact_chat_box)
        box.append(scroll)
        
        # Input
        self.compact_input = Gtk.Entry()
        self.compact_input.connect("activate", self.on_compact_send)
        box.append(self.compact_input)
        
        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        send_btn = Gtk.Button(label="SEND")
        send_btn.connect("clicked", self.on_compact_send)
        btn_box.append(send_btn)
        box.append(btn_box)
        
        self.compact_win.present()
        self.log_activity("Entered compact mode")
    
    def enter_full_mode(self):
        self.window_mode = 'full'
        if self.compact_win:
            self.compact_win.close()
            self.compact_win = None
        self.set_visible(True)
        self.present()
        self.log_activity("Entered full mode")
    
    def on_compact_send(self, widget):
        text = self.compact_input.get_text().strip()
        if not text:
            return
        self.compact_input.set_text("")
        # Add to both chats
        self.add_chat_message("You", text)
        threading.Thread(target=self.process_command, args=(text,), daemon=True).start()
    
    def on_minimize_clicked(self, widget):
        self.previous_mode = self.window_mode
        self.window_mode = 'minimized'
        
        if self.compact_win:
            self.compact_win.set_visible(False)
        else:
            self.set_visible(False)
        
        self.create_notification_bar()
        self.log_activity("Minimized")
    
    def create_notification_bar(self):
        self.notification_win = Gtk.Window()
        self.notification_win.set_title("BenX-Notification")
        self.notification_win.set_default_size(150, 40)
        self.notification_win.set_decorated(False)
        
        surface = self.notification_win.get_surface()
        if surface:
            surface.set_keep_above(True)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        box.append(Gtk.Label(label="BenX"))
        
        # Click to restore
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", lambda g, n, x, y: self.restore_window())
        self.notification_win.add_controller(gesture)
        
        self.notification_win.set_child(box)
        self.notification_win.present()
    
    def restore_window(self):
        if self.notification_win:
            self.notification_win.close()
            self.notification_win = None
        
        if self.previous_mode == 'compact':
            self.enter_compact_mode()
        else:
            self.window_mode = 'full'
            self.set_visible(True)
            self.present()
        
        self.log_activity("Restored")


class BenXGTK4App(Adw.Application):
    def __init__(self, jarvis_instance):
        super().__init__(application_id='com.benx.assistant')
        self.jarvis = jarvis_instance
        self.window = None
    
    def do_activate(self):
        if not self.window:
            self.window = BenXGTK4(self.jarvis, application=self)
        self.window.present()
    
    def run_app(self):
        self.run(None)


def create_gtk4_ui(jarvis_instance):
    """Create and run GTK4 UI"""
    app = BenXGTK4App(jarvis_instance)
    return app
