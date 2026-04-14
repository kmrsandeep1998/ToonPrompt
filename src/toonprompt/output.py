from __future__ import annotations

from typing import TextIO


def print_summary(result, stream: TextIO) -> None:
    if _rich_available():
        try:
            _print_rich_summary(result, stream)
            return
        except Exception:
            pass
    _print_plain_summary(result, stream)


def _rich_available() -> bool:
    try:
        import rich  # noqa: F401
    except Exception:
        return False
    return True


def _print_plain_summary(result, stream: TextIO) -> None:
    delta = result.estimated_input_tokens - result.estimated_output_tokens
    stream.write(
        f"Action: {result.safety.action}\n"
        f"Reason: {result.safety.reason}\n"
        f"Estimator: {result.estimator_name}\n"
        f"Estimated tokens: {result.estimated_input_tokens} -> {result.estimated_output_tokens} "
        f"(delta {delta})\n"
    )


def _print_rich_summary(result, stream: TextIO) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console(file=stream)
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    delta = result.estimated_output_tokens - result.estimated_input_tokens
    delta_str = f"[green]{delta:+,}[/green]" if delta < 0 else f"[red]{delta:+,}[/red]"
    table.add_row("Action", result.safety.action)
    table.add_row("Reason", result.safety.reason)
    table.add_row("Estimator", result.estimator_name)
    table.add_row("Input tokens", f"{result.estimated_input_tokens:,}")
    table.add_row("Output tokens", f"{result.estimated_output_tokens:,}")
    table.add_row("Delta", delta_str)
    console.print(table)
