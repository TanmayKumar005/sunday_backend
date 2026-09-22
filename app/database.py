from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="bind@123",
    host="localhost",
    port=5432,
    database="sunday_db",
)


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()