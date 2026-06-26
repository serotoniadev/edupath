# ruff: noqa
# Copyright 2026 Google LLC

import json
from google.adk.agents import LlmAgent
from google.adk.workflow import Workflow, START, FunctionNode
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.tools import AgentTool
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from .config import config

# --- SCHEMAS ---

class StudentProfile(BaseModel):
    subject: str = Field(description="The subject or skill the student wants to learn.")
    experience_level: str = Field(description="Current experience level (e.g., beginner, intermediate, advanced).")
    learning_goals: str = Field(description="What the student hopes to achieve.")
    available_hours_per_week: int = Field(description="Number of hours per week the student can study.")

class SkillEvaluation(BaseModel):
    detected_gaps: List[str] = Field(description="Skills or concepts the student is missing or needs to learn.")
    recommended_focus_areas: List[str] = Field(description="Main areas the student should focus on.")
    needs_review: bool = Field(description="Whether the profile needs human/teacher review.")
    justification: str = Field(description="Brief explanation of the evaluation results.")

class Milestone(BaseModel):
    week: int = Field(description="The week number of this milestone.")
    topic: str = Field(description="The topic to be covered.")
    activities: List[str] = Field(description="Actionable learning activities or tasks.")
    resources: List[str] = Field(description="Recommended free learning resources or search queries.")

class LearningRoadmap(BaseModel):
    subject: str = Field(description="The subject of the learning roadmap.")
    estimated_weeks: int = Field(description="Total estimated weeks to reach the goal.")
    milestones: List[Milestone] = Field(description="Weekly breakdown of milestones.")
    additional_tips: str = Field(description="General advice for succeeding in this learning path.")

import sys
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Configure MCP Toolset using the active python virtualenv interpreter
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["app/mcp_server.py"]
        )
    )
)

# --- SUB-AGENTS ---

# Specialist Agent 1: Evaluator
skill_evaluator = LlmAgent(
    name="skill_evaluator",
    model=config.model,
    instruction=(
        "You are a specialized Skill Evaluator. Analyze the student's learning goals and background: "
        "Subject: {subject}\n"
        "Experience: {experience_level}\n"
        "Goals: {learning_goals}\n"
        "Hours/week: {available_hours_per_week}\n"
        "Use the get_learning_tips and calculate_study_schedule tools to analyze study strategies and goals. "
        "Identify key knowledge gaps, core focus areas, and determine if tutor review is required. "
        "If the learning goals are extremely vague or broad (e.g., 'learn coding' or 'master math') or hours/week < 5, set needs_review to True. "
        "Format your output as a JSON dict with keys: 'detected_gaps' (list of strings), "
        "'recommended_focus_areas' (list of strings), 'needs_review' (boolean), and 'justification' (string)."
    ),
    tools=[mcp_toolset]
)

# Orchestrator Agent: Routes evaluation tasks
orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=config.model,
    instruction=(
        "You are the Educational Orchestrator. Your task is to coordinate the evaluation of the student's profile. "
        "Call the skill_evaluator tool to analyze the student's input: "
        "Subject: {subject}, Experience: {experience_level}, Goals: {learning_goals}, Hours: {available_hours_per_week}. "
        "Once you receive the evaluation, output the exact JSON dictionary returned by the tool without any extra markdown or conversational text."
    ),
    tools=[AgentTool(skill_evaluator)],
    output_key="evaluation"
)

# Specialist Agent 2: Planner
roadmap_planner = LlmAgent(
    name="roadmap_planner",
    model=config.model,
    instruction=(
        "You are a Curriculum Designer. Create a custom learning roadmap. "
        "Student Subject: {subject}\n"
        "Experience Level: {experience_level}\n"
        "Learning Goals: {learning_goals}\n"
        "Hours per week: {available_hours_per_week}\n"
        "Skill Evaluation: {evaluation}\n"
        "Tutor Notes: {human_notes}\n"
        "Use the search_courses tool to locate high-quality study resources for the milestones. "
        "Use the calculate_study_schedule tool to refine how long each milestone will take. "
        "Design a step-by-step curriculum with weekly milestones and study resources. "
        "Output a JSON dictionary conforming to the learning roadmap schema."
    ),
    output_schema=LearningRoadmap,
    output_key="roadmap",
    tools=[mcp_toolset]
)

