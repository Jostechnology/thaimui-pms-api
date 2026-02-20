import enum
from app.app import db
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import event
from flask import g

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
class User(AuditMixin):
    __tablename__ = "m_user"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id', onupdate='CASCADE'), nullable=False, default=2) # default role_id = 2 (Default User)
    password = db.Column(db.String(200), nullable=False)
    role = db.relationship('Role', back_populates="users", lazy='selectin')
    is_active = db.Column(db.Boolean, nullable=False, default=True)


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
    users = db.relationship('User', back_populates="role", lazy='selectin')
    active_flag = db.Column(db.Boolean, nullable=False)
    permissions = db.relationship('Permission', secondary='m_role_permission', back_populates='roles', lazy='selectin')
    def get_permissions(self):
        if self.role_name == "Admin":
            return ["*"]
        return [perm.permission_code for perm in self.permissions]

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
        lazy='selectin',
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
    roles = db.relationship('Role', secondary='m_role_permission', back_populates='permissions', lazy='selectin')

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
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'

class WorkOrder(AuditMixin):
    __tablename__ = "t_work_order"
    work_order_id = db.Column(db.Integer, primary_key=True)
    doc_num = db.Column(db.Integer, nullable=False)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='work_orders', lazy='selectin')
    status = db.Column(db.Enum(WorkOrderStatus), nullable=False , default=WorkOrderStatus.READY)
    current_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id'))
    current_phase = db.relationship('WorkPhase', foreign_keys=[current_phase_id], post_update=True)
    sales_item = db.relationship(
        "SalesItem",
        back_populates="work_order",
        uselist=False
    )

class PhaseStatus(enum.Enum):
    PENDING = 'Pending'
    IN_PROGRESS = 'In Progress'
    PAUSED = 'Paused'
    COMPLETED = 'Completed'

class WorkPhase(AuditMixin):
    __tablename__ = "t_work_phase"
    work_phase_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id'), nullable=False)
    phase_name = db.Column(db.String(100), nullable=False)
    phase_status = db.Column(db.Enum(PhaseStatus), nullable=False , default=PhaseStatus.PENDING)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    employee_list = db.relationship('Employee', secondary='t_work_assignment', backref='work_phases', lazy='selectin')
    work_order = db.relationship('WorkOrder', foreign_keys=[work_order_id], backref='work_phases', lazy='selectin')
    breaks = db.relationship('WorkPhaseBreak', backref='work_phase', lazy='selectin', order_by='WorkPhaseBreak.break_start')

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
    UNEMPLOYED = 'Unemployed'
    ACTIVE = 'Active'
    ON_LEAVE = 'On Leave'
    SUSPENDED = 'Suspended'
    
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
    work_phase = db.relationship('WorkPhase', foreign_keys=[work_phase_id], backref=db.backref('assignments', overlaps='employee_list,work_phases'), lazy='selectin', overlaps='employee_list,work_phases')
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref=db.backref('assignments', overlaps='employee_list,work_phases'), lazy='selectin', overlaps='employee_list,work_phases')
class SalesItem(AuditMixin):
    __tablename__ = "t_sales_items"
    sales_item_id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), nullable=False)
    item_num = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    doc_num = db.Column(db.Integer, nullable=False)
    doc_entry = db.Column(db.Integer, db.ForeignKey('t_sales_order.doc_entry'))
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='sales_items', lazy='selectin')
    material_list = db.relationship('MaterialList', backref='sales_item', lazy='selectin')
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'))
    work_order = db.relationship('WorkOrder', foreign_keys=[work_order_id], back_populates='sales_item', lazy='selectin')

class MaterialList(AuditMixin):
    __tablename__ = "t_material_list"
    material_list_id = db.Column(db.Integer, primary_key=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'), nullable=False)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    item_num = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

class QCWorkOrder(AuditMixin):
    __tablename__ = "t_qc_work_order"
    qc_work_order_id = db.Column(db.Integer, primary_key=True)

class SalesOrder(AuditMixin):
    __tablename__ = "t_sales_order"
    doc_entry = db.Column(db.Integer, primary_key=True)
    doc_num = db.Column(db.Integer, nullable=False, unique=True)
    card_code = db.Column(db.String(20), nullable=False)
    card_name = db.Column(db.String(200), nullable=False)
    slp_code = db.Column(db.String(20), nullable=False)
    slp_name = db.Column(db.String(200), nullable=False)
    bpl_code = db.Column(db.String(20), nullable=False)
    bpl_name = db.Column(db.String(200), nullable=False)
    group_code = db.Column(db.String(20), nullable=False)
    group_name = db.Column(db.String(200), nullable=False)

    sales_items = db.relationship(
        "SalesItem",
        back_populates="sales_order",
        lazy='selectin'
    )
    work_orders = db.relationship(
        "WorkOrder",
        back_populates="sales_order",
        lazy='selectin'
    )

    