"""
Project Orchestrator - Agentic AI System for Project Management
Implements: Planner, FileSystem, Refactor, Reviewer, and Memory agents
"""
import json
import os
import re
import logging
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from jarvis_ai.config import Config
from jarvis_ai.ai_engine import AIEngine

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Remembers and manages project structure"""
    
    def __init__(self):
        self.projects = {}  # project_name -> project_data
        self.current_project = None
        self.memory_file = Config.BENX_DIR / "project_memory.json"
        self.load_memory()
    
    def load_memory(self):
        """Load project memory from disk"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projects = data.get("projects", {})
                    self.current_project = data.get("current_project")
        except Exception as e:
            logger.warning(f"Failed to load project memory: {e}")
            self.projects = {}
    
    def save_memory(self):
        """Save project memory to disk"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "projects": self.projects,
                    "current_project": self.current_project,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save project memory: {e}")
    
    def register_project(self, project_name: str, base_path: str, structure: Dict):
        """Register a new project in memory"""
        self.projects[project_name] = {
            "base_path": base_path,
            "structure": structure,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        self.current_project = project_name
        self.save_memory()
    
    def update_project_structure(self, project_name: str, structure: Dict):
        """Update project structure"""
        if project_name in self.projects:
            self.projects[project_name]["structure"] = structure
            self.projects[project_name]["last_modified"] = datetime.now().isoformat()
            self.save_memory()
    
    def get_project_structure(self, project_name: str = None) -> Optional[Dict]:
        """Get project structure"""
        name = project_name or self.current_project
        if name and name in self.projects:
            return self.projects[name]
        return None
    
    def scan_project_structure(self, base_path: str) -> Dict:
        """Scan and return current project structure"""
        structure = {
            "files": [],
            "directories": [],
            "dependencies": [],
            "framework": None,
            "language": None
        }
        
        base = Path(base_path)
        if not base.exists():
            return structure
        
        # Scan files and directories
        for item in base.rglob("*"):
            if item.is_file():
                structure["files"].append(str(item.relative_to(base)))
                # Detect language/framework
                if item.suffix == ".py":
                    structure["language"] = "python"
                elif item.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                    structure["language"] = "javascript" if ".ts" not in item.suffix else "typescript"
                elif item.suffix == ".go":
                    structure["language"] = "go"
                elif item.suffix == ".rs":
                    structure["language"] = "rust"
                elif item.suffix == ".java":
                    structure["language"] = "java"
            elif item.is_dir() and item.name not in [".git", "__pycache__", "node_modules", ".venv", "venv"]:
                structure["directories"].append(str(item.relative_to(base)))
        
        # Detect framework
        if (base / "requirements.txt").exists():
            structure["framework"] = "flask"
            try:
                with open(base / "requirements.txt", 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "fastapi" in content.lower():
                        structure["framework"] = "fastapi"
                    elif "django" in content.lower():
                        structure["framework"] = "django"
                    elif "flask" in content.lower():
                        structure["framework"] = "flask"
            except OSError:
                pass
        elif (base / "package.json").exists():
            structure["framework"] = "node"
            try:
                with open(base / "package.json", 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    deps = pkg.get("dependencies", {})
                    if "react" in deps:
                        structure["framework"] = "react"
                    elif "vue" in deps:
                        structure["framework"] = "vue"
                    elif "express" in deps:
                        structure["framework"] = "express"
            except (json.JSONDecodeError, OSError):
                pass
        
        return structure


class PlannerAgent:
    """Decides what to build and creates project plans"""
    
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
    
    def create_plan(self, user_request: str, context: Dict = None) -> Dict:
        """Create a detailed project plan from user request"""
        system_prompt = """You are a project planning AI. Analyze user requests and create detailed, actionable project plans.

Your plans should include:
1. Project type and purpose
2. Technology stack recommendations
3. File structure (folders and files)
4. Dependencies needed
5. Implementation steps
6. Key features to implement

Return a JSON object with this structure:
{
    "project_name": "name",
    "project_type": "web_app|api|cli|library|etc",
    "description": "what this project does",
    "tech_stack": {
        "language": "python|javascript|go|etc",
        "framework": "flask|fastapi|react|express|etc",
        "database": "sqlite|postgresql|mongodb|none",
        "other": ["list", "of", "tools"]
    },
    "structure": {
        "directories": ["dir1", "dir2/subdir"],
        "files": [
            {"path": "file.py", "purpose": "description", "content_hint": "what should be in it"}
        ]
    },
    "dependencies": ["package1", "package2"],
    "steps": [
        {"step": 1, "action": "create directory", "target": "src/"},
        {"step": 2, "action": "create file", "target": "src/main.py", "content": "code here"}
    ],
    "features": ["feature1", "feature2"]
}"""
        
        context_str = ""
        if context:
            context_str = f"\n\nCurrent Context:\n{json.dumps(context, indent=2)}"
        
        prompt = f"""Create a detailed project plan for this request:

