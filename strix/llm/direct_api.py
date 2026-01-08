"""Direct HTTP API client for CLIProxyAPI.

This module provides direct HTTP communication with CLIProxyAPI endpoints,
bypassing LiteLLM entirely for a lighter and more direct integration.

Usage:
    from strix.llm.direct_api import DirectAPIClient
    
    client = DirectAPIClient(
        endpoint="http://localhost:8317/v1",
        model="qwen3-coder-plus"
    )
    
    response = await client.chat_completion(messages=[
        {"role": "user", "content": "Hello!"}
    ])
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


logger = logging.getLogger(__name__)


@dataclass
class DirectAPIResponse:
    """Response from direct API call."""
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str
    raw_response: dict[str, Any]


class DirectAPIError(Exception):
    """Base exception for direct API errors."""
    def __init__(self, message: str, status_code: int | None = None, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class DirectAPIRateLimitError(DirectAPIError):
    """Rate limit exceeded."""
    pass


class DirectAPIAuthError(DirectAPIError):
    """Authentication failed."""
    pass


class DirectAPIConnectionError(DirectAPIError):
    """Connection failed."""
    pass


class DirectAPITimeoutError(DirectAPIError):
    """Request timed out."""
    pass


def _should_retry(exception: Exception) -> bool:
    """Determine if an exception should be retried."""
    if isinstance(exception, DirectAPIRateLimitError):
        return True
    if isinstance(exception, DirectAPIConnectionError):
        return True
    if isinstance(exception, DirectAPITimeoutError):
        return True
    if isinstance(exception, DirectAPIError):
        # Retry on 5xx errors
        if exception.status_code and exception.status_code >= 500:
            return True
    return False


class DirectAPIClient:
    """Direct HTTP client for CLIProxyAPI endpoints.
    
    This client communicates directly with OpenAI-compatible API endpoints
    without using LiteLLM, providing a lighter footprint and more direct control.
    """
    
    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 300,
        max_retries: int = 5,
    ):
        """Initialize the direct API client.
        
        Args:
            endpoint: API endpoint URL (e.g., "http://localhost:8317/v1")
            model: Model name to use
            api_key: API key (optional for CLIProxyAPI OAuth mode)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.endpoint = endpoint or self._get_endpoint()
        self.model = model or self._get_model()
        self.api_key = api_key or self._get_api_key()
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Remove trailing slash and /v1 suffix for base URL
        self.base_url = self.endpoint.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"
        
        # Statistics
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        
        logger.info(f"DirectAPIClient initialized: endpoint={self.base_url}, model={self.model}")
    
    def _get_endpoint(self) -> str:
        """Get API endpoint from environment or config."""
        endpoint = (
            os.getenv("CLIPROXY_ENDPOINT")
            or os.getenv("LLM_API_BASE")
            or os.getenv("OPENAI_API_BASE")
        )
        if not endpoint:
            raise DirectAPIError(
                "No API endpoint configured. Set CLIPROXY_ENDPOINT or LLM_API_BASE environment variable."
            )
        return endpoint
    
    def _get_model(self) -> str:
        """Get model name from environment or config."""
        return (
            os.getenv("CLIPROXY_MODEL")
            or os.getenv("STRIX_LLM")
            or "qwen3-coder-plus"
        )
    
    def _get_api_key(self) -> str:
        """Get API key from environment or use placeholder for OAuth mode."""
        return (
            os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "cliproxy-direct-mode"
        )
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _handle_response_error(self, response: requests.Response) -> None:
        """Handle HTTP response errors."""
        if response.status_code == 200:
            return
        
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text
        
        if response.status_code == 401:
            raise DirectAPIAuthError(
                f"Authentication failed: {error_message}",
                status_code=response.status_code,
                details=error_message
            )
        elif response.status_code == 429:
            raise DirectAPIRateLimitError(
                f"Rate limit exceeded: {error_message}",
                status_code=response.status_code,
                details=error_message
            )
        elif response.status_code >= 500:
            raise DirectAPIError(
                f"Server error: {error_message}",
                status_code=response.status_code,
                details=error_message
            )
        else:
            raise DirectAPIError(
                f"API error ({response.status_code}): {error_message}",
                status_code=response.status_code,
                details=error_message
            )
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=1, max=30),
        retry=retry_if_exception_type((
            DirectAPIRateLimitError,
            DirectAPIConnectionError,
            DirectAPITimeoutError,
        )),
        reraise=True,
    )
    def _make_request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/chat/completions")
            json_data: JSON body for POST requests
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{path}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json_data,
                timeout=self.timeout,
            )
            
            self._handle_response_error(response)
            return response.json()
            
        except requests.exceptions.Timeout as e:
            raise DirectAPITimeoutError(
                f"Request timed out after {self.timeout}s",
                details=str(e)
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise DirectAPIConnectionError(
                f"Connection failed: {e}",
                details=str(e)
            ) from e
        except requests.exceptions.RequestException as e:
            raise DirectAPIError(
                f"Request failed: {e}",
                details=str(e)
            ) from e
    
    async def _make_request_async(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an async HTTP request to the API.
        
        This wraps the synchronous request in an executor for async compatibility.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._make_request(method, path, json_data)
        )
    
    def list_models(self) -> list[dict[str, Any]]:
        """List available models.
        
        Returns:
            List of model dictionaries
        """
        response = self._make_request("GET", "/models")
        return response.get("data", [])
    
    async def list_models_async(self) -> list[dict[str, Any]]:
        """List available models (async version)."""
        response = await self._make_request_async("GET", "/models")
        return response.get("data", [])
    
    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> DirectAPIResponse:
        """Make a chat completion request.
        
        Args:
            messages: List of message dictionaries
            model: Model name (overrides default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            **kwargs: Additional parameters
            
        Returns:
            DirectAPIResponse with the completion
        """
        request_data: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
        }
        
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if stop is not None:
            request_data["stop"] = stop
        
        # Add any additional parameters
        request_data.update(kwargs)
        
        self._total_requests += 1
        
        response = self._make_request("POST", "/chat/completions", request_data)
        
        # Parse response
        choices = response.get("choices", [])
        if not choices:
            raise DirectAPIError("No choices in response")
        
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "unknown")
        
        # Parse usage
        usage = response.get("usage", {})
        self._total_tokens += usage.get("total_tokens", 0)
        
        return DirectAPIResponse(
            content=content,
            model=response.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=finish_reason,
            raw_response=response,
        )
    
    async def chat_completion_async(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> DirectAPIResponse:
        """Make a chat completion request (async version)."""
        request_data: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
        }
        
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if stop is not None:
            request_data["stop"] = stop
        
        request_data.update(kwargs)
        
        self._total_requests += 1
        
        response = await self._make_request_async("POST", "/chat/completions", request_data)
        
        choices = response.get("choices", [])
        if not choices:
            raise DirectAPIError("No choices in response")
        
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "unknown")
        
        usage = response.get("usage", {})
        self._total_tokens += usage.get("total_tokens", 0)
        
        return DirectAPIResponse(
            content=content,
            model=response.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=finish_reason,
            raw_response=response,
        )
    
    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
            "endpoint": self.endpoint,
            "model": self.model,
        }


# Global client instance for convenience
_global_client: DirectAPIClient | None = None


def get_direct_api_client() -> DirectAPIClient:
    """Get or create the global DirectAPIClient instance."""
    global _global_client
    if _global_client is None:
        _global_client = DirectAPIClient()
    return _global_client


def is_direct_api_mode() -> bool:
    """Check if direct API mode is enabled."""
    return os.getenv("STRIX_DIRECT_API_MODE", "").lower() == "true"


def token_counter(text: str) -> int:
    """Estimate token count for text.
    
    This is a simple estimation based on character count.
    For more accurate counts, consider using a tokenizer.
    """
    # Rough estimation: ~4 characters per token for English text
    return len(text) // 4


def supports_prompt_caching(model: str) -> bool:
    """Check if a model supports prompt caching.
    
    Currently returns False for all models as we don't implement
    caching in direct API mode.
    """
    return False


def supports_vision(model: str) -> bool:
    """Check if a model supports vision/image inputs.
    
    This is a simple check based on model name patterns.
    """
    model_lower = model.lower()
    vision_keywords = ["vision", "gpt-4-turbo", "gpt-4o", "claude-3", "qwen-vl"]
    return any(kw in model_lower for kw in vision_keywords)
