"""
main.py — Morph Orchestrator
====================================
Reads a requirements.md → plans → launches 7 parallel specialist AI agents
→ tracks everything in a live Rich terminal dashboard → zips all output.

Usage:
    python main.py [requirements.md]
    python main.py --requirements path/to/file.md
    python main.py --help
"""
import argparse
import asyncio
import sys
import tempfile
import time
from pathlib import Path

import config
from agents import (
    AgentState, PlannerAgent,
    DesignAgent, DevAgent, TestAgent,
    SwaggerAgent, LLDAgent, StartupAgent, ReadmeAgent,
    CodeBuilderAgent,
)
from dashboard import Dashboard, console
from packager import build_zip


# ─── CLI ─────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        prog="morph",
        description="AI multi-agent React/Vite prototype generator",
    )
    p.add_argument(
        "requirements",
        nargs="?",
        default=config.REQUIREMENTS_FILE,
        help="Path to requirements Markdown file (default: %(default)s)",
    )
    p.add_argument("--output", default=config.OUTPUT_DIR, help="Output directory")
    p.add_argument("--list-models", action="store_true", help="List env config and exit")
    return p.parse_args()


# ─── Helpers ─────────────────────────────────────────────────────────────────
def read_requirements(path: str) -> str:
    p = Path(path)
    if not p.exists():
        console.print(f"[red]ERROR: Requirements file not found: {path}[/red]")
        console.print("[dim]Create a requirements.md file or pass --requirements <path>[/dim]")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


async def run_agent_with_dashboard_refresh(agent, dashboard: Dashboard):
    """Run a single agent and keep refreshing the dashboard while it runs."""
    task = asyncio.create_task(agent.run())
    while not task.done():
        dashboard.refresh()
        await asyncio.sleep(config.DASHBOARD_REFRESH_RATE)
    try:
        await task  # re-raise any exception
    except Exception:
        pass  # already logged in agent state


async def run_all_parallel(agents: list, dashboard: Dashboard):
    """
    Run all agents in parallel.  We use asyncio.gather so all start at once.
    A separate refresh loop keeps the dashboard live.
    """
    stop_refresh = asyncio.Event()

    async def refresh_loop():
        while not stop_refresh.is_set():
            dashboard.refresh()
            await asyncio.sleep(config.DASHBOARD_REFRESH_RATE)

    refresh_task = asyncio.create_task(refresh_loop())
    # Run all agents concurrently
    results = await asyncio.gather(
        *[agent.run() for agent in agents],
        return_exceptions=True,
    )
    stop_refresh.set()
    await refresh_task
    return results


