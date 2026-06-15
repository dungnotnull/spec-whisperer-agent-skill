#!/usr/bin/env python3
"""
prompt_parser.py — Prompt Clause Extractor & Classifier
Part of the spec-whisperer skill.

Extracts meaningful clauses from an implementation prompt and classifies
each as: CLEAR, INFERABLE, AMBIGUOUS, MISSING_CRITICAL, MISSING_OPTIONAL.

Usage:
    python prompt_parser.py --text "build me a login page with email auth"
    python prompt_parser.py --file prompt.txt
    echo "add search to products" | python prompt_parser.py --stdin
    python prompt_parser.py --text "..." --context-dir ./src  # read codebase

Output JSON:
    {
        "trigger_type": "IMPLEMENT",
        "clauses": [
            {
                "text": "login page",
                "type": "CLEAR",
                "domain": "scope_boundary",
                "inferable": false,
                "blocks_others": false
            },
            ...
        ],
        "missing_critical_count": 2,
        "ambiguous_count": 1,
        "inferable_items": ["React (from package.json)", "Tailwind (from config)"],
        "feature_title": "Login Page with Email Authentication",
        "feature_slug": "login-page-email-authentication",
        "is_continuation": false,
        "is_multi_feature": false
    }
"""

import sys
import re
import json
import argparse
from pathlib import Path


# ── Trigger Detection ─────────────────────────────────────────────────────────

IMPLEMENT_SIGNALS = [
    r"\b(build|create|make|write|implement|develop|add|code|create)\b",
    r"\bi need (a|an|the)\b",
    r"\bcan you (build|make|create|write|implement|add)\b",
    r"\bhelp me (build|make|create|implement)\b",
    r"\bset up\b",
    r"\bscaffold\b",
]

CONTINUE_SIGNALS = [
    r"\b(continue|extend|add to|also add|and (also|make|add))\b",
    r"\bkeep (going|building)\b",
    r"\bnext (step|feature|part)\b",
]

SKIP_SIGNALS = [
    r"^(explain|what is|what are|how does|how do|how can|show me|tell me|why)\b",
    r"\b(debug|diagnose|fix this error|what.?s wrong)\b",
    r"\b(review|check|look at|read|analyze)\b",
    r"^(list|enumerate|describe|summarize)\b",
]


def detect_trigger(text: str) -> str:
    """Return 'IMPLEMENT', 'CONTINUE', or 'SKIP'."""
    lower = text.lower().strip()

    for pattern in SKIP_SIGNALS:
        if re.search(pattern, lower):
            return "SKIP"

    for pattern in CONTINUE_SIGNALS:
        if re.search(pattern, lower):
            return "CONTINUE"

    for pattern in IMPLEMENT_SIGNALS:
        if re.search(pattern, lower):
            return "IMPLEMENT"

    # Default: if it describes something to build, it's IMPLEMENT
    # Short noun phrases without verbs are often feature requests
    if len(lower.split()) <= 8 and not lower.endswith("?"):
        return "IMPLEMENT"

    return "SKIP"


# ── Ambiguity Signals ─────────────────────────────────────────────────────────

AMBIGUOUS_WORDS = {
    "fast": ("performance", "How fast? e.g., 'search results within 500ms'"),
    "slow": ("performance", "What performance is acceptable?"),
    "simple": ("scope_boundary", "Simple in what way — fewer features, simpler UI, or simpler code?"),
    "clean": ("acceptance_criteria", "What does 'clean' mean here?"),
    "nice": ("style_polish", None),  # MISSING_OPTIONAL
    "good": ("acceptance_criteria", "What makes this 'good'?"),
    "proper": ("acceptance_criteria", "What does 'proper' mean here?"),
    "real-time": ("ui_behavior", "How real-time — live WebSocket push, or polling every N seconds?"),
    "live": ("ui_behavior", "How live — WebSocket push or periodic refresh?"),
    "modern": ("style_polish", None),
    "responsive": ("ui_behavior", None),  # Always yes — MISSING_OPTIONAL
    "secure": ("auth_permissions", "What security requirements specifically?"),
    "scalable": ("performance", "What scale are we targeting?"),
    "performant": ("performance", "What performance target?"),
    "full": ("scope_boundary", "Full — what's included and what's out of scope?"),
    "complete": ("scope_boundary", "Complete — what does that include?"),
    "basic": ("scope_boundary", "Basic — what's the minimum scope?"),
    "advanced": ("scope_boundary", "Advanced — what features does that include?"),
    "dynamic": ("ui_behavior", "Dynamic in what way?"),
}

# Domains that are ALWAYS MISSING_CRITICAL if not addressed
ALWAYS_CRITICAL_DOMAINS = {
    "acceptance_criteria": [
        r"\b(work|works|working|correct|correctly|right|done|finish|complete)\b",
    ],
    "scope_boundary": [
        r"\b(whole|entire|full|complete|all the|everything)\b",
        r"\band\s+(also|more|other)\b",
    ],
}

