from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.settings import settings
from .routers import auth, users, empresas, datasets, connections, agents, runs, tables

app = FastAPI(
    title="AgentGraph API",
    description="API multi-usuários para gerenciamento de agentes, datasets, conexões e execuções",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [
    "http://localhost:3000",      # React dev server
    "http://localhost:3001",      # Vite dev server
    "http://localhost:8080",      # Vue dev server
    "http://localhost:5173",      # Vite default
    "http://127.0.0.1:3000",     # React dev server (IP)
    "http://127.0.0.1:3001",     # Vite dev server (IP)
    "http://127.0.0.1:8080",     # Vue dev server (IP)
    "http://127.0.0.1:5173",     # Vite default (IP)
    "http://localhost:8000",      # FastAPI docs
    "http://127.0.0.1:8000",     # FastAPI docs (IP)
]

if hasattr(settings, 'ALLOWED_ORIGINS') and settings.ALLOWED_ORIGINS:
    origins.extend(settings.ALLOWED_ORIGINS.split(','))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
    max_age=86400,  # 24 horas
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(empresas.router, prefix="/empresas", tags=["empresas"])
app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
app.include_router(connections.router, prefix="/connections", tags=["connections"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(runs.router, prefix="", tags=["runs"])  # /runs e /agents/{id}/runs
app.include_router(tables.router, prefix="/tables", tags=["tables"])

@app.get("/healthz")
def healthcheck():
    return {"status": "ok", "version": app.version}

# Startup: garantir diretórios e tabelas (com retry aguardando Postgres ficar pronto)
@app.on_event("startup")
def on_startup():
    settings.ensure_dirs()
    import logging, time
    from sqlalchemy import text
    from .db.session import engine
    from .models import Base

    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            # Testa conexão rápida
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Cria tabelas se não existirem
            Base.metadata.create_all(bind=engine)
            logging.info("[startup] Banco conectado e tabelas garantidas.")
            break
        except Exception as e:
            if attempt == max_attempts:
                logging.warning(f"[startup] Falha ao garantir tabelas: {e}")
                break
            sleep_s = 1.0
            logging.info(f"[startup] Aguardando Postgres ficar pronto (tentativa {attempt}/{max_attempts})...")
            time.sleep(sleep_s)

