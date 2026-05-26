"""SQLite persistence for autonomous audit runs (SPEC minimal schema)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from b2_automation.autonomous_contracts import FieldPipelineResult, MachineFieldMapV1
from b2_automation.local_extraction import utc_now


class RunStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_runs (
                  id TEXT PRIMARY KEY,
                  blank_form_path TEXT NOT NULL,
                  source_folder_path TEXT NOT NULL,
                  output_dir TEXT NOT NULL,
                  status TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS machine_field_maps (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  version TEXT NOT NULL,
                  template_file TEXT NOT NULL,
                  activity_code TEXT,
                  field_count INTEGER NOT NULL,
                  auto_fillable_field_count INTEGER NOT NULL,
                  low_confidence_field_count INTEGER NOT NULL,
                  raw_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_requirements (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  field_label TEXT NOT NULL,
                  field_type TEXT NOT NULL,
                  table_index INTEGER,
                  row_index INTEGER,
                  column_index INTEGER,
                  mapped_schema_path TEXT,
                  mapping_confidence REAL NOT NULL,
                  can_auto_fill INTEGER NOT NULL,
                  fallback_behavior TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS synthesized_answers (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  requirement_id TEXT NOT NULL,
                  answer_text TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  automation_status TEXT NOT NULL,
                  fallback_applied INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS form_writes (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  requirement_id TEXT NOT NULL,
                  output_file TEXT NOT NULL,
                  write_status TEXT NOT NULL
                );
                """
            )

    def create_run(self, source_folder: str, output_dir: str) -> str:
        run_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_runs (id, blank_form_path, source_folder_path, output_dir, status, started_at) VALUES (?,?,?,?,?,?)",
                (run_id, "", source_folder, output_dir, "running", utc_now()),
            )
        return run_id

    def finish_run(self, run_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE audit_runs SET status=?, completed_at=? WHERE id=?",
                (status, utc_now(), run_id),
            )

    def persist_template_run(
        self,
        run_id: str,
        form_id: str,
        field_map: MachineFieldMapV1,
        results: list[FieldPipelineResult],
        write_out: dict[str, Any],
    ) -> None:
        map_id = str(uuid.uuid4())
        raw = json.dumps(field_map.to_dict(), ensure_ascii=False)
        summary = field_map.summary
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO machine_field_maps
                   (id, run_id, version, template_file, activity_code, field_count,
                    auto_fillable_field_count, low_confidence_field_count, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    map_id,
                    run_id,
                    field_map.version,
                    field_map.template_file,
                    form_id,
                    summary.detected_field_count,
                    summary.auto_fillable_field_count,
                    summary.low_confidence_field_count,
                    raw,
                ),
            )
            for req in field_map.fields:
                loc = req.form_location
                conn.execute(
                    """INSERT INTO audit_requirements
                       (id, run_id, field_label, field_type, table_index, row_index, column_index,
                        mapped_schema_path, mapping_confidence, can_auto_fill, fallback_behavior)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"{run_id}:{req.id}",
                        run_id,
                        req.field_label,
                        req.field_type,
                        loc.table_index,
                        loc.row_index,
                        loc.column_index,
                        req.mapped_schema_path,
                        req.mapping_confidence,
                        1 if req.can_auto_fill else 0,
                        req.fallback_behavior,
                    ),
                )
            out_docx = write_out.get("completed_docx") or ""
            for r in results:
                conn.execute(
                    """INSERT INTO synthesized_answers
                       (id, run_id, requirement_id, answer_text, confidence, automation_status, fallback_applied)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        run_id,
                        r.requirement.id,
                        r.answer.text,
                        r.answer.confidence,
                        r.answer.automation_status,
                        1 if r.answer.fallback_applied else 0,
                    ),
                )
                patched = r.requirement.id in (write_out.get("write_report") or {}).get("patched_fields", [])
                if not patched:
                    wr = write_out.get("write_report") or {}
                    patched_ids = {f["field_id"] for f in wr.get("fields", []) if f.get("write_status") == "written"}
                    patched = r.requirement.id in patched_ids
                conn.execute(
                    """INSERT INTO form_writes (id, run_id, requirement_id, output_file, write_status)
                       VALUES (?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        run_id,
                        r.requirement.id,
                        out_docx,
                        "written" if patched else "skipped",
                    ),
                )
