"""Reports orchestration (mirrors tms-2 ADR-069).

Sync execution: insert pending run → compose → render per format → upload
artefacts to MinIO → mark completed. Definitions are code-defined in
app/reports/<code>/ and seeded into m_report_definition from REPORT_REGISTRY.
"""
import json
import time
import uuid
from datetime import datetime

from flask import g

from app.con_sqlalchemy import ReportRun, ReportRunStatus, ReportDefinition, bangkok_now
from app.ma_sqlalchemy import (
    ReportRunSchema, ReportRunDetailSchema, ReportDefinitionSchema,
)
from app.repositories import report_repository
from app.reports import REPORT_REGISTRY
from app.reports._helpers import render_csv_rows
from app.services import storage_service
from app.app import db
from app.exception import (
    NotFoundError, ValidationError, MissingFieldsError,
)

# Inline JSON in result_json when payload is smaller than this; else upload as a file.
INLINE_JSON_SIZE_LIMIT = 256 * 1024

# Every report supports these out of the box (csv rendered centrally from rows).
DEFAULT_SUPPORTED_FORMATS = ["json", "xlsx", "csv"]


# ---------------------------------------------------------------------------
# Definition catalogue (seeded from the code registry)
# ---------------------------------------------------------------------------

def sync_definitions():
    """Upsert m_report_definition rows from REPORT_REGISTRY. Idempotent."""
    for code, mod in REPORT_REGISTRY.items():
        row = report_repository.get_definition_by_code(code)
        name = getattr(mod, "NAME", code)
        description = getattr(mod, "DESCRIPTION", "")
        category = getattr(mod, "CATEGORY", "OTHER")
        params_schema = getattr(mod, "PARAMS_SCHEMA", {})
        formats = getattr(mod, "SUPPORTED_FORMATS", DEFAULT_SUPPORTED_FORMATS)
        if row is None:
            row = ReportDefinition(code=code)
            db.session.add(row)
        row.name = name
        row.description = description
        row.category = category
        row.params_schema_json = params_schema
        row.supported_formats = formats
        if row.definition_version is None:
            row.definition_version = 1
    db.session.commit()


def list_definitions():
    defs = report_repository.get_all_definitions()
    if not defs:
        # Lazy first-run seed so a fresh DB still serves the gallery.
        sync_definitions()
        defs = report_repository.get_all_definitions()
    return ReportDefinitionSchema(many=True).dump(defs)


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

def get_run(run_id):
    run = report_repository.get_run_by_id(run_id)
    if not run:
        raise NotFoundError(f"Report run {run_id} not found")
    data = ReportRunDetailSchema().dump(run)
    data["file_urls"] = _build_file_urls(run.file_object_keys)
    return data


def list_runs(data):
    page = data.get("page", 1)
    per_page = data.get("per_page", 20)
    result = report_repository.list_runs(
        page=page, per_page=per_page,
        code=data.get("code"),
        requested_by=data.get("requested_by"),
        status=data.get("status"),
    )
    return {
        "items": ReportRunSchema(many=True).dump(result["items"]),
        "total_pages": result["total_pages"],
        "total": result["total"],
    }


def _get_definition_and_module(code):
    if not code:
        raise MissingFieldsError("code is required")
    definition = report_repository.get_definition_by_code(code)
    if not definition:
        # Definition may simply not be seeded yet on a fresh DB.
        sync_definitions()
        definition = report_repository.get_definition_by_code(code)
    if not definition:
        raise NotFoundError(f"Report definition '{code}' not found")
    if code not in REPORT_REGISTRY:
        raise NotFoundError(f"Report code '{code}' has no compose module registered")
    return definition, REPORT_REGISTRY[code]


def preview_run(code, params, page=None, per_page=None):
    """Lightweight execution: validate, compose, render JSON. No DB row, no MinIO.
    Used by the interactive Report View page. `page`/`per_page` slice the row list
    for on-screen tables; extra top-level keys (breakdown/gantt/...) pass through whole."""
    definition, definition_module = _get_definition_and_module(code)
    validated_params = _validate_params(definition.params_schema_json, params or {})
    data = definition_module.compose(validated_params)
    rendered = definition_module.render(data, 'json')
    if not isinstance(rendered, dict):
        return {'meta': {}, 'rows': []}

    # render_json_default only emits {meta, rows}; surface compose pass-through
    # keys (breakdown, gantt, employee_totals, ...) computed over the FULL row
    # set so the FE charts get complete data, not just the current page.
    for k, v in data.items():
        if k not in ('summary', 'rows') and k not in rendered:
            rendered[k] = v

    if per_page:
        page = page or 1
        all_rows = rendered.get('rows', []) or []
        total = len(all_rows)
        start = (page - 1) * per_page
        end = start + per_page
        rendered = {
            **rendered,
            'rows': all_rows[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 1,
            },
        }
    return rendered


