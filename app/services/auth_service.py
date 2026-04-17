from app.exception import AppException, UniqueError, ValidationError, NotFoundError, AuthenticationError
from app.ma_sqlalchemy import UserSchema
from app.repositories import user_login_repository, user_repository
from app.services.user_service import check_user_permission
from app.utils import create_token, hash_bcrypt, verify_bcrypt, decode_token
from app.app import db
from app.con_sqlalchemy import Tokenlist


def login_service(data):
    try:
        username = data.get("username")
        password = data.get("password")

        user = user_repository.get_user_for_login(username)
        
        if not user:
            raise NotFoundError("รหัสหรือชื่อผู้ใช้ไม่ถูกต้อง")

        if not verify_bcrypt(password, user.password):
            raise NotFoundError("รหัสหรือชื่อผู้ใช้ไม่ถูกต้อง")

        if not bool(user.is_active):
            raise NotFoundError("ผู้ใช้งานนี้ถูกระงับการใช้งาน")

        user_branch_ids = []
        user_branches = []
        for branch in user.branches:
            if branch.is_active:
                user_branch_ids.append(branch.branch_id)
                user_branches.append({
                    "branch_id": branch.branch_id,
                    "branch_name": branch.branch_name
                })

        has_all_branch_access = check_user_permission(user.user_id, "ALL_BRANCH", "view")
        if (not user_branch_ids) and not has_all_branch_access:
            raise NotFoundError("คุณไม่มีสิทธิ์เข้าถึงสาขาใดเลย หรือสาขาของคุณถูกระงับการใช้งาน")

        branch_select_token = create_token(
            {
                "user_id": user.user_id,
                "username": user.username,
                "allowed_branches": user_branch_ids,
            },
            "branch_select"
        )
        return branch_select_token, user_branches, has_all_branch_access

    except Exception:
        raise


def select_branch_service(data):
    try:
        branch_select_token = data.get("branch_select_token")
        branch_id = int(data.get("branch_id"))

        if not branch_select_token or branch_id is None:
            raise ValidationError("branch_select_token และ branch_id จำเป็นต้องมี")

        decoded = decode_token(branch_select_token)
        if not decoded:
            raise AuthenticationError("branch_select_token ไม่ถูกต้องหรือหมดอายุ")

        if decoded.get("type") != "branch_select":
            raise AuthenticationError("Token ประเภทไม่ถูกต้อง")

        allowed_branches = decoded.get("allowed_branches", [])
        if branch_id not in allowed_branches:
            raise AuthenticationError("คุณไม่มีสิทธิ์เข้าถึงสาขานี้")

        user = user_repository.get_user_for_login(decoded.get("username"))
        if not user or not user.is_active:
            raise NotFoundError("ไม่พบผู้ใช้งานหรือถูกระงับการใช้งาน")

        token_data = {
            "user_id": user.user_id,
            "username": user.username,
            "role_name": user.role.role_name,
            "role_id": user.role.role_id,
            "role_code": user.role.role_code,
            "permissions": user.role.get_permissions(),
            "branch_id": branch_id,
        }

        access_token = create_token(token_data, "access")
        refresh_token = create_token(token_data, "refresh")

        access_jti = decode_token(access_token).get("jti")
        refresh_jti = decode_token(refresh_token).get("jti")

        db.session.add(Tokenlist(jwt_id=access_jti, user_id=user.user_id, token_type="access"))
        db.session.add(Tokenlist(jwt_id=refresh_jti, user_id=user.user_id, token_type="refresh"))
        db.session.commit()

        return access_token, refresh_token

    except AppException:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def select_all_branch_service(data):
    try:
        branch_select_token = data.get("branch_select_token")

        if not branch_select_token:
            raise ValidationError("branch_select_token จำเป็นต้องมี")

        decoded = decode_token(branch_select_token)
        if not decoded:
            raise AuthenticationError("branch_select_token ไม่ถูกต้องหรือหมดอายุ")

        if decoded.get("type") != "branch_select":
            raise AuthenticationError("Token ประเภทไม่ถูกต้อง")

        user = user_repository.get_user_for_login(decoded.get("username"))
        if not user or not user.is_active:
            raise NotFoundError("ไม่พบผู้ใช้งานหรือถูกระงับการใช้งาน")

        permissions = user.role.get_permissions()
        if not check_user_permission(user.user_id, "ALL_BRANCH", "view"):
            raise AuthenticationError("คุณไม่มีสิทธิ์เข้าถึงโหมด All Branch")

        token_data = {
            "user_id": user.user_id,
            "username": user.username,
            "role_name": user.role.role_name,
            "role_id": user.role.role_id,
            "role_code": user.role.role_code,
            "permissions": permissions,
            "all_branch_mode": True,
        }

        access_token = create_token(token_data, "all_branch")
        refresh_token = create_token(token_data, "refresh")

        access_jti = decode_token(access_token).get("jti")
        refresh_jti = decode_token(refresh_token).get("jti")

        db.session.add(Tokenlist(jwt_id=access_jti, user_id=user.user_id, token_type="all_branch"))
        db.session.add(Tokenlist(jwt_id=refresh_jti, user_id=user.user_id, token_type="refresh"))
        db.session.commit()

        return access_token, refresh_token

    except AppException:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def register_service(data):
    try:
        user_schema = UserSchema()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise ValidationError("Username and password are required")

        if user_repository.check_username_exist(username):
            raise UniqueError("username นี้มีอยู่แล้ว")

        hashed_password = hash_bcrypt(password)
        create_user_data = {
            "username": username,
            "password": hashed_password
        }

        new_user = user_repository.create_user(create_user_data)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.dump(new_user)

    except AppException:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise AppException("An unexpected error occurred")


