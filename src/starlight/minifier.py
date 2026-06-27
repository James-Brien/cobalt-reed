"""Basic minification pass: whitespace reduction, comment stripping."""

import re
from .obfuscator import Language


class Minifier:
    """Simple source code minification through whitespace and comment reduction."""

    def minify(self, source: str, language: Language) -> str:
        if language == Language.PYTHON:
            return self._minify_python(source)
        if language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            return self._minify_js(source)
        return source

    @staticmethod
    def _minify_python(source: str) -> str:
        lines = source.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.rstrip()
            if stripped.lstrip().startswith("#"):
                continue
            result.append(stripped)
        return "\n".join(result)

    @staticmethod
    def _minify_js(source: str) -> str:
        source = re.sub(r"//.*$", "", source, flags=re.MULTILINE)
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        lines = [l.rstrip() for l in source.split("\n") if l.strip()]
        return "\n".join(lines)
