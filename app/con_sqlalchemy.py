import enum
from app.app import db
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.orm import with_loader_criteria
from sqlalchemy.orm import Session
from sqlalchemy import event , Numeric
from flask import g
from sqlalchemy import UniqueConstraint

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
    if execute_state.is_select and hasattr(g, "branch_id"):
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
    if not hasattr(g, "branch_id"):
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
                raise Exception("Unauthorized! ไม่ได้รับอนุญาตให้แก้ไขข้อมูลของสาขาอื่น")
                
    # ตอนลบข้อมูล (DELETE)
    for obj in session.deleted:
        if isinstance(obj, BranchScopedMixin):
            if obj.branch_id != g.branch_id:
                raise Exception("Unauthorized! ไม่ได้รับอนุญาตให้ลบข้อมูลของสาขาอื่น")

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

    branches = db.relationship('Branch', secondary=user_branch_mapping, back_populates='users')

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

class Branch(BaseModel):
    __tablename__ = 'm_branch'

    branch_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch_code = db.Column(db.String(20), unique=True, nullable=False)
    branch_name = db.Column(db.String(100), nullable=False) 

    users = db.relationship('User', secondary=user_branch_mapping, back_populates='branches')

class Module(BaseModel):
    __tablename__ = "m_module"
    module_id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(255), nullable=False)
    module_code = db.Column(db.String(20), nullable=False)
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


class RolePermission(BaseModel):
    __tablename__ = "m_role_permission"
    role_permission_id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('m_permission.permission_id'), nullable=False)
    active_flag = db.Column(db.Boolean, nullable=False)

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
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    status = db.Column(db.Enum(WorkOrderStatus), nullable=False , default=WorkOrderStatus.READY)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    current_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id'))
    current_phase = db.relationship('WorkPhase', foreign_keys=[current_phase_id], post_update=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'))
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='work_order')
    item_components = db.relationship('ItemComponent', back_populates='work_order')
    work_phases = db.relationship('WorkPhase', foreign_keys='WorkPhase.work_order_id', back_populates='work_order')

class PhaseStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    PAUSED = 'PAUSED'
    COMPLETED = 'COMPLETED'

class WorkPhase(AuditMixin):
    __tablename__ = "t_work_phase"
    work_phase_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id'), nullable=False)
    phase_name = db.Column(db.String(100), nullable=False)
    phase_status = db.Column(db.Enum(PhaseStatus), nullable=False , default=PhaseStatus.PENDING)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    work_order = db.relationship('WorkOrder', foreign_keys=[work_order_id], back_populates='work_phases', lazy='noload')
    breaks = db.relationship('WorkPhaseBreak', back_populates='work_phase', order_by='WorkPhaseBreak.break_start')
    assignments = db.relationship('WorkAssignment', back_populates='work_phase')

class BreakType(enum.Enum):
    LUNCHBREAK = "LUNCHBREAK"
    RESTBREAK = "RESTBREAK"
    OTHER = "OTHER"

class WorkPhaseBreak(AuditMixin):
    __tablename__ = "t_work_phase_break"
    break_id = db.Column(db.Integer, primary_key=True)
    work_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id', ondelete='CASCADE'), nullable=False)
    break_start = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    break_end = db.Column(db.DateTime, nullable=True)
    break_type = db.Column(db.Enum(BreakType), nullable=False, default=BreakType.OTHER)
    Remark = db.Column(db.String(255), nullable=True)
    work_phase = db.relationship('WorkPhase', back_populates='breaks', lazy='noload')


@event.listens_for(WorkPhaseBreak, 'before_insert', propagate=True)
def validate_break_remark_before_insert(mapper, connection, target):
    """Require `Remark` when `break_type` is 'Other'."""
    try:
        is_other = target.break_type == BreakType.OTHER
    except Exception:
        is_other = False
    if is_other:
        remark = getattr(target, 'Remark', None) or getattr(target, 'remark', None)
        if not remark or not str(remark).strip():
            # Allow missing remark for OTHER; set empty remark instead of raising
            try:
                if hasattr(target, 'Remark'):
                    target.Remark = ""
                else:
                    target.remark = ""
            except Exception:
                # Best effort: do not block insert if remark is missing
                pass


