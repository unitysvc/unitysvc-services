"""Tests for the service lifecycle module."""

import asyncio
import re
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from unitysvc_services.lifecycle import (
    ServiceLifecycleAPI,
    delete_service,
    deprecate_service,
    submit_service,
    withdraw_service,
)

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


# =============================================================================
# ServiceLifecycleAPI class tests
# =============================================================================


class TestServiceLifecycleAPI:
    """Tests for the ServiceLifecycleAPI class."""

    @pytest.fixture
    def api(self, monkeypatch):
        """Create a ServiceLifecycleAPI instance with mocked env vars."""
        monkeypatch.setenv("UNITYSVC_BASE_URL", "https://test.api.example.com")
        monkeypatch.setenv("UNITYSVC_API_KEY", "test-api-key")
        return ServiceLifecycleAPI()

    def test_delete_service_basic(self, api):
        """Test delete_service method with basic parameters."""
        with patch.object(api, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"deleted": True}

            result = asyncio.run(api.delete_service("test-service-id"))

            mock_delete.assert_called_once_with("/seller/services/test-service-id", params={})
            assert result == {"deleted": True}

    def test_delete_service_with_dryrun(self, api):
        """Test delete_service method with dryrun flag."""
        with patch.object(api, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"would_delete": True}

            result = asyncio.run(api.delete_service("test-id", dryrun=True))

            mock_delete.assert_called_once_with(
                "/seller/services/test-id", params={"dryrun": "true"}
            )
            assert result == {"would_delete": True}

    def test_delete_service_with_force(self, api):
        """Test delete_service method with force flag."""
        with patch.object(api, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"deleted": True, "forced": True}

            result = asyncio.run(api.delete_service("test-id", force=True))

            mock_delete.assert_called_once_with(
                "/seller/services/test-id", params={"force": "true"}
            )
            assert result == {"deleted": True, "forced": True}

    def test_delete_service_with_all_flags(self, api):
        """Test delete_service method with both dryrun and force flags."""
        with patch.object(api, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {}

            asyncio.run(api.delete_service("test-id", dryrun=True, force=True))

            mock_delete.assert_called_once_with(
                "/seller/services/test-id", params={"dryrun": "true", "force": "true"}
            )

    def test_update_service_status_deprecated(self, api):
        """Test update_service_status with deprecated status."""
        with patch.object(api, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = {"status": "deprecated"}

            result = asyncio.run(api.update_service_status("test-id", status="deprecated"))

            mock_patch.assert_called_once_with(
                "/seller/services/test-id", json_data={"status": "deprecated"}
            )
            assert result == {"status": "deprecated"}

    def test_update_service_status_pending(self, api):
        """Test update_service_status with pending status (submit)."""
        with patch.object(api, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = {"status": "pending"}

            result = asyncio.run(api.update_service_status("test-id", status="pending"))

            mock_patch.assert_called_once_with(
                "/seller/services/test-id", json_data={"status": "pending"}
            )
            assert result == {"status": "pending"}

    def test_update_service_status_draft(self, api):
        """Test update_service_status with draft status (withdraw)."""
        with patch.object(api, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = {"status": "draft"}

            result = asyncio.run(api.update_service_status("test-id", status="draft"))

            mock_patch.assert_called_once_with(
                "/seller/services/test-id", json_data={"status": "draft"}
            )
            assert result == {"status": "draft"}


# =============================================================================
# CLI command parameter acceptance tests
# =============================================================================


def create_test_app():
    """Create a Typer app for testing CLI commands."""
    import typer

    app = typer.Typer()
    app.command("deprecate")(deprecate_service)
    app.command("submit")(submit_service)
    app.command("withdraw")(withdraw_service)
    app.command("delete")(delete_service)
    return app


@pytest.fixture
def cli_app():
    """Create a test CLI app."""
    return create_test_app()


class TestDeprecateServiceCLI:
    """Tests for the deprecate_service CLI command."""

    def test_deprecate_requires_service_id(self, cli_app):
        """Test that deprecate command requires at least one service ID."""
        result = runner.invoke(cli_app, ["deprecate"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_deprecate_accepts_single_service_id(self, cli_app):
        """Test deprecate accepts a single service ID."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "deprecated"}, None)]
            result = runner.invoke(cli_app, ["deprecate", "test-service-id", "--yes"])
            assert result.exit_code == 0
            assert "Deprecating service" in result.output

    def test_deprecate_accepts_multiple_service_ids(self, cli_app):
        """Test deprecate accepts multiple service IDs."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("id1", {"status": "deprecated"}, None),
                ("id2", {"status": "deprecated"}, None),
            ]
            result = runner.invoke(cli_app, ["deprecate", "id1", "id2", "--yes"])
            assert result.exit_code == 0
            assert "Deprecating 2 services" in result.output

    def test_deprecate_yes_flag_short(self, cli_app):
        """Test deprecate accepts -y short flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "deprecated"}, None)]
            result = runner.invoke(cli_app, ["deprecate", "test-id", "-y"])
            assert result.exit_code == 0

    def test_deprecate_prompts_for_confirmation(self, cli_app):
        """Test deprecate prompts for confirmation without --yes."""
        result = runner.invoke(cli_app, ["deprecate", "test-id"], input="n\n")
        assert "Cancelled" in result.output


class TestSubmitServiceCLI:
    """Tests for the submit_service CLI command."""

    def test_submit_requires_service_id(self, cli_app):
        """Test that submit command requires at least one service ID."""
        result = runner.invoke(cli_app, ["submit"])
        assert result.exit_code != 0

    def test_submit_accepts_single_service_id(self, cli_app):
        """Test submit accepts a single service ID."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "pending"}, None)]
            result = runner.invoke(cli_app, ["submit", "test-service-id", "--yes"])
            assert result.exit_code == 0
            assert "Submitting" in result.output

    def test_submit_accepts_multiple_service_ids(self, cli_app):
        """Test submit accepts multiple service IDs."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("id1", {"status": "pending"}, None),
                ("id2", {"status": "pending"}, None),
            ]
            result = runner.invoke(cli_app, ["submit", "id1", "id2", "--yes"])
            assert result.exit_code == 0

    def test_submit_yes_flag_long(self, cli_app):
        """Test submit accepts --yes long flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "pending"}, None)]
            result = runner.invoke(cli_app, ["submit", "test-id", "--yes"])
            assert result.exit_code == 0

    def test_submit_prompts_for_confirmation(self, cli_app):
        """Test submit prompts for confirmation without --yes."""
        result = runner.invoke(cli_app, ["submit", "test-id"], input="n\n")
        assert "Cancelled" in result.output


class TestWithdrawServiceCLI:
    """Tests for the withdraw_service CLI command."""

    def test_withdraw_requires_service_id(self, cli_app):
        """Test that withdraw command requires at least one service ID."""
        result = runner.invoke(cli_app, ["withdraw"])
        assert result.exit_code != 0

    def test_withdraw_accepts_single_service_id(self, cli_app):
        """Test withdraw accepts a single service ID."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "draft"}, None)]
            result = runner.invoke(cli_app, ["withdraw", "test-service-id", "--yes"])
            assert result.exit_code == 0
            assert "Withdrawing" in result.output

    def test_withdraw_accepts_multiple_service_ids(self, cli_app):
        """Test withdraw accepts multiple service IDs."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("id1", {"status": "draft"}, None),
                ("id2", {"status": "draft"}, None),
            ]
            result = runner.invoke(cli_app, ["withdraw", "id1", "id2", "--yes"])
            assert result.exit_code == 0

    def test_withdraw_yes_flag_short(self, cli_app):
        """Test withdraw accepts -y short flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"status": "draft"}, None)]
            result = runner.invoke(cli_app, ["withdraw", "test-id", "-y"])
            assert result.exit_code == 0

    def test_withdraw_prompts_for_confirmation(self, cli_app):
        """Test withdraw prompts for confirmation without --yes."""
        result = runner.invoke(cli_app, ["withdraw", "test-id"], input="n\n")
        assert "Cancelled" in result.output


class TestDeleteServiceCLI:
    """Tests for the delete_service CLI command."""

    def test_delete_requires_service_id(self, cli_app):
        """Test that delete command requires at least one service ID."""
        result = runner.invoke(cli_app, ["delete"])
        assert result.exit_code != 0

    def test_delete_accepts_single_service_id(self, cli_app):
        """Test delete accepts a single service ID."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"deleted": True}, None)]
            result = runner.invoke(cli_app, ["delete", "test-service-id", "--yes"])
            assert result.exit_code == 0
            assert "Deleting service" in result.output

    def test_delete_accepts_multiple_service_ids(self, cli_app):
        """Test delete accepts multiple service IDs."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("id1", {"deleted": True}, None),
                ("id2", {"deleted": True}, None),
            ]
            result = runner.invoke(cli_app, ["delete", "id1", "id2", "--yes"])
            assert result.exit_code == 0
            assert "Deleting 2 services" in result.output

    def test_delete_dryrun_flag(self, cli_app):
        """Test delete accepts --dryrun flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"would_delete": True}, None)]
            result = runner.invoke(cli_app, ["delete", "test-id", "--dryrun"])
            assert result.exit_code == 0
            assert "Dry-run mode" in result.output

    def test_delete_force_flag(self, cli_app):
        """Test delete accepts --force flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"deleted": True}, None)]
            result = runner.invoke(cli_app, ["delete", "test-id", "--force", "--yes"])
            assert result.exit_code == 0

    def test_delete_yes_flag_short(self, cli_app):
        """Test delete accepts -y short flag."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"deleted": True}, None)]
            result = runner.invoke(cli_app, ["delete", "test-id", "-y"])
            assert result.exit_code == 0

    def test_delete_prompts_for_confirmation(self, cli_app):
        """Test delete prompts for confirmation without --yes (and not dryrun)."""
        result = runner.invoke(cli_app, ["delete", "test-id"], input="n\n")
        assert "Cancelled" in result.output

    def test_delete_no_prompt_in_dryrun(self, cli_app):
        """Test delete doesn't prompt for confirmation in dryrun mode."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", {"would_delete": True}, None)]
            # No input needed - dryrun should not prompt
            result = runner.invoke(cli_app, ["delete", "test-id", "--dryrun"])
            assert result.exit_code == 0


# =============================================================================
# Error handling tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in CLI commands."""

    def test_deprecate_shows_error_on_failure(self, cli_app):
        """Test deprecate shows error message when API call fails."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [("test-id", None, "API Error: Not found")]
            result = runner.invoke(cli_app, ["deprecate", "test-id", "--yes"])
            assert "API Error: Not found" in result.output
            assert "✗" in result.output

    def test_deprecate_mixed_success_and_failure(self, cli_app):
        """Test deprecate handles mixed success and failure results."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("id1", {"status": "deprecated"}, None),
                ("id2", None, "Not found"),
            ]
            result = runner.invoke(cli_app, ["deprecate", "id1", "id2", "--yes"])
            assert result.exit_code == 1  # Should fail due to error
            assert "Success:" in result.output
            assert "Failed:" in result.output

    def test_delete_shows_cascade_info(self, cli_app):
        """Test delete shows cascade deletion information."""
        with patch("unitysvc_services.lifecycle.asyncio.run") as mock_run:
            mock_run.return_value = [
                ("test-id", {"deleted": True, "cascade_deleted": {"subscriptions": 5}}, None)
            ]
            result = runner.invoke(cli_app, ["delete", "test-id", "--yes"])
            assert result.exit_code == 0
            assert "subscription" in result.output.lower()


