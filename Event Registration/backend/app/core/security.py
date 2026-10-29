from passlib.context import CryptContext
from datetime import datetime,timedelta
from jose import jwt

SECRET_KEY="something_you_can_never_hack"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

pwd_context=CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password:str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password:str,hashed_password:str)->bool:
    return pwd_context.verify(plain_password,hashed_password)

def create_access_token(data:dict)->str:
    to_encode=data.copy()
    expire=datetime.utcnow()+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(
        to_encode,SECRET_KEY,algorithm=ALGORITHM
    )
    return encoded_jwt