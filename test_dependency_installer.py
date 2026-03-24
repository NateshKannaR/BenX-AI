#!/usr/bin/env python3
"""
Test the dependency installer
"""
from jarvis_ai.dependency_installer import DependencyInstaller

# Test checking for missing dependencies
print("🔍 Checking for screen analysis dependencies...")
missing_python, missing_system = DependencyInstaller.get_missing_dependencies("screen_analysis")

if missing_python:
    print(f"Missing Python packages: {', '.join(missing_python)}")
else:
    print("✅ All Python packages installed")

if missing_system:
    print(f"Missing system packages: {', '.join(missing_system)}")
else:
    print("✅ All system packages installed")

# Test the prompt (will ask for confirmation)
if missing_python or missing_system:
    print("\n" + "="*50)
    result = DependencyInstaller.prompt_install("screen_analysis")
    if result:
        print(result)
else:
    print("\n✨ All dependencies already installed!")
