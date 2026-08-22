import enum
from app.app import db
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import event, Numeric, select, func, UniqueConstraint
from sqlalchemy.orm import column_property, with_loader_criteria, Session
from flask import g
from app.exception import AuthorizationError
from app.utils import QTY_EPS

def bangkok_now():
    """Return current datetime in Asia/Bangkok. If zoneinfo/tzdata is unavailable,
    fall back to UTC+7 offset to avoid import-time errors on Windows.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Bangkok"))
    except Exception:
        # tzdata not available in this environment — fallback to UTC+7
        return datetime.utcnow() + timedelta(hours=7)

class BaseModel(db.Model):
    __abstract__ = True
    created_date = db.Column(db.DateTime, default=bangkok_now)
    updated_date = db.Column(db.DateTime, default=bangkok_now, onupdate=bangkok_now)

class AuditMixin(BaseModel):
    """Mixin to add created_by and updated_by tracking"""
    __abstract__ = True
    created_by = db.Column(db.String(80))
    updated_by = db.Column(db.String(80))

class BranchScopedMixin:
    """Mixin สำหรับบังคับให้ตารางต้องมี branch_id เสมอ"""
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=False, index=True)

@event.listens_for(Session, "do_orm_execute")
def _add_branch_filter(execute_state):
    """เช็คว่า 1. เป็นคำสั่งดึงข้อมูล (SELECT) และ 2. User คนนี้ล็อกอินและมี g.branch_id อยู่"""
    if execute_state.is_select and g.get("branch_id") is not None:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                BranchScopedMixin,
                lambda cls: cls.branch_id == g.branch_id,
                include_aliases=True,
            )
        )
@event.listens_for(db.session, "before_flush")
def manage_branch_data(session, flush_context, instances):
    """ถ้า API รอบนี้ไม่มีข้อมูลสาขา จะปล่อยผ่านไป"""
    if g.get("all_branch_mode"):
        for obj in list(session.new) + list(session.dirty) + list(session.deleted):
            if isinstance(obj, BranchScopedMixin):
                raise AuthorizationError("โหมด All Branch ไม่อนุญาตให้แก้ไขข้อมูล")
        return

    if not g.get("branch_id"):
        return
        
    # ตอนสร้างของใหม่ (INSERT) -> ยัดสาขาให้อัตโนมัติ
    for obj in session.new:
        if isinstance(obj, BranchScopedMixin):
            # ถ้าไม่ได้ส่ง branch_id มา ให้ดึงจาก g.branch_id ของคนที่ล็อกอินอยู่มาใส่
            if getattr(obj, "branch_id", None) is None:
                obj.branch_id = g.branch_id

    # ตอนแก้ไขข้อมูล (UPDATE) -> เช็คว่าใช่ของสาขาตัวเองไหม
    for obj in session.dirty:
        if isinstance(obj, BranchScopedMixin):
            if obj.branch_id != g.branch_id:
                raise AuthorizationError("ไม่ได้รับอนุญาตให้แก้ไขข้อมูลของสาขาอื่น")
                
    # ตอนลบข้อมูล (DELETE)
    for obj in session.deleted:
        if isinstance(obj, BranchScopedMixin):
            if obj.branch_id != g.branch_id:
                raise AuthorizationError("ไม่ได้รับอนุญาตให้ลบข้อมูลของสาขาอื่น")

@event.listens_for(AuditMixin, 'before_insert', propagate=True)
def receive_before_insert(mapper, connection, target):
    """Set created_by when inserting"""
    username = g.get("username", None)
    if username:
        target.created_by = username
        target.updated_by = username

@event.listens_for(AuditMixin, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Set updated_by when updating"""
    username = g.get("username", None)
    if username:
        target.updated_by = username

class Branch(AuditMixin):
    __tablename__ = 'm_branch'

    branch_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch_code = db.Column(db.String(20), unique=True, nullable=False)
    branch_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default='1')

    users = db.relationship('User', secondary='map_user_branch', back_populates='branches', lazy='noload')

user_branch_mapping = db.Table(
    'map_user_branch',
    db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('m_user.user_id', ondelete='CASCADE'), primary_key=True),
    db.Column('branch_id', db.Integer, db.ForeignKey('m_branch.branch_id', ondelete='CASCADE'), primary_key=True)
)

class User(AuditMixin):
    __tablename__ = "m_user"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id', onupdate='CASCADE'), nullable=False, default=2) # default role_id = 2 (Default User)
    password = db.Column(db.String(200), nullable=False)
    role = db.relationship('Role', back_populates="users")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    branches = db.relationship('Branch', secondary='map_user_branch', back_populates='users')

class Tokenlist(BaseModel):
    __tablename__ = "t_token_list"
    id = db.Column(db.Integer, primary_key=True)
    jwt_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    token_type = db.Column(db.String(20), default="refresh")

class Role(BaseModel):
    __tablename__ = "m_role"
    role_id = db.Column(db.Integer, primary_key=True)
    role_code = db.Column(db.String(80), nullable=False)
    role_name = db.Column(db.String(250), unique=True, nullable=False)
    description = db.Column(db.String(200))
    users = db.relationship('User', back_populates="role", lazy='noload')
    active_flag = db.Column(db.Boolean, nullable=False)
    permissions = db.relationship('Permission', secondary='m_role_permission', back_populates='roles')
    def get_permissions(self):
        if self.role_name == "Admin":
            return ["*"]
        return [perm.permission_code for perm in self.permissions]

class Module(BaseModel):
    __tablename__ = "m_module"
    module_id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(255), nullable=False)
    module_code = db.Column(db.String(20), nullable=False, unique=True)
    parent_id = db.Column(db.Integer)
    level = db.Column(db.Integer, default=1)
    sort_order = db.Column(db.Integer)

    permissions = db.relationship(
        'Permission',
        back_populates='module',
        cascade='all, delete-orphan'
    )

class Permission(BaseModel):
    __tablename__ = "m_permission"
    permission_id =  db.Column(db.Integer, primary_key=True)
    module_id = db.Column(
        db.Integer,
        db.ForeignKey('m_module.module_id', ondelete='CASCADE'),
        nullable=False
    )
    method = db.Column(db.String(20), nullable=False) # view, create, edit, delete
    permission_code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    roles = db.relationship('Role', secondary='m_role_permission', back_populates='permissions', lazy='noload')

    module = db.relationship(
        'Module',
        back_populates='permissions'
    )

    __table_args__ = (
        db.UniqueConstraint('module_id', 'method', name='uq_permission_module_method'),
    )



class RolePermission(BaseModel):
    __tablename__ = "m_role_permission"
    role_permission_id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('m_permission.permission_id'), nullable=False)
    active_flag = db.Column(db.Boolean, nullable=False)
    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)

class WorkOrderStatus(enum.Enum):
    READY = 'READY'
    INPROGRESS = 'INPROGRESS'
    WAIT_TEST = 'WAIT_TEST'
    TESTING = 'TESTING'
    COMPLETED = 'COMPLETED'

class WorkOrder(AuditMixin):
    __tablename__ = "t_work_order"
    work_order_id = db.Column(db.Integer, primary_key=True)
    doc_num = db.Column(db.Integer, nullable=False)
    work_order_code = db.Column(db.String(50), nullable=True)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    status = db.Column(db.Enum(WorkOrderStatus), nullable=False , default=WorkOrderStatus.READY)
    quantity = db.Column(db.Double, nullable=False, default=1)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'))
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='work_order')
    item_components = db.relationship('ItemComponent', back_populates='work_order')
    work_runs = db.relationship('WorkRun', back_populates='work_order', cascade='all, delete-orphan')

class BreakType(enum.Enum):
    LUNCHBREAK = "LUNCHBREAK"
    RESTBREAK = "RESTBREAK"
    OTHER = "OTHER"

class WorkRunAssignment(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_work_run_assignment"
    work_run_assignment_id = db.Column(db.Integer, primary_key=True)
    work_run_id = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)
    from_time = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    to_time = db.Column(db.DateTime, nullable=True)
    work_run = db.relationship('WorkRun', back_populates='assignments', lazy='noload')
    employee = db.relationship('Employee', back_populates='work_run_assignments', lazy='noload')

