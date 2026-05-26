"""SENTINEL CLI.

    b2-sentinel [--cognitive|--no-cognitive] run [--form FORM_ID]+ [--inbox PATH] [--output PATH] [--cognitive|--no-cognitive]
    b2-sentinel discover                 -- list forms with available templates and approval maps
    b2-sentinel judge OUT_DIR            -- re-run Layer 6 on a previous run's filled DOCX
    b2-sentinel rollover --form FORM_ID  -- run rollover memory only

The default `run` (no flags) runs every DOCX template that has generated or approved wiring against ./inbox.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import click
from rich.console import Console
from rich.table import Table

from .cognitive.adapter import create_adapter, set_adapter
from .cognitive.config import load_cognitive_config, get_cognitive_config
from .core.paths import (
    ACTIVE_FORMS,
    INBOX_DIR,
    OUTPUTS_DIR,
    PRIOR_PACKET_DIR,
    REPO_ROOT,
    form_map_path,
    form_template_path,
)
from .core.status import FinalStatus
from .layer1_form_brain.write_authority import list_available_forms
from .layer8_audit_packet.run_manifest import make_manifest, write_manifest
from .pipeline import run_form

console = Console()


@click.group(invoke_without_command=True)
@click.option("--form", "forms", multiple=True, help="One or more form ids; default = all wired templates.")
@click.option("--inbox", "inbox", type=click.Path(path_type=Path), default=None, help="Evidence inbox.")
@click.option("--output", "output", type=click.Path(path_type=Path), default=None, help="Outputs dir.")
@click.option("--cognitive/--no-cognitive", "cognitive_flag", default=None, help="Enable/disable cognitive layer.")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None, help="Path to b2-sentinel.yaml.")
@click.pass_context
def cli(ctx: click.Context, forms: tuple[str, ...], inbox: Path | None, output: Path | None, cognitive_flag: bool | None, config_path: Path | None) -> None:
    """B2 SENTINEL - closed-loop B-2 compliance intelligence."""
    yaml_path = config_path or (REPO_ROOT / "b2-sentinel.yaml")
    config = load_cognitive_config(yaml_path)
    if cognitive_flag is not None:
        config.enabled = cognitive_flag
        from .cognitive.config import set_cognitive_config
        set_cognitive_config(config)
    set_adapter(create_adapter(config))

    if config.enabled:
        console.print(f"[bold magenta]Cognitive layer: ON[/bold magenta] (adapter={config.adapter}, model={config.model})")

    if ctx.invoked_subcommand is None:
        ctx.invoke(run, forms=forms, inbox=inbox, output=output, cognitive_flag=None)


@cli.command("run")
@click.option("--form", "forms", multiple=True, help="Form ids to run; default = all wired templates.")
@click.option("--inbox", "inbox", type=click.Path(path_type=Path), default=None)
@click.option("--output", "output", type=click.Path(path_type=Path), default=None)
@click.option("--cognitive/--no-cognitive", "cognitive_flag", default=None, help="Enable/disable cognitive layer (overrides config).")
def run(forms: tuple[str, ...], inbox: Path | None, output: Path | None, cognitive_flag: bool | None) -> None:
    """Run the SENTINEL pipeline against the inbox."""
    if cognitive_flag is not None:
        config = get_cognitive_config()
        config.enabled = cognitive_flag
        from .cognitive.config import set_cognitive_config
        set_cognitive_config(config)
        set_adapter(create_adapter(config))
        if config.enabled:
            console.print(f"[bold magenta]Cognitive layer: ON[/bold magenta] (adapter={config.adapter}, model={config.model})")

    inbox = inbox or INBOX_DIR
    output = output or OUTPUTS_DIR
    selected: list[str] = list(forms) if forms else list(ACTIVE_FORMS)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started = datetime.now()
    console.rule(f"[bold cyan]B2 SENTINEL run {run_id}")
    console.print(f"Inbox: [yellow]{inbox}[/yellow]")
    console.print(f"Forms: [yellow]{', '.join(selected)}[/yellow]")

    results = []
    artifacts_by_form: dict[str, list[str]] = {}
    final_statuses: dict[str, FinalStatus] = {}
    errors: dict[str, str] = {}

    for form_id in selected:
        try:
            result = run_form(form_id, run_id=run_id, inbox=inbox, outputs_dir=output)
        except Exception as exc:  # noqa: BLE001
            message = f"{type(exc).__name__}: {exc}"
            console.print(f"[red]ERROR[/red] running {form_id}: {message}")
            artifacts_by_form[form_id] = []
            final_statuses[form_id] = FinalStatus.FAILED_RUNTIME_ERROR
            errors[form_id] = message
            continue
        results.append(result)
        artifacts_by_form[form_id] = list(result.artifacts.keys())
        final_statuses[form_id] = result.final_status
        emoji = "[green]OK[/green]" if result.overall_passed else "[red]X[/red]"
        console.print(f"  {emoji} {form_id} -> {result.final_status.value} ({result.out_dir})")

    finished = datetime.now()
    manifest = make_manifest(
        run_id=run_id,
        started_at=started,
        finished_at=finished,
        forms=selected,
        artifacts=artifacts_by_form,
        final_statuses=final_statuses,
        errors=errors,
    )
    run_dir = output / run_id
    write_manifest(manifest, run_dir / "run_manifest.json")

    # Cross-form consistency check (packet-level intelligence)
    if len(results) >= 2:
        from .ontology.builder import load_ontology
        from .ontology.consistency import check_packet_consistency, write_consistency_report
        ontology = load_ontology()
        consistency = check_packet_consistency(ontology, run_dir, selected)
        write_consistency_report(consistency, run_dir / "cross_form_consistency.json")
        if not consistency.passed:
            console.print(
                f"\n[bold yellow]CROSS-FORM CONSISTENCY:[/bold yellow] "
                f"{len(consistency.violations)} violation(s) detected"
            )
            for v in consistency.violations[:5]:
                console.print(f"  [red]{v.canonical_id}[/red]: {v.message}")

    _summary_table(results)
    if errors:
        console.print("[red]Runtime errors:[/red]")
        for form_id, message in errors.items():
            console.print(f"  - {form_id}: {message}")
    if errors or len(results) != len(selected) or not all(r.overall_passed for r in results):
        sys.exit(2)


def _summary_table(results) -> None:
    table = Table(title="Run Summary", show_lines=True)
    table.add_column("Form", style="cyan", no_wrap=True)
    table.add_column("Final Status")
    table.add_column("Format")
    table.add_column("Completion")
    table.add_column("Output Dir")
    for r in results:
        cr = None
        try:
            cr_path = r.out_dir / "completion_report.json"
            if cr_path.exists():
                import json
                with cr_path.open(encoding="utf-8") as fh:
                    cr = json.load(fh)
        except Exception:  # noqa: BLE001
            cr = None
        fmt = "OK" if cr and cr.get("overall_passed_format") else "FAIL"
        comp = "OK" if cr and cr.get("overall_passed_completion") else "FAIL"
        status_color = "green" if r.overall_passed else "red"
        table.add_row(
            r.form_id,
            f"[{status_color}]{r.final_status.value}[/{status_color}]",
            fmt,
            comp,
            str(r.out_dir),
        )
    console.print(table)


@cli.command("discover")
def discover() -> None:
    """List forms with available templates and approval maps."""
    table = Table(title="SENTINEL Forms")
    table.add_column("Form ID")
    table.add_column("Template")
    table.add_column("Approval Map")
    table.add_column("Has Prior Packet")
    for fid in list_available_forms():
        tpl = form_template_path(fid)
        amp = form_map_path(fid)
        prior = any(PRIOR_PACKET_DIR.glob(f"*{fid.upper().replace('_RL2', '').replace('_PAGE', ' PAGE')}*.docx")) if PRIOR_PACKET_DIR.exists() else False
        table.add_row(
            fid,
            "OK" if tpl.exists() else "missing",
            "OK" if amp.exists() else "missing",
            "yes" if prior else "no",
        )
    console.print(table)


@cli.command("judge")
@click.argument("out_dir", type=click.Path(path_type=Path, exists=True, file_okay=False))
def judge_cmd(out_dir: Path) -> None:
    """Re-run Layer 6 on a previously generated form packet directory."""
    from .layer6_completion_judge.judge import judge_completion
    from .layer6_completion_judge.self_critique import self_critique
    from .layer1_form_brain.obligation_graph import load_obligation_graph
    import json

    form_id = out_dir.name
    graph = load_obligation_graph(form_id)
    review_path = out_dir / "review.json"
    structure_path = out_dir / "structure_guard_report.json"
    filled = out_dir / f"{form_id}_filled.docx"
    if not (review_path.exists() and structure_path.exists() and filled.exists()):
        console.print(f"[red]Missing artifacts in {out_dir}[/red]")
        sys.exit(1)
    from .core.models import StructureGuardReport, FieldDecision

    structure_report = StructureGuardReport.model_validate_json(structure_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    decisions = {
        fid: FieldDecision.model_validate(payload)
        for fid, payload in review["decisions"].items()
    }

    completion = judge_completion(
        graph=graph, decisions=decisions,
        filled_path=filled, structure_report=structure_report,
    )
    critique = self_critique(graph=graph, decisions=decisions, filled_path=filled, completion=completion)
    console.print(f"Final status: [bold]{completion.final_status.value}[/bold]")
    console.print(f"Self-critique passed: {critique['passed']}")
    if critique["findings"]:
        console.print("Findings:")
        for f in critique["findings"]:
            console.print(f"  - {f}")


@cli.command("rollover")
@click.option("--form", "form_id", required=True)
@click.option("--inbox", "inbox", type=click.Path(path_type=Path), default=None)
def rollover_cmd(form_id: str, inbox: Path | None) -> None:
    """Run rollover memory only - compares prior_b2_packet vs current evidence."""
    from .agents.agent1_regulatory_analyst import run_regulatory_analyst
    from .agents.agent2_forensic_investigator import run_forensic_investigator
    from .innovations.rollover_memory import evaluate_rollover
    from .pipeline import _find_prior_packet_for
    import json

    inbox = inbox or INBOX_DIR
    a1 = run_regulatory_analyst(form_id)
    a2 = run_forensic_investigator(graph=a1.obligation_graph, inbox=inbox)
    prior = _find_prior_packet_for(form_id)
    if not prior:
        console.print(f"[red]No prior packet found for {form_id} under {PRIOR_PACKET_DIR}[/red]")
        sys.exit(1)
    entries = evaluate_rollover(graph=a1.obligation_graph, new_ledger=a2.ledger, prior_filled_path=prior)
    table = Table(title=f"Rollover for {form_id}")
    table.add_column("Field")
    table.add_column("Old")
    table.add_column("New")
    table.add_column("Decision", style="bold")
    table.add_column("Reason")
    for e in entries:
        table.add_row(e.field_id, e.old_value or "-", e.new_candidate or "-", e.rollover_decision.value, e.reason)
    console.print(table)


@cli.command("ontology")
@click.option("--rebuild", is_flag=True, help="Force rebuild from approval maps.")
@click.option("--stats", is_flag=True, help="Show ontology statistics.")
def ontology_cmd(rebuild: bool, stats: bool) -> None:
    """Build, inspect, or rebuild the global field ontology."""
    from .ontology.builder import build_ontology, save_ontology, load_ontology, ONTOLOGY_PATH

    if rebuild or not ONTOLOGY_PATH.exists():
        ontology = build_ontology()
        out = save_ontology(ontology)
        console.print(f"[green]Ontology built:[/green] {out}")
    else:
        ontology = load_ontology()
        console.print(f"[green]Ontology loaded:[/green] {ONTOLOGY_PATH}")

    total = len(ontology.canonical_fields)
    by_cat: dict[str, int] = {}
    consistency_required = 0
    for cf in ontology.canonical_fields.values():
        by_cat[cf.category] = by_cat.get(cf.category, 0) + 1
        if cf.cross_form_consistency_required:
            consistency_required += 1

    console.print(f"\n[bold]Canonical Fields:[/bold] {total}")
    console.print(f"[bold]Cross-form consistency enforced:[/bold] {consistency_required}")
    console.print(f"\n[bold]By Category:[/bold]")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        console.print(f"  {cat:20s} {count:4d}")

    if stats:
        console.print(f"\n[bold]Top Identity Fields (consistency required):[/bold]")
        identity = [
            cf for cf in ontology.canonical_fields.values()
            if cf.cross_form_consistency_required
        ]
        for cf in sorted(identity, key=lambda x: -len(x.bindings))[:15]:
            forms = [b.form_id for b in cf.bindings]
            console.print(f"  {cf.canonical_id:45s} ({len(forms):2d} forms)")


def main(argv: Iterable[str] | None = None) -> int:
    try:
        cli(args=list(argv) if argv is not None else None, standalone_mode=False)
        return 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    except click.exceptions.ClickException as exc:
        exc.show()
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]ERROR:[/red] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
