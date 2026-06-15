#!/usr/bin/env python3
"""
spec_generator.py — Micro-Spec Generator
Part of the spec-whisperer skill.

Generates a complete micro-spec from parsed prompt data + user answers.

Usage:
    python spec_generator.py --parse-result parse.json --answers answers.json
    python spec_generator.py --prompt "build login page" --answers '{"done":"user can sign in"}'
    python spec_generator.py --stdin  # reads full context JSON

Output JSON:
    {
        "spec_markdown": "# Spec: Login Page...",
        "confidence": 87,
        "badge": "🟢",
        "label": "Good",
        "risk": "Medium",
        "can_lock": true,
        "blockers": [],
        "title": "Login Page with Email Auth",
        "slug": "login-page-email-auth"
    }
"""

import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"


# ── Confidence Calculator ─────────────────────────────────────────────────────

def calculate_confidence(parsed: dict, answers: dict) -> tuple[int, list[str]]:
    """Returns (score, list_of_blockers)."""
    score = 100
    blockers = []

    clauses = parsed.get("clauses", [])
    missing_critical = [c for c in clauses if c["type"] == "MISSING_CRITICAL"]
    ambiguous = [c for c in clauses if c["type"] == "AMBIGUOUS"]

    # Count resolved vs unresolved
    answered_domains = set(answers.keys()) if answers else set()

    unresolved_critical = [c for c in missing_critical
                           if c["domain"] not in answered_domains]
    unresolved_ambiguous = [c for c in ambiguous
                            if c["domain"] not in answered_domains]

    # Deductions
    critical_deduction = min(len(unresolved_critical) * 20, 60)
    score -= critical_deduction

    ambiguous_deduction = min(len(unresolved_ambiguous) * 8, 32)
    score -= ambiguous_deduction

    # Acceptance criteria check
    has_ac = (
        "acceptance_criteria" in answered_domains
        or bool(answers.get("done"))
        or bool(answers.get("acceptance_criteria"))
        or bool(answers.get("success"))
    )
    if not has_ac and "acceptance_criteria" not in [c["domain"] for c in missing_critical]:
        # Prompt had no done condition and it wasn't flagged as critical
        score -= 10

    # Scope check
    if parsed.get("is_multi_feature"):
        score -= 12
        blockers.append("Multiple features detected — split into separate specs for clarity")

    # Tech context bonus
    if parsed.get("inferable_items"):
        score += min(len(parsed["inferable_items"]) * 3, 8)

    # Answers provided bonus
    if answers:
        answered_count = len([v for v in answers.values() if v and str(v).strip()])
        score += min(answered_count * 4, 10)

    # Examples in prompt bonus
    if re.search(r'\be\.g\.|for example|such as|like\b', parsed.get("raw_prompt", ""), re.I):
        score += 5

    score = max(0, min(100, score))

    # Build blocker list
    for c in unresolved_critical:
        hint = c.get("question_hint", f"Resolve: {c['domain']}")
        blockers.append(f"[{c['domain'].upper()}] {hint}")

    return score, blockers


def get_badge(score: int) -> tuple[str, str]:
    """Returns (badge_emoji, label)."""
    if score >= 90: return "🟢", "Excellent"
    if score >= 75: return "🟢", "Good"
    if score >= 60: return "🟡", "Acceptable"
    if score >= 45: return "🟠", "Marginal"
    if score >= 30: return "🔴", "Low"
    return "🚨", "Critical"


def get_risk(parsed: dict) -> str:
    """Determine risk level from clauses and domain."""
    clauses = parsed.get("clauses", [])
    all_text = " ".join([
        c.get("text", "") for c in clauses
    ] + [parsed.get("raw_prompt", "")]).lower()

    high_signals = [
        "auth", "password", "token", "secret", "payment", "billing",
        "stripe", "migration", "schema", "delete", "permission", "role", "security"
    ]
    medium_signals = [
        "api", "endpoint", "integration", "webhook", "data model",
        "multi-user", "concurrent", "performance", "cache", "external"
    ]

    if any(sig in all_text for sig in high_signals):
        return "High"
    if any(sig in all_text for sig in medium_signals):
        return "Medium"
    return "Low"


# ── Section Builders ──────────────────────────────────────────────────────────

