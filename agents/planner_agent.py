"""
agents/planner_agent.py — Reads the requirements markdown and produces
a structured JSON plan that all other agents will use.
"""
import json
import re
import time
from pathlib import Path

from llm_client import LLMClient
from agents.base_agent import AgentState, Status


SYSTEM_PROMPT = """You are a senior software architect. Your job is to read a project requirements document
and produce a detailed, structured JSON plan for building a React + Vite prototype.

RETURN ONLY VALID JSON — no markdown fences, no explanation, no preamble.

The JSON must follow this exact schema:
{
  "project_name": "string",
  "description": "string (2-3 sentences)",
  "tech_stack": ["React", "Vite", "TypeScript", "Tailwind CSS", ...],
  "key_features": ["feature1", "feature2", ...],
  "pages": [
    {"name": "PageName", "route": "/route", "description": "what this page does"}
  ],
  "components": ["ComponentName1", "ComponentName2", ...],
  "api_endpoints": [
    {"method": "GET", "path": "/api/resource", "description": "what it returns"}
  ],
  "data_models": [
    {"name": "ModelName", "fields": [{"name": "field", "type": "string", "required": true}]}
  ],
  "state_management": "string (e.g. Zustand / React Context / Redux Toolkit)",
  "styling": "string (e.g. Tailwind CSS + shadcn/ui)",
  "test_framework": "string (e.g. Vitest + React Testing Library)",
  "backend_type": "string (mock | express | fastapi | none)",
  "deployment_target": "string (e.g. Vercel / Docker / Netlify)",
  "agent_tasks": {
    "design":   "specific instruction for the UI/UX design agent",
    "dev":      "specific instruction for the development agent",
    "tests":    "specific instruction for the test agent",
    "swagger":  "specific instruction for the API docs agent",
    "lld":      "specific instruction for the low-level design agent",
    "startup":  "specific instruction for the startup guide agent",
    "readme":   "specific instruction for the readme agent"
  }
}"""


class PlannerAgent:
    """
    Runs SYNCHRONOUSLY before all parallel agents.
    Returns a dict (the plan) and populates its own AgentState.
    """

    def __init__(self, requirements: str, global_log: list):
        self.requirements = requirements
        self.global_log   = global_log
        self.llm          = LLMClient()
        self.state        = AgentState(name="Planner", icon="🧠")

    def _glog(self, msg: str):
        self.state.log(msg)
        ts = time.strftime("%H:%M:%S")
        self.global_log.append(f"[{ts}] {msg}")

    async def run(self) -> dict:
        self.state.status     = Status.RUNNING
        self.state.start_time = time.time()
        self.state.activity   = "Analysing requirements…"
        self.state.progress   = 10
        self._glog("🧠 Planner Agent started — analysing requirements")

        user_msg = f"""Here are the project requirements:

---
{self.requirements}
---

Produce the JSON plan now."""

        try:
            collected: list[str] = []
            tc = 0

            async def on_token(chunk: str):
                nonlocal tc
                tc += len(chunk)
                self.state.tokens_out = tc
                collected.append(chunk)
                self.state.progress = min(10 + int(tc / 50), 85)
                self.state.activity = f"Building plan… ({tc} chars)"

            raw = await self.llm.stream_collect(SYSTEM_PROMPT, user_msg, on_token=on_token)

            self.state.activity = "Parsing JSON plan…"
            self.state.progress = 90
            plan = self._parse_json(raw)

            self.state.status   = Status.COMPLETED
            self.state.progress = 100
            self.state.activity = f"Plan ready — {len(plan.get('components', []))} components, {len(plan.get('api_endpoints', []))} endpoints"
            self.state.end_time = time.time()
            self._glog(f"✅ Planner done — project: {plan.get('project_name', '?')}")
            return plan

        except Exception as exc:
            self.state.status   = Status.FAILED
            self.state.error    = str(exc)
            self.state.activity = f"FAILED: {exc}"
            self.state.end_time = time.time()
            self._glog(f"❌ Planner FAILED: {exc}")
            # Return a sensible fallback so other agents can still proceed
            return self._fallback_plan()

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_json(raw: str) -> dict:
        # Strip possible markdown fences
        raw = raw.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*",     "", raw)
        raw = re.sub(r"\s*```$",     "", raw)
        return json.loads(raw)

    @staticmethod
    def _fallback_plan() -> dict:
        return {
            "project_name":    "React Vite Prototype",
            "description":     "A modern React + Vite application.",
            "tech_stack":      ["React", "Vite", "TypeScript", "Tailwind CSS"],
            "key_features":    ["Dashboard", "Data Display", "Responsive Layout"],
            "pages":           [{"name": "Home", "route": "/", "description": "Landing page"},
                                {"name": "Dashboard", "route": "/dashboard", "description": "Main dashboard"}],
            "components":      ["App", "Header", "Sidebar", "Dashboard", "Footer"],
            "api_endpoints":   [{"method": "GET", "path": "/api/data", "description": "Fetch all records"}],
            "data_models":     [{"name": "Item", "fields": [{"name": "id", "type": "string", "required": True}]}],
            "state_management": "React Context",
            "styling":         "Tailwind CSS",
            "test_framework":  "Vitest + React Testing Library",
            "backend_type":    "mock",
            "deployment_target": "Vercel",
            "agent_tasks": {
                "design":   "Create a modern, clean UI/UX design system.",
                "dev":      "Build the React Vite app with all components.",
                "tests":    "Write comprehensive unit and integration tests.",
                "swagger":  "Document all REST API endpoints in OpenAPI 3.0.",
                "lld":      "Provide low-level design for backend services.",
                "startup":  "Write a complete startup and deployment guide.",
                "readme":   "Write a comprehensive README with badges.",
            },
        }
