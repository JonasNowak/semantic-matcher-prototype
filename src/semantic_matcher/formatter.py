"""
Terminal table and UI formatter for policy match results.
Inspired by bat (clean borders, gutter line numbers, subtle colors)
and Claude Code (sleek panels, interactive REPL cards, and status banners).
"""

import math
from typing import Dict, List, Optional

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .models import DecomposedText, MatchResult

# Terminal ANSI color escapes (Fallback for non-rich output)
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"
GRAY = "\033[90m"
DIM = "\033[2m"


def make_score_bar(pct: float, width: int = 10) -> str:
    """Create a visual gauge bar (e.g. ▰▰▰▰▰▰▰▰▱▱) for percentage."""
    pct = max(0.0, min(100.0, pct))
    filled = int(round((pct / 100.0) * width))
    empty = width - filled
    return "▰" * filled + "▱" * empty


def color_percentage(pct: float) -> str:
    """Colorize percentage based on severity."""
    if pct >= 70.0:
        return f"{RED}{BOLD}{pct:5.1f}%{RESET}"
    elif pct >= 40.0:
        return f"{YELLOW}{pct:5.1f}%{RESET}"
    elif pct >= 15.0:
        return f"{CYAN}{pct:5.1f}%{RESET}"
    else:
        return f"{GRAY}{pct:5.1f}%{RESET}"


def format_table(results: List[MatchResult], max_rows: int = 10, use_colors: bool = True) -> str:
    """
    Format a list of MatchResult objects into a bat-inspired Unicode table.
    Works with or without rich.
    """
    if not results:
        return "No policy matches found above threshold."

    rows_to_show = results[:max_rows]

    headers = ["#", "POLICY ID", "POLICY NAME & FRAMEWORK", "MATCH SCORE", "SUB-SCORES", "SIGNALS & TOKENS"]
    widths = [3, 9, 36, 22, 18, 32]

    def pad(text: str, width: int) -> str:
        text = str(text)
        if len(text) > width:
            return text[:width - 3] + "..."
        return text.ljust(width)

    # Bat-style thin Unicode borders
    top_line    = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    header_sep  = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    row_sep     = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    bottom_line = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

    lines = [top_line]

    # Header
    hdr_cells = [f" {pad(h, w)} " for h, w in zip(headers, widths)]
    if use_colors:
        hdr_cells[0] = f" {CYAN}{pad(headers[0], widths[0])}{RESET} "
        for i in range(1, len(hdr_cells)):
            hdr_cells[i] = f" {BOLD}{pad(headers[i], widths[i])}{RESET} "
    lines.append("│" + "│".join(hdr_cells) + "│")
    lines.append(header_sep)

    # Content
    for idx, r in enumerate(rows_to_show):
        # Gutter rank (like bat line numbers)
        rank_str = f"{r.rank:>2} "
        if use_colors:
            rank_str = f"{GRAY}{rank_str}{RESET}"

        # Policy ID
        pol_id = pad(r.policy_id, widths[1])
        if use_colors:
            pol_id = f"{BOLD}{CYAN}{pol_id}{RESET}"

        # Name and framework
        name_short = r.name if len(r.name) <= widths[2] else r.name[:widths[2] - 3] + "..."
        name_cell = pad(name_short, widths[2])

        # Score with gauge
        bar = make_score_bar(r.match_percentage, width=8)
        raw_pct = f"{bar} {r.match_percentage:5.1f}%"
        if use_colors:
            if r.match_percentage >= 70.0:
                score_cell = f"{RED}{BOLD}{raw_pct}{RESET}"
            elif r.match_percentage >= 40.0:
                score_cell = f"{YELLOW}{raw_pct}{RESET}"
            elif r.match_percentage >= 15.0:
                score_cell = f"{CYAN}{raw_pct}{RESET}"
            else:
                score_cell = f"{GRAY}{raw_pct}{RESET}"
        else:
            score_cell = pad(raw_pct, widths[3])

        # Sub-scores
        sub_str = f"M:{int(r.morph_score*100):02d} F:{int(r.field_score*100):02d} T:{int(r.trigger_score*100):02d}"
        sub_cell = pad(sub_str, widths[4])
        if use_colors:
            sub_cell = f"{GRAY}{sub_cell}{RESET}"

        # Signals & tokens
        fields_str = " ".join(f"[{f}]" for f in r.contributing_fields[:2])
        tokens_str = ", ".join(r.contributing_tokens[:3])
        signals = f"{fields_str} {tokens_str}".strip()
        signals_cell = pad(signals, widths[5])

        line = f"│ {rank_str}│ {pol_id} │ {name_cell} │ {score_cell} │ {sub_cell} │ {signals_cell} │"
        lines.append(line)

    lines.append(bottom_line)
    return "\n".join(lines)


