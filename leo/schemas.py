"""
Pydantic models for structured data exchanged between Leo's agents.

These schemas enforce consistent communication: the Quiz Master produces
QuizOutput objects, and the Evaluator returns EvaluationOutput objects.
Using structured output guarantees that downstream agents (and the UI)
always receive well-formed JSON instead of free-text.
"""

from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    """A single quiz question with multiple-choice options."""
    question_number: int = Field(description="Sequential question number starting from 1")
    question: str = Field(description="The quiz question text")
    options: list[str] = Field(description="Four multiple-choice options labelled A, B, C, D")
    correct_answer: str = Field(description="The correct option letter (A, B, C, or D)")
    explanation: str = Field(description="Brief explanation of why the answer is correct")


class QuizOutput(BaseModel):
    """Structured output from the Quiz Master agent."""
    topic: str = Field(description="The topic being quizzed")
    questions: list[QuizQuestion] = Field(description="List of quiz questions")


class TopicEvaluation(BaseModel):
    """Evaluation result for a single question."""
    question_number: int = Field(description="Which question this evaluates")
    student_answer: str = Field(description="The student's submitted answer")
    correct_answer: str = Field(description="The actual correct answer")
    is_correct: bool = Field(description="Whether the student's answer matches")
    feedback: str = Field(description="Detailed feedback for the student")


class EvaluationOutput(BaseModel):
    """Structured output from the Evaluator agent."""
    topic: str = Field(description="The topic that was evaluated")
    score: int = Field(description="Number of correct answers")
    total: int = Field(description="Total number of questions")
    percentage: float = Field(description="Score as a percentage")
    evaluations: list[TopicEvaluation] = Field(description="Per-question evaluation details")
    weak_areas: list[str] = Field(description="Topics/concepts the student struggled with")
    needs_reteaching: bool = Field(description="True if the student scored below 60%")
    overall_feedback: str = Field(description="Encouraging overall summary for the student")
