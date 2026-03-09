import enum
from app.app import db
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import event , Numeric
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
    current_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id'))
    current_phase = db.relationship('WorkPhase', foreign_keys=[current_phase_id], post_update=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id', ondelete='CASCADE'))
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], back_populates='work_order', lazy='selectin')
    item_components = db.relationship('ItemComponent', back_populates='work_order', lazy='selectin')

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
    sales_order = db.relationship('SalesOrder', foreign_keys=[doc_entry], back_populates='sales_items', lazy='selectin')
    material_list = db.relationship('MaterialList', backref='sales_item', lazy='selectin')
    work_order = db.relationship('WorkOrder', back_populates='sales_item', lazy='selectin', uselist=False)
    
    

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
    component_usages = db.relationship('ComponentMaterialUsage', back_populates='material_list', lazy='selectin')

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
    remark = db.Column(db.String(500), nullable=True)
    sales_item = db.relationship('SalesItem', foreign_keys=[sales_item_id], backref=db.backref('qc_work_orders', lazy='selectin'), lazy='selectin')
    qc_form = db.relationship('QCForm', uselist=False, backref='qc_work_order', cascade='all, delete-orphan', lazy='selectin')
    qc_items = db.relationship('QCItem', backref='qc_work_order', cascade='all, delete-orphan', lazy='selectin')


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


class QCItem(AuditMixin):
    """รายการสินค้าในใบสั่งงาน QC — 1-to-many กับ QCWorkOrder"""
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
    qc_work_order_id = db.Column(db.Integer, db.ForeignKey('t_qc_work_order.qc_work_order_id', ondelete='CASCADE'), nullable=False)
    qc_work_order = db.relationship('QCWorkOrder', foreign_keys=[qc_work_order_id], backref=db.backref('qc_certifications', lazy='selectin'), lazy='selectin')
    
    check_items = db.relationship('QCCheckItem', backref='certification', cascade='all, delete-orphan', lazy='selectin')


class QCCheckItem(AuditMixin):
    __tablename__ = "t_qc_check_item"
    test_id = db.Column(db.Integer, primary_key=True)
    
    # สิ่งที่เพิ่ม: 1. Foreign Key ผูกกับตารางแม่ (QCCertification)
    qc_certification_id = db.Column(db.Integer, db.ForeignKey('t_qc_certification.qc_certification_id', ondelete='CASCADE'), nullable=False)

    # ฟิลด์เก็บข้อมูลตามหน้า UI
    item_no = db.Column(db.String(50), nullable=True)       # ลำดับที่ เช่น "01", "02" (Frontend ส่งมา)
    test_number = db.Column(db.String(255), nullable=False) # เลข Test No. (ระบบรันให้)
    ref_number = db.Column(db.String(255), nullable=True)   # รหัสอ้างอิง (User กรอก)
    description = db.Column(db.Text, nullable=True)         # รายละเอียดสินค้าแบบยาวๆ (Frontend ส่งมา)
    wll = db.Column(db.Float, nullable=True)                # ค่า W.L.L.
    load_test = db.Column(db.Float, nullable=True)          # ค่า Load Test




  
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
class ItemComponent(AuditMixin):
    __tablename__ = "t_item_component"
    item_component_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id', ondelete='CASCADE'), nullable=False)
    work_order = db.relationship('WorkOrder', back_populates='item_components', lazy='selectin')
    material_usages = db.relationship(
        "ComponentMaterialUsage",
        back_populates="item_component",
    )
    component_name = db.Column(db.String(255), nullable=False)
    component_specs = db.relationship(
        "ComponentSpec",
        back_populates="item_component",
        lazy='selectin'
    )
    component_options = db.relationship(
        "ComponentOption",
        back_populates="item_component",
        lazy='selectin'
    )
    remark = db.Column(db.String(255), nullable=True)
    img_url = db.Column(db.String(500), nullable=True)


class ComponentMaterialUsage(AuditMixin):
    __tablename__ = "t_component_material_usage"
    usage_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    item_component = db.relationship("ItemComponent", back_populates="material_usages", lazy='selectin')
    material_list = db.relationship("MaterialList", back_populates="component_usages", lazy='selectin')

class ComponentSpecType(BaseModel):
    __tablename__ = "t_component_spec_type"
    component_spec_type_id = db.Column(db.Integer, primary_key=True)
    component_spec_type_name = db.Column(db.String(255), nullable=False)
    spec_type = db.Column(db.Enum('boolean', 'decimal', 'text'), nullable=False)
    component_specs = db.relationship(
        "ComponentSpec",
        back_populates="component_spec_type",
        lazy='selectin'
    )

class MaterialTransaction(AuditMixin):
    __tablename__ = "t_material_transaction"
    
    transaction_id = db.Column(db.Integer, primary_key=True)
    
    #ผูกกับตาราง t_material_list
    material_list_id = db.Column(db.Integer, db.ForeignKey('t_material_list.material_list_id', ondelete='CASCADE'), nullable=False)
    
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(24), nullable=False)  # "ADD" หรือ "REMOVE"
    related_document_code = db.Column(db.String(128), nullable=False) # เอกสารที่อ้างอิง

    # สร้าง Relationship ให้เชื่อมหากันได้ง่ายๆ
    material_list = db.relationship('MaterialList', backref=db.backref('transactions', lazy='selectin'))
class ComponentSpec(AuditMixin):
    __tablename__ = "t_component_spec"
    component_spec_id = db.Column(db.Integer, primary_key=True)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    component_spec_type_id = db.Column(db.Integer, db.ForeignKey('t_component_spec_type.component_spec_type_id', ondelete='CASCADE'), nullable=False)
    end_side = db.Column(db.Enum('top', 'bottom'), nullable=True)
    bool_value = db.Column(db.Boolean, nullable=True)
    decimal_value = db.Column(db.Numeric(10, 4), nullable=True)
    text_value = db.Column(db.String(255), nullable=True)
    item_component = db.relationship("ItemComponent", back_populates="component_specs", lazy='selectin')
    component_spec_type = db.relationship("ComponentSpecType", back_populates="component_specs", lazy='selectin')
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
        lazy='selectin'
    )

class ComponentOption(AuditMixin):
    __tablename__ = "t_component_option"
    component_option_id = db.Column(db.Integer, primary_key=True)
    component_option_type_id = db.Column(db.Integer, db.ForeignKey('t_component_option_type.component_option_type_id', ondelete='CASCADE'), nullable=False)
    item_component_id = db.Column(db.Integer, db.ForeignKey('t_item_component.item_component_id', ondelete='CASCADE'), nullable=False)
    component_option_type = db.relationship("ComponentOptionType", back_populates="component_options", lazy='selectin')
    item_component = db.relationship("ItemComponent", back_populates="component_options", lazy='selectin')
