from .session import engine, SessionLocal
from ..models import Base, User
from ..core.security import get_password_hash

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # cria admin se não existir
        from sqlalchemy import select
        exists = db.execute(select(User).where(User.email == "admin@example.com")).scalar_one_or_none()
        if not exists:
            user = User(email="admin@example.com", nome="Admin", senha_hash=get_password_hash("admin"), ativo=True)
            db.add(user)
            db.commit()
            print("Admin criado: admin@example.com / admin")
        else:
            print("Admin já existe")
    finally:
        db.close()

