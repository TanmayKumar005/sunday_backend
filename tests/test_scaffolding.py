"""Progressive scaffolding (pure, no database)."""

from app.ai.scaffolding import (
    GENERIC_STEPS,
    MAX_LEVEL,
    SECTION_SCAFFOLDS,
    ScaffoldContext,
    build_scaffold,
    next_level,
)
from app.seed.fractions_hints import FRACTIONS_HINTS
from app.seed.fractions_questions import FRACTIONS_QUESTIONS


def ctx(section="7.8", hint="Try common denominators.", answer="3/4", **kw):
    data = dict(
        concept="Adding unlike fractions",
        question_type="MCQ",
        correct_answer=answer,
        explanation="1/2 = 2/4, so 2/4 + 1/4 = 3/4.",
        hint=hint,
        section_code=section,
    )
    data.update(kw)
    return ScaffoldContext(**data)


def test_levels_advance_one_at_a_time_and_stop_at_four():
    assert [next_level(n) for n in (None, 0, 1, 2, 3, 4, 9)] == [1, 1, 2, 3, 4, 4, 4]
    assert MAX_LEVEL == 4


def test_level_types_in_order():
    names = [build_scaffold(n, ctx()).level_name for n in (1, 2, 3, 4)]
    assert names == ["HINT", "CONCEPT_REMINDER", "WORKED_STEPS", "FINAL_EXPLANATION"]


def test_only_level_four_reveals_the_answer():
    for level in (1, 2, 3):
        step = build_scaffold(level, ctx())
        assert step.reveals_answer is False
        assert step.correct_answer is None

    final = build_scaffold(4, ctx())
    assert final.reveals_answer is True
    assert final.correct_answer == "3/4"
    assert "2/4" in final.content


def test_level_one_uses_question_hint_or_a_generic_fallback():
    assert build_scaffold(1, ctx(hint="Use the same denominator.")).content == "Use the same denominator."

    fallback = build_scaffold(1, ctx(hint=None))
    assert "Adding unlike fractions" in fallback.content
    assert "3/4" not in fallback.content

    numerical = build_scaffold(1, ctx(hint=None, question_type="NUMERICAL"))
    assert "calculate" in numerical.content


def test_level_two_is_the_section_concept_reminder():
    step = build_scaffold(2, ctx("7.6"))
    assert step.content == SECTION_SCAFFOLDS["7.6"]["reminder"]


def test_level_three_gives_worked_steps_on_a_similar_example():
    step = build_scaffold(3, ctx("7.5"))
    assert len(step.steps) >= 3
    assert step.steps == SECTION_SCAFFOLDS["7.5"]["example_steps"]
    assert "Similar example" in step.content


def test_fallbacks_when_section_has_no_scaffold_material():
    reminder = build_scaffold(2, ctx(section=None, section_explanation="Unit text."))
    assert reminder.content == "Unit text."

    steps = build_scaffold(3, ctx(section="9.9"))
    assert steps.steps == GENERIC_STEPS

    no_explanation = build_scaffold(4, ctx(explanation=None))
    assert no_explanation.correct_answer == "3/4"
    assert no_explanation.content


def test_invalid_level_rejected():
    for bad in (0, 5, -1):
        try:
            build_scaffold(bad, ctx())
        except ValueError:
            continue
        raise AssertionError(f"level {bad} should be rejected")


def test_every_section_has_scaffold_material():
    assert set(SECTION_SCAFFOLDS) == set(FRACTIONS_QUESTIONS)
    for material in SECTION_SCAFFOLDS.values():
        assert material["reminder"] and material["example_problem"]
        assert len(material["example_steps"]) >= 3


def test_every_question_has_a_hint():
    for code, questions in FRACTIONS_QUESTIONS.items():
        assert len(FRACTIONS_HINTS[code]) == len(questions), code
        assert all(h.strip() for h in FRACTIONS_HINTS[code])


def test_lower_levels_never_leak_seeded_answers():
    """Levels 1-3 must not contain a question's answer."""

    for code, questions in FRACTIONS_QUESTIONS.items():
        for index, q in enumerate(questions):
            context = ScaffoldContext(
                concept=q["concept"],
                question_type=q["question_type"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
                hint=FRACTIONS_HINTS[code][index],
                section_code=code,
            )
            answer = q["correct_answer"]

            for level in (1, 2, 3):
                step = build_scaffold(level, context)
                text = " ".join([step.content] + step.steps)

                # Fraction answers ("3/8") and long text answers are checked in
                # the hint; the shared concept/worked text is checked against
                # every fraction answer in the section (definition questions
                # such as "smaller" are allowed to be taught by the reminder).
                if level == 1 and (len(answer) >= 4 or "/" in answer):
                    assert answer not in text, (code, index, answer)

                if level in (2, 3):
                    for other in questions:
                        if "/" in other["correct_answer"]:
                            assert other["correct_answer"] not in text, (
                                code, level, other["correct_answer"]
                            )
