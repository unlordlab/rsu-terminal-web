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

def decode_token(token: str) -> dict | None:
    """Decodifica un token JWT en crudo (string). Devuelve None si no es válido.

    Se usa tanto para WebSockets (donde el token llega como query param,
    ya que el navegador no permite fijar cabeceras en el handshake de WS)
    como internamente desde verify_token().
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    return payload