@event.listens_for(WorkPhaseBreak, 'before_update', propagate=True)
def validate_break_remark_before_update(mapper, connection, target):
    """Require `Remark` when `break_type` is 'OTHER' on updates."""
    try:
        is_other = target.break_type == BreakType.OTHER
    except Exception:
        is_other = False
    if is_other:
        remark = getattr(target, 'Remark', None) or getattr(target, 'remark', None)
        if not remark or not str(remark).strip():
            # Allow missing remark for OTHER on update; set empty remark instead of raising
            try:
                if hasattr(target, 'Remark'):
                    target.Remark = ""
                else:
                    target.remark = ""
            except Exception:
                pass

class EmployeeStatus(enum.Enum):
    UNEMPLOYED = 'UNEMPLOYED'
    ACTIVE = 'Active'
    ONLEAVE = 'ONLEAVE'
    SUSPENDED = 'SUSPENDED'

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
    salary_base = db.Column(db.Float, nullable=False, default=0.0)
    assignments = db.relationship('WorkAssignment', back_populates='employee', lazy='noload')

class EmployeeSalaryHistory(AuditMixin):
    __tablename__ = "t_employee_salary_history"
    salary_history_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)
    old_salary = db.Column(db.Float, nullable=False)
    new_salary = db.Column(db.Float, nullable=False)
    effective_date = db.Column(db.DateTime, nullable=False, default=bangkok_now)
    remark= db.Column(db.String(255), nullable=True)


class WorkAssignment(AuditMixin):
    __tablename__ = "t_work_assignment"
    work_assignment_id = db.Column(db.Integer, primary_key=True)
    work_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)
    work_phase = db.relationship('WorkPhase', foreign_keys=[work_phase_id], back_populates='assignments', lazy='noload')
    employee = db.relationship('Employee', foreign_keys=[employee_id], back_populates='assignments')

class SalesItemStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    COMPLETED = 'COMPLETED'

class SalesItem(AuditMixin):
    __tablename__ = "t_sales_items"
    sales_item_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(SalesItemStatus), nullable=False , default=SalesItemStatus.PENDING)
    item_code = db.Column(db.String(50), nullable=False)
    item_num = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    doc_num = db.Column(db.Integer, nullable=False)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='sales_items', lazy='noload')
    material_list = db.relationship('MaterialList', back_populates='sales_item')
    work_order = db.relationship('WorkOrder', back_populates='sales_item', uselist=False)
    qc_work_orders = db.relationship('QCWorkOrder', back_populates='sales_item')
    sales_item_transactions = db.relationship('SalesItemTransaction', back_populates='sales_item')
    
    @property
    def producing_qty(self):
        if self.work_order and self.work_order.status != WorkOrderStatus.COMPLETED:
            return self.work_order.quantity
        return 0

    @property
    def produced_qty(self):
        if self.work_order and self.work_order.status == WorkOrderStatus.COMPLETED:
            return self.work_order.quantity
        return 0

    @property
    def queued_for_test_qty(self):
        return sum(t.quantity for t in self.sales_item_transactions if t.type == SalesItemTransactionType.QUEUED_FOR_TEST)

    @property
    def tested_qty(self):
        return sum(t.quantity for t in self.sales_item_transactions if t.type == SalesItemTransactionType.TESTED)

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
    status = db.Column(db.Enum(MachineStatus), nullable=False, default=MachineStatus.IDLE)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
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
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    original_num = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    sales_item = db.relationship('SalesItem', back_populates='material_list', lazy='noload')
    component_usages = db.relationship('ComponentMaterialUsage', back_populates='material_list', lazy='noload')
    # Forward: used by remaining_num property and transaction_service
    transactions = db.relationship('MaterialTransaction', back_populates='material_list')

    @property
    def remaining_num(self):
        total_removed = sum(t.amount for t in self.transactions if t.type == 'REMOVE')
        total_added = sum(t.amount for t in self.transactions if t.type == 'ADD')
        return self.original_num - (total_removed - total_added)

class QCWorkOrderStatus(enum.Enum):
    PENDING = 'PENDING'
    INPROGRESS = 'INPROGRESS'
    PASSED = 'PASSED'
    FAILED = 'FAILED'

