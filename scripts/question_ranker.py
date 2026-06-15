#!/usr/bin/env python3
"""
question_ranker.py — Clarification Question Ranker
Part of the spec-whisperer skill.

Takes classified clauses and selects the top 3 highest-impact questions.

Usage:
    python question_ranker.py --clauses '[{"type":"MISSING_CRITICAL","domain":"acceptance_criteria",...}]'
    python question_ranker.py --file clauses.json
    python question_ranker.py --stdin

Output JSON:
    {
        "questions": [
            {
                "rank": 1,
                "domain": "acceptance_criteria",
                "impact_score": 75,
                "question": "How will you know this is done?",
                "example": "e.g., 'user enters email/password and lands on /dashboard'"
            },
            ...
        ],
        "total_candidates": 5,
        "questions_count": 2,
        "formatted_message": "Before I start, I have 2 quick questions:\n\n1. ..."
    }
"""

import sys
import json
import argparse
from pathlib import Path


# ── Impact Score Weights ──────────────────────────────────────────────────────

TYPE_WEIGHT = {
    "MISSING_CRITICAL": 40,
    "AMBIGUOUS": 20,
    "MISSING_OPTIONAL": -999,  # Never ask
    "CLEAR": -999,
    "INFERABLE": -999,
}

DOMAIN_WEIGHT = {
    "acceptance_criteria": 35,
    "scope_boundary":      30,
    "data_model":          28,
    "auth_permissions":    25,
    "api_contract":        22,
    "error_handling":      18,
    "ui_behavior":         15,
    "performance":         12,
    "tech_stack":          10,
    "copy_text":            2,
    "style_polish":         2,
}

BLOCKS_OTHERS_BONUS = 20
INFERABLE_PENALTY = -999
MIN_SCORE_TO_ASK = 25  # Questions below this score are not worth asking


# ── Question Templates ────────────────────────────────────────────────────────

QUESTION_TEMPLATES = {
    "acceptance_criteria": {
        "question": "How will you know this is working correctly?",
        "example": "e.g., 'user can submit the form and see a success message'",
        "label": "Done condition",
    },
    "scope_boundary": {
        "question": "What's included in this feature — and what's explicitly NOT included?",
        "example": "e.g., 'just the list view — no create/edit/delete for now'",
        "label": "Scope",
    },
    "data_model": {
        "question": "Where does the data come from and what shape is it?",
        "example": "e.g., 'from the existing /api/products endpoint, which returns {id, name, price}'",
        "label": "Data",
    },
    "auth_permissions": {
        "question": "Who can see and use this feature?",
        "example": "e.g., 'all logged-in users' or 'admin role only'",
        "label": "Access",
    },
    "api_contract": {
        "question": "What API should this use — existing endpoint or new one?",
        "example": "e.g., 'GET /api/orders already exists' or 'we need to create it'",
        "label": "API",
    },
    "error_handling": {
        "question": "What should happen when things go wrong or the data is empty?",
        "example": "e.g., 'show an error toast if the API fails, empty state says No items yet'",
        "label": "Error states",
    },
    "ui_behavior": {
        "question": "How should the interaction work?",
        "example": "e.g., 'filter as user types' vs 'only when they press Enter'",
        "label": "Behavior",
    },
    "performance": {
        "question": "What's the performance target for this feature?",
        "example": "e.g., 'search results within 300ms' or 'no strict requirement'",
        "label": "Performance",
    },
}

# Ambiguous word → specific question override
AMBIGUOUS_OVERRIDES = {
    "real-time": {
        "question": "How real-time does this need to be?",
        "example": "e.g., 'live WebSocket updates' vs 'refresh every 5 seconds' vs 'on page load'",
        "label": "Real-time behavior",
    },
    "fast": {
        "question": "What's the performance target?",
        "example": "e.g., 'results appear within 500ms' or 'sub-second page loads'",
        "label": "Performance target",
    },
    "simple": {
        "question": "What does 'simple' mean here?",
        "example": "e.g., 'minimal features for MVP' or 'clean minimal UI'",
        "label": "Simplicity definition",
    },
    "full": {
        "question": "What does 'full' include — what's in scope?",
        "example": "e.g., 'list + detail + create + edit + delete' or just 'list + detail'?",
        "label": "Full scope",
    },
    "complete": {
        "question": "What does 'complete' include?",
        "example": "e.g., list all the features you have in mind",
        "label": "Complete scope",
    },
    "live": {
        "question": "How live does the data need to be?",
        "example": "e.g., 'WebSocket push' vs 'reload on focus' vs 'manual refresh'",
        "label": "Data freshness",
    },
}


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_clause(clause: dict) -> int:
    clause_type = clause.get("type", "CLEAR")
    domain = clause.get("domain", "")
    is_inferable = clause.get("inferable", False)
    blocks_others = clause.get("blocks_others", False)

    if is_inferable:
        return INFERABLE_PENALTY

    type_w = TYPE_WEIGHT.get(clause_type, -999)
    if type_w < 0:
        return type_w

    domain_w = DOMAIN_WEIGHT.get(domain, 8)
    blocks_bonus = BLOCKS_OTHERS_BONUS if blocks_others else 0

    return type_w + domain_w + blocks_bonus


