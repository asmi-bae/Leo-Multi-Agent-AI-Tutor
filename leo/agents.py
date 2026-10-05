"""
Agent definitions for Leo's multi-agent tutoring system.

Each function constructs a CrewAI Agent with its own role, goal, backstory
(from prompts.py), and optional tools.  Agents are created as functions
rather than module-level singletons so that the LLM instance can be
injected at runtime (useful for switching models or during tests).
"""

from crewai import Agent

from leo.prompts import (
    COORDINATOR_BACKSTORY,
    COORDINATOR_GOAL,
    COORDINATOR_ROLE,
    EVALUATOR_BACKSTORY,
    EVALUATOR_GOAL,
    EVALUATOR_ROLE,
    EXPLAINER_BACKSTORY,
    EXPLAINER_GOAL,
    EXPLAINER_ROLE,
    QUIZ_MASTER_BACKSTORY,
    QUIZ_MASTER_GOAL,
    QUIZ_MASTER_ROLE,
)


def create_coordinator(llm: str | None = None) -> Agent:
    """Create the Coordinator agent that plans and delegates."""
    return Agent(
        role=COORDINATOR_ROLE,
        goal=COORDINATOR_GOAL,
        backstory=COORDINATOR_BACKSTORY,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_explainer(llm: str | None = None) -> Agent:
    """Create the Explainer agent that teaches concepts."""
    return Agent(
        role=EXPLAINER_ROLE,
        goal=EXPLAINER_GOAL,
        backstory=EXPLAINER_BACKSTORY,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_quiz_master(llm: str | None = None) -> Agent:
    """Create the Quiz Master agent that generates questions."""
    return Agent(
        role=QUIZ_MASTER_ROLE,
        goal=QUIZ_MASTER_GOAL,
        backstory=QUIZ_MASTER_BACKSTORY,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_evaluator(llm: str | None = None) -> Agent:
    """Create the Evaluator agent that grades answers."""
    return Agent(
        role=EVALUATOR_ROLE,
        goal=EVALUATOR_GOAL,
        backstory=EVALUATOR_BACKSTORY,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )
