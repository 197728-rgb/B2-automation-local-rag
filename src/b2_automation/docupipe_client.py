"""DocuPipe client with explicit stub mode and configurable live HTTP mode.

The live DocuPipe API shape can vary by account/workspace, so endpoint paths are
configuration-driven. The client refuses silent fixture fallback in live mode.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import requests


class DocuPipeConfigError(RuntimeError):
    """Raised when required DocuPipe configuration is missing."""


class DocuPipeRuntimeError(RuntimeError):
    """Raised when DocuPipe returns an invalid or failed response."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise DocuPipeConfigError(f"Missing required environment variable: {name}")
    return value


def is_stub_mode() -> bool:
    # Production-safe default: live mode unless the caller explicitly enables the fixture stub.
    return os.getenv("B2_DOCUPIPE_STUB", "0") == "1"


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _json_or_raise(resp: requests.Response, context: str, *, job_id: str | None = None) -> dict[str, Any]:
    label = f"{context} job_id={job_id}" if job_id else context
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise DocuPipeRuntimeError(f"DocuPipe {label} failed: HTTP {resp.status_code}: {resp.text[:500]}") from exc
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise DocuPipeRuntimeError(f"DocuPipe {label} returned non-JSON response: {resp.text[:500]}") from exc
    if not isinstance(data, dict):
        raise DocuPipeRuntimeError(f"DocuPipe {label} returned unsupported JSON type: {type(data)!r}")
    return data


def _first_present(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _request_with_retry(call: Callable[[], requests.Response], *, context: str, job_id: str | None = None) -> requests.Response:
    delays = (0.0, 2.0, 4.0)
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            resp = call()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == len(delays):
                raise DocuPipeRuntimeError(f"DocuPipe {context} job_id={job_id or 'n/a'} request failed after retries: {exc}") from exc
            continue
        if resp.status_code in {429} or 500 <= resp.status_code <= 599:
            if attempt == len(delays):
                return resp
            continue
        return resp
    raise DocuPipeRuntimeError(f"DocuPipe {context} job_id={job_id or 'n/a'} request failed after retries: {last_exc}")


class DocuPipeClient:
    """Small HTTP client for upload → run → poll → result workflows."""

    def __init__(self) -> None:
        self.api_key = _require_env("DOCUPIPE_API_KEY")
        self.base_url = _require_env("DOCUPIPE_API_URL")
        self.schema_id = _require_env("DOCUPIPE_SCHEMA_ID")
        self.timeout = float(os.getenv("DOCUPIPE_HTTP_TIMEOUT", "60"))
        self.poll_interval = float(os.getenv("DOCUPIPE_POLL_INTERVAL", "5"))
        self.poll_timeout = float(os.getenv("DOCUPIPE_POLL_TIMEOUT", "900"))
        self.upload_path = os.getenv("DOCUPIPE_UPLOAD_PATH", "/documents")
        self.run_path = os.getenv("DOCUPIPE_RUN_PATH", "/extractions")
        self.status_path_template = os.getenv("DOCUPIPE_STATUS_PATH_TEMPLATE", "/extractions/{job_id}")
        self.result_path_template = os.getenv("DOCUPIPE_RESULT_PATH_TEMPLATE", "/extractions/{job_id}/result")

    def upload_pdf(self, pdf_path: Path) -> dict[str, Any]:
        def _call() -> requests.Response:
            with pdf_path.open("rb") as f:
                files = {"file": (pdf_path.name, f, "application/pdf")}
                return requests.post(
                    _url(self.base_url, self.upload_path),
                    headers=_headers(self.api_key),
                    files=files,
                    timeout=self.timeout,
                )

        resp = _request_with_retry(_call, context="upload")
        return _json_or_raise(resp, "upload")

    def start_extraction(self, uploaded: dict[str, Any]) -> str:
        document_id = _first_present(uploaded, ("document_id", "id", "file_id", "documentId"))
        payload: dict[str, Any] = {"schema_id": self.schema_id}
        if document_id:
            payload["document_id"] = document_id

        def _call() -> requests.Response:
            return requests.post(
                _url(self.base_url, self.run_path),
                headers={**_headers(self.api_key), "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )

        resp = _request_with_retry(_call, context="start extraction")
        data = _json_or_raise(resp, "start extraction")
        job_id = _first_present(data, ("job_id", "id", "extraction_id", "run_id"))
        if not job_id:
            raise DocuPipeRuntimeError(f"DocuPipe start extraction response did not include a job id: {data}")
        return str(job_id)

    def poll_until_complete(self, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.poll_timeout
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            path = self.status_path_template.format(job_id=job_id)

            def _call() -> requests.Response:
                return requests.get(_url(self.base_url, path), headers=_headers(self.api_key), timeout=self.timeout)

            resp = _request_with_retry(_call, context="poll status", job_id=job_id)
            data = _json_or_raise(resp, "poll status", job_id=job_id)
            last = data
            status = str(_first_present(data, ("status", "state")) or "").lower()
            if status in {"completed", "complete", "succeeded", "success", "done"}:
                return data
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise DocuPipeRuntimeError(f"DocuPipe job {job_id} failed: {data}")
            time.sleep(self.poll_interval)
        raise DocuPipeRuntimeError(f"DocuPipe job {job_id} timed out after {self.poll_timeout}s. Last status: {last}")

    def fetch_result(self, job_id: str) -> dict[str, Any]:
        path = self.result_path_template.format(job_id=job_id)

        def _call() -> requests.Response:
            return requests.get(_url(self.base_url, path), headers=_headers(self.api_key), timeout=self.timeout)

        resp = _request_with_retry(_call, context="fetch result", job_id=job_id)
        return _json_or_raise(resp, "fetch result", job_id=job_id)

    def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
        uploaded = self.upload_pdf(pdf_path)
        job_id = self.start_extraction(uploaded)
        completed = self.poll_until_complete(job_id)
        inline_result = completed.get("result")
        if isinstance(inline_result, dict):
            result = completed
        else:
            result = self.fetch_result(job_id)
        result.setdefault("_docupipe_job_id", job_id)
        return result


def process_pdf(pdf_path: Path) -> dict[str, Any]:
    """Process a PDF through DocuPipe or explicit fixture-backed stub mode."""

    pdf_path = Path(pdf_path)
    if is_stub_mode():
        fixture = os.getenv("B2_DOCUPIPE_FIXTURE")
        if not fixture:
            raise DocuPipeConfigError("Stub mode requires B2_DOCUPIPE_FIXTURE pointing to a JSON file")
        fixture_path = Path(fixture)
        if not fixture_path.is_file():
            raise DocuPipeConfigError(f"B2_DOCUPIPE_FIXTURE does not exist: {fixture_path}")
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        data.setdefault("_stub_source_pdf", pdf_path.name)
        return data

    return DocuPipeClient().process_pdf(pdf_path)
