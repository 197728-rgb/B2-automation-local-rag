# B2 Sentinel Governance Baseline

B2 Sentinel is governed cognitive infrastructure for B-2 compliance production.

## Controlling Principle

LLM reasons. Deterministic system governs.

The cognitive layer may support evidence discovery, ambiguity review, contradiction detection, semantic aliasing, uncertainty scoring, and evidence synthesis.

The cognitive layer may not directly write, bypass approval maps, override validators, ignore blockers, invent evidence, or create fake completion.

Validators, exact approval maps, structure guard, required-policy overlays, and completion policy remain the legal authority.

## Hard Blockers

These acceptance gates are hard blockers and must not be bypassed by adapters, prompts, aliases, or retrieval confidence:

- Exact approval maps authorize DOCX writes.
- Required fields without governed evidence become REVIEW_REQUIRED or another blocking state.
- Low-confidence values cannot be silently promoted.
- Conflicts and contradictions must remain traceable and reviewable.
- Filled output must not be handed off unless the structure guard passes.
- Completion must fail honestly when required obligations are unmet.

## LLM Boundary

The LLM may recommend, explain, classify risk, synthesize evidence, and identify ambiguity.

The LLM may not act as write authority, validation authority, completion authority, or exception authority.

Every promoted value must remain traceable, reviewable, explainable, and governed.
