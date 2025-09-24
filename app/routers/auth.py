"""
Google OAuth認証API
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from jose import JWTError, jwt
import logging

from ..database import get_db
from ..models import User, RefreshToken, UserSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# JWT設定
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "demo-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24時間
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))  # 30日

# Google OAuth設定
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/callback")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# HTTPBearer認証スキーム
security = HTTPBearer(auto_error=False)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


def create_access_token(data: dict) -> str:
    """アクセストークンを作成"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    """リフレッシュトークンを作成"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """トークンをハッシュ化"""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """現在のユーザーを取得"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報がありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効な認証トークンです",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)  # 文字列から整数に変換
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの検証に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.get("/google/url")
async def get_google_auth_url():
    """Google認証URLを取得"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth設定が不完全です"
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    request: GoogleCallbackRequest,
    db: Session = Depends(get_db)
):
    """Google認証コールバック"""
    logger.info(f"Google callback started with code: {request.code[:10]}...")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error(f"OAuth config missing: CLIENT_ID={bool(GOOGLE_CLIENT_ID)}, SECRET={bool(GOOGLE_CLIENT_SECRET)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth設定が不完全です"
        )

    logger.info(f"Exchanging code for token...")
    # 認証コードをトークンに交換
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": request.code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="認証コードの交換に失敗しました"
            )

        token_data = token_response.json()

        # ユーザー情報を取得
        user_response = await client.get(
            GOOGLE_USER_INFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ユーザー情報の取得に失敗しました"
            )

        google_user = user_response.json()

    # ユーザーをデータベースに保存または更新
    user = db.query(User).filter(User.email == google_user["email"]).first()

    if not user:
        # 新規ユーザー作成
        user = User(
            google_id=google_user["id"],
            email=google_user["email"],
            name=google_user.get("name", google_user["email"]),
            picture=google_user.get("picture")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # ユーザー設定を初期化
        user_settings = UserSettings(
            user_id=user.id,
            settings={}
        )
        db.add(user_settings)
        db.commit()
    else:
        # 既存ユーザー更新
        user.google_id = google_user["id"]
        user.name = google_user.get("name", user.name)
        user.picture = google_user.get("picture", user.picture)
        user.updated_at = datetime.utcnow()
        db.commit()

    # JWTトークンを作成 (subは文字列として保存)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token()

    # リフレッシュトークンをデータベースに保存
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """現在のユーザー情報を取得"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """トークンをリフレッシュ"""
    # リフレッシュトークンを検証
    token_hash = hash_token(request.refresh_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです"
        )

    # 新しいトークンを作成 (subは文字列として保存)
    new_access_token = create_access_token(data={"sub": str(db_token.user_id)})
    new_refresh_token = create_refresh_token()

    # 古いリフレッシュトークンを削除
    db.delete(db_token)

    # 新しいリフレッシュトークンを保存
    new_db_refresh_token = RefreshToken(
        user_id=db_token.user_id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_db_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ログアウト"""
    # ユーザーのすべてのリフレッシュトークンを削除
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()

    return {"message": "ログアウトしました"}


@router.get("/status")
async def auth_status(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """認証状態を確認"""
    if not credentials:
        return {"authenticated": False}

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        return {"authenticated": True, "user_id": int(user_id_str) if user_id_str else None}
    except JWTError:
        return {"authenticated": False}


@router.get("/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー設定を取得"""
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not user_settings:
        return {"settings": {}}
    return {"settings": user_settings.settings}


@router.put("/settings")
async def update_user_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー設定を更新"""
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()

    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.id,
            settings=settings
        )
        db.add(user_settings)
    else:
        user_settings.settings = settings
        user_settings.updated_at = datetime.utcnow()

    db.commit()
    return {"message": "設定を更新しました", "settings": settings}