"""Local, read-only coding tools used by the Jarvis desktop control surface."""
from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess
from typing import Iterable


class JarvisCodingAssistant:
    """Provide safe workspace inspection and validation without network access."""

    IGNORED_DIRECTORIES = {".git", "__pycache__", ".venv", "venv", "node_modules"}

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def project_status(self) -> str:
        result = self._run(["git", "status", "--short"])
        if result is None:
            return "Git is not available in this workspace."
        return result or "Workspace is clean."

    def search(self, query: str, limit: int = 40) -> str:
        query = query.strip()
        if not query:
            return "Enter text to search for."

        matches = []
        query_lower = query.lower()
        for path in self._workspace_files():
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as source:
                    for line_number, line in enumerate(source, start=1):
                        if query_lower in line.lower():
                            relative = path.relative_to(self.workspace)
                            matches.append(f"{relative}:{line_number}: {line.strip()}")
                            if len(matches) >= limit:
                                return "\n".join(matches + [f"Showing first {limit} matches."])
            except OSError:
                continue
        return "\n".join(matches) if matches else f"No matches for: {query}"

    def validate_python(self) -> str:
        sources = list(self.workspace.rglob("*.py"))
        checked = 0
        errors = []
        for path in sources:
            if self._is_ignored(path):
                continue
            checked += 1
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(str(exc))

        if errors:
            return "Python validation failed:\n" + "\n".join(errors)
        return f"Python validation passed for {checked} files."

    def list_python_files(self, limit: int = 80) -> str:
        files = []
        for path in self.workspace.rglob("*.py"):
            if not self._is_ignored(path):
                files.append(str(path.relative_to(self.workspace)))
        files.sort()
        if len(files) > limit:
            files = files[:limit] + [f"Showing first {limit} Python files."]
        return "\n".join(files) or "No Python files found."

    def read_file(self, relative_path: str, max_lines: int = 80) -> str:
        try:
            path = (self.workspace / relative_path).resolve()
            path.relative_to(self.workspace)
        except (ValueError, OSError):
            return "Path must be inside the Jarvis workspace."

        if not path.is_file():
            return f"File not found: {relative_path}"
        try:
            with path.open("r", encoding="utf-8", errors="replace") as source:
                lines = source.readlines()[:max_lines]
        except OSError as exc:
            return f"Unable to read file: {exc}"
        return "".join(f"{index:>4}  {line}" for index, line in enumerate(lines, start=1))

    def _workspace_files(self) -> Iterable[Path]:
        for path in self.workspace.rglob("*"):
            if path.is_file() and not self._is_ignored(path):
                yield path

    def _is_ignored(self, path: Path) -> bool:
        return any(part in self.IGNORED_DIRECTORIES for part in path.parts)

    def _run(self, command: list[str]) -> str | None:
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return (completed.stdout or completed.stderr).strip()
