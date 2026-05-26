"""Cognitive Orchestration Layer.

The LLM reasons. The deterministic system governs.

This layer produces structured reasoning objects that the deterministic spine
consumes as enriched input. It never writes to DOCX, never decides
authorization, and never bypasses the approval map.
"""