class WorkRunMachine(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_work_run_machine"
    work_run_machine_id = db.Column(db.Integer, primary_key=True)
    work_run_id = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('m_machine.machine_id'), nullable=False)
    from_time = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    to_time = db.Column(db.DateTime, nullable=True)
    allocated_maintenance_cost = db.Column(db.Float, nullable=True, default=0.0)
    depreciation_per_second = db.Column(db.Float, nullable=False, default=0.0)
    maintenance_rate_per_second = db.Column(db.Float, nullable=False, default=0.0)
    depreciation_cost = db.Column(db.Float, nullable=True)
    maintenance_cost = db.Column(db.Float, nullable=True)
    work_run = db.relationship('WorkRun', back_populates='machines', lazy='noload')
    machine = db.relationship('Machine', lazy='noload')

class WorkRunCost(AuditMixin, BranchScopedMixin):
    """Aggregated cost summary for one WorkRun (material + labor + machine)."""
    __tablename__ = "t_work_run_cost"
    cost_id = db.Column(db.Integer, primary_key=True)
    work_run_id = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), unique=True, nullable=False)
    material_cost = db.Column(db.Float, nullable=True)
    depreciation_cost = db.Column(db.Float, nullable=True)
    maintenance_cost = db.Column(db.Float, nullable=True)
    base_labor_cost = db.Column(db.Float, nullable=True)
    day_labor_cost = db.Column(db.Float, nullable=True)
    ot_labor_cost = db.Column(db.Float, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)
    work_run = db.relationship('WorkRun', lazy='noload', overlaps='cost')

class WorkRunBreak(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_work_run_break"
    break_id = db.Column(db.Integer, primary_key=True)
    work_run_id = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    break_start = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    break_end = db.Column(db.DateTime, nullable=True)
    break_type = db.Column(db.Enum(BreakType), nullable=False, default=BreakType.OTHER)
    remark = db.Column(db.String(255), nullable=True)
    work_run = db.relationship('WorkRun', back_populates='breaks', lazy='noload')

@event.listens_for(WorkRunBreak, 'before_insert', propagate=True)
def validate_run_break_remark_before_insert(mapper, connection, target):
    if target.break_type == BreakType.OTHER:
        if not target.remark or not str(target.remark).strip():
            target.remark = ""

@event.listens_for(WorkRunBreak, 'before_update', propagate=True)
def validate_run_break_remark_before_update(mapper, connection, target):
    if target.break_type == BreakType.OTHER:
        if not target.remark or not str(target.remark).strip():
            target.remark = ""

class EmployeeStatus(enum.Enum):
    UNEMPLOYED = 'UNEMPLOYED'
    ACTIVE = 'Active'
    ONLEAVE = 'ONLEAVE'
    SUSPENDED = 'SUSPENDED'

class Shift(AuditMixin):
    """Global shift config. Defines work window, work days, and pay multipliers."""
    __tablename__ = "m_shift"
    shift_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="DEFAULT")
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    work_days = db.Column(db.String(40), nullable=False, default="MON,TUE,WED,THU,FRI")
    ot_multiplier = db.Column(db.Float, nullable=False, default=1.5)
    weekend_multiplier = db.Column(db.Float, nullable=False, default=2.0)
    holiday_multiplier = db.Column(db.Float, nullable=False, default=3.0)
    is_default = db.Column(db.Boolean, nullable=False, default=False)

class Holiday(AuditMixin):
    __tablename__ = "m_holiday"
    holiday_id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    source = db.Column(db.String(50), nullable=False, default="MANUAL")

class Employee(AuditMixin):
    __tablename__ = "m_employee"
    employee_id = db.Column(db.Integer, primary_key=True)
    employee_first_name = db.Column(db.String(100), nullable=False)
    employee_last_name = db.Column(db.String(100), nullable=False)
    citizen_id = db.Column(db.String(20), unique=True, nullable=False)
    phone_number = db.Column(db.String(10), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(EmployeeStatus),nullable=False,default=EmployeeStatus.UNEMPLOYED)
    user_id = db.Column(db.Integer, db.ForeignKey('m_user.user_id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    base_salary = db.Column(db.Float, nullable=False, default=0.0)
    day_rate = db.Column(db.Float, nullable=False, default=0.0)
    ot_hourly_rate = db.Column(db.Float, nullable=False, default=0.0)
    photo_key = db.Column(db.String(500), nullable=True)
    work_run_assignments = db.relationship('WorkRunAssignment', back_populates='employee', lazy='noload')
    test_result_assignments = db.relationship('TestResultAssignment', back_populates='employee', lazy='noload')
    shift_override = db.relationship('EmployeeShift', back_populates='employee', uselist=False, lazy='noload')

class EmployeeShift(AuditMixin):
    """Per-employee override of the global Shift. Full override (replaces shift window/days)."""
    __tablename__ = "m_employee_shift"
    employee_shift_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id', ondelete='CASCADE'), unique=True, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    work_days = db.Column(db.String(40), nullable=False, default="MON,TUE,WED,THU,FRI")
    employee = db.relationship('Employee', back_populates='shift_override', lazy='noload')

class EmployeeSalaryHistory(AuditMixin):
    __tablename__ = "t_employee_salary_history"
    salary_history_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)
    old_base_salary = db.Column(db.Float, nullable=False, default=0.0)
    new_base_salary = db.Column(db.Float, nullable=False, default=0.0)
    old_day_rate = db.Column(db.Float, nullable=False, default=0.0)
    new_day_rate = db.Column(db.Float, nullable=False, default=0.0)
    old_ot_hourly_rate = db.Column(db.Float, nullable=False, default=0.0)
    new_ot_hourly_rate = db.Column(db.Float, nullable=False, default=0.0)
    effective_date = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    remark= db.Column(db.String(255), nullable=True)


class WorkRunStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    PAUSED = 'PAUSED'
    COMPLETED = 'COMPLETED'

class WorkRunTransactionType(enum.Enum):
    SENT_TO_TESTING = 'SENT_TO_TESTING'
    DEFECT_CONSUMED = 'DEFECT_CONSUMED'

class WorkRun(AuditMixin, BranchScopedMixin):
    """One production attempt within a WorkOrder. Rework = new WorkRun on the same WorkOrder."""
    __tablename__ = "t_work_run"
    work_run_id = db.Column(db.Integer, primary_key=True)
    lot_number = db.Column(db.String(100), nullable=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Double, nullable=False, default=1)           # planned/pick qty
    usable_qty = db.Column(db.Double, nullable=True)                     # set at completion — good items
    completion_remark = db.Column(db.String(500), nullable=True)          # required when usable_qty < quantity
    wms_pick_reference = db.Column(db.String(100), nullable=True)
    status = db.Column(db.Enum(WorkRunStatus), nullable=False, default=WorkRunStatus.PENDING)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    rework_source_test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='SET NULL'), nullable=True)
    qty_from_failed = db.Column(db.Double, nullable=True)
    work_order = db.relationship('WorkOrder', back_populates='work_runs', lazy='noload')
    assignments = db.relationship('WorkRunAssignment', back_populates='work_run', cascade='all, delete-orphan', lazy='noload')
    machines = db.relationship('WorkRunMachine', back_populates='work_run', cascade='all, delete-orphan', lazy='noload')
    breaks = db.relationship('WorkRunBreak', back_populates='work_run', cascade='all, delete-orphan', order_by='WorkRunBreak.break_start', lazy='noload')
    test_result_sources = db.relationship('TestResultWorkRun', back_populates='work_run', cascade='all, delete-orphan')
    rework_sources = db.relationship('WorkRunReworkSource', foreign_keys='WorkRunReworkSource.rework_work_run_id', back_populates='rework_work_run', cascade='all, delete-orphan')
    rework_destinations = db.relationship('WorkRunReworkSource', foreign_keys='WorkRunReworkSource.source_work_run_id', back_populates='source_work_run')
    rework_source_test_result = db.relationship('TestResult', foreign_keys=[rework_source_test_result_id], back_populates='rework_work_runs', lazy='noload')
    transactions              = db.relationship('WorkRunTransaction', back_populates='work_run', cascade='all, delete-orphan')
    required_items            = db.relationship('WorkRunRequiredItem', back_populates='work_run', cascade='all, delete-orphan', lazy='noload')
    cost                      = db.relationship('WorkRunCost', foreign_keys='WorkRunCost.work_run_id', uselist=False, lazy='noload', overlaps='work_run')
    component_pins            = db.relationship('WorkRunComponentPin', back_populates='work_run', cascade='all, delete-orphan', lazy='noload')


    @property
    def defect_qty(self):
        if self.usable_qty is None:
            return None
        return self.quantity - self.usable_qty

    @property
    def consumed_defect_qty(self):
        return sum(src.qty for src in self.rework_destinations)

    @property
    def outstanding_defect_qty(self):
        if self.defect_qty is None:
            return None
        return self.defect_qty - self.consumed_defect_qty

    @property
    def tested_qty(self):
        return sum(src.qty_from_run for src in self.test_result_sources)

    @property
    def untested_qty(self):
        if self.usable_qty is None:
            return None
        return self.usable_qty - self.tested_qty

class SalesItemStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    COMPLETED = 'COMPLETED'

# Item group that marks a made-to-order item built from a BOM. It has to be
# manufactured in-house, so it can never be completed without production —
# regardless of what the produce flag from center says.
MANUFACTURED_ITEM_GROUP = "Z-BOM"

class SalesItem(AuditMixin):
    __tablename__ = "t_sales_items"
    sales_item_id = db.Column(db.Integer, primary_key=True)
    center_sales_item_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Enum(SalesItemStatus), nullable=False , default=SalesItemStatus.PENDING)
    item_code = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Double, nullable=False)
    order_line_num = db.Column(db.Integer, nullable=True)
    unit_name = db.Column(db.String(28), nullable=False, default="Piece")
    unit_id = db.Column(db.Integer, nullable=False, default=0)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    doc_num = db.Column(db.Integer, nullable=False)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    produce = db.Column(db.Boolean, nullable=False)
    test = db.Column(db.Boolean, nullable=False)
    item_group = db.Column(db.String(64), nullable=False, default="Z-BOM")
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='sales_items', lazy='noload')

    __table_args__ = (
        db.Index('ix_sales_items_doc_entry_produce', 'doc_entry', 'produce'),
        db.Index('ix_sales_items_doc_entry_test', 'doc_entry', 'test'),
    )
    material_list = db.relationship('MaterialList', back_populates='sales_item')
    work_order = db.relationship('WorkOrder', back_populates='sales_item', uselist=False, lazy="noload")
    qc_work_orders = db.relationship('QCWorkOrder', back_populates='sales_item')
    test_specs = db.relationship('TestSpec', back_populates='sales_item')
    picking_request_items = db.relationship('PickingRequestItem', back_populates='sales_item', lazy='noload')

    # Production
    @property
    def producing_qty(self):
        if not self.work_order:
            return 0
        return sum(r.quantity for r in self.work_order.work_runs if r.status == WorkRunStatus.INPROGRESS)

    @property
    def produced_qty(self):
        if not self.work_order:
            return 0
        return sum(r.usable_qty or 0 for r in self.work_order.work_runs if r.status == WorkRunStatus.COMPLETED)

    # Test
    @property
    def unavailable_for_test_qty(self):
        """Physical units already claimed against the shared DIRECT test pool
        (the pool `create_qc_work_order`'s planned-qty guard bounds by
        `quantity`). COMPONENT_SECTION QCs are excluded on purpose: per the
        TestSpec unification "per-spec full qty" decision, each declaring
        component independently requires the WHOLE `quantity` to be covered —
        it does not draw down this shared pool. Summing them in here (the old
        single-pool model, pre-TestSpec) would make two declaring components
        exhaust — or go negative on — availability between themselves alone,
        wrongly blocking every other test on the item.

        Requires qc_work_orders[*].test_spec to be eager-loaded (it's
        lazy='noload') — see sales_item_repository's eager-load comment on
        this exact point; an unloaded test_spec silently reads as None and
        this would misclassify every QC as DIRECT.
        """
        return sum(
            tr.claimed_qty
            for qc in self.qc_work_orders
            for tr in qc.test_results
            if qc.test_spec is None or qc.test_spec.source_type == TestSpecSourceType.DIRECT
        )

    @property
    def picked_qty(self):
        """Sum of all PickingRequestItem quantities where the parent PR is SUCCESS."""
        return sum(
            item.quantity
            for item in self.picking_request_items
            if item.picking_request and item.picking_request.status == PickingRequestStatus.SUCCESS
        )

    @property
    def available_for_test_qty(self):
        if not self.produce:
            return self.picked_qty - self.unavailable_for_test_qty
        return self.produced_qty - self.unavailable_for_test_qty
    
    # Cert & Test Results
    @property
    def passed_qty(self):
        return sum(
            tr.claimed_qty for qc in self.qc_work_orders for tr in qc.test_results
            if tr.overall_status == TestResultStatus.PASSED
        )

    @property
    def failed_qty(self):
        return sum(
            tr.claimed_qty for qc in self.qc_work_orders for tr in qc.test_results
            if tr.overall_status == TestResultStatus.FAILED
        )

    # Production gate for BOM items
    @property
    def is_manufactured(self):
        """Z-BOM item — built from a BOM, so it must go through production."""
        return (self.item_group or "").strip().upper() == MANUFACTURED_ITEM_GROUP

    @property
    def production_blocker(self):
        """Reason a Z-BOM item's production is not finished yet, else None.

        Requires work_order -> work_runs to be eager-loaded (both are lazy='noload',
        so an unloaded work_order reads as None and would wrongly report a blocker).
        """
        if not self.is_manufactured:
            return None
        if not self.work_order:
            return "เป็นรายการ Z-BOM แต่ยังไม่มีใบสั่งผลิต"
        open_runs = sum(1 for r in self.work_order.work_runs if r.status != WorkRunStatus.COMPLETED)
        if open_runs:
            return f"เป็นรายการ Z-BOM และยังมีรอบผลิตที่ยังไม่จบ {open_runs} รอบ"
        if self.produced_qty < self.quantity - QTY_EPS:
            return f"เป็นรายการ Z-BOM ผลิตได้ {self.produced_qty}/{self.quantity} ยังไม่ครบ"
        return None

    @property
    def has_open_work(self):
        """True if any production run or QC work order on this item is still unfinished."""
        if self.work_order and any(r.status != WorkRunStatus.COMPLETED for r in self.work_order.work_runs):
            return True
        return (self.num_qc_work_order or 0) > (self.num_qc_successed_work_order or 0)

    @property
    def is_completable(self):
        if self.status == SalesItemStatus.COMPLETED:
            return (False, "งานถูกปิดไปแล้ว")

        blocker = self.production_blocker
        if blocker:
            return (False, blocker)

        # produced means usable items by default itself.
        if (self.produced_qty < self.quantity - QTY_EPS) and self.produce:
            return (False, "ยังผลิตไม่ครบ")

        if self.produce and self.producing_qty > QTY_EPS:
            return (False, "ยังมีรายการผลิตค้างอยู่")
        
        if self.test and self.num_qc_work_order == 0:
            return (False, "ไม่สำเร็จ ยังไม่ได้ทำใบสั่งเทส")
                
        # Produced or not produced / Produced is done or not. If it has test and test is not done, False
        if (self.num_qc_successed_work_order == self.num_qc_work_order) and self.num_qc_work_order != 0:
            return (True, "สำเร็จ ทำการเทสผ่าน")
        if self.num_qc_work_order == 0:
            return (True, "สำเร็จ ไม่มีรายการเทส")
        
        return (False, "มีรายการเทสยังไม่เสร็จ (รายการนี้เป็นรายการ Fallback ด้วย หากเกิดข้อผิดพลาด หากตรวจสอบครบถ้วนว่าเทสผ่านหมดแล้ว อาจเกิดปัญหาที่โปรแกรม)")
    
class MachineType(AuditMixin):
    __tablename__ = "m_machine_type"
    machine_type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), nullable=False)
    type_description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    machines = db.relationship('Machine', back_populates='machine_type', lazy='noload')

class MachineStatus(enum.Enum):
    RUNNING = "RUNNING"
    DOWN = "DOWN"
    IDLE = "IDLE"
    OFFLINE = "OFFLINE"

class Machine(AuditMixin,BranchScopedMixin):
    __tablename__ = "m_machine"
    machine_id = db.Column(db.Integer, primary_key=True)
    machine_code = db.Column(db.String(50), nullable=False)
    machine_name = db.Column(db.String(255), nullable=False)
    machine_description = db.Column(db.String(500))
    manufacturer = db.Column(db.String(255), nullable=True)
    purchase_date = db.Column(db.DateTime, nullable=True)
    purchase_price = db.Column(db.Float, nullable=False, default=0)
    useful_life_years = db.Column(db.Integer, nullable=True, default=0)
    working_hours_per_day = db.Column(db.Integer, nullable=True, default=0)
    remaining_maintenance_cost = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.Enum(MachineStatus), nullable=False, default=MachineStatus.IDLE)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_second_hand = db.Column(db.Boolean, nullable=False, default=False)
    accumulated_hours = db.Column(db.Float, nullable=True, default=0.0)
    photo_key = db.Column(db.String(500), nullable=True)
    machine_type_id = db.Column(db.Integer, db.ForeignKey('m_machine_type.machine_type_id'), nullable=True)
    machine_type = db.relationship('MachineType', back_populates='machines', lazy='joined')
    maintenances = db.relationship('MachineMaintenance', back_populates='machine', lazy='noload')
    __table_args__ = (
    UniqueConstraint('branch_id', 'machine_code', name='uq_branch_machine_code'),
)

