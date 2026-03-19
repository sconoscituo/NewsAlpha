"""Subscription management API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.utils.auth import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscriptionPlan(BaseModel):
    id: str
    name: str
    price_krw: int
    features: List[str]


class UserSubscription(BaseModel):
    user_id: int
    plan_id: str
    keywords: List[str]
    email_enabled: bool
    email: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class SubscribeRequest(BaseModel):
    plan_id: str
    keywords: List[str] = []
    email_enabled: bool = False
    email: Optional[str] = None


PLANS = [
    SubscriptionPlan(
        id="free",
        name="무료 플랜",
        price_krw=0,
        features=["일 5개 뉴스 요약", "기본 투자 점수"],
    ),
    SubscriptionPlan(
        id="basic",
        name="베이직 플랜",
        price_krw=9900,
        features=["일 50개 뉴스 요약", "투자 점수 + 감성 분석", "이메일 뉴스레터"],
    ),
    SubscriptionPlan(
        id="premium",
        name="프리미엄 플랜",
        price_krw=29900,
        features=["무제한 뉴스 요약", "키워드 개인화", "실시간 알림", "섹터 분석"],
    ),
]


@router.get("/plans", response_model=List[SubscriptionPlan])
async def list_plans():
    """Return available subscription plans."""
    return PLANS


@router.post("/subscribe", response_model=UserSubscription)
async def subscribe(
    req: SubscribeRequest,
    current_user=Depends(get_current_user),
):
    """Subscribe current user to a plan."""
    plan = next((p for p in PLANS if p.id == req.plan_id), None)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{req.plan_id}' not found",
        )
    # In a real implementation, persist to DB and handle payment
    return UserSubscription(
        user_id=current_user.id,
        plan_id=req.plan_id,
        keywords=req.keywords,
        email_enabled=req.email_enabled,
        email=req.email,
        created_at=datetime.utcnow(),
        expires_at=None,
    )


@router.get("/me", response_model=UserSubscription)
async def get_my_subscription(current_user=Depends(get_current_user)):
    """Get current user's subscription info."""
    return UserSubscription(
        user_id=current_user.id,
        plan_id="free",
        keywords=[],
        email_enabled=False,
        email=None,
        created_at=datetime.utcnow(),
        expires_at=None,
    )


@router.delete("/cancel")
async def cancel_subscription(current_user=Depends(get_current_user)):
    """Cancel current user's subscription."""
    return {"message": "구독이 취소되었습니다.", "user_id": current_user.id}
