import base64
import json
from app.app import db
from app.exception import AppException, MissingFieldsError, NotFoundError, UniqueError
from app.con_sqlalchemy import Role
from app.repositories import module_repository, role_repository, user_repository, branch_repository
from app.ma_sqlalchemy import GetPermissionSchema, GetRolePremissionSchema, ModuleSchema, RolePermissionSchema, RoleSchema
from app.utils import encode_jwt , hash_bcrypt, verify_bcrypt


def check_user_permission(user_id: int, module_code: str, action: str) -> bool:
    try:
        if not user_id or not module_code or not action:
            raise MissingFieldsError("Missing user_id, module_code, or action")
        return role_repository.check_user_has_permission(user_id, module_code, action)
    except AppException:
        raise
    except Exception as e:
        raise AppException(str(e))


def create_role(role_data: dict):
    try:
        new_role = Role(
            role_code=role_data.get("role_code"),
            role_name=role_data.get("role_name"),
            description=role_data.get("description"),
            active_flag=role_data.get("active_flag", True)
        )
        new_role = role_repository.create_role(new_role)
        
        # Add permissions
        module_list = role_data.get("module_list", [])
        if module_list:
            upsert_data = {
                "role_id": new_role.role_id,
                "module_list": module_list
            }
            upsert_role_permission(upsert_data)

        db.session.commit()
        return RoleSchema().dump(new_role)
    except Exception as e:
        db.session.rollback()
        raise e


def get_all_roles():
    try:
        roles = role_repository.get_all_roles()
        sche = RoleSchema(many=True)
        return sche.dump(roles)
    except Exception as e:
        raise e

def get_module_tree():
    try:
        modules = module_repository.get_all_modules()
        module_dict = {}
        for mod in modules:
            if mod.level == 1:
                perm_query = module_repository.get_permissions_of_module(mod)
                perm_res = GetPermissionSchema(many=True).dump(perm_query)
                perm_ls = []
                for perm in perm_res:
                    perm_ls.append(perm.get("method"))

                module_dict[mod.module_id] = {
                    "module_id": mod.module_id,
                    "module_name": mod.module_name,
                    "module_code": mod.module_code,
                    "sub_modules": [],
                    "permission": perm_ls,
                    "sort_order": mod.sort_order,
                }
            elif mod.level == 2 and mod.parent_id in module_dict:
                perm_query = module_repository.get_permissions_of_module(mod)
                perm_res = GetPermissionSchema(many=True).dump(perm_query)
                perm_ls = []
                for perm in perm_res:
                    perm_ls.append(perm.get("method"))
                module_dict[mod.parent_id]["sub_modules"].append(
                    {
                        "module_id": mod.module_id,
                        "module_name": mod.module_name,
                        "module_code": mod.module_code,
                        "permission": perm_ls,
                        "sort_order": mod.sort_order,
                    }
                )
        return list(module_dict.values())
    except Exception as e:
        raise e

def get_role_permission(username, role_id):
    try:

        role_permission = role_repository.get_active_permissions_by_role(role_id)
        if not role_permission:
            role_permission = []

        schema = GetRolePremissionSchema(many=True)
        result = schema.dump(role_permission)
        module_code_map = module_repository.get_module_id_code_map()

        # Flat list of granted permissions: ["MODULE_CODE.method", ...]
        flat_permissions = [
            f"{module_code_map[r['module_id']]}.{r['method']}"
            for r in result
            if r.get("module_id") in module_code_map and r.get("method")
        ]
        
        data_bytes = json.dumps(flat_permissions).encode("utf-8")
        permission_tree_b64 = base64.b64encode(data_bytes).decode("utf-8")

        payload = {
            "signed_permission_tree": permission_tree_b64
        }

        token = encode_jwt(payload)

        # signature = private_key.sign(
        #     data_bytes,
        #     asym_padding.PSS(mgf=asym_padding.MGF1(hashes.SHA256()), salt_length=asym_padding.PSS.MAX_LENGTH),
        #     hashes.SHA256()
        # )
        return (
            base64.b64encode(data_bytes).decode("utf-8"),
            token
        )

    except Exception as e:
        raise e
    
