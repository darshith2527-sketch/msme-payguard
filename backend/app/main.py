from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .db import Base, engine
from .routers import invoices

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MSME PayGuard API",
    description="AI-powered receivables intelligence & dispute prevention for MSMEs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
