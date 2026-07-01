"""Cobalt CLI — code obfuscation toolkit."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .validator import EnvValidator, EnvSchema, Language, TransformPass


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", stream=sys.stderr)


PASS_MAP = {
    "mangle": TransformPass.MANGLE,
    "flatten": TransformPass.FLATTEN,
    "deadcode": TransformPass.DEAD_CODE,
    "minify": TransformPass.MINIFY,
    "encodestrings": TransformPass.ENCODE_STRINGS,
}


@click.group()
@click.version_option(version=__version__, prog_name="cobalt")
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Cobalt — Code obfuscation and minification experiment toolkit."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-p", "--passes", default="mangle,encodestrings",
              help="Comma-separated transform passes")
@click.option("-s", "--seed", type=int, default=0,
              help="Random seed (0 = random)")
@click.option("-o", "--output", type=click.Path(), help="Output file")
@click.option("--aggressive", is_flag=True, help="Enable aggressive mode")
def obfuscate(filepath: str, passes: str, seed: int, output: Optional[str],
              aggressive: bool) -> None:
    """Obfuscate a source file."""
    pass_names = [p.strip().lower() for p in passes.split(",")]
    pass_list = [PASS_MAP[p] for p in pass_names if p in PASS_MAP]
    if not pass_list:
        click.echo(f"Invalid passes: {passes}. Valid: {list(PASS_MAP.keys())}", err=True)
        return

    config = EnvSchema(
        passes=pass_list, seed=seed, aggressive=aggressive,
        flatten_probability=0.5 if aggressive else 0.3,
        max_dead_code_lines=500 if aggressive else 200,
    )
    obf = EnvValidator(config=config)
    result = obf.obfuscate_file(filepath)

    if output:
        Path(output).write_text(result.obfuscated_source, encoding="utf-8")
        click.echo(f"Obfuscated output written to {output}")
    else:
        click.echo(result.obfuscated_source)

    click.echo(f"\n--- Stats ---", err=True)
    click.echo(f"Passes: {result.passes_applied}", err=True)
    click.echo(f"Size: {result.original_size:,} → {result.obfuscated_size:,} bytes "
               f"({result.size_change_pct:+.1f}%)", err=True)
    click.echo(f"Entropy: {result.entropy_before:.3f} → {result.entropy_after:.3f}", err=True)
    click.echo(f"Identifiers mangled: {result.identifiers_mangled}", err=True)
    click.echo(f"Dead code blocks: {result.dead_code_inserted}", err=True)
    if result.errors:
        click.echo(f"Errors: {result.errors}", err=True)


@main.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("-p", "--passes", default="mangle,encodestrings")
@click.option("-e", "--extensions", default=".py,.js,.ts,.go")
@click.option("-s", "--seed", type=int, default=0)
def batch(directory: str, passes: str, extensions: str, seed: int) -> None:
    """Obfuscate all source files in a directory."""
    pass_names = [p.strip().lower() for p in passes.split(",")]
    pass_list = [PASS_MAP[p] for p in pass_names if p in PASS_MAP]
    ext_list = [e.strip() for e in extensions.split(",")]

    config = EnvSchema(passes=pass_list, seed=seed)
    obf = EnvValidator(config=config)
    results = obf.obfuscate_directory(directory, extensions=ext_list)

    total_orig = sum(r.original_size for r in results)
    total_obf = sum(r.obfuscated_size for r in results)
    click.echo(f"Processed {len(results)} files")
    click.echo(f"Total size: {total_orig:,} → {total_obf:,} bytes "
               f"({(total_obf - total_orig) / max(total_orig, 1) * 100:+.1f}%)")


@main.command()
@click.option("-l", "--language", type=click.Choice(["python", "javascript", "go"]),
              default="python")
def info(language: str) -> None:
    """Show available transforms and info for a language."""
    lang = {"python": Language.PYTHON, "javascript": Language.JAVASCRIPT, "go": Language.GO}[language]
    click.echo(f"Language: {lang.value}")
    click.echo(f"Available passes:")
    for name, tpass in PASS_MAP.items():
        click.echo(f"  {name}")
    if language == "python":
        click.echo("  Supports: mangle, flatten (AST), deadcode, minify, encodestrings")
    elif language in ("javascript", "go"):
        click.echo("  Supports: mangle, deadcode, minify")


if __name__ == "__main__":
    main()
