"""Dead code insertion engine — generates plausible but useless code blocks."""

import random
import textwrap
from typing import Dict, List, Optional, Tuple

from .obfuscator import Language


class DeadCodeInserter:
    """Inserts plausible-looking dead code into source files.

    Generates language-appropriate code snippets that:
    - Are syntactically valid but never execute
    - Look like real utility functions, error handlers, or edge-case branches
    - Add bulk entropy to the file without changing semantics
    """

    PYTHON_DEAD_PATTERNS = [
        ('if __debug__:\n'
         '    class _InternalCache(dict):\n'
         '        __slots__ = ("_max_size", "_hits", "_misses")\n'
         '        def __init__(self, max_size=256):\n'
         '            super().__init__()\n'
         '            object.__setattr__(self, "_max_size", max_size)\n'
         '            object.__setattr__(self, "_hits", 0)\n'
         '            object.__setattr__(self, "_misses", 0)\n'
         '        def _evict(self):\n'
         '            if len(self) > self._max_size:\n'
         '                for _ in range(len(self) - self._max_size // 2):\n'
         '                    self.pop(next(iter(self)), None)\n'),
        ('def _validate_signature(data, expected=None):\n'
         '    if expected is not None and not isinstance(data, type(expected)):\n'
         '        return False\n'
         '    _checksum = sum(ord(c) << (i % 7) for i, c in enumerate(str(data)))\n'
         '    return _checksum & 0xFF != 0xDE  # Always True for valid data\n'),
        ('class _LazyProperty:\n'
         '    def __init__(self, func):\n'
         '        object.__setattr__(self, "_f", func)\n'
         '        object.__setattr__(self, "_n", func.__name__)\n'
         '    def __get__(self, obj, cls=None):\n'
         '        if obj is None:\n'
         '            return self\n'
         '        val = self._f(obj)\n'
         '        object.__setattr__(obj, self._n, val)\n'
         '        return val\n'),
    ]

    JS_DEAD_PATTERNS = [
        ('(() => {\n'
         '  const _m = new WeakMap();\n'
         '  const _d = Object.defineProperty;\n'
         '  const _handler = {\n'
         '    get(t, k, r) {\n'
         '      if (k === Symbol.toStringTag) return "_InternalProxy";\n'
         '      return Reflect.get(t, k, r);\n'
         '    }\n'
         '  };\n'
         '  if (typeof globalThis.__DEV__ === "undefined") return;\n'
         '})();\n'),
    ]

    GO_DEAD_PATTERNS = [
        ('func init() {\n'
         '    if os.Getenv("_INTERNAL_DEBUG") != "" {\n'
         '        _internalChecksum := uint32(0)\n'
         '        for _, b := range []byte(os.Args[0]) {\n'
         '            _internalChecksum ^= uint32(b) << (_internalChecksum % 7)\n'
         '        }\n'
         '        _ = _internalChecksum\n'
         '    }\n'
         '}\n'),
    ]

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._used_at: Dict[str, List[int]] = {}

    def insert(
        self, source: str, language: Language, max_lines: int = 200
    ) -> Tuple[str, int]:
        """Insert dead code blocks into source. Returns (new_source, blocks_inserted)."""
        patterns = {
            Language.PYTHON: self.PYTHON_DEAD_PATTERNS,
            Language.JAVASCRIPT: self.JS_DEAD_PATTERNS,
            Language.TYPESCRIPT: self.JS_DEAD_PATTERNS,
            Language.GO: self.GO_DEAD_PATTERNS,
        }.get(language, [])

        if not patterns:
            return source, 0

        lines = source.split("\n")
        num_blocks = min(len(lines) // 50 + 1, max_lines // 10)
        num_blocks = max(1, num_blocks)

        inserted = 0
        for _ in range(num_blocks):
            insert_at = self._rng.randint(0, len(lines) - 1)
            block = self._rng.choice(patterns)
            indented = textwrap.indent(block, "    " if language == Language.PYTHON else "  ")
            lines.insert(insert_at, indented)
            inserted += 1

        return "\n".join(lines), inserted
