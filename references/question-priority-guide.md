# Question Priority Guide

_Load during Phase 2 — Targeted Questions._

---

## The Core Principle

You have at most 3 questions. Every question not asked saves momentum. Every wrong question asked is a trust tax. The goal is to ask the 3 questions whose answers unlock the most implementation certainty.

---

## Impact Scoring Formula

```python
def impact_score(clause: dict) -> int:
    score = 0

    # 1. Clause type weight
    weights = {
        "MISSING_CRITICAL": 40,
        "AMBIGUOUS":        20,
    }
    score += weights.get(clause["type"], 0)

    # 2. Domain importance weight
    domain_weights = {
        "acceptance_criteria": 35,  # Without this, "done" is undefined
        "scope_boundary":      30,  # Without this, scope creeps forever
        "data_model":          28,  # Drives architecture
        "auth_permissions":    25,  # Cross-cutting, hard to retrofit
        "api_contract":        22,  # If backend involved
        "error_handling":      18,  # Catches failure modes
        "ui_behavior":         15,  # Can be iterated quickly
        "performance":         12,  # Can be optimized later
        "copy_text":            2,  # Pure MISSING_OPTIONAL territory
        "style_polish":         2,  # Same
    }
    score += domain_weights.get(clause["domain"], 8)

    # 3. Downstream dependency bonus
    # Does answering this question unlock other ambiguous clauses?
    if clause.get("blocks_others", False):
        score += 20

    # 4. Cannot-infer penalty
    # If it CAN be inferred from context, don't ask — penalty removes it from candidates
    if clause.get("inferable", False):
        score -= 100  # Effectively removes from candidate pool

    return score
```

---

## Domain Classification

Classify each clause into one domain before scoring:

| Domain Key | What It Covers | Example Clauses |
|---|---|---|
| `acceptance_criteria` | How will success be measured? What is "done"? | "working", "correct", "good" |
| `scope_boundary` | Where does this feature start and stop? | "and also", "full", "complete", "the whole" |
| `data_model` | Entities, their properties, relationships, sources | "user", "order", "product", "list of..." |
| `auth_permissions` | Who can see/do this? Which role? | "admin", "authenticated", "owner only" |
| `api_contract` | Endpoint paths, HTTP methods, request/response shape | "call the API", "fetch from", "POST to" |
| `error_handling` | What happens on failure, empty state, invalid input | "if it fails", "empty", "invalid" |
| `ui_behavior` | Interactions, transitions, loading, responsiveness | "click", "hover", "mobile", "animation" |
| `performance` | Speed, latency, throughput targets | "fast", "real-time", "instant", "scalable" |
| `copy_text` | Labels, messages, placeholder text | "button says", "error message", "title" |
| `style_polish` | Visual design details beyond existing system | "color", "font", "spacing", "shadow" |

---

## Question Writing Rules

### Rule 1: Lead with the domain label
```
✅ Good: "**[Scope]** Should this include just the list view, or also create/edit/delete?"
❌ Bad:  "What features should I include?"
```
The domain label orients the developer instantly.

### Rule 2: Include a concrete example in parentheses
```
✅ Good: "**[Done condition]** How will you know it's working? (e.g., 'user can sign in with email and land on /dashboard')"
❌ Bad:  "What should happen when the user logs in successfully?"
```
Examples make abstract questions concrete and cut response time in half.

### Rule 3: Binary or constrained choices beat open questions
```
✅ Good: "**[Scope]** Just the list page, or also the detail page?"
✅ Good: "**[Search]** Trigger on keystroke, or on Enter/button click?"
❌ Bad:  "What should the search functionality do?"
```
Open questions get open answers. Constrained choices get fast, precise answers.

### Rule 4: One domain per question
```
✅ Good: "**[Data]** Where does order data come from — an existing API or a new endpoint?"
❌ Bad:  "Where does order data come from and who can see it and what if there's no data?"
```
Two questions in one dilutes both.

### Rule 5: Never ask what you can observe
```
If package.json has "react": "^18"   → Never ask "What framework?"
If tailwind.config.js exists          → Never ask "How should I style it?"
If auth middleware is in the codebase → Never ask "Do you need authentication?"
If existing API client exists          → Never ask "How should I fetch data?"
```

### Rule 6: Frame around the user's goal, not the implementation
```
✅ Good: "**[Done]** When is this search feature finished? (e.g., 'user types a product name and the list filters to matching items')"
❌ Bad:  "What API should the search endpoint call?"
```
The developer thinks in goals, not implementation details.

---

## The Three-Question Budget

### Budget Allocation by Scenario

**Vague prompt (< 20 words):**
- Q1: Acceptance criteria / done condition [highest impact always]
- Q2: Scope boundary [second highest almost always]
- Q3: Most critical missing data or auth detail

