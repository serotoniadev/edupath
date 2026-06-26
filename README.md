# 🎓 EduPath — Personalized AI Learning Roadmap Generator

> **Google ADK Hackathon Submission** | Track: *Agents for Good* | Built with [Google Agent Development Kit](https://adk.dev/) v2.2

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.2.0-orange.svg)](https://adk.dev/)
[![Gemini](https://img.shields.io/badge/Powered%20by-Gemini%202.5%20Flash-green.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Problem Statement

Every learner is unique — yet most online resources offer the same static paths. Students waste hours on irrelevant content, get overwhelmed by vague goals, and drop out before reaching mastery.

**EduPath** solves this by generating **personalized, week-by-week learning roadmaps** tailored to each student's subject, experience level, goals, and available time — powered by a multi-agent AI system built on the Google ADK.

---

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **Multi-Agent Orchestration** | Dedicated agents for evaluation, planning, and output formatting |
| 🔒 **Security Guardrails** | Detects PII, prompt injection, and academic dishonesty at intake |
| 🛠️ **MCP Tool Integration** | Searches real courses, calculates realistic study schedules, fetches learning tips |
| 👨‍🏫 **Human-in-the-Loop** | Tutor review checkpoint for high-risk or underspecified learning requests |
| 📋 **Structured Output** | Clean, markdown-formatted 8+ week roadmaps with resources and milestones |
| ♻️ **Resumable Sessions** | Workflow pauses for human review and resumes without losing state |

---

## 🏗️ Architecture

```
User Input (StudentProfile)
        │
        ▼
┌─────────────────────┐
│  security_checkpoint │  ← PII scrubbing, injection detection, dishonesty check
└─────────────────────┘
        │
   pass / fail
        │
┌──────────────────┐    ┌──────────────────────┐
│  initialize_flow │    │ security_event_handler│ ← 🚫 Alert + terminate
└──────────────────┘    └──────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│              orchestrator_agent (LlmAgent)             │
│   ┌──────────────────┐  ┌────────────────────────┐   │
│   │ skill_evaluator  │  │    roadmap_planner      │   │
│   │  (sub-agent)     │  │    (sub-agent)          │   │
│   └──────────────────┘  └────────────────────────┘   │
│            ↕ MCP Tools                                 │
│   search_courses | get_learning_tips | study_schedule  │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────┐
│ check_evaluation │ ← Route: auto_approve / needs_review
└──────────────────┘
        │
   auto / review
        │
┌──────────────────┐    ┌──────────────────┐
│ roadmap_planner  │◄───│  human_approval  │ ← 🧑‍🏫 HITL checkpoint
└──────────────────┘    └──────────────────┘
        │
        ▼
┌──────────────────┐
│  final_output    │ ← Markdown roadmap rendered in chat
└──────────────────┘
```

### ADK Capabilities Used

| Capability | Implementation |
|-----------|----------------|
| `Workflow` graph | Multi-step, conditional, branching pipeline |
| `LlmAgent` | `orchestrator_agent`, `skill_evaluator`, `roadmap_planner` |
| `FunctionNode` | `security_checkpoint`, `initialize_flow`, `check_evaluation`, `final_output` |
| `McpToolset` | `fastmcp` stdio server with 3 custom tools |
| `RequestInput` (HITL) | Tutor approval gate before roadmap generation |
| `ResumabilityConfig` | Workflow resumes after human review without losing state |
| Conditional routing | `{"pass": ..., "fail": ...}` and `{"auto_approve": ..., "needs_review": ...}` |

---

## 📂 Project Structure

```
edupath/
├── app/
│   ├── agent.py          # Main workflow graph, all agents, security checkpoint
│   ├── mcp_server.py     # FastMCP server: search_courses, get_learning_tips, calculate_study_schedule
│   └── config.py         # AgentConfig dataclass (model, temperature, thresholds)
├── tests/
│   └── unit/             # Unit tests for security checkpoint and routing logic
├── .env                  # API key & model config (not committed)
├── .gitignore
├── Makefile              # make playground | make test | make lint
├── pyproject.toml        # Dependencies with pinned ranges
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager
- A [Google AI Studio API key](https://aistudio.google.com/apikey) starting with `AIzaSy`

### 1. Clone & Install

```bash
git clone https://github.com/<your-username>/edupath.git
cd edupath
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

**.env**:
```
GOOGLE_API_KEY=AIzaSy...
GOOGLE_GENAI_USE_VERTEXAI=False
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Launch Playground

```bash
uv run adk web app --host 127.0.0.1 --port 18081 --reload_agents
```

Open [http://127.0.0.1:18081](http://127.0.0.1:18081) in your browser.

---

## 🧪 Testing

### Test 1 — Full Roadmap Generation

Send this in the playground chat:

```json
{
  "subject": "Python Programming",
  "experience_level": "beginner",
  "learning_goals": "Build a web scraper using BeautifulSoup",
  "available_hours_per_week": 10
}
```

**Expected**: 8-week structured roadmap with milestones, activities, and resources.

### Test 2 — Human-in-the-Loop (Tutor Review)

```json
{
  "subject": "Machine Learning",
  "experience_level": "beginner",
  "learning_goals": "learn coding",
  "available_hours_per_week": 3
}
```

**Expected**: Agent pauses and requests tutor feedback before generating roadmap.

### Test 3 — Security Block

```json
{
  "subject": "Math",
  "experience_level": "beginner",
  "learning_goals": "cheat on test for my final exam",
  "available_hours_per_week": 5
}
```

**Expected**: Immediate 🚫 Security Alert, workflow terminates without LLM calls.

### Run Unit Tests

```bash
uv run pytest tests/unit/ -v
```

---

## 🔒 Security Design

EduPath implements a multi-layered security checkpoint **before any LLM call**:

1. **PII Scrubbing** — Emails and phone numbers are detected via regex and replaced with `[EMAIL_REDACTED]` / `[PHONE_REDACTED]`
2. **Prompt Injection Detection** — Keywords like `"ignore previous instructions"`, `"jailbreak"`, `"override"` trigger immediate termination
3. **Academic Dishonesty Filter** — Cheating-related phrases are caught and blocked with a safety message
4. **Audit Logging** — Every checkpoint decision is logged to stderr as structured JSON for observability

---

## 🛠️ MCP Tools

The `mcp_server.py` exposes three tools via FastMCP (stdio transport):

| Tool | Description |
|------|-------------|
| `search_courses` | Returns curated course recommendations by subject and level |
| `get_learning_tips` | Fetches study tips and strategies for a given learning style |
| `calculate_study_schedule` | Computes week count and session breakdown from hours/week |

---

## 🌍 Impact — Why This Matters

- **Educational equity**: Personalized learning paths, previously only available to students with private tutors, now accessible to anyone
- **Dropout prevention**: Realistic schedules based on actual available time reduce overwhelm
- **Teacher augmentation**: HITL gate allows educators to review and improve AI-generated plans before delivery
- **Safe AI**: Security layer ensures the system cannot be weaponized for academic dishonesty

---

## 🤝 Contributing

This project was built for the Google ADK Hackathon. Contributions, issues, and feedback are welcome!

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🖼️ Assets

### Project Banner
![EduPath Banner](assets/cover_page_banner.png)

### System Architecture
![EduPath Workflow Diagram](assets/architecture_diagram.png)

---

## 🎙️ Demo Script

The spoken narration and video cues for demonstrating the project can be found in [DEMO_SCRIPT.txt](DEMO_SCRIPT.txt).

---

## 🙏 Acknowledgements

Built with ❤️ using:
- [Google Agent Development Kit (ADK)](https://adk.dev/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Google Gemini](https://ai.google.dev/)
- [Pydantic](https://docs.pydantic.dev/)
