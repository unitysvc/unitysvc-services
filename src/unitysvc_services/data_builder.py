"""Data builder classes for creating service data files.

This module provides builder classes that simplify creating offering.json,
listing.json, and provider.toml files with:
- Fluent API with chainable setter methods
- Convenience methods for common operations (add_document, add_code_example, etc.)
- Smart write() that skips writing if only time_created differs
- Automatic timestamp management

Example usage:
    from unitysvc_services.data_builder import OfferingDataBuilder, ListingDataBuilder

    # Create an offering
    offering = (
        OfferingDataBuilder("gpt-4")
        .set_display_name("GPT-4 Turbo")
        .set_description("OpenAI's most capable model")
        .set_service_type("llm")
        .set_status("ready")
        .set_details({"max_tokens": 128000, "context_length": 128000})
        .set_token_pricing(input_price="10.00", output_price="30.00")
        .add_upstream_interface(
            "OpenAI API",
            base_url="https://api.openai.com/v1",
        )
        .build()
    )

    # Write to file (skips if only time_created differs)
    offering.write(Path("services/gpt-4/offering.json"))

    # Create a listing
    listing = (
        ListingDataBuilder()
        .set_status("ready")
        .set_token_pricing(input_price="15.00", output_price="45.00")
        .add_code_example(
            title="Python Example",
            file_path="../../docs/example.py",
            description="Basic usage example",
        )
        .add_document(
            title="Getting Started",
            file_path="../../docs/getting_started.md",
            category="getting_started",
        )
        .build()
    )

    listing.write(Path("services/gpt-4/listing.json"))
"""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import json5