def create_module(data):
    try:
        module_name = data.get("module_name")
        module_code = data.get("module_code")
        sort_order = data.get("sort_order", 0)
        parent_id = data.get("parent_id")  # เพิ่ม parent_id สำหรับ sub-module
        level = data.get("level", 1)  # default เป็น main module
        permssion_list = data.get("permission_list", [])
        create_permission_list = []

        if level == 1 and sort_order == 0:
            sort_order = module_repository.get_module_highest_order()
            sort_order = sort_order.sort_order + 1 if sort_order else 1

        if not module_name or not module_code:
            raise MissingFieldsError("Missing module_name or module_code")

        existing = module_repository.get_module_by_code(module_code)
        if existing:
            raise UniqueError("Module Already exists")
        

        if parent_id:
            parent = module_repository.get_module_by_id(parent_id)
            if not parent:
                raise NotFoundError("Parent module not found")

        create_obj = {
            "module_name" : module_name,
            "module_code" : module_code,
            "sort_order" : sort_order,
            "parent_id" : parent_id,
            "level" : level,
        }

        new_module = module_repository.create_module(create_obj)
        db.session.add(new_module)
        db.session.flush()
        per_view = "view."
        dec_view = "View "
        if not permssion_list:
            permission_code = per_view+ data.get("module_code")
            description = dec_view+ data.get("module_name")
            permiss_dict = {
                "permission_code": permission_code,
                "description": description,
                "module_id": new_module.module_id,
                "method": "view",
            }
            create_permission_list.append(permiss_dict)
        else:
            for pl in permssion_list:
                if pl == "view":
                    permission_code = per_view+ data.get("module_code")
                    description = dec_view+ data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "view",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "create":
                    permission_code = "create." + data.get("module_code")
                    description = "Create " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "create",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "edit":
                    permission_code = "edit." + data.get("module_code")
                    description = "Edit " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "edit",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "delete":
                    permission_code = "delete." + data.get("module_code")
                    description = "Delete " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "delete",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "export":
                    permission_code = "export." + data.get("module_code")
                    description = "Export " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "export",
                    }
                    create_permission_list.append(permiss_dict)

        for perm in create_permission_list:
            permission = module_repository.create_permission(perm)
            db.session.add(permission)

        db.session.commit()

        return ModuleSchema().dump(new_module)
    except Exception as e:
        db.session.rollback()
        raise e
    
def edit_module(module_id,data):
    try:
        module = module_repository.get_module_by_id(module_id)
        if not module:
            return {"error": "Module not found"}, 404

        module_name = data.get("module_name")
        module_code = data.get("module_code")
        sort_order = data.get("sort_order", module.sort_order)
        permission_list = data.get("permission_list", [])

        if not module_name or not module_code:
            raise MissingFieldsError("Missing module_name or module_code")

        existing = module_repository.get_module_by_code(module_code)
        if existing and existing.module_id != module_id:
            raise UniqueError("Module code already exists")

        module.module_name = module_name
        module.module_code = module_code
        module.sort_order = sort_order

        # Update permissions: diff-based (keep existing, delete removed, add new)
        existing_permissions = module_repository.get_permissions_of_module(module)
        new_methods = set(permission_list) if permission_list else set()

        # ลบ permission ที่ไม่อยู่ใน list ใหม่
        for perm in existing_permissions:
            if perm.method not in new_methods:
                db.session.delete(perm)
            else:
                # อัปเดต code/description ให้ตรงกับชื่อ module ใหม่
                perm.permission_code = f"{perm.method}.{module_code}"
                perm.description = f"{perm.method.capitalize()} {module_name}"
                new_methods.discard(perm.method)

        # สร้างเฉพาะ permission ที่ยังไม่มี
        valid_methods = {"view", "create", "edit", "delete"}
        for method in new_methods:
            if method not in valid_methods:
                continue
            permiss_dict = {
                "permission_code": f"{method}.{module_code}",
                "description": f"{method.capitalize()} {module_name}",
                "module_id": module.module_id,
                "method": method,
            }
            new_permission = module_repository.create_permission(permiss_dict)
            db.session.add(new_permission)

        db.session.commit()

        return ModuleSchema().dump(module)
    except Exception as e:
        db.session.rollback()
        raise e

