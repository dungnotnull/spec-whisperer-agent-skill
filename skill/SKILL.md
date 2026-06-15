---
name: spec-whisperer
description: Intercept any implementation request and generate a locked micro-spec before writing code. Use this skill whenever someone asks you to build, create, implement, make, write, develop, or add a feature or component. Trigger BEFORE writing any code, creating any file, or running any build command. This skill runs a structured ambiguity triage on the prompt, asks at most 3 targeted clarifying questions, generates a micro-spec with acceptance criteria and a confidence score, and waits for developer approval before implementation begins. The entire flow takes 60–120 seconds and prevents rework from misunderstood requirements. Also triggers when the user says "continue building" or "add to" — load existing spec first. Never trigger for explain/debug/review requests. The spec is the contract; implementation is the delivery.
---

# spec-whisperer Skill

You stop before you code. Every implementation request passes through a structured spec checkpoint first. This takes 90 seconds and saves hours of rework.

**The rule is absolute: no code, no files, no commands until the spec is locked.**

---

## PHASE 0 — TRIGGER DETECTION

Read the user's message and classify it:

**→ IMPLEMENT** (run all phases): Request to build, create, implement, make, write, develop, add a feature, code a component.
- Signals: "build me", "create a", "write a", "implement", "make a", "add", "I need a", "code a"

**→ CONTINUE** (load existing spec): Request to extend or continue existing work.
- Signals: "continue", "add to", "extend", "also add", "and make it"
- Action: run `scripts/spec_store.py --find "{keywords}"` → present most relevant spec → ask `"Continue with this spec? [Y/update]"`

**→ SKIP** (proceed without spec): Non-implementation request.
- Signals: "explain", "what is", "how does", "debug", "review", "what's wrong", "show me an example"
- Action: answer normally, do not run spec-whisperer

When in doubt between IMPLEMENT and SKIP: **IMPLEMENT**. A false positive (unnecessary spec) is better than a false negative (coding without spec).

---

## PHASE 1 — AMBIGUITY TRIAGE

Load `references/ambiguity-taxonomy.md`.

Run `scripts/prompt_parser.py --text "{user_prompt}"` or classify manually.

For every meaningful clause in the prompt, assign one of:

| Label | Meaning | Action |
|---|---|---|
| `CLEAR` | Explicit and unambiguous | Lock as assumption |
| `INFERABLE` | Not stated but strongly implied by context | Lock as assumption, note it |
| `AMBIGUOUS` | Could mean 2+ different things | Candidate question |
| `MISSING_CRITICAL` | Required to implement, not mentioned | Candidate question |
| `MISSING_OPTIONAL` | Nice to have, can TBD | Flag in spec, don't ask |

**What to infer without asking:**
- Language/framework from existing files in the codebase
- Coding style from existing code
- Auth system from `package.json`, imports, or prior context
- Database from existing models
- Test framework from existing test files

**What you must never infer:**
- What "success" looks like (acceptance criteria)
- Where the scope ends ("just the list" vs "list + detail page + search")
- Who the user is (customer vs internal vs admin)
- Whether data is real-time or periodic
- What happens on error

---

## PHASE 2 — TARGETED QUESTIONS

Load `references/question-priority-guide.md`.

Run `scripts/question_ranker.py --clauses "{json}"` or rank manually.

From all AMBIGUOUS and MISSING_CRITICAL clauses, select **exactly the top 3 by impact**. If fewer than 3 critical gaps exist, ask fewer. Never pad to 3.

**Impact priority order:**
1. Missing acceptance criteria (blocks everything)
2. Unclear scope boundary (causes infinite expansion)
3. Unknown data model / entity relationships (drives architecture)
4. Auth / permissions (cross-cutting concern)
5. API contract (if backend involved)
6. Error handling / edge cases
7. UI behavior specifics
8. Copy / style / polish

**Question format — one message, numbered:**

```
Before I start, I have [N] quick questions to make sure I build exactly what you need:

1. **[Domain: Acceptance Criteria]** How will you know this is working correctly? What's the "done" condition? (e.g., "user can log in with Google and see their dashboard")

2. **[Domain: Scope]** Should this include [X] or just [Y]? (e.g., "just the login form, or also password reset and 'remember me'?")

3. **[Domain: Data]** Where does [entity] come from — [option A] or [option B]? (e.g., "is the user list loaded from an API or hardcoded for now?")
```

**Question writing rules:**
- Include a concrete example in parentheses — makes abstract questions concrete
- Never ask: "What tech stack?" (infer from context), "What color?" (MISSING_OPTIONAL), "What's your deadline?" (irrelevant to spec)
- Each question reveals a different dimension — don't ask two questions about the same topic

