# PROJECT-DEVELOPMENT-PHASE-TRACKING.md

_Last Updated: 2026-06-07_

---

## Project: spec-whisperer
**Version:** 1.0.0
**Status:** ✅ All Phases Complete

---

## Phase Overview

| Phase | Name | Status | Deliverables |
|---|---|---|---|
| 1 | Architecture & Design | ✅ Done | CLAUDE.md, PROJECT-detail.md, this file |
| 2 | Core Skill File | ✅ Done | skill/SKILL.md |
| 3 | Reference Library | ✅ Done | 4 reference .md files |
| 4 | Core Scripts | ✅ Done | 5 Python scripts |
| 5 | Assets & Templates | ✅ Done | spec_template.md, confidence_thresholds.json |
| 6 | Evaluation Suite | ✅ Done | evals/evals.json — 10 test cases |
| 7 | README | ✅ Done | README.md |

---

## Phase 1: Architecture ✅
- [x] Core problem statement: unstructured intent transfer
- [x] Ambiguity taxonomy: CLEAR / INFERABLE / AMBIGUOUS / MISSING_CRITICAL / MISSING_OPTIONAL
- [x] Micro-spec format (7 sections, exactly 1 page)
- [x] Confidence scoring formula (base 100, deductions + bonuses)
- [x] Question selection algorithm (impact scoring, max 3)
- [x] Trigger detection (high-confidence, context-required, skip, re-use)
- [x] Spec storage system (.specs/ + index.json)
- [x] 3 integration modes + 9 edge cases
- [x] CLAUDE.md, PROJECT-detail.md, this tracker

## Phase 2: Core Skill File ✅
- [x] YAML frontmatter with precise trigger description
- [x] Phase 0–4 harness with explicit decision logic
- [x] Trigger detection rules
- [x] Ambiguity triage protocol
- [x] Question selection and presentation format
- [x] Spec generation instructions
- [x] Confidence scoring instructions
- [x] Lock protocol with user approval flow
- [x] Skip/re-use logic
- [x] Reference file load guidance

## Phase 3: Reference Library ✅
- [x] `ambiguity-taxonomy.md` — full classification rules with examples
- [x] `question-priority-guide.md` — impact scoring + question writing rules
- [x] `spec-format-guide.md` — section rules, length limits, quality criteria
- [x] `confidence-scoring-rubric.md` — formula, deductions, bonuses, interpretation

## Phase 4: Core Scripts ✅
- [x] `spec_whisperer.py` — main orchestrator (all modes)
- [x] `prompt_parser.py` — prompt clause extractor and classifier
- [x] `question_ranker.py` — impact scoring and top-3 selector
- [x] `spec_generator.py` — micro-spec markdown generator
- [x] `spec_store.py` — save/load/search specs in .specs/

## Phase 5: Assets ✅
- [x] `spec_template.md` — full spec skeleton with placeholders
- [x] `confidence_thresholds.json` — score bands and agent actions

## Phase 6: Evaluation Suite ✅
- [x] 10 test cases covering all trigger types and confidence bands
- [x] Edge cases: vague prompt, over-specified, re-use, skip, multi-feature

## Phase 7: README ✅
- [x] Install guide (3 modes)
- [x] Quick-start examples
- [x] Example spec output
- [x] Configuration reference

---

## Key Design Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-06-07 | Max 3 questions | More questions kill vibe-coding momentum; ruthless prioritization is the skill |
| 2026-06-07 | Confidence score is a deduction model (start at 100) | Makes gaps visible; easier to explain than additive scoring |
| 2026-06-07 | Spec is exactly ≤ 1 page | Longer = project plan, not spec; brevity forces prioritization |
| 2026-06-07 | Agent won't start coding below 30% confidence | Hard floor prevents hallucinating entire architectures |
| 2026-06-07 | Acceptance criteria must have "verifiable by X" | Untestable criteria are worthless; verifiability is the spec's whole point |
| 2026-06-07 | Specs saved to .specs/ with index.json | Enables spec re-use across sessions; builds a project knowledge base |
