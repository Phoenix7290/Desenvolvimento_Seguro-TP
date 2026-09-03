from fastapi import FastAPI

from app.routes import auth, events, pages

app = FastAPI(title="eventos-api")


@app.get("/")
def read_root():
    """Rota de health-check, usada para validar que o serviço está no ar."""
    return {"status": "ok", "service": "eventos-api"}


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(pages.router)