"{user_request}"
{context_str}

Think step-by-step:
1. What type of project is this?
2. What technology stack is best?
3. What files and folders are needed?
4. What dependencies are required?
5. What are the implementation steps?

Return ONLY valid JSON."""
        
        response = self.ai_engine.query_groq(system_prompt, prompt)
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                plan = json.loads(json_match.group(0))
                return plan
            except json.JSONDecodeError:
                logger.error("Failed to parse plan JSON")
        
        # Fallback plan
        return {
            "project_name": "new_project",
            "project_type": "application",
            "description": user_request,
            "tech_stack": {"language": "python", "framework": "flask"},
            "structure": {"directories": [], "files": []},
            "dependencies": [],
            "steps": [],
            "features": []
        }
    
    def plan_modification(self, user_request: str, current_structure: Dict) -> Dict:
        """Plan a modification to existing project"""
        system_prompt = """You are a project modification planner. Analyze requests to modify existing projects.

Return a JSON object with:
{
    "modification_type": "add_feature|refactor|fix_bug|change_framework|etc",
    "targets": ["file1.py", "dir1/"],
    "actions": [
        {"action": "create|modify|delete|refactor", "target": "path", "description": "what to do"}
    ],
    "dependencies_to_add": ["package1"],
    "dependencies_to_remove": ["package2"]
}"""
        
        prompt = f"""Plan this modification:

Request: "{user_request}"

Current Structure:
{json.dumps(current_structure, indent=2)}

What needs to be changed? Return ONLY valid JSON."""
        
        response = self.ai_engine.query_groq(system_prompt, prompt)
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return {
            "modification_type": "modify",
            "targets": [],
            "actions": [],
            "dependencies_to_add": [],
            "dependencies_to_remove": []
        }


class FileSystemAgent:
    """Creates and edits files"""
    
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
    
    def create_file(self, file_path: str, content: str = "", purpose: str = "") -> Tuple[bool, str]:
        """Create a file with content"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if not content and purpose:
                # Generate content based on purpose
                content = self._generate_file_content(path, purpose)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, f"✅ Created {file_path}"
        except Exception as e:
            return False, f"❌ Failed to create {file_path}: {str(e)}"
    
    def _generate_file_content(self, file_path: Path, purpose: str) -> str:
        """Generate file content using AI"""
        ext = file_path.suffix
        system_prompt = f"""You are a code generator. Generate appropriate {ext} file content based on the purpose.

Generate clean, well-structured code with:
- Proper imports
- Good structure
- Comments where helpful
- Best practices

Return ONLY the code, no markdown formatting."""
        
        prompt = f"""Generate code for {file_path.name} with purpose: {purpose}

File extension: {ext}
Return clean, production-ready code."""
        
        content = self.ai_engine.query_groq(system_prompt, prompt)
        # Remove markdown code blocks if present
        content = re.sub(r'```[\w]*\n?', '', content)
        return content.strip()
    
    def create_directory(self, dir_path: str) -> Tuple[bool, str]:
        """Create a directory"""
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            return True, f"✅ Created directory {dir_path}"
        except Exception as e:
            return False, f"❌ Failed to create directory: {str(e)}"
    
    def read_file(self, file_path: str) -> Tuple[bool, str]:
        """Read file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return True, f.read()
        except Exception as e:
            return False, f"❌ Failed to read {file_path}: {str(e)}"
    
    def write_file(self, file_path: str, content: str) -> Tuple[bool, str]:
        """Write content to file"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"✅ Updated {file_path}"
        except Exception as e:
            return False, f"❌ Failed to write {file_path}: {str(e)}"
    
    def delete_file(self, file_path: str) -> Tuple[bool, str]:
        """Delete a file"""
        try:
            Path(file_path).unlink()
            return True, f"✅ Deleted {file_path}"
        except Exception as e:
            return False, f"❌ Failed to delete {file_path}: {str(e)}"
    
    def execute_plan(self, plan: Dict, base_path: str = ".") -> List[str]:
        """Execute a project plan"""
        results = []
        base = Path(base_path)
        
        # Create directories
        for dir_path in plan.get("structure", {}).get("directories", []):
            full_path = base / dir_path
            success, msg = self.create_directory(str(full_path))
            results.append(msg)
        
        # Create files
        for file_info in plan.get("structure", {}).get("files", []):
            if isinstance(file_info, dict):
                file_path = file_info.get("path", "")
                purpose = file_info.get("purpose", "")
                content_hint = file_info.get("content_hint", "")
            else:
                file_path = str(file_info)
                purpose = ""
                content_hint = ""
            
            if file_path:
                full_path = base / file_path
                content = file_info.get("content", "") if isinstance(file_info, dict) else ""
                success, msg = self.create_file(str(full_path), content, purpose or content_hint)
                results.append(msg)
        
        return results


