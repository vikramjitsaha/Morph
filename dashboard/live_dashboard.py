"""
dashboard/live_dashboard.py — Real-time Rich terminal dashboard.

Shows a grid of agent panels + scrolling global log.
Updates at DASHBOARD_REFRESH_RATE Hz (default 4 Hz = every 250ms).
"""
import time
from typing import List

from rich.align     import Align
from rich.columns   import Columns
from rich.console   import Console
from rich.layout    import Layout
from rich.live      import Live
from rich.panel     import Panel
from rich.progress  import (BarColumn, MofNCompleteColumn, Progress,
                            SpinnerColumn, TaskProgressColumn, TextColumn,
                            TimeElapsedColumn)
from rich.rule      import Rule
from rich.table     import Table
from rich.text      import Text

import config
from agents.base_agent import AgentState, Status, STATUS_ICON


console = Console()


# ─── Colour map for statuses ─────────────────────────────────────────────────
STATUS_COLOUR = {
    Status.PENDING:   "grey58",
    Status.RUNNING:   "cyan",
    Status.COMPLETED: "bright_green",
    Status.FAILED:    "bright_red",
    Status.SKIPPED:   "yellow",
}

PROGRESS_COLOUR = {
    Status.PENDING:   "grey58",
    Status.RUNNING:   "cyan",
    Status.COMPLETED: "green",
    Status.FAILED:    "red",
    Status.SKIPPED:   "yellow",
}


# ─── Single agent panel ───────────────────────────────────────────────────────
def _agent_panel(state: AgentState) -> Panel:
    colour = STATUS_COLOUR[state.status]
    icon   = STATUS_ICON[state.status]

    # Progress bar (manual ASCII-style so we don't need a Progress object per panel)
    pct      = state.progress
    bar_len  = 20
    filled   = int(bar_len * pct / 100)
    bar      = "█" * filled + "░" * (bar_len - filled)
    bar_text = Text(f"[{bar}] {pct:3d}%", style=colour)

    table = Table.grid(padding=(0, 1))
    table.add_column(width=3)
    table.add_column()

    table.add_row(Text(icon),            Text(f"{state.icon} {state.name}", style=f"bold {colour}"))
    table.add_row(Text("⏱"),            Text(state.elapsed, style="dim"))
    table.add_row(Text("🔢"),            Text(f"{state.tokens_out:,} tokens", style="dim"))
    table.add_row(Text(""),              bar_text)
    table.add_row(Text("📌"),            Text(state.activity[:65], style="italic dim"))

    if state.output_files:
        files_str = ", ".join(state.output_files[-3:])
        if len(state.output_files) > 3:
            files_str += f" (+{len(state.output_files)-3} more)"
        table.add_row(Text("📄"), Text(files_str[:65], style="green dim"))

    if state.error:
        table.add_row(Text("⚠️"), Text(state.error[:65], style="bright_red"))

    border_colour = colour if state.status != Status.PENDING else "grey35"
    return Panel(table, border_style=border_colour, padding=(0, 1))


# ─── Summary bar ─────────────────────────────────────────────────────────────
def _summary_bar(states: List[AgentState], start_ts: float) -> Table:
    done     = sum(1 for s in states if s.status == Status.COMPLETED)
    running  = sum(1 for s in states if s.status == Status.RUNNING)
    failed   = sum(1 for s in states if s.status == Status.FAILED)
    total    = len(states)
    elapsed  = int(time.time() - start_ts)
    elapsed_str = f"{elapsed//60:02d}:{elapsed%60:02d}"

    t = Table.grid(padding=(0, 2))
    t.add_column()
    t.add_column()
    t.add_column()
    t.add_column()
    t.add_column()
    t.add_row(
        Text(f"🕐 {elapsed_str}",        style="bold white"),
        Text(f"✅ {done}/{total} done",   style="bright_green"),
        Text(f"🔄 {running} running",     style="cyan"),
        Text(f"❌ {failed} failed",       style="bright_red" if failed else "dim"),
        Text(f"🤖 {config.LLM_PROVIDER.upper()} / {config.get_active_model()}", style="dim"),
    )
    return t


