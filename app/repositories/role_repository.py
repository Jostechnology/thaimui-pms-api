from app.app import db
from app.con_sqlalchemy import Permission, Role, RolePermission

def get_all_roles():
    try:
        roles = db.session.query(Role).all()
        return roles
    
    except Exception:
        raise


def create_role(role_data: dict):
    try:
        new_role = Role(
            role_code=role_data.get("role_code"),
            role_name=role_data.get("role_name"),
            description=role_data.get("description"),
            active_flag=role_data.get("active_flag", True)
        )
        db.session.add(new_role)
        db.session.commit()
        return new_role
    except Exception:
        db.session.rollback()
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