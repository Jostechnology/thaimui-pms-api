"""Item-code decoding + legend/reference import.

Decodable categories (a sheet whose name matches a declared schema, e.g. SLING,
CHAIN) parse a structured item code into detail fields via positional segment
slicing; every other category falls through to a flat Item No. -> description
reference lookup. Best-effort: bad or short codes never raise — they yield
source 'none' with whatever partial fields matched.

Positions are NOT hardcoded. On import each field's 1-indexed position range is
read from the segment-column header (e.g. "1-2", "10-12", bare "9") that precedes
its decode column, and stored in ItemDecodeSegment.segment. Decoding derives the
distinct (segment, field) pairs for a category straight from the stored rows.
"""
import re
from collections import defaultdict, OrderedDict
from io import BytesIO

import openpyxl

from app.app import db
from app.exception import ValidationError
from app.repositories import item_decode_repository


# Code declares only WHICH sheets are decodable (case-insensitive; the category
# stored/looked-up is the sheet name upper-cased) and a small header->schema-key
# alias map. Everything about positions comes from the sheet headers.
DECODABLE_CATEGORIES = {'SLING', 'CHAIN'}
REFERENCE_SHEET_NAME = 'REFERENCE'

# Default schema key for a decode column = its header normalized (whitespace
# collapsed, lower-cased). Only the exceptions below need an explicit alias.
# Field keys MUST equal the FE schema keys in TemplateSectionForm.tsx.
FIELD_ALIASES = {
    'construction and strand': 'structure',
    'unit': 'grade_unit',
}

# Reverse of FIELD_ALIASES: schema field key -> the sheet header it came from.
# Used by the export to rebuild original headers. Any field not listed here is
# Title-cased (type -> "Type", manufacturer -> "Manufacturer").
REVERSE_FIELD_HEADERS = {
    'structure': 'Construction and Strand',
    'grade_unit': 'Unit',
}

REFERENCE_SHEET_TITLE = 'Reference'
REFERENCE_HEADERS = ('Item No.', 'Item Description')
EXPORT_FILENAME = 'ThaiMui - Item Description.xlsx'
XLSX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

_RANGE_LIKE_RE = re.compile(r'^\d[\d\s\-]*$')
_RANGE_RE = re.compile(r'^(\d+)(?:\s*-\s*(\d+))?$')


# --------------------------------------------------------------------------- #
# Range helpers
# --------------------------------------------------------------------------- #
def _looks_like_range(text):
    """True when a header cell is a position/segment token rather than a field
    name (starts with a digit; only digits, spaces and dashes)."""
    return bool(_RANGE_LIKE_RE.match(text or ''))


def _parse_range(segment):
    """'a-b' (1-indexed inclusive) or bare 'n' -> (start, end). Raises
    ValueError on an unparseable or inverted token."""
    m = _RANGE_RE.match((segment or '').strip())
    if not m:
        raise ValueError(f"unparseable range token '{segment}'")
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) is not None else start
    if start < 1 or end < start:
        raise ValueError(f"unparseable range token '{segment}'")
    return start, end


def _canon_segment(segment):
    """Canonical stored form: 'a-b' when a != b, else bare 'n'."""
    start, end = _parse_range(segment)
    return f"{start}-{end}" if end != start else f"{start}"


def _slice(code, segment):
    """Slice a 1-indexed inclusive range out of code. Returns '' when the code
    is too short for the range (partial decode allowed — never raises)."""
    try:
        start, end = _parse_range(segment)
    except ValueError:
        return ''
    if len(code) < end:
        return ''
    return code[start - 1:end]


def _alias(header):
    """Decode-column header -> schema field key (default = normalized header)."""
    key = ' '.join((header or '').split()).lower()
    return FIELD_ALIASES.get(key, key)


# --------------------------------------------------------------------------- #
# Decoding
# --------------------------------------------------------------------------- #
def _normalize(item_code):
    """item code -> canonical (ideally 12-char) code. A 'B' sitting at boundary
    slot 5 acts as a separator and is dropped (generalized to any code >= 5
    chars). Never raises."""
    c = (item_code or '').upper().replace('-', '')
    if len(c) >= 5 and c[4] == 'B':
        c = c[:4] + c[5:]
    return c


def _strip_mm(value):
    """Strip a trailing ' mm'/'mm' so the FE can keep its own 'mm' postfix
    without doubling. '9.5 mm' -> '9.5'."""
    if not isinstance(value, str):
        return value
    v = value.strip()
    if v.lower().endswith('mm'):
        v = v[:-2].strip()
    return v


