"""Interactive prompt system for creating data files.

This module provides a systematic way to prompt users for field values
using a field registry approach, making it easy to add/remove/modify fields.
"""

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

console = Console()


# =============================================================================
# HELPER FUNCTIONS FOR AUTO-DISCOVERY
# =============================================================================


def find_seller_name(data_dir: Path | None = None) -> str | None:
    """Find seller name from seller.json or seller.toml in data directory.

    Args:
        data_dir: Directory to search for seller file (defaults to search common locations)

    Returns:
        Seller name if found, None otherwise
    """
    # Search in multiple common locations
    search_dirs = []

    if data_dir is not None:
        search_dirs.append(data_dir)
    else:
        # Common locations to search
        cwd = Path.cwd()
        search_dirs.extend(
            [
                cwd / "data",  # ./data (most common)
                cwd,  # current directory
                cwd.parent / "data",  # ../data (if we're in a subdirectory)
                cwd.parent,  # parent directory
            ]
        )

    # Look for seller file in each search directory
    for search_dir in search_dirs:
        for filename in ["seller.json", "seller.toml"]:
            seller_file = search_dir / filename
            if seller_file.exists():
                try:
                    if filename.endswith(".json"):
                        with open(seller_file) as f:
                            data = json.load(f)
                    else:  # .toml
                        with open(seller_file, "rb") as f:
                            data = tomllib.load(f)

                    seller_name = data.get("name")
                    if seller_name:
                        return seller_name
                except Exception:
                    continue

    return None


def prompt_for_pricing() -> dict[str, Any]:
    """Interactively prompt for pricing information (for seller_price).

    Returns:
        Dictionary with pricing data
    """
    console.print("\n[bold cyan]Adding pricing information[/bold cyan]")

    # Required field: pricing type (now inside price_data)
    # Note: revenue_share is only valid for seller_price, which is the only context
    # where this function is called
    pricing_type = Prompt.ask(
        "[bold blue]Pricing type[/bold blue] [red]*[/red]",
        choices=["one_million_tokens", "one_second", "image", "step", "revenue_share"],
        default="one_million_tokens",
    )

    # Optional fields
    description = Prompt.ask("[bold blue]Description[/bold blue] [dim](optional)[/dim]", default="")
    currency = Prompt.ask("[bold blue]Currency code[/bold blue] [dim](optional, e.g., 'USD')[/dim]", default="USD")
    reference = Prompt.ask(
        "[bold blue]Reference URL[/bold blue] [dim](optional, link to upstream pricing page)[/dim]", default=""
    )

    # Build price_data based on pricing type
    price_data: dict[str, Any]

    if pricing_type == "revenue_share":
        # Revenue share pricing - just needs a percentage
        console.print("\n[dim]Revenue share: seller receives a percentage of customer charge[/dim]")
        percentage = Prompt.ask(
            "[bold blue]Percentage[/bold blue] [dim](0-100, e.g., '70' for 70%)[/dim]",
            default="70",
        )
        price_data = {"type": pricing_type, "percentage": percentage}
    else:
        # Other pricing types - ask for price structure
        console.print("\n[dim]Price data structure options:[/dim]")
        console.print('[dim]  1. Simple: {"type": "...", "price": "10.00"}[/dim]')
        console.print('[dim]  2. Input/Output (LLMs): {"type": "...", "input": "5.00", "output": "15.00"}[/dim]')
        console.print('[dim]  3. Custom: any JSON with "type" field included[/dim]')

        structure = Prompt.ask(
            "\n[bold blue]Price data structure[/bold blue]",
            choices=["simple", "input_output", "custom"],
            default="simple",
        )

        if structure == "simple":
            amount = Prompt.ask(
                "[bold blue]Price amount[/bold blue] [dim](e.g., '0.50')[/dim]",
                default="0",
            )
            price_data = {"type": pricing_type, "price": amount}

        elif structure == "input_output":
            input_amount = Prompt.ask(
                "[bold blue]Input price amount[/bold blue] [dim](e.g., '0.50')[/dim]",
                default="0",
            )
            output_amount = Prompt.ask(
                "[bold blue]Output price amount[/bold blue] [dim](e.g., '1.50')[/dim]",
                default="0",
            )
            price_data = {"type": pricing_type, "input": input_amount, "output": output_amount}

        else:  # custom
            console.print(
                f'\n[dim]Enter additional price_data fields as JSON (type "{pricing_type}" will be added)[/dim]'
            )
            console.print('[dim]Example: {"price": "0.05"}[/dim]')
            while True:
                json_input = Prompt.ask("[bold blue]Additional price data JSON[/bold blue]", default="{}")
                try:
                    custom_data = json.loads(json_input)
                    if not isinstance(custom_data, dict):
                        console.print("[red]Error: Price data must be a JSON object (dict)[/red]")
                        continue
                    price_data = {"type": pricing_type, **custom_data}
                    break
                except json.JSONDecodeError as e:
                    console.print(f"[red]Invalid JSON: {e}[/red]")
                    console.print("[dim]Try again or press Ctrl+C to cancel[/dim]")

    # Build pricing dict
    pricing: dict[str, Any] = {
        "price_data": price_data,
    }

    if description:
        pricing["description"] = description
    if currency:
        pricing["currency"] = currency
    if reference:
        pricing["reference"] = reference

    return pricing


