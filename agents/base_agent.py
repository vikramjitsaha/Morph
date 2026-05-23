"""
agents/base_agent.py — Abstract base for all parallel agents.

Each agent:
  • gets a shared AgentState object that the dashboard reads
  • calls the LLM (streaming) and writes output files
  • updates its own status, progress and log in real-time
"""
import asyncio
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from llm_client import LLMClient


# ─── Agent Status Enum ────────────────────────────────────────────────────────
class Status(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    SKIPPED    = "skipped"


STATUS_ICON = {
    Status.PENDING:   "⏳",
    Status.RUNNING:   "🔄",
    Status.COMPLETED: "✅",
    Status.FAILED:    "❌",
    Status.SKIPPED:   "⏭️",
}


# ─── Shared Mutable State ─────────────────────────────────────────────────────
@dataclass
class AgentState:
    name:         str
    icon:         str       = "🤖"
    status:       Status    = Status.PENDING
    progress:     int       = 0         # 0-100
    activity:     str       = "Waiting for orchestrator…"
    output_files: list      = field(default_factory=list)
    logs:         list      = field(default_factory=list)   # list[str]
    error:        str       = ""
    start_time:   Optional[float] = None
    end_time:     Optional[float] = None
    tokens_out:   int       = 0

    @property
    def elapsed(self) -> str:
        if self.start_time is None:
            return "—"
        end = self.end_time or time.time()
        secs = int(end - self.start_time)
        return f"{secs//60:02d}:{secs%60:02d}"

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] [{self.name}] {msg}"
        self.logs.append(entry)
        # keep last 200
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]


# ─── Base Agent ───────────────────────────────────────────────────────────────
class BaseAgent(ABC):
    """
    Subclass this for each specialist agent.
    Override: system_prompt, user_prompt(requirements, plan), output_filename.
    """

    # Subclasses set these
    AGENT_NAME:     str = "BaseAgent"
    AGENT_ICON:     str = "🤖"
    OUTPUT_SUBDIR:  str = ""      # sub-folder inside workspace

    def __init__(
        self,
        workspace: Path,
        global_log: list,        # shared log list for dashboard footer
        requirements: str,
        plan: dict,
    ):
        self.workspace    = workspace
        self.global_log   = global_log
        self.requirements = requirements
        self.plan         = plan
        self.state        = AgentState(name=self.AGENT_NAME, icon=self.AGENT_ICON)
        self.llm          = LLMClient()
        self.output_dir   = workspace / self.OUTPUT_SUBDIR if self.OUTPUT_SUBDIR else workspace

    # ── Abstract interface ────────────────────────────────────────────────────
    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def user_prompt(self) -> str: ...

    @abstractmethod
    async def process_output(self, raw: str): ...

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def run(self):
        self.state.status     = Status.RUNNING
        self.state.start_time = time.time()
        self.state.progress   = 5
        self.state.activity   = "Connecting to LLM…"
        self._glog(f"🚀 {self.AGENT_NAME} started")

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.state.activity = "Generating with LLM (streaming)…"
            self.state.progress = 10

            collected: list[str] = []
            token_count = 0

            async def on_token(chunk: str):
                nonlocal token_count
                token_count += len(chunk)
                self.state.tokens_out = token_count
                # Update activity every ~200 chars
                if token_count % 200 < len(chunk):
                    preview = "".join(collected[-40:]).replace("\n", " ").strip()
                    self.state.activity = f"Writing… «{preview[-60:]}»"
                    p = min(10 + int(token_count / (config.MAX_TOKENS * 3) * 80), 85)
                    self.state.progress = p
                collected.append(chunk)

            import config  # late import avoids circular
            raw = await self.llm.stream_collect(
                self.system_prompt,
                self.user_prompt(),
                on_token=on_token,
            )
            self.state.progress = 88
            self.state.activity = "Post-processing output…"
            await self.process_output(raw)

            self.state.status   = Status.COMPLETED
            self.state.progress = 100
            self.state.activity = f"Done — {len(self.state.output_files)} file(s)"
            self.state.end_time = time.time()
            self._glog(f"✅ {self.AGENT_NAME} completed in {self.state.elapsed}")

        except Exception as exc:
            self.state.status   = Status.FAILED
            self.state.progress = 0
            self.state.error    = str(exc)
            self.state.activity = f"ERROR: {exc}"
            self.state.end_time = time.time()
            self.state.log(f"ERROR: {exc}")
            self._glog(f"❌ {self.AGENT_NAME} FAILED: {exc}")
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _glog(self, msg: str):
        """Append to both local state and global shared log."""
        self.state.log(msg)
        ts = time.strftime("%H:%M:%S")
        self.global_log.append(f"[{ts}] {msg}")
        if len(self.global_log) > 500:
            del self.global_log[:-500]

    def write_file(self, filename: str, content: str) -> Path:
        path = self.output_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.state.output_files.append(str(path.relative_to(self.workspace)))
        self.state.log(f"📄 Written: {path.relative_to(self.workspace)}")
        return path

    def plan_summary(self) -> str:
        """Return a short plan summary for prompts."""
        endpoints = [
            f"{e.get('method','?')} {e.get('path','')}" if isinstance(e, dict) else str(e)
            for e in self.plan.get('api_endpoints', [])
        ]
        return (
            f"Project: {self.plan.get('project_name', 'React/Vite Prototype')}\n"
            f"Description: {self.plan.get('description', '')}\n"
            f"Tech Stack: {', '.join(self.plan.get('tech_stack', ['React', 'Vite', 'TypeScript']))}\n"
            f"Key Features: {', '.join(self.plan.get('key_features', []))}\n"
            f"Components: {', '.join(self.plan.get('components', []))}\n"
            f"API Endpoints: {', '.join(endpoints)}\n"
        )