# ── Question Builder ──────────────────────────────────────────────────────────

def build_question(clause: dict) -> dict:
    domain = clause.get("domain", "")
    clause_text = clause.get("text", "")
    question_hint = clause.get("question_hint", "")

    # Check for specific ambiguous word override
    if clause_text.lower() in AMBIGUOUS_OVERRIDES:
        override = AMBIGUOUS_OVERRIDES[clause_text.lower()]
        return {
            "domain": domain,
            "label": override["label"],
            "question": override["question"],
            "example": override["example"],
            "clause_type": clause.get("type"),
            "clause_text": clause_text,
        }

    # Use domain template
    if domain in QUESTION_TEMPLATES:
        template = QUESTION_TEMPLATES[domain]
        return {
            "domain": domain,
            "label": template["label"],
            "question": template["question"],
            "example": template["example"],
            "clause_type": clause.get("type"),
            "clause_text": clause_text,
        }

    # Fallback: use the question_hint from the clause itself
    if question_hint:
        return {
            "domain": domain,
            "label": domain.replace("_", " ").title(),
            "question": question_hint,
            "example": "",
            "clause_type": clause.get("type"),
            "clause_text": clause_text,
        }

    return None


# ── Formatter ─────────────────────────────────────────────────────────────────

def format_questions_message(questions: list[dict]) -> str:
    n = len(questions)
    if n == 0:
        return ""

    plural = "s" if n > 1 else ""
    lines = [f"Before I start, I have {n} quick question{plural}:\n"]

    for i, q in enumerate(questions, 1):
        label = q.get("label", q["domain"].replace("_", " ").title())
        question = q["question"]
        example = q.get("example", "")

        lines.append(f"{i}. **[{label}]** {question}")
        if example:
            lines.append(f"   ({example})")
        lines.append("")

    return "\n".join(lines).rstrip()


# ── Main Ranker ───────────────────────────────────────────────────────────────

def rank_questions(clauses: list[dict], max_questions: int = 3) -> dict:
    # Score all clauses
    scored = []
    for clause in clauses:
        score = score_clause(clause)
        if score >= MIN_SCORE_TO_ASK:
            scored.append((score, clause))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate by domain (keep highest-scored per domain)
    seen_domains = set()
    top_scored = []
    for score, clause in scored:
        domain = clause.get("domain", "")
        if domain not in seen_domains:
            seen_domains.add(domain)
            top_scored.append((score, clause))

    # Take top max_questions
    selected = top_scored[:max_questions]

    # Build question objects
    questions = []
    for rank, (score, clause) in enumerate(selected, 1):
        q = build_question(clause)
        if q:
            q["rank"] = rank
            q["impact_score"] = score
            questions.append(q)

    formatted = format_questions_message(questions)

    return {
        "questions": questions,
        "total_candidates": len(scored),
        "questions_count": len(questions),
        "formatted_message": formatted,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rank clarification questions from classified prompt clauses."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--clauses", type=str, help="JSON array of classified clauses")
    group.add_argument("--file", type=str, help="Path to clauses JSON file")
    group.add_argument("--stdin", action="store_true", help="Read clauses JSON from stdin")

    parser.add_argument("--max", type=int, default=3, help="Max questions to select (default: 3)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--message-only", action="store_true", help="Output only the formatted message")

    args = parser.parse_args()

    if args.clauses:
        raw = args.clauses
    elif args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    try:
        clauses = json.loads(raw)
        if isinstance(clauses, dict) and "clauses" in clauses:
            clauses = clauses["clauses"]
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = rank_questions(clauses, args.max)

    if args.message_only:
        print(result["formatted_message"])
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
