"""
Leo: Multi-Agent AI Tutor — Gradio Interface

A rich, interactive Gradio application that guides the student through
a full tutoring session:
  1. Enter name & topic → Coordinator plans, Explainer teaches
  2. Quiz Master presents multiple-choice questions
  3. Student answers → Evaluator grades and gives feedback
  4. If score < 60%: automatic re-teach loop with new quiz

The interface shows which agent is active at each step and maintains
a live activity log of all agent handoffs.
"""

from __future__ import annotations

import gradio as gr

from leo.crew import LeoTutor
from leo.schemas import QuizOutput, EvaluationOutput

# ── Globals ──────────────────────────────────────────────────────────────────
tutor: LeoTutor | None = None

CSS = """
/* ── Dark theme overrides ─────────────────────────────────────────────── */
.gradio-container {
    max-width: 1000px !important;
    margin: 0 auto !important;
}

/* Agent badges */
.agent-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
    margin: 2px 4px;
}
.badge-coordinator { background: #3b82f6; color: white; }
.badge-explainer   { background: #8b5cf6; color: white; }
.badge-quizmaster  { background: #f59e0b; color: white; }
.badge-evaluator   { background: #10b981; color: white; }

/* Activity log */
.activity-log {
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 0.85em;
    line-height: 1.6;
    padding: 12px;
    background: #1a1a2e;
    border-radius: 8px;
    border: 1px solid #333;
    color: #e0e0e0;
    max-height: 400px;
    overflow-y: auto;
}

/* Score card */
.score-card {
    text-align: center;
    padding: 24px;
    border-radius: 12px;
    margin: 16px 0;
}
.score-pass { background: linear-gradient(135deg, #065f46, #047857); color: white; }
.score-fail { background: linear-gradient(135deg, #7f1d1d, #991b1b); color: white; }

/* Header */
.leo-header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #1e1b4b, #312e81, #4c1d95);
    border-radius: 12px;
    margin-bottom: 16px;
    color: white;
}
.leo-header h1 { margin: 0; font-size: 2em; }
.leo-header p  { margin: 4px 0 0; opacity: 0.8; }
"""


def format_activity_log(logs: list[dict]) -> str:
    """Format agent activity logs as styled HTML."""
    if not logs:
        return '<div class="activity-log"><em>No activity yet. Enter a topic to begin.</em></div>'

    badge_map = {
        "🎯 Coordinator": "badge-coordinator",
        "📚 Explainer": "badge-explainer",
        "🧩 Quiz Master": "badge-quizmaster",
        "✅ Evaluator": "badge-evaluator",
        "🔄 Coordinator": "badge-coordinator",
    }

    lines = []
    for i, log in enumerate(logs):
        badge_class = badge_map.get(log["agent"], "badge-coordinator")
        lines.append(
            f'<span class="agent-badge {badge_class}">{log["agent"]}</span> '
            f'<strong>{log["action"]}</strong> — {log["content"]}'
        )

    return '<div class="activity-log">' + "<br>".join(lines) + "</div>"


def format_quiz_display(quiz: QuizOutput) -> str:
    """Format quiz questions as readable markdown."""
    md = f"## 🧩 Quiz: {quiz.topic}\n\n"
    md += "Answer each question by selecting A, B, C, or D.\n\n---\n\n"

    for q in quiz.questions:
        md += f"### Question {q.question_number}\n"
        md += f"**{q.question}**\n\n"
        for opt in q.options:
            md += f"- {opt}\n"
        md += "\n---\n\n"

    return md


def format_evaluation_display(evaluation: EvaluationOutput) -> str:
    """Format evaluation results as rich markdown."""
    pct = evaluation.percentage
    score_class = "score-pass" if pct >= 60 else "score-fail"
    emoji = "🎉" if pct >= 80 else ("✅" if pct >= 60 else "📚")

    md = f"""
<div class="score-card {score_class}">
    <h2>{emoji} Score: {evaluation.score}/{evaluation.total} ({pct:.0f}%)</h2>
</div>

## Detailed Feedback

"""

    for ev in evaluation.evaluations:
        icon = "✅" if ev.is_correct else "❌"
        md += f"### {icon} Question {ev.question_number}\n"
        md += f"- **Your answer:** {ev.student_answer}\n"
        md += f"- **Correct answer:** {ev.correct_answer}\n"
        if not ev.is_correct:
            md += f"- **Feedback:** {ev.feedback}\n"
        md += "\n"

    if evaluation.weak_areas:
        md += "### 🔍 Areas to Review\n"
        for area in evaluation.weak_areas:
            md += f"- {area}\n"
        md += "\n"

    md += f"### 💬 Overall\n{evaluation.overall_feedback}\n"

    if evaluation.needs_reteaching:
        md += (
            "\n> ⚠️ **Score below 60% — a focused re-teaching session "
            "will start automatically!**\n"
        )

    return md


# ── Gradio Event Handlers ───────────────────────────────────────────────────

