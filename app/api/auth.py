from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import SignupRequest, LoginRequest, TokenPair, UserOut
from app.api import deps

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, svc: AuthService = Depends(get_auth_service)):
    user = svc.signup(email=payload.email, password=payload.password)
    return user


@router.post("/login", response_model=TokenPair)
def login(form_data: OAuth2PasswordRequestForm = Depends(), svc: AuthService = Depends(get_auth_service)):
    user, tokens = svc.login(email=form_data.username, password=form_data.password)
    return tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(refresh_token: str = Body(embed=True), svc: AuthService = Depends(get_auth_service)):
    tokens = svc.refresh(refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(refresh_token: str = Body(embed=True), svc: AuthService = Depends(get_auth_service)):
    svc.logout(refresh_token)
    return None


@router.get("/profile", response_model=UserOut)
def profile(current_user=Depends(deps.get_current_user)):
    return current_user