# ============================================================================
# Rich / Claude Code UI Components
# ============================================================================

def print_claude_header(console: "Console", version: str = "0.1.0"):
    """Render a Claude Code-style brand header."""
    header_text = Text()
    header_text.append("✦ ", style="bold bright_cyan")
    header_text.append("SEMANTIC POLICY MATCHER", style="bold white")
    header_text.append(f"  v{version}", style="dim cyan")

    panel = Panel(
        header_text,
        box=box.ROUNDED,
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(panel)


def print_prompt_card(console: "Console", prompt: str):
    """Render the user prompt in a Claude Code-style prompt panel."""
    prompt_text = Text()
    prompt_text.append('"', style="dim")
    prompt_text.append(prompt, style="bold bright_white")
    prompt_text.append('"', style="dim")

    panel = Panel(
        prompt_text,
        title="[bold cyan]Prompt Under Evaluation[/bold cyan]",
        title_align="left",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 2),
    )
    console.print(panel)


def print_explanation_card(console: "Console", decomposed: DecomposedText):
    """Render morphological and semantic decomposition cards (Claude Code style)."""
    from .morphology.stemmer import stem_word

    # 1. Morphology & Compounds Table
    compounds_table = Table(
        box=box.SIMPLE_HEAD,
        border_style="dim white",
        header_style="bold cyan",
        show_header=True,
        padding=(0, 1),
    )
    compounds_table.add_column("Token", style="white", no_wrap=True)
    compounds_table.add_column("Morphological Decomposition", style="bright_yellow")
    compounds_table.add_column("Stemmed Morphemes", style="dim cyan")

    # Find tokens that underwent decomposition or notable tokens
    seen_tokens = set()
    shown = 0
    for tok in decomposed.tokens:
        tok_clean = tok.lower().strip()
        if tok_clean in seen_tokens or len(tok_clean) < 3:
            continue
        seen_tokens.add(tok_clean)
        
        parts = [p for p in decomposed.compounds_split if p in tok_clean and p != tok_clean]
        if parts:
            stems = [stem_word(p) for p in parts]
            compounds_table.add_row(tok, " + ".join(parts), ", ".join(stems))
            shown += 1
        else:
            stem = stem_word(tok_clean)
            compounds_table.add_row(tok, "[dim]--[/dim]", stem)
            shown += 1
        if shown >= 8:
            break

    # 2. Semantic Field Activations
    active_fields = {k: v for k, v in decomposed.fields_activation.items() if v > 0.05}
    sorted_fields = sorted(active_fields.items(), key=lambda x: x[1], reverse=True)

    fields_text = Text()
    if sorted_fields:
        for fname, act in sorted_fields:
            pct = int(round(act * 100))
            bar = make_score_bar(pct, width=8)
            fields_text.append(f"  {fname:<22} ", style="bold bright_magenta")
            fields_text.append(f"{bar} ", style="cyan")
            fields_text.append(f"{pct:>3}%\n", style="bold white")
    else:
        fields_text.append("  No significant semantic field activations.\n", style="dim")

    decomp_group = Group(
        Text("Linguistic Morphemes & Subwords:", style="bold cyan"),
        compounds_table,
        Text("\nActive Lexical Fields (Wortfelder):", style="bold cyan"),
        fields_text,
    )

    panel = Panel(
        decomp_group,
        title="[bold yellow]🔬 Algorithmic Decomposition (Morphology & Semantics)[/bold yellow]",
        title_align="left",
        box=box.ROUNDED,
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)


