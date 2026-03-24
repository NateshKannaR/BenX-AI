# Dependency Installer Fix - No More Repeated Prompts

## Problem
BenX was asking to install packages repeatedly, even after they were already installed.

## Root Cause
The dependency installer was checking and prompting **before** executing commands, rather than only when commands actually failed due to missing dependencies.

## Solution
Changed the approach to **lazy installation**:

### Before (Bad):
```
User: "what's on my screen"
  ↓
Check dependencies → Prompt to install
  ↓
Execute command
```
**Problem**: Prompts every time, even if packages are installed!

### After (Good):
```
User: "what's on my screen"
  ↓
Try to execute command
  ↓
If ImportError/ModuleNotFoundError → Prompt to install → Retry
  ↓
Success!
```
**Solution**: Only prompts when command actually fails!

## Changes Made

### 1. **Executor.py** - Smart Error Detection
```python
try:
    result = command_map[action]()
except Exception as cmd_error:
    # Only install if error is due to missing dependencies
    if "no module" in str(cmd_error).lower() or "import" in str(cmd_error).lower():
        install_result = DependencyInstaller.auto_install_for_command(action, confirm_cb)
        # Retry after installation
        result = command_map[action]()
```

### 2. **Command Engine** - Proper Error Raising
Changed from returning error strings to raising ImportError:
```python
# Before
if not OCR_AVAILABLE:
    return "❌ OCR not available..."

# After
if not OCR_AVAILABLE:
    raise ImportError("OCR not available...")
```

### 3. **Better Error Detection**
Now detects these error patterns:
- `"no module"`
- `"import"`
- `"not available"`
- `"not installed"`

## Benefits

✅ **No repeated prompts** - Only asks once when actually needed
✅ **Smarter detection** - Only installs when command fails
✅ **Better UX** - No annoying repeated dialogs
✅ **Automatic retry** - Retries command after successful installation
✅ **Proper error handling** - Clear error messages if installation fails

## Testing

```bash
# First time - will prompt to install
python benx.py
> "what's on my screen"
[Shows install dialog] → Click Install → Works!

# Second time - no prompt!
> "what's on my screen"
[Works immediately, no dialog!]
```

## Files Modified
- ✅ `jarvis_ai/executor.py` - Lazy installation logic
- ✅ `jarvis_ai/command_engine.py` - Proper ImportError raising
- ✅ Error detection for screen analysis, OCR, and automation

**Now BenX only asks to install packages when they're actually needed!** 🎉
