# PROJECT-detail.md — spec-whisperer

## 1. Core Problem

Vibe coders (and AI agents working with them) share one catastrophic pattern:

```
User: "build me a dashboard"
Agent: [writes 300 lines]
User: "no I meant a mobile dashboard with dark mode and real-time data"
Agent: [rewrites 300 lines]
User: "also it needs auth"
Agent: [rewrites again]
```

The root cause is never laziness — it's **unstructured intent transfer**. The user has a clear vision. The agent makes reasonable assumptions. Neither the vision nor the assumptions were ever made explicit, so mismatches are only discovered after significant work.

spec-whisperer solves this by making the implicit explicit **before implementation begins**.

---

## 2. The Ambiguity Taxonomy

Every prompt contains clauses that fall into one of five categories:

| Category | Definition | Example | Action |
|---|---|---|---|
| **CLEAR** | Explicit, unambiguous, directly stated | "use React" | Lock as assumption |
| **INFERABLE** | Not stated but strongly implied by context | Framework from existing codebase | Lock as assumption + note |
| **AMBIGUOUS** | Stated but could mean multiple things | "fast" — how fast? | Generate question |
| **MISSING_CRITICAL** | Required to implement, completely absent | No acceptance criteria | Generate question |
| **MISSING_OPTIONAL** | Nice to have but can proceed without | Error message copy | Flag as TBD, proceed |

**Rule:** Only AMBIGUOUS and MISSING_CRITICAL clauses become questions, and only the top 3 by impact.

---

## 3. The Micro-Spec Format

Every generated spec has exactly these sections:

```markdown
# Spec: {title}
**Date:** {date} | **Status:** DRAFT / LOCKED
**Confidence:** {score}% | **Risk:** Low / Medium / High

## Goal
One sentence. What does this do for the user?

## In Scope
- [Bullet list of what will be built]

## Out of Scope
- [Bullet list of what will NOT be built in this iteration]

## Acceptance Criteria
- [ ] {Testable criterion 1} — verifiable by {how}
- [ ] {Testable criterion 2} — verifiable by {how}
- [ ] {Testable criterion 3} — verifiable by {how}

## Edge Cases
- {Edge case}: {expected behavior}

## Assumptions
- {Assumption} [INFERRED / STATED]

## Tech Constraints
- {Language/framework/library/version}
- {Existing patterns to follow}

## Out of Spec (TBD)
- {Things that were missing but won't block implementation}
```

**Rules:**
- Goal: exactly 1 sentence
- In Scope: 3–8 bullets
- Acceptance Criteria: exactly 3–6, all testable (each has "verifiable by X")
- Edge Cases: 2–5 (inferred from domain knowledge)
- Assumptions: all CLEAR + INFERABLE items explicitly listed
- Tech Constraints: language, framework, relevant libraries, existing patterns

---

## 4. Confidence Scoring System

The confidence score (0–100%) measures how much of the implementation can proceed without ambiguity.

### Score Formula

```python
base_score = 100

# Deductions
for each MISSING_CRITICAL clause:
    base_score -= 20  # cap: -60 total

for each AMBIGUOUS clause:
    base_score -= 8   # cap: -32 total

if acceptance_criteria_count == 0:
    base_score -= 15

if tech_stack_unknown:
    base_score -= 10

if scope_unbounded:  # "build everything", "full app", no clear boundary
    base_score -= 15

# Bonuses
if user_provided_examples:
    base_score += 5

if existing_codebase_context:
    base_score += 8

if all_questions_answered:
    base_score += 10

confidence = max(0, min(100, base_score))
```

### Score Interpretation

| Score | Label | Agent Action |
|---|---|---|
| 90–100% | Excellent | Proceed immediately after spec lock |
| 70–89% | Good | Proceed after spec lock, note assumptions |
| 50–69% | Marginal | Must resolve at least 1 blocker before lock |
| 30–49% | Low | Must resolve all MISSING_CRITICAL before lock |
| 0–29% | Critical | Cannot proceed — too many unknowns |

