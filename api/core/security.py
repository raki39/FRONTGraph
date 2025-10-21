from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..db.session import get_db
from ..models import User, UserRole
from sqlalchemy.orm import Session

from ..core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Lista de emails que têm privilégios de admin
ADMIN_EMAILS = [
    "admin@example.com",
    "admin@agentgraph.com",
    "root@agentgraph.com"
]


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == sub).first()
    if not user or not user.ativo:
        raise credentials_exception
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency para verificar se o usuário atual é um administrador.
    Verifica se o usuário tem role ADMIN ou SUPER_ADMIN no banco de dados.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Privilégios de administrador necessários."
        )
    return current_user


def get_current_super_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency para verificar se o usuário atual é um super administrador.
    Apenas SUPER_ADMIN pode gerenciar roles de outros usuários.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Privilégios de super administrador necessários."
        )
    return current_user

def is_admin_user(user: User) -> bool:
    """
    Verifica se um usuário é administrador (ADMIN ou SUPER_ADMIN).
    """
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]

def is_super_admin_user(user: User) -> bool:
    """
    Verifica se um usuário é super administrador.
    """
    return user.role == UserRole.SUPER_ADMIN

