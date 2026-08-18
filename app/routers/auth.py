from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLogin,
)
from app.schemas.common import APIResponse
from app.schemas.user import UserCreate, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer or vendor",
    description="Registers a new account. By default, allows registration with CUSTOMER or VENDOR role.",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> APIResponse[UserOut]:
    auth_service = AuthService(db)
    created_user = auth_service.register_user(user_in=user_in)
    return APIResponse(
        success=True,
        message="Registration successful. Welcome to the platform!",
        data=UserOut.model_validate(created_user),
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="User login with JSON credentials",
    description="Authenticates user with email and password, returning JWT access and refresh tokens.",
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> APIResponse[TokenResponse]:
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data)
    token_response = auth_service.generate_token_response(user)
    return APIResponse(
        success=True,
        message="Login successful",
        data=token_response,
    )


@router.post(
    "/login/oauth2",
    status_code=status.HTTP_200_OK,
    summary="OAuth2 password form login (Swagger UI compatibility)",
    include_in_schema=True,
)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    user = auth_service.authenticate_user(login_data)
    token_response = auth_service.generate_token_response(user)
    return {
        "access_token": token_response.access_token,
        "token_type": token_response.token_type,
    }


@router.post(
    "/refresh",
    response_model=APIResponse[TokenRefreshResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a newly issued access token.",
)
def refresh_token(
    refresh_in: TokenRefreshRequest,
    db: Session = Depends(get_db),
) -> APIResponse[TokenRefreshResponse]:
    auth_service = AuthService(db)
    new_token = auth_service.refresh_access_token(refresh_in.refresh_token)
    return APIResponse(
        success=True,
        message="Access token refreshed successfully",
        data=new_token,
    )


@router.get(
    "/me",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile details of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> APIResponse[UserOut]:
    return APIResponse(
        success=True,
        message="Profile retrieved successfully",
        data=UserOut.model_validate(current_user),
    )
