#!/usr/bin/env python3
"""Validate and package skills as .skill ZIP archives."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
import zipfile

from validate_repo import validate_repo


def package_skill(skill_dir: Path, output_dir: Path) -> Path:
    """Package one skill atomically, preserving its root directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{skill_dir.name}.skill"
    files = sorted(
        path for path in skill_dir.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    if any(path.is_symlink() for path in skill_dir.rglob("*")):
        raise ValueError(f"symlinks are not allowed in skill packages: {skill_dir}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{skill_dir.name}-", suffix=".skill", dir=output_dir)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, arcname=str(Path(skill_dir.name) / path.relative_to(skill_dir)))
        with zipfile.ZipFile(temporary) as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"corrupt archive member: {corrupt}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=root / "dist")
    parser.add_argument("--only", action="append", help="package only this skill; repeatable")
    args = parser.parse_args()
    errors = validate_repo(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    selected = set(args.only or [])
    missing = selected - {path.name for path in (root / "skills").iterdir() if path.is_dir()}
    if missing:
        parser.error(f"unknown skills: {', '.join(sorted(missing))}")
    for skill_dir in sorted(path for path in (root / "skills").iterdir() if path.is_dir()):
        if selected and skill_dir.name not in selected:
            continue
        try:
            print(package_skill(skill_dir, args.output_dir))
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            print(f"ERROR: {skill_dir.name}: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
