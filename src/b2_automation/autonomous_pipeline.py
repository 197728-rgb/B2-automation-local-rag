"""SPEC-1 autonomous end-to-end orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from b2_automation.analyst_agent import analyze_blank_form
from b2_automation.autonomous_contracts import (
    AutonomousRunResult,
    FieldPipelineResult,
    NOT_VERIFIED_TEXT,
    SynthesizedAnswer,
)
from b2_automation.form_writer import write_completed_form
from b2_automation.investigator_agent import gather_evidence, preload_evidence_cache, write_evidence_artifact
from b2_automation.local_extraction import DEFAULT_REVIEW_FORMS, normalize_review_forms, utc_now
from b2_automation.paths import resolve_project_root
from b2_automation.run_store import RunStore
from b2_automation.validation_gate import validate_answer
from b2_automation.writer_agent import synthesize_human_response


@dataclass(frozen=True)
class TemplateRunOutcome:
    template_path: Path
    form_id: str
    status: str
    field_results: list[FieldPipelineResult]
    completed_docx: str | None
    structure_guard_passed: bool


def _resolve_template(root: Path, form_id: str) -> Path | None:
    templates = root / "templates"
    if not templates.is_dir():
        return None
    candidates = [
        templates / f"{form_id}.docx",
        templates / f"B24 (RL2).docx" if form_id == "B24_RL2" else None,
        templates / "B24_RL2.docx",
    ]
    for path in candidates:
        if path and path.is_file():
            return path
    for path in sorted(templates.glob("*.docx")):
        if form_id.replace("_", "").lower() in path.stem.replace(" ", "").replace("(", "").replace(")", "").lower():
            return path
    return None


def _infer_form_id(template_path: Path) -> str:
    stem = template_path.stem
    if "RL2" in stem.upper() or stem.upper().startswith("B24"):
        return "B24_RL2"
    if stem.upper().startswith("B81"):
        return "B81"
    if stem.upper().startswith("B89"):
        return "B89"
    if stem.upper().startswith("B90"):
        return "B90"
    if "COVER" in stem.upper():
        return "Cover_Page"
    return stem.replace(" ", "_")


def run_field_pipeline(
    requirement,
    *,
    source_folder: Path,
    form_id: str,
    evidence_cache: dict,
    template_path: Path,
) -> FieldPipelineResult:
    try:
        evidence = gather_evidence(requirement, source_folder, form_id=form_id, cache=evidence_cache)
        drafted = synthesize_human_response(requirement, evidence)
        validated = validate_answer(requirement, evidence, drafted, template_path=str(template_path))
        return FieldPipelineResult(
            requirement=requirement,
            evidence=evidence,
            answer=validated,
            status=validated.automation_status,
        )
    except Exception as exc:  # noqa: BLE001 — one field must not stop run
        answer = SynthesizedAnswer(
            requirement_id=requirement.id,
            text=NOT_VERIFIED_TEXT,
            confidence=0.0,
            justification=str(exc),
            automation_status="failed_with_fallback",
            fallback_applied=True,
            citations=[],
        )
        from b2_automation.autonomous_contracts import EvidenceBundle

        return FieldPipelineResult(
            requirement=requirement,
            evidence=EvidenceBundle(requirement_id=requirement.id, gaps=[str(exc)]),
            answer=answer,
            status="failed_with_fallback",
        )


def run_autonomous_template(
    template_path: Path,
    *,
    source_folder: Path,
    output_dir: Path,
    root: Path | None = None,
    form_id: str | None = None,
    use_llm_analyst: bool = True,
    run_store: RunStore | None = None,
    run_id: str | None = None,
    persist_sqlite: bool = True,
) -> TemplateRunOutcome:
    root = root or resolve_project_root()
    template_path = Path(template_path).resolve()
    resolved_form = form_id or _infer_form_id(template_path)

    field_map = analyze_blank_form(template_path, root=root, form_id=resolved_form, use_llm=use_llm_analyst)
    evidence_cache = preload_evidence_cache(source_folder)

    field_results: list[FieldPipelineResult] = []
    for req in field_map.fields:
        field_results.append(
            run_field_pipeline(
                req,
                source_folder=source_folder,
                form_id=resolved_form,
                evidence_cache=evidence_cache,
                template_path=template_path,
            )
        )

    stem = template_path.stem
    audit_dir = output_dir / "audit-trail"
    write_evidence_artifact([r.evidence for r in field_results], audit_dir / f"{stem}_evidence.json")

    write_out = write_completed_form(
        template_path=template_path,
        field_map=field_map,
        results=field_results,
        output_dir=output_dir,
    )

    statuses = [r.status for r in field_results]
    if any(s == "failed_with_fallback" for s in statuses):
        run_status = "failed_with_fallback"
    elif any(s != "completed" for s in statuses):
        run_status = "completed_with_warnings"
    else:
        run_status = "completed"

    if persist_sqlite and run_store and run_id:
        run_store.persist_template_run(run_id, resolved_form, field_map, field_results, write_out)

    return TemplateRunOutcome(
        template_path=template_path,
        form_id=resolved_form,
        status=run_status,
        field_results=field_results,
        completed_docx=write_out.get("completed_docx"),
        structure_guard_passed=bool(write_out.get("structure_guard_passed")),
    )


def run_autonomous_pipeline(
    *,
    root: Path | None = None,
    inbox: Path,
    out_dir: Path,
    templates: tuple[str, ...] | None = None,
    use_llm_analyst: bool = True,
    persist_sqlite: bool = True,
) -> AutonomousRunResult:
    """Full autonomous run — analyzeDocxForm through writeCompletedDocx."""
    root = root or resolve_project_root()
    inbox = Path(inbox).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    started = utc_now()
    forms = normalize_review_forms(templates) if templates else DEFAULT_REVIEW_FORMS

    store = RunStore(out_dir / "autonomous.db") if persist_sqlite else None
    run_id = store.create_run(str(inbox), str(out_dir)) if store else None

    outcomes: list[TemplateRunOutcome] = []
    all_results: list[FieldPipelineResult] = []
    completed_forms: list[str] = []

    for form_id in forms:
        tpl = _resolve_template(root, form_id)
        if not tpl:
            continue
        sub_out = out_dir / form_id
        outcome = run_autonomous_template(
            tpl,
            source_folder=inbox,
            output_dir=sub_out,
            root=root,
            form_id=form_id,
            use_llm_analyst=use_llm_analyst,
            run_store=store,
            run_id=run_id,
            persist_sqlite=persist_sqlite,
        )
        outcomes.append(outcome)
        all_results.extend(outcome.field_results)
        if outcome.completed_docx:
            completed_forms.append(outcome.completed_docx)

    if any(o.status == "failed_with_fallback" for o in outcomes):
        status = "failed_with_fallback"
    elif any(o.status != "completed" for o in outcomes):
        status = "completed_with_warnings"
    else:
        status = "completed"

    manifest = {
        "mode": "autonomous",
        "status": status,
        "started_at": started,
        "completed_at": utc_now(),
        "source_folder": str(inbox),
        "templates_processed": [o.form_id for o in outcomes],
        "completed_docx": completed_forms,
        "structure_guard_passed": all(o.structure_guard_passed for o in outcomes) if outcomes else False,
        "low_confidence_field_ids": [
            r.requirement.id
            for r in all_results
            if r.answer.automation_status == "completed_with_low_confidence"
        ],
        "fallback_field_ids": [r.requirement.id for r in all_results if r.answer.fallback_applied],
        "human_review_artifacts": False,
    }
    manifest_path = out_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if store and run_id:
        store.finish_run(run_id, status)

    return AutonomousRunResult(
        started_at=started,
        completed_at=manifest["completed_at"],
        blank_form_path=str(outcomes[0].template_path) if outcomes else "",
        source_folder=str(inbox),
        output_dir=str(out_dir),
        status=status,
        field_count=len(all_results),
        completed_forms=completed_forms,
        field_results=all_results,
        manifest_path=str(manifest_path),
    )
