import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import (
    TokenRefreshResponse,
    TokenResponse,
    UserLogin,
)
from app.schemas.user import UserCreate, UserOut

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register_user(
        self,
        user_in: UserCreate,
        allow_admin_creation: bool = False,
    ) -> User:
        """
        Validates uniqueness, hashes password, and creates a new user.
        Disallows direct registration as ADMIN unless explicitly authorized.
        """
        if self.user_repo.exists_by_email(user_in.email):
            raise ConflictException(
                message="An account with this email address already exists",
                details={"email": user_in.email},
            )

        if user_in.role == UserRole.ADMIN and not allow_admin_creation:
            raise ForbiddenException(
                message="Self-registration as ADMIN is not permitted",
                details={"role": user_in.role.value},
            )

        hashed = hash_password(user_in.password)
        created_user = self.user_repo.create(user_in=user_in, hashed_password=hashed)
        logger.info("Successfully registered new user: id=%d, role=%s", created_user.id, created_user.role)
        return created_user

    def authenticate_user(self, login_data: UserLogin) -> User:
        """
        Authenticates user by email and password.
        """
        user = self.user_repo.get_by_email(login_data.email)
        if not user:
            raise UnauthorizedException(
                message="Incorrect email or password",
                details={"auth_error": "invalid_credentials"},
            )

        if not verify_password(login_data.password, user.hashed_password):
            raise UnauthorizedException(
                message="Incorrect email or password",
                details={"auth_error": "invalid_credentials"},
            )

        if not user.is_active:
            raise ForbiddenException(
                message="User account is deactivated. Please contact support.",
                details={"user_id": user.id},
            )

        return user

    def generate_token_response(self, user: User) -> TokenResponse:
        """
        Generates access and refresh tokens for a verified user.
        """
        access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
        )
        refresh_token = create_refresh_token(
            subject=user.id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserOut.model_validate(user),
        )

    def refresh_access_token(self, refresh_token_str: str) -> TokenRefreshResponse:
        """
        Validates refresh token and generates a new access token.
        """
        payload = decode_token(refresh_token_str)
        token_type = payload.get("type")
        if token_type != "refresh":
            raise UnauthorizedException(
                message="Invalid token type provided for refresh",
                details={"expected": "refresh", "received": token_type},
            )

        subject = payload.get("sub")
        if not subject:
            raise UnauthorizedException(
                message="Token payload is missing subject",
                details={"token_error": "missing_subject"},
            )

        try:
            user_id = int(subject)
        except ValueError:
            raise UnauthorizedException(message="Invalid user identifier in token")

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="User associated with token no longer exists")

        if not user.is_active:
            raise ForbiddenException(message="User account is deactivated")

        new_access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
        )

        return TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
