import uuid
from typing import Optional
from datetime import datetime

from services.database import execute_query_one, execute_command_with_return

from logger import get_logger

logger = get_logger(__name__)


class User:
    def __init__(self, **kwargs):
        self.user_id = kwargs.get("user_id")
        self.name = kwargs.get("name")
        self.email = kwargs.get("email")
        self.password_hash = kwargs.get("password_hash")
        self.created_at = kwargs.get("created_at")
        self.updated_at = kwargs.get("updated_at")

    @classmethod
    async def find_by_id(cls, user_id: str) -> Optional["User"]:
        query = "SELECT * FROM users WHERE user_id = $1"
        result = await execute_query_one(query, uuid.UUID(user_id))
        return cls(**dict(result)) if result else None

    @classmethod
    async def find_by_email(cls, email: str) -> Optional["User"]:
        query = "SELECT * FROM users WHERE email = $1"
        result = await execute_query_one(query, email)
        return cls(**dict(result)) if result else None

    @classmethod
    async def create(cls, name: str, email: str, password_hash: str) -> Optional["User"]:
        query = """
            INSERT INTO users (user_id, name, email, password_hash, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            RETURNING *
        """
        result = await execute_command_with_return(
            query, uuid.uuid4(), name, email, password_hash
        )
        return cls(**dict(result)) if result else None

    async def save(self) -> bool:
        query = """
            UPDATE users SET name = $2, email = $3, updated_at = NOW()
            WHERE user_id = $1
        """
        from services.database import execute_command

        await execute_command(query, self.user_id, self.name, self.email)
        return True

    async def delete(self) -> bool:
        query = "DELETE FROM users WHERE user_id = $1"
        from services.database import execute_command

        await execute_command(query, self.user_id)
        return True

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    def to_public_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