class MachineMaintenance(AuditMixin,BranchScopedMixin):
    __tablename__ = "t_machine_maintenance"
    maintenance_id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('m_machine.machine_id', ondelete='CASCADE'), nullable=False)
    maintenance_date = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    maintenance_type = db.Column(db.String(50), nullable=False) # Preventive, Corrective
    description = db.Column(db.String(500), nullable=True)
    fix_cost = db.Column(db.Float, nullable=True, default=0)
    machine = db.relationship('Machine', foreign_keys=[machine_id], back_populates='maintenances', lazy='noload')



class MaterialList(AuditMixin):
    __tablename__ = "t_material_list"
    material_list_id = db.Column(db.Integer, primary_key=True)
    center_material_id = db.Column(db.Integer, nullable=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    quantity = db.Column(db.Double, nullable=False)
    unit_name = db.Column(db.String(28), nullable=False, default="Piece")
    unit_id = db.Column(db.Integer, nullable=False, default=0)
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    item_group = db.Column(db.String(64), nullable=False, default="OTHER")
    sales_item = db.relationship('SalesItem', back_populates='material_list', lazy='noload')
    component_usages = db.relationship('ComponentMaterialUsage', back_populates='material_list', lazy='noload')
    # Forward: used by remaining_num property and transaction_service
    transactions = db.relationship('MaterialTransaction', back_populates='material_list')
    order_line_num = db.Column(db.Integer)

    @property
    def remaining_num(self):
        return sum(t.amount for t in self.transactions)

    @property
    def cost_per_unit(self):
        if self.quantity and self.quantity > 0:
            return round(self.cost_price / self.quantity, 6)
        return 0.0

class TestSpecSourceType(enum.Enum):
    DIRECT = 'DIRECT'
    COMPONENT_SECTION = 'COMPONENT_SECTION'


class TestSpec(AuditMixin):
    """Unifies the two origins of a QC/test document that used to be forked by
    the bare-boolean-by-proxy `QCWorkOrder.source_work_order_id`: a manually
    created DIRECT spec, or a COMPONENT_SECTION spec generated because one of
    the WorkOrder's ItemComponent template sections declared a test. One spec
    per (sales_item, item_component) — see project_testspec_unification memory.
    """
    __tablename__ = "t_test_spec"
    __table_args__ = (
        UniqueConstraint('sales_item_id', 'item_component_id', name='uq_test_spec_sales_item_component'),
    )

    test_spec_id = db.Column(db.Integer, primary_key=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    source_type = db.Column(db.Enum(TestSpecSourceType), nullable=False)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='SET NULL'), nullable=True)
    item_component_version_id = db.Column(db.Integer, db.ForeignKey('t_item_component_version.version_id', ondelete='SET NULL'), nullable=True)
    section_keys = db.Column(db.JSON, nullable=True)
    required_qty = db.Column(db.Double, nullable=False)

    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='test_specs', lazy='noload')
    item_component = db.relationship('ItemComponent', foreign_keys=[item_component_id], lazy='noload')
    item_component_version = db.relationship('ItemComponentVersion', foreign_keys=[item_component_version_id], lazy='noload')
    qc_work_orders = db.relationship('QCWorkOrder', back_populates='test_spec', lazy='noload')


class QCWorkOrderStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    PASSED = 'PASSED'

class QCWorkOrder(AuditMixin):
    __tablename__ = "t_qc_work_order"
    qc_work_order_id = db.Column(db.Integer, primary_key=True)
    qc_work_order_code = db.Column(db.String(50), nullable=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    status = db.Column(db.Enum(QCWorkOrderStatus), nullable=False, default=QCWorkOrderStatus.PENDING)
    qc_date = db.Column(db.DateTime, nullable=True)
    qc_by = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Double, nullable=False, default=1)
    remark = db.Column(db.String(500), nullable=True)
    # Points at the TestSpec (DIRECT or COMPONENT_SECTION) this QCWorkOrder was
    # created to fulfil. SET NULL on TestSpec delete: the QCWorkOrder (and any
    # TestResult already recorded against it) must survive even if the spec is gone.
    test_spec_id = db.Column(db.Integer, db.ForeignKey('t_test_spec.test_spec_id', ondelete='SET NULL'), nullable=True, index=True)
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='qc_work_orders')
    test_spec = db.relationship('TestSpec', foreign_keys=[test_spec_id], back_populates='qc_work_orders', lazy='noload')
    qc_form = db.relationship('QCForm', uselist=False, back_populates='qc_work_order', cascade='all, delete-orphan')
    qc_items = db.relationship('QCItem', back_populates='qc_work_order', cascade='all, delete-orphan')
    test_results = db.relationship('TestResult', back_populates='qc_work_order', lazy='noload')

    @property
    def is_component_declared(self):
        return self.test_spec is not None and self.test_spec.source_type == TestSpecSourceType.COMPONENT_SECTION


SalesItem.num_qc_work_order = column_property(
    select(func.count(QCWorkOrder.qc_work_order_id))
    .where(QCWorkOrder.sales_item_id == SalesItem.sales_item_id)
    .correlate(SalesItem)
    .scalar_subquery()
)

SalesItem.num_qc_successed_work_order = column_property(
    select(func.count(QCWorkOrder.qc_work_order_id))
    .where(
        QCWorkOrder.sales_item_id == SalesItem.sales_item_id,
        QCWorkOrder.status == QCWorkOrderStatus.PASSED,
    )
    .correlate(SalesItem)
    .scalar_subquery()
)


class QCForm(AuditMixin):
    """ข้อมูล form ใบสั่งงาน QC (checkbox มาตรฐาน, ใบรับรอง, serial, remark) — 1-to-1 กับ QCWorkOrder"""
    __tablename__ = "t_qc_form"
    qc_form_id = db.Column(db.Integer, primary_key=True)
    qc_work_order_id = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='CASCADE'), nullable=False, unique=True)

    # มาตรฐาน
    std_ptt         = db.Column(db.Boolean, default=False)
    std_chevron     = db.Column(db.Boolean, default=False)
    std_valeur      = db.Column(db.Boolean, default=False)
    std_ophir       = db.Column(db.Boolean, default=False)
    std_three_spec  = db.Column(db.Boolean, default=False)
    std_others      = db.Column(db.Boolean, default=False)
    std_others_text = db.Column(db.String(200), nullable=True)

    # ใบรับรอง
    cert_inhouse      = db.Column(db.Boolean, default=False)
    cert_third_party  = db.Column(db.Boolean, default=False)
    cert_ndt          = db.Column(db.Boolean, default=False)
    cert_others       = db.Column(db.Boolean, default=False)
    cert_others_text  = db.Column(db.String(200), nullable=True)

    # Serial Number
    serial_tag      = db.Column(db.Boolean, default=False)
    serial_imprint  = db.Column(db.Boolean, default=False)
    serial_continue = db.Column(db.Boolean, default=False)
    serial_others   = db.Column(db.Boolean, default=False)
    serial_others_text = db.Column(db.String(200), nullable=True)

    # Remark & Details
    general_remark           = db.Column(db.Text, nullable=True)
    details                  = db.Column(db.Text, nullable=True)
    customer_receipt_number  = db.Column(db.String(100), nullable=True)

    # วันที่ย้าย / วันที่ส่ง — split out of customer_receipt_number, which the
    # frontend used to (mis)bind to both date inputs via one shared string
    # state field. customer_receipt_number keeps meaning an actual receipt
    # number; its pre-existing values are NOT backfilled into these columns
    # since they are ambiguous (could be either date, in an unknown format).
    transfer_date = db.Column(db.Date, nullable=True)
    delivery_date = db.Column(db.Date, nullable=True)

    qc_work_order = db.relationship('QCWorkOrder', back_populates='qc_form', lazy='noload')