After asking, **wait for answers** before generating the spec.

---

## PHASE 3 — SPEC GENERATION

Load `references/spec-format-guide.md` for section rules.
Load `references/confidence-scoring-rubric.md` for scoring.
Run `scripts/spec_generator.py` or generate manually.

Produce the full micro-spec:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SPEC DRAFT — {Feature Title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Confidence: {score}% {badge}  |  Risk: {Low/Medium/High}

GOAL
{One sentence describing what this does for the user}

IN SCOPE
• {item}
• {item}
• {item}

OUT OF SCOPE
• {item}
• {item}

ACCEPTANCE CRITERIA
☐ {Criterion} — verifiable by {how}
☐ {Criterion} — verifiable by {how}
☐ {Criterion} — verifiable by {how}

EDGE CASES
• {scenario}: {expected behavior}
• {scenario}: {expected behavior}

ASSUMPTIONS
• {Assumption} [STATED]
• {Assumption} [INFERRED from {source}]

TECH CONSTRAINTS
• {Language/framework/version}
• {Library or pattern to use/avoid}

TBD (won't block)
• {Missing optional item}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Confidence badge:**
- 90–100%: `🟢 Excellent`
- 70–89%: `🟡 Good`
- 50–69%: `🟠 Marginal — see blockers`
- 30–49%: `🔴 Low — resolve before proceeding`
- 0–29%: `🚨 Critical — cannot start`

**If score < 50%:** After the spec, add:
```
⚠️ BLOCKERS (resolve before implementation):
• {Unresolved MISSING_CRITICAL item and why it blocks}
```

---

## PHASE 4 — LOCK & HANDOFF

After presenting the spec, ask:

```
Ready to lock this spec and start building?

[Y] Lock and implement  [E] Edit spec  [R] Reject — I'll rephrase
```

**If Y (Accept):**
1. Run `scripts/spec_store.py --save "{spec_markdown}"` → saves to `.specs/YYYY-MM-DD-{slug}.md`
2. Confirm: `✅ Spec locked → .specs/{filename}.md`
3. Begin implementation, carrying the spec as context
4. In your first implementation message, reference the spec: `"Implementing per the locked spec — starting with [first acceptance criterion]"`

**If E (Edit):**
1. Show the spec in editable form (or open `$EDITOR` in Claude Code mode)
2. Accept changes, re-score confidence, re-present
3. Repeat until Y or R

**If R (Reject):**
1. Acknowledge: `"No problem — rephrase your request and I'll run a fresh spec"`
2. Do not implement
3. Do not save spec

**If score < 30% and user tries to accept:**
```
⚠️ Confidence is {score}% — too low to start. Resolve these blockers first:
• {blocker 1}
• {blocker 2}
I can't guarantee useful output without this information.
```

---

## IMPORTANT BEHAVIORS

**The no-code rule is absolute.** Not even a "quick" function, not even a scaffold. The spec comes first, always.

**Be brief in questions.** The user is in flow. Keep each question to 2 lines maximum.

**Don't lecture.** Don't explain why you're asking — just ask. The spec output explains itself.

**Infer aggressively.** Every inferred assumption reduces the number of questions needed. Read all available context before asking anything.

**The spec is a contract, not a TODO list.** Acceptance criteria must be testable. "Works correctly" is not a criterion. "User can submit the form and see a success toast within 500ms" is.

**Confidence is honest.** Never inflate the score to make the user feel better. A 60% score is a signal to resolve ambiguity, not a failure.

**One spec per feature.** If the user asks for "a login page and a dashboard", split into two specs and handle them sequentially.

---

## REFERENCE FILES — Load When Needed

| File | Load During |
|---|---|
| `references/ambiguity-taxonomy.md` | Phase 1: classifying clauses |
| `references/question-priority-guide.md` | Phase 2: ranking and writing questions |
| `references/spec-format-guide.md` | Phase 3: generating spec sections |
| `references/confidence-scoring-rubric.md` | Phase 3: computing confidence score |
| `assets/spec_template.md` | Phase 3: spec skeleton |

## SCRIPTS — Run When Available

| Script | Phase | Purpose |
|---|---|---|
| `scripts/prompt_parser.py` | Phase 1 | Extract and classify prompt clauses |
| `scripts/question_ranker.py` | Phase 2 | Rank clarification questions by impact |
| `scripts/spec_generator.py` | Phase 3 | Generate micro-spec markdown |
| `scripts/spec_store.py` | Phase 4 | Save/load/search specs |
| `scripts/spec_whisperer.py` | All | Main orchestrator (all modes) |
