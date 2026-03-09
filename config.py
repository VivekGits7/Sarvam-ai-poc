from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # ==================== SERVER CONFIGURATION ====================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    ENVIRONMENT: str = Field(default="development", description="Environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # ==================== DATABASE CONFIGURATION ====================
    POSTGRES_DB_HOST: str = Field(default="localhost", description="DB host")
    POSTGRES_DB_PORT: int = Field(default=5432, description="DB port")
    POSTGRES_DB_NAME: str = Field(default="sarvam_db", description="DB name")
    POSTGRES_DB_USER: str = Field(default="postgres", description="DB user")
    POSTGRES_DB_PASSWORD: str = Field(default="", description="DB password")

    # ==================== JWT CONFIGURATION ====================
    JWT_SECRET_KEY: str = Field(default="change-me", description="JWT secret")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Token expiry in minutes")

    # ==================== KLING AI CONFIGURATION ====================
    KLING_ACCESS_KEY: str = Field(default="", description="Kling AI Access Key")
    KLING_SECRET_KEY: str = Field(default="", description="Kling AI Secret Key")
    KLING_API_BASE_URL: str = Field(default="https://api.klingai.com", description="Kling AI API base URL")

    # ==================== AWS S3 CONFIGURATION ====================
    AWS_ACCESS_KEY_ID: str = Field(default="", description="AWS access key ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", description="AWS secret access key")
    AWS_S3_BUCKET: str = Field(default="", description="S3 bucket name")
    AWS_REGION: str = Field(default="ap-south-1", description="AWS region")

    # ==================== EXTERNAL SERVICES ====================
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL")

    # ==================== HELPER PROPERTIES ====================
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_DB_USER}:{self.POSTGRES_DB_PASSWORD}"
            f"@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB_NAME}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