def prompt_for_document(listing_dir: Path) -> dict[str, Any]:
    """Interactively prompt for a single document.

    Args:
        listing_dir: Directory where the listing file will be created (for validating file paths)

    Returns:
        Dictionary with document data
    """
    console.print("\n[bold cyan]Adding a document[/bold cyan]")

    # Required fields
    title = Prompt.ask("[bold blue]Document title[/bold blue] [red]*[/red]")

    mime_type = Prompt.ask(
        "[bold blue]MIME type[/bold blue] [red]*[/red]",
        choices=["markdown", "python", "javascript", "bash", "html", "text", "pdf", "jpeg", "png", "svg", "url"],
        default="markdown",
    )

    category = Prompt.ask(
        "[bold blue]Document category[/bold blue] [red]*[/red]",
        choices=[
            "getting_started",
            "api_reference",
            "tutorial",
            "code_example",
            "use_case",
            "troubleshooting",
            "changelog",
            "best_practice",
            "specification",
            "service_level_agreement",
            "terms_of_service",
            "logo",
            "other",
        ],
        default="getting_started",
    )

    # Optional fields
    description = Prompt.ask("[bold blue]Description[/bold blue] [dim](optional)[/dim]", default="")

    # At least one of file_path or external_url must be specified
    file_path = ""
    external_url = ""

    while not file_path and not external_url:
        console.print("[dim]At least one of file path or external URL must be specified[/dim]")

        file_path = Prompt.ask(
            "[bold blue]File path[/bold blue] [dim](relative to listing dir, e.g., 'docs/guide.md')[/dim]",
            default="",
        )

        # If file_path is provided, validate it exists
        if file_path:
            file_full_path = listing_dir / file_path
            if not file_full_path.exists():
                console.print(f"[yellow]Warning: File not found at {file_full_path}[/yellow]")
                if not Confirm.ask("[bold blue]Use this path anyway?[/bold blue]", default=False):
                    file_path = ""
                    continue

        # If no file_path, must provide external_url
        if not file_path:
            external_url = Prompt.ask(
                "[bold blue]External URL[/bold blue] [dim](required if no file path)[/dim]",
                default="",
            )
            if not external_url:
                console.print("[red]Either file path or external URL must be provided[/red]")
                continue

    is_public = Confirm.ask("[bold blue]Is public?[/bold blue]", default=False)

    # Build document dict
    doc: dict[str, Any] = {
        "title": title,
        "mime_type": mime_type,
        "category": category,
    }

    if description:
        doc["description"] = description
    if file_path:
        doc["file_path"] = file_path
    if external_url:
        doc["external_url"] = external_url
    if is_public:
        doc["is_public"] = is_public

    return doc


