"""
Automatic Dependency Installer - Installs missing packages with user confirmation
"""
import subprocess
import sys
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class DependencyInstaller:
    """Handles automatic installation of missing dependencies"""
    
    # Map of features to their required packages
    FEATURE_DEPENDENCIES = {
        "screen_analysis": {
            "packages": ["pyautogui", "pytesseract", "Pillow"],
            "system_packages": ["tesseract-ocr"],
            "description": "Screen detection and OCR capabilities"
        },
        "automation": {
            "packages": ["pyautogui"],
            "system_packages": [],
            "description": "Screen automation and clicking"
        },
        "ocr": {
            "packages": ["pytesseract", "Pillow"],
            "system_packages": ["tesseract-ocr"],
            "description": "Text extraction from images"
        },
        "image_processing": {
            "packages": ["Pillow"],
            "system_packages": [],
            "description": "Image manipulation and processing"
        },
        "rag": {
            "packages": ["numpy", "faiss-cpu", "sentence-transformers"],
            "system_packages": [],
            "description": "Advanced memory and context retrieval"
        },
        "pdf": {
            "packages": ["reportlab"],
            "system_packages": [],
            "description": "PDF creation"
        }
    }
    
    @staticmethod
    def check_package_installed(package: str) -> bool:
        """Check if a Python package is installed"""
        try:
            __import__(package.replace("-", "_"))
            return True
        except ImportError:
            return False
    
    @staticmethod
    def check_system_package_installed(package: str) -> bool:
        """Check if a system package is installed"""
        try:
            result = subprocess.run(
                ["which", package.split("-")[0]],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def get_missing_dependencies(feature: str) -> Tuple[List[str], List[str]]:
        """Get missing Python and system packages for a feature"""
        if feature not in DependencyInstaller.FEATURE_DEPENDENCIES:
            return [], []
        
        deps = DependencyInstaller.FEATURE_DEPENDENCIES[feature]
        
        missing_python = [
            pkg for pkg in deps["packages"]
            if not DependencyInstaller.check_package_installed(pkg)
        ]
        
        missing_system = [
            pkg for pkg in deps["system_packages"]
            if not DependencyInstaller.check_system_package_installed(pkg)
        ]
        
        return missing_python, missing_system
    
    @staticmethod
    def install_python_packages(packages: List[str]) -> Tuple[bool, str]:
        """Install Python packages using pip"""
        if not packages:
            return True, ""
        
        try:
            logger.info(f"Installing Python packages: {', '.join(packages)}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + packages,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, f"✅ Successfully installed: {', '.join(packages)}"
            else:
                return False, f"❌ Installation failed: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return False, "❌ Installation timed out"
        except Exception as e:
            return False, f"❌ Installation error: {str(e)}"
    
    @staticmethod
    def install_system_packages(packages: List[str]) -> Tuple[bool, str]:
        """Install system packages using package manager"""
        if not packages:
            return True, ""
        
        # Detect package manager
        managers = [
            ("yay", ["yay", "-S", "--noconfirm"]),
            ("pacman", ["sudo", "pacman", "-S", "--noconfirm"]),
            ("apt", ["sudo", "apt", "install", "-y"]),
            ("dnf", ["sudo", "dnf", "install", "-y"]),
            ("zypper", ["sudo", "zypper", "install", "-y"])
        ]
        
        for manager_name, base_cmd in managers:
            try:
                result = subprocess.run(
                    ["which", manager_name],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Installing system packages with {manager_name}: {', '.join(packages)}")
                    result = subprocess.run(
                        base_cmd + packages,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        return True, f"✅ Successfully installed system packages: {', '.join(packages)}"
                    else:
                        return False, f"❌ System package installation failed: {result.stderr[:200]}"
            except Exception:
                continue
        
        return False, f"❌ No package manager found. Please install manually: {', '.join(packages)}"
    
    @staticmethod
    def prompt_install(feature: str, callback=None) -> Optional[str]:
        """
        Prompt user to install missing dependencies for a feature
        
        Args:
            feature: Feature name (e.g., 'screen_analysis', 'automation')
            callback: Optional callback function for GUI confirmation
        
        Returns:
            Success message or None if cancelled/failed
        """
        if feature not in DependencyInstaller.FEATURE_DEPENDENCIES:
            return None
        
        missing_python, missing_system = DependencyInstaller.get_missing_dependencies(feature)
        
        if not missing_python and not missing_system:
            return None  # All dependencies already installed
        
        deps = DependencyInstaller.FEATURE_DEPENDENCIES[feature]
        description = deps["description"]
        
        # Build prompt message
        message = f"🔧 Missing dependencies for {description}:\n\n"
        
        if missing_python:
            message += f"Python packages: {', '.join(missing_python)}\n"
        if missing_system:
            message += f"System packages: {', '.join(missing_system)}\n"
        
        message += "\nWould you like to install them now?"
        
        # Get user confirmation
        confirmed = False
        if callback:
            try:
                confirmed = callback(message)
            except Exception:
                pass
        else:
            try:
                response = input(f"{message} [y/N]: ").strip().lower()
                confirmed = response in ["y", "yes"]
            except Exception:
                return None
        
        if not confirmed:
            return "⚠️ Installation cancelled. Feature may not work without dependencies."
        
        # Install packages
        results = []
        
        if missing_python:
            success, msg = DependencyInstaller.install_python_packages(missing_python)
            results.append(msg)
            if not success:
                return "\n".join(results)
        
        if missing_system:
            success, msg = DependencyInstaller.install_system_packages(missing_system)
            results.append(msg)
            if not success:
                return "\n".join(results)
        
        return "\n".join(results) + f"\n\n✨ {description.capitalize()} is now ready to use!"
    
    @staticmethod
    def auto_install_for_command(command: str, callback=None) -> Optional[str]:
        """
        Automatically detect and install dependencies for a command
        
        Args:
            command: Command name (e.g., 'analyze_screen', 'automate')
            callback: Optional callback for GUI confirmation
        
        Returns:
            Installation result message or None
        """
        # Map commands to features
        command_to_feature = {
            "analyze_screen": "screen_analysis",
            "read_screen_text": "ocr",
            "automate": "automation",
            "screen_aware_click": "automation",
            "analyze_image": "image_processing",
            "create_pdf": "pdf"
        }
        
        feature = command_to_feature.get(command)
        if not feature:
            return None
        
        return DependencyInstaller.prompt_install(feature, callback)
