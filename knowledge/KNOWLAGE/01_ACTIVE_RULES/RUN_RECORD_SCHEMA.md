# Run Record Format

Tool-agnostic JSON. Any pipeline that can emit this can be gated, whatever produced the
document.

Every key is optional; a check with no data to inspect simply finds nothing. That is
deliberate — a partial record can still be gated on what it does carry.

```jsonc
{
  "mode": "MAINTENANCE",            // MAINTENANCE | NEW_FILL | FINAL_REVIEW   (G-1)
  "accepted_baseline_exists": true, // is there an accepted completed current form?
  "document_status": "DRAFT",       // DRAFT | FINAL | RELEASED                (AAR-R009)

  // Direction A: every populated baseline/source fact needs a disposition.   (G-5)
  "source_facts": [
    {
      "key": "B24/type_coc",
      "target": "B24 Type COC",
      "value": "Type COC A",         // what the baseline held
      "target_value": "Type COC A",  // what the output holds
      "disposition": "PRESERVE_BASELINE",
      "incident": "AAR-R010"         // optional: attribute to a known incident
    }
  ],

  // Repeating rows. One identity per row.                        (AAR-R001, AAR-R002)
  "rows": [
    {"kind": "personnel", "table": "B81_personnel", "row": 1,
     "cells": {"name": "M. Stuckey", "level": "II", "method": "UTT"}},
    {"kind": "equipment", "table": "B81_equipment", "row": 1,
     "cells": {"equipment_name": "UTT Meter", "equipment_id": "UT113",
               "function": "Thickness Readings"}}
  ],

  // TCID entries, compared baseline against target.                       (AAR-R003)
  "tcid_entries": [
    {"id": "tcid-1",
     "baseline": {"revision": "0", "record_type": "Inspection", "entry_type": "Qual"},
     "target":   {"revision": "0", "record_type": "Inspection", "entry_type": "Qual"}}
  ],

  // What a reader sees vs what an extractor reads.                        (AAR-R005)
  "fields": [
    {"key": "B24/demonstration_type", "visible": "Tank Car Tank",
     "machine": "Tank Car Tank"}
  ],

  // Protected geometry, before and after the write.                       (AAR-R006)
  "structure": {
    "tables_before": 12, "tables_after": 12,
    "rows_before": 210,  "rows_after": 210,
    "merges_before": 34, "merges_after": 34,
    "document_wide_formatting_pass": false
  },

  // Comparisons must be between the same semantic field.                  (AAR-R008)
  "comparisons": [
    {"id": "cmp-1", "source_field": "B24/date_permission_received",
     "target_field": "B24/date_permission_received"}
  ],

  // Findings the run intends to report.                                   (AAR-R009)
  "reported_findings": [
    {"type": "SIGNATURE_BLANK", "location": "Cover/auditor_signature"}
  ]
}
```

## Dispositions

`CONFIRMED_VALUE` · `PRESERVE_BASELINE` · `CONTROLLED_BLANK` · `AUTHORIZED_NA` ·
`WITHHOLD_CONFLICT` · `UNVERIFIABLE`

Anything else — including a missing disposition or `UNACCOUNTED` — is a blocking finding.

A fact marked `PRESERVE_BASELINE` or `CONFIRMED_VALUE` whose `target_value` is blank is
also blocking: that is AAR-R010, the claim of preservation without the preservation.
