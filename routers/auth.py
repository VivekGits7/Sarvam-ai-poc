from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from models.auth import User
from schema.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginResponse,
    MeResponse,
    UserData,
)
from schema.response import (
    COMMON_ERROR_RESPONSES,
    BadRequestResponse,
    ConflictResponse,
    NotFoundResponse,
)
from error import AppException, ConflictException, UnauthorizedException
from limiter import limiter
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode JWT token and return the authenticated user."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise UnauthorizedException("Invalid token")
    except JWTError:
        raise UnauthorizedException("Invalid or expired token")

    user = await User.find_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User not found")
    return user


# ==================== ENDPOINTS ====================


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {
            "model": RegisterResponse,
            "description": "User registered successfully",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Invalid input data",
        },
        409: {
            "model": ConflictResponse,
            "description": "Email already registered",
        },
    },
)
@limiter.limit("10/minute")
async def register(request: Request, data: RegisterRequest) -> RegisterResponse:
    """
    Register a new user account.

    - **name** (str, required): Display name (2-255 chars)
    - **email** (str, required): Unique email address
    - **password** (str, required): Password (min 8 chars)
    """
    try:
        existing = await User.find_by_email(data.email)
        if existing:
            raise ConflictException("Email already registered")

        hashed = hash_password(data.password)
        user = await User.create(data.name, data.email, hashed)

        return RegisterResponse(
            success=True,
            message="User registered successfully",
            data=UserData(
                user_id=str(user.user_id),
                name=user.name,
                email=user.email,
                created_at=user.created_at.isoformat() if user.created_at else None,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Register error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login user",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": LoginResponse,
            "description": "Login successful, returns JWT token",
        },
        400: {
            "model": BadRequestResponse,
            "description": "Invalid credentials",
        },
    },
)
@limiter.limit("10/minute")
async def login(request: Request, request_data: OAuth2PasswordRequestForm = Depends()) -> LoginResponse:
    """
    Authenticate user with email and password.

    - **username** (str, required): User email address (OAuth2 spec uses 'username' field)
    - **password** (str, required): User password
    - Note: Uses OAuth2 form data (not JSON). Swagger Authorize button works with this endpoint.
    """
    try:
        user = await User.find_by_email(request_data.username)
        if not user or not verify_password(request_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.user_id)}
        )
        return LoginResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            token_type="bearer",
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user profile",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "model": MeResponse,
            "description": "Current user profile returned",
        },
    },
)
@limiter.limit("30/minute")
async def get_me(request: Request, current_user: User = Depends(get_current_user)) -> MeResponse:
    """
    Get the authenticated user's profile.

    - Requires valid JWT token in Authorization header
    """
    try:
        return MeResponse(
            success=True,
            message="User profile retrieved",
            data=UserData(
                user_id=str(current_user.user_id),
                name=current_user.name,
                email=current_user.email,
                created_at=current_user.created_at.isoformat() if current_user.created_at else None,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Get me error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
