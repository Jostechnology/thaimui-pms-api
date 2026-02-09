from app.exception import AppException, UniqueError, ValidationError, NotFoundError
from app.ma_sqlalchemy import UserSchema
from app.repositories import UserLoginRepository, UserRepository
from app.utils import create_token, hash_bcrypt, verify_bcrypt
from app.app import db

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
        }
        access_token = create_token(token_data, "access")
        refresh_token = create_token(token_data, "refresh")

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
    """Logout โดย revoke refresh token"""
    try:
        from app.utils import decode_token
        from app.con_sqlalchemy import Tokenlist
        
        decoded = decode_token(refresh_token)
        if decoded:
            jti = decoded.get("jti")
            user_id = decoded.get("user_id")
            
            # เพิ่ม refresh token เข้า blacklist
            revoked = Tokenlist(
                jwt_id=jti,
                user_id=user_id,
                token_type="refresh"
            )
            db.session.add(revoked)
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
        
        # ตรวจสอบว่า refresh token นี้ถูกใช้ไปแล้วหรือยัง
        used_token = Tokenlist.query.filter_by(jwt_id=jti).first()
        if used_token:
            # ถ้าใช้ซ้ำ = มีคนขโมย token → revoke ทั้งหมดของ user นี้
            raise ValidationError("Refresh token ถูกใช้ไปแล้ว - ตรวจพบความผิดปกติ")
        
        # บันทึกว่า refresh token นี้ถูกใช้แล้ว (blacklist)
        used_refresh = Tokenlist(
            jwt_id=jti,
            user_id=user_id,
            token_type="refresh"
        )
        db.session.add(used_refresh)
        
        # สร้าง access token + refresh token ใหม่
        token_data = {
            "user_id": user_id,
            "username": decoded.get("username")
        }
        new_access_token = create_token(token_data, "access")
        new_refresh_token = create_token(token_data, "refresh")
        
        db.session.commit()
        
        return new_access_token, new_refresh_token
    
    except AppException:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        raise AppException(str(e))