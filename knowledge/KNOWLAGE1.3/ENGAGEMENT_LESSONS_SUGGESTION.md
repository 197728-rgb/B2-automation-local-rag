# Engagement Lessons Suggestion

Proposed promotions into durable engagement and assistant-level guidance. **None of these
are adopted.** Adopted knowledge is in the governing files listed in `README.md`; this is a
proposal register and never overrides them.

Each proposal states what to add, what it buys, and what it costs — so that a decision can
be made rather than assumed.

---

## P-1 — Ship a short activation block, not the whole pack

**Proposal.** Add this to assistant-level standing instructions:

```text
AAR B-2 / QAPE work:
- Lock the mode first: maintenance/rollover, new fill, or final review.
- An accepted completed current form is the maintenance baseline. A blank is the
  baseline only when no accepted baseline exists or regeneration is required.
- Discover fields from the current controlled form and elements from the current
  audited scope. Never reuse remembered table coordinates.
- Resolve semantic identity first, then the physical cell in the current file.
- Every source fact and every relevant target field ends with a recorded disposition.
- Exhaust the applicable record before concluding absence.
- Keep distinct people, equipment, and records in distinct rows.
- Keep program-level and technical-demonstration evidence separate.
- Apply formatting inside the governed write; never sweep afterward.
- Verify semantics, machine-readable extraction, and every rendered page.
- Validate the artifact that actually ships; deliver only intended finals.
- New audit, new session. Facility evidence is never permanent knowledge.
```

**Buys.** The controls apply from the first message, before this pack is opened.
**Costs.** Standing-instruction space, and it needs reissuing whole when it changes (F-35).

## P-2 — Require an explicit mode declaration in the first reply

**Proposal.** On any B-2 or QAPE task, state the mode and the baseline document before
doing anything else, and ask if either is ambiguous.

**Buys.** Closes E-001 and E-004 at the cheapest possible point — before any reading.
**Costs.** One extra exchange when the mode is already obvious from context.

## P-3 — Treat retrieval output as candidates only, everywhere

**Proposal.** Extend the repository's write-authority rule to all reasoning, not just to
DOCX writes: retrieval, embeddings, and model judgment may propose and explain; only a
deterministic, exact, versioned map may authorize a location.

**Buys.** Generalizes the strongest control already in the codebase (F-10) to every
surface, including any future form type.
**Costs.** More cases end in review rather than autofill.

## P-4 — Make degradation loud by default

**Proposal.** Any fallback, weaker source, skipped OCR path, or unavailable dependency is
named in the output artifact, never silently absorbed.

**Buys.** Closes E-014 and, with it, E-043 — an environment failure stops reading as
absent evidence.
**Costs.** Noisier artifacts on healthy runs.

## P-5 — Require a regression test with every restored fix

**Proposal.** When a fix is reapplied after a revert or merge loss, it does not land
without a test that fails in its absence.

**Buys.** The repository shows the same extraction fixes restored at least three separate
times (E-036). This is the only control that stops the cycle.
**Costs.** Slower on the fix that is already understood and urgent.

## P-6 — Declare precedence whenever two documents govern one subject

**Proposal.** When guidance splits across documents, one of them states the split and both
link to it. An undeclared split is treated as a defect in the guidance, not a judgment call
for the reader.

**Buys.** Prevents the write-authority ambiguity recorded as C-1 in
`KNOWLEDGE_SOURCES_INDEX.md` from recurring in the next pair of documents.
**Costs.** A maintenance obligation on every guidance change.

## P-7 — Keep permanent knowledge and audit evidence in separate stores

**Proposal.** Adopt the folder split proposed in `GOOGLE_DRIVE_UPDATE_SUGGESTIONS.md`
(D-1) as an engagement-level rule, not a Drive-specific cleanup: permanent knowledge is a
store that can be loaded in any session; audit evidence is a store that can be loaded in
exactly one.

**Buys.** Makes the boundary in `README.md` structural instead of a matter of care.
**Costs.** A one-time reorganization, and discipline about where new files land.

## P-8 — Ask for the current controlled form, every time

**Proposal.** Where a task depends on a form's structure, request the current controlled
form rather than working from any stored schema, alias list, or template copy.

**Buys.** Makes A-01, A-02, and A-03 structurally impossible instead of merely warned
against.
**Costs.** One request at the start of each job; occasional friction when the user expects
the form to be already known.

---

## Adoption

Proposals move into the governing files only after they are used in a real job and hold.
On adoption, the proposal is deleted from this file and appears once in the file that owns
its axis — never in both.
