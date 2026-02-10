"""Test runner commands for executing service tests locally."""

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI
from .output import format_output

app = typer.Typer(help="Run and manage service tests")
console = Console()


class TestRunner(UnitySvcAPI):
    """Run tests for services locally and submit results to backend."""

    async def list_documents(self, service_id: str, executable_only: bool = True) -> list[dict[str, Any]]:
        """List documents for a service."""
        params = {"executable_only": "true"} if executable_only else {}
        result = await self.get(f"/seller/services/{service_id}/documents", params=params)
        # API may return list directly or wrapped in {"data": [...]}
        if isinstance(result, list):
            return result
        return result.get("data", [])

    async def get_document(self, document_id: str, file_content: bool = False) -> dict[str, Any]:
        """Get document details, optionally with file content."""
        params = {"file_content": "true"} if file_content else {}
        return await self.get(f"/seller/documents/{document_id}", params=params)

    async def update_test_result(
        self,
        document_id: str,
        status: str,
        tests: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update document test metadata with execution results."""
        data: dict[str, Any] = {
            "status": status,
            "executed_at": datetime.now(UTC).isoformat(),
        }
        if tests is not None:
            data["tests"] = tests

        return await self.patch(f"/seller/documents/{document_id}", json_data=data)

    async def list_interfaces(self, service_id: str) -> list[dict[str, Any]]:
        """List all access interfaces for a service from the backend."""
        result = await self.get(f"/seller/services/{service_id}/interfaces")
        if isinstance(result, list):
            return result
        return result.get("data", [])

    async def skip_test(self, document_id: str) -> dict[str, Any]:
        """Mark a test as skipped."""
        return await self.post(f"/seller/documents/{document_id}/skip")

    async def unskip_test(self, document_id: str) -> dict[str, Any]:
        """Remove skip status from a test."""
        return await self.post(f"/seller/documents/{document_id}/unskip")


@app.command("list")
def list_tests(
    service_id: str = typer.Argument(
        None, help="Service ID (supports partial IDs). If not specified, lists tests for all services."
    ),
    all_docs: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all documents, not just executable ones",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, tsv, csv",
    ),
):
    """List testable documents for a service or all services.

    By default, shows only executable documents (code_example, connectivity_test).
    Use --all to show all documents.

    Examples:
        usvc services test list                 # All services
        usvc services test list 297040cd        # Specific service
        usvc services test list --all           # Include non-executable docs
        usvc services test list --format json
    """

    async def _list():
        async def _fetch_interfaces(runner: TestRunner, svc_id: str) -> list[tuple[str, str]]:
            try:
                interfaces = await runner.list_interfaces(svc_id)
                return _resolve_interfaces(interfaces)
            except Exception:
                return [("default", "")]

        async with TestRunner() as runner:
            if service_id:
                # List documents for specific service
                # First get service details to get full ID and name
                services = await runner.get("/seller/services")
                service_list = services.get("data", services) if isinstance(services, dict) else services

                # Find matching service by partial ID
                matched_svc = None
                for svc in service_list:
                    svc_id = str(svc.get("id", ""))
                    if svc_id.startswith(service_id) or service_id in svc_id:
                        matched_svc = svc
                        break

                if not matched_svc:
                    raise ValueError(f"Service not found: {service_id}")

                full_id = str(matched_svc.get("id", ""))
                svc_name = matched_svc.get("name", full_id[:8])
                docs = await runner.list_documents(full_id, executable_only=not all_docs)
                interfaces = await _fetch_interfaces(runner, full_id)
                return [(full_id, svc_name, docs, interfaces)]
            else:
                # List all services first, then get documents for each
                services = await runner.get("/seller/services")
                service_list = services.get("data", services) if isinstance(services, dict) else services

                results = []
                for svc in service_list:
                    svc_id = str(svc.get("id", ""))
                    svc_name = svc.get("name", svc_id[:8])
                    try:
                        docs = await runner.list_documents(svc_id, executable_only=not all_docs)
                        if docs:
                            interfaces = await _fetch_interfaces(runner, svc_id)
                            results.append((svc_id, svc_name, docs, interfaces))
                    except Exception:
                        # Skip services that fail (e.g., no documents)
                        pass
                return results

    try:
        results = asyncio.run(_list())

        # Flatten into one row per (doc, interface) pair
        rows: list[dict[str, str]] = []
        for svc_id, svc_name, docs, interfaces in results:
            for doc in docs:
                meta = doc.get("meta") or {}
                test_meta = meta.get("test") or {}
                doc_id = doc.get("id", "")
                for iface_name, iface_url in interfaces:
                    rows.append({
                        "service_id": svc_id,
                        "service_name": svc_name,
                        "doc_id": doc_id[:8] + "..." if doc_id else "-",
                        "title": doc.get("title", ""),
                        "category": doc.get("category", ""),
                        "interface": iface_name,
                        "interface_base_url": iface_url,
                        "status": test_meta.get("status", "pending"),
                    })

        format_output(
            rows,
            output_format=format,
            columns=["service_name", "doc_id", "title", "category", "interface", "status"],
            column_styles={
                "service_name": "cyan",
                "doc_id": "yellow",
                "title": "white",
                "category": "blue",
                "interface": "magenta",
            },
            title="Service Tests",
            console=console,
        )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def _find_document(documents: list[dict], title: str | None, doc_id: str | None) -> dict:
    """Find a document by title or document ID."""
    if doc_id:
        # Find by document ID (supports partial)
        doc = next((d for d in documents if str(d.get("id", "")).startswith(doc_id)), None)
        if not doc:
            raise ValueError(f"Document not found with ID: {doc_id}")
        return doc
    elif title:
        # Find by title
        doc = next((d for d in documents if d.get("title") == title), None)
        if not doc:
            available = [d.get("title") for d in documents]
            raise ValueError(f"Document not found: '{title}'. Available: {available}")
        return doc
    else:
        raise ValueError("Either --title or --doc-id must be specified")


def _resolve_interfaces(interfaces: list[dict]) -> list[tuple[str, str]]:
    """Extract (name, base_url) pairs from interface list.

    Filters out inactive interfaces. The backend resolves
    ``${GATEWAY_BASE_URL}`` placeholders before returning data,
    so base_url values are ready to use as-is.
    """
    result = []
    for iface in interfaces:
        if not iface.get("is_active", True):
            continue
        result.append((iface.get("name", "default"), iface.get("base_url", "")))

    if not result:
        result.append(("default", ""))

    return result


@app.command("show")
def show_test(
    service_id: str = typer.Argument(None, help="Service ID (required when using --title)"),
    title: str = typer.Option(None, "--title", "-t", help="Document title to show (requires service_id)"),
    doc_id: str = typer.Option(None, "--doc-id", "-d", help="Document ID (supports partial IDs)"),
    script: bool = typer.Option(
        False,
        "--script",
        "-s",
        help="Show script content and execution environment (for debugging)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show test details and metadata for a document.

    When --doc-id is provided, service_id is not required since the document ID
    uniquely identifies the document. When --title is used, service_id is required
    to search within the service's documents.

    Examples:
        usvc services show-test -d abc123
        usvc services show-test -d abc123 --script
        usvc services show-test 297040cd --title "Quick Start"
        usvc services show-test 297040cd -t "Connectivity Test" --format table
    """
    if not title and not doc_id:
        console.print("[red]Error: Either --title or --doc-id must be specified[/red]")
        raise typer.Exit(code=1)

    if title and not service_id:
        console.print("[red]Error: service_id is required when using --title[/red]")
        raise typer.Exit(code=1)

    async def _show():
        async with TestRunner() as runner:
            if doc_id:
                # doc_id uniquely identifies the document, no need for service_id
                return await runner.get_document(doc_id, file_content=script)
            else:
                # --title requires listing documents for the service first
                documents = await runner.list_documents(service_id, executable_only=False)
                doc = _find_document(documents, title, doc_id)
                return await runner.get_document(doc["id"], file_content=script)

    try:
        document = asyncio.run(_show())

        if script:
            # Show script content for debugging
            console.print(f"[bold cyan]Document:[/bold cyan] {document.get('title', 'Unknown')}")
            console.print(f"[dim]ID: {document.get('id')}[/dim]")
            console.print(f"[dim]MIME type: {document.get('mime_type')}[/dim]")
            console.print()

            # Remind user about environment setup
            console.print("[bold yellow]Environment Variables (set these before running):[/bold yellow]")
            console.print("  UNITYSVC_BASE_URL=<gateway_url>")
            console.print("  UNITYSVC_API_KEY=<your_customer_api_key>")
            console.print()

            # Show script content
            file_content = document.get("file_content")
            if file_content:
                console.print("[bold yellow]Script Content:[/bold yellow]")
                console.print("-" * 60)
                console.print(file_content)
                console.print("-" * 60)
            else:
                console.print("[yellow]No script content available[/yellow]")

        elif format == "json":
            console.print(json.dumps(document, indent=2, default=str))
        elif format in ("tsv", "csv"):
            sep = "\t" if format == "tsv" else ","
            meta = document.get("meta") or {}
            test_meta = meta.get("test") or {}
            fields = ["id", "title", "category", "mime_type", "status"]
            print(sep.join(fields))
            row = [
                document.get("id", ""),
                document.get("title", ""),
                document.get("category", ""),
                document.get("mime_type", ""),
                test_meta.get("status", "pending"),
            ]
            if format == "csv":
                row = [f'"{v}"' if "," in str(v) or '"' in str(v) else str(v) for v in row]
            print(sep.join(str(v) for v in row))
        elif format == "table":
            table = Table(title=f"Document: {title}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            # Show main fields
            for key in ["id", "title", "category", "mime_type", "filename", "filesize"]:
                if key in document:
                    table.add_row(key, str(document[key]) if document[key] is not None else "-")

            # Show test metadata
            meta = document.get("meta") or {}
            test_meta = meta.get("test") or {}
            if test_meta:
                table.add_row("[bold]test[/bold]", "")
                for key, value in test_meta.items():
                    if value is not None:
                        display_value = str(value)
                        if len(display_value) > 100:
                            display_value = display_value[:100] + "..."
                        table.add_row(f"  {key}", display_value)

            console.print(table)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("run")
def run_test(
    service_id: str = typer.Argument(..., help="Service ID (supports partial IDs, minimum 8 chars)"),
    title: str = typer.Option(None, "--title", "-t", help="Only run test with this title (runs all if not specified)"),
    doc_id: str = typer.Option(None, "--doc-id", "-d", help="Only run test with this document ID (supports partial)"),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Execution timeout in seconds",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output including stdout/stderr",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force rerun all tests (ignore previous success status)",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        "-x",
        help="Stop on first failure",
    ),
):
    """Run tests locally and submit results to backend.

    By default, runs ALL executable tests for the service. Use --title or --doc-id
    to run a specific test.

    Fetches scripts from the backend and executes locally. UNITYSVC_BASE_URL is set
    automatically per access interface. Set UNITYSVC_API_KEY to your ops_customer
    team API key before running tests:

        export UNITYSVC_API_KEY=svcpass_your_customer_api_key

    Results are submitted back to the backend to update test metadata.

    Examples:
        # Run all tests for a service
        usvc services run-tests 297040cd

        # Run specific test by title
        usvc services run-tests 297040cd --title "Quick Start"

        # Run specific test by document ID
        usvc services run-tests 297040cd -d abc123

        # Run with verbose output
        usvc services run-tests 297040cd --verbose

        # Force rerun (ignore previous success)
        usvc services run-tests 297040cd --force

        # Stop on first failure
        usvc services run-tests 297040cd --fail-fast
    """
    from .utils import execute_script_content

    def _execute_script(file_content: str, mime_type: str, output_contains: str | None, resolved_base_url: str) -> dict:
        """Execute a single script with the given base URL. Returns result dict."""
        exec_env: dict[str, str] = {}
        if resolved_base_url:
            exec_env["UNITYSVC_BASE_URL"] = resolved_base_url

        try:
            result = execute_script_content(
                script=file_content,
                mime_type=mime_type,
                env_vars=exec_env,
                timeout=timeout,
                output_contains=output_contains,
            )
            return {
                "exit_code": result.get("exit_code", -1),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "status": result.get("status", "task_failed"),
                "error": result.get("error"),
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "status": "task_failed",
                "error": str(e),
            }

    async def _run():
        async with TestRunner() as runner:
            # List all executable documents
            documents = await runner.list_documents(service_id, executable_only=True)

            if not documents:
                console.print("[yellow]No testable documents found.[/yellow]")
                return []

            # Filter by title or doc_id if specified
            if title or doc_id:
                doc = _find_document(documents, title, doc_id)
                documents = [doc]

            # Fetch access interfaces from the backend (URLs already resolved)
            try:
                interfaces_data = await runner.list_interfaces(service_id)
                interfaces_list = _resolve_interfaces(interfaces_data)
            except Exception:
                interfaces_list = [("default", "")]

            # Show environment context before running tests
            api_key = os.environ.get("UNITYSVC_API_KEY", "")
            if interfaces_list or api_key:
                for iface_name, iface_url in interfaces_list:
                    console.print(f"[dim]{iface_name}: UNITYSVC_BASE_URL={iface_url}[/dim]")
                api_key_display = f"{api_key[:12]}...{api_key[-4:]}" if len(api_key) > 20 else api_key
                console.print(f"[dim]UNITYSVC_API_KEY={api_key_display or '(not set)'}[/dim]")
                console.print()
            else:
                console.print("[yellow]Warning: No interfaces found and UNITYSVC_API_KEY is not set[/yellow]")
                console.print()

            multi_interface = len(interfaces_list) > 1
            stop_early = False
            results = []
            for doc in documents:
                if stop_early:
                    break

                doc_title = doc.get("title", doc.get("id", ""))
                document_id = doc["id"]

                # Check status from list response (avoids fetching document if skipped)
                meta = doc.get("meta") or {}
                test_meta = meta.get("test") or {}
                if not force:
                    status = test_meta.get("status")
                    if status == "success":
                        label = f"{doc_title} (all interfaces)" if multi_interface else doc_title
                        console.print(f"[cyan]Running: {label}...[/cyan]")
                        console.print("  [yellow]SKIP[/yellow] (already passed)")
                        results.append({"title": doc_title, "status": "skipped", "reason": "already passed"})
                        continue
                    if status == "skip":
                        label = f"{doc_title} (all interfaces)" if multi_interface else doc_title
                        console.print(f"[cyan]Running: {label}...[/cyan]")
                        console.print("  [yellow]SKIP[/yellow] (marked as skip)")
                        results.append({"title": doc_title, "status": "skipped", "reason": "marked as skip"})
                        continue

                # Fetch document with file content once per document
                full_doc = await runner.get_document(document_id, file_content=True)
                file_content = full_doc.get("file_content")
                if not file_content:
                    console.print(f"[cyan]Running: {doc_title}...[/cyan]")
                    console.print("  [yellow]SKIP[/yellow] (no file content)")
                    results.append({"title": doc_title, "status": "skipped", "reason": "no file content"})
                    continue

                mime_type = full_doc.get("mime_type", "")
                full_meta = full_doc.get("meta") or {}
                output_contains = full_meta.get("output_contains")

                # Run script against each access interface
                doc_results = []
                for iface_name, resolved_url in interfaces_list:
                    label = f"{doc_title} [{iface_name}]" if multi_interface else doc_title
                    console.print(f"[cyan]Running: {label}...[/cyan]")

                    result = _execute_script(file_content, mime_type, output_contains, resolved_url)
                    result["title"] = label
                    result["interface"] = iface_name
                    result["resolved_base_url"] = resolved_url
                    result["file_content"] = file_content
                    doc_results.append(result)
                    results.append(result)

                    # Display result
                    if result["status"] == "success":
                        console.print("  [green]PASS[/green]")
                    else:
                        console.print(f"  [red]FAIL[/red] ({result['status']})")
                        if result.get("error"):
                            console.print(f"  [red]Error: {result['error']}[/red]")

                    # Save debug files on failure
                    if result["status"] != "success":
                        filename = doc.get("filename", "")
                        script_stem = os.path.splitext(filename)[0] if filename else doc.get("id", "unknown")[:8]
                        # Include interface name in debug file names for disambiguation
                        safe_iface = iface_name.replace(" ", "_").replace("/", "_")
                        base_name = f"failed_{service_id}_{script_stem}_{safe_iface}"
                        if result.get("file_content"):
                            ext = os.path.splitext(filename)[1] if filename else ""
                            script_name = f"{base_name}{ext}"
                            with open(script_name, "w") as f:
                                f.write(result["file_content"])
                            os.chmod(script_name, 0o755)
                            console.print(f"  [dim]script: {script_name}[/dim]")
                        if result.get("stdout"):
                            with open(f"{base_name}.out", "w") as f:
                                f.write(result["stdout"])
                            console.print(f"  [dim]stdout: {base_name}.out[/dim]")
                        if result.get("stderr"):
                            with open(f"{base_name}.err", "w") as f:
                                f.write(result["stderr"])
                            console.print(f"  [dim]stderr: {base_name}.err[/dim]")
                        env_path = f"{base_name}.env"
                        with open(env_path, "w") as f:
                            f.write(f"UNITYSVC_BASE_URL={resolved_url}\n")
                            f.write(f"UNITYSVC_API_KEY={os.environ.get('UNITYSVC_API_KEY', '')}\n")
                        console.print(f"  [dim]   env: {env_path}[/dim]")

                    # Fail fast
                    if fail_fast and result["status"] != "success":
                        console.print("[red]Stopping on first failure (--fail-fast)[/red]")
                        stop_early = True
                        break

                # Update backend with worst status + per-interface breakdown
                if doc_results:
                    failed = [r for r in doc_results if r["status"] not in ("success", "skipped")]
                    worst = failed[0] if failed else doc_results[0]
                    # Build per-interface results
                    iface_results: dict[str, Any] = {}
                    for r in doc_results:
                        entry: dict[str, Any] = {"status": r["status"]}
                        if r.get("exit_code") is not None:
                            entry["exit_code"] = r["exit_code"]
                        if r.get("error"):
                            entry["error"] = r["error"]
                        if r.get("stdout"):
                            entry["stdout"] = r["stdout"][:10000]
                        if r.get("stderr"):
                            entry["stderr"] = r["stderr"][:10000]
                        iface_results[r.get("interface", "default")] = entry
                    try:
                        await runner.update_test_result(
                            document_id=document_id,
                            status=worst["status"],
                            tests=iface_results,
                        )
                    except Exception as update_error:
                        console.print(f"  [yellow]Warning: Failed to update test result: {update_error}[/yellow]")

            return results

    try:
        results = asyncio.run(_run())

        # Summary
        if results:
            passed = sum(1 for r in results if r["status"] == "success")
            failed = sum(1 for r in results if r["status"] not in ("success", "skipped"))
            skipped = sum(1 for r in results if r["status"] == "skipped")

            console.print()
            console.print(f"[bold]Results:[/bold] {passed} passed, {failed} failed, {skipped} skipped")

            if failed > 0:
                raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("skip")
def skip_test(
    service_id: str = typer.Argument(..., help="Service ID (supports partial IDs, minimum 8 chars)"),
    title: str = typer.Option(None, "--title", "-t", help="Document title to skip"),
    doc_id: str = typer.Option(None, "--doc-id", "-d", help="Document ID (supports partial IDs)"),
):
    """Mark a test as skipped.

    Skipped tests won't be required to pass for service approval.
    Only code_example documents can be skipped (connectivity_test cannot).

    Examples:
        usvc services skip-test 297040cd --title "Optional Demo"
        usvc services skip-test 297040cd -d abc123
    """
    if not title and not doc_id:
        console.print("[red]Error: Either --title or --doc-id must be specified[/red]")
        raise typer.Exit(code=1)

    async def _skip():
        async with TestRunner() as runner:
            # Find document by title or ID
            documents = await runner.list_documents(service_id, executable_only=True)
            doc = _find_document(documents, title, doc_id)

            return await runner.skip_test(doc["id"])

    try:
        asyncio.run(_skip())
        test_name = title or doc_id
        console.print(f"[green]Test '{test_name}' marked as skipped.[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("unskip")
def unskip_test(
    service_id: str = typer.Argument(..., help="Service ID (supports partial IDs, minimum 8 chars)"),
    title: str = typer.Option(None, "--title", "-t", help="Document title to unskip"),
    doc_id: str = typer.Option(None, "--doc-id", "-d", help="Document ID (supports partial IDs)"),
):
    """Remove skip status from a test.

    The test will be set to 'pending' status and can be executed again.

    Examples:
        usvc services unskip-test 297040cd --title "Optional Demo"
        usvc services unskip-test 297040cd -d abc123
    """
    if not title and not doc_id:
        console.print("[red]Error: Either --title or --doc-id must be specified[/red]")
        raise typer.Exit(code=1)

    async def _unskip():
        async with TestRunner() as runner:
            # Find document by title or ID
            documents = await runner.list_documents(service_id, executable_only=True)
            doc = _find_document(documents, title, doc_id)

            return await runner.unskip_test(doc["id"])

    try:
        asyncio.run(_unskip())
        test_name = title or doc_id
        console.print(f"[green]Test '{test_name}' unskipped (status: pending).[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
