"""Test runner commands for executing service tests locally."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI

app = typer.Typer(help="Run and manage service tests")
console = Console()


class TestRunner(UnitySvcAPI):
    """Run tests for services locally and submit results to backend."""

    async def list_documents(
        self, service_id: str, executable_only: bool = True
    ) -> list[dict[str, Any]]:
        """List documents for a service."""
        params = {"executable_only": "true"} if executable_only else {}
        result = await self.get(f"/seller/services/{service_id}/documents", params=params)
        # API may return list directly or wrapped in {"data": [...]}
        if isinstance(result, list):
            return result
        return result.get("data", [])

    async def get_document(
        self, document_id: str, file_content: bool = False
    ) -> dict[str, Any]:
        """Get document details, optionally with file content."""
        params = {"file_content": "true"} if file_content else {}
        return await self.get(f"/seller/documents/{document_id}", params=params)

    async def update_test_result(
        self,
        document_id: str,
        status: str,
        exit_code: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Update document test metadata with execution results."""
        data: dict[str, Any] = {
            "status": status,
            "executed_at": datetime.now(UTC).isoformat(),
        }
        if exit_code is not None:
            data["exit_code"] = exit_code
        if stdout is not None:
            data["stdout"] = stdout[:10000]  # Truncate to 10KB
        if stderr is not None:
            data["stderr"] = stderr[:10000]
        if error is not None:
            data["error"] = error

        return await self.patch(f"/seller/documents/{document_id}", json_data=data)

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
                return [(full_id, svc_name, docs)]  # (svc_id, svc_name, docs)
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
                            results.append((svc_id, svc_name, docs))
                    except Exception:
                        # Skip services that fail (e.g., no documents)
                        pass
                return results

    try:
        results = asyncio.run(_list())

        if format == "json":
            # Flatten for JSON output
            all_docs_list = []
            for svc_id, svc_name, docs in results:
                for doc in docs:
                    doc["service_id"] = svc_id
                    doc["service_name"] = svc_name
                    all_docs_list.append(doc)
            console.print(json.dumps(all_docs_list, indent=2, default=str))
        elif format in ("tsv", "csv"):
            sep = "\t" if format == "tsv" else ","
            fields = ["service_id", "service_name", "doc_id", "title", "category", "status"]
            print(sep.join(fields))
            for svc_id, svc_name, docs in results:
                for doc in docs:
                    meta = doc.get("meta") or {}
                    test_meta = meta.get("test") or {}
                    row = [
                        svc_id,
                        svc_name,
                        doc.get("id", ""),
                        doc.get("title", ""),
                        doc.get("category", ""),
                        test_meta.get("status", "pending"),
                    ]
                    if format == "csv":
                        row = [f'"{v}"' if "," in str(v) or '"' in str(v) else str(v) for v in row]
                    print(sep.join(str(v) for v in row))
        elif format == "table":
            total = 0
            for svc_id, svc_name, documents in results:
                if not documents:
                    continue

                # Show service header with full ID
                console.print(f"\n[bold cyan]{svc_name}[/bold cyan] [dim]({svc_id})[/dim]")

                table = Table()
                table.add_column("Doc ID", style="yellow", no_wrap=True)
                table.add_column("Title", style="cyan")
                table.add_column("Category", style="blue")
                table.add_column("Status", style="white")

                for doc in documents:
                    meta = doc.get("meta") or {}
                    test_meta = meta.get("test") or {}
                    status = test_meta.get("status", "pending")
                    doc_id = doc.get("id", "")

                    # Color status
                    if status == "success":
                        status_display = f"[green]{status}[/green]"
                    elif status in ("script_failed", "task_failed", "unexpected_output"):
                        status_display = f"[red]{status}[/red]"
                    elif status == "skip":
                        status_display = f"[yellow]{status}[/yellow]"
                    elif status == "running":
                        status_display = f"[blue]{status}[/blue]"
                    else:
                        status_display = status

                    table.add_row(
                        doc_id[:8] + "..." if doc_id else "-",
                        doc.get("title", ""),
                        doc.get("category", ""),
                        status_display,
                    )
                    total += 1

                console.print(table)

            if total == 0:
                console.print("[yellow]No testable documents found.[/yellow]")
            else:
                console.print(f"\n[dim]Total: {total} document(s)[/dim]")
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def _find_document(documents: list[dict], title: str | None, doc_id: str | None) -> dict:
    """Find a document by title or document ID."""
    if doc_id:
        # Find by document ID (supports partial)
        doc = next(
            (d for d in documents if str(d.get("id", "")).startswith(doc_id)),
            None
        )
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


