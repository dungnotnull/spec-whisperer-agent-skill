#!/usr/bin/env python3
"""
spec_store.py — Spec Storage System
Part of the spec-whisperer skill.

Manages .specs/ directory: save locked specs, load by ID, search by keyword.

Usage:
    python spec_store.py --save spec.md --title "Login Page" --slug login-page --confidence 87
    python spec_store.py --find "login"
    python spec_store.py --load 2026-06-07-login-page
    python spec_store.py --list
    python spec_store.py --status
    python spec_store.py --lock 2026-06-07-login-page
"""

import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

DEFAULT_SPECS_DIR = ".specs"
INDEX_FILE = "index.json"


# ── ANSI helpers ──────────────────────────────────────────────────────────────
BOLD  = "\033[1m"
DIM   = "\033[2m"
GREEN = "\033[32m"
CYAN  = "\033[36m"
YELLOW = "\033[33m"
RED   = "\033[31m"
RESET = "\033[0m"

def col(text, *codes):
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + RESET


# ── Index Management ──────────────────────────────────────────────────────────

def load_index(specs_dir: Path) -> list[dict]:
    idx = specs_dir / INDEX_FILE
    if idx.exists():
        try:
            return json.loads(idx.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_index(specs_dir: Path, index: list[dict]):
    specs_dir.mkdir(parents=True, exist_ok=True)
    idx = specs_dir / INDEX_FILE
    idx.write_text(json.dumps(index, indent=2), encoding="utf-8")


def add_to_index(specs_dir: Path, entry: dict):
    index = load_index(specs_dir)
    # Remove existing entry with same id
    index = [e for e in index if e.get("id") != entry["id"]]
    index.insert(0, entry)  # Most recent first
    save_index(specs_dir, index)


# ── Tag Extraction ────────────────────────────────────────────────────────────

def extract_tags(spec_markdown: str, title: str) -> list[str]:
    """Extract relevant tags from spec content."""
    tags = set()

    text = (spec_markdown + " " + title).lower()

    tag_patterns = {
        "auth": r"\b(auth|login|sign.in|oauth|password|jwt|session)\b",
        "api": r"\b(api|endpoint|rest|graphql|fetch|http)\b",
        "ui": r"\b(component|page|form|button|modal|layout|ui)\b",
        "data": r"\b(database|schema|migration|model|query|crud)\b",
        "search": r"\b(search|filter|query|find)\b",
        "list": r"\b(list|table|grid|pagination)\b",
        "payment": r"\b(payment|billing|stripe|invoice|checkout)\b",
        "admin": r"\b(admin|dashboard|management|panel)\b",
        "react": r"\breact\b",
        "typescript": r"\btypescript\b",
        "python": r"\bpython\b",
        "mobile": r"\b(mobile|responsive|ios|android)\b",
        "realtime": r"\b(real.?time|websocket|socket|live)\b",
    }

    for tag, pattern in tag_patterns.items():
        if re.search(pattern, text, re.I):
            tags.add(tag)

    return sorted(list(tags))[:8]


# ── Save ──────────────────────────────────────────────────────────────────────

def save_spec(
    spec_markdown: str,
    title: str,
    slug: str,
    confidence: int,
    specs_dir: str = DEFAULT_SPECS_DIR,
    status: str = "LOCKED",
    risk: str = "Low",
) -> str:
    """Save spec to .specs/ and update index. Returns file path."""
    base = Path(specs_dir)
    base.mkdir(parents=True, exist_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    spec_id = f"{date}-{slug[:50]}"
    filename = f"{spec_id}.md"
    filepath = base / filename

    # Handle duplicates
    if filepath.exists():
        i = 1
        while filepath.exists():
            filename = f"{spec_id}-{i}.md"
            filepath = base / filename
            i += 1
        spec_id = filename[:-3]

    filepath.write_text(spec_markdown, encoding="utf-8")

    # Update index
    entry = {
        "id": spec_id,
        "title": title,
        "slug": slug,
        "date": date,
        "status": status,
        "confidence": confidence,
        "risk": risk,
        "tags": extract_tags(spec_markdown, title),
        "path": str(filepath),
        "created_at": datetime.now().isoformat(),
    }
    add_to_index(base, entry)

    return str(filepath)


# ── Load ──────────────────────────────────────────────────────────────────────

def load_spec(spec_id_or_path: str, specs_dir: str = DEFAULT_SPECS_DIR) -> dict | None:
    """Load a spec by ID, path, or partial slug match."""
    base = Path(specs_dir)

    # Direct path
    p = Path(spec_id_or_path)
    if p.exists():
        return {
            "id": p.stem,
            "markdown": p.read_text(encoding="utf-8"),
            "path": str(p),
        }

    # By ID from index
    index = load_index(base)
    for entry in index:
        if entry.get("id") == spec_id_or_path:
            fp = Path(entry["path"])
            if fp.exists():
                return {**entry, "markdown": fp.read_text(encoding="utf-8")}

    # By path in .specs/
    candidate = base / f"{spec_id_or_path}.md"
    if candidate.exists():
        return {
            "id": spec_id_or_path,
            "markdown": candidate.read_text(encoding="utf-8"),
            "path": str(candidate),
        }

    return None


# ── Find (Search) ─────────────────────────────────────────────────────────────

def find_specs(query: str, specs_dir: str = DEFAULT_SPECS_DIR, top_n: int = 5) -> list[dict]:
    """Search specs by keyword in title, tags, or content."""
    base = Path(specs_dir)
    index = load_index(base)
    query_lower = query.lower()
    query_words = set(re.split(r'\W+', query_lower))

    results = []
    for entry in index:
        score = 0
        title_lower = entry.get("title", "").lower()
        tags = entry.get("tags", [])

        # Title match (highest weight)
        if query_lower in title_lower:
            score += 30
        for word in query_words:
            if word and word in title_lower:
                score += 10

        # Tag match
        for tag in tags:
            if tag in query_words or query_lower in tag:
                score += 15

        # Content match (if file accessible)
        if score < 10:  # Only read file if title/tag match is weak
            fp = Path(entry.get("path", ""))
            if fp.exists():
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore").lower()
                    for word in query_words:
                        if word and len(word) > 3 and word in content:
                            score += 3
                            break
                except Exception:
                    pass

        if score > 0:
            results.append({**entry, "_score": score})

    results.sort(key=lambda x: (x["_score"], x.get("date", "")), reverse=True)
    return results[:top_n]


# ── Lock ──────────────────────────────────────────────────────────────────────

def lock_spec(spec_id: str, specs_dir: str = DEFAULT_SPECS_DIR) -> bool:
    """Mark a spec as LOCKED in the index and file."""
    base = Path(specs_dir)
    index = load_index(base)

    for entry in index:
        if entry.get("id") == spec_id:
            entry["status"] = "LOCKED"
            entry["locked_at"] = datetime.now().isoformat()

            # Update file content
            fp = Path(entry["path"])
            if fp.exists():
                content = fp.read_text(encoding="utf-8")
                content = content.replace("**Status:** DRAFT", "**Status:** LOCKED", 1)
                fp.write_text(content, encoding="utf-8")

            save_index(base, index)
            return True

    return False


# ── List ──────────────────────────────────────────────────────────────────────

def list_specs(specs_dir: str = DEFAULT_SPECS_DIR) -> list[dict]:
    """List all specs from index, most recent first."""
    base = Path(specs_dir)
    return load_index(base)


def format_spec_list(specs: list[dict]) -> str:
    """Format spec list for terminal display."""
    if not specs:
        return "No specs found. Run spec-whisperer on an implementation request to create one."

    lines = [col(f"\n  {'ID':<45} {'Conf':>5}  {'Risk':<8}  {'Status':<8}  Title", BOLD)]
    lines.append("  " + "─" * 85)

    for s in specs:
        spec_id = s.get("id", "unknown")[:44]
        conf = s.get("confidence", 0)
        risk = s.get("risk", "?")
        status = s.get("status", "?")
        title = s.get("title", "Untitled")[:35]
        tags = ", ".join(s.get("tags", [])[:3])

        # Color by confidence
        if conf >= 75:
            conf_str = col(f"{conf}%", GREEN)
        elif conf >= 50:
            conf_str = col(f"{conf}%", YELLOW)
        else:
            conf_str = col(f"{conf}%", RED)

        status_str = col(status, GREEN if status == "LOCKED" else YELLOW)
        lines.append(f"  {spec_id:<44} {conf_str:>8}  {risk:<8}  {status_str:<16}  {title}")
        if tags:
            lines.append(f"  {'':<44} {'':<8}  {'':<8}  {'':<8}  {col(tags, DIM)}")

    lines.append(f"\n  {len(specs)} spec(s) total\n")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="spec-whisperer spec storage manager.")

    parser.add_argument("--save", type=str, metavar="SPEC_FILE",
                        help="Save a spec file (path to .md)")
    parser.add_argument("--save-content", type=str, help="Save spec from inline markdown string")
    parser.add_argument("--title", type=str, default="Feature", help="Spec title")
    parser.add_argument("--slug", type=str, default="feature", help="Spec slug")
    parser.add_argument("--confidence", type=int, default=75, help="Confidence score 0-100")
    parser.add_argument("--risk", type=str, default="Low", help="Risk level")
    parser.add_argument("--status", type=str, default="LOCKED",
                        choices=["LOCKED", "DRAFT"], help="Spec status")

    parser.add_argument("--find", type=str, metavar="QUERY", help="Search specs")
    parser.add_argument("--load", type=str, metavar="SPEC_ID", help="Load a spec by ID")
    parser.add_argument("--lock", type=str, metavar="SPEC_ID", help="Lock a draft spec")
    parser.add_argument("--list", action="store_true", help="List all specs")
    parser.add_argument("--status-check", action="store_true", help="Show .specs/ status")

    parser.add_argument("--specs-dir", type=str, default=DEFAULT_SPECS_DIR)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted")

    args = parser.parse_args()

    if args.save or args.save_content:
        if args.save:
            fp = Path(args.save)
            if not fp.exists():
                print(f"File not found: {args.save}", file=sys.stderr)
                sys.exit(1)
            content = fp.read_text(encoding="utf-8")
        else:
            content = args.save_content

        path = save_spec(
            spec_markdown=content,
            title=args.title,
            slug=args.slug,
            confidence=args.confidence,
            specs_dir=args.specs_dir,
            status=args.status,
            risk=args.risk,
        )
        print(f"✅ Spec saved → {path}")

    elif args.find:
        results = find_specs(args.find, args.specs_dir)
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(results, indent=indent))
        elif not results:
            print(f"No specs found matching '{args.find}'")
        else:
            print(f"\nFound {len(results)} spec(s) matching '{args.find}':\n")
            for r in results:
                badge = "🟢" if r.get("confidence", 0) >= 75 else "🟡"
                print(f"  {badge} [{r.get('id')}] {r.get('title')} — {r.get('confidence')}% confidence")
                print(f"     Tags: {', '.join(r.get('tags', []))}")
                print()

    elif args.load:
        spec = load_spec(args.load, args.specs_dir)
        if not spec:
            print(f"Spec not found: {args.load}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            output = {k: v for k, v in spec.items() if k != "markdown"}
            indent = 2 if args.pretty else None
            print(json.dumps(output, indent=indent))
        else:
            print(spec["markdown"])

    elif args.lock:
        ok = lock_spec(args.lock, args.specs_dir)
        if ok:
            print(f"✅ Spec locked: {args.lock}")
        else:
            print(f"Spec not found: {args.lock}", file=sys.stderr)
            sys.exit(1)

    elif args.list:
        specs = list_specs(args.specs_dir)
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(specs, indent=indent))
        else:
            print(format_spec_list(specs))

    elif args.status_check:
        base = Path(args.specs_dir)
        specs = list_specs(args.specs_dir)
        locked = sum(1 for s in specs if s.get("status") == "LOCKED")
        drafts = len(specs) - locked
        avg_conf = sum(s.get("confidence", 0) for s in specs) / max(len(specs), 1)

        print(f"\n👻 spec-whisperer — .specs/ status")
        print(f"   Directory: {base.resolve()}")
        print(f"   Total specs:  {len(specs)}")
        print(f"   Locked:       {locked}")
        print(f"   Drafts:       {drafts}")
        print(f"   Avg conf:     {avg_conf:.0f}%")
        if specs:
            latest = specs[0]
            print(f"   Latest:       {latest.get('title')} ({latest.get('date')})")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
