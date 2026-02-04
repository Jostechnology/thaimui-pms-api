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
    role_id = db.Column(db.Integer, default=0, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Tokenlist(BaseModel):
    __tablename__ = "t_token_list"
    id = db.Column(db.Integer, primary_key=True)
    jwt_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)  
    token_type = db.Column(db.String(20), default="refresh")