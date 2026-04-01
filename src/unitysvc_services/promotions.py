"""Promotions command group - remote operations on uploaded promotions."""

import asyncio
import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI
from .models.promotion_data import describe_scope

console = Console()

app = typer.Typer(
    help=(
        "Manage seller promotions on the backend. "
        "Use 'usvc data validate' and 'usvc data upload' for local file operations."
    ),
)


@app.command("list")
def list_promotions() -> None:
    """List seller's promotions on the backend."""

    async def _list() -> dict[str, Any]:
        api = UnitySvcAPI()
        return await api.get("/seller/promotions")

    try:
        result = asyncio.run(_list())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list promotions: {e}")
        raise typer.Exit(code=1)

    rules = result.get("data", [])
    if not rules:
        console.print("[dim]No promotions found[/dim]")
        return

    table = Table(title="Promotions")
    table.add_column("Name", style="bold")
    table.add_column("Scope")
    table.add_column("Code")
    table.add_column("Status")
    table.add_column("Priority", justify="right")
    table.add_column("ID", style="dim")

    for rule in rules:
        status_style = {
            "active": "green",
            "draft": "yellow",
            "paused": "red",
        }.get(rule.get("status", ""), "")
        table.add_row(
            rule.get("name", ""),
            describe_scope(rule.get("scope")),
            rule.get("code", ""),
            f"[{status_style}]{rule.get('status', '')}[/{status_style}]",
            str(rule.get("priority", 0)),
            str(rule.get("id", ""))[:8],
        )

    console.print(table)


@app.command("show")
def show_promotion_remote(
    name_or_id: str = typer.Argument(
        ..., help="Promotion name or ID"
    ),
) -> None:
    """Show details of a promotion on the backend."""

    async def _show() -> dict[str, Any]:
        api = UnitySvcAPI()
        return await _find_promotion_by_name(api, name_or_id)

    try:
        rule = asyncio.run(_show())
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{rule.get('name', '?')}[/bold]")
    if rule.get("description"):
        console.print(f"  {rule['description']}")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    table.add_row("id", str(rule.get("id", "")))
    table.add_row("scope", describe_scope(rule.get("scope")))
    table.add_row("code", rule.get("code", "(none)"))
    table.add_row(
        "pricing",
        json.dumps(rule.get("pricing", {}), indent=2),
    )
    table.add_row("apply_at", str(rule.get("apply_at", "")))
    table.add_row("priority", str(rule.get("priority", 0)))

    status_val = rule.get("status", "")
    status_style = {
        "active": "green", "draft": "yellow", "paused": "red",
    }.get(status_val, "")
    table.add_row(
        "status",
        f"[{status_style}]{status_val}[/{status_style}]",
    )

    console.print(table)


@app.command("activate")
def activate_promotion(
    name_or_id: str = typer.Argument(
        ..., help="Promotion name or ID",
    ),
) -> None:
    """Activate a promotion."""

    async def _activate() -> dict[str, Any]:
        api = UnitySvcAPI()
        promo = await _find_promotion_by_name(api, name_or_id)
        return await api.post(
            f"/seller/promotions/{promo['id']}/activate",
        )

    try:
        result = asyncio.run(_activate())
        console.print(
            f"[green]✓[/green] Activated: "
            f"{result.get('name', name_or_id)}"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to activate: {e}")
        raise typer.Exit(code=1)


@app.command("pause")
def pause_promotion(
    name_or_id: str = typer.Argument(
        ..., help="Promotion name or ID",
    ),
) -> None:
    """Pause a promotion."""

    async def _pause() -> dict[str, Any]:
        api = UnitySvcAPI()
        promo = await _find_promotion_by_name(api, name_or_id)
        return await api.post(
            f"/seller/promotions/{promo['id']}/pause",
        )

    try:
        result = asyncio.run(_pause())
        console.print(
            f"[green]✓[/green] Paused: "
            f"{result.get('name', name_or_id)}"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to pause: {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_promotion(
    name_or_id: str = typer.Argument(
        ..., help="Promotion name or ID",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation",
    ),
) -> None:
    """Delete a promotion."""
    if not force:
        confirm = typer.confirm(
            f"Delete promotion '{name_or_id}'?",
        )
        if not confirm:
            raise typer.Exit(code=0)

    async def _delete() -> None:
        api = UnitySvcAPI()
        promo = await _find_promotion_by_name(api, name_or_id)
        await api.delete(f"/seller/promotions/{promo['id']}")

    try:
        asyncio.run(_delete())
        console.print(f"[green]✓[/green] Deleted: {name_or_id}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to delete: {e}")
        raise typer.Exit(code=1)


# ============================================================================
# HELPERS
# ============================================================================


async def _find_promotion_by_name(
    api: UnitySvcAPI, name_or_id: str,
) -> dict[str, Any]:
    """Find a promotion by name or ID prefix.

    Raises:
        typer.Exit: If not found or ambiguous match
    """
    result = await api.get("/seller/promotions")
    rules = result.get("data", [])

    # Exact name match first
    for rule in rules:
        if rule.get("name") == name_or_id:
            return rule

    # ID prefix match
    matches = [
        r
        for r in rules
        if str(r.get("id", "")).startswith(name_or_id)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        console.print(
            f"[red]Error:[/red] Ambiguous ID prefix "
            f"'{name_or_id}' matches {len(matches)} promotions"
        )
        raise typer.Exit(code=1)

    console.print(
        f"[red]Error:[/red] Promotion '{name_or_id}' not found"
    )
    raise typer.Exit(code=1)
