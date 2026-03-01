from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import Optional, List

from schema.response import BaseResponse


# ==================== AUTH REQUEST SCHEMAS ====================


class RegisterRequest(BaseModel):
    """Request body for user registration."""
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User display name",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="User email address (must be unique)",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 characters)",
        examples=["securepassword123"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ==================== AUTH RESPONSE DATA MODELS ====================


class UserData(BaseModel):
    """Typed response data model for user."""
    user_id: str = Field(
        ...,
        description="Unique UUID of the user",
        examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"],
    )
    name: str = Field(
        ...,
        description="User display name",
        examples=["John Doe"],
    )
    email: str = Field(
        ...,
        description="User email address",
        examples=["john@example.com"],
    )
    created_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of account creation",
        examples=["2025-01-15T10:30:00"],
    )


# ==================== AUTH RESPONSE SCHEMAS ====================


class RegisterResponse(BaseResponse):
    """Response returned after successfully registering a user."""
    data: UserData = Field(..., description="The newly created user's profile data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "User registered successfully",
                "data": {
                    "user_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "created_at": "2025-01-15T10:30:00",
                },
            }
        }
    )


class LoginResponse(BaseModel):
    """Response returned after successful login."""
    success: bool = Field(default=True, description="Whether login was successful")
    message: str = Field(..., description="Login result message", examples=["Login successful"])
    access_token: str = Field(
        ...,
        description="JWT access token for authenticated requests",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Login successful",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    )


class MeResponse(BaseResponse):
    """Response returned for the current authenticated user profile."""
    data: UserData = Field(..., description="Current user's profile data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "User profile retrieved",
                "data": {
                    "user_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "created_at": "2025-01-15T10:30:00",
                },
            }
        }
    )


# ==================== KLING AI ENUMS ====================


class KlingVideoModel(str, Enum):
    """Available Kling AI video generation models."""
    V2_6_PRO = "kling-v2-6"
    V2_5_TURBO = "kling-v2-5-turbo"
    V1_6 = "kling-v1-6"
    V1_5 = "kling-v1-5"
    V1 = "kling-v1"


class KlingVideoMode(str, Enum):
    """Video generation quality mode."""
    STD = "std"
    PRO = "pro"


class KlingVideoDuration(str, Enum):
    """Video duration in seconds."""
    FIVE = "5"
    TEN = "10"


class KlingAspectRatio(str, Enum):
    """Video aspect ratio."""
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class KlingTaskStatus(str, Enum):
    """Kling AI task status values."""
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCEED = "succeed"
    FAILED = "failed"


# ==================== KLING AI REQUEST SCHEMAS ====================


