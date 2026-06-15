# 👻 spec-whisperer

> *"The fastest path to working code is 90 seconds of structured spec."*

A Claude Skill that intercepts any implementation request, runs a structured ambiguity triage, asks at most 3 targeted questions, generates a locked micro-spec with a confidence score, and only then hands off to implementation.

**The rule: no code until the spec is locked.**

---

## The Problem It Solves

```
You: "build me a dashboard"
Agent: [writes 200 lines of code]
You: "no, I meant a mobile dashboard with dark mode and real-time data"
Agent: [rewrites 200 lines]
You: "also it needs auth"
Agent: [rewrites again]
Total: 3 hours wasted
```

spec-whisperer eliminates this by making the spec explicit before the first line of code.

---

## What It Generates

In 60–120 seconds, from any prompt:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👻 spec-whisperer — analyzing your request
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

─── SPEC DRAFT ──────────────────────────────────────────
  Confidence: ████████████████████████░░░░░░░░░░░░░░░░ 87% 🟢 Good  |  Risk: Medium

# Spec: Login Page with Email Authentication

**Date:** 2026-06-07 | **Status:** LOCKED
**Confidence:** 87% 🟢 Good  |  **Risk:** Medium

## Goal
Enable users to sign in with email and password and land on /dashboard.

## In Scope
• Login form with email and password fields
• Client-side validation with inline error messages
• Submit button with loading state during request
• Redirect to /dashboard on successful login
• Error message on invalid credentials

## Out of Scope
• User registration / sign-up flow
• Forgot password / password reset
• Social login (Google, GitHub, etc.)
• Two-factor authentication

## Acceptance Criteria
☐ User can enter email/password, click login, and land on /dashboard — verifiable by completing sign-in end-to-end
☐ Invalid credentials show inline error — verifiable by entering wrong password
☐ Loading state shown during request — verifiable by slow-network simulation

## Edge Cases
• Invalid credentials: show specific error without revealing which field is wrong
• Network timeout: show retry option, do not clear form
• Already logged in: redirect to /dashboard immediately

## Assumptions
• Framework: React 18 [INFERRED from package.json]
• Styling: Tailwind CSS [INFERRED from tailwind.config.js]
• Auth: email + password only [STATED]

## Tech Constraints
• React 18 with hooks
• Tailwind CSS utility classes
• No new dependencies — use existing auth service

[Y] Lock and implement  [E] Edit  [R] Reject
```

---

## Quick Start (5 minutes)

### Step 1: Place the skill
```bash
cp -r spec-whisperer/ ~/.claude/skills/
# or wherever your Claude skills live
```

### Step 2: Test it
```bash
python skill/scripts/spec_whisperer.py --prompt "build a login page"
```

### Step 3: (Optional) Install Claude Code hook
Add to `.claude/settings.json` in your project:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "bash",
      "hooks": [{
        "type": "command",
        "command": "python /path/to/skill/scripts/spec_whisperer.py --hook-mode"
      }]
    }]
  }
}
```

---

## Usage Examples

```bash
# Analyze a prompt and run full interactive flow
python skill/scripts/spec_whisperer.py --prompt "build a search feature"

# Interactive mode (prompts for input)
python skill/scripts/spec_whisperer.py --interactive

# Skip clarification questions (generate from prompt only)
python skill/scripts/spec_whisperer.py --prompt "..." --skip-questions

# With codebase context (auto-infers tech stack)
python skill/scripts/spec_whisperer.py --prompt "..." --context-dir ./src

# Load an existing locked spec
python skill/scripts/spec_whisperer.py --load 2026-06-07-login-page-email-auth

# Search saved specs
python skill/scripts/spec_whisperer.py --find "login"

# List all saved specs
python skill/scripts/spec_whisperer.py --list

# Show .specs/ directory status
python skill/scripts/spec_whisperer.py --status
```

---

## How It Works

