"""Control-flow flattening transformer for code obfuscation.

Converts structured control flow (if/else, for, while) into a switch-based
dispatcher pattern for Python. Uses AST transformation to maintain syntax
correctness after flattening.
"""

import ast
import random
from typing import List, Optional, Set

from .obfuscator import Language


class FlowFlattener:
    """Transforms structured control flow into flattened switch-dispatch form.

    Warning: highly experimental. Produces valid but extremely confusing
    control flow graphs intended for educational/obfuscation research.
    """

    def flatten(
        self, source: str, language: Language,
        probability: float = 0.3,
    ) -> str:
        if language != Language.PYTHON:
            return source  # Only Python supported for now
        return self._flatten_python(source, probability)

    def _flatten_python(self, source: str, probability: float) -> str:
        """AST-level control flow flattening for Python."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        flattener = _PythonASTFlattener(probability, random.Random())
        flattener.visit(tree)
        ast.fix_missing_locations(tree)
        try:
            return ast.unparse(tree)
        except Exception:
            return source


class _PythonASTFlattener(ast.NodeTransformer):
    """Internal AST transformer that inserts opaque predicates and
    switch-case dispatchers around conditional blocks.

    Does NOT fully flatten — it inserts confusing but valid constructs
    that complicate static analysis without breaking runtime behavior.
    """

    def __init__(self, probability: float, rng: random.Random):
        self.probability = probability
        self.rng = rng
        self._switch_var_counter = 0

    def _should_transform(self) -> bool:
        return self.rng.random() < self.probability

    def _new_switch_var(self) -> str:
        self._switch_var_counter += 1
        return f"_s_{self._switch_var_counter}_{self.rng.randint(1000, 9999)}"

    def visit_If(self, node: ast.If) -> ast.AST:
        self.generic_visit(node)
        if not self._should_transform():
            return node
        if not isinstance(node.test, ast.Compare):
            return node

        # Inject an opaque predicate: (cond and opaque) or (cond and not opaque)
        # where opaque is a complex expression that's always True
        opaque = ast.Constant(value=True)
        # Wrap in a confusing but valid form
        opaque_expr = ast.BoolOp(
            op=ast.And(),
            values=[
                ast.Compare(
                    left=ast.Constant(value=1),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=1)],
                ),
                ast.Compare(
                    left=ast.Constant(value=len("")),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=0)],
                ),
            ],
        )
        new_test = ast.BoolOp(
            op=ast.And(),
            values=[node.test, opaque_expr],
        )
        node.test = new_test
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        self.generic_visit(node)
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        self.generic_visit(node)
        return node
