#!/usr/bin/env python3
"""Export canonical skills and prompts into a Model Observatory checkout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_repo import parse_frontmatter, validate_repo


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(_yaml_string(value) for value in values) + "]"


def render_skill(skill_file: Path, metadata: dict) -> str:
    fields, body = parse_frontmatter(skill_file)
    name = fields["name"]
    item = metadata[name]
    frontmatter = [
        "---",
        f"name: {_yaml_string(name)}",
        f"description: {_yaml_string(fields['description'])}",
        f"category: {_yaml_string(item['category'])}",
        f"tags: {_yaml_list(item['tags'])}",
        f"version: {_yaml_string(item['version'])}",
        f"author: {_yaml_string(item['author'])}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + body.lstrip("\n")


def collect_exports(root: Path, target: Path) -> dict[Path, str]:
    metadata = json.loads((root / "observatory.json").read_text(encoding="utf-8"))["skills"]
    exports: dict[Path, str] = {}
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        destination = target / "templates" / "skills" / f"{skill_file.parent.name}.md"
        exports[destination] = render_skill(skill_file, metadata)
    for prompt in sorted((root / "prompts").glob("*.md")):
        exports[target / "templates" / "prompts" / prompt.name] = prompt.read_text(encoding="utf-8")
    return exports


def export(root: Path, target: Path, *, check: bool = False, force: bool = False) -> tuple[list[str], list[str]]:
    """Return status lines and conflicts; never perform Git or deployment operations."""
    if not target.is_dir():
        raise ValueError(f"target is not a directory: {target}")
    exports = collect_exports(root, target)
    statuses: list[str] = []
    conflicts: list[str] = []
    writes: list[tuple[Path, str]] = []
    for destination, content in exports.items():
        relative = destination.relative_to(target)
        if not destination.exists():
            statuses.append(f"CREATE {relative}")
            writes.append((destination, content))
        elif destination.read_text(encoding="utf-8") == content:
            statuses.append(f"SAME   {relative}")
        else:
            statuses.append(f"CHANGE {relative}")
            conflicts.append(str(relative))
            if force:
                writes.append((destination, content))
    if check or (conflicts and not force):
        return statuses, conflicts
    for destination, content in writes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return statuses, conflicts


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="existing Model Observatory checkout or staging directory")
    parser.add_argument("--check", action="store_true", help="preview changes without writing files")
    parser.add_argument("--force", action="store_true", help="explicitly overwrite differing target templates")
    args = parser.parse_args()
    errors = validate_repo(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    try:
        statuses, conflicts = export(root.resolve(), args.target.resolve(), check=args.check, force=args.force)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    for status in statuses:
        print(status)
    if conflicts and not args.force:
        print(f"Refused to overwrite {len(conflicts)} differing file(s); rerun with --force after review.")
        return 2
    if args.check:
        print("Preview only; no files written.")
    else:
        print("Export complete; no commit, push, collection, or deployment was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
