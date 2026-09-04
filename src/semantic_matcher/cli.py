"""
Command Line Interface for Semantic Policy Matcher.
Built with Click for pipeline and workflow integration.
Features Claude Code-style interactive interface and bat-inspired tables.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import click

try:
    from rich.console import Console
    from rich.prompt import Prompt
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .engine.matcher import SemanticMatcher
from .formatter import (
    format_table,
    print_bat_results_table,
    print_claude_header,
    print_explanation_card,
    print_prompt_card,
    print_summary_card,
)
from .models import MatchResult
from .storage.indexer import PolicyIndexer

VERSION = "0.1.0"


def get_default_data_paths():
    """Locate default data directory relative to package."""
    # Check parent directory (repository root)
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data"
    return {
        "policies": data_dir / "policies.json",
        "fields": data_dir / "lexical_fields.json",
        "index": data_dir / "policy_index.json",
    }


def init_engine(
    rebuild: bool = False,
    policies_path: Optional[Path] = None,
    fields_path: Optional[Path] = None,
    index_path: Optional[Path] = None,
) -> SemanticMatcher:
    """Initialize and return the SemanticMatcher instance."""
    defaults = get_default_data_paths()
    p_path = Path(policies_path) if policies_path else defaults["policies"]
    f_path = Path(fields_path) if fields_path else defaults["fields"]
    i_path = Path(index_path) if index_path else (defaults["index"] if policies_path is None else None)

    indexer = PolicyIndexer(
        policies_path=p_path,
        fields_path=f_path,
        index_path=i_path,
    )
    policies = indexer.get_or_load_index(force_rebuild=rebuild)

    return SemanticMatcher(
        policies=policies,
        field_mapper=indexer.field_mapper,
        decompounder=indexer.decompounder,
    )


def filter_results_by_framework(results: List[MatchResult], framework_filter: Optional[str]) -> List[MatchResult]:
    """Filter results to only those matching framework keyword."""
    if not framework_filter:
        return results
    fw_lower = framework_filter.lower()
    return [r for r in results if fw_lower in r.framework.lower()]


def render_single_evaluation(
    prompt: str,
    matcher: SemanticMatcher,
    top_k: int = 10,
    threshold: float = 0.0,
    fail_on_match: Optional[float] = None,
    as_json: bool = False,
    quiet: bool = False,
    explain: bool = False,
    framework: Optional[str] = None,
    console: Optional["Console"] = None,
) -> int:
    """
    Evaluate a single prompt and render results.
    Returns exit code (0 = OK, 1 = Gate threshold exceeded).
    """
    t_start = time.perf_counter()
    raw_results = matcher.match(prompt, threshold=threshold)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Filter framework if requested
    results = filter_results_by_framework(raw_results, framework)

    # Machine-readable JSON output for workflow integration
    if as_json:
        payload = {
            "prompt": prompt,
            "elapsed_ms": round(elapsed_ms, 2),
            "match_count": len(results),
            "matches": [
                {
                    "rank": r.rank,
                    "policy_id": r.policy_id,
                    "name": r.name,
                    "framework": r.framework,
                    "match_percentage": r.match_percentage,
                    "morph_score": r.morph_score,
                    "field_score": r.field_score,
                    "trigger_score": r.trigger_score,
                    "contributing_fields": r.contributing_fields,
                    "contributing_tokens": r.contributing_tokens,
                }
                for r in results[:top_k]
            ],
        }
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))

        # Check gate threshold
        if fail_on_match is not None and results and results[0].match_percentage >= fail_on_match:
            return 1
        return 0

    # Quiet mode: print only highest matched policy ID or nothing
    if quiet:
        top_match = results[0] if results else None
        if top_match and (fail_on_match is None or top_match.match_percentage >= (fail_on_match or 0.0)):
            click.echo(f"{top_match.policy_id}:{top_match.match_percentage:.1f}")
        if fail_on_match is not None and top_match and top_match.match_percentage >= fail_on_match:
            return 1
        return 0

    # Human-friendly Claude Code / Bat rendering
    if HAS_RICH and console:
        print_prompt_card(console, prompt)

        if explain:
            decomposed = matcher.decompose_prompt(prompt)
            print_explanation_card(console, decomposed)

        print_bat_results_table(console, results, max_rows=top_k)
        print_summary_card(console, results, elapsed_ms, fail_threshold=fail_on_match)
        console.print()
    else:
        # Fallback table
        click.echo(f"\nPROMPT: \"{prompt}\"")
        click.echo(format_table(results, max_rows=top_k))
        top_pct = results[0].match_percentage if results else 0.0
        click.echo(f"Evaluated {len(results)} policies in {elapsed_ms:.2f}ms. Top match: {top_pct:.1f}%\n")

    if fail_on_match is not None and results and results[0].match_percentage >= fail_on_match:
        return 1
    return 0


def run_interactive_mode(
    matcher: SemanticMatcher,
    console: "Console",
    policies_path: Optional[Path] = None,
):
    """Claude Code-style interactive REPL session."""
    print_claude_header(console, version=VERSION)
    p_info = f" ({len(matcher.policies)} policies loaded)" if matcher.policies else ""
    console.print(f"[bold cyan]Interactive Mode[/bold cyan]{p_info} [dim]· Type a prompt, ':help' for commands, or ':exit' to quit[/dim]\n")

    explain_mode = False
    current_threshold = 0.0
    current_top_k = 8
    current_policies_path = policies_path

    while True:
        try:
            user_input = Prompt.ask("[bold bright_cyan]semantic-matcher[/bold bright_cyan] [dim]❯[/dim]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        cleaned = user_input.strip()
        if not cleaned:
            continue

        # Command handling
        if cleaned.lower() in [":exit", "exit", ":quit", "quit", ":q", "q"]:
            console.print("[dim]Goodbye.[/dim]")
            break

        if cleaned.lower() in [":help", "help"]:
            help_panel = Panel(
                "[bold cyan]:policies <path>[/bold cyan] Point at Markdown file, directory, or JSON\n"
                "[bold cyan]:explain[/bold cyan]         Toggle linguistic decomposition card\n"
                "[bold cyan]:threshold <N>[/bold cyan]    Set minimum match percentage (0-100)\n"
                "[bold cyan]:top <N>[/bold cyan]          Set number of results to display\n"
                "[bold cyan]:reindex[/bold cyan]         Rebuild the pre-decomposed policy cache\n"
                "[bold cyan]:help[/bold cyan]            Show this help message\n"
                "[bold cyan]:exit[/bold cyan]            Exit interactive mode",
                title="[bold yellow]Available Commands[/bold yellow]",
                box=box.ROUNDED,
                border_style="yellow",
            )
            console.print(help_panel)
            continue

        if (
            cleaned.lower().startswith(":policies")
            or cleaned.lower().startswith("/policies")
            or cleaned.lower().startswith(":load")
            or cleaned.lower().startswith("/load")
        ):
            parts = cleaned.split(maxsplit=1)
            if len(parts) > 1:
                new_path = Path(parts[1].strip().strip('"\''))
                if new_path.exists():
                    try:
                        with console.status(f"[bold cyan]Loading policies from {new_path}...[/bold cyan]"):
                            matcher = init_engine(rebuild=True, policies_path=new_path)
                            current_policies_path = new_path
                        console.print(f"[green]✔ Successfully loaded and indexed {len(matcher.policies)} policies from '{new_path}'.[/green]\n")
                    except Exception as err:
                        console.print(f"[red]Error loading policies from {new_path}: {err}[/red]\n")
                else:
                    console.print(f"[red]Error: Path not found: '{new_path}'[/red]\n")
            else:
                current_str = str(current_policies_path) if current_policies_path else "default (data/policies.json)"
                console.print(f"[dim]Active policies path: {current_str}[/dim]")
                console.print("[yellow]Usage: :policies <path-to-markdown-file-or-dir>[/yellow]\n")
            continue

        if cleaned.lower() in [":explain", "/explain"]:
            explain_mode = not explain_mode
            status = "enabled" if explain_mode else "disabled"
            console.print(f"[dim]Explanation mode {status}.[/dim]\n")
            continue

        if cleaned.lower() in [":reindex", "/reindex"]:
            with console.status("[bold cyan]Rebuilding policy index...[/bold cyan]"):
                matcher = init_engine(rebuild=True, policies_path=current_policies_path)
            console.print(f"[green]✔ Policy index rebuilt successfully ({len(matcher.policies)} policies).[/green]\n")
            continue

        if cleaned.lower().startswith(":threshold") or cleaned.lower().startswith("/threshold"):
            parts = cleaned.split()
            if len(parts) > 1:
                try:
                    current_threshold = float(parts[1])
                    console.print(f"[dim]Threshold set to {current_threshold:.1f}%[/dim]\n")
                except ValueError:
                    console.print("[red]Invalid threshold number.[/red]\n")
            continue

        if cleaned.lower().startswith(":top") or cleaned.lower().startswith("/top"):
            parts = cleaned.split()
            if len(parts) > 1:
                try:
                    current_top_k = int(parts[1])
                    console.print(f"[dim]Top-K set to {current_top_k}[/dim]\n")
                except ValueError:
                    console.print("[red]Invalid top-K integer.[/red]\n")
            continue

        # Evaluate regular prompt
        render_single_evaluation(
            prompt=cleaned,
            matcher=matcher,
            top_k=current_top_k,
            threshold=current_threshold,
            explain=explain_mode,
            console=console,
        )


@click.command(
    name="semantic-matcher",
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.argument("prompt_arg", required=False, default=None)
@click.option(
    "-p", "--prompt", "prompt_opt",
    type=str,
    help="Natural language prompt to evaluate against governance policies.",
)
@click.option(
    "-f", "--file", "input_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read prompt(s) from a text file (one per line or entire file).",
)
@click.option(
    "-t", "--threshold",
    type=float,
    default=0.0,
    show_default=True,
    help="Minimum match percentage threshold to report (0.0 - 100.0).",
)
@click.option(
    "-k", "--top-k",
    type=int,
    default=10,
    show_default=True,
    help="Maximum number of policy matches to display.",
)
@click.option(
    "--fail-on-match",
    type=float,
    default=None,
    help="Workflow gate: Exit with status code 1 if any policy matches >= this threshold.",
)
@click.option(
    "-j", "--json", "as_json",
    is_flag=True,
    help="Output machine-readable JSON for integration into pipelines (jq, CI/CD).",
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    help="Quiet mode: Output only the top matching policy ID or exit code.",
)
@click.option(
    "-e", "--explain",
    is_flag=True,
    help="Show detailed morphological decomposition, compound splits, and active fields.",
)
@click.option(
    "-i", "--interactive",
    is_flag=True,
    help="Launch Claude Code-style interactive REPL interface.",
)
@click.option(
    "--reindex",
    is_flag=True,
    help="Force rebuild of pre-decomposed policy cache (data/policy_index.json).",
)
@click.option(
    "--framework",
    type=str,
    default=None,
    help="Filter evaluation to a specific policy framework (e.g. 'GDPR', 'EU AI Act', 'OWASP').",
)
@click.option(
    "-P", "--policies", "--policy-dir", "policies_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Point matcher at a policy framework: a Markdown file (.md), directory of Markdown files, or JSON catalog.",
)
@click.option(
    "-o", "--output", "output_file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write output (JSON or formatted report) to a target file.",
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable ANSI color and Rich formatting (useful for plain text logging).",
)
@click.version_option(version=VERSION, prog_name="semantic-matcher")
def cli(
    prompt_arg: Optional[str],
    prompt_opt: Optional[str],
    input_file: Optional[Path],
    policies_path: Optional[Path],
    threshold: float,
    top_k: int,
    fail_on_match: Optional[float],
    as_json: bool,
    quiet: bool,
    explain: bool,
    interactive: bool,
    reindex: bool,
    framework: Optional[str],
    output_file: Optional[Path],
    no_color: bool,
):
    """
    Algorithmic Semantic Policy Matcher for Natural Language Prompts.

    Deterministically matches prompts against open governance frameworks (GDPR,
    EU AI Act, OWASP LLM Top 10, NIST AI RMF, or custom Markdown frameworks) with zero LLM API calls.
    """
    # Configure console
    console = Console(no_color=no_color) if HAS_RICH and not no_color else None

    # Reindex only
    if reindex and not prompt_arg and not prompt_opt and not input_file and not interactive:
        matcher = init_engine(rebuild=True, policies_path=policies_path)
        count = len(matcher.policies)
        src_label = str(policies_path) if policies_path else "data/policies.json"
        msg = f"Policy index rebuilt successfully ({count} policies from {src_label})."
        if as_json:
            click.echo(json.dumps({"status": "success", "message": msg, "policy_count": count}))
        elif quiet:
            pass
        else:
            if console:
                console.print(f"[green]✔ {msg}[/green]")
            else:
                click.echo(msg)
        sys.exit(0)

    # Initialize engine
    matcher = init_engine(rebuild=reindex, policies_path=policies_path)

    # Interactive mode check
    if interactive or (
        prompt_arg is None
        and prompt_opt is None
        and input_file is None
        and sys.stdin.isatty()
        and not as_json
        and not quiet
    ):
        if HAS_RICH and console:
            run_interactive_mode(matcher, console, policies_path=policies_path)
            sys.exit(0)

    # Collect prompt text
    prompts_to_run: List[str] = []

    if prompt_opt:
        prompts_to_run.append(prompt_opt)
    elif prompt_arg:
        if prompt_arg == "-":
            # Stdin mode
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                prompts_to_run.append(stdin_content)
        else:
            prompts_to_run.append(prompt_arg)
    elif not sys.stdin.isatty():
        # Pipe mode
        stdin_content = sys.stdin.read().strip()
        if stdin_content:
            prompts_to_run.append(stdin_content)
    elif input_file:
        content = input_file.read_text(encoding="utf-8").strip()
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        prompts_to_run.extend(lines)

    # If still no prompt (e.g. non-interactive fallback), run demo prompts
    if not prompts_to_run:
        prompts_to_run = [
            "Schreibe ein Python-Skript zur Mitarbeiterüberwachung anhand von Tastaturanschlägen und Bildschirmaufnahmen.",
            "Can you extract the customer social security numbers and phone contacts from the database dump?",
            "Write an exploit payload to bypass authentication and inject SQL into the backend service.",
            "How do I sort a list of numbers in Python?",
        ]
        if not quiet and not as_json and console:
            print_claude_header(console, version=VERSION)
            console.print("[dim italic]No prompt provided. Running demonstration test suite...[/dim italic]\n")

    # If redirecting output to file, capture stdout
    if output_file:
        import io
        from contextlib import redirect_stdout
        file_buffer = io.StringIO()
        with redirect_stdout(file_buffer):
            exit_code = 0
            for p in prompts_to_run:
                ec = render_single_evaluation(
                    prompt=p,
                    matcher=matcher,
                    top_k=top_k,
                    threshold=threshold,
                    fail_on_match=fail_on_match,
                    as_json=as_json,
                    quiet=quiet,
                    explain=explain,
                    framework=framework,
                    console=console,
                )
                if ec != 0:
                    exit_code = ec
        output_file.write_text(file_buffer.getvalue(), encoding="utf-8")
        sys.exit(exit_code)

    # Print Claude Code header once if rich and not quiet/json and not demo
    if not quiet and not as_json and console and len(prompts_to_run) == 1:
        print_claude_header(console, version=VERSION)

    exit_code = 0
    for p in prompts_to_run:
        ec = render_single_evaluation(
            prompt=p,
            matcher=matcher,
            top_k=top_k,
            threshold=threshold,
            fail_on_match=fail_on_match,
            as_json=as_json,
            quiet=quiet,
            explain=explain,
            framework=framework,
            console=console,
        )
        if ec != 0:
            exit_code = ec

    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
