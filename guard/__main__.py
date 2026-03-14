"""
__main__.py — CLI entry point for Universal Runtime Guard.

Usage::

    python -m guard audit              # scan and exit non-zero on findings
    python -m guard audit --broken     # also check for broken imports
    python -m guard audit --json       # output results as JSON

Current phase
-------------
**Phase 2 — ``guard audit`` CLI command** (shipped).
Scans installed dependencies and exits non-zero when vulnerabilities or
blocked packages are found, enabling CI/CD gate-keeping.

Next phases
-----------
**Phase 3 — ``guard sbom`` command** (planned).
Generate a CycloneDX / SPDX Software Bill of Materials from the scan
results.
"""

from __future__ import annotations

import argparse
import json
import sys

from guard.dependency import run_all_scans


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guard",
        description="Universal Runtime Guard CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    audit_parser = subparsers.add_parser(
        "audit",
        help="Scan installed dependencies for vulnerabilities and blocked packages.",
    )
    audit_parser.add_argument(
        "--broken",
        action="store_true",
        default=False,
        help="Also check for broken imports (slower).",
    )
    audit_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output results as JSON.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the guard CLI.  Returns the exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "audit":
        return _cmd_audit(args)

    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    """Execute the ``guard audit`` sub-command."""
    warnings = run_all_scans(check_broken=args.broken)

    if args.json_output:
        result = {
            "vulnerabilities": len(warnings),
            "findings": warnings,
        }
        print(json.dumps(result, indent=2))
    else:
        if warnings:
            for w in warnings:
                print(w, file=sys.stderr)
            print(
                f"\n🛡️  guard audit: {len(warnings)} finding(s) detected.",
                file=sys.stderr,
            )
        else:
            print(
                "🛡️  guard audit: no vulnerabilities or blocked packages found.",
                file=sys.stderr,
            )

    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
