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
    tablename = "t_token_list"
    id = db.Column(db.Integer, primary_key=True)
    jwt_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    token_type = db.Column(db.String(20), default="refresh")


class Tokenlist(BaseModel):
    __tablename__ = "t_token_list"
    id = db.Column(db.Integer, primary_key=True)
    jwt_id = db.Column(db.String(255), unique=True, nullable=False)

class Role(BaseModel):
    __tablename__ = "m_role"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200))
    users = db.relationship('User', back_populates="role", lazy='selectin')
    permissions = db.relationship('Permission', secondary='m_role_permission', back_populates='roles', lazy='selectin')
    def get_permissions(self):
        if self.role_name == "Admin":
            return ["*"]
        return [perm.permission_code for perm in self.permissions]

class Permission(BaseModel):
    __tablename__ = "m_permission"
    permission_id = db.Column(db.Integer, primary_key=True)
    permission_code = db.Column(db.String(80), unique=True, nullable=False)
    permission_group = db.Column(db.String(80), nullable=False)
    roles = db.relationship('Role', secondary='m_role_permission', back_populates='permissions', lazy='selectin')

class RolePermission(BaseModel):
    __tablename__ = "m_role_permission"
    role_id = db.Column(db.Integer, db.ForeignKey('m_role.role_id'), primary_key=True, nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('m_permission.permission_id'), primary_key=True, nullable=False)