def find_service_name(service_dir: Path | None = None) -> str | None:
    """Find service name from service.json or service.toml in service directory.

    Args:
        service_dir: Directory to search for service file (defaults to search common locations)

    Returns:
        Service name if found, None otherwise
    """
    # Search in multiple common locations
    search_dirs = []

    if service_dir is not None:
        search_dirs.append(service_dir)
    else:
        # Common locations to search
        cwd = Path.cwd()
        search_dirs.extend(
            [
                cwd,  # current directory (most common for services)
                cwd.parent,  # parent directory (if we're in a subdirectory)
            ]
        )

    # Look for service file in each search directory
    for search_dir in search_dirs:
        for filename in ["service.json", "service.toml"]:
            service_file = search_dir / filename
            if service_file.exists():
                try:
                    if filename.endswith(".json"):
                        with open(service_file) as f:
                            data = json.load(f)
                    else:  # .toml
                        with open(service_file, "rb") as f:
                            data = tomllib.load(f)

                    service_name = data.get("name")
                    if service_name:
                        return service_name
                except Exception:
                    continue

    return None


@dataclass
class FieldDef:
    """Definition for a single field to prompt.

    Attributes:
        name: Field name in the schema
        prompt_text: Text to display to the user
        field_type: Type of field (string, email, choice, boolean, integer)
        required: Whether the field is required
        default: Default value (can be callable that takes context)
        choices: List of choices for choice-type fields
        description: Help text for the field
        skip_if: Callable that returns True if field should be skipped
        validate: Optional validation function
        group: Logical grouping for related fields
    """

    name: str
    prompt_text: str
    field_type: str = "string"  # string, email, uri, choice, boolean, integer
    required: bool = False
    default: Any = None
    choices: list[str] | None = None
    description: str | None = None
    skip_if: Callable[[dict], bool] | None = None
    validate: Callable[[Any], Any] | None = None
    group: str = "general"


@dataclass
class FieldGroup:
    """Group of related fields."""

    name: str
    title: str
    fields: list[FieldDef] = field(default_factory=list)


