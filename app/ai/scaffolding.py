"""Progressive, rule-based scaffolding.

Level 1  small hint               (never reveals the answer)
Level 2  concept reminder         (rule only, no solved copy of the question)
Level 3  worked-step guidance     (a SIMILAR solved example, different numbers)
Level 4  final explanation        (the only level that reveals the answer)

Pure functions; the service layer decides which level a learner may see.
"""

from dataclasses import dataclass, field
from typing import List, Optional

MAX_LEVEL = 4

LEVEL_NAMES = {
    1: "HINT",
    2: "CONCEPT_REMINDER",
    3: "WORKED_STEPS",
    4: "FINAL_EXPLANATION",
}

GENERIC_STEPS = [
    "Read the question again and underline what is being asked.",
    "Write down the numbers and fractions you are given.",
    "Pick the rule from the concept reminder that matches the question.",
    "Work it out one step at a time.",
    "Check that your answer makes sense.",
]

# Static teaching content per NCERT section. The examples deliberately use
# different numbers from the question bank so they never contain an answer.
SECTION_SCAFFOLDS = {
    "7.1": {
        "reminder": (
            "A whole that is shared equally is cut into equal parts, and each "
            "equal part is a fractional unit: sharing among 2 gives halves, "
            "among 3 gives thirds, among 4 gives fourths. The parts must be "
            "equal. The more parts we make, the smaller each part is. With "
            "several wholes, count all the parts first, then share them out."
        ),
        "example_problem": "5 people share 1 sheet of paper equally. What fraction does each person get?",
        "example_steps": [
            "Count the equal shares needed: 5 people, so 5 shares.",
            "Cut the sheet into 5 EQUAL parts.",
            "Each person gets one part, which is one-fifth, 1/5.",
            "Check: 5 parts of 1/5 make the whole sheet.",
        ],
    },
    "7.2": {
        "reminder": (
            "In a fraction, the denominator (bottom number) tells how many "
            "equal parts the whole is cut into, and the numerator (top number) "
            "tells how many of those parts are taken. Parts taken plus parts "
            "left make the whole. A fraction with numerator 1 is a unit "
            "fraction."
        ),
        "example_problem": "A bar has 10 equal pieces and 7 are eaten. What fraction is eaten, and what fraction is left?",
        "example_steps": [
            "Total equal pieces = 10, so the denominator is 10.",
            "Eaten pieces = 7, so the eaten fraction is 7/10.",
            "Left = 10 - 7 = 3 pieces, so 3/10 is left.",
            "Check: 7/10 + 3/10 = 10/10 = 1 whole.",
        ],
    },
    "7.3": {
        "reminder": (
            "When a fractional unit 1/d is used n times, the length is "
            "n x 1/d = n/d. Exactly d of these units make 1 whole. Fractional "
            "units let us measure the leftover part that whole units cannot."
        ),
        "example_problem": "A 1/5 litre spoon is used 6 times. How much is that altogether?",
        "example_steps": [
            "One spoon is 1/5 litre.",
            "Used 6 times, so multiply: 6 x 1/5 = 6/5 litres.",
            "6/5 is more than 1: it is 1 whole and 1/5 litre more.",
            "Check: 5 spoons make 1 litre, and there is 1 more spoon.",
        ],
    },
    "7.4": {
        "reminder": (
            "To place fractions with denominator d, divide each unit gap on "
            "the number line into d equal parts. The marks after 0 are 1/d, "
            "2/d, 3/d, ... and d/d is 1. Keep the same spacing beyond 1. "
            "Fractions further to the right are larger."
        ),
        "example_problem": "Mark 9/4 on the number line.",
        "example_steps": [
            "The denominator is 4, so divide each unit gap into 4 equal parts.",
            "Start at 0 and count 9 marks to the right.",
            "The 4th mark is 4/4 = 1 and the 8th mark is 8/4 = 2.",
            "The 9th mark is one step after 2, so 9/4 lies just after 2 (2 and 1/4).",
        ],
    },
    "7.5": {
        "reminder": (
            "An improper fraction (numerator at least the denominator) can be "
            "written as a mixed fraction. Divide the numerator by the "
            "denominator: the quotient is the whole part and the remainder is "
            "the numerator of the fraction part. To go back, use "
            "whole x denominator + numerator, over the same denominator."
        ),
        "example_problem": "Write 17/5 as a mixed fraction, then change it back.",
        "example_steps": [
            "Divide 17 by 5: quotient 3, remainder 2.",
            "The whole part is 3 and the fraction part is 2/5, so 17/5 = 3 2/5.",
            "Go back: 3 x 5 + 2 = 17.",
            "So 3 2/5 = 17/5.",
        ],
    },
    "7.6": {
        "reminder": (
            "Equivalent fractions show the same amount. Multiply or divide the "
            "numerator and denominator by the same non-zero number to get one. "
            "To simplify, divide both by a common factor until only 1 divides "
            "both."
        ),
        "example_problem": "Find a fraction equal to 3/5 with denominator 10, and simplify 15/25.",
        "example_steps": [
            "5 x 2 = 10, so multiply the numerator by 2 too: 3 x 2 = 6, giving 6/10.",
            "For 15/25, both numbers can be divided by 5.",
            "15 / 5 = 3 and 25 / 5 = 5, so 15/25 = 3/5.",
            "3 and 5 share no factor except 1, so 3/5 is in simplest form.",
        ],
    },
    "7.7": {
        "reminder": (
            "Same denominator: the larger numerator is the larger fraction. "
            "Same numerator: the smaller denominator gives the larger "
            "fraction. Different denominators: rewrite both with a common "
            "denominator, then compare the numerators. To order several "
            "fractions, use one common denominator for all of them."
        ),
        "example_problem": "Which is greater, 2/5 or 3/7?",
        "example_steps": [
            "The denominators differ, so find a common denominator: 5 x 7 = 35.",
            "2/5 = 14/35 and 3/7 = 15/35.",
            "Compare numerators: 15 is more than 14.",
            "So 3/7 is greater than 2/5.",
        ],
    },
    "7.8": {
        "reminder": (
            "For like fractions (same denominator), add or subtract the "
            "numerators and keep the denominator. For unlike fractions, first "
            "rewrite them with a common denominator, then add or subtract. "
            "Denominators are never added. Simplify at the end."
        ),
        "example_problem": "Find 3/5 - 1/10.",
        "example_steps": [
            "The denominators 5 and 10 differ; 10 is a common denominator.",
            "3/5 = 6/10.",
            "Subtract the numerators: 6/10 - 1/10 = 5/10.",
            "Simplify: divide both by 5 to get 1/2.",
        ],
    },
    "7.9": {
        "reminder": (
            "A unit fraction has numerator 1, such as 1/9. Ancient people used "
            "fractions to share food, measure land and divide goods, and "
            "Egyptian scribes often wrote a fraction as a sum of different "
            "unit fractions."
        ),
        "example_problem": "Write 5/6 as a sum of two unit fractions.",
        "example_steps": [
            "Try 1/2 first: 5/6 - 1/2 = 5/6 - 3/6 = 2/6.",
            "2/6 simplifies to 1/3, which is a unit fraction.",
            "So 5/6 = 1/2 + 1/3.",
            "Check: 3/6 + 2/6 = 5/6.",
        ],
    },
}


