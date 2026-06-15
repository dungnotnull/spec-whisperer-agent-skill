#!/usr/bin/env python3
"""
spec_whisperer.py — Main Orchestrator
Part of the spec-whisperer skill.

Runs the full 4-phase spec-whisperer flow:
  Phase 0: Trigger detection
  Phase 1: Ambiguity triage
  Phase 2: Question selection (max 3)
  Phase 3: Spec generation + confidence score
  Phase 4: Lock & save

Usage:
    python spec_whisperer.py --prompt "build a login page"
    python spec_whisperer.py --interactive
    python spec_whisperer.py --hook-mode               # Claude Code hook
    python spec_whisperer.py --load 2026-06-07-login   # Load existing spec
    python spec_whisperer.py --list                     # List saved specs
    python spec_whisperer.py --find "login"             # Search specs
    python spec_whisperer.py --status                   # Show .specs/ status
"""

import sys
import os
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

# ── ANSI ─────────────────────────────────────────────────────────────────────
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
RESET  = "\033[0m"
GHOST  = "👻"

def ansi(text, *codes):
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + RESET

def header(title):
    bar = "━" * 54
    print(f"\n{ansi(bar, CYAN)}")
    print(f"{ansi(f'  {GHOST}  spec-whisperer — {title}', BOLD + CYAN)}")
    print(f"{ansi(bar, CYAN)}\n")

def section(title):
    print(f"\n{ansi('─── ' + title + ' ' + '─' * max(0, 50 - len(title)), DIM)}")

def ok(msg):   print(f"{ansi('✅', '')} {msg}")
def warn(msg): print(f"{ansi('⚠️', '')}  {msg}")
def info(msg): print(f"{ansi('·', DIM)} {msg}")
def err(msg):  print(f"{ansi('✗', RED + BOLD)} {msg}", file=sys.stderr)


# ── Core Flow ─────────────────────────────────────────────────────────────────

def run_triage(prompt: str, context_dir: str = None) -> dict:
    """Phase 0+1: Detect trigger and classify clauses."""
    from prompt_parser import parse_prompt
    return parse_prompt(prompt, context_dir)


def run_questions(parsed: dict) -> dict:
    """Phase 2: Select top 3 questions."""
    from question_ranker import rank_questions
    clauses = parsed.get("clauses", [])
    return rank_questions(clauses, max_questions=3)


def run_generate(parsed: dict, answers: dict) -> dict:
    """Phase 3: Generate spec + confidence score."""
    from spec_generator import generate_spec
    return generate_spec(parsed, answers)


def run_save(spec_result: dict, specs_dir: str = ".specs") -> str:
    """Phase 4: Save locked spec."""
    from spec_store import save_spec
    return save_spec(
        spec_markdown=spec_result["spec_markdown"],
        title=spec_result["title"],
        slug=spec_result["slug"],
        confidence=spec_result["confidence"],
        specs_dir=specs_dir,
        status=spec_result.get("status", "LOCKED"),
        risk=spec_result.get("risk", "Low"),
    )


# ── Display Helpers ────────────────────────────────────────────────────────────

