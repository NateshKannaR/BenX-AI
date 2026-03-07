"""
Code Executor - Safely execute code snippets
"""
import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Execute code snippets safely"""
    
    SUPPORTED_LANGUAGES = {
        'python': {'ext': '.py', 'cmd': ['python3']},
        'javascript': {'ext': '.js', 'cmd': ['node']},
        'bash': {'ext': '.sh', 'cmd': ['bash']},
        'shell': {'ext': '.sh', 'cmd': ['bash']},
    }
    
    def execute_code(self, code: str, language: str = 'python', timeout: int = 10) -> Dict:
        """Execute code and return result"""
        language = language.lower()
        
        if language not in self.SUPPORTED_LANGUAGES:
            return {
                'success': False,
                'error': f"Unsupported language: {language}. Supported: {', '.join(self.SUPPORTED_LANGUAGES.keys())}"
            }
        
        lang_config = self.SUPPORTED_LANGUAGES[language]
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=lang_config['ext'],
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # Execute code
                result = subprocess.run(
                    lang_config['cmd'] + [temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    'success': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            
            finally:
                # Clean up
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Execution timed out after {timeout} seconds"
            }
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_python(self, code: str) -> str:
        """Execute Python code"""
        result = self.execute_code(code, 'python')
        
        if result['success']:
            output = result['stdout']
            return f"✅ Output:\n{output}" if output else "✅ Executed successfully (no output)"
        else:
            error = result.get('stderr') or result.get('error')
            return f"❌ Error:\n{error}"
    
    def execute_bash(self, command: str) -> str:
        """Execute bash command"""
        result = self.execute_code(command, 'bash')
        
        if result['success']:
            return result['stdout'] or "✅ Command executed"
        else:
            return f"❌ Error: {result.get('stderr') or result.get('error')}"
