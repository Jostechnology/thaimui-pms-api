import jwt, uuid ,json, base64
from  app.config import JWT_SECRET_KEY
from datetime import datetime, timedelta, time
import bcrypt

def create_token(data, token_type="access", expires_in=None):
    try:
        if token_type == "access":
            exp = datetime.utcnow() + timedelta(hours=10)
        elif token_type == "refresh":
            exp = datetime.utcnow() + timedelta(days=7)
        else:
            raise ValueError("Invalid token_type")

        payload = {
            **data,
            "type": token_type,
            "exp": exp,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # unique token id
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    except Exception as e:
        print(f"Error creating token: {e}")
        return None

def encode_jwt(data):
    try:
        print(data)
        return jwt.encode(data, JWT_SECRET_KEY, algorithm="HS256")
    except Exception:
        raise

def decode_token(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        print("❌ Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {e}")
        return None
    
def hash_bcrypt(input_string: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(input_string.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_bcrypt(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
def convert_start_date(start_date):
    return datetime.combine(
        datetime.strptime(start_date, "%Y-%m-%d").date(),
        time.min
    )

def convert_end_date(end_date):
    return datetime.combine(
        datetime.strptime(end_date, "%Y-%m-%d").date(),
        time.max
    )


def check_true_permissions(authorizes, permission_tree):
    """
    ตรวจสอบว่า permission_tree มี permission ที่ต้องการทั้งหมดหรือไม่
    authorizes: list of dict เช่น [{"module_code": "USER", "method": "read"}]
    permission_tree: list of module dict ที่มี permission และ sub_modules
    raises ValueError ถ้าไม่มีสิทธิ์
    """
    if not authorizes:
        return

    def find_module_permissions(modules, module_code):
        for m in modules:
            if m.get("module_code") == module_code:
                return m.get("permission", [])
            for sm in m.get("sub_modules", []):
                if sm.get("module_code") == module_code:
                    return sm.get("permission", [])
        return []

    for auth in authorizes:
        module_code = auth.get("module_code")
        method = auth.get("method")
        permissions = find_module_permissions(permission_tree, module_code)

        granted = any(
            isinstance(p, dict) and p.get("method") == method and p.get("check") is True
            for p in permissions
        )

        if not granted:
            raise ValueError(f"ไม่มีสิทธิ์ '{method}' สำหรับ module '{module_code}'")