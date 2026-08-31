# Lesson Promotion

Not every mistake belongs in the active rules. Without a filter, the rule pack becomes
noise and stops being read — which is its own failure mode.

## The decision

```
Incident
   │
   ├─ Facility-specific?  ──yes──►  04_FORENSIC_ARCHIVE only. Stop.
   │
   ├─ Could it happen on another B-2/QAPE?  ──no──►  Forensic archive. Stop.
   │
   ▼ yes
Generalize it  →  02_KNOWLEDGE (incident ID, lesson, durable fix)
   │
   ├─ Can it be tested?  ──yes──►  03_REGRESSION (known-bad + known-good)
   │
   ▼
Would recurrence materially damage the output?
   │
   └─ yes ──►  01_ACTIVE_RULES + a release-gate counter
```

## What each answer costs

**Forensic archive only.** Cheap. The incident stays findable for debugging and carries no
ongoing weight. Correct for anything facility-specific or one-off.

**Knowledge without a test.** The lesson is recorded and explains *why* a rule exists, but
nothing fails if it recurs. In the ledger these are marked `RULE ONLY` — they are the
backlog, not the achievement.

**Regression without an active rule.** The control exists and runs, but no gate counts it.
Appropriate when recurrence is annoying rather than damaging.

**Active rule and gate counter.** The full cost: always loaded, always enforced, blocks
delivery. Reserved for defects that materially damage the output.

## Recording a new incident

1. Allocate the next `AAR-R###`. IDs are permanent and never reused.
2. Write the forensic record: observed, root cause, generalized lesson, durable fix,
   verification.
3. Add a ledger row naming the control, test, gate counter, and state.
4. If testable: add a known-bad and a known-good fixture, an expected-results file, and a
   manifest entry. **Run the known-bad first and confirm it fails** — an untested control
   is an assumption.
5. If materially damaging: add the rule and map it to a gate counter.

## After a failed checker run

The ledger is updated from what actually happened, not from what was intended. A checker
rejection is an incident: record it, find the root cause, generalize, and close the loop
before moving on.

## The standard

A mistake is not learned because it was documented. It is learned when it is

**DOCUMENTED · GENERALIZED · TESTED · ENFORCED · RE-RUN · PASSED.**

Anything short of that is a note.
