#!/usr/bin/env python3
"""Cross-reference gate for the competency map (curriculum/*.md).

The v0.19 domain renumbering left stale references ("Domain 7 (Backup and
Recovery)" when 7 had become Cloud Primitives) scattered through the
document for four versions. This gate makes that class of drift a CI
failure instead of a reader discovery.

Checks:
  1. Every named reference "Domain N (Some Name)" must agree with the
     canonical title of domain N from that file's front matter — every
     significant word in the parenthetical must appear in the canonical
     title. "Domain 7 (Backup and Recovery)" fails while 7 is Cloud
     Primitives.
  2. Every "Domain N" must reference a domain that exists.
  3. File name prefix must match the front matter `domain:` number; no
     duplicate numbers.

Bare references ("Domain 9" with no parenthetical) cannot be validated
semantically; run with --list-bare to enumerate them for manual audit
after any renumbering. Better: never renumber again — domain numbers are
stable IDs, new domains append (see plans/001).

Exit 0 clean, 1 on violations.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CURRICULUM = Path(__file__).resolve().parent.parent / "curriculum"
STOPWORDS = {"and", "the", "of", "as", "a", "an", "amp"}

NAMED_REF = re.compile(r"Domain (\d+)(?:'s)? \(([^)]+)\)")
BARE_REF = re.compile(r"Domain (\d+)\b(?!\s*\()")
FM_FIELD = re.compile(r"^(domain|title):\s*\"?([^\"\n]+)\"?\s*$", re.M)


def words(s: str) -> set[str]:
    s = s.lower().replace("&", " and ").replace("—", " ").replace("-", " ")
    return {w for w in re.findall(r"[a-z]+", s) if w not in STOPWORDS}


def load_domains() -> dict[int, dict]:
    domains: dict[int, dict] = {}
    problems = []
    for f in sorted(CURRICULUM.glob("[0-9][0-9]-*.md")):
        text = f.read_text()
        if not text.startswith("---"):
            continue  # front-matter-less numbered file (00-front-matter)
        fm = text.split("---", 2)[1]
        fields = dict(FM_FIELD.findall(fm))
        if "domain" not in fields:
            continue
        n = int(fields["domain"])
        prefix = int(f.name[:2])
        if prefix != n:
            problems.append(f"{f.name}: file prefix {prefix} != domain: {n}")
        if n in domains:
            problems.append(f"{f.name}: duplicate domain number {n}")
        domains[n] = {"title": fields.get("title", ""), "file": f.name}
    if problems:
        for p in problems:
            print(f"FRONT MATTER: {p}")
        sys.exit(1)
    return domains


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-bare", action="store_true",
                    help="list unvalidatable bare 'Domain N' references")
    args = ap.parse_args()

    domains = load_domains()
    violations = []
    bare = []

    for f in sorted(CURRICULUM.glob("*.md")):
        if f.name == "version-history.md":
            continue  # historical entries legitimately use pre-v0.19 numbers
        text = f.read_text()
        # strip yaml front matter so `domain: N` isn't scanned
        if text.startswith("---"):
            text = text.split("---", 2)[2]
        for m in NAMED_REF.finditer(text):
            n, name = int(m.group(1)), m.group(2)
            if n not in domains:
                violations.append(
                    f"{f.name}: 'Domain {n} ({name})' — no such domain")
                continue
            canonical = words(domains[n]["title"])
            # Accept exact/subset matches, and descriptive parentheticals
            # ("Domain 8 (security reasoning about what to prioritize)")
            # whose first significant word anchors on the canonical title.
            ref_words = words(name)
            first = next(iter(re.findall(r"[a-z]+", name.lower().replace(
                "&", " and "))), "")
            anchored = first in canonical
            if not (ref_words <= canonical or anchored):
                violations.append(
                    f"{f.name}: 'Domain {n} ({name})' but Domain {n} is "
                    f"'{domains[n]['title']}'")
        for m in BARE_REF.finditer(text):
            n = int(m.group(1))
            if n not in domains:
                violations.append(
                    f"{f.name}: bare reference to Domain {n} — no such domain")
            elif f.name != domains[n]["file"]:
                bare.append(f"{f.name}: Domain {n} "
                            f"({domains[n]['title']}) — unvalidated")

    for v in violations:
        print(f"VIOLATION: {v}")
    if args.list_bare:
        for b in bare:
            print(f"bare: {b}")
    print(f"{len(domains)} domains, {len(violations)} violation(s), "
          f"{len(bare)} bare cross-file reference(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
