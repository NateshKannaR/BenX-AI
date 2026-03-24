"""
BenX UI - Clean 3-panel layout
"""
import threading
import logging
import math
import random
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import Canvas
    GUI_AVAILABLE = True
    try:
        import pystray
        from PIL import Image, ImageDraw
        TRAY_AVAILABLE = True
    except ImportError:
        TRAY_AVAILABLE = False
except ImportError:
    GUI_AVAILABLE = False
    TRAY_AVAILABLE = False


class BenXUI:
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.voice_handler import VoiceHandler
        from jarvis_ai.config import Config
        
        self.ai_engine = AIEngine()
        self.voice_handler = VoiceHandler()
        self.config = Config
        self.root = None
        self.processing = False
        self.rotation = 0
        self.cpu = 0
        self.mem = 0
        self.restore_win = None
        self.window_mode = 'full'  # full, compact, minimized
        self.setup_gui()
    
    def setup_gui(self):
        if not GUI_AVAILABLE:
            return
        
        self.root = tk.Tk()
        self.root.title("BenX AI Assistant")
        self.root.configure(bg='#000000')
        
        width, height = 1400, 800
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Main container
        main = tk.Frame(self.root, bg='#000000')
        main.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top: BenX Title with minimize button
        title_frame = tk.Frame(main, bg='#000000', height=80)
        title_frame.pack(fill='x', pady=(0, 20))
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="BenX",
            font=('Orbitron', 48, 'bold'),
            fg='#00ff41',
            bg='#000000'
        ).pack(side='left', expand=True)
        
        tk.Button(
            title_frame,
            text="□",
            command=self.toggle_compact_mode,
            font=('Courier New', 20, 'bold'),
            bg='#000000',
            fg='#00ffff',
            activebackground='#001a00',
            activeforeground='#00ffff',
            relief='flat',
            bd=0,
            padx=15,
            pady=0,
            cursor='hand2'
        ).pack(side='right', padx=(5, 5))
        
        tk.Button(
            title_frame,
            text="─",
            command=self.minimize_window,
            font=('Courier New', 20, 'bold'),
            bg='#000000',
            fg='#00ff41',
            activebackground='#001a00',
            activeforeground='#00ff41',
            relief='flat',
            bd=0,
            padx=15,
            pady=0,
            cursor='hand2'
        ).pack(side='right', padx=(5, 10))
        
        tk.Button(
            title_frame,
            text="×",
            command=self.on_closing,
            font=('Courier New', 20, 'bold'),
            bg='#000000',
            fg='#ff0066',
            activebackground='#001a00',
            activeforeground='#ff0066',
            relief='flat',
            bd=0,
            padx=15,
            pady=0,
            cursor='hand2'
        ).pack(side='right', padx=5)
        
        # Content: 3 panels
        content = tk.Frame(main, bg='#000000')
        content.pack(fill='both', expand=True)
        
        # LEFT PANEL - System Info
        left = tk.Frame(content, bg='#001a00', width=350, bd=2, relief='solid')
        left.pack(side='left', fill='both', padx=(0, 10))
        left.pack_propagate(False)
        
        tk.Label(left, text="◢ SYSTEM INFO", font=('Courier New', 14, 'bold'), fg='#00ff41', bg='#001a00').pack(pady=10)
        
        self.cpu_label = tk.Label(left, text="CPU: 0%", font=('Courier New', 12), fg='#00ff41', bg='#001a00', anchor='w')
        self.cpu_label.pack(fill='x', padx=20, pady=5)
        
        self.mem_label = tk.Label(left, text="Memory: 0%", font=('Courier New', 12), fg='#00ff41', bg='#001a00', anchor='w')
        self.mem_label.pack(fill='x', padx=20, pady=5)
        
        self.disk_label = tk.Label(left, text="Disk: 0%", font=('Courier New', 12), fg='#00ff41', bg='#001a00', anchor='w')
        self.disk_label.pack(fill='x', padx=20, pady=5)
        
        self.battery_label = tk.Label(left, text="Battery: N/A", font=('Courier New', 12), fg='#00ff41', bg='#001a00', anchor='w')
        self.battery_label.pack(fill='x', padx=20, pady=5)
        
        tk.Frame(left, bg='#00ff41', height=2).pack(fill='x', padx=20, pady=10)
        
        self.time_label = tk.Label(left, text="", font=('Courier New', 16, 'bold'), fg='#00ff41', bg='#001a00')
        self.time_label.pack(pady=10)
        
        # Activity Log Section
        tk.Frame(left, bg='#00ff41', height=2).pack(fill='x', padx=20, pady=10)
        tk.Label(left, text="◢ ACTIVITY LOG", font=('Courier New', 12, 'bold'), fg='#00ff41', bg='#001a00').pack(pady=5)
        
        log_frame = tk.Frame(left, bg='#000a00', highlightthickness=0)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        log_scroll = tk.Scrollbar(log_frame, bg='#001a00', troughcolor='#000a00', highlightthickness=0)
        log_scroll.pack(side='right', fill='y')
        
        self.activity_log = tk.Text(log_frame, font=('Courier New', 9), bg='#000a00', fg='#00ff41', height=8, wrap='word', yscrollcommand=log_scroll.set, relief='flat', state='disabled', highlightthickness=0, borderwidth=0)
        self.activity_log.pack(fill='both', expand=True)
        log_scroll.config(command=self.activity_log.yview)
        
        self.activity_entries = []
        
        # CENTER PANEL - BenX Logo
        center = tk.Frame(content, bg='#000000')
        center.pack(side='left', fill='both', expand=True, padx=10)
        
        self.logo_canvas = Canvas(center, bg='#000000', highlightthickness=0)
        self.logo_canvas.pack(fill='both', expand=True)
        
        # RIGHT PANEL - Chat
        right = tk.Frame(content, bg='#001a00', width=450, bd=2, relief='solid')
        right.pack(side='right', fill='both', padx=(10, 0))
        right.pack_propagate(False)
        
        tk.Label(right, text="◢ CHAT", font=('Courier New', 14, 'bold'), fg='#00ff41', bg='#001a00').pack(pady=10)
        
        chat_frame = tk.Frame(right, bg='#000a00', bd=1, relief='solid')
        chat_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.chat_canvas = Canvas(chat_frame, bg='#000a00', highlightthickness=0)
        self.chat_canvas.pack(side='left', fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(chat_frame, command=self.chat_canvas.yview, bg='#001a00')
        scrollbar.pack(side='right', fill='y')
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.chat_inner = tk.Frame(self.chat_canvas, bg='#000a00')
        self.chat_canvas.create_window((0, 0), window=self.chat_inner, anchor='nw')
        self.chat_inner.bind('<Configure>', lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox('all')))
        
        # Input
        input_frame = tk.Frame(right, bg='#001a00', bd=2, relief='solid')
        input_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.input_entry = tk.Entry(input_frame, font=('Courier New', 12), bg='#000a00', fg='#00ff41', insertbackground='#00ff41', relief='flat', bd=10)
        self.input_entry.pack(fill='x')
        self.input_entry.bind('<Return>', lambda e: self.process_input())
        self.input_entry.focus()
        
        # Buttons
        btn_frame = tk.Frame(right, bg='#001a00')
        btn_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Button(btn_frame, text="SEND", command=self.process_input, font=('Courier New', 11, 'bold'), bg='#000000', fg='#00ff41', activebackground='#001a00', activeforeground='#00ff41', relief='solid', bd=2, padx=20, pady=8).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="VOICE", command=self.voice_input, font=('Courier New', 11, 'bold'), bg='#000000', fg='#00ffff', activebackground='#001a00', activeforeground='#00ffff', relief='solid', bd=2, padx=20, pady=8).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="CLEAR", command=self.clear_chat, font=('Courier New', 11, 'bold'), bg='#000000', fg='#ff0066', activebackground='#001a00', activeforeground='#ff0066', relief='solid', bd=2, padx=20, pady=8).pack(side='left', padx=5)
        
        self.animate_logo()
        self.update_time()
        self.update_stats()
        
        self.add_message("BenX", "Hello! I'm BenX, your AI assistant. How can I help you?")
        self.log_activity("✅ BenX started")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def animate_logo(self):
        if not self.root:
            return
        
        self.logo_canvas.delete('all')
        w = int(self.logo_canvas.winfo_width()) or 500
        h = int(self.logo_canvas.winfo_height()) or 600
        cx, cy = w // 2, h // 2
        
        self.rotation = (self.rotation + 2) % 360
        
        # Load and display BenX logo image
        try:
            from PIL import Image, ImageTk
            from pathlib import Path
            
            if not hasattr(self, 'logo_image'):
                logo_path = Path(__file__).parent.parent.parent / "benx.jpg"
                if logo_path.exists():
                    img = Image.open(logo_path)
                    img.thumbnail((300, 300))
                    self.logo_image = ImageTk.PhotoImage(img)
                else:
                    self.logo_image = None
            
            if hasattr(self, 'logo_image') and self.logo_image:
                self.logo_canvas.create_image(cx, cy, image=self.logo_image)
            else:
                self.logo_canvas.create_text(cx, cy, text="BenX", fill='#00ff41', font=('Orbitron', 32, 'bold'))
        except Exception as e:
            self.logo_canvas.create_text(cx, cy, text="BenX", fill='#00ff41', font=('Orbitron', 32, 'bold'))
        
        # Decorative circles around logo (inner ring removed)
        for i, radius in enumerate([180, 150]):
            segments = 24
            for seg in range(segments):
                angle = math.radians((self.rotation + seg * 15 + i * 10) % 360)
                arc_len = math.radians(10)
                
                x1 = cx + radius * math.cos(angle)
                y1 = cy + radius * math.sin(angle)
                x2 = cx + radius * math.cos(angle + arc_len)
                y2 = cy + radius * math.sin(angle + arc_len)
                
                self.logo_canvas.create_line(x1, y1, x2, y2, fill='#00ff41', width=2)
        
        # Corner decorations
        corner_size = 30
        for x, y in [(30, 30), (w-30, 30), (30, h-30), (w-30, h-30)]:
            if x < w/2 and y < h/2:
                self.logo_canvas.create_line(x, y+corner_size, x, y, x+corner_size, y, fill='#00ff41', width=2)
            elif x > w/2 and y < h/2:
                self.logo_canvas.create_line(x-corner_size, y, x, y, x, y+corner_size, fill='#00ff41', width=2)
            elif x < w/2 and y > h/2:
                self.logo_canvas.create_line(x, y-corner_size, x, y, x+corner_size, y, fill='#00ff41', width=2)
            else:
                self.logo_canvas.create_line(x-corner_size, y, x, y, x, y-corner_size, fill='#00ff41', width=2)
        
        self.root.after(50, self.animate_logo)
    
    def update_time(self):
        if not self.root:
            return
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_time)
    
    def update_stats(self):
        try:
            import psutil
            self.cpu = psutil.cpu_percent(interval=0.1)
            self.mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            self.cpu_label.config(text=f"CPU: {self.cpu:.0f}%")
            self.mem_label.config(text=f"Memory: {self.mem:.0f}%")
            self.disk_label.config(text=f"Disk: {disk:.0f}%")
            
            # Log warnings
            if self.cpu > 90 and not hasattr(self, '_cpu_warned'):
                self.log_activity("⚠️ High CPU usage")
                self._cpu_warned = True
            elif self.cpu < 80:
                self._cpu_warned = False
                
            if self.mem > 90 and not hasattr(self, '_mem_warned'):
                self.log_activity("⚠️ Low memory")
                self._mem_warned = True
            elif self.mem < 80:
                self._mem_warned = False
            
            try:
                battery = psutil.sensors_battery()
                if battery:
                    status = "Charging" if battery.power_plugged else "Discharging"
                    self.battery_label.config(text=f"Battery: {battery.percent:.0f}% ({status})")
                    
                    # Log battery warnings
                    if battery.percent < 20 and not battery.power_plugged and not hasattr(self, '_battery_warned'):
                        self.log_activity("⚠️ Low battery")
                        self._battery_warned = True
                    elif battery.percent > 20 or battery.power_plugged:
                        self._battery_warned = False
                else:
                    self.battery_label.config(text="Battery: N/A")
            except:
                self.battery_label.config(text="Battery: N/A")
        except:
            pass
        
        if self.root:
            self.root.after(2000, self.update_stats)
    
    def add_message(self, sender: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        msg_frame = tk.Frame(self.chat_inner, bg='#000a00')
        msg_frame.pack(fill='x', pady=5, padx=10)
        
        color = '#00ff41' if sender == 'BenX' else '#00ffff'
        
        tk.Label(msg_frame, text=f"[{timestamp}] {sender}:", font=('Courier New', 10, 'bold'), fg=color, bg='#000a00', anchor='w').pack(anchor='w')
        tk.Label(msg_frame, text=f"  {message}", font=('Courier New', 10), fg='#cccccc', bg='#000a00', wraplength=400, justify='left', anchor='w').pack(anchor='w', padx=10)
        
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        
        # Log activity
        if sender == 'You':
            self.log_activity(f"Command: {message[:40]}..." if len(message) > 40 else f"Command: {message}")
        elif sender == 'BenX' and '✅' in message:
            self.log_activity(f"Success: {message[:40]}..." if len(message) > 40 else f"Success: {message}")
        elif sender == 'BenX' and '❌' in message:
            self.log_activity(f"Error: {message[:40]}..." if len(message) > 40 else f"Error: {message}")
    
    def log_activity(self, activity: str):
        """Add activity to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {activity}"
        self.activity_entries.append(entry)
        
        # Keep only last 50 entries
        if len(self.activity_entries) > 50:
            self.activity_entries.pop(0)
        
        # Update log display
        self.activity_log.config(state='normal')
        self.activity_log.delete('1.0', tk.END)
        self.activity_log.insert('1.0', '\n'.join(self.activity_entries))
        self.activity_log.config(state='disabled')
        self.activity_log.see(tk.END)
    
    def clear_chat(self):
        for widget in self.chat_inner.winfo_children():
            widget.destroy()
        self.add_message("BenX", "Chat cleared")
        self.log_activity("Chat cleared")
    
    def process_input(self):
        if self.processing:
            return
        
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        self.input_entry.delete(0, tk.END)
        self.add_message("You", user_input)
        
        self.processing = True
        threading.Thread(target=self._process_thread, args=(user_input,), daemon=True).start()
    
    def _process_thread(self, user_input: str):
        try:
            self.jarvis.save_command(user_input)
            from jarvis_ai.executor import CommandExecutor
            
            self.root.after(0, self.log_activity, "Processing command...")
            
            json_cmd = self.ai_engine.interpret_command(user_input, conversation_context=self.ai_engine.conversation_history, learning_engine=self.ai_engine.learning_engine)
            result = CommandExecutor.execute(json_cmd, self.ai_engine, user_input)
            
            if result is None:
                response = self.ai_engine.chat(user_input)
                self.root.after(0, self._show_response, response)
            else:
                self.root.after(0, self._show_response, result)
                
                # Log specific actions
                try:
                    import json
                    cmd_obj = json.loads(json_cmd)
                    action = cmd_obj.get("command", "")
                    
                    if action == "open_app":
                        self.root.after(0, self.log_activity, f"App: {cmd_obj.get('app', 'unknown')}")
                    elif action in ["set_volume", "increase_volume", "decrease_volume"]:
                        self.root.after(0, self.log_activity, f"Volume adjusted")
                    elif action in ["set_brightness", "increase_brightness", "decrease_brightness"]:
                        self.root.after(0, self.log_activity, f"Brightness adjusted")
                    elif action == "take_screenshot":
                        self.root.after(0, self.log_activity, f"Screenshot captured")
                    elif action in ["create_file", "write_file"]:
                        self.root.after(0, self.log_activity, f"File operation")
                    elif action == "search_github":
                        self.root.after(0, self.log_activity, f"GitHub search")
                    elif action == "open_whatsapp_contact":
                        self.root.after(0, self.log_activity, f"WhatsApp opened")
                    elif action == "send_whatsapp_message":
                        self.root.after(0, self.log_activity, f"WhatsApp message requested")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error: {e}")
            self.root.after(0, self._show_response, f"Error: {str(e)}")
            self.root.after(0, self.log_activity, f"❌ Error occurred")
        finally:
            self.processing = False
    
    def _show_response(self, response: str):
        self.add_message("BenX", response)
        # Also add to compact chat if it exists
        if hasattr(self, 'compact_chat_inner') and self.compact_chat_inner:
            self.add_compact_message("BenX", response)
        if hasattr(self.voice_handler, 'tts_engine') and len(response) < 500:
            self.voice_handler.speak(response)
    
    def voice_input(self):
        self.log_activity("🎤 Voice input activated")
        def _listen():
            text = self.voice_handler.listen()
            if text:
                self.root.after(0, lambda: self.input_entry.insert(0, text))
                self.root.after(0, self.process_input)
                self.root.after(0, self.log_activity, f"Voice: {text[:30]}..." if len(text) > 30 else f"Voice: {text}")
            else:
                self.root.after(0, self.log_activity, "❌ Voice input failed")
        
        threading.Thread(target=_listen, daemon=True).start()
    
    def toggle_compact_mode(self):
        """Toggle between full and compact mode"""
        if self.window_mode == 'full':
            self.enter_compact_mode()
        else:
            self.enter_full_mode()
    
    def enter_compact_mode(self):
        """Enter compact mode - chat only"""
        self.window_mode = 'compact'
        
        # Hide main window
        self.root.withdraw()
        
        # Create compact window
        if hasattr(self, 'compact_win') and self.compact_win:
            try:
                self.compact_win.destroy()
            except:
                pass
        
        self.compact_win = tk.Toplevel(self.root)
        self.compact_win.title("BenX Chat")
        self.compact_win.configure(bg='#000000')
        self.compact_win.overrideredirect(True)
        self.compact_win.attributes('-topmost', True)
        
        width, height = 400, 500
        
        # Main frame
        main = tk.Frame(self.compact_win, bg='#001a00', bd=2, relief='solid')
        main.pack(fill='both', expand=True)
        
        # Title bar
        title_bar = tk.Frame(main, bg='#000000', height=40)
        title_bar.pack(fill='x')
        title_bar.pack_propagate(False)
        
        tk.Label(title_bar, text="BenX Chat", font=('Courier New', 12, 'bold'), fg='#00ff41', bg='#000000').pack(side='left', padx=10)
        
        # Expand button
        tk.Button(title_bar, text="▢", command=self.enter_full_mode, font=('Courier New', 14, 'bold'), bg='#000000', fg='#00ffff', activebackground='#001a00', activeforeground='#00ffff', relief='flat', bd=0, padx=10, cursor='hand2').pack(side='right', padx=5)
        
        # Minimize button
        tk.Button(title_bar, text="─", command=self.minimize_window, font=('Courier New', 14, 'bold'), bg='#000000', fg='#00ff41', activebackground='#001a00', activeforeground='#00ff41', relief='flat', bd=0, padx=10, cursor='hand2').pack(side='right', padx=5)
        
        # Chat area
        chat_frame = tk.Frame(main, bg='#000a00', bd=1, relief='solid')
        chat_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.compact_chat_canvas = Canvas(chat_frame, bg='#000a00', highlightthickness=0)
        self.compact_chat_canvas.pack(side='left', fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(chat_frame, command=self.compact_chat_canvas.yview, bg='#001a00')
        scrollbar.pack(side='right', fill='y')
        self.compact_chat_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.compact_chat_inner = tk.Frame(self.compact_chat_canvas, bg='#000a00')
        self.compact_chat_canvas.create_window((0, 0), window=self.compact_chat_inner, anchor='nw')
        self.compact_chat_inner.bind('<Configure>', lambda e: self.compact_chat_canvas.configure(scrollregion=self.compact_chat_canvas.bbox('all')))
        
        # Copy existing messages
        for widget in self.chat_inner.winfo_children():
            # Clone message to compact view
            pass
        
        # Input area
        input_frame = tk.Frame(main, bg='#001a00', bd=2, relief='solid')
        input_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.compact_input = tk.Entry(input_frame, font=('Courier New', 11), bg='#000a00', fg='#00ff41', insertbackground='#00ff41', relief='flat', bd=8)
        self.compact_input.pack(fill='x')
        self.compact_input.bind('<Return>', lambda e: self.process_compact_input())
        self.compact_input.focus()
        
        # Buttons
        btn_frame = tk.Frame(main, bg='#001a00')
        btn_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Button(btn_frame, text="SEND", command=self.process_compact_input, font=('Courier New', 10, 'bold'), bg='#000000', fg='#00ff41', activebackground='#001a00', activeforeground='#00ff41', relief='solid', bd=2, padx=15, pady=6).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="VOICE", command=self.voice_input, font=('Courier New', 10, 'bold'), bg='#000000', fg='#00ffff', activebackground='#001a00', activeforeground='#00ffff', relief='solid', bd=2, padx=15, pady=6).pack(side='left', padx=5)
        
        # Make draggable
        def on_drag(e):
            self.compact_win.geometry(f'+{e.x_root-width//2}+{e.y_root-20}')
        title_bar.bind('<B1-Motion>', on_drag)
        
        # Position
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - width - 40
        y = screen_h - height - 80
        self.compact_win.geometry(f'{width}x{height}+{x}+{y}')
        
        self.log_activity("Entered compact mode")
    
    def enter_full_mode(self):
        """Return to full mode"""
        self.window_mode = 'full'
        
        # Close compact window
        if hasattr(self, 'compact_win') and self.compact_win:
            try:
                self.compact_win.destroy()
            except:
                pass
        
        # Show main window
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.log_activity("Entered full mode")
    
    def process_compact_input(self):
        """Process input from compact mode"""
        if self.processing:
            return
        
        user_input = self.compact_input.get().strip()
        if not user_input:
            return
        
        self.compact_input.delete(0, tk.END)
        
        # Add to both chat views
        self.add_message("You", user_input)
        self.add_compact_message("You", user_input)
        
        self.processing = True
        threading.Thread(target=self._process_thread, args=(user_input,), daemon=True).start()
    
    def add_compact_message(self, sender: str, message: str):
        """Add message to compact chat"""
        if not hasattr(self, 'compact_chat_inner'):
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        msg_frame = tk.Frame(self.compact_chat_inner, bg='#000a00')
        msg_frame.pack(fill='x', pady=5, padx=10)
        
        color = '#00ff41' if sender == 'BenX' else '#00ffff'
        
        tk.Label(msg_frame, text=f"[{timestamp}] {sender}:", font=('Courier New', 9, 'bold'), fg=color, bg='#000a00', anchor='w').pack(anchor='w')
        tk.Label(msg_frame, text=f"  {message}", font=('Courier New', 9), fg='#cccccc', bg='#000a00', wraplength=350, justify='left', anchor='w').pack(anchor='w', padx=10)
        
        self.compact_chat_canvas.update_idletasks()
        self.compact_chat_canvas.yview_moveto(1.0)
    
    def minimize_window(self):
        """Minimize to notification bar"""
        if self.window_mode == 'compact':
            # Close compact window
            if hasattr(self, 'compact_win') and self.compact_win:
                try:
                    self.compact_win.destroy()
                except:
                    pass
            self.previous_mode = 'compact'
        else:
            # Hide main window
            self.root.withdraw()
            self.previous_mode = 'full'
        
        self.window_mode = 'minimized'
        self.log_activity("Creating restore button...")
        self.create_restore_button()
        self.log_activity("Minimized (click notification)")
    
    def create_restore_button(self):
        """Create floating restore button - macOS notification style"""
        if hasattr(self, 'restore_win') and self.restore_win:
            try:
                self.restore_win.destroy()
            except:
                pass
        
        from PIL import Image, ImageDraw, ImageTk
        from pathlib import Path
        
        self.restore_win = tk.Toplevel(self.root)
        self.restore_win.title("BenX")
        self.restore_win.overrideredirect(True)
        self.restore_win.attributes('-topmost', True)
        
        # Very compact notification bar
        width = 150
        height = 40
        
        # Create frame without border
        frame = tk.Frame(self.restore_win, bg='#1a1a1a', bd=0, highlightthickness=0)
        frame.pack(fill='both', expand=True)
        
        # Content frame
        content = tk.Frame(frame, bg='#1a1a1a')
        content.pack(fill='both', expand=True, padx=6, pady=6)
        
        # Left side - Logo
        logo_path = Path(__file__).parent.parent.parent / "benx.jpg"
        if logo_path.exists():
            img = Image.open(logo_path).convert('RGBA')
            img = img.resize((28, 28), Image.Resampling.LANCZOS)
            self.restore_photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(content, image=self.restore_photo, bg='#1a1a1a', bd=0)
        else:
            logo_label = tk.Label(content, text='B', font=('Orbitron', 14, 'bold'), fg='#00ff41', bg='#1a1a1a', bd=0)
        logo_label.pack(side='left', padx=(0, 6))
        
        # Right side - Text
        text_label = tk.Label(content, text='BenX', font=('Arial', 11, 'bold'), fg='#ffffff', bg='#1a1a1a', anchor='w', bd=0)
        text_label.pack(side='left', fill='both', expand=True)
        
        # Bind click to entire window
        def on_click(e):
            self.restore_window()
        
        for widget in [self.restore_win, frame, content, logo_label, text_label]:
            widget.bind('<Button-1>', on_click)
        
        # Make draggable
        def on_drag(e):
            self.restore_win.geometry(f'+{e.x_root-width//2}+{e.y_root-20}')
        
        frame.bind('<B1-Motion>', on_drag)
        
        # Position at top right
        def set_position():
            screen_w = self.root.winfo_screenwidth()
            x = screen_w - width - 20
            y = 60
            self.restore_win.geometry(f'{width}x{height}+{x}+{y}')
            self.restore_win.lift()
            logger.info(f"Restore notification positioned at top right: {x},{y}")
        
        self.restore_win.after(100, set_position)
    
    def restore_window(self):
        """Restore window from minimized state"""
        if hasattr(self, 'restore_win') and self.restore_win:
            self.restore_win.destroy()
            self.restore_win = None
        
        # Restore to previous mode
        previous = getattr(self, 'previous_mode', 'full')
        
        if previous == 'compact':
            self.enter_compact_mode()
        else:
            self.window_mode = 'full'
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        
        self.log_activity(f"Restored to {previous} mode")
    
    def on_closing(self):
        self.root.destroy()
        self.jarvis.running = False
    
    def run(self):
        if self.root:
            self.root.mainloop()


JarvisUI = BenXUI
EnhancedJarvisUI = BenXUI
ModernTechUI = BenXUI
UltimateTechUI = BenXUI