def start_session(student_name: str, topic: str):
    """Phase 1: Coordinator plans → Explainer teaches → Quiz Master generates."""
    global tutor

    if not topic.strip():
        return (
            "⚠️ Please enter a topic.",
            "",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    name = student_name.strip() or "Student"
    tutor = LeoTutor()

    # Phase 1: Plan and Teach
    lesson = tutor.plan_and_teach(topic.strip(), name)
    log_html = format_activity_log(tutor.state.agent_logs)

    # Phase 2: Generate Quiz
    quiz = tutor.generate_quiz()
    quiz_display = format_quiz_display(quiz)
    log_html = format_activity_log(tutor.state.agent_logs)

    return (
        log_html,                        # activity_log
        lesson,                          # lesson_output
        quiz_display,                    # quiz_display
        gr.update(visible=True),         # quiz_section
        gr.update(visible=True),         # answer_section
        gr.update(visible=False),        # eval_section
        gr.update(visible=True),         # lesson_section
        gr.update(visible=False),        # reteach_section
    )


def submit_answers(a1: str, a2: str, a3: str, a4: str):
    """Phase 3: Evaluator grades answers. Phase 4: Optional re-teach loop."""
    global tutor

    if tutor is None or tutor.state.quiz is None:
        return (
            "⚠️ No active quiz. Please start a session first.",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
        )

    # Collect student answers
    answers = {}
    for i, ans in enumerate([a1, a2, a3, a4], 1):
        clean = ans.strip().upper()
        if clean and clean in ("A", "B", "C", "D"):
            answers[i] = clean
        else:
            answers[i] = ans.strip().upper()[:1] if ans.strip() else "?"

    # Phase 3: Evaluate
    evaluation = tutor.evaluate_answers(answers)
    eval_display = format_evaluation_display(evaluation)
    log_html = format_activity_log(tutor.state.agent_logs)

    # Phase 4: Check for re-teaching
    reteach_content = ""
    reteach_visible = False
    if tutor.should_reteach():
        reteach_lesson = tutor.reteach()
        reteach_quiz = tutor.generate_quiz(
            focus_areas=tutor.state.evaluation.weak_areas
        )
        reteach_content = (
            "## 🔄 Re-Teaching Session\n\n"
            f"{reteach_lesson}\n\n---\n\n"
            f"{format_quiz_display(reteach_quiz)}"
        )
        reteach_visible = True
        log_html = format_activity_log(tutor.state.agent_logs)

    return (
        log_html,                                    # activity_log
        eval_display,                                # eval_output
        gr.update(visible=True),                     # eval_section
        gr.update(visible=reteach_visible, value=reteach_content),  # reteach_section
    )


# ── Build the UI ─────────────────────────────────────────────────────────────

def create_app() -> gr.Blocks:
    """Construct and return the Gradio Blocks application."""

    with gr.Blocks(
        css=CSS,
        title="Leo — Multi-Agent AI Tutor",
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
            neutral_hue="slate",
        ),
    ) as app:

        # ── Header ──
        gr.HTML(
            '<div class="leo-header">'
            "<h1>🦁 Leo — Multi-Agent AI Tutor</h1>"
            "<p>Four AI agents collaborate to teach you any topic</p>"
            '<p style="font-size:0.8em; margin-top:8px;">'
            "🎯 Coordinator &nbsp;→&nbsp; 📚 Explainer &nbsp;→&nbsp; "
            "🧩 Quiz Master &nbsp;→&nbsp; ✅ Evaluator"
            "</p></div>"
        )

        with gr.Row():
            # ── Left Column: Controls & Activity ──
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Start a Session")
                student_name = gr.Textbox(
                    label="Your Name",
                    placeholder="Enter your name...",
                    value="Student",
                )
                topic_input = gr.Textbox(
                    label="What do you want to learn?",
                    placeholder="e.g., Photosynthesis, Newton's Laws, Python Decorators...",
                    lines=2,
                )
                start_btn = gr.Button(
                    "🚀 Start Learning",
                    variant="primary",
                    size="lg",
                )

                gr.Markdown("### 🔄 Agent Activity")
                activity_log = gr.HTML(
                    value=format_activity_log([]),
                    label="Activity Feed",
                )

            # ── Right Column: Content ──
            with gr.Column(scale=2):
                # Lesson Section
                with gr.Group(visible=False) as lesson_section:
                    gr.Markdown("### 📚 Lesson")
                    lesson_output = gr.Markdown(
                        label="Lesson Content",
                    )

                # Quiz Section
                with gr.Group(visible=False) as quiz_section:
                    gr.Markdown("### 🧩 Quiz Time!")
                    quiz_display = gr.Markdown(
                        label="Quiz Questions",
                    )

                # Answer Section
                with gr.Group(visible=False) as answer_section:
                    gr.Markdown("### ✏️ Your Answers")
                    gr.Markdown(
                        "Enter A, B, C, or D for each question."
                    )
                    with gr.Row():
                        a1 = gr.Textbox(label="Q1", placeholder="A/B/C/D", max_lines=1)
                        a2 = gr.Textbox(label="Q2", placeholder="A/B/C/D", max_lines=1)
                        a3 = gr.Textbox(label="Q3", placeholder="A/B/C/D", max_lines=1)
                        a4 = gr.Textbox(label="Q4", placeholder="A/B/C/D", max_lines=1)
                    submit_btn = gr.Button(
                        "📤 Submit Answers",
                        variant="primary",
                    )

                # Evaluation Section
                with gr.Group(visible=False) as eval_section:
                    gr.Markdown("### ✅ Evaluation Results")
                    eval_output = gr.Markdown(
                        label="Evaluation",
                    )

                # Re-teach Section (feedback loop)
                reteach_section = gr.Markdown(
                    visible=False,
                    label="Re-Teaching",
                )

        # ── Wire Events ──
        start_btn.click(
            fn=start_session,
            inputs=[student_name, topic_input],
            outputs=[
                activity_log,
                lesson_output,
                quiz_display,
                quiz_section,
                answer_section,
                eval_section,
                lesson_section,
                reteach_section,
            ],
        )

        submit_btn.click(
            fn=submit_answers,
            inputs=[a1, a2, a3, a4],
            outputs=[
                activity_log,
                eval_output,
                eval_section,
                reteach_section,
            ],
        )

    return app


# ── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.launch(share=False, server_name="0.0.0.0", server_port=7860)
