#!/usr/bin/env python3
"""Validate skill packages, prompts, local links, and workflow invariants."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:[ \t]*(.*))$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_ROOT = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "observatory.json",
    ".cursor/rules/surgical-coding.mdc",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".github/workflows/ci.yml",
)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Parse the deliberately small, single-line YAML frontmatter subset used here."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        match = FIELD_RE.fullmatch(line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        key, value = match.groups()
        if key in fields:
            raise ValueError(f"duplicate frontmatter field: {key}")
        if not value.strip():
            raise ValueError(f"empty frontmatter field: {key}")
        fields[key] = value.strip()
    return fields, "\n".join(lines[end + 1 :]) + "\n"


def _check_links(path: Path, body: str) -> list[str]:
    errors = []
    for target in LINK_RE.findall(body):
        target = target.strip().split(maxsplit=1)[0]
        if not target or target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        local = target.split("#", 1)[0]
        if local and not (path.parent / local).exists():
            errors.append(f"{path.relative_to(path.parents[1]) if len(path.parents) > 1 else path}: broken local link {target}")
    return errors


def validate_repo(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for relative in REQUIRED_ROOT:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skills_root = root / "skills"
    skill_names: set[str] = set()
    if not skills_root.is_dir():
        errors.append("missing skills directory")
    else:
        for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
            name = skill_dir.name
            skill_names.add(name)
            skill_file = skill_dir / "SKILL.md"
            if not NAME_RE.fullmatch(name) or len(name) > 64:
                errors.append(f"invalid skill directory name: {name}")
            if not skill_file.is_file():
                errors.append(f"{name}: missing SKILL.md")
                continue
            try:
                fields, body = parse_frontmatter(skill_file)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"{skill_file.relative_to(root)}: {exc}")
                continue
            if set(fields) != {"name", "description"}:
                errors.append(f"{skill_file.relative_to(root)}: frontmatter must contain only name and description")
            if fields.get("name") != name:
                errors.append(f"{skill_file.relative_to(root)}: name must match directory")
            description = fields.get("description", "")
            if not 40 <= len(description) <= 500:
                errors.append(f"{skill_file.relative_to(root)}: description length must be 40–500 characters")
            if len(body.splitlines()) > 500:
                errors.append(f"{skill_file.relative_to(root)}: body exceeds 500 lines")
            for auxiliary in ("README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"):
                if (skill_dir / auxiliary).exists():
                    errors.append(f"{skill_file.relative_to(root)}: remove auxiliary {auxiliary}")
            errors.extend(_check_links(skill_file, body))

    prompts_root = root / "prompts"
    prompt_names: set[str] = set()
    if not prompts_root.is_dir():
        errors.append("missing prompts directory")
    else:
        for prompt in sorted(prompts_root.glob("*.md")):
            prompt_names.add(prompt.stem)
            if not NAME_RE.fullmatch(prompt.stem):
                errors.append(f"invalid prompt slug: {prompt.stem}")
            try:
                fields, body = parse_frontmatter(prompt)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"{prompt.relative_to(root)}: {exc}")
                continue
            required = {"name", "description", "category", "tags", "version", "author"}
            missing = required - set(fields)
            if missing:
                errors.append(f"{prompt.relative_to(root)}: missing fields {sorted(missing)}")
            if not body.strip():
                errors.append(f"{prompt.relative_to(root)}: empty prompt body")
            errors.extend(_check_links(prompt, body))

    metadata_path = root / "observatory.json"
    if metadata_path.is_file():
        try:
            metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
            configured = set(metadata.get("skills", {}))
            if configured != skill_names:
                errors.append(f"observatory.json skill mismatch: missing={sorted(skill_names-configured)}, extra={sorted(configured-skill_names)}")
            for name, item in metadata.get("skills", {}).items():
                if set(item) != {"category", "tags", "version", "author"}:
                    errors.append(f"observatory.json: invalid metadata fields for {name}")
                if not isinstance(item.get("tags"), list) or not all(isinstance(tag, str) for tag in item.get("tags", [])):
                    errors.append(f"observatory.json: tags must be a string list for {name}")
        except (OSError, ValueError, AttributeError) as exc:
            errors.append(f"observatory.json: {exc}")

    plugin_path = root / ".claude-plugin/plugin.json"
    marketplace_path = root / ".claude-plugin/marketplace.json"
    if plugin_path.is_file():
        try:
            plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
            declared_paths = plugin.get("skills")
            if not isinstance(declared_paths, list) or not all(isinstance(item, str) for item in declared_paths):
                errors.append("plugin.json: skills must be a string list")
            else:
                declared_names = {Path(item).name for item in declared_paths}
                if declared_names != skill_names or len(declared_names) != len(declared_paths):
                    errors.append("plugin.json: skills must list every skill exactly once")
                for relative in declared_paths:
                    parts = Path(relative).parts
                    if len(parts) != 2 or parts[0] != "skills" or not (root / relative / "SKILL.md").is_file():
                        errors.append(f"plugin.json: invalid skill path {relative}")
            if marketplace_path.is_file():
                marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
                entries = marketplace.get("plugins", [])
                matching = [
                    entry
                    for entry in entries
                    if entry.get("name") == plugin.get("name") and entry.get("source") == "./"
                ]
                if len(matching) != 1:
                    errors.append("marketplace.json: must expose plugin.json exactly once at source ./")
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            errors.append(f"Claude plugin manifest: {exc}")

    for relative in ("README.md", "CONTRIBUTING.md"):
        path = root / relative
        if path.is_file():
            errors.extend(_check_links(path, path.read_text(encoding="utf-8")))

    workflow = root / ".github/workflows/ci.yml"
    if workflow.is_file():
        text = workflow.read_text(encoding="utf-8")
        for action in re.findall(r"^\s*uses:\s*([^\s#]+)", text, flags=re.MULTILINE):
            revision = action.rsplit("@", 1)[-1]
            if not SHA_RE.fullmatch(revision):
                errors.append(f"ci.yml: action is not pinned to a full commit SHA: {action}")
        for required in (
            "contents: read",
            "python scripts/validate_repo.py",
            "python scripts/sync_guides.py --check",
            "python -m unittest",
            "python scripts/package_skills.py",
        ):
            if required not in text:
                errors.append(f"ci.yml: missing invariant {required!r}")

    for scope in (root / "scripts", root / "tests", skills_root):
        if not scope.is_dir():
            continue
        for path in scope.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, UnicodeError, SyntaxError) as exc:
                errors.append(f"{path.relative_to(root)}: Python syntax error: {exc}")

    if not skill_names:
        errors.append("repository contains no skills")
    if not prompt_names:
        errors.append("repository contains no prompts")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_repo(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed with {len(errors)} error(s).")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
