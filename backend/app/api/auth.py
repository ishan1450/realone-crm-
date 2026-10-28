from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from app.db.database import get_db
from app.models.user import User, UserRole, ApprovalStatus
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserRegister, UserResponse, UserReapply
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.permissions import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Public registration endpoint.
    Creates a new user with pending approval status and Agent role.
    If an account was previously rejected, allows them to re-apply for access.
    """
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        if existing_user.approval_status == ApprovalStatus.REJECTED.value:
            # Re-apply for access
            existing_user.full_name = user_in.full_name
            existing_user.password_hash = get_password_hash(user_in.password)
            existing_user.approval_status = ApprovalStatus.PENDING.value
            existing_user.is_active = False
            existing_user.created_at = datetime.utcnow()
            existing_user.approved_at = None
            existing_user.approved_by = None
            db.commit()
            db.refresh(existing_user)
            return existing_user
        elif existing_user.approval_status == ApprovalStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account registration is already pending administrator review.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

    user = User(
        full_name=user_in.full_name,
        email=user_in.email.lower(),
        password_hash=get_password_hash(user_in.password),
        role=UserRole.AGENT.value,  # Strictly Agent role
        approval_status=ApprovalStatus.PENDING.value,  # Strictly Pending approval
        is_active=False,  # Inactive until approved
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/reapply", response_model=UserResponse)
def reapply_for_access(reapply_in: UserReapply, db: Session = Depends(get_db)):
    """
    Allows a rejected applicant to request access again.
    Resets status back to pending approval for administrator review.
    """
    user = db.query(User).filter(User.email == reapply_in.email.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration found for this email address.",
        )

    if user.approval_status == ApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already approved. Please sign in.",
        )

    if user.approval_status == ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your application is already pending administrator approval.",
        )

    if reapply_in.full_name:
        user.full_name = reapply_in.full_name
    if reapply_in.password:
        user.password_hash = get_password_hash(reapply_in.password)

    user.approval_status = ApprovalStatus.PENDING.value
    user.is_active = False
    user.created_at = datetime.utcnow()
    user.approved_at = None
    user.approved_by = None

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user and issues short-lived access token and refresh token.
    Enforces active and approval status checks.
    """
    user = db.query(User).filter(User.email == login_data.email.lower()).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Denied/Rejected accounts
    if user.approval_status == ApprovalStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Your registration request was rejected by an administrator. You may try again for access.",
        )

    # 2. Pending approval
    if user.approval_status == ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval. An administrator must approve your account before you can log in.",
        )

    # 3. Deactivated accounts
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator.",
        )

    # 4. Strict approved check
    if user.approval_status != ApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not approved.",
        )

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id, role=user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role,
        approval_status=user.approval_status,
        full_name=user.full_name,
        email=user.email,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_data: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchanges a valid refresh token for a fresh access token.
    """
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active or user.approval_status != ApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is no longer active or approved",
        )

    new_access_token = create_access_token(subject=user.id, role=user.role)
    new_refresh_token = create_refresh_token(subject=user.id, role=user.role)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role,
        approval_status=user.approval_status,
        full_name=user.full_name,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile details.
    """
    return current_user


@router.post("/logout")
def logout():
    """
    Client-side logout signal.
    """
    return {"message": "Successfully logged out"}
