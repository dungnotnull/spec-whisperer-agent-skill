# spec-whisperer — Claude Skill

> *"The fastest path to working code is 90 seconds of structured spec."*

---

## What This Project Does

**spec-whisperer** is a Claude Skill that intercepts any implementation request before the agent writes a single line of code, runs it through a structured ambiguity triage, and generates a locked micro-spec — complete with acceptance criteria, edge cases, scope boundaries, and a confidence score.

The agent won't start coding until the spec is approved. This single constraint eliminates the most common vibe-coding failure mode: misunderstood requirements leading to complete rework.

---

## Why It's Unique

| Tool | Writes code | Asks questions | Generates spec | Confidence score | Locks before coding |
|---|---|---|---|---|---|
| Cursor / Copilot | ✅ | Sometimes | ❌ | ❌ | ❌ |
| Claude Code (base) | ✅ | Sometimes | ❌ | ❌ | ❌ |
| **spec-whisperer** | ✅ (after lock) | ✅ (max 3) | ✅ | ✅ | ✅ |

No existing skill or tool does structured ambiguity triage + confidence scoring before implementation begins.

---

## Repository Structure

```
spec-whisperer/
├── CLAUDE.md                              ← You are here
├── PROJECT-detail.md                      ← Full specification
├── PROJECT-DEVELOPMENT-PHASE-TRACKING.md  ← Phase tracker
├── README.md                              ← Install & quick-start
├── skill/
│   ├── SKILL.md                           ← Main skill harness (4 phases)
│   ├── references/
│   │   ├── ambiguity-taxonomy.md          ← Classification rules for prompt clauses
│   │   ├── question-priority-guide.md     ← How to pick the best 3 questions
│   │   ├── spec-format-guide.md           ← Micro-spec structure and rules
│   │   └── confidence-scoring-rubric.md   ← How to compute confidence 0–100
│   ├── scripts/
│   │   ├── spec_whisperer.py              ← Main orchestrator
│   │   ├── prompt_parser.py               ← Prompt clause extractor & classifier
│   │   ├── question_ranker.py             ← Ranks clarification questions by impact
│   │   ├── spec_generator.py              ← Generates micro-spec from parsed data
│   │   └── spec_store.py                  ← Saves/loads specs from .specs/
│   └── assets/
│       ├── spec_template.md               ← Micro-spec markdown skeleton
│       └── confidence_thresholds.json     ← Score thresholds and actions
└── evals/
    └── evals.json                         ← 10 test cases with assertions
```

---

## Core Workflow

```
Developer types: "build me a login page"
                        │
                        ▼
              [INTERCEPT] Trigger detection
                        │
                        ▼
              [TRIAGE] Ambiguity classification
              clear / ambiguous / missing per clause
                        │
                        ▼
              [QUESTION] Max 3 targeted questions
              (only what can't be inferred)
                        │
                        ▼
              [SPEC] Micro-spec generation
              + confidence score 0–100%
                        │
                   ┌────┴────┐
              < 70%           ≥ 70%
           Must resolve    Can proceed
                        │
                        ▼
              [LOCK] Developer approves
              [Y / edit / reject]
                        │
                        ▼
              Implementation begins
              (spec passed as context)
```

---

## Design Principles

- **Max 3 questions** — more questions kill momentum. Prioritize ruthlessly.
- **Never ask what can be inferred** — language, framework, patterns from context are assumed.
- **Confidence score is honest** — not optimistic. Below 70% = blockers exist.
- **Spec is ≤ 1 page** — if it's longer, it's a project plan, not a spec.
- **Fail open** — if the skill errors, it warns and lets the agent proceed without spec.
- **Spec is saved** — every approved spec goes to `.specs/` for future reference and onboarding.