### Phase 0: Trigger Detection
Recognizes implementation intents ("build", "create", "implement", "add", "make") and skips non-implementation requests ("explain", "debug", "review").

### Phase 1: Ambiguity Triage
Classifies every clause in the prompt:
- `CLEAR` — stated explicitly → locked as assumption
- `INFERABLE` — implied by codebase → locked as assumption with source
- `AMBIGUOUS` — stated but could mean 2+ things → question candidate
- `MISSING_CRITICAL` — required, completely absent → question candidate
- `MISSING_OPTIONAL` — nice to have → flagged TBD, not asked

### Phase 2: Questions (max 3)
Selects the 3 highest-impact questions using domain impact scoring. Acceptance criteria and scope boundary always rank highest. Never asks what can be inferred from the codebase.

### Phase 3: Spec + Confidence Score
Generates a structured micro-spec with:
- Goal (1 sentence)
- In scope / Out of scope
- Acceptance Criteria (testable, with "verifiable by X")
- Edge cases
- Assumptions (tagged STATED or INFERRED)
- Tech constraints

**Confidence score (0–100%):**
- 90%+ → Excellent, lock immediately
- 75–89% → Good, lock with notes
- 60–74% → Acceptable, lock with flags
- 45–59% → Marginal, resolve blocker
- <45% → Low/Critical, must resolve

### Phase 4: Lock
Developer approves `[Y/E/R]`. Locked specs saved to `.specs/YYYY-MM-DD-{slug}.md` with searchable index.

---

## The Confidence Score

Before writing a line of code, you see exactly how confident the spec is:

| Score | Badge | Action |
|---|---|---|
| 90–100% | 🟢 Excellent | Start coding immediately |
| 75–89% | 🟢 Good | Start coding, note assumptions |
| 60–74% | 🟡 Acceptable | Start coding, flag open items |
| 45–59% | 🟠 Marginal | Resolve one blocker first |
| 30–44% | 🔴 Low | All blockers must be resolved |
| 0–29% | 🚨 Critical | Too vague, cannot start |

---

## .specs/ Directory

Every locked spec is saved for future reference:

```
.specs/
├── index.json                              ← Searchable index
├── 2026-06-07-login-page-email-auth.md
├── 2026-06-07-product-search-filter.md
└── 2026-06-08-admin-user-management.md
```

Add to `.gitignore` to keep specs local, or commit them for team sharing.

---

## Script Reference

| Script | Purpose | Key Args |
|---|---|---|
| `spec_whisperer.py` | Main orchestrator | `--prompt`, `--interactive`, `--list`, `--find`, `--load` |
| `prompt_parser.py` | Clause extractor | `--text`, `--context-dir`, `--summary` |
| `question_ranker.py` | Question selector | `--clauses`, `--max`, `--message-only` |
| `spec_generator.py` | Spec generator | `--prompt`, `--answers`, `--markdown-only` |
| `spec_store.py` | Storage manager | `--save`, `--find`, `--load`, `--list`, `--lock` |

---

## Comparison

| | spec-whisperer | Copilot | Cursor | Claude Code |
|---|---|---|---|---|
| Writes code | ✅ (after lock) | ✅ | ✅ | ✅ |
| Asks questions | ✅ (max 3) | Sometimes | Sometimes | Sometimes |
| Ambiguity triage | ✅ | ❌ | ❌ | ❌ |
| Generates spec | ✅ | ❌ | ❌ | ❌ |
| Confidence score | ✅ | ❌ | ❌ | ❌ |
| Locks before coding | ✅ | ❌ | ❌ | ❌ |
| Saves spec history | ✅ | ❌ | ❌ | ❌ |

---

## Requirements

- Python 3.10+ (standard library only — zero pip dependencies)
- No external API calls
- Works fully offline
- macOS, Linux, Windows 10+

---

*spec-whisperer v1.0.0 — Because the best code is code written to the right spec.*