def _decode_one(item_code, item_group, seg_fields):
    """seg_fields: distinct (segment, field) pairs for this category, from the
    stored legend. Empty => not a decodable category -> reference lookup."""
    if seg_fields:
        code = _normalize(item_code)
        by_segment = defaultdict(set)
        for segment, field in seg_fields:
            by_segment[segment].add(field)

        fields = {}
        for segment, field_keys in by_segment.items():
            seg_code = _slice(code, segment)
            if not seg_code:
                continue
            rows = item_decode_repository.get_segment_values(item_group, segment, seg_code)
            value_by_field = {r.field: r.value for r in rows}
            for field_key in field_keys:
                if field_key in value_by_field:
                    val = value_by_field[field_key]
                    if field_key == 'size':
                        val = _strip_mm(val)
                    fields[field_key] = val
        if fields:
            return {'source': 'decode', 'fields': fields}
        return {'source': 'none', 'fields': {}}

    # Non-decodable category -> exact reference lookup on the raw code.
    ref = item_decode_repository.get_reference(item_code)
    if ref is not None:
        return {'source': 'reference', 'fields': {'description': ref.item_description}}
    return {'source': 'none', 'fields': {}}


def decode_items(items):
    """items: list[{item_code, item_group}] -> {item_code: {source, fields}}.
    Derives segment/field pairs per category from stored data. Best-effort,
    never raises on bad codes."""
    items = items or []

    # Fetch each distinct category's (segment, field) pairs once.
    seg_fields_by_group = {}
    for item in items:
        group = (item.get('item_group') or '').upper()
        if group and group not in seg_fields_by_group:
            seg_fields_by_group[group] = item_decode_repository.get_category_segments(group)

    results = {}
    for item in items:
        item_code = item.get('item_code')
        if item_code is None or item_code in results:
            continue
        group = (item.get('item_group') or '').upper()
        results[item_code] = _decode_one(item_code, group, seg_fields_by_group.get(group) or [])
    return results


# --------------------------------------------------------------------------- #
# Import (replace-on-upload) + validation report
# --------------------------------------------------------------------------- #
def _cell_text(value):
    if value is None:
        return ''
    return str(value).strip()


