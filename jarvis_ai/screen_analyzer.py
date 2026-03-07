"""
Screen Analyzer with RAG-enhanced image understanding
"""
import logging
from typing import Optional, Tuple
from jarvis_ai.config import Config
from jarvis_ai.ai_engine import AIEngine

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pyautogui
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False


class ScreenAnalyzer:
    """Screen analysis with OCR and AI vision"""
    
    @staticmethod
    def analyze_with_ai(image, ocr_text: str, screen_width: int, screen_height: int) -> str:
        """Analyze screen using AI with OCR text and vision"""
        try:
            # Use vision model for better image understanding
            if hasattr(image, 'save') and OCR_AVAILABLE:
                # Save image temporarily for vision analysis
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    image.save(tmp.name)
                    temp_path = tmp.name
                
                try:
                    # Use AI engine with vision
                    ai_engine = AIEngine()
                    vision_analysis = ai_engine.analyze_image(
                        temp_path,
                        f"Analyze this screen. OCR text found: {ocr_text[:500]}. Describe what you see, including applications, UI elements, and actionable items."
                    )
                    
                    # Combine OCR and vision analysis
                    analysis = f"""Screen Analysis:
                    
Screen Dimensions: {screen_width}x{screen_height}

Vision Analysis:
{vision_analysis}

OCR Text Extracted:
{ocr_text[:1000]}
"""
                    return analysis
                finally:
                    import os
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            
            # Fallback to text-only analysis
            system_prompt = """You are BenX's screen analyzer. Analyze the screen content based on OCR text."""
            
            analysis_prompt = f"""Screen Analysis Request:

Screen Dimensions: {screen_width}x{screen_height}
OCR Text Extracted:
{ocr_text[:2000]}

Analyze this screen and describe what is displayed."""
            
            return AIEngine.query_groq(system_prompt, analysis_prompt)
        except Exception as e:
            logger.error(f"Screen analysis error: {e}")
            return f"Screen analysis: OCR found {len(ocr_text)} characters. Error: {str(e)}"
    
    @staticmethod
    def find_text_on_screen(text: str) -> Optional[Tuple[int, int]]:
        """Find text on screen and return coordinates"""
        if not OCR_AVAILABLE or not AUTOMATION_AVAILABLE:
            return None
        
        try:
            from jarvis_ai.command_engine import CommandEngine
            CommandEngine.take_screenshot()
            img = Image.open(Config.SCREENSHOT_PATH)
            
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            for i, word in enumerate(data['text']):
                if text.lower() in word.lower():
                    x = data['left'][i] + data['width'][i] // 2
                    y = data['top'][i] + data['height'][i] // 2
                    return (x, y)
            
            return None
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return None