def create_run(code, params, formats):
    """Full execution: persist a run, render each format, upload artefacts to MinIO."""
    if not isinstance(formats, list) or not formats:
        raise ValidationError("formats must be a non-empty list")
    definition, definition_module = _get_definition_and_module(code)

    supported = definition.supported_formats or DEFAULT_SUPPORTED_FORMATS
    unsupported = [f for f in formats if f not in supported]
    if unsupported:
        raise ValidationError(f"Unsupported formats for {code}: {unsupported}")

    validated_params = _validate_params(definition.params_schema_json, params or {})

    run_id = str(uuid.uuid4())
    run = ReportRun(
        run_id=run_id,
        definition_code=code,
        definition_version=definition.definition_version,
        params_json=validated_params,
        requested_by=getattr(g, 'username', 'unknown'),
        requested_at=bangkok_now(),
        status=ReportRunStatus.PENDING,
    )
    db.session.add(run)
    db.session.commit()

    started = time.monotonic()
    try:
        run.status = ReportRunStatus.RUNNING
        db.session.commit()

        data = definition_module.compose(validated_params)
        if not isinstance(data, dict):
            raise ValidationError("compose() must return a dict")

        file_object_keys = {}
        total_size = 0
        result_json = None

        for fmt in formats:
            if fmt == 'json':
                rendered = definition_module.render(data, 'json')
                payload = json.dumps(rendered, default=str)
                if len(payload) <= INLINE_JSON_SIZE_LIMIT:
                    result_json = rendered
                else:
                    object_key = _build_object_key(code, run_id, 'json')
                    storage_service.upload_object(payload.encode('utf-8'), object_key, 'application/json')
                    file_object_keys['json'] = object_key
                    total_size += len(payload)
            elif fmt == 'xlsx':
                rendered = definition_module.render(data, 'xlsx')
                object_key = _build_object_key(code, run_id, 'xlsx')
                storage_service.upload_object(
                    rendered, object_key,
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                file_object_keys['xlsx'] = object_key
                total_size += len(rendered)
            elif fmt == 'csv':
                rendered = render_csv_rows(data.get('rows') or [])
                object_key = _build_object_key(code, run_id, 'csv')
                storage_service.upload_object(rendered, object_key, 'text/csv')
                file_object_keys['csv'] = object_key
                total_size += len(rendered)
            else:
                raise ValidationError(f"Unknown format: {fmt}")

        rows_list = data.get('rows') if isinstance(data.get('rows'), list) else None
        row_count = len(rows_list) if rows_list is not None else None

        run.status = ReportRunStatus.COMPLETED
        run.completed_at = bangkok_now()
        run.file_object_keys = file_object_keys or None
        run.file_size_bytes = total_size or None
        run.result_json = result_json
        run.row_count = row_count
        run.runtime_ms = int((time.monotonic() - started) * 1000)
        db.session.commit()

        out = ReportRunDetailSchema().dump(run)
        out["file_urls"] = _build_file_urls(run.file_object_keys)
        return out

    except Exception as e:
        db.session.rollback()
        failed_run = report_repository.get_run_by_id(run_id)
        if failed_run:
            failed_run.status = ReportRunStatus.FAILED
            failed_run.error_message = str(e)
            failed_run.completed_at = bangkok_now()
            failed_run.runtime_ms = int((time.monotonic() - started) * 1000)
            db.session.commit()
        raise


def _build_object_key(code, run_id, ext):
    now = datetime.utcnow()
    return f"reports/{code}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{run_id}.{ext}"


def _build_file_urls(file_object_keys):
    if not file_object_keys:
        return None
    return {fmt: storage_service.get_presigned_url(key)
            for fmt, key in file_object_keys.items()}


def _validate_params(schema, params):
    """Minimal validation: enforce required params + drop unknown keys.
    Compose function is responsible for type coercion and semantic checks."""
    if not isinstance(schema, dict):
        return dict(params)
    declared = schema.get('params', {}) or {}
    if not declared:
        return dict(params)
    required = [k for k, spec in declared.items() if spec.get('required')]
    missing = [k for k in required if params.get(k) in (None, '', [])]
    if missing:
        raise MissingFieldsError(f"Missing required params: {missing}")
    return {k: v for k, v in params.items() if k in declared}