# --- WORKFLOW FUNCTIONS ---

def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    import re
    import datetime
    import sys
    
    input_text = ""
    if isinstance(node_input, StudentProfile):
        input_text = f"{node_input.subject} {node_input.learning_goals}"
    elif isinstance(node_input, dict):
        input_text = f"{node_input.get('subject', '')} {node_input.get('learning_goals', '')}"
    elif hasattr(node_input, "parts") and node_input.parts:
        input_text = node_input.parts[0].text
    elif isinstance(node_input, str):
        input_text = node_input

    # 1. PII Scrubbing (Email & Phone)
    email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_regex = r'\b\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
    
    scrubbed_text = input_text
    has_pii = False
    if re.search(email_regex, scrubbed_text):
        scrubbed_text = re.sub(email_regex, "[EMAIL_REDACTED]", scrubbed_text)
        has_pii = True
    if re.search(phone_regex, scrubbed_text):
        scrubbed_text = re.sub(phone_regex, "[PHONE_REDACTED]", scrubbed_text)
        has_pii = True

    # 2. Prompt Injection Detection
    injection_keywords = [
        "ignore previous instructions", "system prompt", "override instructions",
        "instead of the above", "you are now a", "bypass", "jailbreak", "developer mode"
    ]
    has_injection = any(kw in input_text.lower() for kw in injection_keywords)

    # 3. Domain-Specific Rule: Academic Dishonesty Check
    cheating_keywords = [
        "write my essay", "do my homework", "cheat on test", "give answers to exam", "cheat on quiz"
    ]
    has_academic_dishonesty = any(kw in input_text.lower() for kw in cheating_keywords)

    severity = "INFO"
    details = "Input profile checked and passed cleanly."
    route = "pass"

    if has_pii:
        severity = "WARNING"
        details = "PII detected and redacted from student profile."
    if has_injection:
        severity = "CRITICAL"
        details = "Potential prompt injection attack detected."
        route = "fail"
    elif has_academic_dishonesty:
        severity = "CRITICAL"
        details = "Academic dishonesty / cheating attempt detected."
        route = "fail"

    audit_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": ctx.session.id,
        "event": "security_checkpoint_evaluation",
        "severity": severity,
        "details": details,
        "route_selected": route
    }
    print(json.dumps(audit_log), file=sys.stderr)

    output_data = node_input
    if route == "pass":
        if isinstance(node_input, StudentProfile):
            node_input.learning_goals = re.sub(email_regex, "[EMAIL_REDACTED]", node_input.learning_goals)
            node_input.learning_goals = re.sub(phone_regex, "[PHONE_REDACTED]", node_input.learning_goals)
            output_data = node_input
        elif isinstance(node_input, dict):
            node_input["learning_goals"] = re.sub(email_regex, "[EMAIL_REDACTED]", node_input.get("learning_goals", ""))
            node_input["learning_goals"] = re.sub(phone_regex, "[PHONE_REDACTED]", node_input.get("learning_goals", ""))
            output_data = node_input
        elif hasattr(node_input, "parts") and node_input.parts:
            node_input.parts[0].text = scrubbed_text
            output_data = node_input
        elif isinstance(node_input, str):
            output_data = scrubbed_text

    return Event(
        output=output_data,
        route=route
    )

def security_event_handler(ctx: Context, node_input: Any) -> Event:
    msg = "🚫 Security Alert: Your request was flagged by our safety guardrails. We cannot assist with cheating, academic dishonesty, or prompt overrides."
    yield Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=msg)]
        )
    )