def print_bat_results_table(console: "Console", results: List[MatchResult], max_rows: int = 10):
    """
    Render a bat-inspired table:
    - Gutter column for rank (like bat line numbers)
    - Clean rounded borders with muted cyan/blue lines
    - Visual score meter with severity gradients
    - Badges for frameworks and detected fields
    """
    if not results:
        console.print("[dim]No policy matches found.[/dim]")
        return

    # Bat-style table construction
    table = Table(
        box=box.ROUNDED,
        border_style="dim cyan",
        header_style="bold white",
        show_header=True,
        show_lines=True,
        padding=(0, 1),
    )

    # Gutter column (bat line-number styling)
    table.add_column(
        "#",
        justify="right",
        style="dim cyan",
        no_wrap=True,
        header_style="dim cyan",
    )
    # Policy ID
    table.add_column(
        "POLICY",
        justify="center",
        style="bold bright_cyan",
        no_wrap=True,
    )
    # Name & Framework
    table.add_column(
        "GOVERNANCE POLICY & FRAMEWORK",
        justify="left",
        min_width=24,
    )
    # Match Score & Gauge
    table.add_column(
        "MATCH SCORE",
        justify="left",
        min_width=16,
        no_wrap=True,
    )
    # Sub-scores breakdown
    table.add_column(
        "SUB-SCORES",
        justify="left",
        style="dim",
        min_width=12,
        no_wrap=True,
    )
    # Detected fields & tokens
    table.add_column(
        "DETECTED SIGNALS & TOKENS",
        justify="left",
        min_width=20,
    )

    rows_to_show = results[:max_rows]

    for r in rows_to_show:
        # Gutter line number
        gutter = f"{r.rank}"

        # Policy ID badge
        pol_id_badge = Text(r.policy_id, style="bold bright_cyan")

        # Name & Framework
        name_block = Text()
        name_block.append(f"{r.name}\n", style="bold white")
        name_block.append(f"↳ {r.framework}", style="dim italic")

        # Match score & visual gauge
        score_block = Text()
        pct = r.match_percentage
        bar = make_score_bar(pct, width=8)

        if pct >= 70.0:
            score_block.append(f"{bar} ", style="bold red")
            score_block.append(f"{pct:5.1f}%\n", style="bold bright_red")
            score_block.append("● VIOLATION HIGH", style="bold red on grey15")
        elif pct >= 40.0:
            score_block.append(f"{bar} ", style="bold yellow")
            score_block.append(f"{pct:5.1f}%\n", style="bold yellow")
            score_block.append("▲ WARNING MODERATE", style="bold yellow on grey15")
        elif pct >= 15.0:
            score_block.append(f"{bar} ", style="cyan")
            score_block.append(f"{pct:5.1f}%\n", style="cyan")
            score_block.append("ℹ LOW OVERLAP", style="dim cyan on grey15")
        else:
            score_block.append(f"{bar} ", style="dim")
            score_block.append(f"{pct:5.1f}%\n", style="dim")
            score_block.append("✓ CLEAN", style="dim green")

        # Sub-scores breakdown
        m_pct = int(round(r.morph_score * 100))
        f_pct = int(round(r.field_score * 100))
        t_pct = int(round(r.trigger_score * 100))
        sub_block = Text()
        sub_block.append(f"Morph:   {m_pct:>3}%\n", style="white")
        sub_block.append(f"Field:   {f_pct:>3}%\n", style="bright_magenta")
        sub_block.append(f"Trigger: {t_pct:>3}%", style="bright_yellow")

        # Signals & Tokens
        signals_block = Text()
        if r.contributing_fields:
            for f in r.contributing_fields:
                signals_block.append(f"[{f}] ", style="bold bright_magenta")
            signals_block.append("\n")
        if r.contributing_tokens:
            tokens_str = ", ".join(r.contributing_tokens[:4])
            signals_block.append(f"Tokens: {tokens_str}", style="italic green")
        elif not r.contributing_fields:
            signals_block.append("None", style="dim")

        table.add_row(
            gutter,
            pol_id_badge,
            name_block,
            score_block,
            sub_block,
            signals_block,
        )

    console.print(table)


def print_summary_card(
    console: "Console",
    results: List[MatchResult],
    elapsed_ms: float,
    fail_threshold: Optional[float] = None,
):
    """Render status and gate verdict panel."""
    top = results[0] if results else None
    max_pct = top.match_percentage if top else 0.0

    summary_text = Text()

    # Verdict
    if fail_threshold is not None and max_pct >= fail_threshold:
        border_style = "bold red"
        summary_text.append("✖ CI/WORKFLOW GATE FAILED: ", style="bold bright_red")
        summary_text.append(f"Policy '{top.name}' triggered at {max_pct:.1f}% (Threshold: {fail_threshold:.1f}%)\n", style="white")
    elif max_pct >= 70.0:
        border_style = "bold red"
        summary_text.append("✖ CRITICAL POLICY VIOLATION: ", style="bold bright_red")
        summary_text.append(f"Strong correlation with '{top.name}' ({max_pct:.1f}%)\n", style="white")
    elif max_pct >= 40.0:
        border_style = "bold yellow"
        summary_text.append("▲ WARNING: ", style="bold yellow")
        summary_text.append(f"Moderate correlation with '{top.name}' ({max_pct:.1f}%)\n", style="white")
    else:
        border_style = "bright_green"
        summary_text.append("✔ PROMPT CLEAN: ", style="bold bright_green")
        summary_text.append(f"No significant policy boundaries breached (Highest: {max_pct:.1f}%)\n", style="white")

    summary_text.append(f"⚡ Evaluated {len(results)} policies in {elapsed_ms:.2f}ms ", style="dim cyan")
    summary_text.append("· ", style="dim")
    summary_text.append("Deterministic Algorithmic Execution ", style="dim white")
    summary_text.append("· ", style="dim")
    summary_text.append("Zero LLM Calls", style="dim green")

    panel = Panel(
        summary_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 2),
    )
    console.print(panel)
