import time

import jwt
from fastapi import APIRouter, HTTPException, Request, status

from config import settings
from error import AppException, BadRequestException, ExternalServiceException, NotFoundException
from limiter import limiter
from logger import get_logger
from schema.response import (
    COMMON_ERROR_RESPONSES,
    BadRequestResponse,
    BadGatewayResponse,
    NotFoundResponse,
)
from schema.schemas import (
    KlingTokenData,
    KlingTokenResponse,
    KlingVerifyData,
    KlingVerifyResponse,
    TextToVideoRequest,
    KlingTaskData,
    KlingVideoWorkData,
    KlingCreateTaskResponse,
    KlingTaskStatusResponse,
)
from services.kling_service import generate_jwt_token, kling_api_request

logger = get_logger(__name__)

router = APIRouter(prefix="/api/kling", tags=["Kling AI"])


# ==================== TOKEN ENDPOINTS ====================


@router.post(
    "/token",
    response_model=KlingTokenResponse,
    summary="Generate Kling AI JWT token",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": KlingTokenResponse,
            "description": "Kling AI JWT token generated successfully",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Kling AI credentials not configured",
        },
    },
)
@limiter.limit("30/minute")
async def generate_token(request: Request) -> KlingTokenResponse:
    """
    Generate a JWT token for Kling AI API authentication.

    - Token is signed using KLING_ACCESS_KEY and KLING_SECRET_KEY from config
    - Token expires in 30 minutes (1800 seconds)
    - Use the returned token in `Authorization: Bearer <token>` header for Kling AI API calls
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        expire_seconds = 1800
        token = generate_jwt_token(expire_seconds=expire_seconds)

        return KlingTokenResponse(
            success=True,
            message="Kling AI token generated successfully",
            data=KlingTokenData(
                token=token,
                expires_in=expire_seconds,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Token generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/token/verify",
    response_model=KlingVerifyResponse,
    summary="Verify Kling AI JWT token",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": KlingVerifyResponse,
            "description": "Token is valid",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Token is invalid, expired, or credentials not configured",
        },
        502: {
            "model": BadGatewayResponse,
            "description": "Kling AI API is unreachable or returned an error",
        },
    },
)
@limiter.limit("30/minute")
async def verify_token(request: Request) -> KlingVerifyResponse:
    """
    Verify the Kling AI JWT token by decoding it locally and making a test API call.

    - Generates a fresh token and decodes it to verify the signature
    - Makes a test GET request to Kling AI API to confirm the token is accepted
    - Returns token claims (issuer, expiration) on success
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        # Generate and decode locally to verify signature
        token = generate_jwt_token()
        decoded = jwt.decode(token, settings.KLING_SECRET_KEY, algorithms=["HS256"])

        # Test API call to verify token is accepted by Kling AI
        try:
            await kling_api_request("GET", "/v1/images/generations")
        except Exception as api_error:
            error_str = str(api_error)
            if "401" in error_str or "403" in error_str:
                raise BadRequestException("Token rejected by Kling AI API. Check your KLING_ACCESS_KEY and KLING_SECRET_KEY.")
            if "404" in error_str or "405" in error_str:
                # 404/405 means the API accepted the token but the endpoint doesn't exist — token is valid
                pass
            else:
                raise ExternalServiceException(f"Kling AI API unreachable: {error_str}")

        return KlingVerifyResponse(
            success=True,
            message="Token is valid",
            data=KlingVerifyData(
                valid=True,
                iss=decoded.get("iss", ""),
                exp=decoded.get("exp", 0),
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== TEXT TO VIDEO ENDPOINTS ====================


@router.post(
    "/videos/text2video",
    response_model=KlingCreateTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create text-to-video generation task",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {
            "model": KlingCreateTaskResponse,
            "description": "Video generation task created successfully",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Invalid request data or Kling AI credentials not configured",
        },
        502: {
            "model": BadGatewayResponse,
            "description": "Kling AI API failed to create the task",
        },
    },
)
@limiter.limit("10/minute")
async def create_text_to_video(request: Request, data: TextToVideoRequest) -> KlingCreateTaskResponse:
    """
    Create a text-to-video generation task on Kling AI.

    - **prompt** (str, required): Video description (max 2500 chars)
    - **model_name** (str, optional): Values: `kling-v2-6`, `kling-v2-5-turbo`, `kling-v1-6`, `kling-v1-5`, `kling-v1`. Default: `kling-v2-6`
    - **negative_prompt** (str, optional): Things to avoid in the video
    - **cfg_scale** (float, optional): Guidance scale 0-1. Default: `0.5`
    - **mode** (str, optional): Values: `std` (faster), `pro` (higher quality). Default: `std`
    - **duration** (str, optional): Values: `5`, `10` seconds. Default: `5`
    - **aspect_ratio** (str, optional): Values: `16:9`, `9:16`, `1:1`. Default: `16:9`
    - Note: Returns a task_id. Poll `/videos/text2video/{task_id}` to check status and get the video URL
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        # Build request payload for Kling AI API
        payload = {
            "model_name": data.model_name.value,
            "prompt": data.prompt,
            "cfg_scale": data.cfg_scale,
            "mode": data.mode.value,
            "duration": data.duration.value,
            "aspect_ratio": data.aspect_ratio.value,
        }
        if data.negative_prompt:
            payload["negative_prompt"] = data.negative_prompt

        # Call Kling AI API
        try:
            result = await kling_api_request("POST", "/v1/videos/text2video", json_data=payload)
        except Exception as api_error:
            error_str = str(api_error)
            if "401" in error_str or "403" in error_str:
                raise BadRequestException("Authentication failed. Check your Kling AI credentials.")
            if "429" in error_str:
                raise HTTPException(status_code=429, detail="Kling AI rate limit exceeded. Please try again later.")
            raise ExternalServiceException(f"Kling AI API error: {error_str}")

        # Parse response — Kling AI returns { "code": 0, "data": { "task_id": "...", ... } }
        api_data = result.get("data", {})
        task_id = api_data.get("task_id", "")

        return KlingCreateTaskResponse(
            success=True,
            message="Video generation task created",
            data=KlingTaskData(
                task_id=task_id,
                task_status=api_data.get("task_status", "submitted"),
                task_status_msg=api_data.get("task_status_msg"),
                created_at=str(api_data.get("created_at", "")),
                updated_at=str(api_data.get("updated_at", "")),
                works=None,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Text-to-video creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/videos/text2video/{task_id}",
    response_model=KlingTaskStatusResponse,
    summary="Query text-to-video task status",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": KlingTaskStatusResponse,
            "description": "Task status retrieved successfully",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Kling AI credentials not configured",
        },
        404: {
            "model": NotFoundResponse,
            "description": "Task not found",
        },
        502: {
            "model": BadGatewayResponse,
            "description": "Kling AI API failed to return task status",
        },
    },
)
@limiter.limit("30/minute")
async def get_text_to_video_status(request: Request, task_id: str) -> KlingTaskStatusResponse:
    """
    Query the status of a text-to-video generation task.

    - **task_id** (path): Task ID returned from the create endpoint
    - Returns `submitted`, `processing`, `succeed`, or `failed` status
    - When status is `succeed`, the `works` array contains video download URLs
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        # Query Kling AI API for task status
        try:
            result = await kling_api_request("GET", f"/v1/videos/text2video/{task_id}")
        except Exception as api_error:
            error_str = str(api_error)
            if "401" in error_str or "403" in error_str:
                raise BadRequestException("Authentication failed. Check your Kling AI credentials.")
            if "404" in error_str:
                raise NotFoundException(f"Task '{task_id}' not found")
            if "429" in error_str:
                raise HTTPException(status_code=429, detail="Kling AI rate limit exceeded. Please try again later.")
            raise ExternalServiceException(f"Kling AI API error: {error_str}")

        # Parse response
        api_data = result.get("data", {})

        # Parse works array if present
        works = None
        raw_works = api_data.get("works")
        if raw_works:
            works = [
                KlingVideoWorkData(
                    id=w.get("id", ""),
                    url=w.get("resource", {}).get("resource", "") if isinstance(w.get("resource"), dict) else w.get("url", ""),
                    cover_url=w.get("cover_url") or w.get("resource", {}).get("cover", None) if isinstance(w.get("resource"), dict) else w.get("cover_url"),
                )
                for w in raw_works
            ]

        return KlingTaskStatusResponse(
            success=True,
            message="Task status retrieved",
            data=KlingTaskData(
                task_id=api_data.get("task_id", task_id),
                task_status=api_data.get("task_status", "unknown"),
                task_status_msg=api_data.get("task_status_msg"),
                created_at=str(api_data.get("created_at", "")),
                updated_at=str(api_data.get("updated_at", "")),
                works=works,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Task status query error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