class PromptEngine:
    """Engine for prompting users based on field definitions."""

    def __init__(self, groups: list[FieldGroup]):
        """Initialize prompt engine with field groups.

        Args:
            groups: List of field groups to prompt for
        """
        self.groups = groups

    def prompt_all(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Prompt for all fields in all groups.

        Args:
            context: Initial context/data (e.g., name provided via CLI arg)

        Returns:
            Dictionary with all prompted values
        """
        if context is None:
            context = {}

        data = {}

        for group in self.groups:
            if group.fields:
                console.print(f"\n[bold cyan]{group.title}[/bold cyan]")

                for field_def in group.fields:
                    # Skip if condition met
                    if field_def.skip_if and field_def.skip_if(context):
                        continue

                    # Skip if already in context (provided via CLI)
                    if field_def.name in context:
                        value = context[field_def.name]
                        console.print(f"[dim]{field_def.prompt_text}: {value} (from CLI)[/dim]")
                        data[field_def.name] = value
                        continue

                    # Get default value (can be callable)
                    default_value = field_def.default
                    if callable(default_value):
                        default_value = default_value(context, data)

                    # Prompt based on field type
                    value = self._prompt_field(field_def, default_value, data)

                    # Only add non-None values (unless required)
                    if value is not None or field_def.required:
                        data[field_def.name] = value

                    # Add to context for subsequent fields
                    context[field_def.name] = value

        return data

    def _prompt_field(self, field_def: FieldDef, default_value: Any, current_data: dict[str, Any]) -> Any:
        """Prompt for a single field.

        Args:
            field_def: Field definition
            default_value: Default value to suggest
            current_data: Currently collected data (for validation)

        Returns:
            User input value
        """
        # Indicate if field is optional
        required_marker = " [red]*[/red]" if field_def.required else " [dim](optional)[/dim]"
        prompt_label = f"[bold blue]{field_def.prompt_text}{required_marker}[/bold blue]"

        if field_def.description:
            console.print(f"[dim]{field_def.description}[/dim]")

        try:
            if field_def.field_type == "boolean":
                return Confirm.ask(prompt_label, default=default_value if default_value is not None else False)

            elif field_def.field_type == "integer":
                while True:
                    try:
                        if not field_def.required:
                            # Optional integer - allow empty input
                            default_str = str(default_value) if default_value is not None else ""
                            result = Prompt.ask(prompt_label, default=default_str)
                            if result == "":
                                return None
                            value = int(result)
                        elif default_value is not None:
                            value = IntPrompt.ask(prompt_label, default=default_value)
                        else:
                            value = IntPrompt.ask(prompt_label)

                        # Apply custom validation if provided
                        if field_def.validate:
                            value = field_def.validate(value)
                        return value
                    except ValueError:
                        console.print("[red]Please enter a valid integer[/red]")

            elif field_def.field_type == "choice":
                if not field_def.choices:
                    raise ValueError(f"Field {field_def.name} is type 'choice' but has no choices defined")

                return Prompt.ask(
                    prompt_label,
                    choices=field_def.choices,
                    default=default_value if default_value else field_def.choices[0],
                )

            else:  # string, email, uri
                while True:
                    if not field_def.required and default_value is None:
                        # Optional field with no default - allow empty
                        result = Prompt.ask(prompt_label, default="")
                        if result == "":
                            return None
                    elif default_value is not None:
                        result = Prompt.ask(prompt_label, default=str(default_value))
                    else:
                        result = Prompt.ask(prompt_label)

                    # Validate input
                    if self._validate_field_value(field_def, result):
                        # Apply custom validation if provided
                        if field_def.validate:
                            try:
                                result = field_def.validate(result)
                            except Exception as e:
                                console.print(f"[red]Validation error: {e}[/red]")
                                continue
                        return result
                    else:
                        # Validation failed, loop to retry
                        pass

        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled by user[/yellow]")
            raise typer.Abort()
        except Exception as e:
            console.print(f"[red]Error prompting for {field_def.name}: {e}[/red]")
            raise

    def _validate_field_value(self, field_def: FieldDef, value: Any) -> bool:
        """Validate field value based on field type.

        Args:
            field_def: Field definition
            value: Value to validate

        Returns:
            True if valid, False otherwise (with error message printed)
        """
        if value is None or value == "":
            if field_def.required:
                console.print("[red]This field is required[/red]")
                return False
            return True

        # Type-specific validation
        if field_def.field_type == "email":
            if "@" not in value or "." not in value.split("@")[-1]:
                console.print("[red]Please enter a valid email address[/red]")
                return False

        elif field_def.field_type == "uri":
            if not value.startswith(("http://", "https://")):
                console.print("[red]URL must start with http:// or https://[/red]")
                return False

        return True


# =============================================================================
# SELLER FIELD REGISTRY
# =============================================================================

SELLER_GROUPS = [
    FieldGroup(
        name="basic",
        title="Basic Information",
        fields=[
            FieldDef(
                name="name",
                prompt_text="Seller ID (URL-friendly)",
                field_type="string",
                required=True,
                description="Unique identifier (e.g., 'acme-corp', 'john-doe')",
            ),
            FieldDef(
                name="display_name",
                prompt_text="Display name",
                field_type="string",
                required=False,
                default=lambda ctx, data: ctx.get("name", "").replace("-", " ").replace("_", " ").title(),
                description="Human-readable name (e.g., 'ACME Corporation')",
            ),
            FieldDef(
                name="seller_type",
                prompt_text="Seller type",
                field_type="choice",
                choices=["individual", "organization", "partnership", "corporation"],
                default="individual",
                description="Type of seller entity",
            ),
        ],
    ),
    FieldGroup(
        name="contact",
        title="Contact Information",
        fields=[
            FieldDef(
                name="contact_email",
                prompt_text="Primary contact email",
                field_type="email",
                required=True,
            ),
            FieldDef(
                name="secondary_contact_email",
                prompt_text="Secondary contact email",
                field_type="email",
                required=False,
            ),
            FieldDef(
                name="homepage",
                prompt_text="Homepage URL",
                field_type="uri",
                required=False,
            ),
        ],
    ),
    FieldGroup(
        name="details",
        title="Additional Details",
        fields=[
            FieldDef(
                name="description",
                prompt_text="Description",
                field_type="string",
                required=False,
                default=lambda ctx, data: f"{ctx.get('name', 'seller')} - {data.get('seller_type', 'seller')}",
            ),
            FieldDef(
                name="account_manager",
                prompt_text="Account manager email",
                field_type="email",
                required=False,
                description="Email of the user managing this seller account (must be a registered user)",
            ),
            FieldDef(
                name="business_registration",
                prompt_text="Business registration number",
                field_type="string",
                required=False,
                skip_if=lambda ctx: ctx.get("seller_type") == "individual",
                description="Required for organizations",
            ),
            FieldDef(
                name="tax_id",
                prompt_text="Tax ID (EIN, VAT, etc.)",
                field_type="string",
                required=False,
                skip_if=lambda ctx: ctx.get("seller_type") == "individual",
            ),
        ],
    ),
    FieldGroup(
        name="status",
        title="Status & Verification",
        fields=[
            FieldDef(
                name="status",
                prompt_text="Status",
                field_type="choice",
                choices=["active", "pending", "disabled", "incomplete"],
                default="active",
            ),
            FieldDef(
                name="is_verified",
                prompt_text="Is verified (KYC complete)?",
                field_type="boolean",
                default=False,
            ),
        ],
    ),
]


# =============================================================================
# PROVIDER FIELD REGISTRY
# =============================================================================

PROVIDER_GROUPS = [
    FieldGroup(
        name="basic",
        title="Basic Information",
        fields=[
            FieldDef(
                name="name",
                prompt_text="Provider ID (URL-friendly)",
                field_type="string",
                required=True,
                description="Unique identifier (e.g., 'openai', 'fireworks')",
            ),
            FieldDef(
                name="display_name",
                prompt_text="Display name",
                field_type="string",
                required=False,
                default=lambda ctx, data: ctx.get("name", "").replace("-", " ").replace("_", " ").title(),
                description="Human-readable name (e.g., 'OpenAI', 'Fireworks.ai')",
            ),
            FieldDef(
                name="description",
                prompt_text="Description",
                field_type="string",
                required=False,
            ),
        ],
    ),
    FieldGroup(
        name="contact",
        title="Contact & Web",
        fields=[
            FieldDef(
                name="contact_email",
                prompt_text="Contact email",
                field_type="email",
                required=True,
            ),
            FieldDef(
                name="secondary_contact_email",
                prompt_text="Secondary contact email",
                field_type="email",
                required=False,
            ),
            FieldDef(
                name="homepage",
                prompt_text="Homepage URL",
                field_type="uri",
                required=True,
            ),
        ],
    ),
    FieldGroup(
        name="access",
        title="Provider Access (API Credentials)",
        fields=[
            FieldDef(
                name="base_url",
                prompt_text="API endpoint URL",
                field_type="uri",
                required=True,
                description="Base URL for API access (e.g., 'https://api.openai.com/v1')",
            ),
            FieldDef(
                name="api_key",
                prompt_text="API key (optional, can be set later)",
                field_type="string",
                required=False,
                description="Leave empty if you'll set it later or use env var",
            ),
            FieldDef(
                name="access_method",
                prompt_text="Access method",
                field_type="choice",
                choices=["http", "websocket", "grpc"],
                default="http",
            ),
        ],
    ),
    FieldGroup(
        name="status",
        title="Status",
        fields=[
            FieldDef(
                name="status",
                prompt_text="Provider status",
                field_type="choice",
                choices=["active", "pending", "disabled", "incomplete"],
                default="active",
            ),
        ],
    ),
    FieldGroup(
        name="automation",
        title="Service Population (Optional)",
        fields=[
            FieldDef(
                name="enable_services_populator",
                prompt_text="Enable automated service population?",
                field_type="boolean",
                required=False,
                default=False,
                description="Use a script to automatically populate service offerings and listings",
            ),
            FieldDef(
                name="populator_command",
                prompt_text="Populator script command",
                field_type="string",
                required=False,
                skip_if=lambda ctx: not ctx.get("enable_services_populator", False),
                description="Command to execute (e.g., 'python scripts/populate.py'). Run by 'usvc populate'",
            ),
        ],
    ),
]


# =============================================================================
# SERVICE OFFERING FIELD REGISTRY
# =============================================================================

OFFERING_GROUPS = [
    FieldGroup(
        name="basic",
        title="Basic Information",
        fields=[
            FieldDef(
                name="name",
                prompt_text="Service name (e.g., 'gpt-4', 'llama-3-1-405b')",
                field_type="string",
                required=True,
                description="Usually the model name or service identifier",
            ),
            FieldDef(
                name="display_name",
                prompt_text="Display name",
                field_type="string",
                required=True,
                default=lambda ctx, data: ctx.get("name", "").replace("-", " ").title(),
            ),
            FieldDef(
                name="version",
                prompt_text="Version",
                field_type="string",
                required=False,
                default=None,
            ),
            FieldDef(
                name="description",
                prompt_text="Description",
                field_type="string",
                required=True,
                description="Brief description of the service",
            ),
        ],
    ),
    FieldGroup(
        name="classification",
        title="Service Classification",
        fields=[
            FieldDef(
                name="service_type",
                prompt_text="Service type",
                field_type="choice",
                choices=["llm", "embedding", "vision", "audio", "image", "video", "other"],
                default="llm",
                required=True,
            ),
            FieldDef(
                name="upstream_status",
                prompt_text="Upstream status",
                field_type="choice",
                choices=["uploading", "ready", "deprecated"],
                default="ready",
            ),
        ],
    ),
    FieldGroup(
        name="access",
        title="Upstream Access Interface",
        fields=[
            FieldDef(
                name="upstream_base_url",
                prompt_text="Upstream API endpoint URL",
                field_type="uri",
                required=True,
                description="Base URL for accessing this service upstream",
            ),
            FieldDef(
                name="upstream_api_key",
                prompt_text="Upstream API key (optional)",
                field_type="string",
                required=False,
                description="Leave empty if using provider's API key",
            ),
            FieldDef(
                name="add_upstream_documents",
                prompt_text="Add documents to upstream access interface?",
                field_type="boolean",
                default=False,
                description="API docs, code examples, etc. for accessing the upstream service",
            ),
        ],
    ),
    FieldGroup(
        name="pricing",
        title="Seller Pricing (Optional)",
        fields=[
            FieldDef(
                name="add_seller_pricing",
                prompt_text="Add seller pricing information?",
                field_type="boolean",
                default=False,
                description="The agreed rate between seller and UnitySVC",
            ),
        ],
    ),
    FieldGroup(
        name="additional",
        title="Additional Information (Optional)",
        fields=[
            FieldDef(
                name="tagline",
                prompt_text="Tagline",
                field_type="string",
                required=False,
                description="Short elevator pitch for the service",
            ),
        ],
    ),
]


# =============================================================================
# SERVICE LISTING FIELD REGISTRY
# =============================================================================

LISTING_GROUPS = [
    FieldGroup(
        name="basic",
        title="Basic Information",
        fields=[
            FieldDef(
                name="service_name",
                prompt_text="Service name (must match service.json)",
                field_type="string",
                required=False,
                default=lambda ctx, data: find_service_name(),
                description="Auto-detected from service.json in current directory",
            ),
            FieldDef(
                name="name",
                prompt_text="Listing identifier",
                field_type="string",
                required=False,
                description="Name identifier for the service listing (defaults to filename)",
            ),
            FieldDef(
                name="display_name",
                prompt_text="Display name",
                field_type="string",
                required=False,
                description="Human-readable listing name (e.g., 'Premium GPT-4 Access')",
            ),
        ],
    ),
    FieldGroup(
        name="seller",
        title="Seller Information",
        fields=[
            FieldDef(
                name="seller_name",
                prompt_text="Seller name (must match seller.json)",
                field_type="string",
                required=False,
                default=lambda ctx, data: find_seller_name(),
                description="Auto-detected from seller.json in data directory",
            ),
        ],
    ),
    FieldGroup(
        name="status",
        title="Status",
        fields=[
            FieldDef(
                name="listing_status",
                prompt_text="Listing status",
                field_type="choice",
                choices=["draft", "ready", "deprecated"],
                default="draft",
            ),
        ],
    ),
    FieldGroup(
        name="documents",
        title="Documents (Optional)",
        fields=[
            FieldDef(
                name="add_documents",
                prompt_text="Add documents (SLA, guides, etc.)?",
                field_type="boolean",
                default=False,
                description="Documents provide additional information about the listing",
            ),
        ],
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_seller_data(user_input: dict[str, Any]) -> dict[str, Any]:
    """Create seller data structure from user input.

    Args:
        user_input: User-provided field values

    Returns:
        Complete seller data dictionary
    """
    data = {
        "schema": "seller_v1",
        "time_created": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    # Add all non-None user input
    for key, value in user_input.items():
        if value is not None:
            data[key] = value

    return data


def create_provider_data(user_input: dict[str, Any]) -> dict[str, Any]:
    """Create provider data structure from user input.

    Args:
        user_input: User-provided field values

    Returns:
        Complete provider data dictionary
    """
    # Extract access interface fields
    access_fields = ["base_url", "api_key", "access_method"]
    provider_access_info: dict[str, Any] = {}

    for key in access_fields:
        if key in user_input and user_input[key] is not None:
            provider_access_info[key] = user_input[key]

    # Extract services_populator fields
    populator_fields = ["enable_services_populator", "populator_command"]
    services_populator: dict[str, Any] | None = None

    if user_input.get("enable_services_populator") and user_input.get("populator_command"):
        services_populator = {"command": user_input["populator_command"]}

    # Create base data
    data = {
        "schema": "provider_v1",
        "time_created": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "provider_access_info": provider_access_info,
    }

    # Add services_populator if configured
    if services_populator:
        data["services_populator"] = services_populator

    # Add non-access, non-populator fields
    excluded_fields = access_fields + populator_fields
    for key, value in user_input.items():
        if key not in excluded_fields and value is not None:
            data[key] = value

    return data


def create_offering_data(user_input: dict[str, Any], offering_dir: Path | None = None) -> dict[str, Any]:
    """Create service offering data structure from user input.

    Args:
        user_input: User-provided field values
        offering_dir: Directory where offering file will be created (for validating document file paths)

    Returns:
        Complete service offering data dictionary
    """
    # Extract upstream access interface fields
    upstream_fields = ["upstream_base_url", "upstream_api_key", "add_upstream_documents"]
    upstream_access_interface: dict[str, Any] = {}

    for key in upstream_fields:
        # Map to the actual field names in AccessInterface
        if key == "upstream_base_url" and user_input.get(key):
            upstream_access_interface["base_url"] = user_input[key]
        elif key == "upstream_api_key" and user_input.get(key):
            upstream_access_interface["api_key"] = user_input[key]

    # Handle documents for upstream access interface if user wants to add them
    if user_input.get("add_upstream_documents"):
        if offering_dir is None:
            console.print("[yellow]Warning: Cannot validate file paths without offering directory[/yellow]")
            offering_dir = Path.cwd()

        console.print("\n[bold cyan]Add documents to upstream access interface[/bold cyan]")
        documents = []
        while True:
            doc = prompt_for_document(offering_dir)
            documents.append(doc)

            if not Confirm.ask("\n[bold blue]Add another document?[/bold blue]", default=False):
                break

        if documents:
            upstream_access_interface["documents"] = documents

    # Handle seller pricing if user wants to add it
    seller_price = None
    if user_input.get("add_seller_pricing"):
        seller_price = prompt_for_pricing()

    # Create base data
    data = {
        "schema": "service_v1",
        "time_created": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "upstream_access_interface": upstream_access_interface,
        "details": {},  # Required field, user can add details manually later
    }

    # Add seller price if provided
    if seller_price:
        data["seller_price"] = seller_price

    # Add non-upstream fields (exclude add_upstream_documents and add_seller_pricing which are just flags)
    excluded_fields = upstream_fields + ["add_seller_pricing"]
    for key, value in user_input.items():
        if key not in excluded_fields and value is not None:
            data[key] = value

    return data


def create_listing_data(user_input: dict[str, Any], listing_dir: Path | None = None) -> dict[str, Any]:
    """Create service listing data structure from user input.

    Args:
        user_input: User-provided field values
        listing_dir: Directory where listing file will be created (for validating document file paths)

    Returns:
        Complete service listing data dictionary
    """
    data: dict[str, Any] = {
        "schema": "listing_v1",
        "time_created": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "user_access_interfaces": [],  # Required field, user must add interfaces manually
        "customer_price": None,  # Optional, can be added later
    }

    # Handle documents if user wants to add them
    documents = []
    if user_input.get("add_documents"):
        if listing_dir is None:
            console.print("[yellow]Warning: Cannot validate file paths without listing directory[/yellow]")
            listing_dir = Path.cwd()

        console.print("\n[bold cyan]Add documents to listing[/bold cyan]")
        while True:
            doc = prompt_for_document(listing_dir)
            documents.append(doc)

            if not Confirm.ask("\n[bold blue]Add another document?[/bold blue]", default=False):
                break

    if documents:
        data["documents"] = documents

    # Add all non-None user input (except add_documents which is just a flag)
    for key, value in user_input.items():
        if key != "add_documents" and value is not None:
            data[key] = value

    return data
