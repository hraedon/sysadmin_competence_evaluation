import logging
from typing import Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .schemas import settings
from .orchestrator import HyperVOrchestrator
from .guacamole import GuacamoleClient
from .database import get_db, User

logger = logging.getLogger(__name__)

# Shared Instances
orchestrator = HyperVOrchestrator(
    host=settings.hyperv_host,
    username=settings.hyperv_username,
    password=settings.hyperv_password,
    guest_username=settings.hyperv_guest_username,
    guest_password=settings.hyperv_guest_password,
    dry_run=settings.dry_run,
)

guac_client = GuacamoleClient(
    settings.guacamole_url,
    settings.guacamole_username,
    settings.guacamole_password
)


# ---------------------------------------------------------------------------
# Legacy auth: API key (used during transition)
# ---------------------------------------------------------------------------

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.controller_api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key


# ---------------------------------------------------------------------------
# JWT auth
# ---------------------------------------------------------------------------

async def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization: Bearer <token> header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):]
    from .services.auth_service import decode_token
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Ensure the authenticated user has admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def optional_auth(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Returns User if valid token present, None otherwise."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None
