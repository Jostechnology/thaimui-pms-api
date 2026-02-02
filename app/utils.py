import jwt, uuid
from  app.config import JWT_SECRET_KEY
from datetime import datetime, timedelta, time
import bcrypt

def create_token(data, token_type="access", expires_in=None):
    try:
        if token_type == "access":
            exp = datetime.utcnow() + timedelta(minutes=15)
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