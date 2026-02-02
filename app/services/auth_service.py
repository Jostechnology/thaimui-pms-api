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