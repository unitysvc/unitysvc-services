"""Promotion (pricing rule) data model for seller-managed promotions.

A PromotionData represents a seller-defined pricing adjustment. Promotions
are identified by name (unique per seller) and use a ``scope`` field to
control which customers and services the adjustment applies to.

File schema: ``promotion_v1``

Fields
------
name : str (required)
    Unique identifier per seller. Used for idempotent upsert — uploading
    a promotion with the same name updates the existing one.

description : str | null
    Human-readable description shown in the UI and CLI.

scope : dict | null
    Controls **who** (customers) and **where** (services) the promotion
    applies.  When omitted or null the promotion is a blanket discount
    that applies to all customers on all of the seller's services.

    Customer targeting (``scope.customers``):

    * ``"*"`` or omitted — all customers (blanket).
    * ``{"code": "SUMMER25"}`` — only customers who redeem this code.
    * ``{"code": "{{ promotion_code(6) }}"}`` — backend auto-generates a
      6-character code via the ActionCode system (same as enrollment
      codes).  The generated code is written back to the stored scope
      on first upload and preserved on subsequent upserts.
    * ``{"subscription": "premium"}`` — customers on a specific plan
      tier.
    * ``["id1", "id2", ...]`` — specific customers.  The backend
      auto-assigns the code to their accounts (server-side redemption,
      no customer action needed).

    Service targeting (``scope.services``):

    * ``"*"`` or omitted — all of this seller's services.
    * ``["gpt-4", "gpt-4-enterprise"]`` — specific services by name
      (``listing.name ?? offering.name``).

pricing : dict (required)
    Pricing adjustment using the shared ``Pricing`` union type (e.g.
    ``multiply``, ``constant``, ``add``).

apply_at : "request" | "statement"  (default "request")
    When the rule is evaluated — per API call or during billing.

priority : int  (default 0)
    Higher-priority rules are applied first when multiple rules match.

status : str  (default "draft")
    Lifecycle status: ``draft``, ``active``, ``paused``, etc.

expires_at : datetime | null
    When the promotion expires (code-based promotions only).

max_uses : int | null
    Maximum total redemptions (code-based promotions only).
"""

from __future__ import annotations

import re
from typing import Any

from .base import PriceRuleApplyAtEnum, PriceRuleStatusEnum, validate_pricing

# Derive allowed values from enums
APPLY_AT_VALUES = {e.value for e in PriceRuleApplyAtEnum}
STATUS_VALUES = {e.value for e in PriceRuleStatusEnum}

PROMOTION_SCHEMA_VERSION = "promotion_v1"

# Pattern for {{ promotion_code(N) }} template
_PROMOTION_CODE_PATTERN = re.compile(
    r"^\{\{\s*promotion_code\(\s*(\d+)\s*\)\s*\}\}$"
)


def is_promotion_file(data: dict[str, Any]) -> bool:
    """Check if a data dict is a promotion file (by schema version)."""
    return data.get("schema") == PROMOTION_SCHEMA_VERSION


def strip_schema_field(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the data dict without the ``schema`` field.

    The backend accepts the promotion file format directly, so we only
    need to strip the file-level schema field before POSTing.
    """
    return {k: v for k, v in data.items() if k != "schema"}


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------

def _validate_scope_customers(customers: Any, errors: list[str]) -> None:
    """Validate ``scope.customers``."""
    if customers == "*":
        return
    if isinstance(customers, list):
        if not all(isinstance(c, str) for c in customers):
            errors.append("scope.customers list must contain strings")
        return
    if isinstance(customers, dict):
        allowed_keys = {"code", "subscription"}
        unknown = set(customers.keys()) - allowed_keys
        if unknown:
            errors.append(
                f"scope.customers has unknown keys: {unknown}"
            )
        if "code" in customers:
            code = customers["code"]
            if not isinstance(code, str):
                errors.append("scope.customers.code must be a string")
            elif len(code) > 50 and not _PROMOTION_CODE_PATTERN.match(code):
                errors.append(
                    "scope.customers.code must be <= 50 chars "
                    "or a {{ promotion_code(N) }} template"
                )
        if "subscription" in customers:
            if not isinstance(customers["subscription"], str):
                errors.append(
                    "scope.customers.subscription must be a string"
                )
        return
    errors.append(
        'scope.customers must be "*", a list of IDs, '
        'or a dict with "code" / "subscription"'
    )


def _validate_scope_services(services: Any, errors: list[str]) -> None:
    """Validate ``scope.services``."""
    if services == "*":
        return
    if isinstance(services, list):
        if not all(isinstance(s, str) for s in services):
            errors.append("scope.services list must contain strings")
        return
    errors.append('scope.services must be "*" or a list of service names')


def _validate_scope(scope: Any, errors: list[str]) -> None:
    """Validate the top-level ``scope`` field."""
    if scope is None:
        return
    if not isinstance(scope, dict):
        errors.append("scope must be a dict or null")
        return
    allowed_keys = {"customers", "services"}
    unknown = set(scope.keys()) - allowed_keys
    if unknown:
        errors.append(f"scope has unknown keys: {unknown}")
    if "customers" in scope:
        _validate_scope_customers(scope["customers"], errors)
    if "services" in scope:
        _validate_scope_services(scope["services"], errors)


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

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
        try:
            validate_pricing(data["pricing"])
        except Exception as e:
            errors.append(f"Invalid pricing: {e}")

    # Scope
    if "scope" in data:
        _validate_scope(data.get("scope"), errors)

    # Optional scalar fields
    if "description" in data and data["description"] is not None:
        if not isinstance(data["description"], str):
            errors.append("description must be a string")
        elif len(data["description"]) > 500:
            errors.append("description must be at most 500 characters")

    if "apply_at" in data:
        if data["apply_at"] not in APPLY_AT_VALUES:
            errors.append(
                f"apply_at must be one of {sorted(APPLY_AT_VALUES)}, "
                f"got '{data['apply_at']}'"
            )

    if "status" in data:
        if data["status"] not in STATUS_VALUES:
            errors.append(
                f"status must be one of {sorted(STATUS_VALUES)}, "
                f"got '{data['status']}'"
            )

    if "priority" in data:
        if not isinstance(data["priority"], int):
            errors.append("priority must be an integer")

    if "max_uses" in data and data["max_uses"] is not None:
        if not isinstance(data["max_uses"], int) or data["max_uses"] < 1:
            errors.append("max_uses must be a positive integer")

    return errors


# ---------------------------------------------------------------------------
# Scope display helpers (for CLI)
# ---------------------------------------------------------------------------

def describe_scope(scope: dict[str, Any] | None) -> str:
    """Return a human-readable one-line description of the scope."""
    if scope is None:
        return "all customers, all services"

    parts: list[str] = []

    customers = scope.get("customers")
    if customers is None or customers == "*":
        parts.append("all customers")
    elif isinstance(customers, dict):
        if "code" in customers:
            code = customers["code"]
            if _PROMOTION_CODE_PATTERN.match(code):
                parts.append("code: (auto-generated)")
            else:
                parts.append(f"code: {code}")
        if "subscription" in customers:
            parts.append(f"subscription: {customers['subscription']}")
    elif isinstance(customers, list):
        parts.append(f"{len(customers)} customer(s)")

    services = scope.get("services")
    if services is None or services == "*":
        parts.append("all services")
    elif isinstance(services, list):
        if len(services) <= 3:
            parts.append(f"services: {', '.join(services)}")
        else:
            parts.append(f"{len(services)} service(s)")

    return "; ".join(parts)
