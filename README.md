# 🎯 Jarvis Enhanced - Advanced AI Personal Assistant

A powerful AI-powered personal assistant with complete system control, advanced modal GUI, voice recognition, and natural language processing using Groq AI.

## ✨ Features

- **🤖 Advanced AI Integration**: Powered by Groq AI with multiple model fallbacks
- **🖥️ Complete System Control**: Control volume, brightness, apps, files, processes, and more
- **💬 Natural Language Processing**: Just speak naturally - Jarvis understands you
- **🎤 Voice Recognition**: Speak to Jarvis using your microphone
- **🔊 Text-to-Speech**: Jarvis speaks responses back to you
- **🎨 Beautiful Modal GUI**: Modern dark-themed interface that stays on top
- **📝 Conversation History**: Remembers context from previous conversations
- **⚡ Fast & Responsive**: Multi-threaded processing for smooth experience

## 🚀 Quick Start

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. For voice features (optional), you may need system audio libraries:
```bash
# Arch Linux
sudo pacman -S portaudio python-pyaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio
```

### Running Jarvis

**With GUI (Recommended):**
```bash
python3 jarvis.py
```

**CLI Mode (without GUI):**
```bash
python3 jarvis.py --no-gui
```

## 💡 Usage Examples

### Natural Language Commands
- "Open Chrome browser"
- "Set volume to 80"
- "Increase brightness by 20"
- "Take a screenshot"
- "What's the weather?"
- "Show system information"
- "List running applications"
- "Create a file called notes.txt with my todo list"

### Questions & Conversations
- "What's the capital of France?"
- "Explain quantum computing"
- "Help me write a Python function"
- "What's the weather in New York?"

### System Control
- Volume control (set, increase, decrease, mute)
- Brightness control
- Application management (open, list, kill)
- File operations (create, read, delete, search)
- Process management
- System info and monitoring
- Network management
- Media control
- Package management

## 🎨 GUI Features

- **Modal Interface**: Always-on-top window for quick access
- **Chat Display**: See conversation history
- **Voice Button**: Click to speak commands
- **Quick Actions**: One-click access to common tasks
- **Status Updates**: Real-time processing status

## 🔧 Configuration

Edit `jarvis.py` to customize:
- Groq API key (already configured)
- Model preferences
- GUI colors and theme
- System tool preferences

## 📋 Requirements

- Python 3.7+
- Linux system (Arch, Ubuntu, Debian, etc.)
- Internet connection for AI features
- Microphone (optional, for voice features)

## 🛠️ Troubleshooting

**Voice not working?**
- Install `portaudio` and `pyaudio`
- Check microphone permissions
- Test with: `python3 -c "import speech_recognition as sr; print('OK')"`

**GUI not showing?**
- Install tkinter: `sudo pacman -S tk` or `sudo apt-get install python3-tk`
- Run with `--no-gui` flag for CLI mode

**Commands not working?**
- Check if required system tools are installed (pamixer, brightnessctl, etc.)
- Check logs in `~/.jarvis/jarvis.log`

## 📝 Notes

- Conversation history is saved in `~/.jarvis/conversation.json`
- Command history is saved in `~/.jarvis/history.txt`
- Screenshots are saved to `/tmp/jarvis_screen.png`

## 🎯 Tips

- Press Enter to send messages
- Use voice button for hands-free operation
- Quick actions provide instant access to common tasks
- Jarvis remembers conversation context for better responses

Enjoy your AI assistant! 🚀
# Ben_Assito
# Ben_Assito
# Ben_Assito
# Ben_Assito
# Ben_Assito
# Ben_Assito