def build_goal(parsed: dict, answers: dict) -> str:
    """Build one-sentence goal."""
    # Priority: explicit answer > prompt title > generic
    goal = (
        answers.get("goal")
        or answers.get("purpose")
        or answers.get("description")
    )
    if goal:
        # Clean and ensure it ends with a period and is one sentence
        goal = goal.strip().split('\n')[0]
        # Strip common filler prefixes so we don't double up
        import re as _re
        goal = _re.sub(r"^(user can|users can|the user can|users are able to|user is able to)\s+", "", goal, flags=_re.I).strip()
        # Wrap in "Enable users to..." only if it starts with a bare verb
        first_word = goal.split()[0].lower() if goal.split() else ""
        bare_verbs = {"enter","sign","log","click","view","see","access","create","submit","search","find","select","upload","download","navigate","use","get","fetch"}
        if first_word in bare_verbs:
            goal = f"Enable users to {goal[0].lower() + goal[1:]}"
        else:
            goal = goal[0].upper() + goal[1:] if goal else goal
        if not goal.endswith('.'):
            goal += '.'
        return goal

    # Derive from prompt
    title = parsed.get("feature_title", "Feature")
    prompt = parsed.get("raw_prompt", "").strip()

    # Try to extract user + action from prompt
    match = re.search(r'(user|admin|developer|customer)s?\s+can\s+(.+?)(?:\s+so|\.|$)', prompt, re.I)
    if match:
        return f"{match.group(0).strip().rstrip('.')}.".capitalize()

    # Build clean goal from prompt intent
    # Step 1: Strip the implementation verb (build/create/add...)
    clean = re.sub(
        r'^(build|create|make|write|implement|add|develop|code|set up)\s+(me\s+|us\s+)?(a|an|the)?\s*',
        '', prompt, flags=re.I
    ).strip()

    # Step 2: Map noun-phrase subjects to user-facing verb phrases
    NOUN_TO_GOAL = {
        r'login\s*page|sign.?in\s*page':    "sign in to the application",
        r'signup\s*page|register\s*page':   "create a new account",
        r'search\s*bar|search\s*input':     "search and filter content quickly",
        r'dashboard':                          "view key metrics at a glance",
        r'admin\s*panel':                     "manage application data as an admin",
        r'user\s*profile':                    "view and edit their profile",
        r'settings\s*page':                   "configure their preferences",
        r'checkout|payment':                   "complete a purchase securely",
        r'notification':                       "receive timely updates",
        r'report|analytics':                   "understand their data through reports",
        r'upload|file\s*upload':              "upload and manage files",
        r'list|table|grid':                    "view and manage a list of items",
        r'form|modal':                         "input and submit data efficiently",
        r'api|endpoint':                       "access data through an API",
        r'navigation|menu|navbar':             "navigate the application intuitively",
    }

    for pattern, goal_verb in NOUN_TO_GOAL.items():
        if re.search(pattern, clean, re.I):
            return f"Allow users to {goal_verb}."

    # Step 3: Fallback — use feature title words
    if clean:
        words = clean.rstrip('.').lower()
        return f"Implement {words} for the application."

    return f"Implement {title.lower()} functionality."


def build_in_scope(parsed: dict, answers: dict) -> list[str]:
    """Build in-scope bullet points."""
    items = []

    # From explicit scope answer
    scope_ans = answers.get("scope") or answers.get("in_scope")
    if scope_ans:
        raw_items = re.split(r'[,;\n]|(?<=[a-z])\s+(?:and|also)\s+', scope_ans, flags=re.I)
        for item in raw_items:
            item = item.strip().strip('•-').strip()
            if item and len(item) > 3:
                items.append(item[0].upper() + item[1:])

    # Fill from prompt + answers if still thin
    if len(items) < 2:
        title = parsed.get("feature_title", "Feature").lower()
        prompt = parsed.get("raw_prompt", "").lower()

        # Generic defaults per feature type
        if any(w in prompt for w in ["search", "filter"]):
            items = [
                "Search input field with real-time filtering",
                f"Filter applied to {answers.get('fields', 'relevant fields')}",
                "Empty state message when no results found",
                "Clear/reset button when search is active",
            ]
        elif any(w in prompt for w in ["login", "sign in", "auth"]):
            method = answers.get("auth_method", answers.get("method", "email and password"))
            redirect = answers.get("redirect", "/dashboard")
            items = [
                f"Login form with {method}",
                "Form validation with inline error messages",
                f"Redirect to {redirect} on successful login",
                "Loading state during authentication request",
            ]
        elif any(w in prompt for w in ["list", "table", "grid"]):
            items = [
                f"{title.capitalize()} display with all required data fields",
                "Loading state while data is fetched",
                "Empty state when no items exist",
                "Error state if data fetch fails",
            ]
        elif any(w in prompt for w in ["form", "create", "add", "new"]):
            items = [
                f"{title.capitalize()} form with required fields",
                "Client-side validation before submission",
                "Success feedback on submission",
                "Error handling for failed submissions",
            ]
        else:
            items = [
                f"Core {title} functionality as described",
                "Loading and error states",
                "Responsive layout matching existing design system",
            ]

    return items[:8]  # Cap at 8


