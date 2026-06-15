# Confidence Scoring Rubric

_Load during Phase 3 — compute confidence score before presenting spec._

---

## Formula

```
confidence = 100
confidence -= deductions
confidence += bonuses
confidence = max(0, min(100, confidence))
```

---

## Deductions

Apply each applicable deduction. Deductions are cumulative unless a cap is specified.

### From Ambiguity Triage

| Condition | Deduction | Cap | Notes |
|---|---|---|---|
| Each MISSING_CRITICAL clause (unresolved) | −20 | −60 total | If user answered Phase 2 questions, these become resolved |
| Each AMBIGUOUS clause (unresolved) | −8 | −32 total | |
| Each AMBIGUOUS clause (resolved by answer) | −0 | — | Answered = no deduction |

### From Spec Completeness

| Condition | Deduction | Notes |
|---|---|---|
| Zero acceptance criteria | −15 | "Done" is undefined |
| Acceptance criteria exist but none are testable | −10 | |
| Only 1 acceptance criterion | −5 | |
| No done condition / success metric of any kind | −20 | |

### From Scope Quality

| Condition | Deduction | Notes |
|---|---|---|
| Scope boundary undefined | −15 | e.g., "the whole dashboard", "everything" |
| Scope has > 8 in-scope items | −8 | Too large for one spec |
| Multiple distinct features bundled together | −12 | Should be split |

### From Tech & Context

| Condition | Deduction | Notes |
|---|---|---|
| Tech stack completely unknown (no codebase) | −10 | Greenfield — higher uncertainty |
| Existing codebase but pattern unknown | −5 | |
| Critical integration point unknown (e.g., "fetch from API" but no API docs) | −15 | |
| Security/auth requirement without clear spec | −10 | |

---

## Bonuses

| Condition | Bonus | Notes |
|---|---|---|
| User provided concrete examples in prompt | +5 | Examples reduce ambiguity significantly |
| Existing codebase read and patterns understood | +8 | Strong inference basis |
| User answered all Phase 2 questions | +10 | All critical gaps resolved |
| User answered 2 of 3 questions | +6 | Most gaps resolved |
| User provided acceptance criteria in prompt | +8 | Done condition is clear |
| Similar feature already exists in codebase | +5 | Can follow established pattern |
| Small, bounded scope (≤ 3 in-scope items) | +5 | Low complexity = higher confidence |

**Bonus cap:** +30 total. Confidence cannot exceed 100.

---

## Score Bands and Actions

| Score | Badge | Label | Agent Action |
|---|---|---|---|
| 90–100% | 🟢 | **Excellent** | Lock spec immediately. Begin implementation. Proceed with high confidence. |
| 75–89% | 🟢 | **Good** | Lock spec. Begin implementation. Note key assumptions in first code comment. |
| 60–74% | 🟡 | **Acceptable** | Lock spec. Flag top 2 assumptions as "verify before merge" in spec. |
| 45–59% | 🟠 | **Marginal** | Present spec with blocker list. Ask user to resolve at least the highest-impact blocker. |
| 30–44% | 🔴 | **Low** | Present spec draft only. Do not offer to lock. All MISSING_CRITICAL must be resolved first. |
| 0–29% | 🚨 | **Critical** | Do not present spec. State blockers. Cannot start until resolved. |

---

## Worked Scoring Examples

### Example A: "add search to the products page" (answered 2 questions)

```
Base:                              100

Deductions:
- 0 unresolved MISSING_CRITICAL     -0  (both answered)
- 1 minor AMBIGUOUS remaining        -8  (sort order behavior)
- Acceptance criteria: 3 testable    -0

Bonuses:
- Existing codebase (React + Tailwind) +8
- 2 of 3 questions answered           +6
- Small scope (4 items)               +5

Total: 100 - 8 + 19 = 111 → capped at 100
→ Actually: 100 - 8 + 19 = 111 → score = 95
Badge: 🟢 Excellent
```

### Example B: "build me a login page" (no answers yet, first triage)

```
Base:                              100

Deductions:
- 2 MISSING_CRITICAL (done condition, auth method)  -40
- 1 AMBIGUOUS (scope)                               -8
- No acceptance criteria stated                     -15

Bonuses:
- Existing codebase                                 +8

Total: 100 - 63 + 8 = 45
Badge: 🟠 Marginal
```

After user answers questions:
```
Base:                              100

Deductions:
- 0 unresolved MISSING_CRITICAL    -0  (both answered)
- 0 unresolved AMBIGUOUS           -0  (scope clarified)
- Acceptance criteria added        -0

Bonuses:
- All 3 questions answered        +10
- Existing codebase               +8
- User provided examples          +5

Total: 100 + 23 = 123 → capped at 100
→ score = 87
Badge: 🟢 Good
```

### Example C: "build the entire user management system" (vague, no context)

```
Base:                              100

Deductions:
- 3 MISSING_CRITICAL:              -60 (capped)
  - done condition undefined
  - scope unbounded ("entire system")
  - data model unknown
- Scope unbounded                  -15
- No acceptance criteria           -15
- No tech context                  -10

Bonuses: none

Total: 100 - 100 = 0 (minimum)
Badge: 🚨 Critical
```

---

## Confidence vs Risk Label

Confidence score and risk label are separate dimensions:

| Confidence | Risk | Meaning |
|---|---|---|
| 90% | Low | Clear spec, small scope — ship it |
| 90% | High | Clear spec, but touches auth/payments — review carefully |
| 60% | Low | Some ambiguity, but stakes are low — proceed cautiously |
| 60% | High | Ambiguity in a high-stakes area — must resolve |

**Risk is determined by domain, not by confidence:**

| Risk: High | Risk: Medium | Risk: Low |
|---|---|---|
| Auth/security | API contracts | Pure UI components |
| Payments/billing | Data model changes | Text/copy changes |
| Database migrations | Multi-user interactions | Styling/layout |
| Data deletion | External integrations | Static content |
| Permission changes | Performance-critical paths | Dev tooling |

---

## Presenting the Score

**In the spec header:**
```
Confidence: 87% 🟢 Good  |  Risk: Medium
```

**For Marginal scores (45–59%), add a blocker note:**
```
⚠️ Confidence is 52% — resolve before locking:
• [BLOCKER] Acceptance criteria undefined — how will you verify this is done?
• [NOTE] Scope may expand — confirm: just list view or also create/edit?
```

**For Low scores (30–44%), do not offer to lock:**
```
🔴 Confidence is 38% — too uncertain to lock. Resolve first:
• [BLOCKER] Done condition: what does success look like?
• [BLOCKER] Auth requirement: who can access this feature?
Once resolved, re-run spec-whisperer with your answers.
```

**For Critical scores (< 30%), do not generate spec:**
```
🚨 Confidence is 12% — cannot generate a useful spec.
Too many critical unknowns:
• What does this feature do for the user?
• What is in scope?
• What counts as "done"?
Please provide more detail and try again.
```
