# Automatic Dependency Installation

## Overview
BenX now automatically detects missing dependencies and prompts you to install them when needed!

## How It Works

### 1. **Automatic Detection**
When you try to use a feature that requires additional packages, BenX will:
- Detect which packages are missing
- Show you what needs to be installed
- Ask for your permission before installing

### 2. **Supported Features**

#### Screen Analysis (`analyze_screen`, `read_screen_text`)
- **Python packages**: pyautogui, pytesseract, Pillow
- **System packages**: tesseract-ocr
- **Description**: Screen detection and OCR capabilities

#### Automation (`automate`, `screen_aware_click`)
- **Python packages**: pyautogui
- **Description**: Screen automation and clicking

#### Image Processing (`analyze_image`)
- **Python packages**: Pillow
- **Description**: Image manipulation and processing

#### PDF Creation (`create_pdf`)
- **Python packages**: reportlab
- **Description**: PDF file generation

#### RAG (Advanced Memory)
- **Python packages**: numpy, faiss-cpu, sentence-transformers
- **Description**: Enhanced context retrieval and memory

### 3. **User Experience**

#### In GUI Mode:
```
You: "what's on my screen"
BenX: [Shows dialog]
      🔧 Missing dependencies for Screen detection and OCR capabilities:
      
      Python packages: pyautogui, pytesseract, Pillow
      System packages: tesseract-ocr
      
      Would you like to install them now?
      
      [Cancel] [Install]
```

#### In Terminal Mode:
```
You: "what's on my screen"
BenX: 🔧 Missing dependencies for Screen detection and OCR capabilities:

      Python packages: pyautogui, pytesseract, Pillow
      System packages: tesseract-ocr
      
      Would you like to install them now? [y/N]: y
      
      ✅ Successfully installed: pyautogui, pytesseract, Pillow
      ✅ Successfully installed system packages: tesseract-ocr
      
      ✨ Screen detection and OCR capabilities is now ready to use!
```

### 4. **Installation Process**

BenX will:
1. Install Python packages using `pip`
2. Install system packages using your system's package manager:
   - **Arch Linux**: yay or pacman
   - **Ubuntu/Debian**: apt
   - **Fedora**: dnf
   - **openSUSE**: zypper

### 5. **Manual Testing**

Test the dependency installer:
```bash
python test_dependency_installer.py
```

### 6. **Benefits**

✅ **No more manual installation** - BenX handles it for you
✅ **Smart detection** - Only installs what's actually missing
✅ **User control** - You approve before anything is installed
✅ **Cross-platform** - Works with multiple package managers
✅ **Informative** - Shows exactly what will be installed and why

### 7. **Example Commands That Trigger Auto-Install**

- `"what's on my screen"` → Installs screen analysis tools
- `"analyze screen"` → Installs screen analysis tools
- `"read screen text"` → Installs OCR tools
- `"automate clicking the button"` → Installs automation tools
- `"create a pdf"` → Installs PDF generation tools
- `"analyze this image"` → Installs image processing tools

### 8. **Safety Features**

- ✅ Always asks for confirmation before installing
- ✅ Shows exactly what will be installed
- ✅ Timeout protection (30 seconds for GUI dialogs)
- ✅ Error handling with clear messages
- ✅ Cancellable at any time

## Technical Details

### Architecture
```
User Command → Executor → DependencyInstaller
                              ↓
                    Check Missing Packages
                              ↓
                    Prompt User (GUI/CLI)
                              ↓
                    Install if Confirmed
                              ↓
                    Execute Original Command
```

### Files Modified/Created
- ✅ `jarvis_ai/dependency_installer.py` - New installer module
- ✅ `jarvis_ai/executor.py` - Integrated auto-install
- ✅ `jarvis_ai/gui/beautiful_gtk4.py` - Added GUI confirmation dialog
- ✅ `test_dependency_installer.py` - Test script

## Usage

Just use BenX normally! When you try a feature that needs additional packages, BenX will automatically:
1. Detect what's missing
2. Ask if you want to install it
3. Install it for you (with your permission)
4. Execute your command

**No configuration needed - it just works!** 🚀