def delete_module(module_id):
    try:
        module = module_repository.get_module_by_id(module_id)
        if not module:
            raise NotFoundError("Module not found")

        module_repository.delete_module_by_id(module_id)
        db.session.commit()

        return {"message": "Module deleted successfully"}
    except Exception as e:
        db.session.rollback()
        raise e

    
def get_module(module_id):
    try:
        module = module_repository.get_module_by_id(module_id)
        if not module:
            raise NotFoundError("ไม่พบ Module")
        return ModuleSchema().dump(module)
    except Exception as e:
        raise e

def get_modules_main():
    try:
        modules = module_repository.get_main_modules()
        return ModuleSchema(many=True).dump(modules)
    except Exception as e:
        raise e
    
def get_module_sorted(module_id):
    try:
        module = module_repository.get_sub_module_hightest(module_id)
        if not module:
            return 0
        return module.sort_order
    except Exception as e:
        raise e

def update_role_permissions(role_id, permission_ids):
    try:
        module_repository.deactivate_role_permission_of_role()

        for pid in permission_ids:
            rp = module_repository.get_role_permission_of_role_and_permission(role_id, pid)
            if rp:
                rp.active_flag = True
            else:
                create_obj = {
                    "role_id" : role_id,
                    "permission_id" : pid
                }
                new_rp = module_repository.create_role_permission(create_obj)
                db.session.add(new_rp)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise e
    
def upsert_role_permission(data):
    try:
        role_id = data.get("role_id")
        module_list = data.get("module_list")

        if not role_id or not isinstance(module_list, list):
            raise MissingFieldsError("Missing role_id or module_list")

        # Batch fetch all permissions in one query instead of N queries
        pairs = [
            (m.get("module_id"), m.get("method"))
            for m in module_list
            if m.get("module_id") and m.get("method")
        ]
        permissions = module_repository.get_permissions_by_module_method_pairs(pairs)
        permission_id_set = {p.permission_id for p in permissions if p.permission_id is not None}

        module_repository.deactivate_role_permission_of_role(role_id)

        # Batch fetch existing RolePermission rows in one query
        existing_rps = module_repository.get_role_permissions_by_role(role_id)
        existing_map = {rp.permission_id: rp for rp in existing_rps}

        for pid in permission_id_set:
            if pid in existing_map:
                existing_map[pid].active_flag = True
            else:
                new_rp = module_repository.create_role_permission({"role_id": role_id, "permission_id": pid})
                db.session.add(new_rp)

        db.session.commit()

        updated = module_repository.get_all_modules()
        return RolePermissionSchema(many=True).dump(updated)

    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))

def create_user(data):
    try:
        username = data.get("username")
        password = data.get("password")
        role_id = data.get("role_id")
        if not username or not password:
            raise MissingFieldsError("Missing username, password, or role_id")

        if user_repository.check_username_exist(username):
            raise UniqueError("User already Exists")

        hashed_password = hash_bcrypt(password)

        create_obj = {
            "username" : username,
            "password" : hashed_password,
            "role_id" :  role_id
        }

        new_user = user_repository.create_user(create_obj)
        db.session.add(new_user)
        db.session.commit()

        return user_repository.get_user_by_id(new_user.user_id).username
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))


