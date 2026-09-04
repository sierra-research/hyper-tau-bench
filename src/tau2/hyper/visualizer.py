"""
Rich terminal visualizer for Hyper-τ outer-loop runs.

Displays each step of the Developer ↔ Client interaction with
color-coded panels, budget counters, and a final results summary.

Usage:
    from tau2.hyper.visualizer import HyperTauDisplay

    display = HyperTauDisplay()
    orchestrator = OuterOrchestrator(...)
    result = orchestrator.run(display=display)
"""

import json
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tau2.hyper.data_model import HyperTauTask, OuterLoopResult

# ---------------------------------------------------------------------------
# Tool icons and colors
# ---------------------------------------------------------------------------

TOOL_STYLES = {
    # Sandbox mode
    "read_file": {"icon": "📄", "color": "cyan", "label": "Read File"},
    "write_file": {"icon": "📝", "color": "yellow", "label": "Write File"},
    "edit_file": {"icon": "✏️ ", "color": "yellow", "label": "Edit File"},
    "list_directory": {"icon": "📁", "color": "cyan", "label": "List Directory"},
    "search_files": {"icon": "🔍", "color": "cyan", "label": "Search Files"},
    "run_command": {"icon": "💻", "color": "magenta", "label": "Run Command"},
    "talk_to_client": {"icon": "💬", "color": "blue", "label": "Talk to Client"},
}

DEFAULT_STYLE = {"icon": "🔧", "color": "white", "label": "Tool Call"}