# =============================================================================
# Integration tests with real Typer app from services module
# =============================================================================


class TestServicesIntegration:
    """Tests that lifecycle commands are properly integrated with services app."""

    def test_services_app_has_lifecycle_commands(self):
        """Test that services app includes lifecycle commands."""
        from unitysvc_services.services import app

        # Get registered command names
        command_names = [cmd.name for cmd in app.registered_commands]

        assert "deprecate" in command_names
        assert "submit" in command_names
        assert "withdraw" in command_names
        assert "delete" in command_names

    def test_services_deprecate_help(self):
        """Test deprecate command help text."""
        from unitysvc_services.services import app

        result = runner.invoke(app, ["deprecate", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "deprecated" in output.lower()
        assert "--yes" in output

    def test_services_submit_help(self):
        """Test submit command help text."""
        from unitysvc_services.services import app

        result = runner.invoke(app, ["submit", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "review" in output.lower() or "pending" in output.lower()
        assert "--yes" in output

    def test_services_withdraw_help(self):
        """Test withdraw command help text."""
        from unitysvc_services.services import app

        result = runner.invoke(app, ["withdraw", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "draft" in output.lower()
        assert "--yes" in output

    def test_services_delete_help(self):
        """Test delete command help text."""
        from unitysvc_services.services import app

        result = runner.invoke(app, ["delete", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "delete" in output.lower()
        assert "--dryrun" in output
        assert "--force" in output
        assert "--yes" in output