class RefactorAgent:
    """Modifies existing code intelligently"""
    
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
    
    def refactor_file(self, file_path: str, instruction: str) -> Tuple[bool, str]:
        """Refactor a file based on instruction"""
        # Read current file
        fs_agent = FileSystemAgent(self.ai_engine)
        success, current_content = fs_agent.read_file(file_path)
        
        if not success:
            return False, current_content
        
        # Generate refactored content
        system_prompt = """You are a code refactoring expert. Modify code according to instructions while preserving functionality.

Rules:
- Keep the same functionality
- Improve code quality
- Follow best practices
- Maintain existing structure where possible
- Add comments if helpful

Return ONLY the refactored code, no explanations."""
        
        prompt = f"""Refactor this code:

File: {file_path}
Instruction: {instruction}

Current code:
```python
{current_content}
```

Return the refactored code."""
        
        refactored = self.ai_engine.query_groq(system_prompt, prompt)
        refactored = re.sub(r'```[\w]*\n?', '', refactored)
        refactored = refactored.strip()
        
        # Write back
        success, msg = fs_agent.write_file(file_path, refactored)
        return success, msg if success else f"❌ Refactoring failed: {msg}"
    
    def change_framework(self, project_path: str, from_framework: str, to_framework: str) -> List[str]:
        """Change project framework (e.g., Flask to FastAPI)"""
        results = []
        project = Path(project_path)
        
        # This is a complex operation - use AI to plan and execute
        system_prompt = """You are a framework migration expert. Help migrate code from one framework to another.

Analyze the code and provide migration steps."""
        
        # Find all Python files
        python_files = list(project.rglob("*.py"))
        
        for py_file in python_files:
            if py_file.name.startswith("__"):
                continue
            
            success, content = FileSystemAgent(self.ai_engine).read_file(str(py_file))
            if not success:
                continue
            
            prompt = f"""Migrate this {from_framework} code to {to_framework}:

{content}

Return the migrated code."""
            
            migrated = self.ai_engine.query_groq(system_prompt, prompt)
            migrated = re.sub(r'```[\w]*\n?', '', migrated)
            
            success, msg = FileSystemAgent(self.ai_engine).write_file(str(py_file), migrated.strip())
            results.append(msg)
        
        # Update dependencies
        req_file = project / "requirements.txt"
        if req_file.exists():
            success, content = FileSystemAgent(self.ai_engine).read_file(str(req_file))
            if success:
                content = content.replace(from_framework.lower(), to_framework.lower())
                FileSystemAgent(self.ai_engine).write_file(str(req_file), content)
                results.append(f"✅ Updated requirements.txt")
        
        return results
    
    def fix_bug(self, file_path: str, bug_description: str) -> Tuple[bool, str]:
        """Fix a bug in a file"""
        fs_agent = FileSystemAgent(self.ai_engine)
        success, content = fs_agent.read_file(file_path)
        
        if not success:
            return False, content
        
        system_prompt = """You are a debugging expert. Fix bugs in code while preserving functionality.

Analyze the bug description, find the issue, and fix it.
Return ONLY the fixed code."""
        
        prompt = f"""Fix this bug:

File: {file_path}
Bug: {bug_description}

Code:
```python
{content}
```

Return the fixed code."""
        
        fixed = self.ai_engine.query_groq(system_prompt, prompt)
        fixed = re.sub(r'```[\w]*\n?', '', fixed)
        
        success, msg = fs_agent.write_file(file_path, fixed.strip())
        return success, msg if success else f"❌ Bug fix failed: {msg}"


