from pydantic import BaseModel


class StartAssessmentRequest(BaseModel):

    learner_id: int


class SubmitAnswerRequest(BaseModel):

    question_id: int

    answer: str


class AssessmentStartResponse(BaseModel):

    assessment_id: int

    learner_id: int

    assessment_type: str

    questions: list[int]


class AssessmentAnswerResponse(BaseModel):

    question_id: int

    correct: bool


class AssessmentResult(BaseModel):

    assessment_id: int

    learner_id: int

    score: float

    total_marks: float

    accuracy: float

    status: str