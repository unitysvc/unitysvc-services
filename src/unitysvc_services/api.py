"""Base API client for UnitySVC with automatic curl fallback.

This module provides the base class for all UnitySVC API clients with
automatic network fallback from httpx to curl for systems with network
restrictions (e.g., macOS with conda Python).
"""

import asyncio
import json
import os
from typing import Any
from urllib.parse import urlencode

import httpx


class UnitySvcAPI:
    """Base class for UnitySVC API clients with automatic curl fallback.

    Provides async HTTP GET/POST methods that try httpx first for performance,
    then automatically fall back to curl if network restrictions are detected
    (e.g., macOS with conda Python).

    This base class can be used by:
    - ServiceDataQuery (query/read operations)
    - ServiceDataPublisher (publish/write operations)
    - AdminQuery (administrative operations)
    """

    def __init__(self) -> None:
        """Initialize API client from environment variables.

        Raises:
            ValueError: If required environment variables are not set
        """
        self.base_url = os.environ.get("UNITYSVC_BASE_URL")
        if not self.base_url:
            raise ValueError("UNITYSVC_BASE_URL environment variable not set")

        self.api_key = os.environ.get("UNITYSVC_API_KEY")
        if not self.api_key:
            raise ValueError("UNITYSVC_API_KEY environment variable not set")

        self.base_url = self.base_url.rstrip("/")
        self.use_curl_fallback = False
        self.client = httpx.AsyncClient(
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def _make_request_curl(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make HTTP GET request using curl fallback (async).

        Args:
            endpoint: API endpoint path (e.g., "/publish/sellers")
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: If HTTP status code indicates error (with response details)
            RuntimeError: If curl command fails or times out
        """
        url = f"{self.base_url}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"

        cmd = [
            "curl",
            "-s",  # Silent mode
            "-w",
            "\n%{http_code}",  # Write status code on new line
            "-H",
            f"X-API-Key: {self.api_key}",
            "-H",
            "Accept: application/json",
            url,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Curl command failed"
                raise RuntimeError(f"Curl error: {error_msg}")

            # Parse response: last line is status code, rest is body
            output = stdout.decode().strip()
            lines = output.split("\n")
            status_code = int(lines[-1])
            body = "\n".join(lines[:-1])

            # Parse JSON response
            try:
                response_data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                response_data = {"error": body}

            # Raise exception for non-2xx status codes (mimics httpx behavior)
            if status_code < 200 or status_code >= 300:
                # Create a mock response object to raise HTTPStatusError
                mock_request = httpx.Request("GET", url)
                mock_response = httpx.Response(status_code=status_code, content=body.encode(), request=mock_request)
                raise httpx.HTTPStatusError(f"HTTP {status_code}", request=mock_request, response=mock_response)

            return response_data
        except TimeoutError:
            raise RuntimeError("Request timed out after 30 seconds")
        except httpx.HTTPStatusError:
            # Re-raise HTTP errors as-is
            raise

    async def _make_post_request_curl(
        self, endpoint: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make HTTP POST request using curl fallback (async).

        Args:
            endpoint: API endpoint path (e.g., "/admin/subscriptions")
            json_data: JSON body data
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: If HTTP status code indicates error (with response details)
            RuntimeError: If curl command fails or times out
        """
        url = f"{self.base_url}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"

        cmd = [
            "curl",
            "-s",  # Silent mode
            "-w",
            "\n%{http_code}",  # Write status code on new line
            "-X",
            "POST",
            "-H",
            f"X-API-Key: {self.api_key}",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: application/json",
        ]

        if json_data:
            cmd.extend(["-d", json.dumps(json_data)])

        cmd.append(url)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Curl command failed"
                raise RuntimeError(f"Curl error: {error_msg}")

            # Parse response: last line is status code, rest is body
            output = stdout.decode().strip()
            lines = output.split("\n")
            status_code = int(lines[-1])
            body = "\n".join(lines[:-1])

            # Parse JSON response
            try:
                response_data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                response_data = {"error": body}

            # Raise exception for non-2xx status codes (mimics httpx behavior)
            if status_code < 200 or status_code >= 300:
                # Create a mock response object to raise HTTPStatusError
                mock_request = httpx.Request("POST", url)
                mock_response = httpx.Response(status_code=status_code, content=body.encode(), request=mock_request)
                raise httpx.HTTPStatusError(f"HTTP {status_code}", request=mock_request, response=mock_response)

            return response_data
        except TimeoutError:
            raise RuntimeError("Request timed out after 30 seconds")
        except httpx.HTTPStatusError:
            # Re-raise HTTP errors as-is
            raise

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the backend API with automatic curl fallback.

        Public async utility method for making GET requests. Tries httpx first for performance,
        automatically falls back to curl if network restrictions are detected (e.g., macOS
        with conda Python).

        Args:
            endpoint: API endpoint path (e.g., "/publish/sellers", "/admin/documents")
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            RuntimeError: If both httpx and curl fail
        """
        # If we already know curl is needed, use it directly
        if self.use_curl_fallback:
            return await self._make_request_curl(endpoint, params)

        # Try httpx first
        try:
            response = await self.client.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, OSError):
            # Connection failed - likely network restrictions
            # Fall back to curl and remember this for future requests
            self.use_curl_fallback = True
            return await self._make_request_curl(endpoint, params)

    async def post(
        self, endpoint: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a POST request to the backend API with automatic curl fallback.

        Public async utility method for making POST requests. Tries httpx first for performance,
        automatically falls back to curl if network restrictions are detected (e.g., macOS
        with conda Python).

        Args:
            endpoint: API endpoint path (e.g., "/admin/subscriptions")
            json_data: JSON body data
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            RuntimeError: If both httpx and curl fail
        """
        # If we already know curl is needed, use it directly
        if self.use_curl_fallback:
            return await self._make_post_request_curl(endpoint, json_data, params)

        # Try httpx first
        try:
            response = await self.client.post(f"{self.base_url}{endpoint}", json=json_data, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, OSError):
            # Connection failed - likely network restrictions
            # Fall back to curl and remember this for future requests
            self.use_curl_fallback = True
            return await self._make_post_request_curl(endpoint, json_data, params)

    async def check_task(self, task_id: str, poll_interval: float = 2.0, timeout: float = 300.0) -> dict[str, Any]:
        """Check and wait for task completion (async version).

        Utility function to poll a Celery task until it completes or times out.
        Uses the async HTTP client with curl fallback.

        Args:
            task_id: Celery task ID to poll
            poll_interval: Seconds between status checks (default: 2.0)
            timeout: Maximum seconds to wait (default: 300.0)

        Returns:
            Task result dictionary

        Raises:
            ValueError: If task fails or times out
        """
        import time

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise ValueError(f"Task {task_id} timed out after {timeout}s")

            # Check task status using get() with automatic curl fallback
            # Use UnitySvcAPI.get to ensure we call the async version, not sync wrapper
            try:
                status = await UnitySvcAPI.get(self, f"/tasks/{task_id}")
            except Exception:
                # Network error while checking status - retry
                await asyncio.sleep(poll_interval)
                continue

            state = status.get("state", "PENDING")

            # Check if task is complete
            if status.get("status") == "completed" or state == "SUCCESS":
                return status.get("result", {})
            elif status.get("status") == "failed" or state == "FAILURE":
                error = status.get("error", "Unknown error")
                raise ValueError(f"Task {task_id} failed: {error}")

            # Still processing - wait and retry
            await asyncio.sleep(poll_interval)

    async def aclose(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.aclose()