class ReviewerAgent:
    """Checks correctness of code"""
    
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
    
    def review_file(self, file_path: str) -> Dict:
        """Review a file for correctness"""
        fs_agent = FileSystemAgent(self.ai_engine)
        success, content = fs_agent.read_file(file_path)
        
        if not success:
            return {"valid": False, "errors": [content], "warnings": [], "suggestions": []}
        
        system_prompt = """You are a code reviewer. Check code for:
1. Syntax errors
2. Logic errors
3. Best practices
4. Potential bugs
5. Code quality

Return JSON:
{
    "valid": true/false,
    "errors": ["error1", "error2"],
    "warnings": ["warning1"],
    "suggestions": ["suggestion1"]
}"""
        
        prompt = f"""Review this code:

File: {file_path}
```python
{content}
```

Check for errors, warnings, and provide suggestions. Return ONLY valid JSON."""
        
        response = self.ai_engine.query_groq(system_prompt, prompt)
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Basic syntax check
        if file_path.endswith(".py"):
            try:
                ast.parse(content)
                return {"valid": True, "errors": [], "warnings": [], "suggestions": []}
            except SyntaxError as e:
                return {"valid": False, "errors": [str(e)], "warnings": [], "suggestions": []}
        
        return {"valid": True, "errors": [], "warnings": [], "suggestions": []}
    
    def review_project(self, project_path: str) -> Dict:
        """Review entire project"""
        project = Path(project_path)
        results = {
            "files_reviewed": 0,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Review Python files
        for py_file in project.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            review = self.review_file(str(py_file))
            results["files_reviewed"] += 1
            results["errors"].extend([f"{py_file}: {e}" for e in review.get("errors", [])])
            results["warnings"].extend([f"{py_file}: {w}" for w in review.get("warnings", [])])
            results["suggestions"].extend([f"{py_file}: {s}" for s in review.get("suggestions", [])])
        
        return results


class ProjectOrchestrator:
    """Main orchestrator coordinating all agents"""
    
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
        self.memory = MemoryAgent()
        self.planner = PlannerAgent(ai_engine)
        self.filesystem = FileSystemAgent(ai_engine)
        self.refactor = RefactorAgent(ai_engine)
        self.reviewer = ReviewerAgent(ai_engine)
    
    def is_project_task(self, user_input: str) -> bool:
        """Detect if this is a project-related task"""
        project_keywords = [
            "create project", "build project", "new project", "full project",
            "add", "change", "refactor", "fix bug", "migrate", "convert",
            "login page", "backend", "frontend", "api", "framework",
            "folder structure", "restructure"
        ]
        
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in project_keywords)
    
    def handle_project_request(self, user_input: str, base_path: str = ".") -> str:
        """Handle a project-related request"""
        base = Path(base_path).resolve()
        
        # Check if this is a new project or modification
        is_new_project = any(phrase in user_input.lower() for phrase in [
            "create", "build", "new project", "full project", "make a project"
        ])
        
        if is_new_project:
            return self._create_new_project(user_input, base)
        else:
            return self._modify_existing_project(user_input, base)
    
    def _create_new_project(self, user_input: str, base_path: Path) -> str:
        """Create a new project"""
        # Ask clarifying questions if needed
        questions = self._needs_clarification(user_input)
        if questions:
            return f"🤔 I need some clarification:\n" + "\n".join(f"- {q}" for q in questions)
        
        # Create plan
        plan = self.planner.create_plan(user_input)
        project_name = plan.get("project_name", "new_project")
        
        # Execute plan
        results = self.filesystem.execute_plan(plan, str(base_path))
        
        # Scan and save structure
        structure = self.memory.scan_project_structure(str(base_path))
        self.memory.register_project(project_name, str(base_path), structure)
        
        # Review created files
        review_summary = self._review_created_files(base_path)
        
        # Create summary
        summary = f"""✅ Project '{project_name}' created successfully!

📁 Location: {base_path}
📋 Plan: {plan.get('description', 'N/A')}
🔧 Tech Stack: {plan.get('tech_stack', {})}

Results:
{chr(10).join(results)}

{review_summary}"""
        
        return summary
    
    def _modify_existing_project(self, user_input: str, base_path: Path) -> str:
        """Modify an existing project"""
        # Detect modification type
        if "refactor" in user_input.lower() or "restructure" in user_input.lower():
            return self._refactor_project(user_input, base_path)
        elif "fix bug" in user_input.lower() or "bug in" in user_input.lower():
            return self._fix_bug_in_project(user_input, base_path)
        elif any(fw in user_input.lower() for fw in ["flask", "fastapi", "django", "express"]):
            return self._change_framework(user_input, base_path)
        elif "add" in user_input.lower() or "create" in user_input.lower():
            return self._add_feature(user_input, base_path)
        else:
            # Generic modification
            structure = self.memory.scan_project_structure(str(base_path))
            modification_plan = self.planner.plan_modification(user_input, structure)
            
            results = []
            for action in modification_plan.get("actions", []):
                action_type = action.get("action")
                target = action.get("target")
                
                if action_type == "create":
                    success, msg = self.filesystem.create_file(target, purpose=action.get("description", ""))
                    results.append(msg)
                elif action_type == "modify":
                    success, msg = self.refactor.refactor_file(target, action.get("description", ""))
                    results.append(msg)
                elif action_type == "delete":
                    success, msg = self.filesystem.delete_file(target)
                    results.append(msg)
            
            return f"✅ Modification complete:\n" + "\n".join(results)
    
    def _refactor_project(self, user_input: str, base_path: Path) -> str:
        """Refactor project structure"""
        # Extract target from user input
        if "folder structure" in user_input.lower() or "restructure" in user_input.lower():
            # This would require more complex logic
            return "🔄 Refactoring project structure... (Feature in development)"
        else:
            # Refactor specific files
            structure = self.memory.scan_project_structure(str(base_path))
            modification_plan = self.planner.plan_modification(user_input, structure)
            
            results = []
            for action in modification_plan.get("actions", []):
                if action.get("action") == "refactor":
                    success, msg = self.refactor.refactor_file(
                        action.get("target"),
                        action.get("description", "")
                    )
                    results.append(msg)
            
            return f"✅ Refactoring complete:\n" + "\n".join(results)
    
    def _fix_bug_in_project(self, user_input: str, base_path: Path) -> str:
        """Fix a bug in the project"""
        # Extract file and bug description
        # Simple heuristic: look for file names
        files = list(base_path.rglob("*.py"))
        
        # Try to find the file mentioned
        bug_file = None
        for f in files:
            if any(word in f.name.lower() for word in user_input.lower().split()):
                bug_file = f
                break
        
        if not bug_file and files:
            # Use first Python file as fallback
            bug_file = files[0]
        
        if bug_file:
            success, msg = self.refactor.fix_bug(str(bug_file), user_input)
            return msg
        else:
            return "❌ Could not find file to fix. Please specify the file name."
    
    def _change_framework(self, user_input: str, base_path: Path) -> str:
        """Change project framework"""
        # Detect from/to frameworks
        from_fw = None
        to_fw = None
        
        frameworks = ["flask", "fastapi", "django", "express", "react"]
        for fw in frameworks:
            if fw in user_input.lower():
                if not from_fw:
                    from_fw = fw
                else:
                    to_fw = fw
        
        if not to_fw:
            # Default: assume changing to mentioned framework
            if "fastapi" in user_input.lower():
                to_fw = "fastapi"
                from_fw = "flask"  # Common migration
            elif "flask" in user_input.lower():
                to_fw = "flask"
                from_fw = "fastapi"
        
        if from_fw and to_fw:
            results = self.refactor.change_framework(str(base_path), from_fw, to_fw)
            return f"✅ Migrated from {from_fw} to {to_fw}:\n" + "\n".join(results)
        else:
            return "❌ Could not determine frameworks. Please specify 'from X to Y'."
    
    def _add_feature(self, user_input: str, base_path: Path) -> str:
        """Add a feature to existing project"""
        structure = self.memory.scan_project_structure(str(base_path))
        modification_plan = self.planner.plan_modification(user_input, structure)
        
        results = []
        for action in modification_plan.get("actions", []):
            if action.get("action") == "create":
                success, msg = self.filesystem.create_file(
                    action.get("target"),
                    purpose=action.get("description", "")
                )
                results.append(msg)
        
        return f"✅ Feature added:\n" + "\n".join(results)
    
    def _needs_clarification(self, user_input: str) -> List[str]:
        """Check if clarification is needed"""
        # Simple heuristic - can be enhanced
        if len(user_input.split()) < 5:
            return ["What type of project? (web app, API, CLI, etc.)"]
        return []
    
    def _review_created_files(self, base_path: Path) -> str:
        """Review newly created files"""
        review = self.reviewer.review_project(str(base_path))
        
        if review["errors"]:
            return f"⚠️ Review found {len(review['errors'])} errors. Please check the files."
        elif review["warnings"]:
            return f"ℹ️ Review found {len(review['warnings'])} warnings."
        else:
            return "✅ Code review passed - no issues found!"








