from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base
from app.core.database import engine

import app.models

from app.routes.learner import router as learner_router
from app.routes.question import router as question_router
from app.routes.assessment import router as assessment_router
from app.routes.content import router as content_router
from app.routes.adaptation import router as adaptation_router
from app.routes.progress import router as progress_router


app = FastAPI(
    title="S.U.N.D.A.Y. API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():

    Base.metadata.create_all(
        bind=engine
    )


app.include_router(
    learner_router
)

app.include_router(
    question_router
)

app.include_router(
    assessment_router
)

app.include_router(
    content_router
)

app.include_router(
    adaptation_router
)

app.include_router(
    progress_router
)


@app.get("/")
def home():

    return {
        "message": "Welcome to S.U.N.D.A.Y Backend"
    }


@app.get("/health")
def health():

    return {
        "status": "Running"
    }