class QCWorkOrder(AuditMixin):
    __tablename__ = "t_qc_work_order"
    qc_work_order_id = db.Column(db.Integer, primary_key=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    qc_status = db.Column(db.Enum(QCWorkOrderStatus), nullable=False, default=QCWorkOrderStatus.PENDING)
    qc_date = db.Column(db.DateTime, nullable=True)
    qc_by = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    remark = db.Column(db.String(500), nullable=True)
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='qc_work_orders')
    qc_form = db.relationship('QCForm', uselist=False, back_populates='qc_work_order', cascade='all, delete-orphan')
    qc_items = db.relationship('QCItem', back_populates='qc_work_order', cascade='all, delete-orphan')
    test_results = db.relationship('TestResult', back_populates='qc_work_order', cascade='all, delete-orphan')


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

    qc_work_order = db.relationship('QCWorkOrder', back_populates='qc_form', lazy='noload')


class QCItem(AuditMixin):
    """รายการ material ในใบสั่งงาน QC"""
    __tablename__ = "t_qc_item"
    qc_item_id       = db.Column(db.Integer, primary_key=True)
    qc_work_order_id = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='CASCADE'), nullable=False)
    item_order       = db.Column(db.Integer, nullable=True)
    item_code        = db.Column(db.String(100), nullable=True)
    description      = db.Column(db.Text, nullable=True)
    wll              = db.Column(db.String(50), nullable=True)
    quantity         = db.Column(db.String(50), nullable=True)
    serial_no        = db.Column(db.String(200), nullable=True)
    item_remark      = db.Column(db.String(500), nullable=True)
    qc_work_order = db.relationship('QCWorkOrder', back_populates='qc_items', lazy='noload')


class TestResultStatus(enum.Enum):
    PASSED = 'PASSED'
    FAILED = 'FAILED'


class TestResult(AuditMixin):
    """บันทึกการทดสอบจริง — 1 QCWorkOrder มีได้หลาย TestResult (กรณีทดสอบซ้ำ)"""
    __tablename__ = "t_test_result"
    test_result_id    = db.Column(db.Integer, primary_key=True)
    qc_work_order_id  = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='CASCADE'), nullable=False)
    test_date         = db.Column(db.DateTime, nullable=True, default=bangkok_now)
    tested_by         = db.Column(db.String(100), nullable=True)
    test_method       = db.Column(db.String(255), nullable=True)
    standard_reference = db.Column(db.String(255), nullable=True)
    overall_status    = db.Column(db.Enum(TestResultStatus), nullable=False, default=TestResultStatus.PASSED)
    remark            = db.Column(db.String(500), nullable=True)
    test_result_items = db.relationship('TestResultItem', back_populates='test_result', cascade='all, delete-orphan')
    # Kept as lazy='select': test_result_service navigates test_result.qc_work_order.sales_item
    qc_work_order = db.relationship('QCWorkOrder', back_populates='test_results')


class TestResultItem(AuditMixin):
    """ผลการทดสอบรายหน่วย — 1 row ต่อ 1 ชิ้นที่ทดสอบ (quantity ของ SalesItem)"""
    __tablename__ = "t_test_result_item"
    test_result_item_id = db.Column(db.Integer, primary_key=True)
    test_result_id      = db.Column(db.Integer, db.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False)
    unit_number         = db.Column(db.Integer, nullable=False)  # ลำดับชิ้น เช่น 1, 2, ...
    serial_no           = db.Column(db.String(200), nullable=True)
    wll_measured        = db.Column(db.Float, nullable=True)
    load_test_value     = db.Column(db.Float, nullable=True)
    description         = db.Column(db.Text, nullable=True)
    result              = db.Column(db.Enum(TestResultStatus), nullable=False, default=TestResultStatus.PASSED)
    remark              = db.Column(db.String(500), nullable=True)
    test_result = db.relationship('TestResult', back_populates='test_result_items', lazy='noload')

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

class SalesOrder(AuditMixin):
    __tablename__ = "t_sales_order"
    doc_entry = db.Column(db.Integer, primary_key=True)
    doc_num = db.Column(db.Integer, nullable=False, unique=True)
    card_code = db.Column(db.String(20), nullable=False)
    card_name = db.Column(db.String(200), nullable=False)
    po_number = db.Column(db.String(100), nullable=True)
    slp_code = db.Column(db.String(20), nullable=False)
    slp_name = db.Column(db.String(200), nullable=False)
    bpl_code = db.Column(db.String(20), nullable=False)
    bpl_name = db.Column(db.String(200), nullable=False)
    group_code = db.Column(db.String(20), nullable=False)
    group_name = db.Column(db.String(200), nullable=False)

    sales_items = db.relationship(
        "SalesItem",
        back_populates="sales_order",
    )
    certifications = db.relationship('QCCertification', back_populates='sales_order')

