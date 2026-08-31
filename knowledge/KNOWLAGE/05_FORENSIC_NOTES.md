# 05 FORENSIC NOTES

Historical reasoning only. This file is never current audit authority.

Its purpose is to explain why the active controls exist without retaining customer-specific
B-2 / QAPE facts. It records failure *families*, not incidents (Rule 24).

## Recurrent failure families

### Convenience over authority
Failures recur when the nearest usable string — a filename, folder label, archive name,
shorthand note, prior report, or example — is allowed to displace the governing current
record. The convenient source is not merely easier; it is usually also plausible, which is
what makes it dangerous.

### Identity collapse
Failures recur when visually related records are treated as one semantic object. Record
type, physical leaf location, and entity identity are all part of identity, and a shared
identifier does not merge them. Rows exist to keep identities separable; concatenation
destroys the only thing the table was built to preserve.

### Geometry treated as knowledge
Coordinates are derived output that expires with a document instance. Storing them turns a
routine template revision into silent misplacement, because the stale map still resolves —
it simply resolves to the wrong place.

### Proxy metrics
Successful writes, clean cell counts, narrow search results, raw hashes, plausible renders,
and green process exits are useful signals that can be blind to the defect class being
tested. Each measures something adjacent to correctness and is easier to obtain than
correctness.

### Layer mismatch
A value can satisfy the rendered layer and fail the extracted layer, or the reverse. Both
layers are consumed downstream — one by reviewers, one by automated checks — so verifying
either alone leaves a live failure path.

### Visible emptiness mistaken for structural absence
Document content can carry meaning in XML while appearing empty. Structural checks must
operate below the visible-text layer, and cleanup must not treat blankness as permission.

### Silent degradation
A fallback, a truncation, a narrowed query, or a capped inventory produces output that is
indistinguishable from a complete and confident result. What makes these failures
persistent is not their frequency but their silence.

### Inventory narrowing
Any cap, filter, regex, or pagination boundary converts an incomplete discovery result into
a false inventory unless independently validated. Absence conclusions inherit this error
directly.

### Environment mistaken for evidence
A missing tool, an unreachable source, and an unmaterialized file all present as "nothing
found". Read as evidence absence, they lead to exactly the wrong correction.

### Scratch-state dependence
A workflow can appear repeatable only because artifacts from a previous run remain
available. Only a cold start exposes this, and only before delivery does exposing it help.

### Unverified claims
A completeness or absence claim with nothing that can falsify it is intent presented as
result. This family includes reported corrections: a fix described but not confirmed is
the same failure in a smaller frame. It recurs because writing the claim feels like
performing the check.

### Interface versus implementation
A control tested against the value its code expects, rather than the value its
documentation instructs operators to supply, passes while the documented path walks past
it. The test and the defect never meet.

### Duplicate and superseded references
Near-identical copies agree until one is edited, after which nothing records which won.
Supersession is a declaration; it is not inferrable from timestamp, position, or filename.

### Scope expansion
Work drifts through a sequence of individually reasonable steps, each justified against the
previous step rather than against the original request. The absorbed problems are usually
real, which is why the drift is hard to see from inside it.

### Customer-detail contamination
Concrete historical incidents become retrieval anchors in later work, pulling one
engagement's particulars into another. Reusable knowledge therefore keeps only failure
classes, controls, tests, and decision rules.

## Interpretation rule

Use these notes to understand control rationale. Do not use them to infer facts about a
current audit.
