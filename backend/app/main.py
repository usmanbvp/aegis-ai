from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.investigation import router as investigation_router
from app.api.routes.retrieval import router as retrieval_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AEGIS API",
    description="AI-powered incident investigation and root-cause analysis platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(retrieval_router)
app.include_router(investigation_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/api/v1/health")
def api_healthcheck() -> dict[str, str]:
    return {"status": "ok"}
