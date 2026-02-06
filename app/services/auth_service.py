from app.exception import AppException, UniqueError, ValidationError, NotFoundError
from app.ma_sqlalchemy import UserSchema
from app.repositories import UserLoginRepository, UserRepository 
from app.utils import create_token, hash_bcrypt, verify_bcrypt 
from app.app import db
from app.utils import decode_token
from app.con_sqlalchemy import Tokenlist

def login_service(data):
    try:
        username = data.get("username")
        password = data.get("password")

        user = UserRepository.get_user_by_username(username)

        validate = verify_bcrypt(password, user.password)

        if not validate:
            raise NotFoundError("รหัสหรือชื่อผู้ใช้ไม่ถูกต้อง")
                
        token_data = {
            "user_id": user.user_id,
            "username" : user.username,
            "role_name" : user.role.role_name,
            "role_id" : user.role.role_id,
            "role_code" : user.role.role_code,
            "permissions": user.role.get_permissions()
        }
        access_token = create_token(token_data, "access")
        refresh_token = create_token(token_data, "refresh")

        access_jti = decode_token(access_token).get("jti")
        refresh_jti = decode_token(refresh_token).get("jti")

        db.session.add(Tokenlist(jwt_id=access_jti, user_id=user.user_id, token_type="access"))
        db.session.add(Tokenlist(jwt_id=refresh_jti, user_id=user.user_id, token_type="refresh"))
        db.session.commit()

        return access_token, refresh_token
    
    except AppException as e:
        db.session.rollback()
        raise
    except Exception as e:
        raise

def register_service(data):
    try:
        user_schema = UserSchema()
        username = data.get("username")
        password = data.get("password")
        
        # Validate input
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        # Check uniqueness
        if UserRepository.check_username_exist(username):
            raise UniqueError("username นี้มีอยู่แล้ว")
        
        hashed_password = hash_bcrypt(password)
        create_user_data = {
            "username": username,
            "password": hashed_password
        }
        
        new_user = UserRepository.create_user(create_user_data)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.dump(new_user)
        
    except AppException:
        # Known application errors - rollback and re-raise
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException("An unexpected error occurred")
    
def logout_service(refresh_token):
    """Logout โดยเพิ่ม refresh token เข้า blacklist"""
    try:
        from app.utils import decode_token
        from app.con_sqlalchemy import Tokenlist
        
        decoded = decode_token(refresh_token)
        if decoded:
            user_id = decoded.get("user_id")
            
            # ลบ token ปัจจุบันออกจาก whitelist
            Tokenlist.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        
        return {"message": "Logged out successfully"}
    
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))
    
    
def refresh_token_service(refresh_token):
    try:
        from app.utils import decode_token
        from app.con_sqlalchemy import Tokenlist
        
        # Decode refresh token
        decoded = decode_token(refresh_token)
        if not decoded:
            raise ValidationError("Refresh token ไม่ถูกต้องหรือหมดอายุ")
        
        # ตรวจสอบว่าเป็น refresh token จริงๆ
        if decoded.get("type") != "refresh":
            raise ValidationError("Token ประเภทไม่ถูกต้อง")
        
        jti = decoded.get("jti")
        user_id = decoded.get("user_id")
        
        # Whitelist: ตรวจสอบว่า refresh token นี้มีอยู่ใน whitelist
        valid_token = Tokenlist.query.filter_by(jwt_id=jti, token_type="refresh").first()
        if not valid_token:
            raise ValidationError("Refresh token ไม่ถูกต้องหรือหมดอายุ")
        
        # ลบ token เก่าออกจาก whitelist
        db.session.delete(valid_token)

        Tokenlist.query.filter_by(user_id=user_id).delete()
        
        # สร้าง access token + refresh token ใหม่
        token_data = {
            "user_id": user_id,
            "username": decoded.get("username")
        }
        new_access_token = create_token(token_data, "access")
        new_refresh_token = create_token(token_data, "refresh")

        # เพิ่ม token ใหม่เข้า whitelist
        new_access_jti = decode_token(new_access_token).get("jti")
        new_refresh_jti = decode_token(new_refresh_token).get("jti")
        db.session.add(Tokenlist(jwt_id=new_access_jti, user_id=user_id, token_type="access"))
        db.session.add(Tokenlist(jwt_id=new_refresh_jti, user_id=user_id, token_type="refresh"))
        
        db.session.commit()
        
        print(f"✅ Refresh Token Success for user_id: {user_id}")
        print(f"   Old Refresh Token (Deleted): {jti}")
        print(f"   New Refresh Token Generated")
        
        return new_access_token, new_refresh_token
    
    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))