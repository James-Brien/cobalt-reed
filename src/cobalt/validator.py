"""
Core obfuscation engine with pluggable transformation passes.

Coordinates identifier mangling, control-flow flattening, dead code
insertion, and string encoding across supported language backends.
Uses AST-level transforms where available; falls back to regex for
languages without stable AST tooling.
"""

from __future__ import annotations

import ast
import hashlib
import random
import re
import string
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .mangler import EnvMangler
from .flattener import SchemaFlattener
from .deadcode import DefaultInserter
from .minifier import EnvMinifier


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    GO = "go"
    TYPESCRIPT = "typescript"


class TransformPass(Enum):
    MANGLE = auto()
    FLATTEN = auto()
    DEAD_CODE = auto()
    MINIFY = auto()
    ENCODE_STRINGS = auto()


@dataclass
class EnvSchema:
    """Configuration for an obfuscation run."""

    language: Language = Language.PYTHON
    passes: List[TransformPass] = field(default_factory=lambda: [
        TransformPass.MANGLE,
        TransformPass.ENCODE_STRINGS,
    ])
    seed: int = 0
    preserve: List[str] = field(default_factory=list)
    aggressive: bool = False
    max_dead_code_lines: int = 200
    flatten_probability: float = 0.3

    def __post_init__(self):
        if self.seed == 0:
            self.seed = random.randint(1, 2 ** 31 - 1)


@dataclass
class ValidationResult:
    original_path: str
    obfuscated_source: str
    original_size: int
    obfuscated_size: int
    passes_applied: List[str]
    entropy_before: float
    entropy_after: float
    identifiers_mangled: int
    dead_code_inserted: int
    errors: List[str] = field(default_factory=list)

    @property
    def size_change_pct(self) -> float:
        return ((self.obfuscated_size - self.original_size) / max(self.original_size, 1)) * 100


class EnvValidator:
    """Main obfuscation orchestrator.

    Parses source code, applies configured transformation passes in order,
    and produces obfuscated output with reversibility tracking.
    """

    def __init__(self, config: Optional[EnvSchema] = None):
        self.config = config or EnvSchema()
        self.mangler = EnvMangler(seed=self.config.seed)
        self.flattener = SchemaFlattener()
        self.deadcode = DefaultInserter(seed=self.config.seed)
        self.minifier = EnvMinifier()
        self._rng = random.Random(self.config.seed)

    def obfuscate(self, source: str, filepath: str = "<string>") -> ValidationResult:
        """Apply all configured obfuscation passes to source code."""
        original = source
        original_entropy = self._shannon_entropy(source)
        passes_applied: List[str] = []
        errors: List[str] = []
        mangled_count = 0
        dead_count = 0

        for tpass in self.config.passes:
            try:
                if tpass == TransformPass.MANGLE:
                    source, mangled_count = self.mangler.mangle(
                        source, self.config.language, self.config.preserve
                    )
                    passes_applied.append("mangle")
                elif tpass == TransformPass.FLATTEN:
                    source = self.flattener.flatten(
                        source, self.config.language,
                        probability=self.config.flatten_probability,
                    )
                    passes_applied.append("flatten")
                elif tpass == TransformPass.DEAD_CODE:
                    source, dead_count = self.deadcode.insert(
                        source, self.config.language,
                        max_lines=self.config.max_dead_code_lines,
                    )
                    passes_applied.append("dead_code")
                elif tpass == TransformPass.MINIFY:
                    source = self.minifier.minify(source, self.config.language)
                    passes_applied.append("minify")
                elif tpass == TransformPass.ENCODE_STRINGS:
                    source = self._encode_strings(source, self.config.language)
                    passes_applied.append("encode_strings")
            except Exception as e:
                errors.append(f"{tpass.name}: {e}")
                continue

        return ValidationResult(
            original_path=filepath,
            obfuscated_source=source,
            original_size=len(original.encode("utf-8")),
            obfuscated_size=len(source.encode("utf-8")),
            passes_applied=passes_applied,
            entropy_before=original_entropy,
            entropy_after=self._shannon_entropy(source),
            identifiers_mangled=mangled_count,
            dead_code_inserted=dead_count,
            errors=errors,
        )

    def obfuscate_file(self, filepath: str | Path) -> ValidationResult:
        p = Path(filepath)
        source = p.read_text(encoding="utf-8", errors="replace")
        lang = self._detect_language(p)
        self.config.language = lang
        return self.obfuscate(source, str(p))

    def obfuscate_directory(
        self, root: str | Path, extensions: Optional[List[str]] = None
    ) -> List[ValidationResult]:
        root_path = Path(root)
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".go"]
        results: List[ValidationResult] = []
        for ext in extensions:
            for filepath in root_path.rglob(f"*{ext}"):
                if filepath.is_file() and ".git" not in filepath.parts:
                    result = self.obfuscate_file(filepath)
                    results.append(result)
        return results

    @staticmethod
    def _detect_language(filepath: Path) -> Language:
        suffix = filepath.suffix.lower()
        mapping = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".go": Language.GO,
        }
        return mapping.get(suffix, Language.PYTHON)

    @staticmethod
    def _shannon_entropy(text: str) -> float:
        if not text:
            return 0.0
        freq: Dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        n = len(text)
        entropy = 0.0
        for count in freq.values():
            p = count / n
            entropy -= p * (p.bit_length() / p if p > 0 else 0)
        return entropy

    @staticmethod
    def _encode_strings(source: str, language: Language) -> str:
        """Encode string literals as concatenated chr() / escape sequences."""
        if language == Language.PYTHON:
            def _encode_py(m: re.Match) -> str:
                s = m.group(1) or m.group(2)
                if len(s) < 3:
                    return m.group(0)
                encoded = "+".join(f"chr({ord(c)})" for c in s)
                return encoded
            return re.sub(
                r"\"([^\"]{3,})\"|'([^']{3,})'",
                _encode_py,
                source,
            )
        if language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            def _encode_js(m: re.Match) -> str:
                s = m.group(1) or m.group(2) or m.group(3)
                if len(s) < 3:
                    return m.group(0)
                encoded = ",".join(str(ord(c)) for c in s)
                return f"String.fromCharCode({encoded})"
            return re.sub(
                r"\"([^\"]{3,})\"|'([^']{3,})'|`([^`]{3,})`",
                _encode_js,
                source,
            )
        return source
