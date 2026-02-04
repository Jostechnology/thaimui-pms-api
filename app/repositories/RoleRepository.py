from app.app import db
from app.con_sqlalchemy import Permission, Role, Role_permission

def get_all_roles():
    try:
        roles = db.session.query(Role).all()
        return roles
    
    except Exception:
        raise

def get_role_by_id(id : int):
    try:
        role = db.session.query(Role).filter(Role.role_id == id).first()
        return role
    except Exception:
        raise

def get_active_permissions_by_role(role_id: int):
    try:
        return (
            db.session.query(Role_permission)
            .join(
                Permission,
                Permission.permission_id == Role_permission.permission_id
            )
            .with_entities(
                Role_permission.role_id,
                Role_permission.permission_id,
                Permission.module_id,
                Permission.method,
            )
            .filter(
                Role_permission.role_id == role_id,
                Role_permission.active_flag.is_(True)
            )
            .all()
        )
    except Exception:
        raise