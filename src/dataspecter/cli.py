"""The `dataspecter` command: a thin layer over the public API."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dataspecter._version import __version__
from dataspecter.api import write
from dataspecter.errors import DataspecterError, SpecError
from dataspecter.spec import FORMATS, load_spec

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INVALID = 2  # also what argparse exits with on bad arguments


def _seed(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a non-negative integer, got {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be a non-negative integer, got {text!r}")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataspecter",
        description="Generate synthetic data from a YAML or JSON simulation spec.",
    )
    parser.add_argument("--version", action="version", version=f"dataspecter {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    generate = commands.add_parser(
        "generate",
        help="generate data and write one file per entity",
        description="Validate a spec, generate every entity and write one file per entity.",
    )
    generate.add_argument("spec", help="path to a .yaml, .yml or .json spec")
    generate.add_argument(
        "--out", metavar="DIR", help="output directory (default: the spec's output.dir, or output)"
    )
    generate.add_argument(
        "--format",
        choices=FORMATS,
        help="output format (default: the spec's output.format, or csv)",
    )
    generate.add_argument(
        "--seed", type=_seed, metavar="INTEGER", help="seed for the run (default: the spec's seed)"
    )

    validate = commands.add_parser(
        "validate",
        help="check a spec without generating anything",
        description="Check a spec and report every problem found. Writes no files.",
    )
    validate.add_argument("spec", help="path to a .yaml, .yml or .json spec")
    return parser


def _run(args: argparse.Namespace) -> None:
    spec = load_spec(args.spec)
    if args.command == "validate":
        rows = sum(entity.count for entity in spec.entities.values())
        print(f"{args.spec} is valid: {len(spec.entities)} entities, {rows} rows")
        return

    result = write(spec, out_dir=args.out, format=args.format, seed=args.seed)
    print(f"Seed: {result.seed}")
    width = max(len(entity.name) for entity in result.entities)
    for entity in result.entities:
        print(f"{entity.name:<{width}}  {entity.rows:>9} rows  {entity.path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _run(args)
    except SpecError as error:
        if all(not problem.path for problem in error.problems):
            # The file itself could not be read or parsed; its message already names the file.
            print(f"error: {error}", file=sys.stderr)
        else:
            count = len(error.problems)
            print(f"error: {args.spec} is not a valid spec ({count} problem(s))", file=sys.stderr)
            for problem in error.problems:
                print(f"  {problem}", file=sys.stderr)
        return EXIT_INVALID
    except DataspecterError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILURE
    except Exception as error:  # the CLI is the outermost layer: report, never a traceback
        print(f"error: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
