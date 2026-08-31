# Engagement Lessons — Suggestions

Proposed changes to how engagements are run. **None are adopted**; nothing here overrides
`01_ACTIVE_RULES/`.

## S-1 — Ship a short activation block, not the archive

Put a condensed form of `ACTIVE_RULES.md` into standing assistant instructions so the
rules apply from the first message, before anything is loaded.

*Buys:* controls active immediately. *Costs:* instruction space; must be reissued whole
when it changes.

## S-2 — Declare mode in the first reply

On any B-2/QAPE task, state mode and baseline before anything else, and ask if either is
ambiguous.

*Buys:* closes AAR-R007 at the cheapest point. *Costs:* one exchange when it is obvious.

## S-3 — Separate permanent knowledge from audit evidence structurally

Two stores: one loadable in any session, one loadable in exactly one. Makes AR-03 a
property of the layout rather than of care.

*Buys:* removes the contamination path entirely. *Costs:* one reorganization plus
discipline about where new files land.

## S-4 — Ask for the current controlled form every time

Where a task depends on a form's structure, request the current form rather than working
from a stored schema or template copy.

*Buys:* makes the "fixed table map" assumptions structurally impossible. *Costs:* one
request per job; occasional friction when the form seems already known.

## S-5 — Require a regression test with every restored fix

A fix reapplied after a revert does not land without a test that fails in its absence.

*Buys:* the only thing that stops the "fixed this three times" cycle. *Costs:* slower on
the urgent, already-understood fix.

## S-6 — Update the ledger after every failed checker run

A checker rejection is an incident: record it, find the root cause, generalize, close the
loop before moving on. The ledger is written from what happened, not from what was
intended.

*Buys:* the loop actually closes. *Costs:* a few minutes per rejection.

## S-7 — Give the operator a cheap early interrupt

The most effective correction available is a short mid-task message ("too big", "off
track"). Two such messages corrected more in this session than any file did.

*Buys:* catches drift while it is cheap. *Costs:* none.

## Adoption

A suggestion moves into `01_ACTIVE_RULES/` only after it has been used on a real job and
held. On adoption it is deleted here and appears once there — never in both.
