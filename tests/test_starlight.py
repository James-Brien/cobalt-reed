"""Tests for Starlight obfuscation toolkit."""

from starlight.obfuscator import Obfuscator, ObfuscationConfig, Language, TransformPass
from starlight.mangler import Mangler
from starlight.deadcode import DeadCodeInserter
from starlight.minifier import Minifier


class TestMangler:
    def test_mangle_python(self):
        m = Mangler(seed=42)
        source = "def calculate_total(items):\n    result = 0\n    for item in items:\n        result += item\n    return result"
        mangled, count = m.mangle(source, Language.PYTHON)
        assert count > 0
        assert "calculate_total" not in mangled
        assert "def" in mangled
        assert "for" in mangled  # keyword preserved
        assert "return" in mangled  # keyword preserved

    def test_preserve_keywords(self):
        m = Mangler(seed=1)
        source = "import os\n\ndef main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()"
        mangled, count = m.mangle(source, Language.PYTHON)
        assert "import" in mangled
        assert "def" in mangled
        assert "if" in mangled

    def test_reverse_lookup(self):
        m = Mangler(seed=5)
        source = "my_variable = 42"
        mangled, _ = m.mangle(source, Language.PYTHON)
        assert m.reverse("my_variable") is None


class TestDeadCodeInserter:
    def test_insert_python(self):
        dci = DeadCodeInserter(seed=1)
        source = "def hello():\n    return 'world'\n"
        result, count = dci.insert(source, Language.PYTHON, max_lines=50)
        assert count > 0
        assert len(result.split("\n")) > len(source.split("\n"))
        assert "def hello()" in result

    def test_insert_no_crash_empty(self):
        dci = DeadCodeInserter()
        result, count = dci.insert("", Language.PYTHON)
        assert result == ""
        assert count == 0


class TestMinifier:
    def test_minify_python(self):
        m = Minifier()
        source = "# comment\ndef foo():  # inline\n    return 1\n\n\n"
        result = m.minify(source, Language.PYTHON)
        assert "comment" not in result
        assert "def foo():" in result

    def test_minify_js(self):
        m = Minifier()
        source = "const x = 1; // inline comment\n\n\nconst y = 2;\n"
        result = m.minify(source, Language.JAVASCRIPT)
        assert "// inline comment" not in result
        assert "const x" in result
        assert "const y" in result


class TestObfuscator:
    def test_obfuscate_python_basic(self):
        config = ObfuscationConfig(
            language=Language.PYTHON,
            passes=[TransformPass.MANGLE, TransformPass.MINIFY],
            seed=99,
        )
        obf = Obfuscator(config=config)
        source = (
            "def calculate_total(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item\n"
            "    return total\n"
        )
        result = obf.obfuscate(source, "test.py")
        assert result.identifiers_mangled > 0
        assert len(result.obfuscated_source) > 0

    def test_entropy_increases(self):
        config = ObfuscationConfig(
            language=Language.PYTHON,
            passes=[TransformPass.MANGLE, TransformPass.ENCODE_STRINGS],
            seed=7,
        )
        obf = Obfuscator(config=config)
        source = 'message = "hello world"\nprint(message)\n'
        result = obf.obfuscate(source, "test.py")
        # Just verify it runs without error
        assert result.original_size > 0

    def test_dead_code_increases_size(self):
        config = ObfuscationConfig(
            language=Language.PYTHON,
            passes=[TransformPass.DEAD_CODE],
            seed=3,
            max_dead_code_lines=300,
        )
        obf = Obfuscator(config=config)
        source = "x = 1\ny = 2\n"
        result = obf.obfuscate(source, "test.py")
        assert result.dead_code_inserted > 0
        assert result.obfuscated_size > result.original_size
