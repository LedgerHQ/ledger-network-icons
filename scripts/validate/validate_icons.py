#!/usr/bin/env python3
"""
CI validation script for ledger-network-icons.

Walks all network family directories (e.g. icons/ethereum/) and validates every icon:
  - Naming convention: chain_{chainId}_{size}px.gif
  - Image compliance via check_glyph (dimensions, colors, format) => error if not compliant
  - Pairing completeness (warns if a chain ID is missing a size variant)
  - No extraneous files

Dependencies: wand (+ system libmagickwand-dev)

Usage:
    validate-icons [DIRECTORY]
    or
    python scripts/validate/validate_icons.py [DIRECTORY]

    DIRECTORY defaults to the repo root (auto-detected from script location).
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

from scripts.icon_to_nbgl.icon_to_nbgl import ConversionException, check_glyph

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

ICON_PATTERN = re.compile(r"^chain_(\d+)_(\d+)px\.gif$")

SIZE_SPECS: dict[int, tuple[int, int, int]] = {
    14: (2, 14, 14),  # max_nb_colors, width, height
    48: (2, 48, 48),
    64: (16, 64, 64),
}

VALID_SIZES = set(SIZE_SPECS.keys())


def validate_directory(network_dir: Path) -> tuple[int, int]:
    """Validate all icons in a network family directory. Returns (errors, warnings)."""
    errors = 0
    warnings = 0
    chain_sizes: dict[int, set[int]] = defaultdict(set)

    if not network_dir.is_dir():
        print(f"  SKIP: {network_dir} is not a directory")
        return 0, 0

    for entry in sorted(network_dir.iterdir()):
        if entry.name.startswith("."):
            continue

        if not entry.is_file():
            print(f"  ERROR: unexpected directory {entry.name}")
            errors += 1
            continue

        m = ICON_PATTERN.match(entry.name)
        if not m:
            print(f"  ERROR: {entry.name} does not match naming convention chain_{{chainId}}_{{size}}px.gif")
            errors += 1
            continue

        chain_id = int(m.group(1))
        size = int(m.group(2))

        if size not in VALID_SIZES:
            print(f"  ERROR: {entry.name} has invalid size {size}px (expected {VALID_SIZES})")
            errors += 1
            continue

        chain_sizes[chain_id].add(size)

        max_nb_colors, w, h = SIZE_SPECS[size]
        try:
            check_glyph(entry, max_nb_colors, w, h)
        except ConversionException as e:
            print(f"  ERROR: {entry.name}: {e}")
            errors += 1
        else:
            print(f"  OK: {entry.name}")

    # Warn if a chain ID is missing a size variant
    for chain_id in sorted(chain_sizes.keys()):
        missing = VALID_SIZES - chain_sizes[chain_id]
        if missing:
            sizes_str = ", ".join(f"{s}px" for s in sorted(missing))
            print(f"  WARN: chain {chain_id} missing {sizes_str}")
            warnings += 1

    return errors, warnings


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "icons"
    total_errors = 0
    total_warnings = 0

    network_dirs = sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))

    if not network_dirs:
        print(f"No network directories found in {root}")
        return 1

    for network_dir in network_dirs:
        print(f"\n=== {network_dir.name}/ ===")
        errors, warnings = validate_directory(network_dir)
        total_errors += errors
        total_warnings += warnings

    print(f"\n{'=' * 40}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