**Medium prompt (20–80 words):**
- Q1: Most critical MISSING_CRITICAL
- Q2: Most critical AMBIGUOUS
- Q3: Second MISSING_CRITICAL or second AMBIGUOUS (if score > 40)
- If no third question scores > 40 → ask only 2

**Detailed prompt (> 80 words with most things specified):**
- Check if anything scores > 50 in impact → ask it
- Often: 0–1 questions needed
- Never force questions when the prompt is already specific

**Over-specified prompt ("just do it exactly as I described"):**
- Treat as 0 questions
- Build spec from given information
- Flag remaining unknowns as TBD in spec
- Note confidence score honestly

---

## Question Presentation Format

Always present all questions together in one message. Never ask one at a time unless the previous answer reveals new unknowns.

```
Before I start, I have [N] quick question[s]:

1. **[{Domain}]** {Question text}?
   (e.g., "{concrete example answer}")

2. **[{Domain}]** {Question text}?
   (e.g., "{concrete example answer}")

3. **[{Domain}]** {Question text}?
   (e.g., "{concrete example answer}")
```

**Tone rules:**
- Never apologize for asking
- Never say "just to make sure" or "sorry to bother you"
- Never explain why you're asking — the developer understands
- Keep it professional and fast
- Maximum 2 lines per question (including example)

---

## After the Answers

When the developer answers:

1. Extract the new CLEAR information from each answer
2. Re-classify any AMBIGUOUS/MISSING_CRITICAL clauses that are now resolved
3. Check: are there any new MISSING_CRITICAL clauses revealed by the answers?
   - If yes and they score > 60 → ask 1 follow-up (maximum)
   - If no → proceed to spec generation
4. Do not ask a second round of questions unless a critical blocker was revealed

---

## Questions Never to Ask

These questions are always either inferable or MISSING_OPTIONAL:

```
❌ "What programming language?"       (read the codebase)
❌ "What framework?"                   (read package.json / requirements.txt)
❌ "What color should the button be?"  (use existing design system)
❌ "What should the error message say?"(make something reasonable)
❌ "Do you want it to be responsive?"  (yes, always in 2026)
❌ "Should I add comments to the code?"(follow existing style)
❌ "What font?"                        (use existing typography)
❌ "Should I write tests?"             (check existing test coverage pattern)
❌ "What's your deadline?"             (irrelevant to spec)
❌ "Who is the target user?"           (unless it changes implementation significantly)
```

---

## Worked Examples

### Example A: "add a search bar to the products page"

**Candidates:**
| Clause | Type | Domain | Impact |
|---|---|---|---|
| Search fields (name only vs name+desc+sku) | MISSING_CRITICAL | data_model | 40+28 = 68 |
| Trigger (keystroke vs Enter) | AMBIGUOUS | ui_behavior | 20+15 = 35 |
| No results state | MISSING_OPTIONAL | error_handling | — (skip) |
| Min chars | MISSING_OPTIONAL | ui_behavior | — (skip) |

**Top 2 (nothing else scores above threshold):**
1. **[Data]** Which fields should the search check — just product name, or also description and SKU?
2. **[Behavior]** Should results filter as the user types, or only when they press Enter / click Search?

### Example B: "build me a login page"

**Candidates:**
| Clause | Type | Domain | Impact |
|---|---|---|---|
| Done condition | MISSING_CRITICAL | acceptance_criteria | 40+35 = 75 |
| Auth method (email/password vs OAuth) | MISSING_CRITICAL | auth_permissions | 40+25 = 65 |
| Scope (just login or also signup/reset?) | AMBIGUOUS | scope_boundary | 20+30 = 50 |
| Form validation style | MISSING_OPTIONAL | — | skip |

**Top 3:**
1. **[Done]** How will you know the login page is done? (e.g., "user enters email/password, clicks login, and lands on /dashboard")
2. **[Auth]** Sign in method — email + password, Google OAuth, or both?
3. **[Scope]** Just the login form, or also forgot password and sign-up links?

### Example C: "refactor the UserService class to be cleaner"

**Candidates:**
| Clause | Type | Domain | Impact |
|---|---|---|---|
| "cleaner" definition | AMBIGUOUS | acceptance_criteria | 20+35 = 55 |
| Test behavior preservation | MISSING_CRITICAL | acceptance_criteria | 40+35 = 75 |
| Scope (just UserService or related classes?) | AMBIGUOUS | scope_boundary | 20+30 = 50 |

**Top 3:**
1. **[Done]** What makes the refactor successful — fewer methods, better naming, split into smaller classes, or all three?
2. **[Tests]** Should all existing tests still pass after the refactor, or are some tests also being updated?
3. **[Scope]** Just UserService, or also classes that UserService depends on?