# Phrases that signal CLEAR information
CLEAR_PATTERNS = [
    (r"\buse\s+(react|vue|angular|svelte|next\.?js|nuxt|remix|astro)\b", "tech_stack"),
    (r"\bwith\s+(typescript|javascript|python|go|rust|java|kotlin)\b", "tech_stack"),
    (r"\b(postgresql|mysql|sqlite|mongodb|redis|supabase)\b", "tech_stack"),
    (r"\b(tailwind|bootstrap|mui|chakra|shadcn)\b", "tech_stack"),
    (r"\bgoogle\s+oauth\b", "auth_permissions"),
    (r"\bemail\s+(and\s+)?password\b", "auth_permissions"),
    (r"\bpaginate\b.{0,20}\b(\d+)\s+items\b", "scope_boundary"),
    (r"\bon\s+the\s+\w+\s+page\b", "scope_boundary"),
    (r"\bexisting\s+\w+\s+(api|endpoint|service)\b", "api_contract"),
    (r"\b(admin|user|guest|authenticated)\s+(only|role|user)\b", "auth_permissions"),
]


def infer_from_codebase(context_dir: str) -> list[dict]:
    """Scan codebase files to infer tech stack and patterns."""
    inferred = []
    base = Path(context_dir)

    if not base.exists():
        return inferred

    checks = [
        ("package.json", [
            (r'"react"', "React", "tech_stack"),
            (r'"next"', "Next.js", "tech_stack"),
            (r'"vue"', "Vue", "tech_stack"),
            (r'"typescript"', "TypeScript", "tech_stack"),
            (r'"tailwindcss"', "Tailwind CSS", "tech_stack"),
            (r'"prisma"', "Prisma ORM", "tech_stack"),
            (r'"zod"', "Zod validation", "tech_stack"),
            (r'"vitest"|"jest"', "Testing framework", "tech_stack"),
        ]),
        ("requirements.txt", [
            (r"django", "Django", "tech_stack"),
            (r"fastapi", "FastAPI", "tech_stack"),
            (r"flask", "Flask", "tech_stack"),
            (r"sqlalchemy", "SQLAlchemy", "tech_stack"),
        ]),
        ("Cargo.toml", [(r'\[package\]', "Rust", "tech_stack")]),
        ("go.mod", [(r'^module ', "Go", "tech_stack")]),
        ("pyproject.toml", [(r'^name\s*=', "Python project", "tech_stack")]),
        ("tailwind.config.js", [(r'.*', "Tailwind CSS", "tech_stack")]),
        ("tailwind.config.ts", [(r'.*', "Tailwind CSS", "tech_stack")]),
        (".eslintrc*", [(r'.*', "ESLint", "tech_stack")]),
        ("tsconfig.json", [(r'.*', "TypeScript", "tech_stack")]),
    ]

    for filename, patterns in checks:
        candidates = list(base.rglob(filename))[:1]
        if not candidates:
            # Also check root
            root_candidate = base / filename
            if root_candidate.exists():
                candidates = [root_candidate]

        for filepath in candidates:
            try:
                content = filepath.read_text(errors="ignore")
                for pattern, tech, domain in patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                        inferred.append({
                            "text": tech,
                            "type": "INFERABLE",
                            "domain": domain,
                            "source": str(filepath.relative_to(base)),
                            "inferable": True,
                            "blocks_others": False,
                        })
                        break  # One match per file
            except Exception:
                continue

    # Deduplicate by text
    seen = set()
    unique = []
    for item in inferred:
        if item["text"] not in seen:
            seen.add(item["text"])
            unique.append(item)

    return unique