---

## 5. Question Selection Algorithm

From all AMBIGUOUS and MISSING_CRITICAL clauses, select the top 3 by impact score.

### Impact Scoring Per Question

```python
def impact_score(clause):
    score = 0

    # Clause type weight
    if clause.type == "MISSING_CRITICAL":
        score += 40
    elif clause.type == "AMBIGUOUS":
        score += 20

    # Domain importance weight
    if clause.domain in ("scope", "acceptance_criteria", "data_model"):
        score += 30
    elif clause.domain in ("auth", "security", "payments"):
        score += 25
    elif clause.domain in ("ui_behavior", "api_contract"):
        score += 20
    elif clause.domain in ("error_handling", "edge_cases"):
        score += 15
    else:
        score += 5  # style, copy, etc.

    # Downstream dependency weight
    if clause.blocks_other_clauses:
        score += 20

    return score
```

Top 3 questions by score become the clarification questions. They are asked together in one message, never one at a time.

---

## 6. Trigger Detection

spec-whisperer fires when the agent detects an implementation intent:

### High-Confidence Triggers (always fire)
```
"build me...", "create a...", "write a...", "implement...",
"make a...", "add a feature...", "code a...", "develop a...",
"I need a...", "can you build...", "help me build..."
```

### Context-Required Triggers (fire only if no spec exists)
```
"fix this...", "update the...", "refactor...", "change..."
→ Check: does .specs/ have a relevant spec? If yes, load it. If no, run spec-whisperer.
```

### Skip Triggers (never fire)
```
"explain...", "what is...", "how does...", "show me an example..."
"debug why...", "what's wrong with..." (diagnostic, not implementation)
```

### Re-Use Triggers (load existing spec)
```
"continue building...", "add to the...", "extend the..."
→ Find the most recent relevant spec, present it, ask: "Continue with this spec? [Y/update]"
```

---

## 7. Spec Storage System

Every locked spec is saved to `.specs/`:

```
.specs/
├── 2026-06-07-login-page.md
├── 2026-06-07-user-dashboard.md
├── 2026-06-08-payment-flow.md
└── index.json    ← searchable index of all specs
```

`index.json` format:
```json
[
  {
    "id": "2026-06-07-login-page",
    "title": "Login page with OAuth",
    "date": "2026-06-07",
    "status": "LOCKED",
    "confidence": 87,
    "tags": ["auth", "ui", "react"],
    "path": ".specs/2026-06-07-login-page.md"
  }
]
```

The agent can search this index with `spec_store.py --find "login"` to load relevant prior specs.

---

## 8. Integration Modes

### Mode A: Claude Code (Recommended)
Add to `.claude/settings.json`:
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

The hook checks if the bash command is implementation-related. If yes, interrupts and runs spec flow.

### Mode B: SKILL.md Direct (This skill approach)
The agent reads SKILL.md and follows the 4-phase protocol before coding.

### Mode C: Manual
```bash
python skill/scripts/spec_whisperer.py --prompt "build me a login page"
python skill/scripts/spec_whisperer.py --interactive  # prompts for input
python skill/scripts/spec_whisperer.py --load 2026-06-07-login-page  # load existing spec
```

---

## 9. Edge Cases

| Situation | Handling |
|---|---|
| Prompt is already very detailed | Skip questions (confidence likely ≥ 90%), go straight to spec |
| User says "just do it, don't ask" | Warn once, generate spec with all unknowns flagged, lock it |
| Existing spec found for same feature | Load it, diff against new prompt, show changes, re-lock |
| Score below 30% | Refuse to lock, must resolve MISSING_CRITICAL items first |
| User edits spec | Re-score confidence, present updated spec, re-lock |
| Multi-feature request | Split into sub-specs, handle one at a time |
| Ambiguous scope ("build the whole app") | Flag as MISSING_CRITICAL, ask for MVP boundary |
| No codebase context | Assume greenfield, note in assumptions |
| Existing codebase detected | Read key files, infer tech stack, add to assumptions |
