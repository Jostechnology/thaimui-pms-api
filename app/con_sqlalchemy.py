from app.app import db
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

def bangkok_now():
    return datetime.now(ZoneInfo("Asia/Bangkok"))

class BaseModel(db.Model):
    __abstract__ = True
    created_date = db.Column(db.DateTime, default=bangkok_now)
    updated_date = db.Column(db.DateTime, default=bangkok_now, onupdate=bangkok_now)

class AuditMixin(BaseModel):
    """Mixin to add created_by and updated_by tracking"""
    __abstract__ = True
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)

class User(AuditMixin):
    __tablename__ = "m_user"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id', onupdate='CASCADE'), nullable=False, default=2) # default role_id = 2 (Default User)
    password = db.Column(db.String(200), nullable=False)
    role = db.relationship('Role', back_populates="users", lazy='selectin')

class Tokenlist(BaseModel):
    _tablename_ = "t_token_list"
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

class Module(db.Model):
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

class Permission(db.Model):
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


class Role_permission(db.Model):
    __tablename__ = "m_role_permission"
    role_permission_id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('m_permission.permission_id'), nullable=False)
    active_flag = db.Column(db.Boolean, nullable=False)