def _analyze_segment_sheet(worksheet, category):
    """Parse one legend sheet generically: positions come from the header row.

    Returns (rows, blocked, warnings, reserved):
      - rows     : dedup'd list of {category,segment,code,field,value} to insert.
      - blocked  : structural breaks / overlap that must REJECT the whole import.
      - warnings : non-blocking issues (skipped columns, empty fields).
      - reserved : INFO on declared ranges that emit no field (pending/manual).
    """
    header_row = None
    data_rows = []
    for i, row in enumerate(worksheet.iter_rows(min_row=1, values_only=True)):
        if i == 0:
            header_row = row
        else:
            data_rows.append(row)
    if header_row is None:
        return [], [f"{category}: sheet has no header row"], [], []

    blocked, warnings, reserved = [], [], []

    # --- Walk the header row into segment blocks. A segment header "owns" every
    #     following column up to the next segment header. ------------------- #
    segments = []
    current = None
    for col_idx, cell in enumerate(header_row):
        text = _cell_text(cell)
        if not text:
            if current is not None:
                current['decode_cols'].append((col_idx, ''))  # headerless column
            continue
        if _looks_like_range(text):
            try:
                rng = _parse_range(text)
            except ValueError:
                blocked.append(f"{category}: unparseable range token '{text}'")
                current = None
                continue
            current = {
                'segment': _canon_segment(text),
                'range': rng,
                'code_col': col_idx,
                'decode_cols': [],
            }
            segments.append(current)
        else:
            if current is None:
                blocked.append(
                    f"{category}: decode column '{text}' has no preceding range header")
                continue
            current['decode_cols'].append((col_idx, text))

    # --- Resolve decode columns into named fields / headerless columns. ----- #
    for seg in segments:
        seg['field_cols'] = []       # (col_idx, field_key, header)
        seg['headerless_cols'] = []  # col_idx (no field name)
        for col_idx, htext in seg['decode_cols']:
            if htext:
                seg['field_cols'].append((col_idx, _alias(htext), htext))
            else:
                seg['headerless_cols'].append(col_idx)

    # --- Read data, emitting value rows and counting values per field. ------ #
    rows = []
    seen = set()  # (segment, code, field) dedupe -> unique constraint safety
    field_value_counts = defaultdict(int)      # (seg_index, field_key) -> n
    headerless_value_counts = defaultdict(int)  # (seg_index, col_idx) -> n
    for drow in data_rows:
        for si, seg in enumerate(segments):
            code_col = seg['code_col']
            code = _cell_text(drow[code_col]) if code_col < len(drow) else ''
            if not code:
                continue
            for col_idx, field_key, _htext in seg['field_cols']:
                value = _cell_text(drow[col_idx]) if col_idx < len(drow) else ''
                if not value:
                    continue
                field_value_counts[(si, field_key)] += 1
                key = (seg['segment'], code, field_key)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    'category': category,
                    'segment': seg['segment'],
                    'code': code,
                    'field': field_key,
                    'value': value,
                })
            for col_idx in seg['headerless_cols']:
                value = _cell_text(drow[col_idx]) if col_idx < len(drow) else ''
                if value:
                    headerless_value_counts[(si, col_idx)] += 1

    # --- Classify each segment: reserved / live, collect warnings. ---------- #
    value_emitting = []  # {segment, range, positions, fields}
    for si, seg in enumerate(segments):
        for col_idx in seg['headerless_cols']:
            if headerless_value_counts[(si, col_idx)] > 0:
                warnings.append(
                    f"{category} range {seg['segment']}: unnamed column {col_idx + 1} "
                    f"has values but no field header; skipped")

        field_counts = {fk: field_value_counts[(si, fk)] for _c, fk, _h in seg['field_cols']}
        total_values = sum(field_counts.values())

        if total_values == 0:
            # No decode column at all, or decode column(s) with zero values:
            # a reserved / undefined / manual-only slot. INFO, never blocks.
            reserved.append(
                f"{category} range {seg['segment']}: no mapping (reserved/manual)")
            continue

        # Live segment: any headed field that loaded zero values is a WARN
        # (distinct from a reserved slot, which emits nothing at all).
        for fk, cnt in field_counts.items():
            if cnt == 0:
                warnings.append(
                    f"{category} field '{fk}' (range {seg['segment']}) has a decode "
                    f"column but zero values loaded")

        vfields = sorted(fk for fk, cnt in field_counts.items() if cnt > 0)
        positions = set(range(seg['range'][0] - 1, seg['range'][1]))
        value_emitting.append({
            'segment': seg['segment'],
            'positions': positions,
            'fields': vfields,
        })

    # --- Overlap check (BLOCK) between distinct value-emitting segments. ----
    #     Multiple fields under one segment (core+spiral, grade+grade_unit)
    #     share positions legitimately and are NOT compared against each other.
    for a in range(len(value_emitting)):
        for b in range(a + 1, len(value_emitting)):
            sa, sb = value_emitting[a], value_emitting[b]
            overlap = sorted(p + 1 for p in (sa['positions'] & sb['positions']))
            if overlap:
                blocked.append(
                    f"{category}: fields {sa['fields']} (range {sa['segment']}) and "
                    f"{sb['fields']} (range {sb['segment']}) overlap at position(s) "
                    f"{overlap}")

    return rows, blocked, warnings, reserved


def _parse_reference_sheet(worksheet):
    # Dedupe on item_no (PK) — last occurrence wins.
    by_item_no = {}
    for excel_row in worksheet.iter_rows(min_row=2, values_only=True):
        item_no = _cell_text(excel_row[0]) if len(excel_row) > 0 else ''
        if not item_no:
            continue
        description = _cell_text(excel_row[1]) if len(excel_row) > 1 else ''
        by_item_no[item_no] = {'item_no': item_no, 'item_description': description}
    return list(by_item_no.values())


def _ordered_categories():
    """Decodable categories in a stable display order: SLING then CHAIN first,
    then any other declared category alphabetically. Drives both the overview and
    export so their category/sheet ordering is deterministic."""
    preferred = ['SLING', 'CHAIN']
    ordered = [c for c in preferred if c in DECODABLE_CATEGORIES]
    ordered += sorted(c for c in DECODABLE_CATEGORIES if c not in preferred)
    return ordered


def _group_legend_by_field(rows):
    """Group ordered legend rows [(segment, field, code, value), ...] into an
    OrderedDict keyed by (field, segment) -> [(code, value), ...]. Insertion
    order follows the repository's (segment, field, code) ordering, so fields
    come out grouped by segment then field, values by code."""
    by_field = OrderedDict()
    for segment, field, code, value in rows:
        by_field.setdefault((field, segment), []).append((code, value))
    return by_field


def _field_header(field_key):
    """Reverse-map a schema field key to its original sheet header for export."""
    return REVERSE_FIELD_HEADERS.get(field_key, field_key.title())