def get_user_list(data):
    try:
        page = int(data.get("page", 1))
        per_page = int(data.get("per_page", 10))
        username = data.get("search", "")
        role_id = data.get("filter")

        result = user_repository.get_user_list_paginated(
            page=page,
            limit=per_page,
            username=username, 
            role_id=role_id
        )
        items = []
        for user in result['items']:
            branch_ids = [b.branch_id for b in user.branches]
            branch_names = [b.branch_name for b in user.branches]

            items.append({
                "username": user.username,
                "role_id": user.role_id,
                "role_name": user.role.role_name if user.role else "-",
                "created_date": user.created_date.strftime("%Y-%m-%d %H:%M:%S") if user.created_date else "-",
                "is_active": user.is_active,
                "branch_ids": branch_ids,
                "branch_names": branch_names
            })
        return {
            "items": items,
            "total": result["total"],
            "page": result["page"],
            "pages": result["pages"],
        }

    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))
    
def change_user_role(data):
    try:
        username = data.get("username")
        role_id = data.get("role_id")
        update_by = data.get("update_by")

        user = user_repository.get_user_by_username(username)
        if not user:
            raise NotFoundError("User not found")
        
        role_update = user_repository.change_user_role(username, role_id)
        db.session.add(role_update)
        db.session.commit()
        return user_repository.get_user_by_id(user.user_id).username
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))

def change_user_password(data):
    try:
        username = data.get("username", "").strip()
        new_password_raw = data.get("new_password")
        old_password_raw = data.get("old_password")

        user = user_repository.get_user_by_username(username)
        if not user:
            raise NotFoundError("User not found")
        
        if not username or not new_password_raw or not old_password_raw:
            raise MissingFieldsError("Missing required fields (username, new_password, old_password)")
        
        if not verify_bcrypt(old_password_raw, user.password):
            raise ValueError("รหัสผ่านเดิมไม่ถูกต้อง")
        
        if old_password_raw == new_password_raw:
            raise ValueError("รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม")

        hashed_new_password = hash_bcrypt(new_password_raw)

        user_repository.update_user_password(username, hashed_new_password)
        
        db.session.commit()
        return {"message": "เปลี่ยนรหัสผ่านสำเร็จ", "success": True}

    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))


def ban_user(data):
    try:
        username = data.get("username")
        is_active = data.get("is_active")
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        
        updated_by = data.get("updated_by")

        user = user_repository.get_user_by_username(username)
        if not user:
            return NotFoundError("ไม่พบผู้ใช้งานนี้ในระบบ")

        user.is_active = is_active
        
        if hasattr(user, 'updated_by'):
            user.updated_by = updated_by
            
        db.session.commit()

        status_msg = "คืนสิทธิ์" if is_active else "ระงับสิทธิ์"
        
        return {
            "message": f"ดำเนินการ{status_msg}ผู้ใช้ {username} สำเร็จ",
            "success": True
        }

    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))


def assign_branches_to_user(data):
        username = data.get('username')
        branch_ids = data.get('branch_ids', [])

        if not username:
            raise NotFoundError("กรุณาระบุ Username")

        if not isinstance(branch_ids, list):
            raise NotFoundError("branch_ids ต้องเป็นรูปแบบ Array (List) เท่านั้น")

        #เช็คว่ามี User
        user = user_repository.get_user_by_username(username)
        if not user:
            raise NotFoundError("ไม่พบผู้ใช้งานนี้ในระบบ")

        #ค้นหาข้อมูลสาขาจาก branch_ids ที่ส่งมา
        branches = []
        if branch_ids:
            branches = branch_repository.get_branches_by_ids(branch_ids)
            if len(branches) != len(branch_ids):
                return NotFoundError("ข้อมูลสาขาบางส่วนไม่ถูกต้องหรือไม่พบในระบบ")
        try:
            user_repository.update_user_branches(user, branches)
            db.session.commit()
            return {
                "success": True, 
                "message": f"อัปเดตสิทธิ์สาขาให้ {username} สำเร็จ",
                "data": {
                    "username": username,
                    "assigned_branches": [b.branch_name for b in branches]
                }
            }
        except Exception as e:
            db.session.rollback()
            raise AppException(str(e))