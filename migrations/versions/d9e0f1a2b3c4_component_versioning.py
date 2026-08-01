"""Component document versioning + WorkRun pins + Sales/Production edit approval.

Before this, ItemComponent.doc_version was a bare counter and every save
overwrote the same generated document — an old version could not be
reconstructed, and nothing recorded which document a WorkRun was actually
built against. Sales could also silently rewrite a component after production
had started.

Adds:
  t_item_component_version  — immutable content snapshot per save
  t_work_run_component_pin  — append-only as-built record per WorkRun
  t_component_edit_request  — Sales asks, Production approves, single-use

Backfill: one v1 snapshot per existing ItemComponent built from its live rows,
then a pin on every already-started WorkRun. Historical runs get a pin they
never truly had — the true as-built is unknowable — but that beats a null.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-08-01
"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'd9e0f1a2b3c4'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


EDIT_REQUEST_STATUS = sa.Enum(
    'PENDING', 'APPROVED', 'REJECTED', 'CONSUMED', 'CANCELLED',
    name='componenteditrequeststatus',
)


def upgrade():
    op.create_table(
        't_component_edit_request',
        sa.Column('edit_request_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_component_id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False),
        sa.Column('base_version_no', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('status', EDIT_REQUEST_STATUS, nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', sa.String(length=80), nullable=True),
        sa.Column('reviewed_date', sa.DateTime(), nullable=True),
        sa.Column('review_remark', sa.String(length=500), nullable=True),
        sa.Column('consumed_version_id', sa.Integer(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_component_id'], ['t_item_component.item_component_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['t_work_order.work_order_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
    )
    op.create_index('ix_component_edit_request_component', 't_component_edit_request', ['item_component_id'])
    op.create_index('ix_component_edit_request_work_order', 't_component_edit_request', ['work_order_id'])
    op.create_index('ix_component_edit_request_status', 't_component_edit_request', ['status'])
    op.create_index('ix_component_edit_request_branch', 't_component_edit_request', ['branch_id'])

    op.create_table(
        't_item_component_version',
        sa.Column('version_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_component_id', sa.Integer(), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('component_name', sa.String(length=255), nullable=False),
        sa.Column('remark', sa.String(length=255), nullable=True),
        sa.Column('img_url', sa.String(length=500), nullable=True),
        sa.Column('component_template_id', sa.Integer(), nullable=True),
        sa.Column('template_name', sa.String(length=255), nullable=True),
        sa.Column('sections_snapshot', sa.JSON(), nullable=False),
        sa.Column('section_data_snapshot', sa.JSON(), nullable=False),
        sa.Column('material_usage_snapshot', sa.JSON(), nullable=False),
        sa.Column('doc_ref_no', sa.String(length=120), nullable=True),
        sa.Column('doc_path', sa.String(length=500), nullable=True),
        sa.Column('change_reason', sa.String(length=500), nullable=True),
        sa.Column('edit_request_id', sa.Integer(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_component_id'], ['t_item_component.item_component_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['component_template_id'], ['m_component_template.component_template_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.UniqueConstraint('item_component_id', 'version_no', name='uq_item_component_version_no'),
    )
    op.create_index('ix_item_component_version_component', 't_item_component_version', ['item_component_id'])
    op.create_index('ix_item_component_version_branch', 't_item_component_version', ['branch_id'])

    # Circular pair: version -> edit_request and edit_request -> version. Both
    # tables must exist before either FK can be added.
    op.create_foreign_key(
        'fk_component_version_edit_request',
        't_item_component_version', 't_component_edit_request',
        ['edit_request_id'], ['edit_request_id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_edit_request_consumed_version',
        't_component_edit_request', 't_item_component_version',
        ['consumed_version_id'], ['version_id'], ondelete='SET NULL',
    )

    op.create_table(
        't_work_run_component_pin',
        sa.Column('pin_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('item_component_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('superseded_date', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_component_id'], ['t_item_component.item_component_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['t_item_component_version.version_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
    )
    op.create_index('ix_work_run_component_pin_run', 't_work_run_component_pin', ['work_run_id'])
    op.create_index('ix_work_run_component_pin_component', 't_work_run_component_pin', ['item_component_id'])
    op.create_index('ix_work_run_component_pin_branch', 't_work_run_component_pin', ['branch_id'])

    _backfill()


VERSION_BACKFILL_REASON = 'Backfill: สถานะเอกสารก่อนเริ่มใช้ระบบเวอร์ชัน'
PIN_BACKFILL_REASON = 'Backfill: ผูกย้อนหลังตอนเริ่มใช้ระบบเวอร์ชัน'


def _json_or_empty(value):
    """JSON columns round-trip as str on some drivers and as parsed objects on
    others. Normalise to a JSON string for the insert."""
    if value is None:
        return '[]'
    if isinstance(value, str):
        return value or '[]'
    return json.dumps(value, ensure_ascii=False)


def _backfill():
    """Built in Python rather than INSERT..SELECT so it does not depend on
    JSON_ARRAYAGG/JSON_OBJECT (MySQL 5.7.22+ only)."""
    conn = op.get_bind()

    components = conn.execute(sa.text("""
        SELECT ic.item_component_id, ic.component_name, ic.remark, ic.img_url,
               ic.component_template_id, ic.branch_id, ic.doc_version,
               ic.created_by, ic.updated_by, ic.created_date, ic.updated_date,
               ct.name AS template_name, ct.sections AS template_sections,
               wo.work_order_code, wo.doc_num
        FROM t_item_component ic
        JOIN t_work_order wo ON wo.work_order_id = ic.work_order_id
        LEFT JOIN m_component_template ct
               ON ct.component_template_id = ic.component_template_id
    """)).mappings().all()

    if not components:
        return

    section_rows = conn.execute(sa.text("""
        SELECT item_component_id, section_key, section_type, data
        FROM m_component_template_section_data
    """)).mappings().all()
    sections_by_component = {}
    for row in section_rows:
        sections_by_component.setdefault(row['item_component_id'], []).append({
            'section_key': row['section_key'],
            'section_type': row['section_type'],
            'data': json.loads(row['data']) if isinstance(row['data'], str) else row['data'],
        })

    usage_rows = conn.execute(sa.text("""
        SELECT cmu.item_component_id, cmu.usage_id, cmu.material_list_id,
               cmu.quantity_used, ml.item_code, ml.item_name, ml.item_group,
               ml.unit_price, ml.item_description
        FROM t_component_material_usage cmu
        LEFT JOIN t_material_list ml ON ml.material_list_id = cmu.material_list_id
    """)).mappings().all()
    usages_by_component = {}
    for row in usage_rows:
        usages_by_component.setdefault(row['item_component_id'], []).append({
            'usage_id': row['usage_id'],
            'material_list_id': row['material_list_id'],
            'quantity_used': row['quantity_used'],
            'item_code': row['item_code'],
            'item_name': row['item_name'],
            'item_group': row['item_group'],
            'unit_price': row['unit_price'],
            'item_description': row['item_description'],
        })

    insert_version = sa.text("""
        INSERT INTO t_item_component_version (
            item_component_id, version_no, component_name, remark, img_url,
            component_template_id, template_name,
            sections_snapshot, section_data_snapshot, material_usage_snapshot,
            doc_ref_no, doc_path, change_reason, branch_id,
            created_by, updated_by, created_date, updated_date
        ) VALUES (
            :item_component_id, 1, :component_name, :remark, :img_url,
            :component_template_id, :template_name,
            :sections_snapshot, :section_data_snapshot, :material_usage_snapshot,
            :doc_ref_no, :doc_path, :change_reason, :branch_id,
            :created_by, :updated_by, :created_date, :updated_date
        )
    """)

    for comp in components:
        cid = comp['item_component_id']
        wo_code = comp['work_order_code'] or comp['doc_num']
        has_doc = comp['component_template_id'] is not None
        # Existing documents live in the legacy shared folder. Only versions
        # written after this migration use the per-version /v{n} layout.
        conn.execute(insert_version, {
            'item_component_id': cid,
            'component_name': comp['component_name'],
            'remark': comp['remark'],
            'img_url': comp['img_url'],
            'component_template_id': comp['component_template_id'],
            'template_name': comp['template_name'],
            'sections_snapshot': _json_or_empty(comp['template_sections']),
            'section_data_snapshot': json.dumps(sections_by_component.get(cid, []), ensure_ascii=False),
            'material_usage_snapshot': json.dumps(usages_by_component.get(cid, []), ensure_ascii=False),
            'doc_ref_no': f"{wo_code}_comp{cid}_v{max(comp['doc_version'] or 1, 1)}" if has_doc else None,
            'doc_path': f"work_orders/{wo_code}/components/{cid}" if has_doc else None,
            'change_reason': VERSION_BACKFILL_REASON,
            'branch_id': comp['branch_id'],
            'created_by': comp['created_by'],
            'updated_by': comp['updated_by'],
            'created_date': comp['created_date'],
            'updated_date': comp['updated_date'],
        })

    # doc_version now means "newest version_no", and every component has exactly
    # one backfilled version.
    conn.execute(sa.text("UPDATE t_item_component SET doc_version = 1"))

    # Pin every already-started run to that v1. branch_id comes from the run,
    # which is BranchScoped and therefore always populated.
    conn.execute(sa.text("""
        INSERT INTO t_work_run_component_pin (
            work_run_id, item_component_id, version_id, version_no,
            reason, branch_id, created_by, updated_by, created_date, updated_date
        )
        SELECT
            wr.work_run_id,
            icv.item_component_id,
            icv.version_id,
            icv.version_no,
            :reason,
            wr.branch_id,
            wr.created_by, wr.updated_by, wr.created_date, wr.updated_date
        FROM t_work_run wr
        JOIN t_item_component ic ON ic.work_order_id = wr.work_order_id
        JOIN t_item_component_version icv
          ON icv.item_component_id = ic.item_component_id
        WHERE wr.start_date IS NOT NULL
    """), {'reason': PIN_BACKFILL_REASON})


def downgrade():
    op.drop_constraint('fk_edit_request_consumed_version', 't_component_edit_request', type_='foreignkey')
    op.drop_constraint('fk_component_version_edit_request', 't_item_component_version', type_='foreignkey')
    op.drop_table('t_work_run_component_pin')
    op.drop_table('t_item_component_version')
    op.drop_table('t_component_edit_request')
    EDIT_REQUEST_STATUS.drop(op.get_bind(), checkfirst=True)
    op.execute("UPDATE t_item_component SET doc_version = 0")