@dataclass
class ScaffoldContext:
    """Everything the scaffold builder needs about one question."""

    concept: str
    question_type: str = "MCQ"
    correct_answer: str = ""
    explanation: Optional[str] = None
    hint: Optional[str] = None
    section_code: Optional[str] = None
    section_explanation: Optional[str] = None   # fallback reminder text
    learning_objective: Optional[str] = None


@dataclass
class ScaffoldStep:
    level: int
    level_name: str
    title: str
    content: str
    steps: List[str] = field(default_factory=list)
    correct_answer: Optional[str] = None
    reveals_answer: bool = False


def next_level(current_level: Optional[int]) -> int:
    """Levels are given one at a time: 1, 2, 3, 4 (then stay at 4)."""

    return min((current_level or 0) + 1, MAX_LEVEL)


def default_hint(ctx: ScaffoldContext) -> str:
    if ctx.question_type == "NUMERICAL":
        return (
            f"Think about '{ctx.concept}'. Write down what you know from "
            "the question before you calculate."
        )

    return (
        f"Think about '{ctx.concept}'. Re-read the question slowly and rule "
        "out the options that cannot be right."
    )


def build_scaffold(level: int, ctx: ScaffoldContext) -> ScaffoldStep:
    """Build the content for one scaffold level (1-4)."""

    if level < 1 or level > MAX_LEVEL:
        raise ValueError(f"scaffold level must be between 1 and {MAX_LEVEL}")

    material = SECTION_SCAFFOLDS.get(ctx.section_code or "")

    if level == 1:
        return ScaffoldStep(
            level=1,
            level_name=LEVEL_NAMES[1],
            title="Small hint",
            content=ctx.hint or default_hint(ctx),
        )

    if level == 2:
        if material:
            reminder = material["reminder"]
        else:
            reminder = (
                ctx.section_explanation
                or ctx.learning_objective
                or f"Revise the idea of '{ctx.concept}' before trying again."
            )

        return ScaffoldStep(
            level=2,
            level_name=LEVEL_NAMES[2],
            title="Concept reminder",
            content=reminder,
        )

    if level == 3:
        if material:
            return ScaffoldStep(
                level=3,
                level_name=LEVEL_NAMES[3],
                title="Worked steps on a similar example",
                content=(
                    f"Similar example: {material['example_problem']} "
                    "Follow the same steps for your question."
                ),
                steps=list(material["example_steps"]),
            )

        return ScaffoldStep(
            level=3,
            level_name=LEVEL_NAMES[3],
            title="Steps to follow",
            content="Work through these steps for your question.",
            steps=list(GENERIC_STEPS),
        )

    explanation = ctx.explanation or "No written explanation is available."

    return ScaffoldStep(
        level=4,
        level_name=LEVEL_NAMES[4],
        title="Final explanation",
        content=explanation,
        correct_answer=ctx.correct_answer,
        reveals_answer=True,
    )