@app.command("show")
def show_test(
    service_id: str = typer.Argument(
        ..., help="Service ID (supports partial IDs, minimum 8 chars)"
    ),
    title: str = typer.Option(
        None, "--title", "-t", help="Document title to show"
    ),
    doc_id: str = typer.Option(
        None, "--doc-id", "-d", help="Document ID (supports partial IDs)"
    ),
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

    Examples:
        usvc services show-test 297040cd --title "Quick Start"
        usvc services show-test 297040cd -d abc123
        usvc services show-test 297040cd -t "Connectivity Test" --format table
        usvc services show-test 297040cd -d abc123 --script  # Show script and env
    """
    if not title and not doc_id:
        console.print("[red]Error: Either --title or --doc-id must be specified[/red]")
        raise typer.Exit(code=1)

    async def _show():
        async with TestRunner() as runner:
            # First, list documents to find the one with matching title or ID
            documents = await runner.list_documents(service_id, executable_only=False)

            # Find document by title or ID
            doc = _find_document(documents, title, doc_id)

            # Get full document details (with file_content if --script flag)
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
            console.print("  BASE_URL=<gateway_url>")
            console.print("  API_KEY=<your_customer_api_key>")
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
    service_id: str = typer.Argument(
        ..., help="Service ID (supports partial IDs, minimum 8 chars)"
    ),
    title: str = typer.Option(
        None, "--title", "-t", help="Only run test with this title (runs all if not specified)"
    ),
    doc_id: str = typer.Option(
        None, "--doc-id", "-d", help="Only run test with this document ID (supports partial)"
    ),
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

    Fetches scripts from the backend and executes locally. Test scripts should use
    BASE_URL (or GATEWAY_BASE_URL) and API_KEY environment variables for gateway access.
    Set these in your environment before running tests:

        export BASE_URL=https://gateway.unitysvc.com
        export API_KEY=svcpass_your_customer_api_key

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

    async def _run_single(runner: TestRunner, doc: dict) -> dict:
        """Run a single test and return result."""
        document_id = doc["id"]
        doc_title = doc.get("title", "")

        # Check status from list response (avoids fetching document if skipped)
        meta = doc.get("meta") or {}
        test_meta = meta.get("test") or {}

        if not force:
            status = test_meta.get("status")
            if status == "success":
                return {"title": doc_title, "status": "skipped", "reason": "already passed"}
            if status == "skip":
                return {"title": doc_title, "status": "skipped", "reason": "marked as skip"}

        # Fetch document with file content and execution environment
        full_doc = await runner.get_document(document_id, file_content=True)

        file_content = full_doc.get("file_content")
        if not file_content:
            return {"title": doc_title, "status": "skipped", "reason": "no file content"}

        mime_type = full_doc.get("mime_type", "")
        full_meta = full_doc.get("meta") or {}
        # output_contains is defined at meta level by sellers, not under meta.test
        output_contains = full_meta.get("output_contains")

        # Use environment variables from user's shell (empty dict = inherit current env)
        exec_env: dict[str, str] = {}

        try:
            result = execute_script_content(
                script=file_content,
                mime_type=mime_type,
                env_vars=exec_env,
                timeout=timeout,
                output_contains=output_contains,
            )

            exit_code = result.get("exit_code", -1)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            status = result.get("status", "task_failed")
            error = result.get("error")

        except Exception as e:
            exit_code = -1
            stdout = ""
            stderr = str(e)
            status = "task_failed"
            error = str(e)

        # Update test metadata on backend
        try:
            await runner.update_test_result(
                document_id=document_id,
                status=status,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                error=error,
            )
        except Exception as update_error:
            console.print(f"  [yellow]Warning: Failed to update test result: {update_error}[/yellow]")

        return {
            "title": doc_title,
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
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

            results = []
            for doc in documents:
                doc_title = doc.get("title", doc.get("id", ""))
                console.print(f"[cyan]Running: {doc_title}...[/cyan]")

                result = await _run_single(runner, doc)
                results.append(result)

                # Display result
                if result["status"] == "success":
                    console.print("  [green]PASS[/green]")
                elif result["status"] == "skipped":
                    console.print(f"  [yellow]SKIP[/yellow] ({result.get('reason', '')})")
                else:
                    console.print(f"  [red]FAIL[/red] ({result['status']})")
                    if result.get("error"):
                        console.print(f"  [red]Error: {result['error']}[/red]")

                # Show verbose output
                if verbose and result["status"] not in ("skipped", "success"):
                    if result.get("stdout"):
                        console.print(f"  [dim]stdout: {result['stdout'][:500]}[/dim]")
                    if result.get("stderr"):
                        console.print(f"  [dim]stderr: {result['stderr'][:500]}[/dim]")

                # Fail fast
                if fail_fast and result["status"] not in ("success", "skipped"):
                    console.print("[red]Stopping on first failure (--fail-fast)[/red]")
                    break

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
    service_id: str = typer.Argument(
        ..., help="Service ID (supports partial IDs, minimum 8 chars)"
    ),
    title: str = typer.Option(
        None, "--title", "-t", help="Document title to skip"
    ),
    doc_id: str = typer.Option(
        None, "--doc-id", "-d", help="Document ID (supports partial IDs)"
    ),
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
    service_id: str = typer.Argument(
        ..., help="Service ID (supports partial IDs, minimum 8 chars)"
    ),
    title: str = typer.Option(
        None, "--title", "-t", help="Document title to unskip"
    ),
    doc_id: str = typer.Option(
        None, "--doc-id", "-d", help="Document ID (supports partial IDs)"
    ),
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
