from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Role hierarchy (higher index = more permissions)
ROLE_LEVELS = {"viewer": 0, "analyst": 1, "reviewer": 2, "admin": 3}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str | None = payload.get("sub")
        if not email:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.email == email, User.is_active == True).first()  # noqa: E712
    if not user:
        raise credentials_error
    return user


def require_role(*roles: str):
    """Returns a FastAPI dependency that requires one of the given roles."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}",
            )
        return current_user
    return checker


# Convenience deps
require_admin = require_role("admin")
require_admin_or_reviewer = require_role("admin", "reviewer")
require_any_auth = get_current_user
