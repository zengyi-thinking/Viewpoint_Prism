"""
认证安全工具
包含密码哈希、JWT Token 生成和验证
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
    """
    创建访问令牌

    返回: (token_string, jti)
    """
    to_encode = data.copy()

    # 生成唯一的 JTI (JWT ID)
    jti = f"{to_encode.get('sub', 'unknown')}_{datetime.utcnow().timestamp()}"

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "jti": jti,
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt, jti


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
    """
    创建刷新令牌

    返回: (token_string, jti)
    """
    to_encode = data.copy()

    # 生成唯一的 JTI
    jti = f"{to_encode.get('sub', 'unknown')}_refresh_{datetime.utcnow().timestamp()}"

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 刷新令牌有效期更长（7天）
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({
        "exp": expire,
        "jti": jti,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt, jti


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码并验证令牌"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
