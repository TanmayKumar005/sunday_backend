from fastapi import FastAPI

from app.database import Base, engine
from app.routes.content import router as content_router
from app.routes.assessment import router as assessment_router
from app.models.content import Content
from app.models.assessment import Question

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="S.U.N.D.A.Y. API",
    description="Content and Assessment API for S.U.N.D.A.Y. adaptive learning system",
    version="1.0.0"
)

app.include_router(content_router)
app.include_router(assessment_router)


@app.get("/")
def home():
    return {"message": "S.U.N.D.A.Y. API is running"}

# Register Content routes
app.include_router(content_router)


@app.get("/")
def home():
    return {
        "message": "S.U.N.D.A.Y. API is running"
    }