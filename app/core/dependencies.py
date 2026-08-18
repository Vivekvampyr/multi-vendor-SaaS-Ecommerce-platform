from typing import Callable, List, Optional
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

# OAuth2 scheme for extracting Bearer token from headers
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/oauth2",
    auto_error=False,
)


def get_optional_user_for_web(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extracts user from Authorization header OR 'access_token' cookie without raising 401.
    Ideal for server-rendered HTML views.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload.get("sub"))
        user_repo = UserRepository(db)
        return user_repo.get_by_id(user_id)
    except Exception:
        return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token from header, validates JWT, and fetches authenticated User.
    """
    if not token:
        raise UnauthorizedException(
            message="Authentication credentials were not provided",
            details={"auth_error": "missing_token"},
        )

    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedException(
            message="Invalid token type",
            details={"expected": "access", "received": token_type},
        )

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException(
            message="Token missing subject identifier",
            details={"token_error": "missing_sub"},
        )

    try:
        user_id = int(subject)
    except ValueError:
        raise UnauthorizedException(message="Invalid user identifier in token")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException(message="Authenticated user no longer exists")

    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns authenticated User if valid Bearer token provided, otherwise None.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        subject = payload.get("sub")
        if not subject:
            return None
        user_id = int(subject)
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Validates that the authenticated user account is active.
    """
    if not current_user.is_active:
        raise ForbiddenException(
            message="User account is deactivated",
            details={"user_id": current_user.id},
        )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Verifies that the user holds one of the specified allowed roles.
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            role_names = [role.value for role in allowed_roles]
            raise ForbiddenException(
                message=f"Access forbidden: required role in {role_names}",
                details={
                    "user_role": current_user.role.value,
                    "required_roles": role_names,
                },
            )
        return current_user

    return role_checker


# Role shortcut dependencies
require_admin = require_roles(UserRole.ADMIN)
require_vendor = require_roles(UserRole.VENDOR)
require_customer = require_roles(UserRole.CUSTOMER)
require_vendor_or_admin = require_roles(UserRole.VENDOR, UserRole.ADMIN)


def check_resource_ownership(
    user: User,
    resource_owner_id: int,
    allow_admin: bool = True,
) -> bool:
    """
    Validates that the current user is the owner of a resource, or an admin if allowed.
    Raises ForbiddenException if unauthorized.
    """
    if allow_admin and user.role == UserRole.ADMIN:
        return True

    if user.id == resource_owner_id:
        return True

    raise ForbiddenException(
        message="You do not have permission to access or modify this resource",
        details={"user_id": user.id, "resource_owner_id": resource_owner_id},
    )
