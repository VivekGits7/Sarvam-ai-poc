import uuid
from typing import Optional

import aioboto3
import httpx

from config import settings
from logger import get_logger

logger = get_logger(__name__)


async def download_video(video_url: str, timeout: float = 120.0) -> bytes:
    """Download video from a CDN URL.

    Args:
        video_url: URL of the video to download.
        timeout: Request timeout in seconds.

    Returns:
        Video content as bytes.
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(video_url)
        response.raise_for_status()
        return response.content


async def upload_to_s3(
    file_bytes: bytes,
    file_name: str,
    content_type: str = "video/mp4",
    folder: str = "videos",
) -> str:
    """Upload file bytes to S3 and return the public URL.

    Args:
        file_bytes: File content as bytes.
        file_name: Name of the file in S3.
        content_type: MIME type of the file.
        folder: S3 folder/prefix.

    Returns:
        Public S3 URL of the uploaded file.
    """
    s3_key = f"{folder}/{file_name}"

    session = aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    async with session.client("s3") as s3_client:
        await s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )

    s3_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
    logger.info(f"Uploaded to S3: {s3_key}")
    return s3_url


async def download_and_upload_video(
    video_url: str,
    task_id: str,
    cover_url: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Download video from Kling CDN and upload to S3.

    Args:
        video_url: Kling AI CDN video URL.
        task_id: Kling task ID (used for naming).
        cover_url: Optional cover image URL to also upload.

    Returns:
        Dict with s3_video_url and s3_cover_url.
    """
    # Generate unique filename
    unique_id = uuid.uuid4().hex[:8]
    video_filename = f"{task_id}_{unique_id}.mp4"

    # Download and upload video
    video_bytes = await download_video(video_url)
    s3_video_url = await upload_to_s3(video_bytes, video_filename)

    # Download and upload cover image if provided
    s3_cover_url = None
    if cover_url:
        cover_filename = f"{task_id}_{unique_id}_cover.jpg"
        cover_bytes = await download_video(cover_url)
        s3_cover_url = await upload_to_s3(
            cover_bytes, cover_filename, content_type="image/jpeg", folder="covers"
        )

    return {
        "s3_video_url": s3_video_url,
        "s3_cover_url": s3_cover_url,
    }
