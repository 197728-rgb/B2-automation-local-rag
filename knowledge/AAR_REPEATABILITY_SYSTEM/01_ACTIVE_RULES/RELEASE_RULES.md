# Release Rules

## 1. A claim ships with a check that can fail

Any completeness or absence claim — "all fields accounted for", "no facility data
present", "every page verified" — ships with an automated check that blocks release when
the claim is false, and that has been *demonstrated failing* on a violating input before
it is trusted.

An unverified claim propagates as fact into every decision that trusts it.

Blocks AAR-R025. This is the rule the system was built around.

## 2. The gate decides, not judgment

Run `tools/release_gate.py RUN_RECORD.json`. It emits the disposition ledger and five
counters:

```
UNACCOUNTED SOURCE FACTS
UNSUPPORTED TARGET VALUES
MERGED IDENTITIES
STRUCTURE VIOLATIONS
MACHINE-READABILITY FAILURES
```

Any non-zero counter, or a failing regression suite → **DO NOT SHIP**.

A filled document also requires a passing structure guard. Blocks AAR-R017.

## 3. Validate the path that ships

A fix exists only on the path that produced the delivered file. Verifying a helper proves
the helper.

Reproduce the original failure first, then show the same check passing on the delivered
artifact.

Blocks AAR-R021.

## 4. A fix without a test is on loan

Any fix that has ever been lost to a revert or merge gets a test that fails without it.
Branch churn reliably deletes undefended changes.

Blocks AAR-R022.

## 5. One canonical copy

Exactly one canonical artifact per subject. Every other copy is marked superseded or
deleted. Near-duplicates agree until one is edited, and then the next reader picks by
accident.

Blocks AAR-R023.

## 6. Delivery allowlist

The delivery folder holds the intended finals and nothing else. No temp, debug, or render
artifacts.
