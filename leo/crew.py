"""
Leo's tutoring crew — orchestration engine.

This module wires together all four agents into a sequential CrewAI pipeline
and exposes a high-level `run_tutoring_session` function used by the UI.

Orchestration pattern: **Sequential with feedback loop**
  1. Coordinator → analyses topic, creates study plan
  2. Explainer  → teaches the topic
  3. Quiz Master → generates structured quiz
  4. (Human-in-the-loop: student answers the quiz)
  5. Evaluator  → grades answers, identifies weak areas
  6. If score < 60%: loop back to Explainer for re-teaching, then re-quiz

Memory is enabled at the Crew level so agents share context across tasks.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from leo.agents import (
    create_coordinator,
    create_evaluator,
    create_explainer,
    create_quiz_master,
)
from leo.schemas import EvaluationOutput, QuizOutput
from leo.tasks import (
    create_coordination_task,
    create_evaluation_task,
    create_explanation_task,
    create_quiz_task,
    create_reteach_task,
)

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
MAX_RETEACH_ROUNDS = 2  # Prevent infinite feedback loops


@dataclass
class SessionState:
    """Tracks the state of a single tutoring session."""

    topic: str = ""
    student_name: str = "Student"
    study_plan: str = ""
    lesson: str = ""
    quiz: QuizOutput | None = None
    quiz_raw: str = ""
    evaluation: EvaluationOutput | None = None
    reteach_count: int = 0
    agent_logs: list[dict] = field(default_factory=list)

    def log(self, agent: str, action: str, content: str) -> None:
        """Record an agent action for the UI activity feed."""
        self.agent_logs.append(
            {"agent": agent, "action": action, "content": content}
        )


class LeoTutor:
    """
    High-level orchestrator that runs CrewAI crews step-by-step,
    pausing between quiz generation and evaluation so the student
    can answer questions (human-in-the-loop).
    """

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_MODEL
        self.state = SessionState()

        # Create agent instances (reused across crews)
        self._coordinator = create_coordinator(llm=self.model)
        self._explainer = create_explainer(llm=self.model)
        self._quiz_master = create_quiz_master(llm=self.model)
        self._evaluator = create_evaluator(llm=self.model)

    def _run_crew(self, agents: list[Agent], tasks: list[Task]) -> str:
        """Run a mini-crew and return the final raw output."""
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
        result = crew.kickoff()
        return result

    # ── Phase 1: Plan + Teach ────────────────────────────────────────────

    def plan_and_teach(self, topic: str, student_name: str = "Student") -> str:
        """
        Run the Coordinator and Explainer agents.
        Returns the lesson content as a string.
        """
        self.state = SessionState(topic=topic, student_name=student_name)

        # Coordinator creates study plan
        self.state.log("🎯 Coordinator", "Planning", f"Creating study plan for: {topic}")
        coord_task = create_coordination_task(
            self._coordinator, topic, student_name
        )

        # Explainer teaches
        self.state.log("📚 Explainer", "Teaching", f"Preparing lesson on: {topic}")
        explain_task = create_explanation_task(self._explainer, topic)

        result = self._run_crew(
            agents=[self._coordinator, self._explainer],
            tasks=[coord_task, explain_task],
        )

        self.state.lesson = str(result)
        self.state.log("📚 Explainer", "Completed", "Lesson delivered successfully")
        return self.state.lesson

    # ── Phase 2: Generate Quiz ───────────────────────────────────────────

    def generate_quiz(self, focus_areas: list[str] | None = None) -> QuizOutput:
        """
        Run the Quiz Master to create structured questions.
        Returns a QuizOutput pydantic model.
        """
        self.state.log(
            "🧩 Quiz Master", "Generating",
            f"Creating quiz for: {self.state.topic}"
        )

        quiz_task = create_quiz_task(
            self._quiz_master, self.state.topic, focus_areas
        )

        result = self._run_crew(
            agents=[self._quiz_master],
            tasks=[quiz_task],
        )

        # Parse the pydantic output
        try:
            if hasattr(result, "pydantic") and result.pydantic:
                self.state.quiz = result.pydantic
            else:
                # Fallback: try parsing the raw string
                raw = str(result)
                self.state.quiz = QuizOutput.model_validate_json(raw)
        except Exception:
            # Last resort: try to extract JSON from the text
            raw = str(result)
            # Find JSON-like content
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                json_str = raw[start:end]
                self.state.quiz = QuizOutput.model_validate_json(json_str)
            else:
                raise ValueError(f"Could not parse quiz output: {raw[:200]}")

        self.state.quiz_raw = self.state.quiz.model_dump_json(indent=2)
        self.state.log("🧩 Quiz Master", "Completed", "Quiz generated successfully")
        return self.state.quiz

    # ── Phase 3: Evaluate Answers ────────────────────────────────────────

    def evaluate_answers(self, student_answers: dict[int, str]) -> EvaluationOutput:
        """
        Run the Evaluator on the student's answers.
        Returns an EvaluationOutput pydantic model.

        student_answers: {question_number: "A"/"B"/"C"/"D"}
        """
        # Format answers for the evaluator
        answers_text = "\n".join(
            f"Question {qn}: {ans}" for qn, ans in sorted(student_answers.items())
        )

        self.state.log(
            "✅ Evaluator", "Grading",
            f"Evaluating {len(student_answers)} answers"
        )

        eval_task = create_evaluation_task(
            self._evaluator,
            self.state.topic,
            self.state.quiz_raw,
            answers_text,
        )

        result = self._run_crew(
            agents=[self._evaluator],
            tasks=[eval_task],
        )

        # Parse evaluation result
        try:
            if hasattr(result, "pydantic") and result.pydantic:
                self.state.evaluation = result.pydantic
            else:
                raw = str(result)
                self.state.evaluation = EvaluationOutput.model_validate_json(raw)
        except Exception:
            raw = str(result)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                json_str = raw[start:end]
                self.state.evaluation = EvaluationOutput.model_validate_json(json_str)
            else:
                raise ValueError(f"Could not parse evaluation output: {raw[:200]}")

        self.state.log(
            "✅ Evaluator", "Completed",
            f"Score: {self.state.evaluation.score}/{self.state.evaluation.total} "
            f"({self.state.evaluation.percentage:.0f}%)"
        )

        return self.state.evaluation

    # ── Phase 4: Feedback Loop (Re-teach) ────────────────────────────────

    def should_reteach(self) -> bool:
        """Check if the Evaluator flagged the student for re-teaching."""
        if self.state.evaluation is None:
            return False
        return (
            self.state.evaluation.needs_reteaching
            and self.state.reteach_count < MAX_RETEACH_ROUNDS
        )

    def reteach(self) -> str:
        """
        Re-teach the weak areas identified by the Evaluator.
        Returns the re-teaching lesson content.
        """
        if self.state.evaluation is None:
            raise ValueError("No evaluation to base re-teaching on")

        self.state.reteach_count += 1
        weak = self.state.evaluation.weak_areas

        self.state.log(
            "🔄 Coordinator", "Re-routing",
            f"Student needs re-teaching on: {', '.join(weak)}"
        )
        self.state.log(
            "📚 Explainer", "Re-teaching",
            f"Round {self.state.reteach_count}: Focusing on weak areas"
        )

        reteach_task = create_reteach_task(
            self._explainer, self.state.topic, weak
        )

        result = self._run_crew(
            agents=[self._explainer],
            tasks=[reteach_task],
        )

        lesson = str(result)
        self.state.lesson = lesson
        self.state.log("📚 Explainer", "Completed", "Re-teaching delivered")
        return lesson
