"""Super Admin routes — platform-wide tenant management and usage analytics."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import Tenant, User, Document, Query
from auth.jwt_handler import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/superadmin", tags=["Super Admin"])


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    max_documents: Optional[int] = None
    max_users: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/stats")
async def get_platform_stats(
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide high-level metrics."""
    # Count tenants
    tenants_count = await db.execute(select(func.count(Tenant.id)))
    total_tenants = tenants_count.scalar()

    # Count users
    users_count = await db.execute(select(func.count(User.id)))
    total_users = users_count.scalar()

    # Count documents
    docs_count = await db.execute(select(func.count(Document.id)))
    total_documents = docs_count.scalar()

    # Count queries
    queries_count = await db.execute(select(func.count(Query.id)))
    total_queries = queries_count.scalar()

    # Avg confidence
    avg_conf_res = await db.execute(select(func.avg(Query.confidence_score)))
    avg_confidence = avg_conf_res.scalar() or 0.0

    return {
        "total_tenants": total_tenants,
        "total_users": total_users,
        "total_documents": total_documents,
        "total_queries": total_queries,
        "average_confidence": round(float(avg_confidence), 4),
    }


@router.get("/tenants")
async def list_tenants(
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants on the platform with usage stats."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()

    tenants_list = []
    for t in tenants:
        # Count users in this tenant
        u_count_res = await db.execute(
            select(func.count(User.id)).where(User.tenant_id == t.id)
        )
        user_count = u_count_res.scalar()

        # Count docs in this tenant
        d_count_res = await db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == t.id)
        )
        doc_count = d_count_res.scalar()

        # Count queries in this tenant
        q_count_res = await db.execute(
            select(func.count(Query.id)).where(Query.tenant_id == t.id)
        )
        query_count = q_count_res.scalar()

        tenants_list.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "max_documents": t.max_documents,
            "max_users": t.max_users,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "stats": {
                "users": user_count,
                "documents": doc_count,
                "queries": query_count,
            }
        })

    return tenants_list


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    current_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a tenant's settings (plan limits, active status, name)."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    if request.name is not None:
        tenant.name = request.name
    if request.plan is not None:
        tenant.plan = request.plan
    if request.max_documents is not None:
        tenant.max_documents = request.max_documents
    if request.max_users is not None:
        tenant.max_users = request.max_users
    if request.is_active is not None:
        tenant.is_active = request.is_active

    await db.flush()

    logger.info(
        f"Tenant updated by super admin: id={tenant_id}, plan={tenant.plan}, active={tenant.is_active}",
        extra={"tenant_id": tenant_id, "user_id": current_user["user_id"]},
    )

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_documents": tenant.max_documents,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
    }
