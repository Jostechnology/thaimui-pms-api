from app.con_sqlalchemy import Module, Permission, RolePermission
from app.app import db
from sqlalchemy import desc, tuple_

def get_all_modules():
    try:
        modules = db.session.query(Module).order_by(Module.level, Module.sort_order).all()
        return modules
    except Exception:
        raise

def get_module_id_code_map():
    """Returns dict {module_id: module_code} for all modules."""
    try:
        query = db.session.query(Module.module_id, Module.module_code)
        return {row.module_id: row.module_code for row in query.all()}
    except Exception:
        raise

def get_permissions_of_module(module : Module):
    try:
        permissions = db.session.query(Permission).filter(Permission.module_id == module.module_id).all()
        return permissions
    except Exception:
        raise

def get_module_highest_order():
    try:
        module = db.session.query(Module).filter(Module.level == 1).order_by(desc(Module.sort_order)).first()
        return module
    except Exception:
        raise

def get_module_by_code(module_code):
    try:
        module = db.session.query(Module).filter(Module.module_code == module_code).first()
        return module
    except Exception:
        raise

def get_module_by_id(module_id):
    try:
        module = db.session.query(Module).filter(Module.module_id == module_id).first()
        return module
    except Exception:
        raise

def create_module(data):
    try:
        print(data)
        module_name = data.get("module_name")
        module_code = data.get("module_code")
        sort_order = data.get("sort_order")
        parent_id = data.get("parent_id")
        level = data.get("level")
        new_module = Module(
            module_name=module_name,
            module_code=module_code,
            sort_order=sort_order,
            parent_id=parent_id,
            level=level
        )

        return new_module
    except Exception:
        raise

def create_permission(data):
    try:
        permission_code = data.get("permission_code")
        description = data.get("description")
        module_id = data.get("module_id")
        method = data.get("method")

        new_permission = Permission(
            permission_code=permission_code,
            description=description,
            module_id=module_id,
            method=method
        )

        return new_permission
    except Exception:
        raise

def get_main_modules():
    try:
        modules =db.session.query(Module).filter(Module.level == 1).order_by(Module.sort_order).all()
        return modules
    except Exception:
        raise

def get_sub_module_hightest(module_id):
    try:
        module = db.session.query(Module).filter(Module.level != 1, Module.parent_id == module_id).order_by(desc(Module.sort_order)).first()
        return module
    except Exception:
        raise

def deactivate_role_permission_of_role(role_id):
    try:
        role_permissions = db.session.query(RolePermission).filter(RolePermission.role_id == role_id).all()
        for rp in role_permissions:
            rp.active_flag = False
    
    except Exception:
        raise

def get_role_permission_of_role_and_permission(role_id, permission_id):
    try:
        role_permission = db.session.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id).first()
        return role_permission
    except Exception:
        raise

def create_role_permission(data):
    try:
        role_id = data.get("role_id")
        permission_id = data.get("permission_id")
        role_permission = RolePermission(
            role_id=role_id, permission_id=permission_id, active_flag=True
        )
        return role_permission
    except Exception:
        raise

def update_module(module, data):
    try:
        if data.get("module_name"):
            module.module_name = data.get("module_name")
        if data.get("module_code"):
            module.module_code = data.get("module_code")
        if data.get("sort_order") is not None:
            module.sort_order = data.get("sort_order")
        if data.get("parent_id") is not None:
            module.parent_id = data.get("parent_id")
        if data.get("level") is not None:
            module.level = data.get("level")
        return module
    except Exception:
        raise

def delete_module_by_id(module_id):
    try:
        module = db.session.query(Module).filter(Module.module_id == module_id).first()
        sub_module = db.session.query(Module).filter(Module.parent_id == module_id).all()
        for sm in sub_module:
            db.session.delete(sm)
        if module:
            db.session.delete(module)
        return module
    except Exception:
        raise

def delete_permissions_by_module(module_id):
    try:
        permissions = db.session.query(Permission).filter(Permission.module_id == module_id).all()
        for p in permissions:
            db.session.delete(p)
        return permissions
    except Exception:
        raise

def get_permission_by_module(module_id, method):
    try:
        permission = Permission.query.filter_by(
            module_id=module_id, method=method
        ).first()
        return permission
    except Exception as e:
        raise e

def get_permissions_by_module_method_pairs(pairs):
    """Batch fetch permissions for a list of (module_id, method) pairs. Returns list of Permission."""
    try:
        if not pairs:
            return []
        query = db.session.query(Permission).filter(
            tuple_(Permission.module_id, Permission.method).in_(pairs)
        )
        return query.all()
    except Exception:
        raise

def get_role_permissions_by_role(role_id):
    """Fetch all RolePermission rows for a role. Returns list."""
    try:
        query = db.session.query(RolePermission).filter(RolePermission.role_id == role_id)
        return query.all()
    except Exception:
        raise

def get_all_role_permission():
    try:
        role_permissions = db.session.query(RolePermission).all()
        return role_permissions
    except Exception:
        raise
