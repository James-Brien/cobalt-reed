"""Identifier mangling engine — probabilistic renaming for obfuscation."""

import random
import re
import string
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .obfuscator import Language


@dataclass
class MangleResult:
    source: str
    mapping: Dict[str, str]
    count: int


class Mangler:
    """Probabilistic identifier shuffler for source code obfuscation.

    Generates valid but meaningless identifier names, maintains a mapping
    for reversibility (useful for debugging), and handles keyword/special
    method preservation.
    """

    PY_RESERVED = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
        "try", "while", "with", "yield",
    }
    GO_RESERVED = {
        "break", "case", "chan", "const", "continue", "default", "defer",
        "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
        "interface", "map", "package", "range", "return", "select", "struct",
        "switch", "type", "var",
    }
    JS_RESERVED = {
        "break", "case", "catch", "class", "const", "continue", "debugger",
        "default", "delete", "do", "else", "export", "extends", "finally",
        "for", "function", "if", "import", "in", "instanceof", "let",
        "new", "return", "super", "switch", "this", "throw", "try",
        "typeof", "var", "void", "while", "with", "yield", "async", "await",
    }

    # Special methods that should not be mangled (e.g., __init__, __str__)
    PY_DUNDER_RE = re.compile(r"^__\w+__$")
    GO_EXPORTED_RE = re.compile(r"^[A-Z]\w*$")  # Exported in Go, might break API
    JS_BUILTINS = {"window", "document", "console", "process", "global", "module"}

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._name_cache: Dict[str, str] = {}

    def mangle(
        self, source: str, language: Language, preserve: Optional[List[str]] = None
    ) -> Tuple[str, int]:
        """Mangle identifiers throughout the source, returning (new_source, count)."""
        preserve_set = set(preserve or [])
        if language == Language.PYTHON:
            return self._mangle_python(source, preserve_set)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            return self._mangle_javascript(source, preserve_set)
        elif language == Language.GO:
            return self._mangle_go(source, preserve_set)
        return source, 0

    def _mangle_python(self, source: str, preserve: Set[str]) -> Tuple[str, int]:
        """Mangle Python identifiers using token-aware approach."""
        import keyword as kw
        reserved = self.PY_RESERVED | set(kw.kwlist) | preserve
        identifier_re = re.compile(r'\b([a-zA-Z_]\w*)\b')
        seen: Dict[str, str] = {}
        mangle_count = 0

        def _replace(m: re.Match) -> str:
            nonlocal mangle_count
            name = m.group(1)
            if name in reserved or self.PY_DUNDER_RE.match(name):
                return name
            if name.startswith("_"):
                return name  # Preserve private/protected convention
            if name in seen:
                return seen[name]
            new_name = self._generate_name("py_", 12)
            seen[name] = new_name
            self._name_cache[name] = new_name
            mangle_count += 1
            return new_name

        result = identifier_re.sub(_replace, source)
        return result, mangle_count

    def _mangle_javascript(self, source: str, preserve: Set[str]) -> Tuple[str, int]:
        reserved = self.JS_RESERVED | self.JS_BUILTINS | preserve
        identifier_re = re.compile(r'(?<![.\"\'])\b([a-zA-Z_$][\w$]*)\b(?!\s*\()')
        seen: Dict[str, str] = {}
        mangle_count = 0

        def _replace(m: re.Match) -> str:
            nonlocal mangle_count
            name = m.group(1)
            if name in reserved or len(name) <= 1:
                return name
            if name in seen:
                return seen[name]
            new_name = self._generate_name("_", 10)
            seen[name] = new_name
            mangle_count += 1
            return new_name

        # Avoid mangling property accesses and import/require
        result = identifier_re.sub(_replace, source)
        return result, mangle_count

    def _mangle_go(self, source: str, preserve: Set[str]) -> Tuple[str, int]:
        reserved = self.GO_RESERVED | preserve
        mangle_count = 0
        seen: Dict[str, str] = {}

        def _replace(m: re.Match) -> str:
            nonlocal mangle_count
            name = m.group(1)
            if name in reserved or len(name) <= 1:
                return name
            if name[0].isupper() and self.GO_EXPORTED_RE.match(name):
                return name  # Preserve exported identifiers
            if name in seen:
                return seen[name]
            new_name = self._generate_name("g_", 10)
            seen[name] = new_name
            mangle_count += 1
            return new_name

        result = re.sub(r'\b([a-zA-Z_]\w*)\b', _replace, source)
        return result, mangle_count

    def _generate_name(self, prefix: str, length: int) -> str:
        chars = string.ascii_lowercase + string.digits
        suffix = "".join(self._rng.choice(chars) for _ in range(length - len(prefix)))
        return prefix + suffix

    def reverse(self, name: str) -> Optional[str]:
        """Look up the original name from mangled form. (reverse lookup)."""
        for orig, mangled in self._name_cache.items():
            if mangled == name:
                return orig
        return None

    @property
    def mapping(self) -> Dict[str, str]:
        return dict(self._name_cache)
