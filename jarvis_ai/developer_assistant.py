"""
Developer assistant utilities for project analysis, code search, snippets, and memory.
"""
import ast
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from jarvis_ai.config import Config

logger = logging.getLogger(__name__)


class DeveloperMemory:
    """Persist developer-specific preferences and project notes."""

    def __init__(self):
        self.path = Config.DEVELOPER_MEMORY_FILE
        self.data = {
            "project_conventions": [],
            "preferred_commands": [],
            "recurring_fixes": [],
            "run_notes": [],
        }
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
        except Exception as exc:
            logger.warning(f"Failed to load developer memory: {exc}")

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save developer memory: {exc}")

    def remember(self, category: str, note: str) -> str:
        category = category if category in self.data else "project_conventions"
        note = note.strip()
        if not note:
            return "❌ No memory note provided"
        if note not in self.data[category]:
            self.data[category].append(note)
            self.save()
        return f"🧠 Remembered in {category}: {note}"

    def recall(self, category: Optional[str] = None) -> str:
        if category and category in self.data:
            items = self.data[category]
            if not items:
                return f"No developer memory stored for {category}."
            return f"🧠 {category}:\n" + "\n".join(f"  • {item}" for item in items[-10:])

        lines = ["🧠 Developer Memory:"]
        for key, items in self.data.items():
            if items:
                lines.append(f"{key}:")
                lines.extend(f"  • {item}" for item in items[-5:])
        return "\n".join(lines) if len(lines) > 1 else "No developer memory stored yet."


