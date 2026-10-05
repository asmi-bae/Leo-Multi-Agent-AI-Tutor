"""
Task definitions for Leo's tutoring pipeline.

Each function creates a CrewAI Task that is bound to a specific agent.
Tasks are assembled in sequence by the crew: Coordinate → Explain → Quiz → Evaluate.
The Quiz and Evaluate tasks use output_pydantic for structured output.
"""

from crewai import Task

from leo.schemas import EvaluationOutput, QuizOutput


def create_coordination_task(agent, topic: str, student_name: str = "Student") -> Task:
    """
    Task 1: The Coordinator analyses the student's topic request and creates
    a structured study plan with key sub-topics to cover.
    """
    return Task(
        description=(
            f"The student '{student_name}' wants to learn about: **{topic}**\n\n"
            "Your job:\n"
            "1. Identify 3-5 key sub-topics that must be covered.\n"
            "2. Order them from foundational to advanced.\n"
            "3. Write a brief study plan (bullet points) that the Explainer "
            "will follow.\n"
            "4. If the topic is too vague, note what assumptions you're making.\n\n"
            "Output a clear, structured study plan."
        ),
        expected_output=(
            "A structured study plan with numbered sub-topics, ordered from "
            "basic to advanced, ready for the Explainer to follow."
        ),
        agent=agent,
    )


def create_explanation_task(agent, topic: str) -> Task:
    """
    Task 2: The Explainer teaches the concept following the Coordinator's plan.
    The output from Task 1 is automatically passed as context.
    """
    return Task(
        description=(
            f"Teach the topic **{topic}** following the study plan provided "
            "by the Coordinator (see context above).\n\n"
            "For each sub-topic in the plan:\n"
            "1. Give a one-line summary.\n"
            "2. Use a real-world analogy.\n"
            "3. Provide a clear, detailed explanation.\n"
            "4. End with a 'Key Takeaway' summary.\n\n"
            "Make the explanation engaging and accessible. Use markdown formatting."
        ),
        expected_output=(
            "A comprehensive, well-structured lesson covering all sub-topics "
            "from the study plan, with analogies and key takeaways."
        ),
        agent=agent,
    )


def create_reteach_task(agent, topic: str, weak_areas: list[str]) -> Task:
    """
    Task 2b (Feedback Loop): Re-teach only the weak areas identified by the Evaluator.
    """
    areas_text = "\n".join(f"  - {area}" for area in weak_areas)
    return Task(
        description=(
            f"The student struggled with specific areas of **{topic}**. "
            "Re-teach ONLY the following weak areas using different examples "
            "and analogies than before:\n\n"
            f"{areas_text}\n\n"
            "Use simpler language and more relatable analogies this time. "
            "Focus on building intuition rather than technical depth."
        ),
        expected_output=(
            "A focused, simplified re-explanation of the weak areas "
            "using fresh examples and analogies."
        ),
        agent=agent,
    )


def create_quiz_task(agent, topic: str, focus_areas: list[str] | None = None) -> Task:
    """
    Task 3: The Quiz Master generates structured quiz questions.
    Uses output_pydantic for guaranteed JSON structure.
    """
    focus_text = ""
    if focus_areas:
        areas = ", ".join(focus_areas)
        focus_text = (
            f"\n\nFocus your questions on these specific areas: {areas}. "
            "Create NEW questions different from any previous quiz."
        )

    return Task(
        description=(
            f"Create a quiz to test the student's understanding of **{topic}** "
            "based on the lesson that was just taught (see context above).\n\n"
            "Requirements:\n"
            "• Generate exactly 4 multiple-choice questions.\n"
            "• Each question must have 4 options: A, B, C, D.\n"
            "• Include the correct answer letter and a brief explanation.\n"
            "• Test conceptual understanding, not just memorization.\n"
            f"• Set the topic field to '{topic}'."
            f"{focus_text}"
        ),
        expected_output=(
            "A QuizOutput JSON object with topic and a list of 4 questions, "
            "each having question_number, question, options, correct_answer, "
            "and explanation."
        ),
        agent=agent,
        output_pydantic=QuizOutput,
    )


def create_evaluation_task(
    agent, topic: str, quiz_json: str, student_answers: str
) -> Task:
    """
    Task 4: The Evaluator grades the student's answers and gives feedback.
    Uses output_pydantic for structured output.
    """
    return Task(
        description=(
            f"Evaluate the student's quiz answers for the topic **{topic}**.\n\n"
            f"**Quiz Questions:**\n{quiz_json}\n\n"
            f"**Student's Answers:**\n{student_answers}\n\n"
            "Instructions:\n"
            "1. Compare each student answer to the correct answer.\n"
            "2. Mark each as correct or incorrect.\n"
            "3. For incorrect answers, explain what the right answer is and why.\n"
            "4. Calculate the score and percentage.\n"
            "5. If the percentage is below 60, set needs_reteaching to true "
            "and list the specific weak areas.\n"
            "6. End with an encouraging overall_feedback message.\n"
            f"7. Set the topic field to '{topic}'."
        ),
        expected_output=(
            "An EvaluationOutput JSON object with score, total, percentage, "
            "per-question evaluations, weak_areas, needs_reteaching flag, "
            "and overall_feedback."
        ),
        agent=agent,
        output_pydantic=EvaluationOutput,
    )
