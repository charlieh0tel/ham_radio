"""Command-line interface: tune eggbeater designs from a JSON spec."""

import argparse
import sys
from dataclasses import replace

from .design import REFLECTOR_NONE, DesignSpec, design, optimize_reflector
from .plot import render_artifact
from .report import format_bandwidth, format_cut_sheet
from .spec import specs_from_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beater",
        description="Tune eggbeater antenna designs from a JSON spec.",
    )
    parser.add_argument(
        "spec",
        nargs="?",
        default="-",
        help="path to a JSON spec (one design or a list); '-' or omitted reads stdin",
    )
    parser.add_argument(
        "--optimize-reflector",
        action="store_true",
        help="grid-search reflector spacing and droop for the best match",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="sweep frequency and report the 2:1 VSWR and 3 dB axial-ratio bands",
    )
    parser.add_argument(
        "--deck",
        help="write the tuned NEC deck to this path (single-design specs only)",
    )
    parser.add_argument(
        "--plot",
        help="write a performance plot page (HTML) for the design(s) to this path",
    )
    parser.add_argument("--nec2c", default="nec2c", help="nec2c executable")
    return parser


def load_specs(path: str) -> list[DesignSpec]:
    """Read specs from a file path, or stdin when path is '-'."""
    text = sys.stdin.read() if path == "-" else open(path).read()
    return specs_from_json(text)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    specs = [replace(spec, nec2c=args.nec2c) for spec in load_specs(args.spec)]
    if args.deck and len(specs) > 1:
        parser.error("--deck requires a single-design spec")

    results = []
    for index, spec in enumerate(specs):
        if args.optimize_reflector and spec.reflector == REFLECTOR_NONE:
            parser.error("--optimize-reflector requires a reflector")
        result = optimize_reflector(spec) if args.optimize_reflector else design(spec)
        results.append(result)
        if index:
            print()
        print(format_cut_sheet(result), end="")
        if args.sweep:
            print(format_bandwidth(result), end="")
        if args.deck:
            with open(args.deck, "w") as handle:
                handle.write(result.deck)
            print(f"Wrote NEC deck to {args.deck}")

    if args.plot:
        with open(args.plot, "w") as handle:
            handle.write(render_artifact(results))
        print(f"Wrote plot page to {args.plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
