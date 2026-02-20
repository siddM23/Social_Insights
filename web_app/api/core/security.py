import jwt
import datetime
import bcrypt
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from core.config import JWT_SECRET, ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS

# Monkeypatch bcrypt for passlib compatibility (bcrypt 4.0+ removed __about__)
if not hasattr(bcrypt, "__about__"):
    try:
        from bcrypt import __version__ as bcrypt_version
        class About:
            __version__ = bcrypt_version
        bcrypt.__about__ = About()
    except ImportError:
        pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(token: Optional[str] = None, oauth_token: str = Depends(oauth2_scheme)) -> str:
    # Fallback to query param if header is missing (useful for GET redirects)
    actual_token = oauth_token if oauth_token else token
    
    if not actual_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        payload = jwt.decode(actual_token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