def logout_service(refresh_token):
    try:
        decoded = decode_token(refresh_token)
        if decoded:
            user_id = decoded.get("user_id")
        Tokenlist.query.filter_by(user_id=user_id, token_type="access").delete()
        db.session.commit()
        return {"message": "Logged out successfully"}
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))


def refresh_token_service(refresh_token):
    try:
        decoded = decode_token(refresh_token)
        if not decoded:
            raise ValidationError("Refresh token ไม่ถูกต้องหรือหมดอายุ")

        if decoded.get("type") != "refresh":
            raise ValidationError("Token ประเภทไม่ถูกต้อง")

        jti = decoded.get("jti")
        user_id = decoded.get("user_id")
        branch_id = decoded.get("branch_id")

        valid_token = Tokenlist.query.filter_by(jwt_id=jti, token_type="refresh").first()
        if not valid_token:
            raise ValidationError("Refresh token ไม่ถูกต้องหรือหมดอายุ")

        db.session.delete(valid_token)
        Tokenlist.query.filter_by(user_id=user_id).delete()

        user = user_repository.get_user_for_login(decoded.get("username"))
        if not user:
            raise NotFoundError("ไม่พบข้อมูลผู้ใช้")

        token_data = {
            "user_id": user.user_id,
            "username": user.username,
            "role_name": user.role.role_name,
            "role_id": user.role.role_id,
            "role_code": user.role.role_code,
            "permissions": user.role.get_permissions(),
            "branch_id": branch_id,
        }
        new_access_token = create_token(token_data, "access")
        new_refresh_token = create_token(token_data, "refresh")

        new_access_jti = decode_token(new_access_token).get("jti")
        new_refresh_jti = decode_token(new_refresh_token).get("jti")
        db.session.add(Tokenlist(jwt_id=new_access_jti, user_id=user_id, token_type="access"))
        db.session.add(Tokenlist(jwt_id=new_refresh_jti, user_id=user_id, token_type="refresh"))
        db.session.commit()

        return new_access_token, new_refresh_token

    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))