def display_spec(spec_result: dict):
    """Render spec in terminal with color coding."""
    confidence = spec_result["confidence"]
    badge = spec_result["badge"]
    label = spec_result["label"]
    risk = spec_result["risk"]
    can_lock = spec_result["can_lock"]
    blockers = spec_result.get("blockers", [])

    # Confidence bar
    bar_len = 40
    filled = int((confidence / 100) * bar_len)
    empty = bar_len - filled

    if confidence >= 75:
        bar_color = GREEN
    elif confidence >= 50:
        bar_color = YELLOW
    else:
        bar_color = RED

    conf_bar = ansi("█" * filled, bar_color) + ansi("░" * empty, DIM)
    conf_line = f"  Confidence: {conf_bar} {confidence}% {badge} {label}  |  Risk: {risk}"

    section("SPEC DRAFT")
    print(conf_line)
    print()

    # Print spec with highlighted sections
    md = spec_result["spec_markdown"]
    for line in md.split("\n"):
        if line.startswith("# Spec:"):
            print(ansi(line, BOLD + CYAN))
        elif line.startswith("**"):
            print(ansi(line, DIM))
        elif line.startswith("## "):
            print(ansi(line, BOLD))
        elif line.startswith("☐ "):
            print(ansi(line, GREEN))
        elif line.startswith("• ") and "[STATED]" in line:
            print(ansi(line, DIM))
        elif line.startswith("• ") and "[INFERRED" in line:
            print(ansi(line, DIM))
        elif "MISSING_CRITICAL" in line or "BLOCKER" in line:
            print(ansi(line, RED))
        else:
            print(line)

    if blockers:
        print()
        print(ansi("  ⚠️  BLOCKERS:", YELLOW + BOLD))
        for b in blockers:
            print(ansi(f"  • {b}", YELLOW))


def prompt_approval(spec_result: dict, specs_dir: str = ".specs") -> str:
    """Show approval prompt and return choice."""
    confidence = spec_result["confidence"]
    can_lock = spec_result["can_lock"]

    print()
    if can_lock:
        print(f"  {ansi('[Y]', GREEN + BOLD)} Lock spec and start implementing")
        print(f"  {ansi('[E]', YELLOW + BOLD)} Edit spec first")
        print(f"  {ansi('[R]', RED + BOLD)} Reject — I'll rephrase my request")
    else:
        print(ansi(f"  ⚠️  Confidence {confidence}% is too low to lock — resolve blockers first", YELLOW))
        print(f"  {ansi('[E]', YELLOW + BOLD)} Edit spec to resolve blockers")
        print(f"  {ansi('[R]', RED + BOLD)} Reject — I'll rephrase")

    print()
    try:
        choice = input(f"  {ansi(GHOST, CYAN)} Your choice: ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        print()
        return "R"

    return choice or ("Y" if can_lock else "E")


def handle_approval(choice: str, spec_result: dict, specs_dir: str = ".specs") -> bool:
    """Handle user approval choice. Returns True if implementation should proceed."""
    if choice == "Y":
        if not spec_result["can_lock"]:
            warn("Cannot lock — confidence too low. Edit spec first.")
            return False

        path = run_save(spec_result, specs_dir)
        ok(f"Spec locked → {path}")
        print()
        print(ansi("  Ready to implement. Starting with first acceptance criterion.", DIM))
        return True

    elif choice == "E":
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_spec.md", delete=False, encoding="utf-8"
        ) as f:
            f.write(spec_result["spec_markdown"])
            tmp = f.name

        os.system(f"{editor} {tmp}")
        edited_md = Path(tmp).read_text(encoding="utf-8")
        Path(tmp).unlink(missing_ok=True)

        # Re-generate from edited markdown
        spec_result["spec_markdown"] = edited_md
        spec_result["status"] = "LOCKED"

        path = run_save(spec_result, specs_dir)
        ok(f"Edited spec locked → {path}")
        return True

    else:  # R
        print(ansi(f"\n  {GHOST}  No problem — rephrase your request and I'll run a fresh spec.\n", DIM))
        return False


# ── Interactive Flow ──────────────────────────────────────────────────────────

