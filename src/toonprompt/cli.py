from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import difflib

from . import __version__
from .adapters import resolve_adapter, run_adapter, tool_status
from .config import write_default_config
from .errors import AdapterExecutionError, ConfigError, PromptInputError, ToonPromptError
from .services import PromptProcessingService, doctor_report, metrics_report


TOOLS = ("codex", "claude", "cursor", "gemini")
logger = logging.getLogger("toonprompt")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toon", description="ToonPrompt prompt wrapper")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug-level output.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress all non-error output.")
    parser.add_argument("--profile", default="default", help="Configuration profile to load.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for tool in TOOLS:
        tool_parser = subparsers.add_parser(tool, help=f"proxy {tool}")
        _add_prompt_args(tool_parser)
        tool_parser.add_argument("--dry-run", action="store_true", help="Print transformed prompt and exit.")
        tool_parser.add_argument("--preview", action="store_true", help="show original and transformed prompt")
        tool_parser.add_argument("--explain", action="store_true", help="show transform explanations")
        tool_parser.add_argument("--print-final-prompt", action="store_true", help="print final prompt and exit")
        tool_parser.add_argument("native_args", nargs=argparse.REMAINDER, help="arguments passed to the native CLI")

    inspect_parser = subparsers.add_parser("inspect", help="inspect a prompt without invoking a native CLI")
    _add_prompt_args(inspect_parser)
    inspect_parser.add_argument("--dry-run", action="store_true", help="Print transformed prompt and exit.")
    inspect_parser.add_argument("--preview", action="store_true", help="show original and transformed prompt")
    inspect_parser.add_argument("--explain", action="store_true", help="show transform explanations")
    inspect_parser.add_argument("--diff", action="store_true", help="Show line-by-line diff.")
    inspect_parser.add_argument("--segment", type=int, help="Show specific segment details.")
    inspect_parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")

    config_parser = subparsers.add_parser("config", help="manage config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_init = config_subparsers.add_parser("init", help="write default config")
    config_init.add_argument("--path", type=Path, help="custom path for config file")

    subparsers.add_parser("doctor", help="show installation diagnostics")
    metrics_parser = subparsers.add_parser("metrics", help="show local transformation metrics")
    metrics_parser.add_argument("--json", action="store_true", dest="metrics_json", help="Output metrics as JSON.")
    check_parser = subparsers.add_parser("check", help="check token budget for prompt files")
    check_parser.add_argument("--max-tokens", type=int, required=True, help="Maximum allowed estimated tokens.")
    check_parser.add_argument("files", nargs="+", help="Prompt files to validate.")
    subparsers.add_parser("version", help="print version")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        _setup_logging(args.verbose, args.quiet)
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "doctor":
            return _run_doctor(profile=args.profile)
        if args.command == "metrics":
            return _run_metrics(args, profile=args.profile)
        if args.command == "check":
            return _run_check(args, profile=args.profile)
        if args.command == "config":
            path = write_default_config(args.path)
            print(f"Wrote config to {path}")
            return 0
        if args.command == "inspect":
            return _run_inspect(args, profile=args.profile)
        return _run_tool(args.command, args, profile=args.profile)
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


def _run_inspect(args: argparse.Namespace, profile: str) -> int:
    processed = PromptProcessingService().process(args.prompt, args.prompt_file, args.stdin, profile=profile)
    config = processed.config
    result = processed.result
    if args.format == "json":
        print(
            json.dumps(
                {
                    "action": result.safety.action,
                    "reason": result.safety.reason,
                    "estimator": result.estimator_name,
                    "estimated_input_tokens": result.estimated_input_tokens,
                    "estimated_output_tokens": result.estimated_output_tokens,
                    "delta": result.estimated_input_tokens - result.estimated_output_tokens,
                    "transformed": result.final_text,
                },
                indent=2,
            )
        )
    else:
        print(_format_summary(result, markdown=(args.format == "markdown")))
    if args.explain or config.learning_explanations:
        print("\nExplanations:")
        for line in result.explanations:
            print(f"- {line}")
    if args.segment is not None:
        idx = args.segment - 1
        if 0 <= idx < len(result.segments):
            seg = result.segments[idx]
            print(f"\nSegment {args.segment}: {seg.segment_type.value} ({seg.source})")
            print(seg.text)
        else:
            print(f"\nSegment {args.segment}: not found")
    if args.diff:
        print("\nDiff:\n")
        for line in difflib.unified_diff(
            result.original_text.splitlines(),
            result.final_text.splitlines(),
            fromfile="original",
            tofile="transformed",
            lineterm="",
        ):
            print(line)
    if args.dry_run:
        print("\n=== ToonPrompt dry-run ===")
        print("--- Transformed prompt ---")
        print(result.final_text)
        print("--- End ---")
        return 0
    if args.preview:
        print("\nOriginal:\n")
        print(result.original_text)
        print("\nTransformed:\n")
        print(result.final_text)
    return 0


def _run_tool(tool: str, args: argparse.Namespace, profile: str) -> int:
    processed = PromptProcessingService().process(args.prompt, args.prompt_file, args.stdin, profile=profile, tool=tool)
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
    if args.dry_run:
        print("=== ToonPrompt dry-run ===")
        print(f"Estimator  : {result.estimator_name}")
        print(f"Input tokens (est.)  : {result.estimated_input_tokens}")
        print(f"Output tokens (est.) : {result.estimated_output_tokens}")
        delta = result.estimated_output_tokens - result.estimated_input_tokens
        ratio = (delta / result.estimated_input_tokens * 100) if result.estimated_input_tokens else 0.0
        print(f"Delta       : {delta} ({ratio:.1f} %)")
        print(f"Action      : {result.safety.action}")
        print(f"Reason      : {result.safety.reason}")
        print("\n--- Transformed prompt ---")
        print(result.final_text)
        print("--- End ---")
        return 0

    native_args = list(args.native_args)
    if native_args and native_args[0] == "--":
        native_args = native_args[1:]
    adapter = resolve_adapter(tool, config)
    return run_adapter(adapter, native_args, result.final_text or None)


def _run_doctor(profile: str) -> int:
    config, config_line = doctor_report(profile=profile)
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


def _format_summary(result, markdown: bool = False) -> str:
    delta = result.estimated_input_tokens - result.estimated_output_tokens
    if markdown:
        return (
            f"### ToonPrompt Inspection\n"
            f"- Action: `{result.safety.action}`\n"
            f"- Reason: `{result.safety.reason}`\n"
            f"- Estimator: `{result.estimator_name}`\n"
            f"- Estimated input tokens: `{result.estimated_input_tokens}`\n"
            f"- Estimated output tokens: `{result.estimated_output_tokens}`\n"
            f"- Delta: `{delta}`\n"
        )
    return (
        f"Action: {result.safety.action}\n"
        f"Reason: {result.safety.reason}\n"
        f"Estimator: {result.estimator_name}\n"
        f"Estimated tokens: {result.estimated_input_tokens} -> {result.estimated_output_tokens} "
        f"(delta {delta})"
    )


def _run_metrics(args: argparse.Namespace, profile: str) -> int:
    config, summary = metrics_report(profile=profile)
    if not config.local_metrics_enabled:
        print("Local metrics are disabled. Set local_metrics_enabled = true in config to collect them.")
        return 0
    if args.metrics_json:
        print(
            json.dumps(
                {
                    "transforms_attempted": summary.transforms_attempted,
                    "transforms_applied": summary.transforms_applied,
                    "pass_through": summary.pass_through,
                    "estimated_token_delta_total": summary.estimated_token_delta_total,
                    "pass_through_reasons": summary.pass_through_reasons,
                    "by_tool": summary.by_tool,
                    "daily": summary.daily,
                },
                indent=2,
            )
        )
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
    if summary.by_tool:
        print("- By tool:")
        for tool, data in sorted(summary.by_tool.items()):
            print(f"  - {tool}: {data['applied']} applied / {data['attempted']} attempted (delta {data['delta']})")
    return 0


def _run_check(args: argparse.Namespace, profile: str) -> int:
    failures = []
    for raw_path in args.files:
        path = Path(raw_path)
        processed = PromptProcessingService().process(None, path, False, profile=profile)
        estimate = processed.result.estimated_input_tokens
        if estimate > args.max_tokens:
            failures.append((path, estimate))
    if failures:
        for path, estimate in failures:
            print(f"{path}: {estimate} tokens exceeds budget {args.max_tokens}", file=sys.stderr)
        return 1
    print("All files are within token budget.")
    return 0


def _setup_logging(verbose: bool, quiet: bool) -> None:
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")
        logger.debug("Verbose logging enabled")
    elif quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.WARNING)