class BaseDataBuilder:
    """Base class for data builders with common functionality."""

    def __init__(self, schema: str):
        """Initialize with schema version.

        Args:
            schema: Schema identifier (e.g., "offering_v1", "listing_v1")
        """
        self._data: dict[str, Any] = {
            "schema": schema,
            "time_created": self._current_timestamp(),
        }

    def _current_timestamp(self) -> str:
        """Generate current UTC timestamp in ISO format."""
        now = datetime.now(UTC)
        return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _data_differs_beyond_timestamps(self, existing_data: dict[str, Any], new_data: dict[str, Any]) -> bool:
        """Check if data differs beyond just timestamp fields.

        Args:
            existing_data: Data from existing file
            new_data: New data to compare

        Returns:
            True if there are differences beyond timestamps
        """
        existing_copy = copy.deepcopy(existing_data)
        new_copy = copy.deepcopy(new_data)

        # Remove timestamp fields that we want to ignore
        timestamp_fields = ["time_created", "time_updated"]
        for field in timestamp_fields:
            existing_copy.pop(field, None)
            new_copy.pop(field, None)

        return existing_copy != new_copy

    def set_raw(self, key: str, value: Any) -> Self:
        """Set a raw key-value pair in the data.

        Args:
            key: Field name
            value: Field value

        Returns:
            Self for chaining
        """
        self._data[key] = value
        return self

    def get_data(self) -> dict[str, Any]:
        """Get the current data dictionary.

        Returns:
            Copy of the current data
        """
        return copy.deepcopy(self._data)

    def build(self) -> "BaseDataBuilder":
        """Finalize and return the builder.

        Returns:
            Self for chaining to write()
        """
        return self

    def write(
        self,
        file_path: Path,
        *,
        force: bool = False,
        preserve_time_created: bool = True,
    ) -> bool:
        """Write data to a JSON file.

        Skips writing if the file exists and only time_created differs,
        unless force=True.

        Args:
            file_path: Path to write to
            force: If True, always write even if only timestamps differ
            preserve_time_created: If True, preserve existing time_created

        Returns:
            True if file was written, False if skipped
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data_to_write = copy.deepcopy(self._data)

        # Check existing file
        if file_path.exists() and not force:
            try:
                with open(file_path, encoding="utf-8") as f:
                    existing_data = json5.load(f)

                # Preserve original time_created if requested
                if preserve_time_created and "time_created" in existing_data:
                    data_to_write["time_created"] = existing_data["time_created"]

                # Skip if only timestamps differ
                if not self._data_differs_beyond_timestamps(existing_data, data_to_write):
                    return False

            except (json.JSONDecodeError, OSError):
                # File exists but can't be read - proceed with write
                pass

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_write, f, indent=2, sort_keys=True)
            f.write("\n")

        return True


class OfferingDataBuilder(BaseDataBuilder):
    """Builder for creating offering.json files.

    Example:
        offering = (
            OfferingDataBuilder("gpt-4")
            .set_display_name("GPT-4 Turbo")
            .set_description("OpenAI's most capable model")
            .set_service_type("llm")
            .set_token_pricing(input_price="10.00", output_price="30.00")
            .build()
        )
        offering.write(Path("services/gpt-4/offering.json"))
    """

    def __init__(self, name: str):
        """Initialize offering builder.

        Args:
            name: Service name (required, e.g., "gpt-4", "claude-3-opus")
        """
        super().__init__("offering_v1")
        self._data["name"] = name
        self._data["status"] = "draft"
        self._data["currency"] = "USD"
        self._data["details"] = {}
        self._data["upstream_access_interfaces"] = {}

    def set_currency(self, currency: str) -> Self:
        """Set currency for payout_price.

        Args:
            currency: Currency code (e.g., "USD", "EUR")

        Returns:
            Self for chaining
        """
        self._data["currency"] = currency
        return self

    def set_name(self, name: str) -> Self:
        """Set service name.

        Args:
            name: Technical service name (e.g., "gpt-4")

        Returns:
            Self for chaining
        """
        self._data["name"] = name
        return self

    def set_display_name(self, display_name: str) -> Self:
        """Set human-readable display name.

        Args:
            display_name: Display name (e.g., "GPT-4 Turbo")

        Returns:
            Self for chaining
        """
        self._data["display_name"] = display_name
        return self

    def set_description(self, description: str) -> Self:
        """Set service description.

        Args:
            description: Service description

        Returns:
            Self for chaining
        """
        self._data["description"] = description
        return self

    def set_tagline(self, tagline: str) -> Self:
        """Set short tagline/elevator pitch.

        Args:
            tagline: Short description

        Returns:
            Self for chaining
        """
        self._data["tagline"] = tagline
        return self

    def set_service_type(self, service_type: str) -> Self:
        """Set service type.

        Args:
            service_type: One of: llm, embedding, image_generation,
                         vision_language_model, speech_to_text, etc.

        Returns:
            Self for chaining
        """
        self._data["service_type"] = service_type
        return self

    def set_status(self, status: str) -> Self:
        """Set offering status.

        Args:
            status: One of: draft, ready, deprecated

        Returns:
            Self for chaining
        """
        self._data["status"] = status
        return self

    def set_details(self, details: dict[str, Any]) -> Self:
        """Set technical details dictionary.

        Args:
            details: Dictionary of technical specifications

        Returns:
            Self for chaining
        """
        self._data["details"] = details
        return self

    def add_detail(self, key: str, value: Any) -> Self:
        """Add a single detail field.

        Args:
            key: Detail field name
            value: Detail value

        Returns:
            Self for chaining
        """
        if "details" not in self._data:
            self._data["details"] = {}
        self._data["details"][key] = value
        return self

    def set_tags(self, tags: list[str]) -> Self:
        """Set service tags.

        Args:
            tags: List of tags (e.g., ["byop"])

        Returns:
            Self for chaining
        """
        self._data["tags"] = tags
        return self

    def add_tag(self, tag: str) -> Self:
        """Add a single tag.

        Args:
            tag: Tag to add (e.g., "byop")

        Returns:
            Self for chaining
        """
        if "tags" not in self._data:
            self._data["tags"] = []
        if tag not in self._data["tags"]:
            self._data["tags"].append(tag)
        return self

    def set_token_pricing(
        self,
        input_price: str | None = None,
        output_price: str | None = None,
        cached_input_price: str | None = None,
        unified_price: str | None = None,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set token-based pricing (per 1M tokens).

        Args:
            input_price: Price per 1M input tokens (e.g., "10.00")
            output_price: Price per 1M output tokens (e.g., "30.00")
            cached_input_price: Price per 1M cached input tokens (e.g., "5.00")
            unified_price: Single price for both input/output (alternative)
            description: Pricing description
            reference: URL to upstream pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {"type": "one_million_tokens"}

        if unified_price is not None:
            pricing["price"] = unified_price
        else:
            if input_price is not None:
                pricing["input"] = input_price
            if cached_input_price is not None:
                pricing["cached_input"] = cached_input_price
            if output_price is not None:
                pricing["output"] = output_price

        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["payout_price"] = pricing
        return self

    def set_time_pricing(
        self,
        price_per_second: str,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set time-based pricing (per second).

        Args:
            price_per_second: Price per second (e.g., "0.006")
            description: Pricing description
            reference: URL to upstream pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {
            "type": "one_second",
            "price": price_per_second,
        }
        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["payout_price"] = pricing
        return self

    def set_image_pricing(
        self,
        price_per_image: str,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set per-image pricing.

        Args:
            price_per_image: Price per image (e.g., "0.04")
            description: Pricing description
            reference: URL to upstream pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {
            "type": "image",
            "price": price_per_image,
        }
        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["payout_price"] = pricing
        return self

    def set_payout_price(self, pricing: dict[str, Any]) -> Self:
        """Set raw payout pricing structure.

        Args:
            pricing: Full pricing dict with type and price fields

        Returns:
            Self for chaining
        """
        self._data["payout_price"] = pricing
        return self

    def add_upstream_interface(
        self,
        name: str,
        base_url: str,
        *,
        api_key: str | None = None,
        access_method: str = "http",
        description: str | None = None,
        rate_limits: list[dict[str, Any]] | None = None,
    ) -> Self:
        """Add an upstream access interface.

        Args:
            name: Interface name (e.g., "OpenAI API")
            base_url: Base URL for the API
            api_key: API key (use ${VAR} for env variables)
            access_method: Access method (http, websocket, grpc)
            description: Interface description
            rate_limits: List of rate limit configurations

        Returns:
            Self for chaining
        """
        if "upstream_access_interfaces" not in self._data:
            self._data["upstream_access_interfaces"] = {}

        interface: dict[str, Any] = {
            "access_method": access_method,
            "base_url": base_url,
        }
        if api_key is not None:
            interface["api_key"] = api_key
        if description:
            interface["description"] = description
        if rate_limits:
            interface["rate_limits"] = rate_limits
        else:
            interface["rate_limits"] = []

        self._data["upstream_access_interfaces"][name] = interface
        return self

    def add_document(
        self,
        title: str,
        file_path: str | None = None,
        external_url: str | None = None,
        *,
        category: str = "other",
        mime_type: str = "markdown",
        description: str | None = None,
        reference: str | None = None,
        is_public: bool = True,
    ) -> Self:
        """Add a document to the offering.

        Args:
            title: Document title (becomes the key)
            file_path: Path to local file (relative to offering file)
            external_url: External URL (mutually exclusive with file_path)
            category: Document category
            mime_type: MIME type
            description: Document description
            reference: Reference URL for the document source
            is_public: Whether document is publicly accessible

        Returns:
            Self for chaining
        """
        if "documents" not in self._data or self._data["documents"] is None:
            self._data["documents"] = {}

        doc: dict[str, Any] = {
            "category": category,
            "mime_type": mime_type,
            "is_public": is_public,
        }
        if file_path:
            doc["file_path"] = file_path
        if external_url:
            doc["external_url"] = external_url
        if description:
            doc["description"] = description
        if reference:
            doc["reference"] = reference

        self._data["documents"][title] = doc
        return self


class ListingDataBuilder(BaseDataBuilder):
    """Builder for creating listing.json files.

    Example:
        listing = (
            ListingDataBuilder()
            .set_status("ready")
            .set_token_pricing(input_price="15.00", output_price="45.00")
            .add_code_example("Python Example", "../../docs/example.py")
            .build()
        )
        listing.write(Path("services/gpt-4/listing.json"))
    """

    def __init__(self, name: str | None = None):
        """Initialize listing builder.

        Args:
            name: Optional listing name (defaults to offering name)
        """
        super().__init__("listing_v1")
        self._data["status"] = "draft"
        self._data["currency"] = "USD"
        if name:
            self._data["name"] = name

    def set_currency(self, currency: str) -> Self:
        """Set currency for list_price.

        Args:
            currency: Currency code (e.g., "USD", "EUR")

        Returns:
            Self for chaining
        """
        self._data["currency"] = currency
        return self

    def set_name(self, name: str) -> Self:
        """Set listing name.

        Args:
            name: Listing name

        Returns:
            Self for chaining
        """
        self._data["name"] = name
        return self

    def set_display_name(self, display_name: str) -> Self:
        """Set human-readable display name.

        Args:
            display_name: Display name

        Returns:
            Self for chaining
        """
        self._data["display_name"] = display_name
        return self

    def set_status(self, status: str) -> Self:
        """Set listing status.

        Args:
            status: One of: draft, ready, deprecated

        Returns:
            Self for chaining
        """
        self._data["status"] = status
        return self

    def set_token_pricing(
        self,
        input_price: str | None = None,
        output_price: str | None = None,
        cached_input_price: str | None = None,
        unified_price: str | None = None,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set token-based list pricing (per 1M tokens).

        Args:
            input_price: Price per 1M input tokens (e.g., "15.00")
            output_price: Price per 1M output tokens (e.g., "45.00")
            cached_input_price: Price per 1M cached input tokens (e.g., "7.50")
            unified_price: Single price for both input/output (alternative)
            description: Pricing description
            reference: URL to pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {"type": "one_million_tokens"}

        if unified_price is not None:
            pricing["price"] = unified_price
        else:
            if input_price is not None:
                pricing["input"] = input_price
            if cached_input_price is not None:
                pricing["cached_input"] = cached_input_price
            if output_price is not None:
                pricing["output"] = output_price

        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["list_price"] = pricing
        return self

    def set_time_pricing(
        self,
        price_per_second: str,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set time-based list pricing (per second).

        Args:
            price_per_second: Price per second
            description: Pricing description
            reference: URL to pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {
            "type": "one_second",
            "price": price_per_second,
        }
        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["list_price"] = pricing
        return self

    def set_image_pricing(
        self,
        price_per_image: str,
        description: str | None = None,
        reference: str | None = None,
    ) -> Self:
        """Set per-image list pricing.

        Args:
            price_per_image: Price per image
            description: Pricing description
            reference: URL to pricing page

        Returns:
            Self for chaining
        """
        pricing: dict[str, Any] = {
            "type": "image",
            "price": price_per_image,
        }
        if description:
            pricing["description"] = description
        if reference:
            pricing["reference"] = reference

        self._data["list_price"] = pricing
        return self

    def set_list_price(self, pricing: dict[str, Any]) -> Self:
        """Set raw list pricing structure.

        Args:
            pricing: Full pricing dict with type and price fields

        Returns:
            Self for chaining
        """
        self._data["list_price"] = pricing
        return self

    def add_user_interface(
        self,
        name: str,
        base_url: str,
        *,
        access_method: str = "http",
        description: str | None = None,
    ) -> Self:
        """Add a user access interface.

        Args:
            name: Interface name (e.g., "Provider API")
            base_url: Base URL (use ${GATEWAY_BASE_URL} for gateway)
            access_method: Access method (http, websocket, grpc)
            description: Interface description

        Returns:
            Self for chaining
        """
        if "user_access_interfaces" not in self._data or self._data["user_access_interfaces"] is None:
            self._data["user_access_interfaces"] = {}

        interface: dict[str, Any] = {
            "access_method": access_method,
            "base_url": base_url,
        }
        if description:
            interface["description"] = description

        self._data["user_access_interfaces"][name] = interface
        return self

    def add_document(
        self,
        title: str,
        file_path: str | None = None,
        external_url: str | None = None,
        *,
        category: str = "other",
        mime_type: str = "markdown",
        description: str | None = None,
        reference: str | None = None,
        is_public: bool = True,
        is_active: bool = True,
    ) -> Self:
        """Add a document to the listing.

        Args:
            title: Document title (becomes the key)
            file_path: Path to local file (relative to listing file)
            external_url: External URL (mutually exclusive with file_path)
            category: Document category (getting_started, api_reference, etc.)
            mime_type: MIME type (markdown, python, javascript, bash, etc.)
            description: Document description
            reference: Reference URL for the document source
            is_public: Whether document is publicly accessible
            is_active: Whether document is active

        Returns:
            Self for chaining
        """
        if "documents" not in self._data or self._data["documents"] is None:
            self._data["documents"] = {}

        doc: dict[str, Any] = {
            "category": category,
            "mime_type": mime_type,
            "is_public": is_public,
            "is_active": is_active,
        }
        if file_path:
            doc["file_path"] = file_path
        if external_url:
            doc["external_url"] = external_url
        if description:
            doc["description"] = description
        if reference:
            doc["reference"] = reference

        self._data["documents"][title] = doc
        return self

    def add_code_example(
        self,
        title: str,
        file_path: str,
        *,
        mime_type: str = "python",
        description: str | None = None,
        is_public: bool = True,
    ) -> Self:
        """Add a code example document.

        Convenience method for adding code examples with category="code_example".

        Args:
            title: Example title (e.g., "Python Example")
            file_path: Path to code file (relative to listing file)
            mime_type: Code type (python, javascript, bash)
            description: Example description
            is_public: Whether example is publicly accessible

        Returns:
            Self for chaining
        """
        return self.add_document(
            title=title,
            file_path=file_path,
            category="code_example",
            mime_type=mime_type,
            description=description,
            is_public=is_public,
        )

    def add_getting_started(
        self,
        title: str,
        file_path: str,
        *,
        description: str | None = None,
        is_public: bool = True,
    ) -> Self:
        """Add a getting started guide.

        Convenience method for adding documentation with category="getting_started".

        Args:
            title: Document title (e.g., "Getting Started Guide")
            file_path: Path to markdown file
            description: Document description
            is_public: Whether document is publicly accessible

        Returns:
            Self for chaining
        """
        return self.add_document(
            title=title,
            file_path=file_path,
            category="getting_started",
            mime_type="markdown",
            description=description,
            is_public=is_public,
        )

    def set_user_parameters_schema(
        self,
        schema: dict[str, Any],
        ui_schema: dict[str, Any] | None = None,
    ) -> Self:
        """Set JSON Schema for user parameters.

        Args:
            schema: JSON Schema for user input
            ui_schema: Optional UI schema for form rendering

        Returns:
            Self for chaining
        """
        self._data["user_parameters_schema"] = schema
        if ui_schema:
            self._data["user_parameters_ui_schema"] = ui_schema
        return self

    def set_byop_parameters(
        self,
        api_key_name: str = "API Key",
        api_key_env_var: str | None = None,
        api_key_placeholder: str | None = None,
        default_api_key: str | None = None,
    ) -> Self:
        """Set up BYOP (Bring Your Own Provider) user parameters.

        Convenience method for common BYOP configuration.

        Args:
            api_key_name: Display name for the API key field
            api_key_env_var: Environment variable name hint (e.g., "OPENAI_API_KEY")
            api_key_placeholder: Placeholder text in the input field
            default_api_key: Default API key value

        Returns:
            Self for chaining
        """
        schema: dict[str, Any] = {
            "title": "Be Your Own Provider",
            "description": "Access service with your own API key",
            "type": "object",
            "required": ["apikey"],
            "properties": {
                "apikey": {
                    "type": "string",
                    "title": api_key_name,
                    "default": "",
                }
            },
        }

        ui_schema: dict[str, Any] = {
            "apikey": {
                "ui:autofocus": True,
                "ui:emptyValue": "",
                "ui:autocomplete": "off",
                "ui:enableMarkdownInDescription": False,
            }
        }

        if api_key_placeholder:
            ui_schema["apikey"]["ui:placeholder"] = api_key_placeholder

        if api_key_env_var:
            ui_schema["apikey"]["ui:description"] = f"API Key known as {api_key_env_var}"

        self._data["user_parameters_schema"] = schema
        self._data["user_parameters_ui_schema"] = ui_schema

        if default_api_key:
            self._data["service_options"] = {"ops_testing_parameters": {"apikey": default_api_key}}

        return self

    def set_service_options(self, options: dict[str, Any]) -> Self:
        """Set service-specific options.

        Args:
            options: Service options dictionary

        Returns:
            Self for chaining
        """
        self._data["service_options"] = options
        return self


class ProviderDataBuilder(BaseDataBuilder):
    """Builder for creating provider.toml files.

    Example:
        provider = (
            ProviderDataBuilder("openai")
            .set_display_name("OpenAI")
            .set_description("OpenAI API services")
            .set_website("https://openai.com")
            .set_status("ready")
            .build()
        )
        provider.write(Path("provider.toml"))
    """

    def __init__(self, name: str):
        """Initialize provider builder.

        Args:
            name: Provider name (required, e.g., "openai")
        """
        super().__init__("provider_v1")
        self._data["name"] = name
        self._data["status"] = "draft"

    def set_name(self, name: str) -> Self:
        """Set provider name.

        Args:
            name: Provider name

        Returns:
            Self for chaining
        """
        self._data["name"] = name
        return self

    def set_display_name(self, display_name: str) -> Self:
        """Set human-readable display name.

        Args:
            display_name: Display name

        Returns:
            Self for chaining
        """
        self._data["display_name"] = display_name
        return self

    def set_description(self, description: str) -> Self:
        """Set provider description.

        Args:
            description: Provider description

        Returns:
            Self for chaining
        """
        self._data["description"] = description
        return self

    def set_website(self, website: str) -> Self:
        """Set provider website URL.

        Args:
            website: Website URL

        Returns:
            Self for chaining
        """
        self._data["website"] = website
        return self

    def set_status(self, status: str) -> Self:
        """Set provider status.

        Args:
            status: One of: draft, ready, deprecated

        Returns:
            Self for chaining
        """
        self._data["status"] = status
        return self

    def set_logo(self, logo_path: str) -> Self:
        """Set logo path.

        Args:
            logo_path: Path to logo file or URL

        Returns:
            Self for chaining
        """
        self._data["logo"] = logo_path
        return self

    def set_terms_of_service(self, tos_path: str) -> Self:
        """Set terms of service path.

        Args:
            tos_path: Path to ToS file or URL

        Returns:
            Self for chaining
        """
        self._data["terms_of_service"] = tos_path
        return self

    def set_services_populator(
        self,
        command: str | list[str],
        *,
        requirements: list[str] | None = None,
        envs: dict[str, str] | None = None,
    ) -> Self:
        """Configure services populator for auto-updating service data.

        Args:
            command: Command to run (string or list of arguments)
            requirements: Python packages to install
            envs: Environment variables to set

        Returns:
            Self for chaining
        """
        populator: dict[str, Any] = {"command": command}
        if requirements:
            populator["requirements"] = requirements
        if envs:
            populator["envs"] = envs

        self._data["services_populator"] = populator
        return self

    def write(
        self,
        file_path: Path,
        *,
        force: bool = False,
        preserve_time_created: bool = True,
    ) -> bool:
        """Write data to a TOML or JSON file.

        Args:
            file_path: Path to write to (.toml or .json)
            force: If True, always write even if only timestamps differ
            preserve_time_created: If True, preserve existing time_created

        Returns:
            True if file was written, False if skipped
        """
        file_path = Path(file_path)

        if file_path.suffix == ".toml":
            return self._write_toml(file_path, force=force, preserve_time_created=preserve_time_created)
        else:
            return super().write(file_path, force=force, preserve_time_created=preserve_time_created)

    def _write_toml(
        self,
        file_path: Path,
        *,
        force: bool = False,
        preserve_time_created: bool = True,
    ) -> bool:
        """Write data to a TOML file."""
        import tomllib

        import tomli_w

        file_path.parent.mkdir(parents=True, exist_ok=True)

        data_to_write = copy.deepcopy(self._data)

        # Check existing file
        if file_path.exists() and not force:
            try:
                with open(file_path, "rb") as f:
                    existing_data = tomllib.load(f)

                # Preserve original time_created if requested
                if preserve_time_created and "time_created" in existing_data:
                    data_to_write["time_created"] = existing_data["time_created"]

                # Skip if only timestamps differ
                if not self._data_differs_beyond_timestamps(existing_data, data_to_write):
                    return False

            except (tomllib.TOMLDecodeError, OSError):
                # File exists but can't be read - proceed with write
                pass

        with open(file_path, "wb") as f:
            tomli_w.dump(data_to_write, f)

        return True
