from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, events, inscricoes, pages

from app.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="eventos-api")

ALLOWED_ORIGINS = [
    "http://localhost:3000",       # frontend local, ajuste pro seu domínio real
    "https://app.eventos-api.com", # exemplo de domínio de produção do frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # nunca "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/")
def read_root():
    """Rota de health-check, usada para validar que o serviço está no ar."""
    return {"status": "ok", "service": "eventos-api"}

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(inscricoes.router)
app.include_router(pages.router)