# Spec Format Guide

_Load during Phase 3 — Spec Generation._

---

## The Seven Sections

Every micro-spec has exactly these sections, in this order. No additions, no omissions.

---

### Section 1: GOAL

**Rule:** Exactly one sentence. Subject + verb + object + value.

**Formula:** `{Who} can {do what} {so that / which enables} {outcome}.`

**Quality test:** If a new developer reads only this sentence, do they understand what the feature is for and why it matters?

```
✅ Good:
"Users can search the product catalog by name so they can find items without scrolling."
"Admins can export the user list to CSV to share data with the finance team."
"The checkout form validates payment details before submission to prevent failed orders."

❌ Bad:
"Add search functionality."           (no user, no value)
"Search bar for products."            (not a sentence)
"Users should be able to search."     (no outcome, vague verb)
"Implement a comprehensive search solution for the product catalog page." (verbose)
```

---

### Section 2: IN SCOPE

**Rule:** 3–8 bullet points. Each is a specific deliverable, not a category.

**Quality test:** A developer reading this list knows exactly what to build. No item requires interpretation.

```
✅ Good:
• Text input that filters the product list as the user types
• Filter applies to product name only
• Empty state: "No products match your search" message
• Clear button appears when search field has content
• Search state persists on page refresh (query param)

❌ Bad:
• Search functionality          (too vague)
• Good UX                       (not a deliverable)
• All necessary components      (meaningless)
• Search and filter features    (bundling — split into specifics)
```

**Scope creep guard:** If an item would take more than 2 days to build on its own, it belongs in a separate spec.

---

### Section 3: OUT OF SCOPE

**Rule:** 2–5 bullet points. Explicitly name things the developer might assume are included.

**Purpose:** Prevent the "I thought you wanted X too" conversation.

**What to include:**
- Adjacent features the user might assume are included
- Future enhancements that are obviously related
- Infrastructure changes that could be inferred

```
✅ Good:
• Advanced filters (category, price range, availability)
• Search result ranking or relevance scoring
• Search history / saved searches
• Server-side search (this spec uses client-side filtering)
• Search analytics / tracking

❌ Bad:
• Rocket surgery           (irrelevant — don't pad)
• World domination         (same)
```

**Rule:** If you're not sure if something is out of scope, ask it as a scope question (Phase 2) — don't silently exclude it.

---

### Section 4: ACCEPTANCE CRITERIA

**Rule:** 3–6 bullet points. Every criterion must be:
1. **Testable** — a QA engineer or developer can verify it with a specific test
2. **Verifiable by X** — explicitly state how to verify it
3. **Binary** — either passes or fails, no "mostly works"

**Format:**
```
☐ {What must be true} — verifiable by {specific test/observation}
```

**The verifiability test:** Replace "verifiable by" with "I will verify this by" and read it aloud. If it sounds like a real test step, it's good. If it sounds like more description, rewrite it.

```
✅ Good:
☐ Search filters the product list as the user types — verifiable by typing "shoe" and confirming only products with "shoe" in the name appear within 300ms
☐ Clearing the search field restores the full product list — verifiable by clearing input and confirming all products reappear
☐ The search field is accessible via keyboard — verifiable by Tab key reaching the input and Enter triggering search
☐ Empty state message appears when no results match — verifiable by typing a nonsense string and confirming "No products found" message appears

❌ Bad:
☐ Search works correctly         (not testable — what does "correctly" mean?)
☐ Good performance               (not binary — how fast is "good"?)
☐ User can search for products   (too vague — this is the goal, not a criterion)
☐ Handle edge cases              (not a criterion — list the specific edge cases)
```

---

### Section 5: EDGE CASES

**Rule:** 2–5 items. Each has a scenario and expected behavior.

**Format:**
```
• {Scenario}: {Expected behavior}
```

**What to include:** Boundary conditions, empty states, error states, unexpected inputs.

**Domain-specific edge cases to always consider:**

| Domain | Always-check edge cases |
|---|---|
| Search / filter | Empty query, no results, special characters, very long query |
| Forms | Empty submission, invalid input, network error on submit, double-submit |
| Lists | Empty list, single item, very long list (1000+ items) |
| Auth | Expired session, wrong credentials, account locked, rate limiting |
| File upload | Empty file, file too large, wrong format, upload failure |
| Payments | Declined card, insufficient funds, timeout, duplicate payment |

