"""Idempotent seed for Class 6 Maths / Ganita Prakash / Chapter 7: Fractions.

Usage (from project root, with .env configured):
    python -m app.seed.seed_fractions

Safe to re-run. It only inserts or refreshes content/question rows that it
owns (matched by section_code, and by unit_id + question_text). It never
deletes anything and never touches learners, profiles or assessments.
"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.content import Content
from app.models.question import Question
from app.seed.fractions_content import FRACTIONS_CONTENT
from app.seed.fractions_hints import FRACTIONS_HINTS
from app.seed.fractions_questions import FRACTIONS_QUESTIONS

SEEDED_TABLES = ("content", "questions", "assessment_answers")


def add_missing_columns(engine):
    """Add columns introduced in Stage 1 to tables that already exist.

    create_all() only creates missing TABLES. This adds missing COLUMNS
    (nullable, with server default if defined) so an existing dev database
    keeps its data. Does nothing on a fresh database.
    """

    inspector = inspect(engine)

    for table in Base.metadata.sorted_tables:

        if table.name not in SEEDED_TABLES:
            continue

        if not inspector.has_table(table.name):
            continue

        existing = {
            column["name"]
            for column in inspector.get_columns(table.name)
        }

        for column in table.columns:

            if column.name in existing:
                continue

            ddl = (
                f'ALTER TABLE "{table.name}" '
                f'ADD COLUMN "{column.name}" '
                f"{column.type.compile(dialect=engine.dialect)}"
            )

            if column.server_default is not None:
                ddl += f" DEFAULT '{column.server_default.arg}'"  # type: ignore

            with engine.begin() as connection:
                connection.execute(text(ddl))


def seed_fractions(db: Session) -> dict:

    stats = {
        "content_created": 0,
        "content_existing": 0,
        "questions_created": 0,
        "questions_existing": 0,
    }

    units = {}

    for section in FRACTIONS_CONTENT:

        unit = (
            db.query(Content)
            .filter(Content.section_code == section["section_code"])
            .first()
        )

        if unit is None:
            unit = Content(**section)
            db.add(unit)
            stats["content_created"] += 1
        else:
            for key, value in section.items():
                setattr(unit, key, value)
            stats["content_existing"] += 1

        db.flush()

        units[section["section_code"]] = unit

    for section_code, questions in FRACTIONS_QUESTIONS.items():

        unit = units[section_code]

        hints = FRACTIONS_HINTS.get(section_code, [])

        for index, item in enumerate(questions):

            values = {
                **item,
                "hint": hints[index] if index < len(hints) else None,
                "topic": unit.topic,
                "learning_objective": unit.learning_objective,
            }

            question = (
                db.query(Question)
                .filter(
                    Question.unit_id == unit.unit_id,
                    Question.question_text == item["question_text"],
                )
                .first()
            )

            if question is None:
                db.add(Question(unit_id=unit.unit_id, **values))
                stats["questions_created"] += 1
            else:
                for key, value in values.items():
                    setattr(question, key, value)
                stats["questions_existing"] += 1

    db.commit()

    return stats


def main():

    from app.core.database import SessionLocal, engine

    import app.models  # noqa: F401  (register all tables)

    Base.metadata.create_all(bind=engine)

    add_missing_columns(engine)

    db = SessionLocal()

    try:
        stats = seed_fractions(db)
    finally:
        db.close()

    print("Fractions seed complete:", stats)


if __name__ == "__main__":
    main()
