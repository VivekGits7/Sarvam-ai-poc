import time
from typing import Any, Optional

import jwt
import httpx

from config import settings
from logger import get_logger

logger = get_logger(__name__)


def generate_jwt_token(expire_seconds: int = 1800) -> str:
    """Generate a JWT token for Kling AI API authentication.

    Args:
        expire_seconds: Token expiration time in seconds. Default: 1800 (30 minutes).

    Returns:
        Encoded JWT token string.
    """
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": settings.KLING_ACCESS_KEY,
        "exp": int(time.time()) + expire_seconds,
        "nbf": int(time.time()) - 5,
    }
    return jwt.encode(payload, settings.KLING_SECRET_KEY, algorithm="HS256", headers=headers)


def get_auth_headers() -> dict[str, str]:
    """Get authorization headers with a fresh JWT token."""
    token = generate_jwt_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def kling_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Make an authenticated request to the Kling AI API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (e.g., /v1/videos/image2video)
        json_data: Request body for POST/PUT requests.
        params: Query parameters for GET requests.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response from the API.
    """
    url = f"{settings.KLING_API_BASE_URL}{endpoint}"
    headers = get_auth_headers()

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
        )
        response.raise_for_status()
        return response.json()
