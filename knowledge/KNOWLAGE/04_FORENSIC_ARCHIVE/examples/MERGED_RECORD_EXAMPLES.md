# Merged-Record Examples

**HISTORICAL EXAMPLE — NOT CURRENT AUDIT AUTHORITY**

Kept as visual benchmarks for what a merged record looks like in a real output. These are
shapes to recognize, never values to reuse.

## Personnel (AAR-R001)

Observed, wrong:

```
M. StuckeyM. Perry | IIII | UTTVT
```

Correct shape:

```
Row 1: M. Stuckey | II | UTT
Row 2: M. Perry   | II | VT
```

Three independent signals, any one sufficient: the glued name boundary (`yM`), a level
outside {I, II, III}, and a method outside the controlled NDT set.

## Equipment (AAR-R002)

Observed, wrong:

```
UTT MeterStep Block
UT113-3726
Thickness ReadingsMeter Verification
```

Correct shape:

```
Row 1: UTT Meter  | UT113 | Thickness Readings
Row 2: Step Block | 3726  | Meter Verification
```

The identifier `UT113-3726` reads as one value and is two. The function cell shows the
same glued boundary as the name.

## Content control (AAR-R005)

Observed, wrong: cell displays `Tank Car Tank`; text extraction returns empty.

Correct: displayed value and extracted value are equal.

## Baseline preservation (AAR-R010)

Observed, wrong: Type COC populated in the baseline, blank in the rollover output, and the
run recorded no disposition for it.

Correct: the value is present in the target, disposition `PRESERVE_BASELINE`.