# ─── Main ─────────────────────────────────────────────────────────────────────
async def main():
    args = parse_args()

    # Validate config
    try:
        config.validate()
    except EnvironmentError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(1)

    if args.list_models:
        console.print(f"[bold]LLM Provider:[/bold] {config.LLM_PROVIDER}")
        console.print(f"[bold]Model:[/bold]        {config.get_active_model()}")
        console.print(f"[bold]Max Tokens:[/bold]   {config.MAX_TOKENS}")
        sys.exit(0)

    # Read requirements
    requirements = read_requirements(args.requirements)
    output_dir   = Path(args.output)

    console.print(f"\n[bold cyan]🤖 Morph[/bold cyan] — starting up")
    console.print(f"  Requirements : [yellow]{args.requirements}[/yellow]")
    console.print(f"  LLM          : [cyan]{config.LLM_PROVIDER} / {config.get_active_model()}[/cyan]")
    console.print(f"  Output       : [green]{output_dir}[/green]")
    console.print()

    # Shared global log
    global_log: list[str] = []

    # ── Phase 1: Planner (sequential) ─────────────────────────────────────────
    planner    = PlannerAgent(requirements=requirements, global_log=global_log)
    dummy_states: list[AgentState] = []  # no parallel agents yet

    console.print("[bold]Phase 1:[/bold] Running Planner Agent…")

    # Minimal dashboard just for planner
    with Dashboard(planner.state, dummy_states, global_log, args.requirements) as dash:
        stop = asyncio.Event()

        async def refresh_planner():
            while not stop.is_set():
                dash.refresh()
                await asyncio.sleep(config.DASHBOARD_REFRESH_RATE)

        rt = asyncio.create_task(refresh_planner())
        plan = await planner.run()
        stop.set()
        await rt

    console.print(f"\n[green]✅ Plan ready:[/green] {plan.get('project_name', '?')}")

    # ── Phase 2: Create workspace ──────────────────────────────────────────────
    project_slug = plan.get("project_name", "prototype").replace(" ", "_").lower()[:30]
    workspace    = output_dir / f"workspace_{project_slug}"
    workspace.mkdir(parents=True, exist_ok=True)

    # ── Phase 3: Spin up parallel agents ──────────────────────────────────────
    agent_classes = [
        DesignAgent,
        DevAgent,
        TestAgent,
        SwaggerAgent,
        LLDAgent,
        StartupAgent,
        ReadmeAgent,
    ]

    agents = [
        cls(
            workspace=workspace,
            global_log=global_log,
            requirements=requirements,
            plan=plan,
        )
        for cls in agent_classes
    ]

    agent_states = [a.state for a in agents]

    console.print(f"\n[bold]Phase 2:[/bold] Launching [cyan]{len(agents)}[/cyan] parallel agents…")
    time.sleep(0.5)

    with Dashboard(planner.state, agent_states, global_log, args.requirements) as dash:
        results = await run_all_parallel(agents, dash)
        # Final refresh
        dash.refresh()
        time.sleep(1)

    # ── Phase 3: CodeBuilder — npm install + iterative build fix ──────────────
    console.print("\n[bold]Phase 3:[/bold] Running CodeBuilder Agent (npm install + build)…")

    builder = CodeBuilderAgent(
        workspace=workspace,
        global_log=global_log,
        plan=plan,
    )

    with Dashboard(planner.state, [*agent_states, builder.state],
                   global_log, args.requirements) as dash:
        await run_agent_with_dashboard_refresh(builder, dash)
        dash.refresh()
        time.sleep(1)

    # ── Phase 4: Package into ZIP ──────────────────────────────────────────────
    console.print("\n[bold]Phase 4:[/bold] Packaging output into ZIP…")
    zip_path = build_zip(
        workspace=workspace,
        project_name=plan.get("project_name", "prototype"),
        output_dir=output_dir,
        agent_states=[planner.state, *agent_states, builder.state],
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print()
    console.rule("[bold green]🎉 Morph Complete[/bold green]")
    console.print()
    console.print(f"  📦 [bold]ZIP:[/bold] [green]{zip_path}[/green]")
    console.print(f"  📁 [bold]Workspace:[/bold] {workspace}")
    console.print()

    # Agent summary table
    from rich.table import Table
    t = Table(title="Agent Results", show_header=True, header_style="bold cyan")
    t.add_column("Agent",    style="bold")
    t.add_column("Status",   justify="center")
    t.add_column("Files",    justify="right")
    t.add_column("Tokens",   justify="right")
    t.add_column("Duration", justify="right")

    for s in [planner.state, *agent_states, builder.state]:
        colour = {
            "completed": "green",
            "failed":    "red",
            "pending":   "grey58",
            "running":   "cyan",
        }.get(s.status.value, "white")
        t.add_row(
            f"{s.icon} {s.name}",
            f"[{colour}]{s.status.value}[/{colour}]",
            str(len(s.output_files)),
            f"{s.tokens_out:,}",
            s.elapsed,
        )

    console.print(t)

    # Count errors
    errors = [s for s in agent_states if s.status.value == "failed"]
    if errors:
        console.print(f"\n[yellow]⚠️  {len(errors)} agent(s) failed:[/yellow]")
        for s in errors:
            console.print(f"   [red]{s.name}:[/red] {s.error}")

    console.print(f"\n[dim]All files saved to {zip_path}[/dim]\n")


if __name__ == "__main__":
    asyncio.run(main())
