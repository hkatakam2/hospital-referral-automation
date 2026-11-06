from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.extractions import methods_router
from app.api.extractions import router as extractions_router
from app.api.health import router as health_router
from app.api.referrals import router as referrals_router
from app.config import settings
from app.extraction.policy import load_policy


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.referral_policy = load_policy(settings.referral_policy_path)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(health_router, prefix="/api")
app.include_router(referrals_router, prefix="/api")
app.include_router(documents_router, prefix="/api")

app.include_router(extractions_router, prefix="/api")

app.include_router(methods_router, prefix="/api")