class ItemComponent(AuditMixin):
    __tablename__ = "t_item_component"
    item_component_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'), nullable=False)
    work_order = db.relationship('WorkOrder', back_populates='item_components', lazy='noload')
    material_usages = db.relationship(
        "ComponentMaterialUsage",
        back_populates="item_component",
    )
    component_name = db.Column(db.String(255), nullable=False)
    component_specs = db.relationship(
        "ComponentSpec",
        back_populates="item_component",
    )
    component_options = db.relationship(
        "ComponentOption",
        back_populates="item_component",
    )
    remark = db.Column(db.String(255), nullable=True)
    img_url = db.Column(db.String(500), nullable=True)


class ComponentMaterialUsage(AuditMixin):
    __tablename__ = "t_component_material_usage"
    usage_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    item_component = db.relationship("ItemComponent", back_populates="material_usages", lazy='noload')
    material_list = db.relationship("MaterialList", back_populates="component_usages")

class ComponentSpecType(BaseModel):
    __tablename__ = "t_component_spec_type"
    component_spec_type_id = db.Column(db.Integer, primary_key=True)
    component_spec_type_name = db.Column(db.String(255), nullable=False)
    spec_type = db.Column(db.Enum('boolean', 'decimal', 'text'), nullable=False)
    component_specs = db.relationship(
        "ComponentSpec",
        back_populates="component_spec_type",
        lazy='noload'
    )

class MaterialTransaction(AuditMixin):
    __tablename__ = "t_material_transaction"

    transaction_id = db.Column(db.Integer, primary_key=True)

    #ผูกกับตาราง t_material_list
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)

    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(24), nullable=False)  # "ADD" หรือ "REMOVE"
    related_document_code = db.Column(db.String(128), nullable=False) # เอกสารที่อ้างอิง

    material_list = db.relationship('MaterialList', back_populates='transactions', lazy='noload')

class SalesItemTransactionType(enum.Enum):
    PRODUCED = 'PRODUCED'
    QUEUED_FOR_TEST = 'QUEUED_FOR_TEST'
    TESTED = 'TESTED'

class SalesItemTransaction(AuditMixin):
    __tablename__ = "t_sales_item_transaction"

    transaction_id = db.Column(db.Integer, primary_key=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.Enum(SalesItemTransactionType), nullable=False)
    related_document_code = db.Column(db.String(128), nullable=False)

    sales_item = db.relationship('SalesItem', back_populates='sales_item_transactions', lazy='noload')

class ComponentSpec(AuditMixin):
    __tablename__ = "t_component_spec"
    component_spec_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    component_spec_type_id = db.Column(db.Integer, db.ForeignKey('t_component_spec_type.component_spec_type_id', ondelete='CASCADE'), nullable=False)
    end_side = db.Column(db.Enum('top', 'bottom'), nullable=True)
    bool_value = db.Column(db.Boolean, nullable=True)
    decimal_value = db.Column(db.Numeric(10, 4), nullable=True)
    text_value = db.Column(db.String(255), nullable=True)
    item_component = db.relationship("ItemComponent", back_populates="component_specs", lazy='noload')
    component_spec_type = db.relationship("ComponentSpecType", back_populates="component_specs")
    __table_args__ = (
        db.UniqueConstraint(
            'item_component_id',
            'component_spec_type_id',
            'end_side',
            name='uq_item_component_spec'
        ),
    )

class ComponentOptionType(BaseModel):
    __tablename__ = "t_component_option_type"
    component_option_type_id = db.Column(db.Integer, primary_key=True)
    component_option_type_name = db.Column(db.String(255), nullable=False)
    component_options = db.relationship(
        "ComponentOption",
        back_populates="component_option_type",
        lazy='noload'
    )

class ComponentOption(AuditMixin):
    __tablename__ = "t_component_option"
    component_option_id = db.Column(db.Integer, primary_key=True)
    component_option_type_id = db.Column(db.Integer, db.ForeignKey('t_component_option_type.component_option_type_id', ondelete='CASCADE'), nullable=False)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    component_option_type = db.relationship("ComponentOptionType", back_populates="component_options")
    item_component = db.relationship("ItemComponent", back_populates="component_options", lazy='noload')
