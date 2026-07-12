"""認証モジュール（JWT）"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db, User

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8時間

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証が必要です")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無効なトークンです")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無効なトークンです")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが見つかりません")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理者権限が必要です")
    return current_user


def create_default_users(db: Session):
    """初期ユーザーを作成する"""
    defaults = [
        {"username": "admin", "password": "admin123", "display_name": "管理者", "role": "admin", "tanto_code": ""},
        {"username": "user1", "password": "user123", "display_name": "発送担当1", "role": "operator", "tanto_code": "T001"},
        {"username": "user2", "password": "user123", "display_name": "発送担当2", "role": "operator", "tanto_code": "T002"},
        {"username": "user3", "password": "user123", "display_name": "発送担当3", "role": "operator", "tanto_code": "T003"},
    ]
    for u in defaults:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            db.add(User(
                username=u["username"],
                hashed_password=hash_password(u["password"]),
                display_name=u["display_name"],
                role=u["role"],
                tanto_code=u["tanto_code"],
            ))
    db.commit()
