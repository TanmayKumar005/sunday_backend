from fastapi import FastAPI

from app.core.database import Base
from app.core.database import engine
from app.routes.learner import router as learner_router
from app.routes.content import router as content_router



import app.models

app = FastAPI(
    title="S.U.N.D.A.Y",
    version="1.0.0"
)


@app.on_event("startup")
def startup():

    Base.metadata.create_all(bind=engine)

app.include_router(learner_router)
app.include_router(content_router)


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