def get_item_decode_overview():
    """Overview of every decodable category: its (field, segment) pairs with the
    full code->value legend per field, plus row counts. reference_count is the
    ItemReference row total. Same source the decoder derives its pairs from."""
    categories = []
    for category in _ordered_categories():
        rows = item_decode_repository.get_category_legend_rows(category)
        fields = [
            {
                'field': field,
                'segment': segment,
                'values': [{'code': code, 'value': value} for code, value in pairs],
            }
            for (field, segment), pairs in _group_legend_by_field(rows).items()
        ]
        categories.append({
            'category': category,
            'value_count': item_decode_repository.count_category_rows(category),
            'fields': fields,
        })
    return {
        'categories': categories,
        'reference_count': item_decode_repository.count_reference(),
    }


def get_item_reference_list(data):
    """Paginated ItemReference list. `search` (case-insensitive) matches item_no
    OR item_description. Returns dict with data/total/page/pages."""
    data = data or {}
    page = data.get('page', 1)
    per_page = data.get('per_page', 25)
    search = data.get('search')
    result = item_decode_repository.get_reference_list(page, per_page, search)
    return {
        'data': [
            {'item_no': r.item_no, 'item_description': r.item_description}
            for r in result.items
        ],
        'total': result.total,
        'page': result.page,
        'pages': result.pages,
    }


def export_workbook():
    """Rebuild the legend/reference workbook as .xlsx bytes. One legend sheet per
    decodable category (a column PAIR [segment-range, field header] per field,
    independent-length code/value lists) plus a flat Reference sheet."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)  # drop the default empty sheet
    try:
        for category in _ordered_categories():
            worksheet = workbook.create_sheet(title=category.title())
            rows = item_decode_repository.get_category_legend_rows(category)
            by_field = _group_legend_by_field(rows)
            for pair_idx, ((field, segment), pairs) in enumerate(by_field.items()):
                seg_col = pair_idx * 2 + 1
                field_col = seg_col + 1
                worksheet.cell(row=1, column=seg_col, value=segment)
                worksheet.cell(row=1, column=field_col, value=_field_header(field))
                for offset, (code, value) in enumerate(pairs):
                    worksheet.cell(row=2 + offset, column=seg_col, value=code)
                    worksheet.cell(row=2 + offset, column=field_col, value=value)

        reference_ws = workbook.create_sheet(title=REFERENCE_SHEET_TITLE)
        reference_ws.cell(row=1, column=1, value=REFERENCE_HEADERS[0])
        reference_ws.cell(row=1, column=2, value=REFERENCE_HEADERS[1])
        for offset, ref in enumerate(item_decode_repository.get_all_reference_rows()):
            reference_ws.cell(row=2 + offset, column=1, value=ref.item_no)
            reference_ws.cell(row=2 + offset, column=2, value=ref.item_description)

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()
    finally:
        workbook.close()


def import_workbook(file_storage):
    """Load the legend/reference workbook, validate it, and (if clean) replace
    all decode data in one transaction.

    Returns a validation report:
      { ok, blocked[], warnings[], reserved[], loaded_counts{} }
    A blocked report writes NOTHING (ok:false). Only true I/O / parse failures
    raise ValidationError; validation failures are reported with ok:false so the
    FE can render the full report."""
    try:
        workbook = openpyxl.load_workbook(file_storage, read_only=True, data_only=True)
    except Exception as e:
        raise ValidationError(f"Could not read workbook: {e}")

    report = {'ok': True, 'blocked': [], 'warnings': [], 'reserved': [], 'loaded_counts': {}}
    category_rows = {}
    ref_rows = None

    try:
        for sheet_name in workbook.sheetnames:
            upper = sheet_name.strip().upper()
            if upper == REFERENCE_SHEET_NAME:
                ref_rows = _parse_reference_sheet(workbook[sheet_name])
                continue
            if upper in DECODABLE_CATEGORIES:
                rows, blocked, warnings, reserved = _analyze_segment_sheet(
                    workbook[sheet_name], upper)
                report['blocked'].extend(blocked)
                report['warnings'].extend(warnings)
                report['reserved'].extend(reserved)
                category_rows[upper] = rows
            else:
                report['warnings'].append(
                    f"sheet '{sheet_name}': no matching decodable schema; skipped")

        if report['blocked']:
            # Reject the whole import — nothing has been written to the session.
            report['ok'] = False
            return report

        for category, rows in category_rows.items():
            report['loaded_counts'][category] = \
                item_decode_repository.replace_category_segments(category, rows)
        if ref_rows is not None:
            report['loaded_counts']['reference'] = \
                item_decode_repository.replace_all_reference(ref_rows)

        db.session.commit()
    except ValidationError:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise ValidationError(f"Failed to import workbook: {e}")
    finally:
        workbook.close()

    return report