class QCItem(AuditMixin):
    """
    Instruction items on a QCWorkOrder — describes what is needed to perform the test.
    material_list_id + required_qty = trackable rows seeded into TestResultRequiredItem at test creation.
    Rows without material_list_id are pure documentation (wll, serial_no, print purposes).
    """
    __tablename__ = "t_qc_item"
    qc_item_id       = db.Column(db.Integer, primary_key=True)
    qc_work_order_id = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='CASCADE'), nullable=False)
    item_order       = db.Column(db.Integer, nullable=True)
    item_code        = db.Column(db.String(100), nullable=True)
    description      = db.Column(db.Text, nullable=True)
    wll              = db.Column(db.String(50), nullable=True)
    quantity         = db.Column(db.String(50), nullable=True)   # human-readable / print
    serial_no        = db.Column(db.String(200), nullable=True)
    item_remark      = db.Column(db.String(500), nullable=True)
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True)
    required_qty     = db.Column(db.Double, nullable=True)      # numeric qty for pool allocation
    qc_work_order    = db.relationship('QCWorkOrder', back_populates='qc_items', lazy='noload')
    material_list    = db.relationship('MaterialList', lazy='noload')


class TestResultStatus(enum.Enum):
    PASSED = 'PASSED'
    FAILED = 'FAILED'


class TestType(enum.Enum):
    PROOF_LOAD  = 'PROOF_LOAD'
    BREAKING    = 'BREAKING'
    VISUAL      = 'VISUAL'
    DIMENSIONAL = 'DIMENSIONAL'


class CheckStatus(enum.Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    NA   = 'NA'


class TestSessionStatus(enum.Enum):
    PENDING    = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    PAUSED     = 'PAUSED'
    COMPLETED  = 'COMPLETED'


class TestResult(AuditMixin, BranchScopedMixin):
    """
    One test session covering claimed_qty items from a SalesItem.
    Phase 1 (INPROGRESS): created with claimed_qty — fires IN_TESTING transaction.
    Phase 2 (COMPLETED):  finalized with per-item results — fires TESTED_PASSED/TESTED_FAILED.
    """
    __tablename__ = "t_test_result"
    test_result_id     = db.Column(db.Integer, primary_key=True)
    test_result_code   = db.Column(db.String(100), nullable=True)
    qc_work_order_id   = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='SET NULL'), nullable=True)
    claimed_qty        = db.Column(db.Double, nullable=False)
    session_status     = db.Column(db.Enum(TestSessionStatus), nullable=False, default=TestSessionStatus.INPROGRESS)
    started_at         = db.Column(db.DateTime, nullable=True)
    test_method        = db.Column(db.String(255), nullable=True)   # printed label (free text)
    test_type          = db.Column(db.Enum(TestType), nullable=True) # controlled type for logic / checklist
    standard_reference = db.Column(db.String(255), nullable=True)
    overall_status     = db.Column(db.Enum(TestResultStatus), nullable=True)
    remark             = db.Column(db.String(500), nullable=True)
    test_result_items       = db.relationship('TestResultItem', back_populates='test_result', cascade='all, delete-orphan')
    photos                  = db.relationship('TestResultPhoto', back_populates='test_result', cascade='all, delete-orphan', order_by='TestResultPhoto.sequence', lazy='noload')
    spec                    = db.relationship('TestResultSpec', back_populates='test_result', uselist=False, cascade='all, delete-orphan', lazy='noload')
    work_run_sources        = db.relationship('TestResultWorkRun', back_populates='test_result', cascade='all, delete-orphan')
    required_items          = db.relationship('TestResultRequiredItem', back_populates='test_result', cascade='all, delete-orphan', lazy='noload')
    qc_work_order           = db.relationship('QCWorkOrder', back_populates='test_results', lazy='noload')
    rework_work_runs        = db.relationship('WorkRun', foreign_keys='WorkRun.rework_source_test_result_id', back_populates='rework_source_test_result', lazy='noload')
    assignments             = db.relationship('TestResultAssignment', back_populates='test_result', cascade='all, delete-orphan', lazy='noload')
    machines                = db.relationship('TestResultMachine', back_populates='test_result', cascade='all, delete-orphan', lazy='noload')
    breaks                  = db.relationship('TestResultBreak', back_populates='test_result', cascade='all, delete-orphan', order_by='TestResultBreak.break_start', lazy='noload')
    cost                    = db.relationship('TestResultCost', foreign_keys='TestResultCost.test_result_id', uselist=False, lazy='noload', overlaps='test_result')

    @property
    def failed_item_qty(self):
        return sum(1 for item in self.test_result_items if item.result == TestResultStatus.FAILED)

    @property
    def reworked_qty(self):
        return sum(wr.qty_from_failed or 0 for wr in self.rework_work_runs)

    @property
    def outstanding_failed_qty(self):
        return self.failed_item_qty - self.reworked_qty


class TestResultItem(AuditMixin, BranchScopedMixin):
    """ผลการทดสอบรายหน่วย — 1 row ต่อ 1 ชิ้นที่ทดสอบ (quantity ของ SalesItem)"""
    __tablename__ = "t_test_result_item"
    test_result_item_id = db.Column(db.Integer, primary_key=True)
    test_result_id      = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    unit_number         = db.Column(db.Integer, nullable=False)  # ลำดับชิ้น เช่น 1, 2, ...
    serial_no           = db.Column(db.String(200), nullable=True)
    wll_measured        = db.Column(db.Float, nullable=True)
    load_test_value     = db.Column(db.Float, nullable=True)   # applied peak load
    description         = db.Column(db.Text, nullable=True)
    result              = db.Column(db.Enum(TestResultStatus), nullable=False, default=TestResultStatus.PASSED)
    remark              = db.Column(db.String(500), nullable=True)

    # --- Proof load test parameters/measurements ---
    required_load       = db.Column(db.Float, nullable=True)   # target load (WLL × factor per standard)
    hold_time_sec       = db.Column(db.Integer, nullable=True)
    length_before       = db.Column(db.Float, nullable=True)
    length_after        = db.Column(db.Float, nullable=True)

    # --- Breaking test ---
    breaking_force      = db.Column(db.Float, nullable=True)
    min_breaking_load   = db.Column(db.Float, nullable=True)

    # --- Verdict ---
    fail_reason         = db.Column(db.String(255), nullable=True)

    # --- Breaking test load curve (sampled series, stored whole) ---
    load_curve          = db.Column(db.JSON, nullable=True)   # [{"t": <sec>, "load": <value>}, ...]

    test_result = db.relationship('TestResult', back_populates='test_result_items', lazy='noload')
    checks = db.relationship('TestResultCheck', back_populates='test_result_item',
                             cascade='all, delete-orphan', order_by='TestResultCheck.sequence')

    @property
    def permanent_set(self):
        """Proof-load acceptance criterion: permanent elongation after load removed."""
        if self.length_before is not None and self.length_after is not None:
            return round(self.length_after - self.length_before, 4)
        return None

    @property
    def efficiency(self):
        """Breaking test: actual breaking force as % of minimum breaking load."""
        if self.breaking_force is not None and self.min_breaking_load:
            return round(self.breaking_force / self.min_breaking_load * 100, 1)
        return None


class TestResultCheck(AuditMixin, BranchScopedMixin):
    """Per-unit visual/inspection checklist row (e.g. 'Broken wires', 'Mechanism function')."""
    __tablename__ = "t_test_result_check"
    check_id = db.Column(db.Integer, primary_key=True)
    test_result_item_id = db.Column(db.Integer,
        db.ForeignKey('t_test_result_item.test_result_item_id', ondelete='CASCADE'), nullable=False)
    check_name = db.Column(db.String(255), nullable=False)
    status     = db.Column(db.Enum(CheckStatus), nullable=False, default=CheckStatus.NA)
    note       = db.Column(db.String(500), nullable=True)
    sequence   = db.Column(db.Integer, nullable=False, default=0)
    test_result_item = db.relationship('TestResultItem', back_populates='checks', lazy='noload')


class TestResultPhoto(AuditMixin, BranchScopedMixin):
    """Session-level test evidence photos (stored in MinIO; DB holds the object_key)."""
    __tablename__ = "t_test_result_photo"
    photo_id       = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer,
        db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    object_key     = db.Column(db.String(500), nullable=False)
    caption        = db.Column(db.String(255), nullable=True)
    sequence       = db.Column(db.Integer, nullable=False, default=0)
    test_result    = db.relationship('TestResult', back_populates='photos', lazy='noload')


