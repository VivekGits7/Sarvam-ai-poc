import time
from typing import Any

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
    KlingVideoUrlData,
    KlingVideoUrlResponse,
    KlingS3UploadData,
    KlingS3UploadResponse,
)
from services.kling_service import generate_jwt_token, kling_api_request
from services.s3_service import download_and_upload_video

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
    - **sound** (str, optional): Generate native audio (dialogue, ambient sound, effects). Values: `on`, `off`. Default: `on`. Supported on kling-v2-6+
    - Note: Returns a task_id. Poll `/videos/text2video/{task_id}` to check status and get the video URL
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        # Build request payload for Kling AI API
        payload: dict[str, Any] = {
            "model_name": data.model_name.value,
            "prompt": data.prompt,
            "negative_prompt": data.negative_prompt or "",
            "mode": data.mode.value,
            "duration": data.duration.value,
            "aspect_ratio": data.aspect_ratio.value,
            "sound": data.sound.value,
            "callback_url": "",
            "external_task_id": "",
        }
        if data.cfg_scale is not None:
            payload["cfg_scale"] = data.cfg_scale

        logger.info(f"Kling API payload: {payload}")

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

        # Parse videos from task_result.videos (actual Kling AI response format)
        works = None
        task_result = api_data.get("task_result", {})
        if task_result:
            raw_videos = task_result.get("videos", [])
            if raw_videos:
                works = [
                    KlingVideoWorkData(
                        id=v.get("id", ""),
                        url=v.get("url", ""),
                        cover_url=v.get("cover_url"),
                    )
                    for v in raw_videos
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


@router.get(
    "/videos/{task_id}/url",
    response_model=KlingVideoUrlResponse,
    summary="Get video URL for a completed task",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": KlingVideoUrlResponse,
            "description": "Video URL retrieved successfully",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Task is still processing or credentials not configured",
        },
        404: {
            "model": NotFoundResponse,
            "description": "Task not found",
        },
        502: {
            "model": BadGatewayResponse,
            "description": "Kling AI API failed",
        },
    },
)
@limiter.limit("30/minute")
async def get_video_url(request: Request, task_id: str) -> KlingVideoUrlResponse:
    """
    Get the video download URL for a completed generation task.

    - **task_id** (path): Task ID returned from the create endpoint
    - Returns the video URL and cover image URL when task status is `succeed`
    - Returns task status with null URLs if still processing
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

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

        api_data = result.get("data", {})
        task_status = api_data.get("task_status", "unknown")

        # Extract video URL from task_result.videos
        video_url = None
        cover_url = None
        task_result = api_data.get("task_result", {})
        if task_result:
            videos = task_result.get("videos", [])
            if videos:
                video_url = videos[0].get("url")
                cover_url = videos[0].get("cover_url")

        if task_status == "succeed" and not video_url:
            raise BadRequestException("Task succeeded but no video URL found in response")

        message = "Video is ready" if video_url else f"Task is {task_status}"

        return KlingVideoUrlResponse(
            success=True,
            message=message,
            data=KlingVideoUrlData(
                task_id=api_data.get("task_id", task_id),
                task_status=task_status,
                video_url=video_url,
                cover_url=cover_url,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Get video URL error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== S3 UPLOAD ENDPOINTS ====================


@router.post(
    "/videos/{task_id}/save",
    response_model=KlingS3UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save Kling video to S3",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {
            "model": KlingS3UploadResponse,
            "description": "Video downloaded from Kling CDN and uploaded to S3",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Task not yet complete, credentials not configured, or S3 not configured",
        },
        404: {
            "model": NotFoundResponse,
            "description": "Task not found",
        },
        502: {
            "model": BadGatewayResponse,
            "description": "Kling AI API or S3 upload failed",
        },
    },
)
@limiter.limit("10/minute")
async def save_video_to_s3(request: Request, task_id: str) -> KlingS3UploadResponse:
    """
    Download a completed Kling video from CDN and upload to AWS S3.

    - **task_id** (path): Task ID returned from the create endpoint
    - Fetches the video URL from Kling AI, downloads the video, and uploads to S3
    - Also uploads the cover image if available
    - Returns permanent S3 URLs for the video and cover image
    - Note: Task must have status `succeed` before calling this endpoint
    """
    try:
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise BadRequestException("Kling AI credentials not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env")

        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_S3_BUCKET:
            raise BadRequestException("AWS S3 credentials not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET in .env")

        # Fetch task status from Kling AI
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

        api_data = result.get("data", {})
        task_status = api_data.get("task_status", "unknown")

        if task_status != "succeed":
            raise BadRequestException(f"Task is not complete yet. Current status: {task_status}")

        # Extract video and cover URLs
        task_result = api_data.get("task_result", {})
        videos = task_result.get("videos", [])
        if not videos:
            raise BadRequestException("Task succeeded but no video found in response")

        video_url = videos[0].get("url")
        cover_url = videos[0].get("cover_url")

        if not video_url:
            raise BadRequestException("Task succeeded but video URL is empty")

        # Download from Kling CDN and upload to S3
        try:
            s3_result = await download_and_upload_video(
                video_url=video_url,
                task_id=task_id,
                cover_url=cover_url,
            )
        except Exception as s3_error:
            logger.error(f"S3 upload error: {str(s3_error)}")
            raise ExternalServiceException(f"Failed to save video to S3: {str(s3_error)}")

        return KlingS3UploadResponse(
            success=True,
            message="Video saved to S3 successfully",
            data=KlingS3UploadData(
                task_id=task_id,
                s3_video_url=str(s3_result["s3_video_url"]),
                s3_cover_url=s3_result.get("s3_cover_url"),
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Save to S3 error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
