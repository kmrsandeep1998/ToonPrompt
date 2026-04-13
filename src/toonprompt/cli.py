from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .adapters import resolve_adapter, run_adapter, tool_status
from .config import write_default_config
from .errors import AdapterExecutionError, ConfigError, PromptInputError, ToonPromptError
from .services import PromptProcessingService, doctor_report, metrics_report


TOOLS = ("codex", "claude", "cursor", "gemini")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toon", description="ToonPrompt prompt wrapper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for tool in TOOLS:
        tool_parser = subparsers.add_parser(tool, help=f"proxy {tool}")
        _add_prompt_args(tool_parser)
        tool_parser.add_argument("--preview", action="store_true", help="show original and transformed prompt")
        tool_parser.add_argument("--explain", action="store_true", help="show transform explanations")
        tool_parser.add_argument("--print-final-prompt", action="store_true", help="print final prompt and exit")
        tool_parser.add_argument("native_args", nargs=argparse.REMAINDER, help="arguments passed to the native CLI")

    inspect_parser = subparsers.add_parser("inspect", help="inspect a prompt without invoking a native CLI")
    _add_prompt_args(inspect_parser)
    inspect_parser.add_argument("--preview", action="store_true", help="show original and transformed prompt")
    inspect_parser.add_argument("--explain", action="store_true", help="show transform explanations")

    config_parser = subparsers.add_parser("config", help="manage config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_init = config_subparsers.add_parser("init", help="write default config")
    config_init.add_argument("--path", type=Path, help="custom path for config file")

    subparsers.add_parser("doctor", help="show installation diagnostics")
    subparsers.add_parser("metrics", help="show local transformation metrics")
    subparsers.add_parser("version", help="print version")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "doctor":
            return _run_doctor()
        if args.command == "metrics":
            return _run_metrics()
        if args.command == "config":
            path = write_default_config(args.path)
            print(f"Wrote config to {path}")
            return 0
        if args.command == "inspect":
            return _run_inspect(args)
        return _run_tool(args.command, args)
    except (ConfigError, PromptInputError, AdapterExecutionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ToonPromptError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def main_codex() -> int:
    return main(["codex", *sys.argv[1:]])


def main_claude() -> int:
    return main(["claude", *sys.argv[1:]])


def main_cursor() -> int:
    return main(["cursor", *sys.argv[1:]])


def main_gemini() -> int:
    return main(["gemini", *sys.argv[1:]])


def _add_prompt_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="inline prompt text")
    parser.add_argument("--prompt-file", type=Path, help="path to file containing prompt text")
    parser.add_argument("--stdin", action="store_true", help="read prompt text from stdin")


def _run_inspect(args: argparse.Namespace) -> int:
    processed = PromptProcessingService().process(args.prompt, args.prompt_file, args.stdin)
    config = processed.config
    result = processed.result
    print(_format_summary(result))
    if args.explain or config.learning_explanations:
        print("\nExplanations:")
        for line in result.explanations:
            print(f"- {line}")
    if args.preview:
        print("\nOriginal:\n")
        print(result.original_text)
        print("\nTransformed:\n")
        print(result.final_text)
    return 0


def _run_tool(tool: str, args: argparse.Namespace) -> int:
    processed = PromptProcessingService().process(args.prompt, args.prompt_file, args.stdin)
    config = processed.config
    result = processed.result
    if args.preview:
        print(_format_summary(result), file=sys.stderr)
        print("\nTransformed prompt:\n", file=sys.stderr)
        print(result.final_text, file=sys.stderr)
    if args.explain:
        print("Transform explanations:", file=sys.stderr)
        for line in result.explanations:
            print(f"- {line}", file=sys.stderr)
    if args.print_final_prompt:
        print(result.final_text)
        return 0

    native_args = list(args.native_args)
    if native_args and native_args[0] == "--":
        native_args = native_args[1:]
    adapter = resolve_adapter(tool, config)
    return run_adapter(adapter, native_args, result.final_text or None)


def _run_doctor() -> int:
    config, config_line = doctor_report()
    print(config_line)
    print(f"Config valid: yes")
    print("Tools:")
    missing = False
    for tool in TOOLS:
        present, detail = tool_status(tool, config)
        status = "ok" if present else "missing"
        print(f"- {tool}: {status} ({detail})")
        if not present:
            missing = True
    return 1 if missing else 0


def _format_summary(result) -> str:
    delta = result.estimated_input_tokens - result.estimated_output_tokens
    return (
        f"Action: {result.safety.action}\n"
        f"Reason: {result.safety.reason}\n"
        f"Estimator: {result.estimator_name}\n"
        f"Estimated tokens: {result.estimated_input_tokens} -> {result.estimated_output_tokens} "
        f"(delta {delta})"
    )


def _run_metrics() -> int:
    config, summary = metrics_report()
    if not config.local_metrics_enabled:
        print("Local metrics are disabled. Set local_metrics_enabled = true in config to collect them.")
        return 0
    print("Local transformation metrics:")
    print(f"- Transforms attempted: {summary.transforms_attempted}")
    print(f"- Transforms applied: {summary.transforms_applied}")
    print(f"- Pass-through count: {summary.pass_through}")
    print(f"- Estimated token delta total: {summary.estimated_token_delta_total}")
    if summary.pass_through_reasons:
        print("- Pass-through reasons:")
        for reason, count in sorted(summary.pass_through_reasons.items()):
            print(f"  - {reason}: {count}")
    return 0