class TextToVideoRequest(BaseModel):
    """Request body for Kling AI text-to-video generation."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2500,
        description="Text description of the video to generate",
        examples=["A cat playing piano in a jazz club, cinematic lighting"],
    )
    model_name: KlingVideoModel = Field(
        default=KlingVideoModel.V2_6_PRO,
        description="Model version to use. Values: `kling-v2-6`, `kling-v2-5-turbo`, `kling-v1-6`, `kling-v1-5`, `kling-v1`",
    )
    negative_prompt: Optional[str] = Field(
        default=None,
        max_length=2500,
        description="Things to avoid in the generated video",
        examples=["blurry, low quality, distorted"],
    )
    cfg_scale: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Guidance scale (0-1). Higher = more faithful to prompt",
        examples=[0.5],
    )
    mode: KlingVideoMode = Field(
        default=KlingVideoMode.STD,
        description="Generation quality. Values: `std` (standard, faster), `pro` (higher quality, slower)",
    )
    duration: KlingVideoDuration = Field(
        default=KlingVideoDuration.FIVE,
        description="Video length in seconds. Values: `5`, `10`",
    )
    aspect_ratio: KlingAspectRatio = Field(
        default=KlingAspectRatio.LANDSCAPE,
        description="Video aspect ratio. Values: `16:9`, `9:16`, `1:1`",
    )


# ==================== KLING AI RESPONSE DATA MODELS ====================


class KlingTokenData(BaseModel):
    """Kling AI JWT token data."""
    token: str = Field(
        ...,
        description="Generated JWT token for Kling AI API authentication",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
        examples=[1800],
    )


# ==================== KLING AI RESPONSE SCHEMAS ====================


class KlingTokenResponse(BaseResponse):
    """Response returned after generating a Kling AI JWT token."""
    data: KlingTokenData = Field(..., description="Generated token data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Kling AI token generated successfully",
                "data": {
                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "expires_in": 1800,
                },
            }
        }
    )


class KlingVerifyData(BaseModel):
    """Kling AI token verification result."""
    valid: bool = Field(
        ...,
        description="Whether the token is valid and accepted by Kling AI API",
        examples=[True],
    )
    iss: str = Field(
        ...,
        description="Issuer (access key) from the token",
        examples=["your_access_key"],
    )
    exp: int = Field(
        ...,
        description="Token expiration timestamp (Unix epoch)",
        examples=[1735700000],
    )


class KlingVerifyResponse(BaseResponse):
    """Response returned after verifying a Kling AI JWT token."""
    data: KlingVerifyData = Field(..., description="Token verification result")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Token is valid",
                "data": {
                    "valid": True,
                    "iss": "your_access_key",
                    "exp": 1735700000,
                },
            }
        }
    )


# ==================== KLING AI VIDEO RESPONSE DATA MODELS ====================


class KlingVideoWorkData(BaseModel):
    """Individual video work item from Kling AI."""
    id: str = Field(
        ...,
        description="Unique ID of the generated video work",
        examples=["work_abc123"],
    )
    url: str = Field(
        ...,
        description="Download URL of the generated video",
        examples=["https://cdn.klingai.com/videos/abc123.mp4"],
    )
    cover_url: Optional[str] = Field(
        None,
        description="Thumbnail/cover image URL",
        examples=["https://cdn.klingai.com/covers/abc123.jpg"],
    )


class KlingTaskData(BaseModel):
    """Kling AI video generation task data."""
    task_id: str = Field(
        ...,
        description="Unique task ID for tracking video generation",
        examples=["task_abc123def456"],
    )
    task_status: str = Field(
        ...,
        description="Current task status. Values: `submitted`, `processing`, `succeed`, `failed`",
        examples=["submitted"],
    )
    task_status_msg: Optional[str] = Field(
        None,
        description="Human-readable status message",
        examples=["Task submitted successfully"],
    )
    created_at: Optional[str] = Field(
        None,
        description="Task creation timestamp (Unix ms)",
        examples=["1735700000000"],
    )
    updated_at: Optional[str] = Field(
        None,
        description="Task last updated timestamp (Unix ms)",
        examples=["1735700060000"],
    )
    works: Optional[List[KlingVideoWorkData]] = Field(
        None,
        description="List of generated video works (populated when task succeeds)",
    )


class KlingCreateTaskResponse(BaseResponse):
    """Response returned after creating a video generation task."""
    data: KlingTaskData = Field(..., description="Created task data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Video generation task created",
                "data": {
                    "task_id": "task_abc123def456",
                    "task_status": "submitted",
                    "task_status_msg": "Task submitted successfully",
                    "created_at": "1735700000000",
                    "updated_at": "1735700000000",
                    "works": None,
                },
            }
        }
    )


class KlingTaskStatusResponse(BaseResponse):
    """Response returned when querying a video generation task status."""
    data: KlingTaskData = Field(..., description="Current task data with status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Task status retrieved",
                "data": {
                    "task_id": "task_abc123def456",
                    "task_status": "succeed",
                    "task_status_msg": "Generation complete",
                    "created_at": "1735700000000",
                    "updated_at": "1735700120000",
                    "works": [
                        {
                            "id": "work_xyz789",
                            "url": "https://cdn.klingai.com/videos/abc123.mp4",
                            "cover_url": "https://cdn.klingai.com/covers/abc123.jpg",
                        }
                    ],
                },
            }
        }
    )
