#!/usr/bin/env python3
"""Build deduplicated, review-required research candidates from public snapshots."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
import urllib.parse
import urllib.request

BASE_URL = "https://islinxu.github.io/model-observatory/data/"


def safe_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value) or any(char in value for char in "<>'\""):
        return None
    parsed = urllib.parse.urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def load_sources(names, *, data_dir=None, base_url=BASE_URL, timeout=30):
    payloads, errors = {}, {}
    for name in names:
        try:
            if data_dir is not None:
                with (Path(data_dir) / name).open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            else:
                request = urllib.request.Request(
                    urllib.parse.urljoin(base_url.rstrip("/") + "/", name),
                    headers={"User-Agent": "islinxu-skills-research-intake"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = json.load(response)
            if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                raise ValueError("unsupported schema_version")
            payloads[name] = payload
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    return payloads, errors


def ascii_slug(value):
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "-".join(re.findall(r"[a-z0-9]+", normalized))


def paper_slug(identifier):
    if not isinstance(identifier, str) or ":" not in identifier:
        return None
    suffix = ascii_slug(identifier.split(":", 1)[1])
    return f"paper-{suffix}" if suffix else None


def model_slug(identifier):
    if not isinstance(identifier, str) or not identifier.startswith("homc:"):
        return None
    suffix = identifier[len("homc:") :].split("|", 1)[0]
    suffix = ascii_slug(suffix)
    return f"homc-{suffix}" if suffix else None


def _append_source(candidate, source):
    signature = json.dumps(source, ensure_ascii=False, sort_keys=True)
    if all(json.dumps(item, ensure_ascii=False, sort_keys=True) != signature for item in candidate["sources"]):
        candidate["sources"].append(source)


def collect_candidates(*, awesome=None, homc=None, tasks=None, kind="all", limit=20, generated_at=None):
    candidates = {}
    skipped = Counter()
    already_tracked = set()
    tracked_slugs = {task.get("slug") for task in (tasks or {}).get("tasks", []) if task.get("slug")}
    sample_limited = False

    if kind in {"all", "papers"} and awesome is not None:
        sample_limited = True
        for repo in awesome.get("repos", []):
            if repo.get("status") != "ok":
                skipped["stale_or_unavailable_repositories"] += 1
                continue
            for item in repo.get("sample", []):
                if not item.get("is_new"):
                    continue
                slug = paper_slug(item.get("id"))
                title = item.get("title")
                url = safe_url(item.get("url"))
                if not slug:
                    skipped["missing_paper_id"] += 1
                    continue
                if not title:
                    skipped["missing_title"] += 1
                    continue
                if not url:
                    skipped["invalid_url"] += 1
                    continue
                if slug in tracked_slugs:
                    already_tracked.add(slug)
                    continue
                candidate = candidates.setdefault(
                    slug,
                    {"slug": slug, "kind": "paper", "title": title, "url": url, "review_required": True, "sources": []},
                )
                _append_source(
                    candidate,
                    {
                        "type": "awesome",
                        "id": repo.get("id"),
                        "captured_at": repo.get("captured_at") or awesome.get("captured_at"),
                        "section": item.get("section"),
                        "published": item.get("published"),
                        "upstream": bool(repo.get("upstream")),
                    },
                )

    if kind in {"all", "models"} and homc is not None:
        sample_limited = True
        if homc.get("status") != "ok":
            skipped["homc_not_current"] += 1
        else:
            for row in homc.get("rows", []):
                if row.get("state") not in {"new", "unverified"} and not row.get("is_new"):
                    continue
                slug = model_slug(row.get("id"))
                title = row.get("name")
                url = safe_url(row.get("url"))
                if not slug:
                    skipped["missing_model_id"] += 1
                    continue
                if not title:
                    skipped["missing_title"] += 1
                    continue
                if not url:
                    skipped["invalid_url"] += 1
                    continue
                if slug in tracked_slugs:
                    already_tracked.add(slug)
                    continue
                candidate = candidates.setdefault(
                    slug,
                    {"slug": slug, "kind": "model", "title": title, "url": url, "review_required": True, "sources": []},
                )
                _append_source(
                    candidate,
                    {
                        "type": "homc",
                        "id": row.get("id"),
                        "captured_at": homc.get("captured_at"),
                        "as_of": homc.get("as_of"),
                        "state": row.get("state"),
                        "is_new": bool(row.get("is_new")),
                        "vendor": row.get("vendor"),
                        "grades": row.get("grades") or [],
                        "single_b_source": bool(row.get("single_b_source")),
                    },
                )

    groups = [
        [candidates[slug] for slug in sorted(candidates) if candidates[slug]["kind"] == "paper"],
        [candidates[slug] for slug in sorted(candidates) if candidates[slug]["kind"] == "model"],
    ]
    ordered = []
    index = 0
    while any(index < len(group) for group in groups):
        for group in groups:
            if index < len(group):
                ordered.append(group[index])
        index += 1
    if len(ordered) > limit:
        skipped["over_limit"] = len(ordered) - limit
        ordered = ordered[:limit]
        sample_limited = True
    sources = {}
    for name, payload in (("awesome.json", awesome), ("homc.json", homc), ("tasks.json", tasks)):
        if payload is not None:
            sources[name] = {"status": payload.get("status"), "captured_at": payload.get("captured_at")}
    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "tracking_checked": tasks is not None,
        "sample_limited": sample_limited,
        "candidates": ordered,
        "already_tracked": sorted(already_tracked),
        "skipped": dict(sorted(skipped.items())),
        "sources": sources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="read snapshots from this directory instead of the network")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--kind", choices=("all", "papers", "models"), default="all")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    names = ["tasks.json"]
    if args.kind in {"all", "papers"}:
        names.append("awesome.json")
    if args.kind in {"all", "models"}:
        names.append("homc.json")
    payloads, errors = load_sources(names, data_dir=args.data_dir, base_url=args.base_url)
    if not payloads:
        for name, error in errors.items():
            print(f"ERROR {name}: {error}")
        return 1
    result = collect_candidates(
        awesome=payloads.get("awesome.json"),
        homc=payloads.get("homc.json"),
        tasks=payloads.get("tasks.json"),
        kind=args.kind,
        limit=args.limit,
    )
    result["errors"] = errors
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    for name, error in errors.items():
        print(f"WARNING {name}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
