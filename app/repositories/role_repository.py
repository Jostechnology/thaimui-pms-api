from app.app import db
from app.con_sqlalchemy import Module, Permission, Role, RolePermission, User

def get_all_roles():
    try:
        roles = db.session.query(Role).all()
        return roles
    
    except Exception:
        raise


def create_role(role):
    try:
        db.session.add(role)
        db.session.flush()
        return role
    except Exception:
        db.session.rollback()
        raise
    

def get_role_by_id(id : int):
    try:
        role = db.session.query(Role).filter(Role.role_id == id).first()
        return role
    except Exception:
        raise

def check_user_has_permission(user_id: int, module_code: str, method: str) -> bool:
    try:
        query = (
            db.session.query(RolePermission)
            .join(User, User.role_id == RolePermission.role_id)
            .join(Permission, Permission.permission_id == RolePermission.permission_id)
            .join(Module, Module.module_id == Permission.module_id)
            .filter(
                User.user_id == user_id,
                Module.module_code == module_code,
                Permission.method == method,
                RolePermission.active_flag.is_(True)
            )
        )
        return query.first() is not None
    except Exception:
        raise

def get_active_permissions_by_role(role_id: int):
    try:
        return (
            db.session.query(RolePermission)
            .join(
                Permission,
                Permission.permission_id == RolePermission.permission_id
            )
            .with_entities(
                RolePermission.role_id,
                RolePermission.permission_id,
                Permission.module_id,
                Permission.method,
            )
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.active_flag.is_(True)
            )
            .all()
        )
    except Exception:
        raise