def build_out_of_scope(parsed: dict, answers: dict, in_scope: list[str]) -> list[str]:
    """Build out-of-scope bullet points."""
    items = []

    oos_ans = answers.get("out_of_scope") or answers.get("not_included")
    if oos_ans:
        raw_items = re.split(r'[,;\n]', oos_ans)
        for item in raw_items:
            item = item.strip().strip('•-').strip()
            if item and len(item) > 3:
                items.append(item[0].upper() + item[1:])

    if len(items) < 2:
        prompt = parsed.get("raw_prompt", "").lower()

        if any(w in prompt for w in ["search", "filter"]):
            items = [
                "Backend/server-side search (client-side filtering only)",
                "Advanced filters (category, price range, date range)",
                "Search history or saved searches",
                "Search analytics or tracking",
            ]
        elif any(w in prompt for w in ["login", "sign in"]):
            items = [
                "User registration / sign-up flow",
                "Password reset / forgot password",
                "Two-factor authentication (2FA)",
                "Social login beyond what is specified",
            ]
        elif any(w in prompt for w in ["list", "table"]):
            items = [
                "Create / edit / delete operations (read-only list)",
                "Export to CSV or PDF",
                "Advanced filtering or sorting beyond basic",
            ]
        elif any(w in prompt for w in ["form", "create"]):
            items = [
                "Edit / update existing records",
                "Bulk create operations",
                "File or image uploads",
            ]
        else:
            items = [
                "Future enhancements beyond this iteration",
                "Performance optimizations (deferred)",
                "Third-party integrations not specified",
            ]

    return items[:5]


def build_acceptance_criteria(parsed: dict, answers: dict) -> list[str]:
    """Build testable acceptance criteria."""
    criteria = []

    done = (
        answers.get("done")
        or answers.get("acceptance_criteria")
        or answers.get("success")
    )

    if done:
        # Use the full done statement as the primary criterion
        # Don't split on "and" — it destroys the meaning
        done_clean = done.strip().strip('•-').strip()
        if done_clean and len(done_clean) > 5:
            if "verif" not in done_clean.lower() and " — " not in done_clean:
                verif = "completing the full flow end-to-end"
                criteria.append(f"☐ {done_clean[0].upper() + done_clean[1:]} — verifiable by {verif}")
            else:
                criteria.append(f"☐ {done_clean[0].upper() + done_clean[1:]}")

    # Fill with smart defaults if thin
    if len(criteria) < 3:
        prompt = parsed.get("raw_prompt", "").lower()

        if any(w in prompt for w in ["search", "filter"]):
            criteria = [
                "☐ Typing in the search field filters the list within 300ms — verifiable by entering a query and observing results",
                "☐ Clearing the search field restores the full unfiltered list — verifiable by clearing input and confirming all items return",
                "☐ Empty state message appears when no items match — verifiable by entering a nonsense string",
            ]
        elif any(w in prompt for w in ["login", "sign in", "auth"]):
            auth_method = answers.get("auth_method", "email and password")
            redirect = answers.get("redirect", "/dashboard")
            criteria = [
                f"☐ User can sign in with {auth_method} and land on {redirect} — verifiable by completing sign-in flow end-to-end",
                "☐ Invalid credentials show an inline error message — verifiable by entering wrong password",
                "☐ Form is disabled and shows loading state during sign-in request — verifiable by slow-network simulation",
            ]
        elif any(w in prompt for w in ["form", "create", "add"]):
            criteria = [
                "☐ Submitting valid form data creates a new record and shows success feedback — verifiable by completing the form and checking the list",
                "☐ Submitting with empty required fields shows inline validation errors — verifiable by clicking submit on an empty form",
                "☐ Network error on submission shows an error message without losing form data — verifiable by simulating offline mode",
            ]
        else:
            title = parsed.get("feature_title", "feature")
            criteria = [
                f"☐ {title} renders correctly with valid data — verifiable by loading the page with test data",
                "☐ Loading state is shown while data is being fetched — verifiable by slow-network simulation",
                "☐ Error state is shown if data fetch fails — verifiable by mocking a failed API response",
            ]

    return criteria[:6]