# ─── Log panel ────────────────────────────────────────────────────────────────
def _log_panel(global_log: list, max_lines: int = 12) -> Panel:
    recent = global_log[-max_lines:] if global_log else ["Waiting for agents to start…"]
    text   = Text()
    for line in recent:
        if "✅" in line or "Done" in line or "completed" in line:
            text.append(line + "\n", style="bright_green")
        elif "❌" in line or "FAILED" in line or "ERROR" in line:
            text.append(line + "\n", style="bright_red")
        elif "🚀" in line or "started" in line:
            text.append(line + "\n", style="cyan")
        elif "🧠" in line:
            text.append(line + "\n", style="magenta")
        else:
            text.append(line + "\n", style="dim white")
    return Panel(text, title="[bold]📡 Live Log[/bold]", border_style="grey35", padding=(0, 1))


# ─── Full layout builder ──────────────────────────────────────────────────────
def _build_layout(
    planner_state: AgentState,
    agent_states:  List[AgentState],
    global_log:    list,
    requirements_file: str,
    start_ts:      float,
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header",  size=3),
        Layout(name="summary", size=3),
        Layout(name="planner", size=8),
        Layout(name="agents",  ratio=1),
        Layout(name="log",     size=16),
    )

    # ── Header ────────────────────────────────────────────────────────────────
    header_text = Text()
    header_text.append("  🤖  MORPH  ", style="bold white on dark_blue")
    header_text.append(f"  Requirements: {requirements_file}  ", style="bold dim")
    header_text.append(f"  Provider: {config.LLM_PROVIDER.upper()} / {config.get_active_model()}  ", style="cyan")
    layout["header"].update(Panel(Align.center(header_text), style="dark_blue", padding=(0, 0)))

    # ── Summary ───────────────────────────────────────────────────────────────
    layout["summary"].update(
        Panel(_summary_bar(agent_states, start_ts), border_style="grey35", padding=(0, 2))
    )

    # ── Planner panel ─────────────────────────────────────────────────────────
    layout["planner"].update(_agent_panel(planner_state))

    # ── Agent grid (2 columns) ────────────────────────────────────────────────
    left_agents  = agent_states[::2]   # even indices
    right_agents = agent_states[1::2]  # odd indices

    left_col  = Layout(name="left")
    right_col = Layout(name="right")
    layout["agents"].split_row(left_col, right_col)

    left_col.split_column(*[Layout(_agent_panel(s), size=9) for s in left_agents])
    right_col.split_column(*[Layout(_agent_panel(s), size=9) for s in right_agents])

    # ── Log ───────────────────────────────────────────────────────────────────
    layout["log"].update(_log_panel(global_log))

    return layout


# ─── Public API ───────────────────────────────────────────────────────────────
class Dashboard:
    """
    Context manager wrapping Rich Live.

    Usage:
        with Dashboard(planner_state, agent_states, global_log, req_file) as dash:
            # run agents in background; dashboard auto-refreshes
            await asyncio.sleep(0.1)  # yield to event loop
    """

    def __init__(
        self,
        planner_state:     AgentState,
        agent_states:      List[AgentState],
        global_log:        list,
        requirements_file: str = "requirements.md",
    ):
        self.planner_state     = planner_state
        self.agent_states      = agent_states
        self.global_log        = global_log
        self.requirements_file = requirements_file
        self.start_ts          = time.time()
        self._live             = Live(
            self._render(),
            console=console,
            refresh_per_second=int(1.0 / config.DASHBOARD_REFRESH_RATE),
            screen=True,
        )

    def _render(self):
        return _build_layout(
            self.planner_state,
            self.agent_states,
            self.global_log,
            self.requirements_file,
            self.start_ts,
        )

    def refresh(self):
        self._live.update(self._render())

    def __enter__(self):
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        self._live.__exit__(*args)
