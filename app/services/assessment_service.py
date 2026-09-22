from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.assessment import AssessmentAnswer
from app.models.question import Question


def create_assessment(
    db: Session,
    learner_id: int
):

    questions = (
        db.query(Question)
        .order_by(Question.id)
        .limit(5)
        .all()
    )

    if not questions:
        return None

    question_ids = [
        int(getattr(question, "id"))
        for question in questions
    ]

    assessment = Assessment(
        learner_id=learner_id,
        assessment_type="Baseline",
        question_ids=question_ids,
        status="In Progress"
    )

    db.add(assessment)

    db.commit()

    db.refresh(assessment)

    return assessment


def submit_answer(
    db: Session,
    assessment_id: int,
    question_id: int,
    answer: str
):

    assessment = (
        db.query(Assessment)
        .filter(
            Assessment.id == assessment_id
        )
        .first()
    )

    if assessment is None:
        return None

    assessment_question_ids = getattr(
        assessment,
        "question_ids"
    )

    if question_id not in assessment_question_ids:
        return None

    question = (
        db.query(Question)
        .filter(
            Question.id == question_id
        )
        .first()
    )

    if question is None:
        return None

    correct_answer = str(
        getattr(question, "correct_answer")
    )

    is_correct = (
        answer.strip().lower()
        == correct_answer.strip().lower()
    )

    existing_answer = (
        db.query(AssessmentAnswer)
        .filter(
            AssessmentAnswer.assessment_id == assessment_id,
            AssessmentAnswer.question_id == question_id
        )
        .first()
    )

    if existing_answer:

        setattr(
            existing_answer,
            "answer",
            answer
        )

        setattr(
            existing_answer,
            "is_correct",
            int(is_correct)
        )

    else:

        new_answer = AssessmentAnswer(
            assessment_id=assessment_id,
            question_id=question_id,
            answer=answer,
            is_correct=int(is_correct)
        )

        db.add(new_answer)

    db.commit()

    return {
        "question_id": question_id,
        "correct": is_correct
    }


def calculate_result(
    db: Session,
    assessment_id: int
):

    assessment = (
        db.query(Assessment)
        .filter(
            Assessment.id == assessment_id
        )
        .first()
    )

    if assessment is None:
        return None

    question_ids = getattr(
        assessment,
        "question_ids"
    )

    questions = (
        db.query(Question)
        .filter(
            Question.id.in_(question_ids)
        )
        .all()
    )

    total_marks = 0

    for question in questions:

        marks = int(
            getattr(question, "marks")
        )

        total_marks += marks

    score = 0

    answers = (
        db.query(AssessmentAnswer)
        .filter(
            AssessmentAnswer.assessment_id
            == assessment_id
        )
        .all()
    )

    for answer in answers:

        is_correct = int(
            getattr(answer, "is_correct")
        )

        if is_correct:

            answer_question_id = int(
                getattr(answer, "question_id")
            )

            question = next(
                (
                    q
                    for q in questions
                    if int(getattr(q, "id"))
                    == answer_question_id
                ),
                None
            )

            if question is not None:

                score += int(
                    getattr(question, "marks")
                )

    accuracy = 0.0

    if total_marks > 0:

        accuracy = (
            score / total_marks
        ) * 100

    if len(answers) == len(questions):

        setattr(
            assessment,
            "status",
            "Completed"
        )

    setattr(
        assessment,
        "score",
        score
    )

    setattr(
        assessment,
        "total_marks",
        total_marks
    )

    setattr(
        assessment,
        "accuracy",
        accuracy
    )

    db.commit()

    return {
        "assessment_id": int(
            getattr(assessment, "id")
        ),
        "learner_id": int(
            getattr(assessment, "learner_id")
        ),
        "score": score,
        "total_marks": total_marks,
        "accuracy": round(accuracy, 2),
        "status": getattr(
            assessment,
            "status"
        )
    }