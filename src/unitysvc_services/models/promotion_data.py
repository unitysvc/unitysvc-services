"""Promotion (pricing rule) data model for seller-managed promotions.

A PromotionData represents a seller-defined pricing adjustment that can be
applied to their services. Promotions are identified by name (unique per seller)
and support both code-based (customer redemption) and blanket (all customers)
distribution modes.
"""

from typing import Any

from .base import PriceRuleApplyAtEnum, PriceRuleStatusEnum, validate_pricing


class PromotionData:
    """Base data for a seller promotion (pricing rule).

    This is the logical data model — not a Pydantic BaseModel itself,
    but a namespace for the typed dict structure used in promotion files.
    The actual validation is done by PromotionV1.
    """


class PromotionV1:
    """File schema for promotion data (promotion_v1).

    This uses a plain dict approach like the rest of the codebase —
    validation is done via validate_promotion().
    """


# Derive allowed values from enums
APPLY_AT_VALUES = {e.value for e in PriceRuleApplyAtEnum}
STATUS_VALUES = {e.value for e in PriceRuleStatusEnum}


def validate_promotion(data: dict[str, Any]) -> list[str]:
    """Validate a promotion data dict.

    Args:
        data: Promotion data dict (from JSON/TOML file)

    Returns:
        List of validation error strings (empty = valid)
    """
    errors: list[str] = []

    # Required fields
    if "name" not in data:
        errors.append("Missing required field: name")
    elif not isinstance(data["name"], str):
        errors.append("name must be a string")
    elif len(data["name"]) > 100:
        errors.append("name must be at most 100 characters")

    if "pricing" not in data:
        errors.append("Missing required field: pricing")
    elif isinstance(data["pricing"], dict):
        # Validate pricing structure using existing validator
        try:
            validate_pricing(data["pricing"])
        except Exception as e:
            errors.append(f"Invalid pricing: {e}")

    # Optional fields with type checks
    if "description" in data and data["description"] is not None:
        if not isinstance(data["description"], str):
            errors.append("description must be a string")
        elif len(data["description"]) > 500:
            errors.append("description must be at most 500 characters")

    if "code" in data and data["code"] is not None:
        if not isinstance(data["code"], str):
            errors.append("code must be a string")
        elif len(data["code"]) > 50:
            errors.append("code must be at most 50 characters")

    if "apply_at" in data:
        if data["apply_at"] not in APPLY_AT_VALUES:
            errors.append(
                f"apply_at must be one of {APPLY_AT_VALUES}, "
                f"got '{data['apply_at']}'"
            )

    if "status" in data:
        if data["status"] not in STATUS_VALUES:
            errors.append(
                f"status must be one of {STATUS_VALUES}, "
                f"got '{data['status']}'"
            )

    if "priority" in data:
        if not isinstance(data["priority"], int):
            errors.append("priority must be an integer")

    if "applies_to_all_services" in data:
        if not isinstance(data["applies_to_all_services"], bool):
            errors.append("applies_to_all_services must be a boolean")

    if "requires_redemption" in data:
        if not isinstance(data["requires_redemption"], bool):
            errors.append("requires_redemption must be a boolean")

    if "service_names" in data and data["service_names"] is not None:
        if not isinstance(data["service_names"], list):
            errors.append("service_names must be a list of strings")
        elif not all(isinstance(s, str) for s in data["service_names"]):
            errors.append("service_names must be a list of strings")

    if "max_uses" in data and data["max_uses"] is not None:
        if not isinstance(data["max_uses"], int) or data["max_uses"] < 1:
            errors.append("max_uses must be a positive integer")

    return errors


PROMOTION_SCHEMA_VERSION = "promotion_v1"


def is_promotion_file(data: dict[str, Any]) -> bool:
    """Check if a data dict is a promotion file (by schema version)."""
    return data.get("schema") == PROMOTION_SCHEMA_VERSION


def strip_schema_field(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the data dict without the 'schema' field.

    The backend accepts the promotion file format directly, so we only
    need to strip the file-level schema field before POSTing.
    """
    return {k: v for k, v in data.items() if k != "schema"}
