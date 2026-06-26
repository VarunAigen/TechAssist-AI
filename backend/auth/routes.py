"""Authentication routes — login, register (tenant-aware), profile."""

import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import User, Tenant
from auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Request/Response Models ──────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterTenantRequest(BaseModel):
    """Register a new company (tenant) + its first admin user."""
    company_name: str
    admin_email: str
    admin_password: str
    admin_name: str


class RegisterUserRequest(BaseModel):
    """Register a new user within an existing tenant (invited by admin)."""
    email: str
    password: str
    full_name: str
    tenant_id: str
    role: str = "bd_rep"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_name: str


# ── Helper ───────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a company name to a URL-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:100]


def _build_token_payload(user: User, tenant: Tenant) -> dict:
    """Build the JWT payload with user + tenant info."""
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
    }


# ── Routes ───────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token (with tenant scope)."""
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Load tenant
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your organization has been deactivated. Contact support.",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(_build_token_payload(user, tenant))

    from database.audit import log_audit_action
    await log_audit_action(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="login",
        details={"email": user.email}
    )

    logger.info(f"User logged in: {user.email}", extra={"tenant_id": tenant.id, "user_id": user.id})

    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
        },
    )


@router.post("/register/tenant", response_model=AuthResponse)
async def register_tenant(request: RegisterTenantRequest, db: AsyncSession = Depends(get_db)):
    """Register a new company (tenant) and its first admin user."""
    # Validate password strength
    if len(request.admin_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == request.admin_email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    # Create slug, ensure unique
    slug = _slugify(request.company_name)
    existing_tenant = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    if existing_tenant.scalar_one_or_none():
        slug = slug + "-" + str(hash(request.admin_email))[:6]

    # Create tenant
    tenant = Tenant(
        name=request.company_name,
        slug=slug,
        plan="free",
        max_documents=20,
        max_users=5,
    )
    db.add(tenant)
    await db.flush()  # Get tenant.id

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=request.admin_email,
        password_hash=hash_password(request.admin_password),
        full_name=request.admin_name,
        role="tenant_admin",
    )
    db.add(user)
    await db.flush()  # Get user.id

    token = create_access_token(_build_token_payload(user, tenant))

    from database.audit import log_audit_action
    await log_audit_action(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="register_tenant",
        resource_type="tenant",
        resource_id=tenant.id,
        details={"company_name": tenant.name, "admin_email": user.email}
    )

    logger.info(
        f"New tenant registered: {tenant.name} ({tenant.slug})",
        extra={"tenant_id": tenant.id, "user_id": user.id},
    )

    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
        },
    )


@router.post("/register", response_model=AuthResponse)
async def register_user(request: RegisterUserRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user within an existing tenant (invited by admin)."""
    # Validate password strength
    if len(request.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # Verify tenant exists
    tenant = await db.get(Tenant, request.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(400, "Invalid or inactive organization")

    # Check if email already exists in this tenant
    existing = await db.execute(
        select(User).where(User.email == request.email, User.tenant_id == request.tenant_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered in this organization")

    # Check tenant user limit
    user_count_result = await db.execute(
        select(User).where(User.tenant_id == request.tenant_id, User.is_active == True)
    )
    user_count = len(user_count_result.scalars().all())
    if user_count >= tenant.max_users:
        raise HTTPException(400, f"Organization user limit reached ({tenant.max_users})")

    # Create user
    pwd_hash = hash_password(request.password)
    user = User(
        tenant_id=request.tenant_id,
        email=request.email,
        password_hash=pwd_hash,
        full_name=request.full_name,
        role=request.role if request.role in ("bd_rep", "tenant_admin") else "bd_rep",
    )
    db.add(user)
    await db.flush()

    token = create_access_token(_build_token_payload(user, tenant))

    from database.audit import log_audit_action
    await log_audit_action(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role}
    )

    logger.info(
        f"New user registered: {user.email}",
        extra={"tenant_id": tenant.id, "user_id": user.id},
    )

    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
        },
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile with tenant info."""
    tenant = await db.get(Tenant, current_user["tenant_id"])
    tenant_name = tenant.name if tenant else "Unknown"

    return UserProfile(
        id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        tenant_id=current_user["tenant_id"],
        tenant_name=tenant_name,
    )
