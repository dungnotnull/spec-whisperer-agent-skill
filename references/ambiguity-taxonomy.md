# Ambiguity Taxonomy

_Load during Phase 1 — Ambiguity Triage._

---

## The Five Categories

Every clause in a prompt falls into exactly one category.

---

### CLEAR
**Definition:** Explicit, specific, and unambiguous. No reasonable interpretation would change what to build.

**Criteria:**
- States the specific technology, behavior, or constraint
- Has only one plausible interpretation in context
- A developer reading it would make the same decision every time

**Examples:**
```
"use TypeScript"                    → CLEAR
"authentication via Google OAuth"   → CLEAR
"paginate at 20 items per page"     → CLEAR
"deploy to Vercel"                  → CLEAR
"store in PostgreSQL"               → CLEAR
"the table must be sortable by date"→ CLEAR
```

**Action:** Lock as stated assumption. List in spec under ASSUMPTIONS with tag [STATED].

---

### INFERABLE
**Definition:** Not explicitly stated but strongly implied by context — existing codebase, prior conversation, industry standard, or obvious domain knowledge.

**Sources of inference (check in order):**
1. Existing files in the codebase (`package.json`, `requirements.txt`, `go.mod`, `*.config.*`)
2. Existing code patterns (auth system, component library, API style)
3. Prior conversation context in this session
4. Industry standard for this domain (login page → needs validation; API → needs error codes)
5. Adjacent features already built ("I already have a product list" → implies similar patterns)

**Examples:**
```
No framework stated, but React visible in package.json    → INFERABLE: React
No DB stated, but Prisma schema exists                    → INFERABLE: PostgreSQL via Prisma
No style stated, but Tailwind in package.json             → INFERABLE: Tailwind
"same as the product list" → patterns visible in code     → INFERABLE: copy patterns
```

**Action:** Lock as inferred assumption. List in spec under ASSUMPTIONS with tag [INFERRED from {source}].

**Inference confidence rule:**
- 2+ signals confirm the same inference → high confidence, lock it
- 1 clear signal → medium confidence, lock it with a note
- No signals, educated guess → do NOT infer, treat as AMBIGUOUS

---

### AMBIGUOUS
**Definition:** Stated in the prompt but could reasonably mean two or more meaningfully different implementations.

**The two-implementation test:** If two different developers, both reasonable, could implement the request differently based on the same clause — it's AMBIGUOUS.

**Examples:**
```
"fast"
  → Could mean: < 200ms response / < 3s page load / sub-second search
  → Ask: "What performance target? e.g., 'search results appear within 500ms'"

"simple"
  → Could mean: minimal features / simple UI / simple code / simple UX
  → Ask: "What does 'simple' mean here — fewer features, or a cleaner UI?"

"real-time"
  → Could mean: WebSocket push / polling every 5s / SSE / on-demand
  → Ask: "How real-time? Live push (WebSocket), or refresh-on-navigate?"

"user profile"
  → Could mean: read-only display / editable fields / with avatar upload
  → Ask: "Can users edit their profile, or is it read-only?"

"notifications"
  → Could mean: in-app / email / push / SMS / all of the above
  → Ask: "What type of notifications? In-app, email, or push?"
```

**Action:** Generate question (candidate). Becomes a question if ranked in top 3 by impact.

---

### MISSING_CRITICAL
**Definition:** A piece of information required to build the feature that is completely absent from the prompt. Implementation cannot begin or would be wrong without it.

**Categories of critical missing information:**

**Acceptance criteria / done condition:**
```
"build a login page"
  → No success condition stated
  → Ask: "How will you know the login page is working? e.g., 'user can sign in with email/password and land on /dashboard'"
```

**Scope boundary:**
```
"build the user management section"
  → No boundary: is it list only? list + detail? list + detail + create + delete?
  → Ask: "What's the scope? List view only, or also create/edit/delete users?"
```

**Data source / entity:**
```
"show the user's orders"
  → No data source: API? DB query? Mock data? Which endpoint?
  → Ask: "Where does order data come from? An existing API endpoint, or do we create a new one?"
```

**Who uses it / permission level:**
```
"add an admin panel"
  → No user type: which admins? any logged-in user? specific role?
  → Ask: "Who can access the admin panel? All authenticated users, or a specific admin role?"
```

**Error / empty state:**
```
"display the list of products"
  → No empty state or error handling spec
  → Ask: "What should happen if the product list is empty, or the API fails?"
  (Only ask if error handling would meaningfully change the implementation)
```

**Action:** Generate question (highest priority candidate — impact score +40).

---

### MISSING_OPTIONAL
**Definition:** Information that would improve the implementation but is not required to start. The agent can make a reasonable default choice.

**Examples:**
```
Button text copy ("Submit" is a fine default)
Exact error message wording
Animation timing (CSS defaults are fine)
Color scheme when a design system exists
Tooltip content
Placeholder text
Loading spinner style
```

**Action:** Do NOT ask about this. Note as TBD in the spec under "Out of Spec". Make a reasonable default choice and implement it.

**The MISSING_OPTIONAL trap:** Many agents ask about optional things because they feel thorough. This is the opposite of helpful — it creates friction for zero implementation value. If the user can change it in 30 seconds after seeing it, don't ask.

---

## Clause Extraction Process

To extract and classify clauses from a prompt:

### Step 1: Identify nouns (entities)
Every noun that will become code: user, product, order, dashboard, button, table, form, endpoint, job, etc.

For each: Is it defined? What properties does it have? Where does it come from? Who can see/modify it?

### Step 2: Identify verbs (actions)
Every action the system or user performs: login, create, update, delete, search, filter, notify, export, etc.

For each: Is the behavior completely described? Are there conditions? What's the result? What about failure?

### Step 3: Identify constraints
Technical: framework, language, library, performance, compatibility
Business: who can do it, when, in what state
UX: layout, responsiveness, accessibility, loading states

For each: Stated explicitly? Inferable? Or absent?

### Step 4: Identify the success condition
The single most important thing: how does the developer / user know it's working?

If not stated → MISSING_CRITICAL.

---

## Worked Example

**Prompt:** "add a search bar to the products page"

**Clause extraction:**

| Clause | Category | Rationale |
|---|---|---|
| "search bar" — UI component | CLEAR | It's a text input that filters |
| "products page" — scope | INFERABLE | Page likely exists, check codebase |
| search triggers on: keystroke vs submit? | AMBIGUOUS | Two valid implementations |
| filters which fields? name only vs name+description+sku | MISSING_CRITICAL | Different DB queries |
| what if no results? | MISSING_OPTIONAL | Can default to "No products found" |
| minimum character threshold? | MISSING_OPTIONAL | Can default to 1 or 2 |

**Top questions by impact:**
1. [MISSING_CRITICAL] What fields should be searched — just product name, or also description and SKU?
2. [AMBIGUOUS] Should search trigger as the user types, or only when they press Enter?

**Score:** 100 - 8 (1 ambiguous) - 20 (1 missing_critical) = 72% → Good

**Note:** Only 2 questions — fewer than 3 is correct. Never pad to 3.
