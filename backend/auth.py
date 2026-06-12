from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

bearer = HTTPBearer()

def create_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    return jwt.encode(
        {**data, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm
    )

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    try:
        return jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