def build_edge_cases(parsed: dict, answers: dict) -> list[str]:
    """Build edge case list."""
    prompt = parsed.get("raw_prompt", "").lower()
    cases = []

    edge_ans = answers.get("edge_cases") or answers.get("edge")
    if edge_ans:
        raw = re.split(r'[;\n]', edge_ans)
        for item in raw:
            item = item.strip().strip('•-').strip()
            if ':' not in item and len(item) > 5:
                item = f"Unexpected input: {item}"
            if item:
                cases.append(f"• {item}")

    if len(cases) < 2:
        if any(w in prompt for w in ["search", "filter"]):
            cases = [
                "• Empty query: show full unfiltered list",
                "• No results: show 'No items match \"{query}\"' with a clear link",
                "• Special characters (< > & \"): sanitize and search safely",
                "• Very long query (> 100 chars): truncate display, keep functional",
            ]
        elif any(w in prompt for w in ["login", "sign in"]):
            cases = [
                "• Invalid credentials: show specific error without revealing which field is wrong",
                "• Network timeout: show retry option, do not clear form",
                "• Already logged in: redirect to dashboard immediately",
                "• Account locked: show account-locked message with support contact",
            ]
        elif any(w in prompt for w in ["form", "create"]):
            cases = [
                "• Double submit: disable submit button after first click",
                "• Network error: show error toast, keep form data intact",
                "• Required field empty: show inline validation before submit",
                "• Session expired mid-form: redirect to login, preserve form state",
            ]
        elif any(w in prompt for w in ["list", "table"]):
            cases = [
                "• Empty list: show empty state with helpful message",
                "• Single item: layout remains correct",
                "• Very long list (1000+ items): verify performance / pagination",
                "• API error: show error state with retry button",
            ]
        else:
            cases = [
                "• Network failure: graceful error state with retry option",
                "• Empty data: appropriate empty state shown",
                "• Unexpected API response shape: handled without crashing",
            ]

    return cases[:5]


def build_assumptions(parsed: dict) -> list[str]:
    """Build assumptions list from CLEAR and INFERABLE clauses."""
    assumptions = []
    clauses = parsed.get("clauses", [])

    for c in clauses:
        if c["type"] == "CLEAR":
            text = c.get("text", "").strip()
            if text:
                assumptions.append(f"• {text[0].upper() + text[1:]} [STATED]")
        elif c["type"] == "INFERABLE":
            text = c.get("text", "").strip()
            source = c.get("source", "codebase context")
            if text:
                assumptions.append(f"• {text[0].upper() + text[1:]} [INFERRED from {source}]")

    # Always add standard assumptions if thin
    if len(assumptions) < 2:
        prompt = parsed.get("raw_prompt", "").lower()
        if "react" not in prompt and not any("React" in a for a in assumptions):
            assumptions.append("• Framework: to be confirmed from codebase [INFERRED]")
        assumptions.append("• Styling: follows existing design system [INFERRED from codebase]")
        assumptions.append("• No new database schema changes required unless stated [INFERRED]")

    return assumptions[:12]


def build_tech_constraints(parsed: dict, answers: dict) -> list[str]:
    """Build tech constraints from inferred + stated info."""
    constraints = []
    clauses = parsed.get("clauses", [])

    # From CLEAR + INFERABLE tech_stack clauses
    for c in clauses:
        if c.get("domain") == "tech_stack" and c["type"] in ("CLEAR", "INFERABLE"):
            constraints.append(f"• {c['text']}")

    tech_ans = answers.get("tech") or answers.get("tech_stack") or answers.get("constraints")
    if tech_ans:
        for item in re.split(r'[,;\n]', tech_ans):
            item = item.strip().strip('•-').strip()
            if item:
                constraints.append(f"• {item}")

    if not constraints:
        constraints = [
            "• Language / framework: see codebase (to be confirmed)",
            "• Follow existing code patterns and component conventions",
            "• No new dependencies without justification",
        ]

    return constraints[:8]


def build_tbd(parsed: dict) -> list[str]:
    """Build TBD (won't block) list from MISSING_OPTIONAL clauses."""
    tbd = []
    clauses = parsed.get("clauses", [])

    for c in clauses:
        if c["type"] == "MISSING_OPTIONAL":
            domain = c.get("domain", "")
            text = c.get("text", "")
            label = domain.replace("_", " ").title()
            if text:
                tbd.append(f"• {label}: {text} (sensible default will be used)")
            else:
                tbd.append(f"• {label}: not specified (default applied)")

    if not tbd:
        tbd = ["• Error message copy (reasonable defaults used)"]

    return tbd[:4]