class HyperTauDisplay:
    """Rich terminal display for Hyper-τ outer-loop execution.

    Plug this into ``OuterOrchestrator.run(display=...)`` to get
    a live view of the Developer ↔ Client interaction.
    """

    def __init__(self, console: Optional[Console] = None, verbose: bool = False):
        self.console = console or Console()
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Task info
    # ------------------------------------------------------------------

    def show_task_info(
        self,
        task: Optional[HyperTauTask],
        domain: str,
        max_steps: int,
    ) -> None:
        """Display the task header panel."""
        lines = Text()
        lines.append("Hyper-τ Run\n", style="bold bright_white")
        lines.append(f"Domain: ", style="dim")
        lines.append(f"{domain}\n", style="bold")

        if task:
            lines.append(f"Task: ", style="dim")
            lines.append(f"{task.id}\n", style="bold cyan")
            lines.append(f"{task.task_description}\n", style="dim")

        lines.append(f"\nBudget: ", style="dim")
        lines.append(f"{max_steps} steps", style="bold")

        self.console.print()
        self.console.print(
            Panel(
                lines,
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(1, 3),
            )
        )

    # ------------------------------------------------------------------
    # Step display
    # ------------------------------------------------------------------

    def show_client_message(self, content: str) -> None:
        """Display a message from the Client (brief or response)."""
        # Truncate very long messages unless verbose
        display_content = content
        if not self.verbose and len(content) > 2000:
            display_content = (
                content[:2000] + "\n\n... (truncated, use --verbose for full output)"
            )

        self.console.print()
        self.console.print(
            Panel(
                display_content,
                title="[bold blue]💬 Client[/bold blue]",
                border_style="blue",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def show_final_eval_start(self) -> None:
        """Signal that final scoring is starting."""
        self.console.print()
        self.console.print("[bold magenta]🧪 Running final scoring...[/bold magenta]")

    def show_result(self, result: OuterLoopResult) -> None:
        """Display the final results summary."""
        # Build results table
        table = Table(
            title="Final Results",
            box=box.HEAVY,
            title_style="bold bright_white",
            show_header=True,
            header_style="bold cyan",
            padding=(0, 2),
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row(
            "Final test reward",
            f"[green]{result.final_test_reward:.3f}[/green]",
        )

        table.add_section()
        table.add_row("Total steps", str(result.total_outer_steps))
        table.add_row("Client turns used", str(result.client_turns_used))

        self.console.print()
        self.console.print(table)

        # Step timeline
        if result.steps:
            self.console.print()
            self._show_step_timeline(result)

    def _show_step_timeline(self, result: OuterLoopResult) -> None:
        """Show a compact timeline of all steps taken."""
        timeline = Text()
        timeline.append("Step timeline: ", style="dim")

        for step in result.steps:
            style = TOOL_STYLES.get(step.action, DEFAULT_STYLE)
            icon = style["icon"]
            timeline.append(f"{icon} ", style=style["color"])

        self.console.print(timeline)

    # ------------------------------------------------------------------
    # Sandbox mode events
    # ------------------------------------------------------------------

    def show_sandbox_phase(self, phase: str, detail: str = "") -> None:
        """Display a sandbox pipeline phase header."""
        self.console.print()
        icons = {
            "kit_build": "📦",
            "builder_start": "🏗️ ",
            "builder_done": "🏁",
            "extract": "📤",
            "scoring": "🧪",
        }
        icon = icons.get(phase, "▶")
        label = phase.replace("_", " ").title()
        msg = f"[bold bright_cyan]{icon} {label}[/bold bright_cyan]"
        if detail:
            msg += f"  [dim]{detail}[/dim]"
        self.console.print(msg)

    def show_sandbox_step(
        self,
        step: int,
        max_steps: int,
        thinking: Optional[str],
        tool_calls: Optional[list[dict]],
        tool_results: Optional[list[dict]],
        reasoning_summary: Optional[str] = None,
    ) -> None:
        """Display one step of the sandbox builder's work."""
        self.console.print()
        step_label = f"Step {step}/{max_steps}" if max_steps > 0 else f"Step {step}"
        self.console.rule(
            f"[bold]{step_label}[/bold]  [dim](sandbox)[/dim]",
            style="dim",
        )

        if reasoning_summary:
            display_summary = reasoning_summary
            if not self.verbose and len(reasoning_summary) > 1500:
                display_summary = (
                    reasoning_summary[:1500]
                    + "\n\n... (truncated, use --verbose for full output)"
                )
            self.console.print(
                Panel(
                    display_summary,
                    title="[bold cyan]Reasoning Summary[/bold cyan]",
                    border_style="cyan",
                    box=box.ROUNDED,
                    padding=(0, 2),
                )
            )

        # Show visible assistant text if present
        if thinking:
            display_thinking = thinking
            if not self.verbose and len(thinking) > 1000:
                display_thinking = (
                    thinking[:1000]
                    + "\n\n... (truncated, use --verbose for full output)"
                )
            self.console.print(
                Panel(
                    display_thinking,
                    title="[bold green]🛠️  Builder Message[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(0, 2),
                )
            )

        # Show tool calls and results
        if tool_calls:
            for i, tc in enumerate(tool_calls):
                name = tc.get("name", "unknown")
                args = tc.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, ValueError):
                        args = {"raw": args}

                style = TOOL_STYLES.get(name, DEFAULT_STYLE)
                icon = style["icon"]
                color = style["color"]
                label = style["label"]

                # Format args compactly
                args_display = self._format_sandbox_args(name, args)

                self.console.print(
                    f"  {icon} [{color} bold]{label}[/{color} bold] {args_display}"
                )

                # Show result if available
                if tool_results and i < len(tool_results):
                    result_text = tool_results[i].get("result", "")
                    if result_text:
                        display_result = result_text
                        if not self.verbose and len(result_text) > 1500:
                            display_result = (
                                result_text[:1500]
                                + f"\n\n... ({len(result_text)} total chars, "
                                "use --verbose for full)"
                            )
                        self.console.print(
                            Panel(
                                display_result,
                                title=f"[{color}]{label} Result[/{color}]",
                                border_style=color,
                                box=box.ROUNDED,
                                padding=(0, 2),
                            )
                        )

        # Budget status
        if max_steps > 0:
            steps_pct = step / max_steps * 100
            steps_color = (
                "green" if steps_pct < 60 else "yellow" if steps_pct < 80 else "red"
            )
            self.console.print(
                f"  [{steps_color}]Steps: {step}/{max_steps}[/{steps_color}]",
            )
        else:
            self.console.print(f"  [dim]Steps (telemetry only): {step}[/dim]")

    def _format_sandbox_args(self, tool_name: str, args: dict) -> str:
        """Format sandbox tool arguments for display."""
        if tool_name == "read_file":
            path = args.get("path", "?")
            offset = args.get("offset", 0)
            limit = args.get("limit", 0)
            extra = ""
            if offset:
                extra += f", offset={offset}"
            if limit:
                extra += f", limit={limit}"
            return f'("{path}"{extra})'

        elif tool_name == "write_file":
            path = args.get("path", "?")
            contents = args.get("contents", "")
            return f'("{path}", {len(contents)} chars)'

        elif tool_name == "edit_file":
            path = args.get("path", "?")
            old = args.get("old_string", "")
            new = args.get("new_string", "")
            return f'("{path}", {len(old)} chars → {len(new)} chars)'

        elif tool_name == "list_directory":
            path = args.get("path", ".")
            recursive = args.get("recursive", False)
            extra = ", recursive" if recursive else ""
            return f'("{path}"{extra})'

        elif tool_name == "search_files":
            pattern = args.get("pattern", "?")
            path = args.get("path", ".")
            return f'("{pattern}" in {path})'

        elif tool_name == "run_command":
            cmd = args.get("command", "?")
            if len(cmd) > 80:
                cmd = cmd[:77] + "..."
            return f'("{cmd}")'

        elif tool_name == "submit":
            return "()"

        elif args:
            try:
                return f"({json.dumps(args)})"
            except (TypeError, ValueError):
                return f"({args})"
        return "()"

    def show_sandbox_done(self, reason: str, steps: int, tool_calls: int) -> None:
        """Display sandbox builder completion."""
        self.console.print()
        if reason == "submitted":
            self.console.rule(
                f"[bold green]✅ SUBMITTED[/bold green]  "
                f"[dim]({steps} steps, {tool_calls} tool calls)[/dim]",
                style="green",
            )
        elif reason == "max_steps":
            self.console.rule(
                f"[bold yellow]⏰ MAX STEPS[/bold yellow]  "
                f"[dim]({steps} steps, {tool_calls} tool calls)[/dim]",
                style="yellow",
            )
        elif reason == "time_budget":
            self.console.rule(
                f"[bold yellow]⏰ TIME LIMIT[/bold yellow]  "
                f"[dim]({steps} steps, {tool_calls} tool calls)[/dim]",
                style="yellow",
            )
        else:
            self.console.rule(
                f"[bold]{reason}[/bold]  "
                f"[dim]({steps} steps, {tool_calls} tool calls)[/dim]",
                style="dim",
            )