class TestResultSpec(AuditMixin, BranchScopedMixin):
    """Per-session product spec snapshot (NOT item master — captured as-tested)."""
    __tablename__ = "t_test_result_spec"
    spec_id          = db.Column(db.Integer, primary_key=True)
    test_result_id   = db.Column(db.Integer,
        db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False, unique=True)
    construction     = db.Column(db.String(100), nullable=True)   # "6x36 IWRC"
    grade            = db.Column(db.String(50),  nullable=True)   # "1960 N/mm²"
    coating          = db.Column(db.String(50),  nullable=True)   # "GAL"
    diameter         = db.Column(db.Float,       nullable=True)   # mm
    nominal_length   = db.Column(db.Float,       nullable=True)   # m
    tensile_strength = db.Column(db.Float,       nullable=True)   # N/mm²
    manufacturer     = db.Column(db.String(255), nullable=True)
    batch_no         = db.Column(db.String(100), nullable=True)
    termination      = db.Column(db.String(255), nullable=True)  # "Ordinary Thimble + Ferrule"
    test_result      = db.relationship('TestResult', back_populates='spec', lazy='noload')


class TestResultWorkRun(BaseModel):
    """Association: which WorkRun(s) contributed items to a TestResult, and how many."""
    __tablename__ = "t_test_result_work_run"
    id             = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    work_run_id    = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    qty_from_run   = db.Column(db.Double, nullable=False)

    test_result = db.relationship('TestResult', back_populates='work_run_sources', lazy='noload')
    work_run    = db.relationship('WorkRun',    back_populates='test_result_sources', lazy='noload')


class WorkRunReworkSource(BaseModel):
    """Association: which source WorkRun(s) contributed defective items to a rework WorkRun, and how many."""
    __tablename__ = "t_work_run_rework_source"
    id                  = db.Column(db.Integer, primary_key=True)
    rework_work_run_id  = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    source_work_run_id  = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    qty                 = db.Column(db.Double, nullable=False)
    rework_work_run = db.relationship('WorkRun', foreign_keys=[rework_work_run_id], back_populates='rework_sources', lazy='noload')
    source_work_run = db.relationship('WorkRun', foreign_keys=[source_work_run_id], back_populates='rework_destinations', lazy='noload')


class WorkRunRequiredItem(AuditMixin, BranchScopedMixin):
    """BOM snapshot for a WorkRun — materials it needs before it can start."""
    __tablename__ = "t_work_run_required_item"
    id                   = db.Column(db.Integer, primary_key=True)
    work_run_id          = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    material_list_id     = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True)
    item_code            = db.Column(db.String(100), nullable=False)
    item_name            = db.Column(db.String(255), nullable=False)
    quantity             = db.Column(db.Double, nullable=False)
    unit                 = db.Column(db.String(50), nullable=True)
    qty_consumed_actual  = db.Column(db.Double, nullable=True)   # None until complete

    work_run                 = db.relationship('WorkRun', back_populates='required_items', lazy='noload')
    material_list            = db.relationship('MaterialList', lazy='noload')


class TestResultRequiredItem(AuditMixin, BranchScopedMixin):
    """
    Material requirement for a TestResult, seeded from QCItem at create time.
    qty_consumed_actual reported at finalize (informational — WMS owns real stock).
    """
    __tablename__ = "t_test_result_required_item"
    id                   = db.Column(db.Integer, primary_key=True)
    test_result_id       = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    qc_item_id           = db.Column(db.Integer, db.ForeignKey('t_qc_item.qc_item_id', ondelete='SET NULL'), nullable=True)
    material_list_id     = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True)
    item_code            = db.Column(db.String(100), nullable=False)
    item_name            = db.Column(db.String(255), nullable=False)
    required_qty         = db.Column(db.Double, nullable=False)
    unit                 = db.Column(db.String(50), nullable=True)
    qty_consumed_actual  = db.Column(db.Double, nullable=True)   # None until finalize

    test_result           = db.relationship('TestResult', back_populates='required_items', lazy='noload')
    material_list         = db.relationship('MaterialList', lazy='noload')


class TestResultAssignment(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_test_result_assignment"

    test_result_assignment_id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)
    from_time = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    to_time = db.Column(db.DateTime, nullable=True)
    test_result = db.relationship('TestResult', back_populates='assignments', lazy='noload')
    employee = db.relationship('Employee', back_populates='test_result_assignments', lazy='noload')


class TestResultMachine(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_test_result_machine"

    test_result_machine_id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('m_machine.machine_id'), nullable=False)
    from_time = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    to_time = db.Column(db.DateTime, nullable=True)
    allocated_maintenance_cost = db.Column(db.Float, nullable=True, default=0.0)
    depreciation_per_second = db.Column(db.Float, nullable=False, default=0.0)
    maintenance_rate_per_second = db.Column(db.Float, nullable=False, default=0.0)
    depreciation_cost = db.Column(db.Float, nullable=True)
    maintenance_cost = db.Column(db.Float, nullable=True)
    test_result = db.relationship('TestResult', back_populates='machines', lazy='noload')
    machine = db.relationship('Machine', lazy='noload')


class TestResultBreak(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_test_result_break"

    break_id       = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    break_start    = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    break_end      = db.Column(db.DateTime, nullable=True)
    break_type     = db.Column(db.Enum(BreakType), nullable=False, default=BreakType.OTHER)
    remark         = db.Column(db.String(255), nullable=True)
    test_result    = db.relationship('TestResult', back_populates='breaks', lazy='noload')


class TestResultCost(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_test_result_cost"

    cost_id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), unique=True, nullable=False)
    material_cost = db.Column(db.Float, nullable=True)
    depreciation_cost = db.Column(db.Float, nullable=True)
    maintenance_cost = db.Column(db.Float, nullable=True)
    base_labor_cost = db.Column(db.Float, nullable=True)
    day_labor_cost = db.Column(db.Float, nullable=True)
    ot_labor_cost = db.Column(db.Float, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)
    test_result = db.relationship('TestResult', lazy='noload', overlaps='cost')

class WorkRunTransaction(AuditMixin, BranchScopedMixin):
    """Audit log of item movements on a WorkRun (sent to testing, defects consumed by rework)."""
    __tablename__ = "t_work_run_transaction"
    transaction_id        = db.Column(db.Integer, primary_key=True)
    work_run_id           = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False)
    quantity              = db.Column(db.Double, nullable=False)
    type                  = db.Column(db.Enum(WorkRunTransactionType), nullable=False)
    related_document_code = db.Column(db.String(128), nullable=False)
    work_run = db.relationship('WorkRun', back_populates='transactions', lazy='noload')


class CertificationStatus(enum.Enum):
    PASSED = 'PASSED'
    FAILED = 'FAILED'

class QCCertification(AuditMixin):
    __tablename__ = "t_qc_certification"
    qc_certification_id = db.Column(db.Integer, primary_key=True)

    certification_number = db.Column(db.String(255), nullable=False)
    certification_date = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    standard_reference = db.Column(db.String(255), nullable=True)
    remark = db.Column(db.String(500), nullable=True)
    test_method = db.Column(db.String(255), nullable=True)
    certification_status = db.Column(db.Enum(CertificationStatus), nullable=False, default=CertificationStatus.PASSED)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry', ondelete='CASCADE'), nullable=False)
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='certifications', lazy='noload')

    check_items = db.relationship('QCCheckItem', back_populates='certification', cascade='all, delete-orphan')


class QCCheckItem(AuditMixin): # Certificate Item
    __tablename__ = "t_qc_check_item"
    test_id = db.Column(db.Integer, primary_key=True)

    qc_certification_id  = db.Column(db.Integer, db.ForeignKey('t_qc_certification.qc_certification_id', ondelete='CASCADE'), nullable=False)
    sales_item_id        = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='SET NULL'), nullable=True)
    test_result_item_id  = db.Column(db.Integer, db.ForeignKey('t_test_result_item.test_result_item_id', ondelete='SET NULL'), nullable=True)
    sales_item           = db.relationship('SalesItem', foreign_keys=[sales_item_id])
    test_result_item     = db.relationship('TestResultItem', foreign_keys=[test_result_item_id])
    certification        = db.relationship('QCCertification', back_populates='check_items', lazy='noload')

    item_no     = db.Column(db.String(50), nullable=True)
    test_number = db.Column(db.String(255), nullable=False)
    ref_number  = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    wll         = db.Column(db.Float, nullable=True)
    load_test   = db.Column(db.Float, nullable=True)

