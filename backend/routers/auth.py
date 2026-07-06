from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import create_token
from config import settings
from middleware.rate_limit import login_rate_limit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    password: str

@router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login(req: LoginRequest):
    if req.password != settings.community_password:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    token = create_token({"sub": "trader"})
    return {"access_token": token, "token_type": "bearer"}