def extract_clauses(text: str, context_dir: str = None) -> list[dict]:
    """Extract and classify all meaningful clauses from a prompt."""
    clauses = []
    lower = text.lower()

    # 1. CLEAR clauses from explicit patterns
    for pattern, domain in CLEAR_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            clauses.append({
                "text": match.group(0),
                "type": "CLEAR",
                "domain": domain,
                "inferable": False,
                "blocks_others": False,
            })

    # 2. AMBIGUOUS clauses from ambiguous words
    for word, (domain, question) in AMBIGUOUS_WORDS.items():
        if re.search(rf'\b{word}\b', lower):
            clause_type = "MISSING_OPTIONAL" if question is None else "AMBIGUOUS"
            clauses.append({
                "text": word,
                "type": clause_type,
                "domain": domain,
                "question_hint": question,
                "inferable": False,
                "blocks_others": domain in ("scope_boundary", "acceptance_criteria"),
            })

    # 3. MISSING_CRITICAL — acceptance criteria check
    # If no explicit success condition is stated
    has_success_condition = bool(re.search(
        r'\b(so that|so users? can|which (allows?|enables?|lets?)|'
        r'works? when|succeeds? when|passes? when|done when|'
        r'verif|confirm|test)\b',
        lower
    ))
    if not has_success_condition:
        clauses.append({
            "text": "acceptance_criteria",
            "type": "MISSING_CRITICAL",
            "domain": "acceptance_criteria",
            "question_hint": "How will you know this is done? (e.g., 'user can do X and see Y')",
            "inferable": False,
            "blocks_others": True,
        })

    # 4. MISSING_CRITICAL — scope boundary check
    has_scope_word = bool(re.search(
        r'\b(whole|entire|full|complete|all the|everything|all of)\b', lower
    ))
    word_count = len(text.split())
    if has_scope_word or (word_count < 10 and detect_trigger(text) == "IMPLEMENT"):
        # Very short or explicitly unbounded
        if not any(c["domain"] == "scope_boundary" for c in clauses):
            clauses.append({
                "text": "scope_boundary",
                "type": "MISSING_CRITICAL",
                "domain": "scope_boundary",
                "question_hint": "What's the scope? What's in vs out for this iteration?",
                "inferable": False,
                "blocks_others": True,
            })

    # 5. INFERABLE from codebase
    if context_dir:
        inferred = infer_from_codebase(context_dir)
        clauses.extend(inferred)

    # Deduplicate by (type, domain) keeping highest-priority type
    type_priority = {"MISSING_CRITICAL": 0, "AMBIGUOUS": 1, "MISSING_OPTIONAL": 2, "INFERABLE": 3, "CLEAR": 4}
    seen_domain = {}
    for c in clauses:
        key = c["domain"]
        if key not in seen_domain or type_priority[c["type"]] < type_priority[seen_domain[key]["type"]]:
            seen_domain[key] = c

    return list(seen_domain.values())


def generate_title(text: str) -> tuple[str, str]:
    """Generate a spec title and slug from the prompt."""
    # Remove trigger words
    cleaned = re.sub(
        r'^(build me|create|make|write|implement|add|develop|code|set up)\s+(a|an|the)?\s*',
        '', text.strip(), flags=re.IGNORECASE
    )
    cleaned = cleaned.strip().rstrip('.')

    # Title case
    title = ' '.join(word.capitalize() for word in cleaned.split())
    if len(title) > 60:
        title = title[:57] + '...'

    # Slug
    slug = re.sub(r'[^a-z0-9\s-]', '', cleaned.lower())
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = re.sub(r'-+', '-', slug)[:60]

    return title or "Feature Implementation", slug or "feature-implementation"


def detect_multi_feature(text: str) -> bool:
    """Check if the prompt describes multiple distinct features."""
    connectors = [
        r'\band\s+(also|then)\b',
        r'\bplus\s+\w',
        r'\bas\s+well\s+as\b',
        r'\b,\s*\w+\s+page\b',
        r'\bthen\s+(build|create|add)\b',
    ]
    return any(re.search(p, text, re.I) for p in connectors)


def parse_prompt(text: str, context_dir: str = None) -> dict:
    """Main entry point: parse a prompt and return full classification."""
    trigger = detect_trigger(text)
    clauses = extract_clauses(text, context_dir) if trigger != "SKIP" else []
    title, slug = generate_title(text)

    missing_critical = [c for c in clauses if c["type"] == "MISSING_CRITICAL"]
    ambiguous = [c for c in clauses if c["type"] == "AMBIGUOUS"]
    inferable = [c for c in clauses if c["type"] == "INFERABLE"]

    return {
        "trigger_type": trigger,
        "clauses": clauses,
        "missing_critical_count": len(missing_critical),
        "ambiguous_count": len(ambiguous),
        "inferable_items": [f"{c['text']} (from {c.get('source', 'context')})" for c in inferable],
        "feature_title": title,
        "feature_slug": slug,
        "is_continuation": trigger == "CONTINUE",
        "is_multi_feature": detect_multi_feature(text) if trigger == "IMPLEMENT" else False,
        "raw_prompt": text,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parse and classify an implementation prompt.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", type=str, help="Prompt text to parse")
    group.add_argument("--file", type=str, help="Path to prompt file")
    group.add_argument("--stdin", action="store_true", help="Read from stdin")

    parser.add_argument("--context-dir", type=str, default=None,
                        help="Path to codebase directory for inference")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--summary", action="store_true", help="Human-readable summary")

    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    result = parse_prompt(text.strip(), args.context_dir)

    if args.summary:
        print(f"Trigger:    {result['trigger_type']}")
        print(f"Title:      {result['feature_title']}")
        print(f"Slug:       {result['feature_slug']}")
        print(f"Missing:    {result['missing_critical_count']} critical, {result['ambiguous_count']} ambiguous")
        print(f"Inferable:  {len(result['inferable_items'])} items")
        if result['inferable_items']:
            for item in result['inferable_items']:
                print(f"  • {item}")
        print(f"\nClauses ({len(result['clauses'])}):")
        for c in result['clauses']:
            print(f"  [{c['type']:18}] {c['domain']:22} — {c['text'][:50]}")
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