def run_interactive_flow(
    prompt: str,
    context_dir: str = None,
    specs_dir: str = ".specs",
    skip_questions: bool = False,
) -> dict:
    """Full interactive 4-phase flow. Returns spec result dict."""

    header("analyzing your request")

    # Phase 0+1: Triage
    info("Reading prompt and classifying clauses...")
    parsed = run_triage(prompt, context_dir)

    trigger = parsed.get("trigger_type", "IMPLEMENT")

    if trigger == "SKIP":
        info("This looks like a question, not an implementation request — skipping spec.")
        return {"trigger": "SKIP"}

    if trigger == "CONTINUE":
        from spec_store import find_specs
        results = find_specs(prompt[:50], specs_dir)
        if results:
            latest = results[0]
            print(f"\n  Found existing spec: {ansi(latest['title'], BOLD)}")
            print(f"  Confidence: {latest['confidence']}% | Status: {latest['status']}")
            try:
                choice = input(f"\n  Continue with this spec? [Y/update/new]: ").strip().upper()
            except (EOFInput, KeyboardInterrupt):
                choice = "Y"

            if choice != "N" and choice != "NEW":
                spec = load_existing_spec(latest["id"], specs_dir)
                if spec:
                    ok(f"Loaded spec: {latest['title']}")
                    return spec

    if parsed.get("is_multi_feature"):
        warn("Multiple features detected in one request.")
        print(ansi("  spec-whisperer handles one feature at a time.", DIM))
        print(ansi("  Which feature should we spec first? (or rephrase as a single feature)\n", DIM))
        try:
            rephrased = input("  Focus on: ").strip()
        except (EOFError, KeyboardInterrupt):
            rephrased = prompt
        if rephrased:
            prompt = rephrased
            parsed = run_triage(prompt, context_dir)

    # Phase 2: Questions
    answers = {}
    if not skip_questions:
        questions_result = run_questions(parsed)
        questions = questions_result.get("questions", [])

        if questions:
            section("CLARIFICATION")
            print(questions_result["formatted_message"])

            try:
                print(ansi("\n  Your answers (press Enter twice when done):", DIM))
                answer_lines = []
                while True:
                    try:
                        line = input("  > ").strip()
                        if not line and answer_lines:
                            break
                        if line:
                            answer_lines.append(line)
                    except EOFError:
                        break

                raw_answers = " ".join(answer_lines)

                # Parse answers back to domains
                for i, q in enumerate(questions):
                    domain = q["domain"]
                    if raw_answers:
                        answers[domain] = raw_answers
                        # Try to split numbered answers
                        m = re.search(rf'{i+1}\.\s+(.+?)(?=\d\.|$)', raw_answers, re.DOTALL)
                        if m:
                            answers[domain] = m.group(1).strip()

            except (EOFError, KeyboardInterrupt):
                info("Skipping questions — generating spec from available info.")

    # Phase 3: Generate
    section("GENERATING SPEC")
    spec_result = run_generate(parsed, answers)

    display_spec(spec_result)

    # Phase 4: Lock
    choice = prompt_approval(spec_result, specs_dir)
    handle_approval(choice, spec_result, specs_dir)

    return spec_result


def load_existing_spec(spec_id: str, specs_dir: str = ".specs") -> dict | None:
    from spec_store import load_spec
    spec = load_spec(spec_id, specs_dir)
    if spec:
        return {
            "spec_markdown": spec.get("markdown", ""),
            "title": spec.get("title", ""),
            "slug": spec.get("slug", ""),
            "confidence": spec.get("confidence", 75),
            "badge": "🟢",
            "label": "Good",
            "risk": spec.get("risk", "Low"),
            "can_lock": True,
            "blockers": [],
            "status": spec.get("status", "LOCKED"),
        }
    return None


# ── Hook Mode ────────────────────────────────────────────────────────────────

