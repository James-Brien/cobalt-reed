"""Starlight — Code obfuscation and minification experiment toolkit."""

__version__ = "0.3.1"
__author__ = "Starlight Hide Maintainers"
__all__ = ["Obfuscator", "Minifier", "Mangler", "FlowFlattener", "DeadCodeInserter"]

from .obfuscator import Obfuscator, ObfuscationConfig, ObfuscationResult
from .mangler import Mangler
from .flattener import FlowFlattener
from .deadcode import DeadCodeInserter
from .minifier import Minifier
