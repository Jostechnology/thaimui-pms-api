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

class WorkOrder(AuditMixin):
    __tablename__ = "t_work_order"
    work_order_id = db.Column(db.Integer, primary_key=True)
    doc_num = db.Column(db.String(50), nullable=False)

class WorkPhase(AuditMixin):
    __tablename__ = "t_work_phase"
    work_phase_id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('t_work_order.work_order_id'), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)

class Employee(AuditMixin):
    __tablename__ = "m_employee"
    employee_id = db.Column(db.Integer, primary_key=True)
    salary = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('m_user.user_id'), nullable=False)

class WorkAssignment(AuditMixin):
    __tablename__ = "t_work_assignment"
    work_assignment_id = db.Column(db.Integer, primary_key=True)
    work_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('m_employee.employee_id'), nullable=False)

class SalesItem(AuditMixin):
    __tablename__ = "t_sales_items"
    sales_item_id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), nullable=False)
    item_num = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    doc_num = db.Column(db.String(50), nullable=False)

class WorkItem(AuditMixin):
    __tablename__ = "t_work_items"
    work_item_id = db.Column(db.Integer, primary_key=True)
    work_phase_id = db.Column(db.Integer, db.ForeignKey('t_work_phase.work_phase_id'), nullable=False)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id'), nullable=False)

class MaterialList(AuditMixin):
    __tablename__ = "t_material_list"
    material_list_id = db.Column(db.Integer, primary_key=True)
    sales_item_id = db.Column(db.Integer, db.ForeignKey('t_sales_items.sales_item_id'), nullable=False)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500))
    item_num = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)