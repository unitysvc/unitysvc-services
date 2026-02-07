"""Shared output formatting for CLI commands.

Provides a single format_output() function that handles json, table, tsv,
and csv output for list-of-dicts tabular data.
"""

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

_console = Console()


def escape_csv(value: Any) -> str:
    """Escape a value for CSV output.

    Wraps the value in quotes if it contains commas, quotes, or newlines.
    Internal quotes are doubled per RFC 4180.
    """
    if value is None:
        return ""
    s = str(value)
    if "," in s or '"' in s or "\n" in s:
        return '"' + s.replace('"', '""') + '"'
    return s


def format_output(
    data: list[dict[str, Any]],
    *,
    output_format: str = "table",
    columns: list[str] | None = None,
    column_styles: dict[str, str] | None = None,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    """Format and print tabular data in the requested format.

    Args:
        data: List of dicts representing rows.
        output_format: One of "json", "table", "tsv", "csv".
        columns: Which dict keys to include, in order.
            Defaults to all keys from the first row.
        column_styles: Rich styles per column name (table mode only).
        title: Table title (table mode only).
        console: Rich Console instance. Defaults to module-level console.
    """
    con = console or _console

    if not columns:
        columns = list(data[0].keys()) if data else []

    if output_format == "json":
        # Filter to selected columns
        filtered = [{k: row.get(k) for k in columns} for row in data]
        print(json.dumps(filtered, indent=2, default=str))

    elif output_format in ("tsv", "csv"):
        sep = "\t" if output_format == "tsv" else ","
        fmt = escape_csv if output_format == "csv" else lambda v: "" if v is None else str(v)
        print(sep.join(columns))
        for row in data:
            print(sep.join(fmt(row.get(col)) for col in columns))

    elif output_format == "table":
        if not data:
            con.print("[yellow]No data found.[/yellow]")
            return

        table = Table(title=title)
        styles = column_styles or {}

        for col in columns:
            header = col.replace("_", " ").title()
            style = styles.get(col)
            if style:
                table.add_column(header, style=style)
            else:
                table.add_column(header)

        for row in data:
            values = []
            for col in columns:
                v = row.get(col)
                if v is None:
                    values.append("N/A")
                elif isinstance(v, dict | list):
                    values.append(str(v)[:50])
                else:
                    values.append(str(v))
            table.add_row(*values)

        con.print(table)
        con.print(f"\n[green]Total:[/green] {len(data)} item(s)")

    else:
        con.print(f"[red]Unknown format: {output_format}[/red]")
        raise typer.Exit(code=1)
