# AAR Repeatability System

Version 2.0 · Supersedes the KNOWLAGE knowledge packs (1.2, 1.3)

A closed learning loop for AAR M-1002 Exhibit B-2 and QAPE audit work. Its purpose is not
to store lessons. It is to make a repeated mistake **fail** rather than depend on anyone,
human or model, remembering it.

## The loop

```
MISTAKE OCCURS
      ↓
Record exact incident          →  04_FORENSIC_ARCHIVE/
      ↓
Identify root cause
      ↓
Generalize the lesson          →  02_KNOWLEDGE/
      ↓
Create durable prevention rule →  01_ACTIVE_RULES/
      ↓
Create KNOWN-BAD test          →  03_REGRESSION/known_bad/
      ↓
Create KNOWN-GOOD test         →  03_REGRESSION/known_good/
      ↓
Add mandatory release gate     →  tools/release_gate.py
      ↓
Future run MUST pass
      ↓
Only then ship
```

`tools/LESSON_PROMOTION.md` decides how far an incident travels, so the rule layer stays
small enough to be read.

## The four layers, and why they are separate

| Layer | Contains | Size | Loaded |
|---|---|---|---|
| `01_ACTIVE_RULES/` | Only what must never be violated | Small | Always |
| `02_KNOWLEDGE/` | Why the rules exist; how failures happened | Medium | On demand |
| `03_REGRESSION/` | Executable known-bad / known-good cases | Grows | Every run |
| `04_FORENSIC_ARCHIVE/` | Exact historical incidents | Grows | Debugging only |

The separation is the point. A single pile of lessons is unreadable, so it stops being
read; the rules must stay short enough that following them is easier than skipping them.
And the forensic archive is never audit-value authority — it records what happened once,
not what is true now.

## What actually prevents recurrence

Layers 1, 2 and 4 are documents. A future session can write around a document.

Layer 3 and the release gate cannot be written around:

```
$ python 03_REGRESSION/run_regression.py
TEST           INCIDENT    BAD   GOOD  STATUS
TEST-B81-001   AAR-R001    FAIL  PASS  PASS
...
All 9 controls working: every known-bad case fails, every known-good case passes.

$ python tools/release_gate.py RUN_RECORD.json
MERGED IDENTITIES: 3
DO NOT SHIP
```

Both halves are required. A known-bad case that must fail proves the control catches the
defect; a known-good case that must pass proves it does not simply reject everything.

## Incident IDs

Every mistake gets a permanent `AAR-R###`, and every test names the incident it protects:

```
TEST-B81-001  protects against  AAR-R001   (personnel records concatenated)
TEST-B81-002  protects against  AAR-R002   (equipment records concatenated)
```

When something recurs, the ID tells you *which* link broke:

1. the rule was missing;
2. the test was missing;
3. the test existed but was not run;
4. the test was defective;
5. the shipping path bypassed the validator.

That is a diagnosis. "It did it again" is not.

## The shipping gate

`tools/release_gate.py` emits a disposition ledger — every source fact, its target, and
what happened to it — then five counters:

```
UNACCOUNTED SOURCE FACTS: 0
UNSUPPORTED TARGET VALUES: 0
MERGED IDENTITIES: 0
STRUCTURE VIOLATIONS: 0
MACHINE-READABILITY FAILURES: 0
REGRESSION SUITE: PASS

SHIP
```

Any non-zero counter, or a failing suite, prints `DO NOT SHIP` and exits non-zero.

## Quick start

```bash
python 03_REGRESSION/run_regression.py            # are the controls working?
python tools/release_gate.py my_run_record.json   # may this ship?
```

Run record format: `03_REGRESSION/schema.md`.

## The standard

A mistake is not learned because it was documented. It is learned when it is

**DOCUMENTED · GENERALIZED · TESTED · ENFORCED · RE-RUN · PASSED.**

## Evolving this system

Reissue it whole. No fragment patching, no bolting rules onto the side — that is
AAR-R023's failure mode applied to the rule set itself. When it changes, the next version
is a complete consolidated package, and the old one is marked superseded.
