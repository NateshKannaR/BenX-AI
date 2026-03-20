# BenX-AI

🎯 **BenX** - Advanced AI Personal Assistant with complete Linux system control, RAG capabilities, and beautiful GTK4 UI.

## ✨ Features

- 🧠 **Advanced AI** - Powered by Groq's latest models (Llama 3.3, Compound, Qwen3)
- 💬 **Natural Conversation** - Context-aware chat with conversation history
- 🎨 **Beautiful GTK4 UI** - Modern, glassmorphic interface
- 🖥️ **System Control** - Complete control over your Linux system
- 📁 **File Operations** - Create, read, write, search, and manage files
- 🔊 **Audio Control** - Volume, mute, media playback
- 💡 **Display Control** - Brightness adjustment
- 🌐 **Network Management** - WiFi, connections
- 📸 **Screen Analysis** - OCR and image understanding
- 🤖 **Automation** - Automate complex tasks
- 👨‍💻 **Developer Tools** - Code analysis, project orchestration
- 📚 **RAG (Retrieval-Augmented Generation)** - Enhanced context from memory
- 🗓️ **Task Scheduling** - Schedule tasks and reminders

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/NateshKannaR/BenX-AI.git
cd BenX-AI
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up API Key

Get a free API key from [Groq Console](https://console.groq.com/keys)

**Option A: Environment Variable (Recommended)**
```bash
export GROQ_API_KEY='your_key_here'
```

**Option B: Add to ~/.bashrc (Permanent)**
```bash
echo 'export GROQ_API_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

**Option C: Use Setup Script**
```bash
./setup_and_run.sh
```

### 4. Run BenX
```bash
python3 benx.py
```

Or use the setup script:
```bash
./setup_and_run.sh
```

## 🧪 Test Installation

Run the test script to verify everything is working:
```bash
python3 test_benx.py
```

## 📖 Usage Examples

### System Control
```
"open chrome"
"set volume to 50"
"increase brightness"
"lock screen"
"what's my battery status"
```

### File Operations
```
"create a file called test.py"
"read the file config.json"
"search for files containing 'todo'"
"list files in Downloads"
```

### AI Assistance
```
"what's the weather"
"explain quantum computing"
"help me write a Python function"
"analyze my screen"
```

### Developer Tools
```
"analyze this project"
"find all TODO comments"
"create a React component"
"search code for function_name"
```

### Automation
```
"automate opening chrome and going to github.com"
"schedule a reminder at 5 PM"
"preview automation steps"
```

## 🛠️ Configuration

Edit `jarvis_ai/config.py` to customize:
- Models and fallbacks
- Timeout settings
- UI theme colors
- System tool preferences
- RAG settings

## 📋 Requirements

- Python 3.8+
- Linux (tested on Arch, Ubuntu, Fedora)
- GTK4 (optional, for GUI)
- Internet connection (for AI API)

## 🔧 Troubleshooting

### API Key Issues
```bash
# Check if API key is set
echo $GROQ_API_KEY

# Set it temporarily
export GROQ_API_KEY='your_key_here'
```

### Model Errors
If you see 400/404 errors, the models may have changed. Check available models:
```bash
curl -s -X GET "https://api.groq.com/openai/v1/models" \
  -H "Authorization: Bearer $GROQ_API_KEY" | python3 -m json.tool
```

### Dependencies
```bash
# Install missing dependencies
pip install -r requirements.txt

# For GTK4 UI (optional)
sudo pacman -S gtk4 libadwaita  # Arch
sudo apt install libgtk-4-1 libadwaita-1-0  # Ubuntu
```

## 📚 Documentation

- [Quick Start Guide](QUICK_START.md)
- [Fix Summary](BENX_FIX_SUMMARY.md)
- [GTK4 UI Guide](BEAUTIFUL_GTK4_COMPLETE.md)
- [Screen Analysis](BEAUTIFUL_SCREEN_ANALYSIS.md)
- [Activity Log](ACTIVITY_LOG_GUIDE.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Powered by [Groq](https://groq.com/) - Ultra-fast AI inference
- Built with GTK4 and Libadwaita
- Uses Llama 3.3, Compound, and other state-of-the-art models

## 📞 Support

If you encounter any issues:
1. Check the [troubleshooting section](#-troubleshooting)
2. Run `python3 test_benx.py` to diagnose
3. Check logs at `~/.benx/benx.log`
4. Open an issue on GitHub

---

Made with ❤️ by [NateshKannaR](https://github.com/NateshKannaR)