def run_hook_mode(specs_dir: str = ".specs"):
    """
    Called by Claude Code PreToolUse hook.
    Reads the pending tool input from environment / stdin.
    If it looks like an implementation request, run spec flow.
    Otherwise exit cleanly.
    """
    # In hook mode, the prompt comes from the last human message
    # Claude Code passes tool context via environment
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    human_turn = os.environ.get("CLAUDE_LAST_HUMAN_MESSAGE", "")

    check_text = human_turn or tool_input

    if not check_text:
        sys.exit(0)  # Nothing to check

    from prompt_parser import detect_trigger
    trigger = detect_trigger(check_text)

    if trigger == "IMPLEMENT":
        # Check if a spec already exists for this session
        from spec_store import find_specs
        existing = find_specs(check_text[:40], specs_dir)
        if existing and existing[0].get("status") == "LOCKED":
            # Spec already exists — proceed
            info(f"Using existing spec: {existing[0]['title']}")
            sys.exit(0)

        # Run abbreviated flow (no interactive prompt in hook mode)
        parsed = run_triage(check_text)
        questions_result = run_questions(parsed)
        spec_result = run_generate(parsed, {})

        if spec_result["confidence"] >= 45:
            # Auto-present spec, save as draft
            spec_result["status"] = "DRAFT"
            path = run_save(spec_result, specs_dir)
            print(f"\n{GHOST} spec-whisperer: spec draft created → {path}")
            print(f"   Confidence: {spec_result['confidence']}% {spec_result['badge']}")
            print(f"   Run: python spec_whisperer.py --load {spec_result['spec_id']} to review\n")

    sys.exit(0)  # Always exit 0 — never block the tool


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=f"{GHOST} spec-whisperer — Spec before you code."
    )
    parser.add_argument("--prompt", type=str, help="Implementation request to spec")
    parser.add_argument("--interactive", action="store_true", help="Prompt for input interactively")
    parser.add_argument("--hook-mode", action="store_true", help="Claude Code hook mode")
    parser.add_argument("--load", type=str, metavar="SPEC_ID", help="Load an existing spec")
    parser.add_argument("--find", type=str, metavar="QUERY", help="Search saved specs")
    parser.add_argument("--list", action="store_true", help="List all saved specs")
    parser.add_argument("--status", action="store_true", help="Show .specs/ directory status")
    parser.add_argument("--context-dir", type=str, default=None,
                        help="Codebase directory for tech stack inference")
    parser.add_argument("--specs-dir", type=str, default=".specs",
                        help="Directory to store specs")
    parser.add_argument("--skip-questions", action="store_true",
                        help="Skip clarification questions, generate from prompt only")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = parser.parse_args()

    if args.hook_mode:
        run_hook_mode(args.specs_dir)

    elif args.status:
        from spec_store import spec_store_status
        import subprocess
        subprocess.run([sys.executable, str(SCRIPTS_DIR / "spec_store.py"),
                        "--status-check", "--specs-dir", args.specs_dir])

    elif args.list:
        from spec_store import list_specs, format_spec_list
        specs = list_specs(args.specs_dir)
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(specs, indent=indent))
        else:
            print(format_spec_list(specs))

    elif args.find:
        from spec_store import find_specs
        results = find_specs(args.find, args.specs_dir)
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(results, indent=indent))
        else:
            if not results:
                print(f"No specs found matching '{args.find}'")
            else:
                for r in results:
                    badge = "🟢" if r.get("confidence", 0) >= 75 else "🟡"
                    print(f"  {badge} [{r['id']}] {r['title']} — {r['confidence']}% | {r['status']}")

    elif args.load:
        spec = load_existing_spec(args.load, args.specs_dir)
        if not spec:
            err(f"Spec not found: {args.load}")
            sys.exit(1)
        if args.json:
            output = {k: v for k, v in spec.items() if k != "spec_markdown"}
            print(json.dumps(output, indent=2 if args.pretty else None))
        else:
            print(spec["spec_markdown"])

    elif args.prompt:
        result = run_interactive_flow(
            prompt=args.prompt,
            context_dir=args.context_dir,
            specs_dir=args.specs_dir,
            skip_questions=args.skip_questions,
        )
        if args.json:
            output = {k: v for k, v in result.items() if k != "spec_markdown"}
            print(json.dumps(output, indent=2 if args.pretty else None))

    elif args.interactive:
        header("interactive mode")
        try:
            prompt = input(f"  {ansi(GHOST, CYAN)} What do you want to build? ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if prompt:
            run_interactive_flow(
                prompt=prompt,
                context_dir=args.context_dir,
                specs_dir=args.specs_dir,
                skip_questions=args.skip_questions,
            )
        else:
            print("No prompt provided.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