```
✅ Good:
• Empty search query: show the full product list (no filtering applied)
• No results: show "No products match '{query}'" with a clear/reset link
• Special characters in query: sanitize and search safely, no errors thrown
• Very long query (> 100 chars): truncate display, still functional

❌ Bad:
• Edge cases handled gracefully    (not a spec — this is a wish, not a behavior)
• Errors shown to user             (too vague — which errors? what message?)
```

---

### Section 6: ASSUMPTIONS

**Rule:** List every CLEAR and INFERABLE clause explicitly. Developers should not be surprised by what was assumed.

**Format:**
```
• {Assumption statement} [{STATED} / {INFERRED from {source}}]
```

```
✅ Good:
• Framework: React 18 [INFERRED from package.json]
• Styling: Tailwind CSS utility classes [INFERRED from tailwind.config.js]
• State management: React useState only (no Redux needed at this scale) [INFERRED from codebase patterns]
• Search is client-side (product list is already loaded in memory) [STATED in prompt]
• No backend changes required [INFERRED from scope of client-side filtering]

❌ Bad:
• Standard assumptions apply    (meaningless)
• React                          (no sourcing, incomplete)
```

**Why this matters:** When an assumption is wrong, the developer needs to know exactly what to override. Tagged sources make corrections fast.

---

### Section 7: TECH CONSTRAINTS

**Rule:** List concrete technical boundaries — what to use and what to avoid.

```
✅ Good:
• Language: TypeScript
• Framework: React 18 with functional components and hooks
• Styling: Tailwind CSS — no custom CSS files
• Search: client-side filtering with Array.filter() — no Fuse.js or search library
• State: React useState — no Redux or Zustand needed
• API: no new endpoints required (data is already fetched by parent component)
• Testing: Vitest + React Testing Library (existing setup)

❌ Bad:
• Use good practices    (not a constraint)
• Modern tech           (meaningless)
• Clean code            (not a constraint)
```

---

## Quality Checklist

Before presenting the spec, verify:

- [ ] GOAL is exactly one sentence with user + action + outcome
- [ ] IN SCOPE has 3–8 specific, non-overlapping deliverables
- [ ] OUT OF SCOPE names adjacent features the dev might assume
- [ ] ACCEPTANCE CRITERIA: each has "verifiable by {specific test}"
- [ ] ACCEPTANCE CRITERIA: all are binary pass/fail
- [ ] EDGE CASES: each has specific expected behavior (not "handled gracefully")
- [ ] ASSUMPTIONS: all are tagged [STATED] or [INFERRED from X]
- [ ] TECH CONSTRAINTS: specific versions/libraries/patterns, not general principles
- [ ] Total spec fits on one screen / ≤ 1 page

---

## Title Generation Rules

The spec title should be:
- 3–6 words
- Noun phrase (not a sentence)
- Specific enough to distinguish from other specs
- Suitable as a filename slug

```
✅ Good:
"Product Search with Client-Side Filtering"
"Login Page with Email and Google OAuth"
"Admin User Management CRUD"
"Order History with Pagination"

❌ Bad:
"Search"                (too generic)
"Build the login page"  (sentence, not noun phrase)
"User feature"          (meaningless)
```

**Slug generation:** lowercase, spaces → hyphens, remove special chars
`"Product Search with Client-Side Filtering"` → `product-search-client-side-filtering`

---

## Spec Length Rules

| Section | Target length | Max length |
|---|---|---|
| Goal | 1 sentence | 1 sentence |
| In Scope | 3–8 bullets | 10 bullets |
| Out of Scope | 2–5 bullets | 6 bullets |
| Acceptance Criteria | 3–6 bullets | 8 bullets |
| Edge Cases | 2–5 bullets | 6 bullets |
| Assumptions | 3–8 bullets | 12 bullets |
| Tech Constraints | 3–8 bullets | 10 bullets |
| **Total** | **≤ 40 lines** | **≤ 55 lines** |

If the spec is longer, it's describing two features. Split it.
