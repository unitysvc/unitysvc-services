"""Model data fetching utilities for LLM service providers.

This module provides utilities for fetching model pricing, context window,
and evaluation data from external sources like LiteLLM, Hugging Face,
and OpenRouter. These are useful for any-llm providers that need to
enrich their service data with information from these sources.

Example usage:
    from unitysvc_services.model_data import ModelDataFetcher, ModelDataLookup

    fetcher = ModelDataFetcher()
    litellm_data = fetcher.fetch_litellm_model_data()
    hf_data = fetcher.fetch_huggingface_leaderboard_data()

    lookup = ModelDataLookup()
    details = lookup.lookup_model_details("gpt-4", litellm_data)
"""

import json
from typing import Any

import httpx


class ModelDataFetcher:
    """Handles fetching model data from external sources.

    This class provides methods to fetch model information from various
    public APIs and data sources:
    - LiteLLM: Model pricing and context window data
    - Hugging Face Leaderboard: Model evaluation benchmarks
    - OpenRouter: Model details, pricing, and context lengths
    - Hugging Face Model Hub: Individual model details

    All fetch methods use caching to avoid redundant network requests.
    """

    def __init__(self, user_agent: str = "unitysvc-services/1.0"):
        """Initialize the fetcher with an httpx client.

        Args:
            user_agent: User agent string for HTTP requests
        """
        self._client: httpx.Client | None = None
        self._user_agent = user_agent
        self._litellm_data: dict[str, Any] | None = None
        self._hf_leaderboard_data: dict[str, Any] | None = None
        self._openrouter_data: dict[str, Any] | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazily create and return the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                headers={"User-Agent": self._user_agent},
                timeout=30.0,
            )
        return self._client

    def fetch_litellm_model_data(self, quiet: bool = False) -> dict[str, Any]:
        """Fetch model pricing and context window data from LiteLLM.

        LiteLLM maintains a comprehensive JSON file with pricing and context
        window information for models from various providers.

        Args:
            quiet: If True, suppress progress messages

        Returns:
            Dictionary mapping model identifiers to their pricing/context data.
            Returns empty dict if fetch fails.

        Example:
            >>> fetcher = ModelDataFetcher()
            >>> data = fetcher.fetch_litellm_model_data()
            >>> data.get("gpt-4")
            {'input_cost_per_token': 0.00003, 'output_cost_per_token': 0.00006, ...}
        """
        if self._litellm_data is not None:
            return self._litellm_data

        url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

        try:
            if not quiet:
                print("Fetching LiteLLM model data...")
            response = self.client.get(url)
            response.raise_for_status()
            self._litellm_data = response.json()
            return self._litellm_data
        except httpx.HTTPError as e:
            if not quiet:
                print(f"Warning: Failed to fetch LiteLLM model data: {e}")
            self._litellm_data = {}
            return self._litellm_data
        except json.JSONDecodeError as e:
            if not quiet:
                print(f"Warning: Failed to parse LiteLLM model data: {e}")
            self._litellm_data = {}
            return self._litellm_data

    def fetch_huggingface_leaderboard_data(self, quiet: bool = False) -> dict[str, Any]:
        """Fetch model evaluation data from Hugging Face Open LLM Leaderboard.

        The leaderboard contains benchmark scores for various LLMs on tasks
        like ARC, HellaSwag, MMLU, TruthfulQA, WinoGrande, and GSM8K.

        Args:
            quiet: If True, suppress progress messages

        Returns:
            Dictionary mapping model names to their leaderboard data.
            Returns empty dict if fetch fails.

        Example:
            >>> fetcher = ModelDataFetcher()
            >>> data = fetcher.fetch_huggingface_leaderboard_data()
            >>> data.get("meta-llama/Llama-2-70b-chat-hf")
            {'average': 67.87, 'arc': 64.59, 'mmlu': 63.91, ...}
        """
        if self._hf_leaderboard_data is not None:
            return self._hf_leaderboard_data

        url = "https://huggingface.co/api/datasets/open-llm-leaderboard/results"

        try:
            if not quiet:
                print("Fetching Hugging Face leaderboard data...")
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Convert to a dict keyed by model name for easier lookup
            leaderboard_dict: dict[str, Any] = {}
            if "rows" in data:
                for row in data["rows"]:
                    if "row" in row and "fullname" in row["row"]:
                        model_name = row["row"]["fullname"]
                        leaderboard_dict[model_name] = row["row"]

            self._hf_leaderboard_data = leaderboard_dict
            return self._hf_leaderboard_data
        except httpx.HTTPError as e:
            if not quiet:
                print(f"Warning: Failed to fetch Hugging Face leaderboard data: {e}")
            self._hf_leaderboard_data = {}
            return self._hf_leaderboard_data
        except (json.JSONDecodeError, KeyError) as e:
            if not quiet:
                print(f"Warning: Failed to parse Hugging Face leaderboard data: {e}")
            self._hf_leaderboard_data = {}
            return self._hf_leaderboard_data

    def fetch_openrouter_models_data(self, quiet: bool = False) -> dict[str, Any]:
        """Fetch model data from OpenRouter API.

        OpenRouter provides information about available models including
        context lengths, pricing, and capabilities.

        Args:
            quiet: If True, suppress progress messages

        Returns:
            Dictionary mapping model IDs to their OpenRouter data.
            Returns empty dict if fetch fails.

        Example:
            >>> fetcher = ModelDataFetcher()
            >>> data = fetcher.fetch_openrouter_models_data()
            >>> data.get("anthropic/claude-3-opus")
            {'id': 'anthropic/claude-3-opus', 'context_length': 200000, ...}
        """
        if self._openrouter_data is not None:
            return self._openrouter_data

        url = "https://openrouter.ai/api/v1/models"

        try:
            if not quiet:
                print("Fetching OpenRouter model data...")
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Convert to a dict keyed by model ID for easier lookup
            models_dict: dict[str, Any] = {}
            if "data" in data:
                for model in data["data"]:
                    if "id" in model:
                        models_dict[model["id"]] = model

            self._openrouter_data = models_dict
            return self._openrouter_data
        except httpx.HTTPError as e:
            if not quiet:
                print(f"Warning: Failed to fetch OpenRouter model data: {e}")
            self._openrouter_data = {}
            return self._openrouter_data
        except (json.JSONDecodeError, KeyError) as e:
            if not quiet:
                print(f"Warning: Failed to parse OpenRouter model data: {e}")
            self._openrouter_data = {}
            return self._openrouter_data

    def fetch_huggingface_model_details(
        self, model_id: str, quiet: bool = False
    ) -> dict[str, Any] | None:
        """Fetch detailed model information from Hugging Face Model Hub API.

        Attempts to fetch model details using various ID format variations
        to handle different naming conventions.

        Args:
            model_id: Model identifier (e.g., "llama-2-70b", "meta-llama/Llama-2-70b")
            quiet: If True, suppress progress messages

        Returns:
            Model details dict if found, None otherwise.

        Example:
            >>> fetcher = ModelDataFetcher()
            >>> details = fetcher.fetch_huggingface_model_details("meta-llama/Llama-2-70b-chat-hf")
            >>> details.get("pipeline_tag")
            'text-generation'
        """
        # Try various model ID formats for HF
        model_variations = [
            model_id,
            model_id.replace(":", "/"),
            f"huggingface/{model_id}",
            f"microsoft/{model_id}",
            f"meta-llama/{model_id}",
            f"google/{model_id}",
            f"mistralai/{model_id}",
            f"anthropic/{model_id}",
        ]

        # Use shorter timeout for individual model lookups
        for model_name in model_variations:
            url = f"https://huggingface.co/api/models/{model_name}"
            try:
                response = self.client.get(url, timeout=15.0)
                if response.status_code == 200:
                    return response.json()
            except httpx.HTTPError:
                continue

        return None

    def clear_cache(self) -> None:
        """Clear all cached data to force fresh fetches."""
        self._litellm_data = None
        self._hf_leaderboard_data = None
        self._openrouter_data = None

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ModelDataFetcher":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


class ModelDataLookup:
    """Handles looking up model details from fetched data.

    This class provides static methods for fuzzy matching model IDs
    against the data fetched by ModelDataFetcher.
    """

    @staticmethod
    def lookup_model_details(
        model_id: str, litellm_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Look up additional model details from LiteLLM data.

        Performs fuzzy matching to find model data, trying:
        1. Exact match
        2. Match with provider prefix (e.g., "openai/gpt-4")
        3. Partial match (model_id in key or key in model_id)

        Args:
            model_id: Model identifier to look up
            litellm_data: Dictionary from fetch_litellm_model_data()

        Returns:
            Model details dict if found, None otherwise.
        """
        if not litellm_data:
            return None

        # Try exact match first
        if model_id in litellm_data:
            return litellm_data[model_id]

        # Try with provider prefix
        for key in litellm_data:
            if key.endswith(f"/{model_id}") or key.endswith(model_id):
                return litellm_data[key]

        # Try partial match
        for key in litellm_data:
            if model_id in key or key in model_id:
                return litellm_data[key]

        return None

    @staticmethod
    def lookup_hf_leaderboard_details(
        model_id: str, hf_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Look up model evaluation details from Hugging Face leaderboard data.

        Performs fuzzy matching with various transformations including
        case variations and underscore/hyphen substitutions.

        Args:
            model_id: Model identifier to look up
            hf_data: Dictionary from fetch_huggingface_leaderboard_data()

        Returns:
            Leaderboard details dict if found, None otherwise.
        """
        if not hf_data:
            return None

        # Try exact match first
        if model_id in hf_data:
            return hf_data[model_id]

        # Try different variations
        variations = [
            model_id.lower(),
            model_id.upper(),
            model_id.replace("-", "_"),
            model_id.replace("_", "-"),
        ]

        for variation in variations:
            if variation in hf_data:
                return hf_data[variation]

        # Try partial matching
        for key in hf_data:
            key_lower = key.lower()
            model_lower = model_id.lower()

            if model_lower in key_lower or key_lower in model_lower:
                return hf_data[key]

            # Try matching without common prefixes
            key_clean = (
                key_lower.replace("huggingface/", "")
                .replace("microsoft/", "")
                .replace("meta-llama/", "")
            )
            if model_lower in key_clean or key_clean in model_lower:
                return hf_data[key]

        return None

    @staticmethod
    def lookup_openrouter_details(
        model_id: str, openrouter_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Look up model details from OpenRouter data.

        Performs fuzzy matching with case-insensitive comparison
        and partial matching.

        Args:
            model_id: Model identifier to look up
            openrouter_data: Dictionary from fetch_openrouter_models_data()

        Returns:
            OpenRouter details dict if found, None otherwise.
        """
        if not openrouter_data:
            return None

        # Try exact match first
        if model_id in openrouter_data:
            return openrouter_data[model_id]

        # Try different variations and partial matching
        model_lower = model_id.lower()

        for key in openrouter_data:
            key_lower = key.lower()

            if (
                key_lower == model_lower
                or key_lower.endswith(f"/{model_lower}")
                or key_lower.endswith(model_lower)
                or model_lower in key_lower
                or key_lower in model_lower
            ):
                return openrouter_data[key]

        return None