class SalesOrderStatus(enum.Enum):
    INPROGRESS = 'INPROGRESS'
    COMPLETED = 'COMPLETED'

class UrgencyLevel(enum.Enum):
    LOW = 'LOW'
    NORMAL = 'NORMAL'
    HIGH = 'HIGH'
    URGENT = 'URGENT'

class SalesOrder(AuditMixin):
    __tablename__ = "t_sales_order"
    doc_entry = db.Column(db.Integer, primary_key=True)
    center_sales_order_id = db.Column(db.Integer, nullable=True)
    doc_num = db.Column(db.Integer, nullable=False, unique=True)
    status = db.Column(db.Enum(SalesOrderStatus), nullable=False, default=SalesOrderStatus.INPROGRESS)
    # Center can request cancel at any time. cancel_requested = drain-pending banner
    # (block new forward work, let in-flight runs/tests finish). cancel_completed_date
    # is stamped when the drain empties — terminal. Stop-forward only: no WMS reversal.
    cancel_requested = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    cancel_requested_date = db.Column(db.DateTime, nullable=True)
    cancel_completed_date = db.Column(db.DateTime, nullable=True)
    urgency_level = db.Column(db.Enum(UrgencyLevel), nullable=True)
    card_code = db.Column(db.String(20), nullable=False)
    card_name = db.Column(db.String(200), nullable=False)
    po_number = db.Column(db.String(100), nullable=True)
    slp_code = db.Column(db.String(20), nullable=False)
    slp_name = db.Column(db.String(200), nullable=False)
    bpl_code = db.Column(db.String(20), nullable=False)
    bpl_name = db.Column(db.String(200), nullable=False)
    group_code = db.Column(db.String(20), nullable=False)
    group_name = db.Column(db.String(200), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)

    sales_items = db.relationship(
        "SalesItem",
        back_populates="sales_order",
        lazy='noload',
    )
    certifications = db.relationship('QCCertification', back_populates='sales_order')
    picking_requests = db.relationship('PickingRequest', back_populates='sales_order', lazy='noload')

class ItemComponent(AuditMixin):
    __tablename__ = "t_item_component"
    item_component_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    work_order = db.relationship('WorkOrder', back_populates='item_components', lazy='noload')
    material_usages = db.relationship(
        "ComponentMaterialUsage",
        back_populates="item_component",
    )
    component_name = db.Column(db.String(255), nullable=False)
    remark = db.Column(db.String(255), nullable=True)
    img_url = db.Column(db.String(500), nullable=True)
    component_template_sections = db.relationship('ComponentTemplateSectionData', back_populates='item_component', lazy='noload')
    component_template_id = db.Column(db.Integer, db.ForeignKey('m_component_template.component_template_id'), nullable=True)
    component_template = db.relationship('ComponentTemplate', back_populates='item_components', lazy='noload')
    doc_version = db.Column(db.Integer, nullable=False, default=0)
    versions = db.relationship(
        'ItemComponentVersion',
        back_populates='item_component',
        cascade='all, delete-orphan',
        order_by='ItemComponentVersion.version_no',
        lazy='noload',
    )
    edit_requests = db.relationship(
        'ComponentEditRequest',
        back_populates='item_component',
        cascade='all, delete-orphan',
        lazy='noload',
    )


class ItemComponentVersion(AuditMixin):
    """Immutable content snapshot of an ItemComponent, one row per real save.

    `ItemComponent.doc_version` points at the newest `version_no`. The snapshot
    columns are what the generated PDF for that version was rendered from —
    never re-read the live rows to reproduce an old version.
    """
    __tablename__ = "t_item_component_version"
    __table_args__ = (UniqueConstraint('item_component_id', 'version_no', name='uq_item_component_version_no'),)

    version_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)
    component_name = db.Column(db.String(255), nullable=False)
    remark = db.Column(db.String(255), nullable=True)
    img_url = db.Column(db.String(500), nullable=True)
    component_template_id = db.Column(db.Integer, db.ForeignKey('m_component_template.component_template_id'), nullable=True)
    template_name = db.Column(db.String(255), nullable=True)
    # template.sections as it stood when this version was saved — templates get edited
    sections_snapshot = db.Column(db.JSON, nullable=False, default=list)
    # [{"section_key":..., "section_type":..., "data":...}]
    section_data_snapshot = db.Column(db.JSON, nullable=False, default=list)
    # [{"material_list_id":..., "item_code":..., "item_name":..., "quantity_used":...}]
    material_usage_snapshot = db.Column(db.JSON, nullable=False, default=list)
    doc_ref_no = db.Column(db.String(120), nullable=True)
    doc_path = db.Column(db.String(500), nullable=True)
    change_reason = db.Column(db.String(500), nullable=True)
    # use_alter: t_component_edit_request points back at this table, so the FK
    # pair is circular and must be added after both tables exist.
    edit_request_id = db.Column(db.Integer, db.ForeignKey('t_component_edit_request.edit_request_id', ondelete='SET NULL', use_alter=True, name='fk_component_version_edit_request'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)

    item_component = db.relationship('ItemComponent', back_populates='versions', lazy='noload')
    edit_request = db.relationship('ComponentEditRequest', foreign_keys=[edit_request_id], lazy='noload')


class WorkRunComponentPin(AuditMixin, BranchScopedMixin):
    """Which component version a WorkRun is being built against — the as-built record.

    Append-only: re-pinning supersedes the previous row instead of updating it,
    so the full pin history of a run survives. Current pin per component is the
    row with `superseded_date IS NULL`.
    """
    __tablename__ = "t_work_run_component_pin"

    pin_id = db.Column(db.Integer, primary_key=True)
    work_run_id = db.Column(db.Integer, db.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False, index=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('t_item_component_version.version_id', ondelete='CASCADE'), nullable=False)
    version_no = db.Column(db.Integer, nullable=False)
    superseded_date = db.Column(db.DateTime, nullable=True)
    reason = db.Column(db.String(500), nullable=True)

    work_run = db.relationship('WorkRun', back_populates='component_pins', lazy='noload')
    item_component = db.relationship('ItemComponent', lazy='noload')
    version = db.relationship('ItemComponentVersion', lazy='noload')


class ComponentEditRequestStatus(enum.Enum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    CONSUMED = 'CONSUMED'
    CANCELLED = 'CANCELLED'


class ComponentEditRequest(AuditMixin):
    """Sales asks Production for permission to edit a component whose WorkOrder
    is already in production. An APPROVED request is single-use: the next save
    consumes it and flips it to CONSUMED."""
    __tablename__ = "t_component_edit_request"

    edit_request_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False, index=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'), nullable=False, index=True)
    base_version_no = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.Enum(ComponentEditRequestStatus), nullable=False, default=ComponentEditRequestStatus.PENDING, index=True)
    reviewed_by = db.Column(db.String(80), nullable=True)
    reviewed_date = db.Column(db.DateTime, nullable=True)
    review_remark = db.Column(db.String(500), nullable=True)
    consumed_version_id = db.Column(db.Integer, db.ForeignKey('t_item_component_version.version_id', ondelete='SET NULL'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)

    item_component = db.relationship('ItemComponent', back_populates='edit_requests', lazy='noload')
    work_order = db.relationship('WorkOrder', lazy='noload')
    consumed_version = db.relationship('ItemComponentVersion', foreign_keys=[consumed_version_id], lazy='noload')


class ComponentMaterialUsage(AuditMixin):
    __tablename__ = "t_component_material_usage"
    usage_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)
    quantity_used = db.Column(db.Double, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('m_branch.branch_id'), nullable=True, index=True)
    item_component = db.relationship("ItemComponent", back_populates="material_usages", lazy='noload')
    material_list = db.relationship("MaterialList", back_populates="component_usages")


class MaterialTransactionType(enum.Enum):
    INIT   = 'INIT'    # first stock entry when material arrives
    ADD    = 'ADD'     # additional stock added (positive amount)
    REMOVE = 'REMOVE'  # stock consumed/removed (negative amount)

class MaterialTransaction(AuditMixin):
    __tablename__ = "t_material_transaction"

    transaction_id = db.Column(db.Integer, primary_key=True)

    #ผูกกับตาราง t_material_list
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)

    amount = db.Column(db.Double, nullable=False)  # positive = in, negative = out
    type = db.Column(db.Enum(MaterialTransactionType), nullable=False)
    related_document_code = db.Column(db.String(128), nullable=False) # เอกสารที่อ้างอิง

    material_list = db.relationship('MaterialList', back_populates='transactions', lazy='noload')

