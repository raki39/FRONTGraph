from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models import User
from ..schemas import TokenWithUSer, UserOut, UserCreate
from ..core.security import verify_password, create_access_token, get_current_user, get_password_hash

router = APIRouter()

@router.post("/login", response_model=TokenWithUSer)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.senha_hash) or not user.ativo:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token(subject=user.email)
    response = {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "ativo": user.ativo,
            "created_at": user.created_at,
        }
    }
    return response

@router.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Verifica se o email já existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Cria novo usuário
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        nome=user_data.nome,
        email=user_data.email,
        senha_hash=hashed_password,
        ativo=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

