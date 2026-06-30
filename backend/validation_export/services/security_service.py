import base64
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from backend.shared.logger import get_logger

logger = get_logger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class SecurityService:
    """
    Handles authentication, Role-Based Access Control (RBAC), and encryption.
    """
    # Simple role mapping for demonstration/enterprise integration
    ROLES = {
        "admin_key_123": ["ADMIN", "BA", "SCRUM_MASTER"],
        "ba_key_456": ["BA"],
        "sm_key_789": ["SCRUM_MASTER"]
    }

    @staticmethod
    def authenticate(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Dict[str, Any]:
        """
        Authenticates the request using the X-API-Key header.
        """
        if not api_key:
            # Fallback/allow default access in local development, but log warning
            logger.warning("No API key provided. Using anonymous development access.")
            return {"user": "dev_user", "roles": ["ADMIN", "BA", "SCRUM_MASTER"]}

        if api_key in SecurityService.ROLES:
            roles = SecurityService.ROLES[api_key]
            user = f"user_{api_key[-3:]}"
            return {"user": user, "roles": roles}

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

    @staticmethod
    def authorize(user_info: Dict[str, Any], required_roles: List[str]) -> bool:
        """
        Validates if the user possesses any of the required roles.
        """
        user_roles = user_info.get("roles", [])
        if any(role in required_roles for role in user_roles):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User lacks required permissions. Required roles: {required_roles}"
        )

    @staticmethod
    def encrypt_payload(data: str) -> str:
        """
        Simple base64 obfuscation for transit, designed to be swapped with AES-256.
        """
        if not data:
            return ""
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decrypt_payload(encrypted_data: str) -> str:
        """
        Decrypts base64 payload.
        """
        if not encrypted_data:
            return ""
        try:
            return base64.b64decode(encrypted_data.encode("utf-8")).decode("utf-8")
        except Exception:
            return encrypted_data  # fallback if not encrypted