def initialize_flow(ctx: Context, node_input: Any) -> Event:
    data = {}
    if isinstance(node_input, StudentProfile):
        data = node_input.model_dump()
    elif isinstance(node_input, dict):
        data = node_input
    elif hasattr(node_input, "parts") and node_input.parts:
        text = node_input.parts[0].text.strip()
        try:
            data = json.loads(text)
        except Exception:
            data = {
                "subject": "Python Programming",
                "experience_level": "beginner",
                "learning_goals": text or "learn programming",
                "available_hours_per_week": 10
            }
    else:
        data = {
            "subject": "Python Programming",
            "experience_level": "beginner",
            "learning_goals": "Build a web scraper",
            "available_hours_per_week": 10
        }

    return Event(
        output=data,
        state={
            "subject": data.get("subject", "General"),
            "experience_level": data.get("experience_level", "beginner"),
            "learning_goals": data.get("learning_goals", ""),
            "available_hours_per_week": data.get("available_hours_per_week", 5),
            "human_notes": "None"
        }
    )

def check_evaluation(ctx: Context, node_input: Any) -> Event:
    evaluation_str = ""
    if hasattr(node_input, "parts") and node_input.parts:
        evaluation_str = node_input.parts[0].text.strip()
    elif isinstance(node_input, str):
        evaluation_str = node_input
    
    if evaluation_str.startswith("```json"):
        evaluation_str = evaluation_str[7:]
    if evaluation_str.startswith("```"):
        evaluation_str = evaluation_str[3:]
    if evaluation_str.endswith("```"):
        evaluation_str = evaluation_str[:-3]
    evaluation_str = evaluation_str.strip()

    try:
        evaluation = json.loads(evaluation_str)
    except Exception:
        evaluation = {
            "detected_gaps": ["General foundations"],
            "recommended_focus_areas": ["Basic concepts"],
            "needs_review": False,
            "justification": "Could not parse evaluation JSON."
        }

    return Event(
        output=evaluation,
        state={"evaluation": evaluation},
        route="needs_review" if evaluation.get("needs_review", False) else "auto_approve"
    )

async def human_approval(ctx: Context, node_input: Any):
    if not ctx.resume_inputs or "teacher_feedback" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="teacher_feedback",
            message="Your goals/schedule require tutor review. Please provide feedback/adjustments, or type 'Approved' to proceed."
        )
        return

    feedback = ctx.resume_inputs["teacher_feedback"]
    yield Event(
        output=feedback,
        state={"human_notes": feedback}
    )

def final_output(ctx: Context, node_input: Any) -> Event:
    roadmap = ctx.state.get("roadmap", {})
    subject = roadmap.get("subject", "Curriculum")
    weeks = roadmap.get("estimated_weeks", 0)
    milestones = roadmap.get("milestones", [])
    tips = roadmap.get("additional_tips", "")
    human_notes = ctx.state.get("human_notes", "None")

    md = f"# 🚀 Learning Roadmap: {subject}\n"
    md += f"**Estimated Duration**: {weeks} weeks\n"
    if human_notes and human_notes != "None":
        md += f"**Tutor Notes**: *{human_notes}*\n\n"
    md += "\n## Weekly Milestones\n"
    
    for ms in milestones:
        md += f"### Week {ms.get('week')}: {ms.get('topic')}\n"
        md += "**Activities**:\n"
        for act in ms.get("activities", []):
            md += f"- {act}\n"
        md += "**Suggested Resources**:\n"
        for res in ms.get("resources", []):
            md += f"- {res}\n"
        md += "\n"

    md += "## 💡 General Tips\n"
    md += tips + "\n"

    yield Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=md)]
        )
    )
    yield Event(output=roadmap)

# --- WORKFLOW GRAPH CONFIG ---

root_agent = Workflow(
    name="edupath_workflow",
    description="Orchestrates student skill evaluation and personalized roadmap planning.",
    input_schema=StudentProfile,
    edges=[
        ('START', security_checkpoint),
        (security_checkpoint, {"pass": initialize_flow, "fail": security_event_handler}),
        (initialize_flow, orchestrator_agent),
        (orchestrator_agent, check_evaluation),
        (check_evaluation, {"needs_review": human_approval, "auto_approve": roadmap_planner}),
        (human_approval, roadmap_planner),
        (roadmap_planner, final_output)
    ]
)

app = App(
    name="app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True)
)
