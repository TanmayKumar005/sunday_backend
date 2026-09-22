from fastapi import FastAPI

from app.core.database import Base
from app.core.database import engine

import app.models

from app.routes.learner import router as learner_router
from app.routes.question import router as question_router
from app.routes.assessment import router as assessment_router


app = FastAPI(
    title="S.U.N.D.A.Y. API",
    version="1.0.0"
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