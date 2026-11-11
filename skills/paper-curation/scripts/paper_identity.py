#!/usr/bin/env python3
"""Generate stable, deterministic paper identities without network access."""

from __future__ import annotations

import argparse
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit

_NEW_ARXIV = re.compile(r"^(?P<id>\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
_OLD_ARXIV = re.compile(
    r"^(?P<id>(?:astro-ph|cond-mat|gr-qc|hep-ex|hep-lat|hep-ph|hep-th|math-ph|nlin|nucl-ex|nucl-th|physics|quant-ph|math|cs|q-bio|q-fin|stat|eess|econ)(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$",
    re.IGNORECASE,
)


def normalize_arxiv(value: str) -> str:
    """Return ``arxiv:<id>`` with URL decorations and version removed."""
    text = value.strip()
    if not text:
        raise ValueError("arXiv identifier is empty")

    if "://" in text:
        parsed = urlsplit(text)
        if parsed.hostname not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            raise ValueError("URL is not an arXiv URL")
        match = re.match(r"^/(?:abs|pdf)/(.+)$", parsed.path, re.IGNORECASE)
        if not match:
            raise ValueError("arXiv URL must use /abs/ or /pdf/")
        text = match.group(1)
    else:
        text = text.split("?", 1)[0].split("#", 1)[0]

    text = re.sub(r"^arxiv\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\.pdf$", "", text, flags=re.IGNORECASE).strip("/")

    for pattern in (_NEW_ARXIV, _OLD_ARXIV):
        match = pattern.fullmatch(text)
        if match:
            identifier = match.group("id")
            if "/" in identifier:
                archive, suffix = identifier.split("/", 1)
                identifier = f"{archive.lower()}/{suffix}"
            return f"arxiv:{identifier}"
    raise ValueError(f"unsupported arXiv identifier: {value!r}")


def title_identity(title: str) -> str:
    """Return an ASCII title slug, falling back to a hash for non-ASCII titles."""
    normalized = unicodedata.normalize("NFKC", title).casefold().strip()
    normalized = " ".join(normalized.split())
    if not normalized:
        raise ValueError("title is empty")
    slug = "-".join(re.findall(r"[a-z0-9]+", normalized))
    if not slug:
        slug = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"title:{slug}"


def paper_identity(*, arxiv: str | None = None, title: str | None = None) -> str:
    """Prefer arXiv identity and require exactly one input source."""
    if (arxiv is None) == (title is None):
        raise ValueError("provide exactly one of arxiv or title")
    return normalize_arxiv(arxiv) if arxiv is not None else title_identity(title or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--arxiv", help="arXiv id, arXiv: id, or /abs//pdf/ URL")
    group.add_argument("--title", help="paper title used when no arXiv id exists")
    args = parser.parse_args()
    try:
        print(paper_identity(arxiv=args.arxiv, title=args.title))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