class DeveloperAssistant:
    """Project-aware developer helper."""

    TEXT_EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt",
        ".html", ".css", ".scss", ".yml", ".yaml", ".toml", ".ini",
        ".sh", ".env", ".java", ".go", ".rs",
    }
    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}

    def __init__(self):
        self.memory = DeveloperMemory()

    def _iter_text_files(self, base_path: str):
        base = Path(base_path).expanduser().resolve()
        if not base.exists():
            return
        for path in base.rglob("*"):
            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in self.TEXT_EXTENSIONS:
                yield path

    def detect_project_type(self, base_path: str = ".") -> Dict[str, object]:
        base = Path(base_path).expanduser().resolve()
        result = {
            "path": str(base),
            "language": "unknown",
            "framework": "unknown",
            "project_type": "generic",
        }
        if not base.exists():
            return result

        package_json = base / "package.json"
        requirements = base / "requirements.txt"
        pyproject = base / "pyproject.toml"

        if package_json.exists():
            result["language"] = "javascript"
            result["project_type"] = "node"
            try:
                with open(package_json, "r", encoding="utf-8") as handle:
                    pkg = json.load(handle)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    result["framework"] = "react"
                    result["project_type"] = "frontend"
                elif "next" in deps:
                    result["framework"] = "nextjs"
                    result["project_type"] = "fullstack"
                elif "express" in deps:
                    result["framework"] = "express"
                    result["project_type"] = "api"
            except Exception:
                pass

        if requirements.exists() or pyproject.exists():
            result["language"] = "python"
            result["project_type"] = "python"
            text = ""
            try:
                if requirements.exists():
                    text += requirements.read_text(encoding="utf-8", errors="ignore")
                if pyproject.exists():
                    text += "\n" + pyproject.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
            lowered = text.lower()
            if "fastapi" in lowered:
                result["framework"] = "fastapi"
                result["project_type"] = "api"
            elif "flask" in lowered:
                result["framework"] = "flask"
                result["project_type"] = "web"
            elif "django" in lowered:
                result["framework"] = "django"
                result["project_type"] = "web"

        return result

    def _find_route_files(self, base_path: str) -> List[str]:
        hits = []
        route_patterns = [
            r"@app\.(get|post|put|delete|route)",
            r"APIRouter",
            r"router\.(get|post|put|delete)",
            r"express\(",
            r"app\.(get|post|put|delete)\(",
        ]
        for path in self._iter_text_files(base_path):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if any(re.search(pattern, text) for pattern in route_patterns):
                hits.append(str(path))
        return hits[:10]

    def _find_auth_files(self, base_path: str) -> List[str]:
        hits = []
        auth_tokens = ("auth", "login", "signup", "jwt", "session", "passport", "oauth")
        for path in self._iter_text_files(base_path):
            lowered = path.name.lower()
            if any(token in lowered for token in auth_tokens):
                hits.append(str(path))
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            if any(token in text for token in auth_tokens):
                hits.append(str(path))
        return hits[:10]

    def suggest_files_to_edit(self, request: str, base_path: str = ".") -> List[str]:
        query_terms = [term for term in re.findall(r"[a-zA-Z_]{3,}", request.lower()) if term not in {"please", "create", "change", "update"}]
        scored = Counter()
        for path in self._iter_text_files(base_path):
            score = 0
            lowered_name = path.name.lower()
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                text = ""
            for term in query_terms:
                if term in lowered_name:
                    score += 5
                if term in text:
                    score += min(3, text.count(term))
            if score:
                scored[str(path)] += score
        return [path for path, _ in scored.most_common(8)]

    def _collect_project_stats(self, base_path: str) -> Dict[str, object]:
        base = Path(base_path).expanduser().resolve()
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "top_extensions": [],
            "largest_files": [],
            "entry_files": [],
        }
        if not base.exists():
            return stats

        extension_counter = Counter()
        largest_files = []

        for path in base.rglob("*"):
            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue
            if path.is_dir():
                stats["total_dirs"] += 1
                continue
            if not path.is_file():
                continue

            stats["total_files"] += 1
            extension = path.suffix.lower() or "<no_ext>"
            extension_counter[extension] += 1

            try:
                size = path.stat().st_size
            except Exception:
                size = 0
            largest_files.append((size, str(path)))

        stats["top_extensions"] = extension_counter.most_common(6)
        stats["largest_files"] = [path for _, path in sorted(largest_files, reverse=True)[:5]]

        common_entry_files = [
            "main.py",
            "app.py",
            "server.py",
            "manage.py",
            "index.js",
            "index.ts",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "README.md",
        ]
        stats["entry_files"] = [
            str(base / name) for name in common_entry_files if (base / name).exists()
        ][:6]
        return stats

    def analyze_project(self, base_path: str = ".", request: str = "") -> str:
        info = self.detect_project_type(base_path)
        stats = self._collect_project_stats(base_path)
        route_files = self._find_route_files(base_path)
        auth_files = self._find_auth_files(base_path)
        suggestions = self.suggest_files_to_edit(request, base_path) if request else []

        lines = [
            "🛠️ Project Analysis:",
            f"Path: {info['path']}",
            f"Language: {info['language']}",
            f"Framework: {info['framework']}",
            f"Project Type: {info['project_type']}",
            f"Directories: {stats['total_dirs']}",
            f"Files: {stats['total_files']}",
        ]
        if stats["top_extensions"]:
            ext_summary = ", ".join(f"{ext} ({count})" for ext, count in stats["top_extensions"])
            lines.append(f"Top file types: {ext_summary}")
        if stats["entry_files"]:
            lines.append("Likely entry files:")
            lines.extend(f"  • {item}" for item in stats["entry_files"])
        if auth_files:
            lines.append("Auth-related files:")
            lines.extend(f"  • {item}" for item in auth_files[:5])
        if route_files:
            lines.append("Route/API files:")
            lines.extend(f"  • {item}" for item in route_files[:5])
        if stats["largest_files"]:
            lines.append("Largest files:")
            lines.extend(f"  • {item}" for item in stats["largest_files"][:3])
        if suggestions:
            lines.append("Suggested files to edit:")
            lines.extend(f"  • {item}" for item in suggestions[:5])
        return "\n".join(lines)

    def search_code(self, query: str, base_path: str = ".") -> str:
        if not query:
            return "❌ No code search query provided"
        matches = []
        for path in self._iter_text_files(base_path):
            try:
                for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                    if query.lower() in line.lower():
                        matches.append(f"{path}:{lineno}: {line.strip()[:160]}")
                        if len(matches) >= 25:
                            break
            except Exception:
                continue
            if len(matches) >= 25:
                break
        if not matches:
            return f"🔍 No code matches found for '{query}'"
        return f"🔍 Code matches for '{query}':\n" + "\n".join(matches)

    def find_symbol(self, symbol: str, base_path: str = ".") -> str:
        if not symbol:
            return "❌ No symbol provided"
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
        matches = []
        for path in self._iter_text_files(base_path):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for lineno, line in enumerate(lines, start=1):
                if pattern.search(line):
                    matches.append(f"{path}:{lineno}: {line.strip()[:160]}")
                    if len(matches) >= 25:
                        break
            if len(matches) >= 25:
                break
        if not matches:
            return f"🔎 Symbol '{symbol}' not found"
        return f"🔎 Symbol references for '{symbol}':\n" + "\n".join(matches)

    def list_todos(self, base_path: str = ".") -> str:
        matches = []
        for path in self._iter_text_files(base_path):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for lineno, line in enumerate(lines, start=1):
                if "todo" in line.lower() or "fixme" in line.lower():
                    matches.append(f"{path}:{lineno}: {line.strip()[:160]}")
        if not matches:
            return "✅ No TODO or FIXME markers found"
        return "📝 TODO/FIXME items:\n" + "\n".join(matches[:50])

    def find_dead_code_candidates(self, base_path: str = ".") -> str:
        definitions = []
        references = Counter()

        for path in self._iter_text_files(base_path):
            if path.suffix != ".py":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(text)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    definitions.append((node.name, str(path), getattr(node, "lineno", 1)))

            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text):
                references[token] += 1

        candidates = []
        for name, path, lineno in definitions:
            if references[name] <= 1 and not name.startswith("_"):
                candidates.append(f"{path}:{lineno}: {name}")

        if not candidates:
            return "✅ No obvious dead-code candidates found"
        return "🧹 Possible dead-code candidates:\n" + "\n".join(candidates[:25])

    def generate_snippet(self, snippet_type: str, name: str = "Example", framework: str = "") -> str:
        kind = (snippet_type or "").strip().lower()
        safe_name = re.sub(r"[^A-Za-z0-9_]", "", name) or "Example"
        component_name = safe_name[:1].upper() + safe_name[1:]

        snippets = {
            "react_component": f"""import './{component_name}.css';

export default function {component_name}() {{
  return (
    <section className="{safe_name.lower()}">
      <h1>{component_name}</h1>
    </section>
  );
}}
""",
            "fastapi_route": f"""from fastapi import APIRouter

router = APIRouter()

@router.get("/{safe_name.lower()}")
async def get_{safe_name.lower()}():
    return {{"name": "{component_name}"}} 
""",
            "flask_route": f"""from flask import Blueprint, jsonify

bp = Blueprint("{safe_name.lower()}", __name__)

@bp.get("/{safe_name.lower()}")
def get_{safe_name.lower()}():
    return jsonify({{"name": "{component_name}"}})
""",
            "test_file": f"""def test_{safe_name.lower()}():
    assert True
""",
            "plugin_template": f"""def register(plugin_manager):
    def handle_{safe_name.lower()}(obj, ai_engine=None, user_input=""):
        return "✅ {component_name} plugin executed"

    plugin_manager.register_command("{safe_name.lower()}", handle_{safe_name.lower()})
""",
            "cli_command": f"""import argparse


def main():
    parser = argparse.ArgumentParser(prog="{safe_name.lower()}")
    parser.add_argument("--name", default="{component_name}")
    args = parser.parse_args()
    print(f"Hello {{args.name}}")


if __name__ == "__main__":
    main()
""",
        }

        if kind not in snippets:
            supported = ", ".join(sorted(snippets))
            return f"❌ Unsupported snippet type. Try: {supported}"
        detail = f" ({framework})" if framework else ""
        return f"🧩 Generated {kind}{detail}:\n\n{snippets[kind]}"
