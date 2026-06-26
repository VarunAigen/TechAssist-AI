"""Audit logging utility — records user actions for compliance."""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import AuditLog

logger = logging.getLogger(__name__)


async def log_audit_action(
    db: AsyncSession,
    tenant_id: str,
    user_id: int,
    action: str,
    resource_type: str = None,
    resource_id: int = None,
    details: dict = None,
    ip_address: str = None,
):
    """Log a user action to the audit_logs table."""
    try:
        log_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        await db.flush()
        
        logger.info(
            f"Audit log entry created: action={action}, user={user_id}, tenant={tenant_id}",
            extra={"tenant_id": tenant_id, "user_id": user_id, "action": action}
        )
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}", extra={"tenant_id": tenant_id, "user_id": user_id})
        # We don't raise the error to avoid blocking the user request if auditing fails temporarily
