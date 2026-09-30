import os

# Settings() is built at import time; point everything at a throwaway SQLite DB
# (assigned, not setdefault, so tests can never touch a real Postgres DB).
os.environ["APP_NAME"] = "SUNDAY-test"
os.environ["APP_VERSION"] = "test"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ALGORITHM"] = "HS256"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401,E402
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Not used as a context manager on purpose: skips the Postgres startup hook.
    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session):
    from app.seed.seed_fractions import seed_fractions

    seed_fractions(db_session)
    return db_session