# ---------------------------------------------------------------------------
# Picking Request
# ---------------------------------------------------------------------------

class PickingRequestStatus(enum.Enum):
    PENDING = 'PENDING'   # created, awaiting manual confirmation
    SENT    = 'SENT'      # sent to WMS (manually marked)
    SUCCESS = 'SUCCESS'   # WMS confirmed receipt
    FAILED  = 'FAILED'    # failed / cancelled

class PickingRequest(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_picking_request"
    picking_request_id   = db.Column(db.Integer, primary_key=True)
    picking_request_code = db.Column(db.String(100), nullable=True)
    doc_entry            = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry', ondelete='SET NULL'), nullable=True)
    status               = db.Column(db.Enum(PickingRequestStatus), nullable=False, default=PickingRequestStatus.PENDING)
    wms_reference        = db.Column(db.String(100), nullable=True)
    remark               = db.Column(db.String(500), nullable=True)

    items       = db.relationship('PickingRequestItem', back_populates='picking_request', cascade='all, delete-orphan')
    sales_order = db.relationship('SalesOrder', back_populates='picking_requests', lazy='noload')


class PickingRequestItem(AuditMixin, BranchScopedMixin):
    __tablename__ = "t_picking_request_item"
    picking_request_item_id = db.Column(db.Integer, primary_key=True)
    picking_request_id      = db.Column(db.Integer, db.ForeignKey('t_picking_request.picking_request_id', ondelete='CASCADE'), nullable=False)
    sales_item_id           = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='SET NULL'), nullable=True)
    material_list_id        = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True)
    order_line_num          = db.Column(db.Integer)
    item_code               = db.Column(db.String(100), nullable=False)
    item_name               = db.Column(db.String(255), nullable=False)
    quantity                = db.Column(db.Double, nullable=False)
    unit                    = db.Column(db.String(50), nullable=True)
    remark                  = db.Column(db.String(500), nullable=True)

    picking_request          = db.relationship('PickingRequest', back_populates='items', lazy='noload')
    sales_item               = db.relationship('SalesItem', back_populates='picking_request_items', lazy='noload')
    material_list            = db.relationship('MaterialList', lazy='noload')


class DocumentCodeList(BaseModel):
    __tablename__ = "m_document_code_list"
    document_code_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gen_number_type = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=True)

    gen_number_config = db.relationship('GenNumberConfig', back_populates='document_code', lazy='noload', uselist=False)


class GenNumberConfig(BaseModel):
    __tablename__ = "m_gen_number_config"
    gen_number_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gen_number_type = db.Column(db.String(50), nullable=False)
    gen_number_prefix = db.Column(db.String(20), nullable=True)
    gen_number_format = db.Column(db.String(100), nullable=False)
    gen_number_current = db.Column(db.Integer, nullable=False, default=0)
    year_buddhist = db.Column(db.Boolean, default=True)
    document_code_id = db.Column(db.Integer, db.ForeignKey('m_document_code_list.document_code_id'), nullable=True)

    document_code = db.relationship('DocumentCodeList', back_populates='gen_number_config', lazy='noload')


class OperationCostMonthly(AuditMixin):
    __tablename__ = "m_operation_cost_monthly"
    operation_cost_monthly_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operation_cost_date = db.Column(db.Date, nullable=False, default = bangkok_now)
    depreciation_building_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    depreciation_building_period = db.Column(db.Integer, nullable=False, default=0)
    depreciation_util_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    depreciation_util_period = db.Column(db.Integer, nullable=False, default=0)
    office_rent_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    office_supplies_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    water_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    electricity_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    utility_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    
class ComponentTemplate(AuditMixin):
    __tablename__ = "m_component_template"
    component_template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    sections = db.Column(db.JSON, nullable=False)
    item_components = db.relationship('ItemComponent', back_populates='component_template', lazy='noload')

class ComponentTemplateSectionData(AuditMixin):
    __tablename__ = "m_component_template_section_data"
    section_data_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section_type = db.Column(db.String(255), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    section_key = db.Column(db.String(255), nullable=False)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    item_component = db.relationship('ItemComponent', back_populates='component_template_sections', lazy='noload')
    # Per-instance override of the template's section-level "is_test_section" flag.
    # NULL means "inherit whatever the template section says" — only an explicit
    # True/False here overrides it. See item_component_service.resolve_test_section_keys
    # for the single source of truth on resolving this.
    is_test_section = db.Column(db.Boolean, nullable=True)

class PhaseTemplate(AuditMixin):
    __tablename__ = "m_phase_template"
    phase_template_id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    items = db.relationship('PhaseTemplateItem', back_populates='phase_template', cascade='all, delete-orphan', order_by='PhaseTemplateItem.sort_order', lazy='noload')

class PhaseTemplateItem(AuditMixin):
    __tablename__ = "m_phase_template_item"
    phase_template_item_id = db.Column(db.Integer, primary_key=True)
    phase_template_id = db.Column(db.Integer, db.ForeignKey('m_phase_template.phase_template_id', ondelete='CASCADE'), nullable=False)
    phase_name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    machine_type_id = db.Column(db.Integer, db.ForeignKey('m_machine_type.machine_type_id'), nullable=True)
    phase_template = db.relationship('PhaseTemplate', back_populates='items', lazy='noload')
    machine_type = db.relationship('MachineType', lazy='noload')


# ---------------------------------------------------------------------------
# Reports (mirrors tms-2 ADR-069). Definitions are code-defined and seeded;
# every execution is recorded as a ReportRun with file artefacts in MinIO.
# ---------------------------------------------------------------------------

class ReportRunStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class ReportDefinition(AuditMixin):
    """Reports catalogue. Each row mirrors a Python module under app/reports/{code}/.
    Seeded from REPORT_REGISTRY (see report_service.sync_definitions)."""
    __tablename__ = "m_report_definition"
    code = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(80), nullable=True)
    params_schema_json = db.Column(db.JSON, nullable=False)
    supported_formats = db.Column(db.JSON, nullable=False)
    definition_version = db.Column(db.Integer, nullable=False, default=1)


class ReportRun(BaseModel):
    """Audit record per report execution. File artefacts live in MinIO;
    presigned URLs are generated fresh at fetch time, never persisted."""
    __tablename__ = "t_report_run"
    run_id = db.Column(db.String(36), primary_key=True)
    definition_code = db.Column(
        db.String(80),
        db.ForeignKey('m_report_definition.code', ondelete='RESTRICT'),
        nullable=False,
    )
    definition_version = db.Column(db.Integer, nullable=False)
    params_json = db.Column(db.JSON, nullable=False)
    requested_by = db.Column(db.String(80), nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    status = db.Column(
        db.Enum(ReportRunStatus, values_callable=lambda x: [m.value for m in x]),
        nullable=False,
        default=ReportRunStatus.PENDING,
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    file_object_keys = db.Column(db.JSON, nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    result_json = db.Column(db.JSON, nullable=True)
    row_count = db.Column(db.Integer, nullable=True)
    runtime_ms = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.Index('ix_report_run_definition', 'definition_code'),
        db.Index('ix_report_run_requested', 'requested_at'),
        db.Index('ix_report_run_status', 'status'),
    )


class ItemDecodeSegment(AuditMixin):
    """Positional code-decoder legend value-map for decodable item categories
    (SLING, CHAIN). One row = one (category, segment, code) -> field/value pair.
    Refreshed wholesale by admin xlsx upload (replace-on-upload)."""
    __tablename__ = 'item_decode_segment'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(32), nullable=False)   # 'SLING' | 'CHAIN'
    segment = db.Column(db.String(8), nullable=False)     # '1-2','3-4','5-7','8','9','10-12'
    code = db.Column(db.String(8), nullable=False)        # e.g. 'RA','636','2','095'
    field = db.Column(db.String(32), nullable=False)      # 'type','brand','structure', etc.
    value = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('category', 'segment', 'code', 'field', name='uq_item_decode_segment'),
        db.Index('ix_item_decode_segment_lookup', 'category', 'segment', 'code'),
    )


class ItemReference(AuditMixin):
    """Flat Item No. -> Item Description lookup for non-decodable categories.
    Refreshed wholesale by admin xlsx upload (replace-on-upload)."""
    __tablename__ = 'item_reference'
    item_no = db.Column(db.String(64), primary_key=True)
    item_description = db.Column(db.String(500))