# ── Main Generator ────────────────────────────────────────────────────────────

def generate_spec(parsed: dict, answers: dict = None) -> dict:
    """Generate a complete micro-spec from parsed data + answers."""
    if answers is None:
        answers = {}

    confidence, blockers = calculate_confidence(parsed, answers)
    badge, label = get_badge(confidence)
    risk = get_risk(parsed)

    title = parsed.get("feature_title", "Feature Implementation")
    slug = parsed.get("feature_slug", "feature-implementation")
    date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()
    status = "LOCKED" if confidence >= 45 and not blockers else "DRAFT"
    spec_id = f"{date}-{slug[:40]}"

    # Build sections
    goal = build_goal(parsed, answers)
    in_scope = build_in_scope(parsed, answers)
    out_of_scope = build_out_of_scope(parsed, answers, in_scope)
    acceptance_criteria = build_acceptance_criteria(parsed, answers)
    edge_cases = build_edge_cases(parsed, answers)
    assumptions = build_assumptions(parsed)
    tech_constraints = build_tech_constraints(parsed, answers)
    tbd = build_tbd(parsed)

    # Assemble markdown
    in_scope_md = "\n".join(f"• {i}" for i in in_scope)
    oos_md = "\n".join(f"• {i}" for i in out_of_scope)
    ac_md = "\n".join(acceptance_criteria)
    ec_md = "\n".join(edge_cases)
    assumptions_md = "\n".join(assumptions)
    tech_md = "\n".join(tech_constraints)
    tbd_md = "\n".join(tbd)

    blocker_section = ""
    if blockers and confidence < 60:
        blocker_lines = "\n".join(f"• {b}" for b in blockers)
        blocker_section = f"\n---\n\n⚠️ **BLOCKERS** (resolve before locking):\n{blocker_lines}\n"

    spec_md = f"""# Spec: {title}

**Date:** {date} | **Status:** {status}
**Confidence:** {confidence}% {badge} {label}  |  **Risk:** {risk}

---

## Goal

{goal}

---

## In Scope

{in_scope_md}

---

## Out of Scope

{oos_md}

---

## Acceptance Criteria

{ac_md}

---

## Edge Cases

{ec_md}

---

## Assumptions

{assumptions_md}

---

## Tech Constraints

{tech_md}

---

## TBD (Won't Block)

{tbd_md}

---

_Generated by spec-whisperer v1.0.0 | {timestamp}_
_Spec ID: {spec_id}_
{blocker_section}"""

    return {
        "spec_markdown": spec_md.strip(),
        "confidence": confidence,
        "badge": badge,
        "label": label,
        "risk": risk,
        "status": status,
        "can_lock": confidence >= 30 and len(blockers) == 0,
        "blockers": blockers,
        "title": title,
        "slug": slug,
        "spec_id": spec_id,
        "date": date,
        "sections": {
            "goal": goal,
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "acceptance_criteria": acceptance_criteria,
            "edge_cases": edge_cases,
            "assumptions": assumptions,
            "tech_constraints": tech_constraints,
            "tbd": tbd,
        }
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate micro-spec from parsed prompt data.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--parse-result", type=str, help="Path to prompt_parser.py output JSON")
    group.add_argument("--prompt", type=str, help="Raw prompt (will be parsed inline)")
    group.add_argument("--stdin", action="store_true", help="Read full context JSON from stdin")

    parser.add_argument("--answers", type=str, default="{}", help="JSON dict of user answers")
    parser.add_argument("--answers-file", type=str, help="Path to answers JSON file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--markdown-only", action="store_true", help="Output only the spec markdown")

    args = parser.parse_args()

    # Load answers
    if args.answers_file:
        answers = json.loads(Path(args.answers_file).read_text())
    else:
        try:
            answers = json.loads(args.answers)
        except json.JSONDecodeError:
            answers = {}

    # Load parsed data
    if args.parse_result:
        parsed = json.loads(Path(args.parse_result).read_text())
    elif args.prompt:
        from prompt_parser import parse_prompt
        parsed = parse_prompt(args.prompt)
    else:
        data = json.loads(sys.stdin.read())
        parsed = data.get("parsed", data)
        if not answers:
            answers = data.get("answers", {})

    result = generate_spec(parsed, answers)

    if args.markdown_only:
        print(result["spec_markdown"])
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
